from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from langchain_core.messages import HumanMessage
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from typing import List, Optional, Dict, Any
import glob
import json
import os
import requests
import uvicorn

app = FastAPI()

class Config:
    load_dotenv()
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
    texts = [" ".join(f"{key}: {value}" for key, value in record.items()) for record in records]
    embedding_result = embeddings.embed_documents(texts)
    return embedding_result

def process_single_json_file(json_path: str):
    """
    Processa um único arquivo JSON e salva os embeddings
    dentro do diretório correspondente em 'processed_data/<arquivo_sem_extensão>/'.
    """
    file_name = os.path.basename(json_path)
    output_dir = os.path.join(Config.BASE_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"O JSON '{json_path}' não contém uma lista de registros.")

    embedding_result = _generate_embeddings_from_records(data)

    # Envia embeddings para o bd-vetorial
    send_embeddings_to_bd_vetorial(data, embedding_result)

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

def embed_query(text: str) -> List[float]:
    """
    Gera embedding para uma única pergunta.
    """
    return embeddings.embed_query(text)

def search_in_bd_vetorial(query_vector: List[float], top_k: int = 5, filters: Optional[Dict[str, Any]] = None):
    """
    Chama o bd-vetorial (/search_by_vector) passando o vetor da pergunta.
    """
    url = f"{Config.BD_VETORIAL_URL}/search_by_vector"
    payload = {
        "vector": query_vector,
        "top_k": top_k,
        "filters": filters or None
    }
    headers = {"Content-Type": "application/json"}
    resp = requests.post(url, json=payload, headers=headers, timeout=Config.TIMEOUT)
    resp.raise_for_status()
    return resp.json()

def generate_custom_prompt_from_hits(hits: List[dict], query: str) -> str:
    """
    Monta o prompt aumentado a partir dos 'hits' do bd-vetorial.
    Cada hit vem com 'payload' e, dentro dele, 'record' (conforme bd-vetorial).
    """
    # Extrai conteúdo e metadados dos resultados
    chunks = []
    for h in hits:
        payload = h.get("payload", {})
        record = payload.get("record", payload) 
        chunks.append(f"{json.dumps(record, ensure_ascii=False)}")
    sorce_knowledge = "\n".join(chunks)

    augment_prompt = f"""
                        "Você é um assistente especializado no monitoramento hidropônico de uma plantação de alface, projetado para apoiar produtores em suas dúvidas sobre o cultivo. "
                        "Seu objetivo é fornecer informações precisas, esclarecer conceitos, sugerir melhorias e oferecer suporte técnico e especializado nas áreas do cultivo hidropônico de alface, incluindo parâmetros como temperatura, umidade, oxigenação, iluminação, irrigação, pH, e condutividade elétrica, com base nos materiais indexados "
                        "com base nos materiais indexados (dados coletados do monitoramento do cultivo, documentos, vídeos, livros, entre outros). "
                        "***Se não houver contexto suficiente para responder, informe que não é possível responder.*** "
                        "***Não invente respostas e nem amplie a resposta para além do contexto fornecido.*** \n"

                        "### Diretrizes de Resposta: \n"
                        "1. **Escopo**: Responda com base no conteúdo indexado. Se a pergunta não estiver relacionada aos temas do cultivo hidropônico de alface (pH, cE, temperatura, umidade, iluminação, etc.), ou não houver informações disponíveis sobre a variável solicitada, informe educadamente que não é possível responder "
                        "ou não houver informações disponíveis, informe educadamente que não é possível responder. \n"
                        "2. **Tom e Estilo**: Utilize linguagem clara e pedagógica, mantendo-se no mesmo idioma da pergunta. \n"
                        "3. **Referências**: Ao responder, ***inclua referências quando possível. Referenciar é uma boa prática esperada do agrônomo***, "
                        "pois o ajuda a rastrear e verificar as fontes de informação. Use referências que "
                        "foram de fato utilizadas na resposta. Elas podem estar no final do conteúdo, no rodapé ou no assunto. \n"
                        "4. Quando solicitado um relatório de uma data específica, apresente as seguintes informações: \n"
                        "Menor, maior e média dos valores registrados. \n"

                        "### informações uteis: \n"
                        "- **Observação**: os dasdos disponibilizados podem não conter todas as variáveis responda apenas com base nas variáveis que você tem acesso \n"
                        "- **Temperatura da solução nutritiva**: idealmente constante em 20 °C.\n"
                        "- **Temperatura ambiente com luz**: entre 25 °C e 28 °C. Sem luz: entre 19 °C e 20 °C.\n"
                        "- **pH da solução nutritiva**: entre 6.0 e 6.2. Tolerável até 5.8 ou 6.3 com perda de produtividade.\n"
                        "- **Condutividade Elétrica (EC)**: entre 1.6 e 1.9 dS/m. Faixa estendida de 1.5 a 2.5 dS/m, sendo 2.2 um valor máximo produtivo.\n"
                        "- **co2 entre 400.0 e 600.0. Tolerável até 580.0 ou 630.0 com perda de produtividade.\n"


                        "### Como Referenciar ###\n"
                        "1. Sempre que puder usar informação `reference` do metadata, use-a. Ela é mais específica e deve ser priorizada.\n"
                        "2. Quando não puder usar informação `reference` do metadata, use as informações disponíveis, extraia as referências no seguinte formato:\n"
                        "  * `Title`: O que aparece antes de `.json.` \n"
                        "  * `ActivityId`: O número imediatamente após `activity_` \n"
                        "  * Para os outros casos, extraia as referências de elementos disponíveis no metadata. \n"


                        "### Contexto: ###\n"
                        "Você tem acesso a um conjunto de dados que contém informações sobre o cultivo hidropônico de alface. "
                        "Esses dados incluem medições de temperatura interna e externa, Co2, pH e condutividade elétrica. "
                        "**Responda com mais embasamento no contexto abaixo**"
                        "{sorce_knowledge}\n\n"
                        "### Pergunta:\n"
                        "{query}\n"
                        "Responda com base nesse contexto, garantindo que sua resposta seja objetiva, fundamentada e alinhada ao propósito de um chatbot para o cultivo. Certifique-se de referenciar adequadamente cada fonte utilizada. Tente responder somente o que foi pergnutado, sem adicionar informações extras. \n\n"
                    """
    return augment_prompt

@app.post("/upload_json")
async def upload_json(file: UploadFile = File(...)):
    """
    Recebe um arquivo JSON e gera embeddings,
    salvando no mesmo padrão da outra API:
    processed_data/<arquivo_sem_extensão>/arquivo_embeddings.json
    """
    if not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Envie um arquivo .json")

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

@app.get("/chat")
def chat(string: str):
    """
    Recebe a pergunta, busca contexto no bd-vetorial e chama o LLM.
    """
    try:
        query = string

        q_vec = embed_query(query)
        search_res = search_in_bd_vetorial(q_vec, top_k=5, filters=None)

        hits = search_res.get("results", [])
        prompt = generate_custom_prompt_from_hits(hits, query)

        chat = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=Config.TEMPERATURE,
            openai_api_key=Config.API_KEY,
            max_tokens=Config.MAX_TOKENS,
            timeout=Config.TIMEOUT
        )
        messages = [HumanMessage(content=prompt)]
        response = chat.invoke(messages)

        return {"response": response.content, "matches": hits}

    except requests.exceptions.RequestException as e:
        return {"error": f"Falha na comunicação com bd-vetorial: {e}"}
    except Exception as e:
        return {"error": str(e)}

def main():
    uvicorn.run(app, host="0.0.0.0", port=8002)


if __name__ == "__main__":
    main()