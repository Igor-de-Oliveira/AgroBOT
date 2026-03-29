import os
from contextlib import asynccontextmanager

import requests
import uvicorn
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

try:
    from .database import (
        ensure_file_metadata_table,
        fetch_file_metadata,
        get_connection,
        upsert_file_metadata,
    )
    from .s3_storage import (
        build_s3_client,
        ensure_bucket_exists,
        get_s3_settings,
        object_exists_in_s3,
        upload_bytes_to_s3,
    )
    from .upload_service import process_upload_file
except ImportError:
    from database import ensure_file_metadata_table, fetch_file_metadata, get_connection, upsert_file_metadata
    from s3_storage import (
        build_s3_client,
        ensure_bucket_exists,
        get_s3_settings,
        object_exists_in_s3,
        upload_bytes_to_s3,
    )
    from upload_service import process_upload_file

dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(dirname, "templates"))

API_EXTRACTOR_URL = os.getenv("API_EXTRACTOR_URL", "http://api-extractor:8001/process_ods")


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


@app.get("/procesamento_arquivos", response_class=HTMLResponse)
async def processamento_arquivos(request: Request):
    return templates.TemplateResponse("procesamento_arquivos.html", {"request": request})


@app.post("/process_ods")
async def process_upload(file: UploadFile = File(...)):
    result = await process_upload_file(
        file=file,
        api_extractor_url=API_EXTRACTOR_URL,
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


def main():
    uvicorn.run(app, host="0.0.0.0", port=8003)


if __name__ == "__main__":
    main()
