from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, materials, rbac

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(rbac.router)
api_router.include_router(materials.router)
