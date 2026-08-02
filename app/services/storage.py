"""S3 / MinIO storage helpers."""

import io
import uuid
from typing import BinaryIO, Optional

import boto3
from botocore.client import Config

from app.config import get_settings

settings = get_settings()


def get_s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except Exception:
        try:
            client.create_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            pass  # may already exist or minio not ready


def upload_bytes(
    data: bytes,
    filename: str,
    content_type: str = "application/octet-stream",
    folder: str = "assets",
) -> str:
    key = f"{folder}/{uuid.uuid4().hex}_{filename}"
    client = get_s3_client()
    try:
        ensure_bucket()
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{key}"
    except Exception:
        # Fallback: save locally when MinIO unavailable
        from pathlib import Path

        local_dir = Path("/tmp/gamedev-assets") / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        path = local_dir / f"{uuid.uuid4().hex}_{filename}"
        path.write_bytes(data)
        return f"/local-assets/{folder}/{path.name}"


def upload_fileobj(
    fileobj: BinaryIO,
    filename: str,
    content_type: str = "application/octet-stream",
    folder: str = "assets",
) -> str:
    data = fileobj.read()
    return upload_bytes(data, filename, content_type, folder)


def download_bytes(url_or_key: str) -> Optional[bytes]:
    if url_or_key.startswith("/local-assets/"):
        from pathlib import Path

        path = Path("/tmp/gamedev-assets") / url_or_key.replace("/local-assets/", "")
        if path.exists():
            return path.read_bytes()
        return None
    # Treat as S3 key or full URL under public prefix
    key = url_or_key
    if settings.S3_PUBLIC_URL in url_or_key:
        key = url_or_key.split(settings.S3_PUBLIC_URL.rstrip("/") + "/", 1)[-1]
    try:
        client = get_s3_client()
        buf = io.BytesIO()
        client.download_fileobj(settings.S3_BUCKET, key, buf)
        return buf.getvalue()
    except Exception:
        return None
