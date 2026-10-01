from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, jobs, materials, notifications, printers, rbac, reports

from app.core.config import settings

api_router = APIRouter(prefix=settings.api_prefix)
api_router.include_router(auth.router)
api_router.include_router(rbac.router)
api_router.include_router(materials.router)
api_router.include_router(printers.router)
api_router.include_router(jobs.router)
api_router.include_router(reports.router)
api_router.include_router(notifications.router)
