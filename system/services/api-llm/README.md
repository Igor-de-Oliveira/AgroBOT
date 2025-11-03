# API de Embeddings & Chat (api-llm)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

> Serviço FastAPI para (1) gerar embeddings a partir de JSON e enviá-los ao banco vetorial e (2) responder perguntas usando RAG com LLM.
>

---

## Sumário
- [Visão Geral](#visão-geral)
- [Principais Endpoints](#principais-endpoints)
- [Variáveis de Ambiente](#variáveis-de-ambiente)
- [Execução](#execução)
- [Tecnologias](#tecnologias)
- [Estrutura](#estrutura)
- [Licença](#licença)

---

## Visão Geral
- Gera **embeddings OpenAI** para registros de arquivos **JSON**.
- Envia os vetores ao serviço **bd-vetorial** (`/upload_pack`).
- Realiza **busca semântica** (`/search_by_vector`) e compõe um **prompt aumentado** para o **LLM** responder via **/chat**.
- Respostas devem ser objetivas e referenciadas quando possível.

---

## Principais Endpoints
- `POST /upload_json` — recebe **1 JSON**, valida, gera embeddings e envia ao bd‑vetorial. Retorna o caminho do arquivo `*_embeddings.json`.
- `POST /upload_json_batch` — recebe **N JSONs** e processa cada um.
- `GET /chat?string=...` — embed da consulta, **top‑k=5**, monta prompt com hits e consulta o LLM. Retorna `response` e `matches`.

---

## Variáveis de Ambiente
Crie um `.env` com:
```bash
OPENAI_API_KEY=xxxx
EMBEDDING_TYPE=openai
BD_VETORIAL_URL=http://localhost:8005
```
Valores internos notáveis:
- `MODEL_NAME=gpt-4o-mini`, `TEMPERATURE=0.9`, `MAX_TOKENS=1000`, `TIMEOUT=10`
- `MODEL_EMBEDDING=text-embedding-ada-002`
- Saída local: `./processed_data`

---

## Execução

### Local
```bash
cd .\system\services\api-llm\
uv run python .\src\api-llm\main.py
```
A API inicia em `http://localhost:8002`.

### Docker (exemplo)
```bash
docker build -t api-llm .
docker run -p 8002:8002 --env-file .env api-llm
```

---

## Tecnologias
- **FastAPI** + **Uvicorn**
- **OpenAI Embeddings** e **ChatOpenAI** (LangChain)
- **Requests** para integração HTTP
- **dotenv** para variáveis de ambiente

---
