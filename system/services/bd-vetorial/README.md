# Qdrant Vector API — FastAPI Service

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Web-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![Qdrant](https://img.shields.io/badge/VectorDB-Qdrant-FC4C02.svg)](https://qdrant.tech/)


> Microserviço para **ingestão** e **busca semântica** em um índice do **Qdrant**, com endpoints REST para recriar coleção, inserir pontos e pesquisar por vetor. Carrega parâmetros via `.env` e inicia com **Uvicorn**.

---

## Sumário
- [Visão Geral](#-visão-geral)
- [Arquitetura](#-arquitetura)
- [Endpoints](#-endpoints)
- [Modelos (Schemas)](#-modelos-schemas)
- [Variáveis de Ambiente](#-variáveis-de-ambiente)
- [Instalação](#-instalação)
- [Execução](#-execução)
- [Exemplos de Uso (cURL)](#-exemplos-de-uso-curl)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Solução de Problemas](#-solução-de-problemas)
- [Licença](#-licença)

---

## Visão Geral

O serviço expõe uma API HTTP para gerenciar uma **coleção do Qdrant** e realizar **busca por similaridade** usando embeddings (vetores). Principais capacidades:

- **Healthcheck** do Qdrant e listagem de coleções.
- **(Re)criação** de coleção com dimensão e métrica definidas por `.env`.
- **Upsert** de pontos (id, vetor e payload livre).
- **Ingestão em lote** combinando `records` + `embeddings`.
- **Busca por vetor** com `top_k` e **filtros por payload** (campos dentro de `payload.record`).

---


## Endpoints

### `GET /health`
Retorna status do serviço e se o Qdrant está acessível, além das coleções existentes.

**Resposta (200)**
```json
{
  "status": "ok",
  "qdrant": true,
  "collections": ["records", "..."]
}
```

---

### `POST /recreate_collection`
Força a **recriação** da coleção com parâmetros do `.env` (`VECTOR_DIM`, `DISTANCE`).

**Resposta (200)**
```json
{
  "message": "Coleção recriada",
  "collection": "records",
  "dim": 1536,
  "distance": "cosine"
}
```

---

### `POST /upsert_points`
Ingestão direta de **pontos** com vetor já pronto.

**Body (JSON)**
```json
[
  {
    "id": "abc-123",
    "vector": [0.12, 0.05, ...],
    "payload": {
      "record": { "titulo": "Doc A", "status": "ativo" },
      "source": "arquivoX.json"
    }
  }
]
```

**Validações**
- `len(vector)` deve ser igual a `VECTOR_DIM`.
- `id` é opcional (se ausente, será gerado via `uuid4`).

**Resposta (200)**
```json
{ "inserted": 1, "collection": "records" }
```

---

### `POST /upload_pack`
Ingestão em **lote** com dois arrays: `records` e `embeddings` (mesma ordem e tamanho). Cada par vira um ponto com `payload.record = record`.

**Body (JSON)**
```json
{
  "records": [ { "id_externo": 1, "status": "ativo" }, { "id_externo": 2 } ],
  "embeddings": [ [0.1, 0.2, ...], [0.2, 0.3, ...] ]
}
```

**Validações**
- `len(records) == len(embeddings)`
- Cada embedding deve ter `VECTOR_DIM` dimensões.

**Resposta (200)**
```json
{ "inserted": 2, "collection": "records" }
```

---

### `POST /search_by_vector`
Busca **semântica** por vetor (o cliente fornece o embedding da consulta). É possível aplicar **filtros de igualdade** nos campos do `payload.record` (ex.: `{"status": "ativo"}`).

**Body (JSON)**
```json
{
  "vector": [0.11, 0.22, ...],
  "top_k": 5,
  "filters": { "status": "ativo" }
}
```

**Resposta (200)**
```json
{
  "count": 2,
  "results": [
    { "id": "uuid-1", "score": 0.88, "payload": { "record": { "status": "ativo" } } },
    { "id": "uuid-2", "score": 0.74, "payload": { "record": { "status": "ativo" } } }
  ],
  "collection": "records"
}
```

---

## Modelos (Schemas)

- **PointIn**
  - `id: Optional[str]`
  - `vector: List[float]` **(obrigatório)**
  - `payload: Optional[Dict[str, Any]]`

- **UpsertPack**
  - `records: List[Dict[str, Any]]`
  - `embeddings: List[List[float]]`

- **SearchByVector**
  - `vector: List[float]` **(obrigatório)**
  - `top_k: int = 5`
  - `filters: Optional[Dict[str, Any]]` *(aplica em `payload.record.<campo>`)*

---

## Variáveis de Ambiente

| Variável               | Obrigatória | Padrão                    | Descrição                                                                 |
|------------------------|-------------|---------------------------|---------------------------------------------------------------------------|
| `QDRANT_URL`           | Sim         | `http://localhost:6333`  | URL do servidor Qdrant.                                                   |
| `QDRANT_API_KEY`       | Não         | —                         | API Key do Qdrant (deixe vazio se o Qdrant não exigir).                   |
| `QDRANT_COLLECTION`    | Não         | `records`                 | Nome da coleção usada pelo serviço.                                       |
| `VECTOR_DIM`           | Não         | `1536`                    | Dimensão dos vetores.                                                     |
| `DISTANCE`             | Não         | `cosine`                  | Métrica de distância: `cosine`, `euclid`, `dot`.                          |
| `PORT`                 | Não         | `8005`                    | Porta onde o serviço FastAPI escuta.                                      |

Crie um arquivo `.env` na raiz:
```bash
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=
QDRANT_COLLECTION=records
VECTOR_DIM=1536
DISTANCE=cosine
PORT=8005
```

---


## Exemplos de Uso (cURL)

**Healthcheck**
```bash
curl -s http://localhost:8005/health | jq
```

**Recriar coleção**
```bash
curl -s -X POST http://localhost:8005/recreate_collection | jq
```

**Inserir pontos**
```bash
curl -s -X POST http://localhost:8005/upsert_points   -H "Content-Type: application/json"   -d '[{"vector":[0.1,0.2,0.3,...],"payload":{"record":{"status":"ativo"}}}]' | jq
```

**Upload pack (records + embeddings)**
```bash
curl -s -X POST http://localhost:8005/upload_pack   -H "Content-Type: application/json"   -d '{"records":[{"id_externo":1},{"id_externo":2}],"embeddings":[[0.1,0.2,...],[0.2,0.3,...]]}' | jq
```

**Busca por vetor com filtro**
```bash
curl -s -X POST http://localhost:8005/search_by_vector   -H "Content-Type: application/json"   -d '{"vector":[0.1,0.2,0.3,...],"top_k":5,"filters":{"status":"ativo"}}' | jq
```

> **Observação:** substitua `...` pelos valores reais para completar o vetor conforme sua `VECTOR_DIM`.

---