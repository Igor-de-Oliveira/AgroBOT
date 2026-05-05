import base64
import hashlib
import hmac
import logging
import os
import secrets
from contextlib import asynccontextmanager
from typing import Optional

import requests
import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from psycopg.errors import UniqueViolation
from starlette.middleware.sessions import SessionMiddleware

try:
    from .database import (
        count_portal_users,
        create_portal_user,
        deactivate_portal_user,
        delete_file_metadata_by_id,
        delete_portal_user_by_id,
        ensure_file_metadata_table,
        fetch_file_metadata,
        fetch_file_metadata_by_id,
        fetch_portal_user_by_id,
        fetch_portal_user_by_username,
        get_connection,
        list_file_metadata,
        list_portal_users,
        touch_portal_user_last_login,
        update_file_processing_status,
        update_portal_user,
        upsert_file_metadata,
    )
    from .s3_storage import (
        build_s3_client,
        delete_object_from_s3,
        ensure_bucket_exists,
        extract_s3_key_from_link,
        get_s3_settings,
        object_exists_in_s3,
        upload_bytes_to_s3,
    )
    from .upload_service import execute_llm_ingestion_task, process_upload_file
except ImportError:
    from database import (
        count_portal_users,
        create_portal_user,
        deactivate_portal_user,
        delete_file_metadata_by_id,
        delete_portal_user_by_id,
        ensure_file_metadata_table,
        fetch_file_metadata,
        fetch_file_metadata_by_id,
        fetch_portal_user_by_id,
        fetch_portal_user_by_username,
        get_connection,
        list_file_metadata,
        list_portal_users,
        touch_portal_user_last_login,
        update_file_processing_status,
        update_portal_user,
        upsert_file_metadata,
    )
    from s3_storage import (
        build_s3_client,
        delete_object_from_s3,
        ensure_bucket_exists,
        extract_s3_key_from_link,
        get_s3_settings,
        object_exists_in_s3,
        upload_bytes_to_s3,
    )
    from upload_service import execute_llm_ingestion_task, process_upload_file

logger = logging.getLogger("api-portal.auth")


dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(dirname, "templates"))

API_EXTRACTOR_URL = os.getenv("API_EXTRACTOR_URL", "http://api-extractor:8001/process_ods")
API_LLM_INGEST_URL = os.getenv("API_LLM_INGEST_URL", "http://api-llm:8002/ingest_json_reference")
ALLOWED_PAGE_SIZES = {25, 50, 100}

SESSION_SECRET_KEY = os.getenv("PORTAL_SESSION_SECRET", "dev-portal-session-secret-change-me")
SESSION_COOKIE_NAME = os.getenv("PORTAL_SESSION_COOKIE", "portal_session")
SESSION_MAX_AGE_SECONDS = int(os.getenv("PORTAL_SESSION_MAX_AGE", "28800"))
SESSION_SAMESITE = os.getenv("PORTAL_SESSION_SAMESITE", "lax").lower()
APP_ENV = os.getenv("APP_ENV", "development").lower()
SESSION_SECURE = os.getenv("PORTAL_SESSION_SECURE", "true" if APP_ENV == "production" else "false").lower() == "true"

PASSWORD_HASH_ITERATIONS = int(os.getenv("PORTAL_PASSWORD_HASH_ITERATIONS", "390000"))
DEFAULT_CREDENTIALS = "admin,usuario"


class LoginPayload(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=1, max_length=256)


class CreatePortalUserPayload(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=256)
    credential: str = Field(default="usuario", min_length=1, max_length=50)
    is_active: bool = True


class UpdatePortalUserPayload(BaseModel):
    username: str = Field(min_length=3, max_length=120)
    credential: str = Field(min_length=1, max_length=50)
    is_active: bool = True
    password: Optional[str] = Field(default=None, min_length=8, max_length=256)


def get_allowed_credentials() -> set[str]:
    configured = os.getenv("PORTAL_ALLOWED_CREDENTIALS", DEFAULT_CREDENTIALS)
    return {value.strip().lower() for value in configured.split(",") if value.strip()}


