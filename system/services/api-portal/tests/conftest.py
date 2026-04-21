import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from psycopg.rows import dict_row


class FakeHttpResponse:
    def __init__(self, payload=None):
        self._payload = payload or {
            "message": "ok",
            "artifacts": [{"artifact_name": "dados.json", "records": [{"a": 1}]}],
            "artifacts_count": 1,
        }
        self.status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class FakeS3Store:
    def __init__(self):
        self.objects = {}


def load_portal_module():
    src_dir = Path(__file__).resolve().parents[1] / "src" / "api-portal"
    module_path = src_dir / "main.py"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    spec = importlib.util.spec_from_file_location("api_portal_main", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def upload_file(client: TestClient, filename: str, payload: bytes):
    return client.post(
        "/process_ods",
        files={"file": (filename, payload, "application/octet-stream")},
    )


def fetch_metadata(module, file_name: str):
    with module.get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, file_name, file_hash, link_arquivo_AWS, link_json_aws, status_processamento, created_at, updated_at
                FROM file_metadata
                WHERE file_name = %s
                """,
                (file_name,),
            )
            return cur.fetchone()


def truncate_table(module):
    with module.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE file_metadata RESTART IDENTITY;")
        conn.commit()


def truncate_portal_users(module):
    with module.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE portal_users RESTART IDENTITY;")
        conn.commit()


def seed_admin_user(module, username: str = "admin", password: str = "admin123"):
    module.create_portal_user(
        username=username,
        credential="admin",
        password_hash=module.hash_password(password),
        is_active=True,
    )


def ensure_database_available(module):
    try:
        with module.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
    except Exception as exc:
        pytest.skip(f"PostgreSQL indisponivel para teste de integracao: {exc}")


def install_fakes(module, monkeypatch, s3_store):
    def fake_post(url, *args, **kwargs):
        if url == module.API_EXTRACTOR_URL:
            return FakeHttpResponse()
        if url == module.API_LLM_INGEST_URL:
            return FakeHttpResponse({"message": "ingestao concluida", "status": "success"})
        return FakeHttpResponse({"message": "ok"})

    monkeypatch.setattr(module.requests, "post", fake_post)
    monkeypatch.setattr(module, "build_s3_client", lambda: object())
    monkeypatch.setattr(module, "ensure_bucket_exists", lambda *args, **kwargs: None)

    def fake_exists(_s3_client, bucket_name, object_key):
        return (bucket_name, object_key) in s3_store.objects

    def fake_upload(s3_client, bucket_name, object_key, body, content_type):
        s3_store.objects[(bucket_name, object_key)] = body
        endpoint = module.get_s3_settings()["public_endpoint"].rstrip("/")
        return f"{endpoint}/{bucket_name}/{object_key}"

    monkeypatch.setattr(module, "object_exists_in_s3", fake_exists)
    monkeypatch.setattr(module, "upload_bytes_to_s3", fake_upload)


@pytest.fixture
def portal_module(monkeypatch):
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_DB", "agrobot")
    monkeypatch.setenv("POSTGRES_USER", "agrobot")
    monkeypatch.setenv("POSTGRES_PASSWORD", "agrobot")

    monkeypatch.setenv("S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setenv("S3_ACCESS_KEY", "key")
    monkeypatch.setenv("S3_SECRET_KEY", "secret")
    monkeypatch.setenv("S3_ENDPOINT", "http://localhost:9000")

    module = load_portal_module()
    ensure_database_available(module)

    return module


@pytest.fixture
def fake_s3_store():
    return FakeS3Store()


@pytest.fixture
def client(portal_module):
    with TestClient(portal_module.app) as test_client:
        login_response = test_client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        assert login_response.status_code == 200
        yield test_client


@pytest.fixture
def anonymous_client(portal_module):
    with TestClient(portal_module.app) as test_client:
        yield test_client
