from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, conlist
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
import os
import json
import uvicorn
from uuid import uuid4

app = FastAPI()

# ------------------- Config -------------------

class Config:
    load_dotenv()
    QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY = os.getenv("QDRANT_API_KEY") or None
    QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "records")
    VECTOR_DIM = int(os.getenv("VECTOR_DIM", "1536"))
    DISTANCE = os.getenv("DISTANCE", "cosine").lower()
    PORT = int(os.getenv("PORT", "8005"))

dist_map = {
    "cosine": Distance.COSINE,
    "euclid": Distance.EUCLID,
    "dot": Distance.DOT,
}
DISTANCE = dist_map.get(Config.DISTANCE, Distance.COSINE)

qdrant = QdrantClient(url=Config.QDRANT_URL, api_key=Config.QDRANT_API_KEY)

def ensure_collection():
    """Garante que a coleção exista com a dimensão e métrica definidas via .env."""
    try:
        info = qdrant.get_collection(Config.QDRANT_COLLECTION)
        # Checa dimensão configurada vs existente
        cur = qdrant.get_collection(Config.QDRANT_COLLECTION).config.params
        cur_dim = cur.vectors.size  # type: ignore
        cur_dist = cur.vectors.distance  # type: ignore
        if cur_dim != Config.VECTOR_DIM or cur_dist != DISTANCE:
            # recria para alinhar
            qdrant.recreate_collection(
                collection_name=Config.QDRANT_COLLECTION,
                vectors_config=VectorParams(size=Config.VECTOR_DIM, distance=DISTANCE),
            )
    except Exception:
        # não existe -> cria
        qdrant.recreate_collection(
            collection_name=Config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=Config.VECTOR_DIM, distance=DISTANCE),
        )

def filt_from_eq_dict(filters: Optional[Dict[str, Any]]) -> Optional[Filter]:
    if not filters:
        return None
    must = []
    for k, v in filters.items():
        # por padrão guardaremos seu objeto original em payload.record
        # então filtre por "record.<campo>"
        must.append(FieldCondition(key=f"record.{k}", match=MatchValue(value=v)))
    return Filter(must=must) if must else None

# ------------------- Schemas -------------------

class PointIn(BaseModel):
    id: Optional[str] = None
    vector: List[float]  # não validamos dimensão aqui p/ performance
    payload: Optional[Dict[str, Any]] = None

class UpsertPack(BaseModel):
    records: List[Dict[str, Any]]
    embeddings: List[List[float]]

class SearchByVector(BaseModel):
    vector: List[float]
    top_k: int = 5
    filters: Optional[Dict[str, Any]] = None

# ------------------- Endpoints -------------------

@app.get("/health")
def health():
    try:
        cols = qdrant.get_collections()
        return {"status": "ok", "qdrant": True, "collections": [c.name for c in cols.collections]}
    except Exception:
        return {"status": "ok", "qdrant": False}

@app.post("/recreate_collection")
def recreate_collection():
    """Força recreação com os parâmetros do .env."""
    try:
        qdrant.recreate_collection(
            collection_name=Config.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=Config.VECTOR_DIM, distance=DISTANCE),
        )
        return {"message": "Coleção recriada", "collection": Config.QDRANT_COLLECTION,
                "dim": Config.VECTOR_DIM, "distance": Config.DISTANCE}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao recriar coleção: {e}")

@app.post("/upsert_points")
def upsert_points(points: List[PointIn]):
    """
    Ingestão direta de pontos já com vetor:
    [
      {"id":"abc","vector":[...],"payload":{"record":{...},"source":"arquivoX.json"}},
      ...
    ]
    """
    ensure_collection()
    # valida dimensão de amostra (opcional, rápido)
    if points and len(points[0].vector) != Config.VECTOR_DIM:
        raise HTTPException(status_code=400, detail=f"Dimensão do vetor ({len(points[0].vector)}) difere de VECTOR_DIM={Config.VECTOR_DIM}")

    qpoints = []
    for p in points:
        qpoints.append(
            PointStruct(
                id=p.id or str(uuid4()),
                vector=list(p.vector),
                payload=p.payload or {}
            )
        )
    try:
        qdrant.upsert(Config.QDRANT_COLLECTION, qpoints)
        return {"inserted": len(qpoints), "collection": Config.QDRANT_COLLECTION}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inserir: {e}")

