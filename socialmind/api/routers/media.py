from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_current_user, get_db
from socialmind.models.media import MediaAsset
from socialmind.models.user import User

router = APIRouter()

# Simple in-memory storage for demo (in production use S3, etc.)
UPLOAD_DIR = "/tmp/socialmind_media"


def _storage_path(storage_key: str) -> str:
    return os.path.join(UPLOAD_DIR, storage_key.lstrip("/"))


class MediaAssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    filename: str
    media_type: str
    file_size_bytes: int | None
    mime_type: str | None
    width: int | None
    height: int | None
    duration_seconds: float | None
    storage_key: str
    storage_bucket: str
    created_at: datetime


@router.get("/", response_model=list[MediaAssetResponse])
async def list_media(
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(MediaAsset))
    media = result.scalars().all()
    return media


@router.post(
    "/upload", response_model=MediaAssetResponse, status_code=status.HTTP_201_CREATED
)
async def upload_media(
    file: Annotated[UploadFile, File()],
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    # Determine media type based on MIME type
    media_type = "image"
    if file.content_type:
        if "video" in file.content_type:
            media_type = "video"
        elif "audio" in file.content_type:
            media_type = "audio"
        elif "gif" in file.content_type:
            media_type = "gif"

    # Read file
    contents = await file.read()
    file_size = len(contents)

    # Create storage key
    storage_key = f"media/{uuid.uuid4()}/{file.filename}"
    file_path = _storage_path(storage_key)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "wb") as output_file:
        output_file.write(contents)

    # Create media asset record
    media = MediaAsset(
        filename=file.filename,
        media_type=media_type,
        file_size_bytes=file_size,
        mime_type=file.content_type,
        storage_key=storage_key,
        storage_bucket="socialmind",
    )

    db.add(media)
    await db.commit()
    await db.refresh(media)

    # In production, upload to S3
    # For now, just store the metadata

    return media


@router.get("/{media_id}/download")
async def download_media(
    media_id: str,
    filename: str | None = None,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    file_path = _storage_path(media.storage_key)
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media file is unavailable"
        )

    return FileResponse(
        file_path,
        media_type=media.mime_type or "application/octet-stream",
        filename=filename or media.filename,
    )


@router.get("/{media_id}", response_model=MediaAssetResponse)
async def get_media(
    media_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )
    return media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media(
    media_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(MediaAsset).where(MediaAsset.id == media_id))
    media = result.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    file_path = _storage_path(media.storage_key)
    if os.path.exists(file_path):
        os.remove(file_path)

    await db.delete(media)
    await db.commit()
