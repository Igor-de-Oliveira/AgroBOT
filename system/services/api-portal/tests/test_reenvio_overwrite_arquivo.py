import hashlib
from uuid import uuid4

from .conftest import fetch_metadata, install_fakes, truncate_table, upload_file


def test_reenvio_mesmo_arquivo_faz_overwrite_em_arquivos(portal_module, fake_s3_store, monkeypatch, client):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    filename = f"integration-{uuid4().hex}.ods"

    first = upload_file(client, filename, b"conteudo-v1")
    assert first.status_code == 200

    second_payload = b"conteudo-v2"
    second = upload_file(client, filename, second_payload)
    assert second.status_code == 200

    body = second.json()
    assert body["source_file_s3_operation"] == "overwrite"

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["file_hash"] == hashlib.sha256(second_payload).hexdigest()
