from __future__ import annotations

from fastapi import APIRouter

api_router = APIRouter(prefix="/api/v1")

# Future v1 route modules will be included here:
# from app.api.v1 import auth, users, printers, gcode, jobs, farmer, notifications, reports
# api_router.include_router(auth.router)
# ...
