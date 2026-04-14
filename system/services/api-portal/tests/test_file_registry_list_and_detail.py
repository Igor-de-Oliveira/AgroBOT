from uuid import uuid4

from psycopg.rows import dict_row

from .conftest import truncate_table


def insert_metadata(portal_module, file_name: str, file_hash: str = "hash"):
    portal_module.upsert_file_metadata(
        file_name=file_name,
        file_hash=file_hash,
        link_arquivo_aws=f"http://localhost:9000/test-bucket/Arquivos/{file_name}",
        link_json_aws=f"http://localhost:9000/test-bucket/Json/{file_name}.json",
        status_processamento="processado",
    )


def get_all_rows(portal_module):
    with portal_module.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT id, file_name FROM file_metadata ORDER BY id;")
            return cur.fetchall()


def test_lista_vazia_retorna_total_zero(portal_module, client):
    truncate_table(portal_module)

    response = client.get("/api/files?page=1&page_size=25")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 0
    assert payload["items"] == []


def test_lista_paginada_suporta_multiplas_paginas(portal_module, client):
    truncate_table(portal_module)

    for index in range(30):
        file_name = f"lista-{uuid4().hex}-{index}.ods"
        insert_metadata(portal_module, file_name=file_name, file_hash=f"hash-{index}")

    first_page = client.get("/api/files?page=1&page_size=25")
    assert first_page.status_code == 200
    first_payload = first_page.json()
    assert first_payload["total"] == 30
    assert len(first_payload["items"]) == 25
    assert first_payload["page"] == 1
    assert all(item["status_processamento"] == "processado" for item in first_payload["items"])

    second_page = client.get("/api/files?page=2&page_size=25")
    assert second_page.status_code == 200
    second_payload = second_page.json()
    assert second_payload["total"] == 30
    assert len(second_payload["items"]) == 5
    assert second_payload["page"] == 2


def test_listagem_rejeita_page_size_invalido(portal_module, client):
    truncate_table(portal_module)

    response = client.get("/api/files?page=1&page_size=10")
    assert response.status_code == 400
    assert "page_size" in response.json()["detail"]


def test_troca_page_size_25_50_100(portal_module, client):
    truncate_table(portal_module)

    for index in range(105):
        file_name = f"troca-size-{uuid4().hex}-{index}.ods"
        insert_metadata(portal_module, file_name=file_name, file_hash=f"hash-size-{index}")

    resp_25 = client.get("/api/files?page=1&page_size=25")
    resp_50 = client.get("/api/files?page=1&page_size=50")
    resp_100 = client.get("/api/files?page=1&page_size=100")

    assert resp_25.status_code == 200
    assert resp_50.status_code == 200
    assert resp_100.status_code == 200

    assert len(resp_25.json()["items"]) == 25
    assert len(resp_50.json()["items"]) == 50
    assert len(resp_100.json()["items"]) == 100


def test_recarregar_consulta_dados_mais_recentes(portal_module, client):
    truncate_table(portal_module)

    first_response = client.get("/api/files?page=1&page_size=25")
    assert first_response.status_code == 200
    assert first_response.json()["total"] == 0

    insert_metadata(portal_module, file_name=f"reload-{uuid4().hex}.ods", file_hash="hash-reload")

    second_response = client.get("/api/files?page=1&page_size=25")
    assert second_response.status_code == 200
    assert second_response.json()["total"] == 1


def test_detalhe_retorna_campos_esperados(portal_module, client):
    truncate_table(portal_module)
    file_name = f"detalhe-{uuid4().hex}.ods"
    insert_metadata(portal_module, file_name=file_name, file_hash="hash-detalhe")
    row = get_all_rows(portal_module)[0]

    response = client.get(f"/api/files/{row['id']}")
    assert response.status_code == 200

    payload = response.json()
    assert payload["id"] == row["id"]
    assert payload["name"] == file_name
    assert payload["hash"] == "hash-detalhe"
    assert payload["created_at"]
    assert payload["link_arquivo_AWS"].startswith("http://localhost:9000/test-bucket/Arquivos/")
    assert payload["link_json_aws"].startswith("http://localhost:9000/test-bucket/Json/")
    assert payload["status_processamento"] == "processado"


def test_exclusao_remove_s3_e_metadado(portal_module, monkeypatch, client):
    truncate_table(portal_module)
    file_name = f"delete-{uuid4().hex}.ods"
    insert_metadata(portal_module, file_name=file_name, file_hash="hash-delete")
    row = get_all_rows(portal_module)[0]
    deleted_keys = []

    monkeypatch.setattr(portal_module, "get_s3_settings", lambda: {"bucket_name": "test-bucket"})
    monkeypatch.setattr(portal_module, "build_s3_client", lambda: object())
    monkeypatch.setattr(portal_module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_delete(_client, _bucket_name, object_key):
        deleted_keys.append(object_key)

    monkeypatch.setattr(portal_module, "delete_object_from_s3", fake_delete)

    response = client.delete(f"/api/files/{row['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == row["id"]

    assert any(key.startswith("Arquivos/") for key in deleted_keys)
    assert any(key.startswith("Json/") for key in deleted_keys)
    assert portal_module.fetch_file_metadata_by_id(row["id"]) is None


def test_exclusao_com_falha_parcial_nao_retorna_sucesso(portal_module, monkeypatch, client):
    truncate_table(portal_module)
    file_name = f"delete-failure-{uuid4().hex}.ods"
    insert_metadata(portal_module, file_name=file_name, file_hash="hash-delete-failure")
    row = get_all_rows(portal_module)[0]
    deleted_keys = []

    monkeypatch.setattr(portal_module, "get_s3_settings", lambda: {"bucket_name": "test-bucket"})
    monkeypatch.setattr(portal_module, "build_s3_client", lambda: object())
    monkeypatch.setattr(portal_module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_delete(_client, _bucket_name, object_key):
        deleted_keys.append(object_key)
        if object_key.startswith("Json/"):
            raise RuntimeError("falha simulada")

    monkeypatch.setattr(portal_module, "delete_object_from_s3", fake_delete)

    response = client.delete(f"/api/files/{row['id']}")
    assert response.status_code == 500
    assert "Falha ao excluir objetos no S3" in response.json()["detail"]
    assert portal_module.fetch_file_metadata_by_id(row["id"]) is not None
    assert any(key.startswith("Arquivos/") for key in deleted_keys)
