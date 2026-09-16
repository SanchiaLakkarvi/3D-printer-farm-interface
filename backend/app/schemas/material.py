"""Pydantic schemas for Material API requests and responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict


class MaterialCreate(BaseModel):
    name: str
    type: str
    colour: str


class MaterialUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    colour: str | None = None


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: str
    colour: str