@app.post("/upload_pack")
def upload_pack(data: UpsertPack):
    """
    Ingestão com um JSON contendo:
    {
      "records": [ {...}, {...} ],
      "embeddings": [ [..], [..] ]
    }
    -> faz o zip record+embedding e envia p/ Qdrant (payload.record = record)
    """
    ensure_collection()
    # Validar se os registros e embeddings têm o mesmo comprimento
    if len(data.records) != len(data.embeddings):
        raise HTTPException(status_code=400, detail="records e embeddings precisam ter o mesmo comprimento")
    # Validar se a dimensão coincide com a configuração
    if data.embeddings and any(len(vec) != Config.VECTOR_DIM for vec in data.embeddings):
        raise HTTPException(status_code=400, detail=f"Dimensão dos vetores difere de VECTOR_DIM={Config.VECTOR_DIM}")
    
    points = []
    for rec, vec in zip(data.records, data.embeddings):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=vec,
                payload={"record": rec}
            )
        )
    try:
        qdrant.upsert(Config.QDRANT_COLLECTION, points)
        return {"inserted": len(points), "collection": Config.QDRANT_COLLECTION}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inserir: {e}")

@app.post("/upload_duplo")
async def upload_duplo(records_file: UploadFile = File(...), embeddings_file: UploadFile = File(...)):
    """
    Ingestão via 2 arquivos:
      - records_file: JSON com lista de objetos
      - embeddings_file: JSON com lista de vetores (mesmo tamanho)
    """
    ensure_collection()

    try:
        rec_bytes = await records_file.read()
        emb_bytes = await embeddings_file.read()
        records = json.loads(rec_bytes.decode("utf-8"))
        embeddings = json.loads(emb_bytes.decode("utf-8"))
        if not isinstance(records, list) or not isinstance(embeddings, list):
            raise ValueError("Arquivos devem ser listas JSON")
        if len(records) != len(embeddings):
            raise ValueError("Tamanhos de records e embeddings não batem")
        if embeddings and len(embeddings[0]) != Config.VECTOR_DIM:
            raise ValueError(f"Dimensão do vetor ({len(embeddings[0])}) difere de VECTOR_DIM={Config.VECTOR_DIM}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao ler arquivos: {e}")

    points = []
    for rec, vec in zip(records, embeddings):
        points.append(
            PointStruct(
                id=str(uuid4()),
                vector=list(vec),
                payload={"record": rec, "source": records_file.filename}
            )
        )
    try:
        qdrant.upsert(Config.QDRANT_COLLECTION, points)
        return {"inserted": len(points), "collection": Config.QDRANT_COLLECTION}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao inserir: {e}")

@app.post("/search_by_vector")
def search_by_vector(body: SearchByVector):
    """
    Busca semântica por vetor (você manda o embedding da query).
    body = {
      "vector": [...],
      "top_k": 5,
      "filters": {"status": "ativo"}  # aplica em payload.record.<campo>
    }
    """
    ensure_collection()
    if len(body.vector) != Config.VECTOR_DIM:
        raise HTTPException(status_code=400, detail=f"Dimensão do vetor ({len(body.vector)}) difere de VECTOR_DIM={Config.VECTOR_DIM}")
    q_filter = filt_from_eq_dict(body.filters)
    try:
        res = qdrant.search(
            collection_name=Config.QDRANT_COLLECTION,
            query_vector=list(body.vector),
            limit=body.top_k,
            query_filter=q_filter
        )
        hits = []
        for p in res:
            hits.append({
                "id": str(p.id),
                "score": p.score,
                "payload": p.payload
            })
        return {"count": len(hits), "results": hits, "collection": Config.QDRANT_COLLECTION}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar: {e}")

def main():
    uvicorn.run(app, host="0.0.0.0", port=Config.PORT)

if __name__ == "__main__":
    main()
