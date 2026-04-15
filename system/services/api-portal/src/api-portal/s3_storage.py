import os
from typing import Any
from urllib.parse import quote, unquote, urlparse


def get_s3_settings() -> dict[str, str]:
    settings = {
        "endpoint": os.getenv("S3_ENDPOINT", "http://minio:9000").strip(),
        "public_endpoint": os.getenv("S3_PUBLIC_ENDPOINT", "").strip(),
        "region": os.getenv("S3_REGION", "us-east-1").strip(),
        "access_key": os.getenv("S3_ACCESS_KEY", "").strip(),
        "secret_key": os.getenv("S3_SECRET_KEY", "").strip(),
        "bucket_name": os.getenv("S3_BUCKET_NAME", "").strip(),
    }
    if not settings["public_endpoint"]:
        settings["public_endpoint"] = settings["endpoint"]
    missing = [key for key, value in settings.items() if not value]
    if missing:
        raise RuntimeError(f"Configuracao S3 incompleta: {', '.join(missing)}")
    return settings


def build_s3_client() -> Any:
    import boto3

    settings = get_s3_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings["endpoint"],
        region_name=settings["region"],
        aws_access_key_id=settings["access_key"],
        aws_secret_access_key=settings["secret_key"],
    )


def ensure_bucket_exists(s3_client: Any, bucket_name: str) -> None:
    from botocore.exceptions import ClientError

    try:
        s3_client.head_bucket(Bucket=bucket_name)
    except ClientError:
        s3_client.create_bucket(Bucket=bucket_name)


def object_exists_in_s3(s3_client: Any, bucket_name: str, object_key: str) -> bool:
    from botocore.exceptions import ClientError

    try:
        s3_client.head_object(Bucket=bucket_name, Key=object_key)
        return True
    except ClientError as exc:
        error_code = str(exc.response.get("Error", {}).get("Code", ""))
        if error_code in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def upload_bytes_to_s3(
    s3_client: Any,
    bucket_name: str,
    object_key: str,
    body: bytes,
    content_type: str,
) -> str:
    s3_client.put_object(Bucket=bucket_name, Key=object_key, Body=body, ContentType=content_type)
    endpoint = get_s3_settings()["public_endpoint"].rstrip("/")
    return f"{endpoint}/{bucket_name}/{quote(object_key, safe='/')}"


def extract_s3_key_from_link(link: str, bucket_name: str) -> str:
    parsed = urlparse(link)
    raw_path = (parsed.path or "").lstrip("/")
    prefix = f"{bucket_name}/"
    if not raw_path.startswith(prefix):
        raise ValueError("Link AWS invalido para o bucket configurado.")
    object_key = unquote(raw_path[len(prefix) :])
    if not object_key:
        raise ValueError("Link AWS sem chave de objeto.")
    return object_key


def delete_object_from_s3(s3_client: Any, bucket_name: str, object_key: str) -> None:
    s3_client.delete_object(Bucket=bucket_name, Key=object_key)
