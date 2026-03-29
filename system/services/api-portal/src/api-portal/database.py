import os
from pathlib import Path
from typing import Any, Optional

from psycopg import Connection
from psycopg.rows import dict_row

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres-arquivos")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "agrobot")
POSTGRES_USER = os.getenv("POSTGRES_USER", "agrobot")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "agrobot")


def get_connection() -> Connection:
    return Connection.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def ensure_file_metadata_table(base_dir: str) -> None:
    migrations_dir = Path(base_dir).resolve().parents[1] / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    with get_connection() as conn:
        with conn.cursor() as cur:
            for migration_file in migration_files:
                ddl = migration_file.read_text(encoding="utf-8")
                cur.execute(ddl)
        conn.commit()


def fetch_file_metadata(file_name: str) -> Optional[dict[str, Any]]:
    query = """
    SELECT id, file_name, file_hash, link_arquivo_AWS, link_json_aws, created_at, updated_at
    FROM file_metadata
    WHERE file_name = %s;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (file_name,))
            return cur.fetchone()


def upsert_file_metadata(
    file_name: str,
    file_hash: str,
    link_arquivo_aws: Optional[str] = None,
    link_json_aws: Optional[str] = None,
) -> None:
    query = """
    INSERT INTO file_metadata (file_name, file_hash, link_arquivo_AWS, link_json_aws)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (file_name) DO UPDATE
    SET
        file_hash = EXCLUDED.file_hash,
        link_arquivo_AWS = COALESCE(EXCLUDED.link_arquivo_AWS, file_metadata.link_arquivo_AWS),
        link_json_aws = COALESCE(EXCLUDED.link_json_aws, file_metadata.link_json_aws),
        updated_at = CASE
            WHEN file_metadata.file_hash IS DISTINCT FROM EXCLUDED.file_hash THEN NOW()
            WHEN file_metadata.link_arquivo_AWS IS DISTINCT FROM COALESCE(EXCLUDED.link_arquivo_AWS, file_metadata.link_arquivo_AWS) THEN NOW()
            WHEN file_metadata.link_json_aws IS DISTINCT FROM COALESCE(EXCLUDED.link_json_aws, file_metadata.link_json_aws) THEN NOW()
            ELSE file_metadata.updated_at
        END;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (file_name, file_hash, link_arquivo_aws, link_json_aws))
        conn.commit()
