"""Pydantic schemas for Print Job upload responses."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import JobStatus


class JobUploadOut(BaseModel):
    """Successful G-code upload response (relative storage key only)."""

    model_config = ConfigDict(from_attributes=True)

    tracking_url: str
    submission_id: uuid.UUID
    id: uuid.UUID
    status: JobStatus
    original_filename: str
    gcode_path: str = Field(
        description="Relative storage key under FILE_STORAGE_ROOT (never absolute).",
    )
