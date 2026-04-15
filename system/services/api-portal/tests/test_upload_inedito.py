import hashlib
from uuid import uuid4

from .conftest import fetch_metadata, install_fakes, truncate_table, upload_file


def test_upload_inedito_persiste_link_s3(portal_module, fake_s3_store, monkeypatch, client):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    filename = f"integration-{uuid4().hex}.ods"
    payload = b"conteudo-inicial"
    expected_hash = hashlib.sha256(payload).hexdigest()

    response = upload_file(client, filename, payload)
    assert response.status_code == 200

    body = response.json()
    assert body["source_file_s3_operation"] == "create"
    assert body["json_s3_operation"] == "create"

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["file_name"] == filename
    assert row["file_hash"] == expected_hash
    assert row["link_arquivo_aws"].startswith("http://localhost:9000/test-bucket/Arquivos/")
    assert row["link_json_aws"].startswith("http://localhost:9000/test-bucket/Json/")
    assert row["status_processamento"] == "processado"
