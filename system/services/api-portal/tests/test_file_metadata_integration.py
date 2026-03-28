import hashlib
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row


def _load_portal_module():
    module_path = Path(__file__).resolve().parents[1] / "src" / "api-portal" / "main.py"
    spec = importlib.util.spec_from_file_location("api_portal_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class _ExtractorResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"message": "ok"}


def _upload_file(client: TestClient, filename: str, payload: bytes):
    return client.post(
        "/process_ods",
        files={"file": (filename, payload, "application/octet-stream")},
    )


def _fetch_metadata(module, file_name: str):
    with module.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, file_name, file_hash, created_at, updated_at
                FROM file_metadata
                WHERE file_name = %s
                """,
                (file_name,),
            )
            return cur.fetchone()


def _truncate_table(module):
    with module.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE file_metadata RESTART IDENTITY;")
        conn.commit()


def _ensure_database_available(module):
    try:
        with module.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
    except Exception as exc:
        pytest.skip(f"PostgreSQL indisponivel para teste de integracao: {exc}")


def test_insert_new_file_metadata(monkeypatch):
    module = _load_portal_module()
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: _ExtractorResponse())
    _ensure_database_available(module)

    with TestClient(module.app) as client:
        _truncate_table(module)
        filename = f"integration-{uuid4().hex}.ods"
        payload = b"conteudo-inicial"
        expected_hash = hashlib.sha256(payload).hexdigest()

        response = _upload_file(client, filename, payload)
        assert response.status_code == 200

        row = _fetch_metadata(module, filename)
        assert row is not None
        assert row["file_name"] == filename
        assert row["file_hash"] == expected_hash
        assert row["created_at"] is not None
        assert row["updated_at"] is not None


def test_update_hash_when_file_content_changes(monkeypatch):
    module = _load_portal_module()
    monkeypatch.setattr(module.requests, "post", lambda *args, **kwargs: _ExtractorResponse())
    _ensure_database_available(module)

    with TestClient(module.app) as client:
        _truncate_table(module)
        filename = f"integration-{uuid4().hex}.ods"
        initial_payload = b"conteudo-v1"
        updated_payload = b"conteudo-v2"
        expected_updated_hash = hashlib.sha256(updated_payload).hexdigest()

        first_response = _upload_file(client, filename, initial_payload)
        assert first_response.status_code == 200
        before = _fetch_metadata(module, filename)
        assert before is not None

        second_response = _upload_file(client, filename, updated_payload)
        assert second_response.status_code == 200
        after = _fetch_metadata(module, filename)
        assert after is not None

        assert after["id"] == before["id"]
        assert after["created_at"] == before["created_at"]
        assert after["file_hash"] == expected_updated_hash
        assert after["updated_at"] >= before["updated_at"]
