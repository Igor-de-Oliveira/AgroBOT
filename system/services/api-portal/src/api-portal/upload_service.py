import hashlib
import json
import re
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from fastapi import HTTPException, UploadFile

S3_PREFIX_FILES = "Arquivos/"
S3_PREFIX_JSON = "Json/"


def sanitize_filename(raw_name: str) -> str:
    base_name = Path(raw_name).name.strip()
    if not base_name:
        raise ValueError("Nome de arquivo invalido.")
    return re.sub(r"[^A-Za-z0-9._-]", "_", base_name)


def build_logical_file_key(file_name: str) -> str:
    stem = Path(file_name).stem or "arquivo"
    safe_stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
    file_name_hash = hashlib.sha256(file_name.lower().encode("utf-8")).hexdigest()[:16]
    return f"{safe_stem}-{file_name_hash}"


def resolve_operation(metadata_exists: bool, object_exists: bool) -> str:
    if metadata_exists and object_exists:
        return "overwrite"
    if metadata_exists and not object_exists:
        return "recreated_missing_s3_object"
    if not metadata_exists and object_exists:
        return "reconciled_missing_db_metadata"
    return "create"


async def process_upload_file(
    file: UploadFile,
    api_extractor_url: str,
    get_s3_settings: Callable[[], dict[str, str]],
    build_s3_client: Callable[[], Any],
    ensure_bucket_exists: Callable[[Any, str], None],
    object_exists_in_s3: Callable[[Any, str, str], bool],
    upload_bytes_to_s3: Callable[[Any, str, str, bytes, str], str],
    fetch_file_metadata: Callable[[str], Optional[dict[str, Any]]],
    upsert_file_metadata: Callable[..., None],
    requests_post: Callable[..., Any],
) -> dict[str, Any]:
    filename = file.filename
    if not filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo invalido.")
    filename = sanitize_filename(filename)

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Arquivo vazio.")

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    logical_file_key = build_logical_file_key(filename)
    source_object_key = f"{S3_PREFIX_FILES}{logical_file_key}/{filename}"
    json_object_key = f"{S3_PREFIX_JSON}{logical_file_key}/{Path(filename).stem}.json"

    try:
        s3_settings = get_s3_settings()
        s3_client = build_s3_client()
        ensure_bucket_exists(s3_client, s3_settings["bucket_name"])
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao inicializar configuracao S3: {exc}",
        ) from exc

    metadata_before_upload = fetch_file_metadata(filename)
    source_exists_in_s3 = object_exists_in_s3(
        s3_client, s3_settings["bucket_name"], source_object_key
    )
    source_operation = resolve_operation(metadata_before_upload is not None, source_exists_in_s3)

    try:
        source_s3_link = upload_bytes_to_s3(
            s3_client=s3_client,
            bucket_name=s3_settings["bucket_name"],
            object_key=source_object_key,
            body=file_bytes,
            content_type=file.content_type or "application/octet-stream",
        )
        upsert_file_metadata(
            file_name=filename,
            file_hash=file_hash,
            link_arquivo_aws=source_s3_link,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao salvar arquivo original no S3 ou atualizar metadados: {exc}",
        ) from exc

    try:
        response = requests_post(
            api_extractor_url,
            files={"file": (filename, file_bytes, file.content_type or "application/octet-stream")},
            timeout=300,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Falha ao encaminhar arquivo para o extractor: {exc}",
        ) from exc

    extractor_payload: dict[str, Any] = {}
    try:
        extractor_payload = response.json()
    except ValueError:
        extractor_payload = {"message": "Extractor retornou sucesso sem JSON valido."}

    json_payload_bytes = json.dumps(extractor_payload, ensure_ascii=False, indent=2).encode("utf-8")
    json_exists_in_s3 = object_exists_in_s3(s3_client, s3_settings["bucket_name"], json_object_key)
    json_operation = resolve_operation(metadata_before_upload is not None, json_exists_in_s3)

    try:
        json_s3_link = upload_bytes_to_s3(
            s3_client=s3_client,
            bucket_name=s3_settings["bucket_name"],
            object_key=json_object_key,
            body=json_payload_bytes,
            content_type="application/json",
        )
        upsert_file_metadata(
            file_name=filename,
            file_hash=file_hash,
            link_arquivo_aws=source_s3_link,
            link_json_aws=json_s3_link,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Falha ao salvar JSON no S3 ou atualizar metadados: {exc}",
        ) from exc

    return {
        "message": "Arquivo recebido, metadados sincronizados e JSON persistido no S3.",
        "file_name": filename,
        "logical_file_key": logical_file_key,
        "file_hash": file_hash,
        "source_file_s3_link": source_s3_link,
        "source_file_s3_operation": source_operation,
        "json_s3_link": json_s3_link,
        "json_s3_operation": json_operation,
        "extractor_response": extractor_payload,
    }
