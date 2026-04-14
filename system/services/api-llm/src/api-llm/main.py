from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import json
import logging
import os
import requests
import uvicorn

app = FastAPI()
logger = logging.getLogger(__name__)


class Config:
    load_dotenv()
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.9
    MAX_TOKENS = 1000
    TIMEOUT = 10
    MODEL_EMBEDDING = "text-embedding-ada-002"
    EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "openai")
    INGEST_SOURCE_TIMEOUT = int(os.getenv("INGEST_SOURCE_TIMEOUT", "30"))

    BASE_OUTPUT_DIR = "./processed_data"
    BD_VETORIAL_URL = os.getenv("BD_VETORIAL_URL", "http://localhost:8005")


if Config.EMBEDDING_TYPE == "openai":
    embeddings = OpenAIEmbeddings(
        model=Config.MODEL_EMBEDDING,
        openai_api_key=Config.API_KEY,
    )
else:
    raise ValueError(f"Tipo de embedding '{Config.EMBEDDING_TYPE}' nao suportado.")


class IngestionRequest(BaseModel):
    file_id: Optional[int] = None
    file_name: Optional[str] = None
    file_hash: str
    logical_file_key: str
    json_reference: str
    json_internal_reference: Optional[str] = None


def _log_ingestion(event: str, **payload: Any) -> None:
    logger.info(json.dumps({"event": event, **payload}, ensure_ascii=False, default=str))


def _generate_embeddings_from_records(records: List[dict]) -> List[List[float]]:
    texts = [" ".join(f"{key}: {value}" for key, value in record.items()) for record in records]
    return embeddings.embed_documents(texts)


def normalize_records(data: Any) -> List[dict]:
    if isinstance(data, list):
        if not all(isinstance(item, dict) for item in data):
            raise ValueError("A lista JSON deve conter apenas objetos.")
        return data

    if isinstance(data, dict):
        records = data.get("records")
        if isinstance(records, list) and all(isinstance(item, dict) for item in records):
            return records

        artifacts = data.get("artifacts")
        if isinstance(artifacts, list):
            collected_records: List[dict] = []
            for artifact in artifacts:
                if not isinstance(artifact, dict):
                    continue
                artifact_records = artifact.get("records")
                if isinstance(artifact_records, list):
                    collected_records.extend([item for item in artifact_records if isinstance(item, dict)])
            if collected_records:
                return collected_records

    raise ValueError("JSON de entrada sem formato suportado para registros.")


def process_single_json_file(json_path: str):
    file_name = os.path.basename(json_path)
    output_dir = os.path.join(Config.BASE_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = normalize_records(data)
    embedding_result = _generate_embeddings_from_records(records)

    send_embeddings_to_bd_vetorial(records, embedding_result)

    output_file = os.path.join(output_dir, file_name.replace(".json", "_embeddings.json"))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embedding_result, f, ensure_ascii=False, indent=4)

    return output_file


def send_embeddings_to_bd_vetorial(records: List[dict], generated_embeddings: List[List[float]]):
    url = f"{Config.BD_VETORIAL_URL}/upload_pack"
    payload = {"records": records, "embeddings": generated_embeddings}
    headers = {"Content-Type": "application/json"}

    response = requests.post(url, json=payload, headers=headers, timeout=Config.TIMEOUT)
    response.raise_for_status()


def embed_query(text: str) -> List[float]:
    return embeddings.embed_query(text)


def search_in_bd_vetorial(query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None):
    url = f"{Config.BD_VETORIAL_URL}/search_by_vector"
    payload = {"vector": query_vector, "top_k": top_k, "filters": filters or None}
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=Config.TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def generate_custom_prompt_from_hits(hits: List[dict], query: str) -> str:
    chunks = []
    for hit in hits:
        payload = hit.get("payload", {})
        record = payload.get("record", payload)
        chunks.append(json.dumps(record, ensure_ascii=False))

    source_knowledge = "\n".join(chunks)
    return (
        "Voce e um assistente especializado no monitoramento hidroponico de alface. "
        "Responda somente com base no contexto fornecido. "
        "Se nao houver contexto suficiente, diga que nao e possivel responder.\n\n"
        f"Contexto:\n{source_knowledge}\n\n"
        f"Pergunta:\n{query}\n"
    )


@app.post("/upload_json")
async def upload_json(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .json")

    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", file.filename)

    content = await file.read()
    try:
        parsed = json.loads(content.decode("utf-8"))
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=4)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Erro ao ler o JSON: {exc}") from exc

    try:
        output_file = process_single_json_file(temp_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar embeddings: {exc}") from exc
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {"message": "Arquivo recebido e processado com sucesso.", "embedding_file": output_file}


@app.post("/upload_json_batch")
async def upload_json_batch(files: List[UploadFile] = File(...)):
    os.makedirs("temp", exist_ok=True)

    results = []
    for file in files:
        if not file.filename.lower().endswith(".json"):
            results.append({"filename": file.filename, "status": "skipped", "reason": "nao e .json"})
            continue

        temp_path = os.path.join("temp", file.filename)
        content = await file.read()
        try:
            parsed = json.loads(content.decode("utf-8"))
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)
            output_file = process_single_json_file(temp_path)
            results.append({"filename": file.filename, "status": "ok", "embedding_file": output_file})
        except Exception as exc:
            results.append({"filename": file.filename, "status": "error", "error": str(exc)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return {"results": results}


@app.post("/ingest_json_reference")
async def ingest_json_reference(payload: IngestionRequest):
    _log_ingestion(
        "ingestion_request_received",
        file_id=payload.file_id,
        file_name=payload.file_name,
        file_hash=payload.file_hash,
        logical_file_key=payload.logical_file_key,
        json_reference=payload.json_reference,
        json_internal_reference=payload.json_internal_reference,
    )

    source_payload = None
    source_url_used = None
    source_errors: List[str] = []
    source_urls = []
    if payload.json_internal_reference:
        source_urls.append(payload.json_internal_reference)
    source_urls.append(payload.json_reference)

    for source_url in source_urls:
        try:
            source_response = requests.get(source_url, timeout=Config.INGEST_SOURCE_TIMEOUT)
            source_response.raise_for_status()
            source_payload = source_response.json()
            source_url_used = source_url
            break
        except requests.Timeout as exc:
            source_errors.append(f"timeout:{source_url}:{exc}")
        except requests.RequestException as exc:
            source_errors.append(f"network:{source_url}:{exc}")
        except ValueError as exc:
            source_errors.append(f"invalid_json:{source_url}:{exc}")

    if source_payload is None:
        _log_ingestion(
            "ingestion_source_unavailable",
            file_id=payload.file_id,
            file_hash=payload.file_hash,
            source_errors=source_errors,
        )
        raise HTTPException(
            status_code=502,
            detail={
                "code": "INGEST_SOURCE_UNAVAILABLE",
                "message": "Falha de rede ao buscar JSON de referencia para ingestao.",
                "attempts": source_urls,
            },
        )

    try:
        records = normalize_records(source_payload)
        generated_embeddings = _generate_embeddings_from_records(records)
        send_embeddings_to_bd_vetorial(records, generated_embeddings)
    except ValueError as exc:
        _log_ingestion("ingestion_payload_invalid", file_id=payload.file_id, file_hash=payload.file_hash, error=str(exc))
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INGEST_PAYLOAD_INVALID",
                "message": "JSON referenciado sem estrutura valida para gerar embeddings.",
            },
        ) from exc
    except requests.RequestException as exc:
        _log_ingestion("ingestion_vector_store_error", file_id=payload.file_id, file_hash=payload.file_hash, error=str(exc))
        raise HTTPException(
            status_code=502,
            detail={
                "code": "VECTOR_STORE_UNAVAILABLE",
                "message": "Falha ao enviar embeddings para o bd-vetorial.",
            },
        ) from exc

    _log_ingestion(
        "ingestion_completed",
        file_id=payload.file_id,
        file_hash=payload.file_hash,
        logical_file_key=payload.logical_file_key,
        records_count=len(records),
        source_url=source_url_used,
    )

    return {
        "message": "Ingestao concluida com sucesso.",
        "status": "success",
        "file_id": payload.file_id,
        "file_hash": payload.file_hash,
        "logical_file_key": payload.logical_file_key,
        "json_reference": payload.json_reference,
        "records_count": len(records),
        "embeddings_count": len(generated_embeddings),
    }


@app.get("/chat")
def chat(string: str):
    try:
        query = string
        q_vec = embed_query(query)
        search_res = search_in_bd_vetorial(q_vec, top_k=5, filters=None)
        hits = search_res.get("results", [])
        prompt = generate_custom_prompt_from_hits(hits, query)

        chat_llm = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=Config.TEMPERATURE,
            openai_api_key=Config.API_KEY,
            max_tokens=Config.MAX_TOKENS,
            timeout=Config.TIMEOUT,
        )
        messages = [HumanMessage(content=prompt)]
        response = chat_llm.invoke(messages)

        return {"response": response.content, "matches": hits}

    except requests.exceptions.RequestException as exc:
        return {"error": f"Falha na comunicacao com bd-vetorial: {exc}"}
    except Exception as exc:
        return {"error": str(exc)}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8002)


if __name__ == "__main__":
    main()