def validate_credential(credential: str) -> str:
    normalized = credential.strip().lower()
    allowed = get_allowed_credentials()
    if normalized not in allowed:
        accepted = ", ".join(sorted(allowed))
        raise HTTPException(status_code=400, detail=f"credential invalida. Valores aceitos: {accepted}")
    return normalized


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_HASH_ITERATIONS)
    return "pbkdf2_sha256${iterations}${salt}${digest}".format(
        iterations=PASSWORD_HASH_ITERATIONS,
        salt=base64.b64encode(salt).decode("ascii"),
        digest=base64.b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_b64, digest_b64 = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_str)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected_digest = base64.b64decode(digest_b64.encode("ascii"))
    except Exception:
        return False

    actual_digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual_digest, expected_digest)


def ensure_initial_admin_user() -> None:
    seed_enabled = os.getenv("PORTAL_SEED_INITIAL_USER", "true").lower() == "true"
    if not seed_enabled:
        return

    if count_portal_users() > 0:
        return

    initial_username = os.getenv("PORTAL_INITIAL_ADMIN_USERNAME", "admin").strip()
    initial_password = os.getenv("PORTAL_INITIAL_ADMIN_PASSWORD", "admin123")
    initial_credential = validate_credential(os.getenv("PORTAL_INITIAL_ADMIN_CREDENTIAL", "admin"))

    create_portal_user(
        username=initial_username,
        credential=initial_credential,
        password_hash=hash_password(initial_password),
        is_active=True,
    )
    logger.info("Usuario inicial criado com sucesso: username=%s", initial_username)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_file_metadata_table(dirname)
    ensure_initial_admin_user()
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET_KEY,
    session_cookie=SESSION_COOKIE_NAME,
    max_age=SESSION_MAX_AGE_SECONDS,
    same_site=SESSION_SAMESITE,
    https_only=SESSION_SECURE,
)


app.mount("/static", StaticFiles(directory=os.path.join(dirname, "static")), name="static")


def get_authenticated_user(request: Request) -> Optional[dict]:
    user_id = request.session.get("user_id")
    if not user_id:
        return None

    user = fetch_portal_user_by_id(int(user_id))
    if not user or not user["is_active"]:
        request.session.clear()
        return None

    return user


def require_authenticated_api_user(request: Request) -> dict:
    user = get_authenticated_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Sessao invalida ou expirada. Faca login novamente.")
    return user


def require_admin_user(request: Request) -> dict:
    user = require_authenticated_api_user(request)
    if user["credential"] != "admin":
        raise HTTPException(status_code=403, detail="Acesso restrito a usuarios administradores.")
    return user


def redirect_if_not_authenticated(request: Request) -> Optional[RedirectResponse]:
    user = get_authenticated_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return None


def redirect_if_not_admin(request: Request) -> Optional[RedirectResponse]:
    redirect = redirect_if_not_authenticated(request)
    if redirect:
        return redirect

    user = get_authenticated_user(request)
    if not user or user["credential"] != "admin":
        return RedirectResponse(url="/", status_code=303)
    return None


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_authenticated_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error_message": ""})


@app.post("/login", response_class=HTMLResponse)
async def login_form(request: Request, username: str = Form(...), password: str = Form(...)):
    sanitized_username = username.strip()
    user = fetch_portal_user_by_username(sanitized_username, include_password_hash=True)
    if not user or not user["is_active"] or not verify_password(password, user["password_hash"]):
        logger.warning("Falha de autenticacao no login HTML para username=%s", sanitized_username)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error_message": "Usuario ou senha invalidos.",
            },
            status_code=401,
        )

    request.session["user_id"] = int(user["id"])
    touch_portal_user_last_login(int(user["id"]))
    logger.info("Login HTML realizado com sucesso para username=%s", sanitized_username)
    return RedirectResponse(url="/", status_code=303)


@app.post("/logout")
async def logout_form(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)


