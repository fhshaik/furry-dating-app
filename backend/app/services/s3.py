"""S3 service for generating presigned upload URLs."""

import uuid
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import HTTPException

from app.core.config import settings

PRESIGNED_URL_EXPIRY = 300  # seconds

# Safe raster image types only; SVG (image/svg+xml) is excluded to prevent XSS via embedded script.
ALLOWED_IMAGE_CONTENT_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
})


def build_public_url(key: str) -> str:
    """Build the public HTTPS URL for an uploaded S3 object."""
    encoded_key = quote(key, safe="/")
    if settings.aws_region == "us-east-1":
        return f"https://{settings.aws_s3_bucket}.s3.amazonaws.com/{encoded_key}"
    return f"https://{settings.aws_s3_bucket}.s3.{settings.aws_region}.amazonaws.com/{encoded_key}"


def generate_upload_url(fursona_id: int, content_type: str = "image/jpeg") -> tuple[str, str, str]:
    """Generate a presigned S3 PUT URL for a fursona image.

    Returns a (upload_url, key, public_url) tuple.
    Only safe raster content types are allowed (SVG excluded to prevent XSS).
    """
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"content_type must be one of: {', '.join(sorted(ALLOWED_IMAGE_CONTENT_TYPES))}",
        )
    key = f"fursonas/{fursona_id}/{uuid.uuid4()}"
    try:
        client = boto3.client(
            "s3",
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region,
        )
        url: str = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.aws_s3_bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=PRESIGNED_URL_EXPIRY,
        )
    except (BotoCoreError, ClientError) as exc:
        raise HTTPException(status_code=500, detail="Failed to generate upload URL") from exc
    return url, key, build_public_url(key)
