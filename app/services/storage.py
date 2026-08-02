"""S3 / MinIO storage helpers with signed URL support."""

import io
import uuid
from pathlib import Path
from typing import BinaryIO, Optional
from urllib.parse import quote

import boto3
from botocore.client import Config

from app.config import get_settings
from app.core.security import hash_token

settings = get_settings()


def get_s3_client(*, public: bool = False):
    """Internal client for put/get; optional public endpoint for browser presigns."""
    endpoint = settings.S3_ENDPOINT
    if public and settings.S3_PUBLIC_ENDPOINT.strip():
        endpoint = settings.S3_PUBLIC_ENDPOINT.strip()
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket() -> None:
    client = get_s3_client()
    try:
        client.head_bucket(Bucket=settings.S3_BUCKET)
    except Exception:
        try:
            client.create_bucket(Bucket=settings.S3_BUCKET)
        except Exception:
            pass


def _presign(key: str) -> str:
    client = get_s3_client(public=True)
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=settings.S3_SIGNED_URL_EXPIRE_SEC,
    )


def _local_signed_url(folder: str, name: str) -> str:
    """HMAC-signed path for local asset fallback (no public listing)."""
    rel = f"{folder}/{name}"
    sig = hash_token(rel)[:32]
    return f"/local-assets/{quote(rel)}?sig={sig}"


def verify_local_asset_sig(rel_path: str, sig: str) -> bool:
    expected = hash_token(rel_path)[:32]
    return sig == expected


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
        if settings.S3_USE_SIGNED_URLS or not settings.S3_PUBLIC_READ:
            return _presign(key)
        return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{key}"
    except Exception:
        local_dir = Path("/tmp/gamedev-assets") / folder
        local_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}_{filename}"
        path = local_dir / name
        path.write_bytes(data)
        return _local_signed_url(folder, name)


def upload_fileobj(
    fileobj: BinaryIO,
    filename: str,
    content_type: str = "application/octet-stream",
    folder: str = "assets",
) -> str:
    data = fileobj.read()
    return upload_bytes(data, filename, content_type, folder)


def download_bytes(url_or_key: str) -> Optional[bytes]:
    if "/local-assets/" in url_or_key:

        path = url_or_key.split("/local-assets/", 1)[-1].split("?", 1)[0]
        local = Path("/tmp/gamedev-assets") / path
        if local.exists():
            return local.read_bytes()
        return None
    key = url_or_key
    public_base = settings.S3_PUBLIC_URL.rstrip("/")
    if public_base and public_base in url_or_key:
        key = url_or_key.split(public_base + "/", 1)[-1]
    if settings.S3_PUBLIC_ENDPOINT.strip():
        pub = settings.S3_PUBLIC_ENDPOINT.rstrip("/")
        if pub in key:
            # path-style: {public}/{bucket}/{key}
            rest = key.split(pub + "/", 1)[-1]
            prefix = f"{settings.S3_BUCKET}/"
            if rest.startswith(prefix):
                key = rest[len(prefix) :]
    if "?" in key:
        key = key.split("?", 1)[0]
    # Strip signed URL host path if present
    if "://" in key:
        # path after bucket
        parts = key.split(f"/{settings.S3_BUCKET}/", 1)
        if len(parts) == 2:
            key = parts[1].split("?", 1)[0]
    try:
        client = get_s3_client()
        buf = io.BytesIO()
        client.download_fileobj(settings.S3_BUCKET, key, buf)
        return buf.getvalue()
    except Exception:
        return None