@app.post("/api/auth/login")
async def api_login(request: Request, payload: LoginPayload):
    username = payload.username.strip()
    user = fetch_portal_user_by_username(username, include_password_hash=True)

    if not user or not user["is_active"] or not verify_password(payload.password, user["password_hash"]):
        logger.warning("Falha de autenticacao na API para username=%s", username)
        raise HTTPException(status_code=401, detail="Usuario ou senha invalidos.")

    request.session["user_id"] = int(user["id"])
    touch_portal_user_last_login(int(user["id"]))
    logger.info("Login API realizado com sucesso para username=%s", username)

    return {
        "message": "Login realizado com sucesso.",
        "user": fetch_portal_user_by_id(int(user["id"])),
    }


@app.post("/api/auth/logout")
async def api_logout(request: Request):
    request.session.clear()
    return {"message": "Logout realizado com sucesso."}


@app.get("/api/auth/session")
async def api_session_status(request: Request):
    user = get_authenticated_user(request)
    if not user:
        return JSONResponse(status_code=401, content={"authenticated": False})
    return {"authenticated": True, "user": user}


@app.get("/", response_class=HTMLResponse)
async def tela(request: Request):
    redirect = redirect_if_not_authenticated(request)
    if redirect:
        return redirect
    current_user = get_authenticated_user(request)
    return templates.TemplateResponse("main.html", {"request": request, "current_user": current_user})


@app.get("/user", response_class=HTMLResponse)
async def legacy_users_redirect(request: Request):
    redirect = redirect_if_not_admin(request)
    if redirect:
        return redirect
    return RedirectResponse(url="/usuarios", status_code=303)


@app.get("/usuarios", response_class=HTMLResponse)
async def users_page(request: Request):
    redirect = redirect_if_not_admin(request)
    if redirect:
        return redirect
    current_user = get_authenticated_user(request)
    return templates.TemplateResponse("usuarios.html", {"request": request, "current_user": current_user})


@app.get("/arquivos", response_class=HTMLResponse)
async def process_ods(request: Request):
    redirect = redirect_if_not_authenticated(request)
    if redirect:
        return redirect
    current_user = get_authenticated_user(request)
    return templates.TemplateResponse("Arquivos.html", {"request": request, "current_user": current_user})


@app.get("/arquivos/{file_id}", response_class=HTMLResponse)
async def file_details_page(request: Request, file_id: int):
    redirect = redirect_if_not_authenticated(request)
    if redirect:
        return redirect
    current_user = get_authenticated_user(request)
    return templates.TemplateResponse(
        "arquivo_detalhe.html", {"request": request, "file_id": file_id, "current_user": current_user}
    )


@app.get("/procesamento_arquivos", response_class=HTMLResponse)
async def processamento_arquivos(request: Request):
    redirect = redirect_if_not_authenticated(request)
    if redirect:
        return redirect
    current_user = get_authenticated_user(request)
    return templates.TemplateResponse("procesamento_arquivos.html", {"request": request, "current_user": current_user})


