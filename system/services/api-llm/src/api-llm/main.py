from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from langchain_openai import OpenAIEmbeddings
from typing import List
import glob
import json
import os
import requests
import uvicorn

app = FastAPI()

class Config:
    load_dotenv()  # Load environment variables from a .env file
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.9
    MAX_TOKENS = 1000
    TIMEOUT = 10
    MODEL_EMBEDDING = 'text-embedding-ada-002'
    EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "openai")

    BASE_OUTPUT_DIR = "./processed_data"
    BD_VETORIAL_URL = os.getenv("BD_VETORIAL_URL", "http://localhost:8005")

if Config.EMBEDDING_TYPE == "openai":
    embeddings = OpenAIEmbeddings(
        model=Config.MODEL_EMBEDDING,
        openai_api_key=Config.API_KEY
    )
else:
    raise ValueError(f"Tipo de embedding '{Config.EMBEDDING_TYPE}' não suportado.")

def _generate_embeddings_from_records(records: List[dict]) -> List[List[float]]:
    # 1 texto por registro -> 1 embedding por registro
    texts = [" ".join(f"{key}: {value}" for key, value in record.items()) for record in records]
    embedding_result = embeddings.embed_documents(texts)
    return embedding_result

def process_single_json_file(json_path: str):
    """
    Processa um único arquivo JSON e salva os embeddings
    dentro do diretório correspondente em 'processed_data/<arquivo_sem_extensão>/'.
    """
    # Diretório dinâmico baseado no nome do arquivo
    file_name = os.path.basename(json_path)
    output_dir = os.path.join(Config.BASE_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    # Lê o conteúdo do JSON
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"O JSON '{json_path}' não contém uma lista de registros.")

    # Gera os embeddings
    embedding_result = _generate_embeddings_from_records(data)

    # Envia embeddings para o bd-vetorial
    send_embeddings_to_bd_vetorial(data, embedding_result)

    # Salva o arquivo de embeddings no mesmo diretório do JSON original
    output_file = os.path.join(output_dir, file_name.replace(".json", "_embeddings.json"))
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(embedding_result, f, ensure_ascii=False, indent=4)

    print(f"Embeddings para '{json_path}' salvos em '{output_file}'")
    return output_file

def send_embeddings_to_bd_vetorial(records: List[dict], embeddings: List[List[float]]):
    """
    Envia os embeddings gerados para o serviço bd-vetorial.
    """
    url = f"{Config.BD_VETORIAL_URL}/upload_pack"
    payload = {
        "records": records,
        "embeddings": embeddings
    }
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar embeddings para o bd-vetorial: {e}")


@app.post("/upload_json")
async def upload_json(file: UploadFile = File(...)):
    """
    Recebe um arquivo JSON e gera embeddings,
    salvando no mesmo padrão da outra API:
    processed_data/<arquivo_sem_extensão>/arquivo_embeddings.json
    """
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .json")

    # Caminho temporário (pode ser dentro de processed_data)
    os.makedirs("temp", exist_ok=True)
    temp_path = os.path.join("temp", file.filename)

    content = await file.read()
    try:
        parsed = json.loads(content.decode("utf-8"))
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=4)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler o JSON: {e}")

    try:
        output_file = process_single_json_file(temp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar embeddings: {e}")
    finally:
        # Remove o arquivo temporário
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return {
        "message": "Arquivo recebido e processado com sucesso.",
        "embedding_file": output_file
    }


@app.post("/upload_json_batch")
async def upload_json_batch(files: List[UploadFile] = File(...)):
    """
    Recebe múltiplos arquivos JSON e gera embeddings
    no mesmo padrão de saída da outra API.
    """
    os.makedirs("temp", exist_ok=True)

    results = []
    for file in files:
        if not file.filename.lower().endswith(".json"):
            results.append({"filename": file.filename, "status": "skipped", "reason": "não é .json"})
            continue

        temp_path = os.path.join("temp", file.filename)
        content = await file.read()
        try:
            parsed = json.loads(content.decode("utf-8"))
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=4)
            output_file = process_single_json_file(temp_path)
            results.append({"filename": file.filename, "status": "ok", "embedding_file": output_file})
        except Exception as e:
            results.append({"filename": file.filename, "status": "error", "error": str(e)})
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    return {"results": results}


def main():
    uvicorn.run(app, host="0.0.0.0", port=8002)


if __name__ == "__main__":
    main()