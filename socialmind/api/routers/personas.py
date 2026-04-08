from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.api.dependencies import get_current_user, get_db
from socialmind.models.persona import Persona
from socialmind.models.user import User

router = APIRouter()


class PersonaCreate(BaseModel):
    name: str
    system_prompt: str
    tone: str = "casual"
    niche: str = "general"
    language: str = "en"
    vocab_level: str = "conversational"
    emoji_usage: str = "moderate"
    hashtag_strategy: str = "relevant"
    reply_probability: float = 0.7
    like_probability: float = 0.8
    follow_back_probability: float = 0.5


class PersonaUpdate(BaseModel):
    name: str | None = None
    system_prompt: str | None = None
    tone: str | None = None
    niche: str | None = None
    language: str | None = None
    vocab_level: str | None = None
    emoji_usage: str | None = None
    hashtag_strategy: str | None = None
    reply_probability: float | None = None
    like_probability: float | None = None
    follow_back_probability: float | None = None


class PersonaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    system_prompt: str
    tone: str
    niche: str
    language: str
    vocab_level: str
    emoji_usage: str
    hashtag_strategy: str
    reply_probability: float
    like_probability: float
    follow_back_probability: float
    created_at: datetime


@router.get("/", response_model=list[PersonaResponse])
async def list_personas(
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(Persona))
    personas = result.scalars().all()
    return personas


@router.post("/", response_model=PersonaResponse, status_code=status.HTTP_201_CREATED)
async def create_persona(
    body: PersonaCreate,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    persona = Persona(**body.model_dump())
    db.add(persona)
    await db.commit()
    await db.refresh(persona)
    return persona


@router.get("/{persona_id}", response_model=PersonaResponse)
async def get_persona(
    persona_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )
    return persona


@router.put("/{persona_id}", response_model=PersonaResponse)
async def update_persona(
    persona_id: str,
    body: PersonaUpdate,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )

    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(persona, key, value)

    await db.commit()
    await db.refresh(persona)
    return persona


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(
    persona_id: str,
    _: Annotated[User, Depends(get_current_user)] = None,
    db: Annotated[AsyncSession, Depends(get_db)] = None,
):
    result = await db.execute(select(Persona).where(Persona.id == persona_id))
    persona = result.scalar_one_or_none()
    if not persona:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Persona not found"
        )

    await db.delete(persona)
    await db.commit()
