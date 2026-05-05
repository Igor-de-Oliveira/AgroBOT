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
VALID_PROCESSING_STATUSES = {"em_processamento", "processado", "erro"}


def get_connection() -> Connection:
    return Connection.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def _serialize_portal_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "credential": row["credential"],
        "is_active": row["is_active"],
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at": row["updated_at"].isoformat() if row.get("updated_at") else None,
        "last_login_at": row["last_login_at"].isoformat() if row.get("last_login_at") else None,
    }


def ensure_file_metadata_table(base_dir: str) -> None:
    migrations_dir = Path(base_dir).resolve().parents[1] / "migrations"
    migration_files = sorted(migrations_dir.glob("*.sql"))
    with get_connection() as conn:
        with conn.cursor() as cur:
            for migration_file in migration_files:
                ddl = migration_file.read_text(encoding="utf-8")
                cur.execute(ddl)
        conn.commit()


def count_portal_users() -> int:
    query = "SELECT COUNT(*) AS total FROM portal_users;"
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query)
            row = cur.fetchone() or {"total": 0}
    return int(row["total"])


def fetch_portal_user_by_username(
    username: str, *, include_password_hash: bool = False
) -> Optional[dict[str, Any]]:
    select_fields = """
    id, username, credential, is_active, created_at, updated_at, last_login_at
    """
    if include_password_hash:
        select_fields = f"{select_fields}, password_hash"

    query = f"""
    SELECT {select_fields}
    FROM portal_users
    WHERE username = %s;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (username,))
            row = cur.fetchone()

    if not row:
        return None
    if include_password_hash:
        return dict(row)
    return _serialize_portal_user(row)


def list_portal_users() -> list[dict[str, Any]]:
    query = """
    SELECT id, username, credential, is_active, created_at, updated_at, last_login_at
    FROM portal_users
    ORDER BY created_at DESC, id DESC;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query)
            rows = cur.fetchall()
    return [_serialize_portal_user(row) for row in rows]


def fetch_portal_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    query = """
    SELECT id, username, credential, is_active, created_at, updated_at, last_login_at
    FROM portal_users
    WHERE id = %s;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()
    if not row:
        return None
    return _serialize_portal_user(row)


def create_portal_user(
    *,
    username: str,
    credential: str,
    password_hash: str,
    is_active: bool = True,
) -> dict[str, Any]:
    query = """
    INSERT INTO portal_users (username, credential, password_hash, is_active)
    VALUES (%s, %s, %s, %s)
    RETURNING id, username, credential, is_active, created_at, updated_at, last_login_at;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (username, credential, password_hash, is_active))
            row = cur.fetchone()
        conn.commit()
    return _serialize_portal_user(row)


def update_portal_user(
    *,
    user_id: int,
    username: str,
    credential: str,
    is_active: bool,
    password_hash: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    query = """
    UPDATE portal_users
    SET
        username = %s,
        credential = %s,
        is_active = %s,
        password_hash = COALESCE(%s, password_hash),
        updated_at = NOW()
    WHERE id = %s
    RETURNING id, username, credential, is_active, created_at, updated_at, last_login_at;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (username, credential, is_active, password_hash, user_id))
            row = cur.fetchone()
        conn.commit()
    if not row:
        return None
    return _serialize_portal_user(row)


def deactivate_portal_user(user_id: int) -> Optional[dict[str, Any]]:
    query = """
    UPDATE portal_users
    SET is_active = FALSE, updated_at = NOW()
    WHERE id = %s
    RETURNING id, username, credential, is_active, created_at, updated_at, last_login_at;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(query, (user_id,))
            row = cur.fetchone()
        conn.commit()
    if not row:
        return None
    return _serialize_portal_user(row)


def delete_portal_user_by_id(user_id: int) -> bool:
    query = "DELETE FROM portal_users WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted


def touch_portal_user_last_login(user_id: int) -> None:
    query = """
    UPDATE portal_users
    SET last_login_at = NOW(), updated_at = NOW()
    WHERE id = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (user_id,))
        conn.commit()


def fetch_file_metadata(file_name: str) -> Optional[dict[str, Any]]:
    query = """
    SELECT id, file_name, file_hash, link_arquivo_AWS, link_json_aws, status_processamento, created_at, updated_at
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
    status_processamento: Optional[str] = None,
) -> None:
    if status_processamento is not None and status_processamento not in VALID_PROCESSING_STATUSES:
        raise ValueError(
            "status_processamento invalido. Valores aceitos: em_processamento, processado, erro."
        )

    query = """
    INSERT INTO file_metadata (file_name, file_hash, link_arquivo_AWS, link_json_aws, status_processamento)
    VALUES (%s, %s, %s, %s, COALESCE(%s, 'processado'))
    ON CONFLICT (file_name) DO UPDATE
    SET
        file_hash = EXCLUDED.file_hash,
        link_arquivo_AWS = COALESCE(EXCLUDED.link_arquivo_AWS, file_metadata.link_arquivo_AWS),
        link_json_aws = COALESCE(EXCLUDED.link_json_aws, file_metadata.link_json_aws),
        status_processamento = COALESCE(%s, file_metadata.status_processamento),
        updated_at = CASE
            WHEN file_metadata.file_hash IS DISTINCT FROM EXCLUDED.file_hash THEN NOW()
            WHEN file_metadata.link_arquivo_AWS IS DISTINCT FROM COALESCE(EXCLUDED.link_arquivo_AWS, file_metadata.link_arquivo_AWS) THEN NOW()
            WHEN file_metadata.link_json_aws IS DISTINCT FROM COALESCE(EXCLUDED.link_json_aws, file_metadata.link_json_aws) THEN NOW()
            WHEN file_metadata.status_processamento IS DISTINCT FROM COALESCE(%s, file_metadata.status_processamento) THEN NOW()
            ELSE file_metadata.updated_at
        END;
    """
    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                query,
                (
                    file_name,
                    file_hash,
                    link_arquivo_aws,
                    link_json_aws,
                    status_processamento,
                    status_processamento,
                    status_processamento,
                ),
            )
        conn.commit()


def update_file_processing_status(file_id: int, status_processamento: str) -> None:
    if status_processamento not in VALID_PROCESSING_STATUSES:
        raise ValueError(
            "status_processamento invalido. Valores aceitos: em_processamento, processado, erro."
        )

    query = """
    UPDATE file_metadata
    SET status_processamento = %s, updated_at = NOW()
    WHERE id = %s;
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (status_processamento, file_id))
        conn.commit()


def list_file_metadata(page: int, page_size: int) -> tuple[list[dict[str, Any]], int]:
    offset = (page - 1) * page_size
    list_query = """
    SELECT id, file_name, file_hash, created_at, link_arquivo_AWS, link_json_aws, status_processamento
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
            "status_processamento": row["status_processamento"],
        }
        for row in rows
    ]

    return items, int(total_row["total"])


def fetch_file_metadata_by_id(file_id: int) -> Optional[dict[str, Any]]:
    query = """
    SELECT id, file_name, file_hash, link_arquivo_AWS, link_json_aws, status_processamento, created_at
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
        "status_processamento": row["status_processamento"],
    }


def delete_file_metadata_by_id(file_id: int) -> bool:
    query = "DELETE FROM file_metadata WHERE id = %s;"
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, (file_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return deleted
