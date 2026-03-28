import hashlib
import os
from contextlib import asynccontextmanager
from typing import Optional

import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from psycopg import Connection
from psycopg.rows import dict_row

dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(dirname, "templates"))

API_EXTRACTOR_URL = os.getenv("API_EXTRACTOR_URL", "http://api-extractor:8001/process_ods")
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-arquivos")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "agrobot")
POSTGRES_USER = os.getenv("POSTGRES_USER", "agrobot")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "agrobot")


def get_connection() -> Connection:
    return Connection.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def ensure_file_metadata_table() -> None:
    migration_path = os.path.abspath(
        os.path.join(dirname, "..", "..", "migrations", "001_create_file_metadata.sql")
    )
    with open(migration_path, "r", encoding="utf-8") as migration_file:
        ddl = migration_file.read()

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def upsert_file_metadata(file_name: str, file_hash: str) -> None:
    query = """
    INSERT INTO file_metadata (file_name, file_hash)
    VALUES (%s, %s)
    ON CONFLICT (file_name) DO UPDATE
    SET
        file_hash = EXCLUDED.file_hash,
        updated_at = CASE
            WHEN file_metadata.file_hash IS DISTINCT FROM EXCLUDED.file_hash THEN NOW()
            ELSE file_metadata.updated_at
        END;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (file_name, file_hash))
        conn.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_file_metadata_table()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def tela(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


app.mount("/static", StaticFiles(directory=os.path.join(dirname, "static")), name="static")


@app.get("/arquivos", response_class=HTMLResponse)
async def process_ods(request: Request):
    return templates.TemplateResponse("Arquivos.html", {"request": request})


@app.get("/procesamento_arquivos", response_class=HTMLResponse)
async def processamento_arquivos(request: Request):
    return templates.TemplateResponse("procesamento_arquivos.html", {"request": request})


@app.post("/process_ods")
async def process_upload(file: UploadFile = File(...)):
    filename: Optional[str] = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()

    try:
        upsert_file_metadata(filename, file_hash)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao persistir metadados no PostgreSQL: {exc}",
        ) from exc

    try:
        response = requests.post(
            API_EXTRACTOR_URL,
            files={"file": (filename, file_bytes, file.content_type or "application/octet-stream")},
            timeout=300,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao encaminhar arquivo para o extractor: {exc}",
        ) from exc

    extractor_payload = {}
    try:
        extractor_payload = response.json()
    except ValueError:
        extractor_payload = {"message": "Extractor retornou sucesso sem JSON valido."}

    return JSONResponse(
        content={
            "message": "Arquivo recebido, metadados salvos e envio ao extractor concluido.",
            "file_name": filename,
            "file_hash": file_hash,
            "extractor_response": extractor_payload,
        }
    )


def main():
    uvicorn.run(app, host="0.0.0.0", port=8003)


if __name__ == "__main__":
    main()
