import requests
from uuid import uuid4

from .conftest import fetch_metadata, install_fakes, truncate_table, upload_file


class FakeResponse:
    def __init__(self, payload=None):
        self._payload = payload or {"message": "ok"}
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_fluxo_feliz_upload_extracao_persistencia_e_ingestao_llm(
    portal_module, fake_s3_store, monkeypatch, client
):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    filename = f"integration-{uuid4().hex}.ods"
    response = upload_file(client, filename, b"conteudo-feliz")

    assert response.status_code == 200
    body = response.json()
    assert body["embeddings_ingestion"]["status"] == "queued"
    assert body["embeddings_ingestion"]["endpoint"] == portal_module.API_LLM_INGEST_URL

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["link_json_aws"].startswith("http://localhost:9000/test-bucket/Json/")
    assert row["status_processamento"] == "processado"


def test_upload_retorna_em_processamento_apos_agendamento(
    portal_module, fake_s3_store, monkeypatch, client
):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    monkeypatch.setattr(
        portal_module,
        "schedule_ingestion_task",
        lambda background_tasks, ingestion_payload: None,
    )

    filename = f"integration-{uuid4().hex}.ods"
    response = upload_file(client, filename, b"conteudo-em-processamento")

    assert response.status_code == 200
    assert response.json()["embeddings_ingestion"]["status"] == "queued"

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["status_processamento"] == "em_processamento"


def test_falha_ingestao_llm_atualiza_status_para_erro_sem_remover_json(
    portal_module, fake_s3_store, monkeypatch, client
):
    truncate_table(portal_module)

    def fake_post(url, *args, **kwargs):
        if url == portal_module.API_EXTRACTOR_URL:
            return FakeResponse(
                {
                    "message": "ok",
                    "artifacts": [{"artifact_name": "dados.json", "records": [{"a": 1}]}],
                    "artifacts_count": 1,
                }
            )
        if url == portal_module.API_LLM_INGEST_URL:
            raise requests.RequestException("api-llm indisponivel")
        return FakeResponse()

    monkeypatch.setattr(portal_module.requests, "post", fake_post)
    monkeypatch.setattr(portal_module, "build_s3_client", lambda: object())
    monkeypatch.setattr(portal_module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_exists(_s3_client, bucket_name, object_key):
        return (bucket_name, object_key) in fake_s3_store.objects

    def fake_upload(s3_client, bucket_name, object_key, body, content_type):
        fake_s3_store.objects[(bucket_name, object_key)] = body
        endpoint = portal_module.get_s3_settings()["public_endpoint"].rstrip("/")
        return f"{endpoint}/{bucket_name}/{object_key}"

    monkeypatch.setattr(portal_module, "object_exists_in_s3", fake_exists)
    monkeypatch.setattr(portal_module, "upload_bytes_to_s3", fake_upload)

    filename = f"integration-{uuid4().hex}.ods"
    response = upload_file(client, filename, b"conteudo-falha-llm")

    assert response.status_code == 200

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["link_json_aws"] is not None
    assert row["status_processamento"] == "erro"
    assert any(object_key.startswith("Json/") for (_, object_key) in fake_s3_store.objects.keys())


def test_reprocessamento_do_mesmo_arquivo_dispara_reingestao(
    portal_module, fake_s3_store, monkeypatch, client
):
    truncate_table(portal_module)
    llm_calls = []

    def fake_post(url, *args, **kwargs):
        if url == portal_module.API_EXTRACTOR_URL:
            return FakeResponse(
                {
                    "message": "ok",
                    "artifacts": [{"artifact_name": "dados.json", "records": [{"a": 1}]}],
                    "artifacts_count": 1,
                }
            )
        if url == portal_module.API_LLM_INGEST_URL:
            llm_calls.append(kwargs.get("json", {}))
            return FakeResponse({"status": "success"})
        return FakeResponse()

    monkeypatch.setattr(portal_module.requests, "post", fake_post)
    monkeypatch.setattr(portal_module, "build_s3_client", lambda: object())
    monkeypatch.setattr(portal_module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_exists(_s3_client, bucket_name, object_key):
        return (bucket_name, object_key) in fake_s3_store.objects

    def fake_upload(s3_client, bucket_name, object_key, body, content_type):
        fake_s3_store.objects[(bucket_name, object_key)] = body
        endpoint = portal_module.get_s3_settings()["public_endpoint"].rstrip("/")
        return f"{endpoint}/{bucket_name}/{object_key}"

    monkeypatch.setattr(portal_module, "object_exists_in_s3", fake_exists)
    monkeypatch.setattr(portal_module, "upload_bytes_to_s3", fake_upload)

    filename = f"integration-{uuid4().hex}.ods"
    first = upload_file(client, filename, b"conteudo-v1")
    second = upload_file(client, filename, b"conteudo-v2")

    assert first.status_code == 200
    assert second.status_code == 200
    assert len(llm_calls) == 2
    assert llm_calls[0]["logical_file_key"] == llm_calls[1]["logical_file_key"]
    assert llm_calls[0]["file_hash"] != llm_calls[1]["file_hash"]

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["status_processamento"] == "processado"


def test_indisponibilidade_temporaria_permite_retentativa_posterior(
    portal_module, fake_s3_store, monkeypatch, client
):
    truncate_table(portal_module)
    llm_attempts = {"count": 0}

    def fake_post(url, *args, **kwargs):
        if url == portal_module.API_EXTRACTOR_URL:
            return FakeResponse(
                {
                    "message": "ok",
                    "artifacts": [{"artifact_name": "dados.json", "records": [{"a": 1}]}],
                    "artifacts_count": 1,
                }
            )
        if url == portal_module.API_LLM_INGEST_URL:
            llm_attempts["count"] += 1
            if llm_attempts["count"] == 1:
                raise requests.Timeout("timeout temporario")
            return FakeResponse({"status": "success"})
        return FakeResponse()

    monkeypatch.setattr(portal_module.requests, "post", fake_post)
    monkeypatch.setattr(portal_module, "build_s3_client", lambda: object())
    monkeypatch.setattr(portal_module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_exists(_s3_client, bucket_name, object_key):
        return (bucket_name, object_key) in fake_s3_store.objects

    def fake_upload(s3_client, bucket_name, object_key, body, content_type):
        fake_s3_store.objects[(bucket_name, object_key)] = body
        endpoint = portal_module.get_s3_settings()["public_endpoint"].rstrip("/")
        return f"{endpoint}/{bucket_name}/{object_key}"

    monkeypatch.setattr(portal_module, "object_exists_in_s3", fake_exists)
    monkeypatch.setattr(portal_module, "upload_bytes_to_s3", fake_upload)

    filename = f"integration-{uuid4().hex}.ods"
    first = upload_file(client, filename, b"conteudo-timeout-v1")
    assert first.status_code == 200

    first_row = fetch_metadata(portal_module, filename)
    assert first_row is not None
    assert first_row["status_processamento"] == "erro"

    second = upload_file(client, filename, b"conteudo-timeout-v2")
    assert second.status_code == 200
    assert llm_attempts["count"] == 2

    second_row = fetch_metadata(portal_module, filename)
    assert second_row is not None
    assert second_row["status_processamento"] == "processado"
