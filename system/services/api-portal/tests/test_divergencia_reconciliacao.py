import hashlib
import json
from uuid import uuid4

from .conftest import fetch_metadata, install_fakes, truncate_table, upload_file


def test_divergencia_banco_s3_recupera_objeto_ausente(portal_module, fake_s3_store, monkeypatch, client):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    filename = f"integration-{uuid4().hex}.ods"

    portal_module.upsert_file_metadata(
        file_name=filename,
        file_hash=hashlib.sha256(b"conteudo-antigo").hexdigest(),
        link_arquivo_aws="http://localhost:9000/test-bucket/Arquivos/ausente",
        link_json_aws="http://localhost:9000/test-bucket/Json/ausente",
    )

    response = upload_file(client, filename, b"conteudo-reconciliado")
    assert response.status_code == 200

    body = response.json()
    assert body["source_file_s3_operation"] == "recreated_missing_s3_object"
    assert body["json_s3_operation"] == "recreated_missing_s3_object"

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["link_arquivo_aws"] != "http://localhost:9000/test-bucket/Arquivos/ausente"
    assert row["link_json_aws"] != "http://localhost:9000/test-bucket/Json/ausente"

    parsed_json_link = row["link_json_aws"].replace("http://localhost:9000/test-bucket/", "")
    stored_json = fake_s3_store.objects[("test-bucket", parsed_json_link)]
    saved_payload = json.loads(stored_json.decode("utf-8"))
    assert saved_payload["message"] == "ok"
