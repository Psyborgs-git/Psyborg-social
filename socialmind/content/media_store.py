from __future__ import annotations

import io
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import aiofiles
from miniopy_async import Minio

from socialmind.config.settings import settings

_MEDIA_TMP = "media_tmp"


class MediaStore:
    BUCKET = "socialmind"

    def __init__(self) -> None:
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    async def upload(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        account_id: str,
    ) -> str:
        """Upload media and return the internal minio:// URL."""
        key = f"accounts/{account_id}/media/{uuid4()}/{filename}"
        await self._client.put_object(
            self.BUCKET,
            key,
            io.BytesIO(data),
            len(data),
            content_type=content_type,
        )
        return f"minio://{self.BUCKET}/{key}"

    async def download_to_temp(self, minio_url: str) -> str:
        """Download object to a local temp file and return the path."""
        bucket, key = self._parse_url(minio_url)
        suffix = Path(key).suffix or ".bin"
        os.makedirs(_MEDIA_TMP, exist_ok=True)
        dest = os.path.join(_MEDIA_TMP, f"{uuid4()}{suffix}")
        response = await self._client.get_object(bucket, key)
        async with aiofiles.open(dest, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)
        return dest

    async def get_public_url(self, minio_url: str, expires: int = 3600) -> str:
        """Generate a presigned URL for temporary public access."""
        bucket, key = self._parse_url(minio_url)
        return await self._client.presigned_get_object(
            bucket, key, expires=timedelta(seconds=expires)
        )

    def _parse_url(self, minio_url: str) -> tuple[str, str]:
        """Parse a minio://bucket/key URL into (bucket, key)."""
        without_scheme = minio_url.removeprefix("minio://")
        bucket, _, key = without_scheme.partition("/")
        return bucket, key

