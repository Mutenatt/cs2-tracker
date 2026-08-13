"""Cloudflare R2 (S3-compatible) para los videos de lineups. El bucket es
privado -- en vez de exponer el endpoint S3 crudo (exige Authorization
firmada, un <video src> de navegador no puede armar eso), GET /lineups firma
cada video_url al vuelo con una URL presignada de corta duración. Ver
config.py para las credenciales (CS2_R2_*)."""

from __future__ import annotations

from functools import lru_cache

from cs2tracker.config import settings


@lru_cache(maxsize=1)
def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        # R2 solo habla el estilo "path", no "virtual-hosted" (bucket.host/key).
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        region_name="auto",
    )


def r2_configured() -> bool:
    return bool(
        settings.r2_account_id
        and settings.r2_bucket
        and settings.r2_access_key_id
        and settings.r2_secret_access_key
    )


def presigned_video_url(video_path: str) -> str | None:
    """video_path es el valor crudo de Lineup.video_url (p.ej.
    "/lineups/de_mirage/ct/deto-ct-caverna.mp4") -- coincide 1:1 con la key
    del objeto en el bucket. None si R2 no está configurado (el caller decide
    qué hacer: en dev sin credenciales, mejor no romper /lineups entero)."""
    if not r2_configured():
        return None
    key = video_path.lstrip("/")
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket, "Key": key},
        ExpiresIn=settings.r2_video_url_ttl,
    )
