from uuid import uuid4

from .conftest import fetch_metadata, install_fakes, truncate_table, upload_file


def test_salvamento_e_overwrite_json_em_prefixo_json(portal_module, fake_s3_store, monkeypatch, client):
    install_fakes(portal_module, monkeypatch, fake_s3_store)
    truncate_table(portal_module)

    filename = f"integration-{uuid4().hex}.ods"

    first = upload_file(client, filename, b"conteudo-json-v1")
    assert first.status_code == 200
    assert first.json()["json_s3_operation"] == "create"

    second = upload_file(client, filename, b"conteudo-json-v2")
    assert second.status_code == 200
    assert second.json()["json_s3_operation"] == "overwrite"

    row = fetch_metadata(portal_module, filename)
    assert row is not None
    assert row["link_json_aws"].startswith("http://localhost:9000/test-bucket/Json/")
