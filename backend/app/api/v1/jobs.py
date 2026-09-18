"""Print Job upload endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import require_submitter
from app.db.session import get_db
from app.models.user import User
from app.schemas.job import JobUploadOut
from app.services import upload_service

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/upload", response_model=JobUploadOut, status_code=201)
def upload_gcode(
    file: Annotated[UploadFile, File(description="Pre-sliced .gcode or .gco file")],
    user: Annotated[User, Depends(require_submitter)],
    db: Annotated[Session, Depends(get_db)],
) -> JobUploadOut:
    """Upload a G-code file and create a Print Job in pending_selection.

    Role comes from the authenticated profile (require_submitter hierarchy).
    Client-supplied paths/filenames are never used for on-disk location.
    """
    job = upload_service.upload_gcode(db=db, user=user, upload=file)
    return JobUploadOut(
        id=job.id,
        status=job.status,
        original_filename=job.original_filename or "",
        gcode_path=job.gcode_path,
    )