@app.post("/process_ods")
async def process_upload(request: Request, background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    require_authenticated_api_user(request)
    result = await process_upload_file(
        file=file,
        api_extractor_url=API_EXTRACTOR_URL,
        api_llm_ingest_url=API_LLM_INGEST_URL,
        get_s3_settings=get_s3_settings,
        build_s3_client=build_s3_client,
        ensure_bucket_exists=ensure_bucket_exists,
        object_exists_in_s3=object_exists_in_s3,
        upload_bytes_to_s3=upload_bytes_to_s3,
        fetch_file_metadata=fetch_file_metadata,
        upsert_file_metadata=upsert_file_metadata,
        requests_post=requests.post,
        schedule_background_ingestion=lambda ingestion_payload: schedule_ingestion_task(
            background_tasks=background_tasks,
            ingestion_payload=ingestion_payload,
        ),
    )
    return JSONResponse(content=result)


def schedule_ingestion_task(background_tasks: BackgroundTasks, ingestion_payload: dict) -> None:
    background_tasks.add_task(
        execute_llm_ingestion_task,
        ingestion_payload=ingestion_payload,
        api_llm_ingest_url=API_LLM_INGEST_URL,
        requests_post=requests.post,
        update_file_processing_status=update_file_processing_status,
    )


def validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise HTTPException(status_code=400, detail="Parametro 'page' deve ser >= 1.")
    if page_size not in ALLOWED_PAGE_SIZES:
        raise HTTPException(status_code=400, detail="Parametro 'page_size' deve ser 25, 50 ou 100.")


@app.get("/api/files")
async def list_files(request: Request, page: int = Query(default=1), page_size: int = Query(default=25)):
    require_authenticated_api_user(request)
    validate_pagination(page, page_size)
    items, total = list_file_metadata(page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/files/{file_id}")
async def file_details(request: Request, file_id: int):
    require_authenticated_api_user(request)
    metadata = fetch_file_metadata_by_id(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")
    return metadata


@app.delete("/api/files/{file_id}")
async def delete_file(request: Request, file_id: int):
    require_authenticated_api_user(request)
    metadata = fetch_file_metadata_by_id(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")

    source_link = metadata.get("link_arquivo_AWS")
    json_link = metadata.get("link_json_aws")
    if not source_link or not json_link:
        raise HTTPException(status_code=500, detail="Metadados com links AWS ausentes.")

    try:
        s3_settings = get_s3_settings()
        s3_client = build_s3_client()
        ensure_bucket_exists(s3_client, s3_settings["bucket_name"])

        source_key = extract_s3_key_from_link(source_link, s3_settings["bucket_name"])
        json_key = extract_s3_key_from_link(json_link, s3_settings["bucket_name"])
        if not source_key.startswith("Arquivos/") or not json_key.startswith("Json/"):
            raise ValueError("Links AWS fora dos prefixos esperados.")

        delete_object_from_s3(s3_client, s3_settings["bucket_name"], source_key)
        delete_object_from_s3(s3_client, s3_settings["bucket_name"], json_key)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Falha ao excluir objetos no S3: {exc}") from exc

    if not delete_file_metadata_by_id(file_id):
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado para exclusao.")

    return {"message": "Arquivo excluido com sucesso.", "id": file_id}


@app.get("/api/users")
async def api_list_users(request: Request):
    require_admin_user(request)
    return {"items": list_portal_users()}


@app.get("/api/users/{user_id}")
async def api_user_details(request: Request, user_id: int):
    require_admin_user(request)
    user = fetch_portal_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    return user


@app.post("/api/users", status_code=201)
async def api_create_user(request: Request, payload: CreatePortalUserPayload):
    require_admin_user(request)
    username = payload.username.strip()
    credential = validate_credential(payload.credential)
    password_hash = hash_password(payload.password)

    try:
        created = create_portal_user(
            username=username,
            credential=credential,
            password_hash=password_hash,
            is_active=payload.is_active,
        )
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="username ja cadastrado.") from exc

    return created


@app.put("/api/users/{user_id}")
async def api_update_user(request: Request, user_id: int, payload: UpdatePortalUserPayload):
    require_admin_user(request)
    username = payload.username.strip()
    credential = validate_credential(payload.credential)
    password_hash = hash_password(payload.password) if payload.password else None

    try:
        updated = update_portal_user(
            user_id=user_id,
            username=username,
            credential=credential,
            is_active=payload.is_active,
            password_hash=password_hash,
        )
    except UniqueViolation as exc:
        raise HTTPException(status_code=409, detail="username ja cadastrado.") from exc

    if not updated:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")
    return updated


@app.post("/api/users/{user_id}/deactivate")
async def api_deactivate_user(request: Request, user_id: int):
    require_admin_user(request)
    updated = deactivate_portal_user(user_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    if int(request.session.get("user_id", 0)) == user_id:
        request.session.clear()

    return updated


@app.delete("/api/users/{user_id}")
async def api_delete_user(request: Request, user_id: int):
    require_admin_user(request)
    if not delete_portal_user_by_id(user_id):
        raise HTTPException(status_code=404, detail="Usuario nao encontrado.")

    if int(request.session.get("user_id", 0)) == user_id:
        request.session.clear()

    return {"message": "Usuario removido com sucesso.", "id": user_id}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8003)


if __name__ == "__main__":
    main()
