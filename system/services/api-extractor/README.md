# API Extractor — Processador de ODS → JSON por Intervalos (FastAPI)

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg)](https://fastapi.tiangolo.com/)
[![Uvicorn](https://img.shields.io/badge/ASGI-Uvicorn-informational.svg)](https://www.uvicorn.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://www.docker.com/)

> Serviço que recebe uma planilha **.ods**, normaliza as abas, **segmenta por intervalos de 12h (08:00–20:00 e 20:00–08:00)** e exporta **JSONs por intervalo**, enviando cada arquivo gerado para um endpoint de LLM configurável via variável de ambiente.

---

## Sumário
- [Visão Geral](#-visão-geral)
- [Linguagens e Tecnologias](#-linguagens-e-tecnologias)
- [Endpoints](#-endpoints)
- [Como Executar](#-como-executar)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Exemplos de Uso](#-exemplos-de-uso)
- [Estrutura de Saída](#-estrutura-de-saída)
- [Observações e Boas Práticas](#-observações-e-boas-práticas)
- [Créditos/Template](#-créditostemplate)

> Este README segue a **estrutura** e o **tom** do modelo de README anexado, adaptado para este serviço específico.

---

## Visão Geral

Este microserviço expõe uma API **FastAPI** com um endpoint para processar arquivos **ODS**:

1. Lê todas as **abas** da planilha.
2. Remove **linhas/colunas totalmente vazias** e preenche valores ausentes.
3. Garante colunas `data` (date) e `hora` (time) quando existirem; caso contrário, informa a ausência.
4. **Classifica** cada linha em intervalos:
   - **08:00–20:00** (associado ao **mesmo dia**)
   - **20:00–08:00** (associado ao **dia seguinte**, quando aplicável)
5. Gera **JSONs por intervalo** e salva em `processed_data/<nome_arquivo>/`.
6. Para cada JSON, faz um **POST** para `API_LLM_URL` (ex.: `http://api-llm:8002/upload_json`).

---

## Linguagens e Tecnologias

- **Python 3.12**
- **FastAPI** (API REST)
- **Uvicorn** (servidor ASGI)
- **pandas** (processamento de planilhas/ODF via `engine="odf"`)
- **requests** (integração HTTP com serviço de LLM)
- **python-multipart** (upload de arquivos)
- **odfpy** (suporte ODS via engine do pandas)

---

## Endpoints

### `POST /process_ods`
- **Body (multipart/form-data)**: `file` = arquivo `.ods`
- **Ação**: processa o ODS, exporta JSONs por intervalo (por aba) e **envia** cada JSON ao LLM definido em `API_LLM_URL`.
- **Resposta (200)**:
  ```json
  { "message": "Processamento concluído com sucesso!" }
  ```
- **Erros comuns**:
  - Colunas `data` e `hora` ausentes em alguma aba → apenas loga aviso para a aba.

---

## Como Executar

### 1) Com Python direto
```bash
cd .\system\services\api-extractor\
uv run python .\src\api-extractor\main.py
```

### 2) Com Docker (exemplo básico)

```bash
docker build -t api-extractor .
docker run -p 8002:8002 --env-file .env api-extractor
```

---

## Variáveis de Ambiente

| Nome          | Obrigatória | Padrão                                   | Descrição |
|---------------|-------------|-------------------------------------------|-----------|
| `API_LLM_URL` | SIM         | `http://api-llm:8002/upload_json`         | URL para onde cada JSON gerado será enviado via `POST`. |

> Você pode usar um arquivo `.env` na raiz do projeto e carregar as variáveis antes de executar (ex.: via `dotenv`).

---

## Exemplos de Uso

### cURL
```bash
curl -X POST "http://localhost:8001/process_ods"   -H "accept: application/json"   -H "Content-Type: multipart/form-data"   -F "file=@dados.ods"
```

## Estrutura de Saída

Após o upload de `dados.ods`, os arquivos são salvos em:

```
processed_data/
└── dados/
    ├── <NomeDaAba>_2025-11-01_08-00-20-00.json
    ├── <NomeDaAba>_2025-11-01_20-00-08-00.json
    └── ...
```

- O **nome do arquivo** inclui a **aba** e o **intervalo**.
- Cada JSON contém um **array de registros** com as colunas originais (ex.: `data` em `YYYY-MM-DD` e `hora` em `HH:MM:SS`).

---
