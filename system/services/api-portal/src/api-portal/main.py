import os
from contextlib import asynccontextmanager

import requests
import uvicorn
from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from .database import (
        delete_file_metadata_by_id,
        ensure_file_metadata_table,
        fetch_file_metadata_by_id,
        fetch_file_metadata,
        get_connection,
        list_file_metadata,
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
    from .upload_service import process_upload_file
except ImportError:
    from database import (
        delete_file_metadata_by_id,
        ensure_file_metadata_table,
        fetch_file_metadata,
        fetch_file_metadata_by_id,
        get_connection,
        list_file_metadata,
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
    from upload_service import process_upload_file

dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(dirname, "templates"))

API_EXTRACTOR_URL = os.getenv("API_EXTRACTOR_URL", "http://api-extractor:8001/process_ods")
API_LLM_INGEST_URL = os.getenv("API_LLM_INGEST_URL", "http://api-llm:8002/ingest_json_reference")
ALLOWED_PAGE_SIZES = {25, 50, 100}


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_file_metadata_table(dirname)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/", response_class=HTMLResponse)
async def tela(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})


app.mount("/static", StaticFiles(directory=os.path.join(dirname, "static")), name="static")


@app.get("/arquivos", response_class=HTMLResponse)
async def process_ods(request: Request):
    return templates.TemplateResponse("Arquivos.html", {"request": request})


@app.get("/arquivos/{file_id}", response_class=HTMLResponse)
async def file_details_page(request: Request, file_id: int):
    return templates.TemplateResponse("arquivo_detalhe.html", {"request": request, "file_id": file_id})


@app.get("/procesamento_arquivos", response_class=HTMLResponse)
async def processamento_arquivos(request: Request):
    return templates.TemplateResponse("procesamento_arquivos.html", {"request": request})


@app.post("/process_ods")
async def process_upload(file: UploadFile = File(...)):
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
    )
    return JSONResponse(content=result)


def validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise HTTPException(status_code=400, detail="Parametro 'page' deve ser >= 1.")
    if page_size not in ALLOWED_PAGE_SIZES:
        raise HTTPException(status_code=400, detail="Parametro 'page_size' deve ser 25, 50 ou 100.")


@app.get("/api/files")
async def list_files(page: int = Query(default=1), page_size: int = Query(default=25)):
    validate_pagination(page, page_size)
    items, total = list_file_metadata(page=page, page_size=page_size)
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@app.get("/api/files/{file_id}")
async def file_details(file_id: int):
    metadata = fetch_file_metadata_by_id(file_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado.")
    return metadata


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int):
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


def main():
    uvicorn.run(app, host="0.0.0.0", port=8003)


if __name__ == "__main__":
    main()
