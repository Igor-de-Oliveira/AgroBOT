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


def list_file_metadata(page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    offset = (page - 1) * page_size
    list_query = """
    SELECT id, file_name, file_hash, created_at, link_arquivo_AWS, link_json_aws
    FROM file_metadata
    ORDER BY created_at DESC, id DESC
    LIMIT %s OFFSET %s;
    """
    total_query = "SELECT COUNT(*) AS total FROM file_metadata;"

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(total_query)
            total_row = cur.fetchone() or {"total": 0}
            cur.execute(list_query, (page_size, offset))
            rows = cur.fetchall()

    items = [
        {
            "id": row["id"],
            "name": row["file_name"],
            "hash": row["file_hash"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "link_arquivo_AWS": row["link_arquivo_aws"],
            "link_json_aws": row["link_json_aws"],
        }
        for row in rows
    ]

    return items, int(total_row["total"])


def fetch_file_metadata_by_id(file_id: int) -> Optional[dict[str, Any]]:
    query = """
    SELECT id, file_name, file_hash, link_arquivo_AWS, link_json_aws, created_at
    FROM file_metadata
    WHERE id = %s;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (file_id,))
            row = cur.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "name": row["file_name"],
        "hash": row["file_hash"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "link_arquivo_AWS": row["link_arquivo_aws"],
        "link_json_aws": row["link_json_aws"],
    }


def delete_file_metadata_by_id(file_id: int) -> bool:
    query = "DELETE FROM file_metadata WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (file_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted
