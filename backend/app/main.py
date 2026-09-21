from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.services.printer_sync_service import sync_all_printers

log = logging.getLogger(__name__)


def _seed_demo_accounts() -> None:
    """Re-create the fake-auth demo accounts (no-op unless AUTH_ADAPTER=fake)."""
    from app.adapters.auth.fake import FakeAuthAdapter
    from app.api.deps import get_auth_port
    from app.db.session import SessionLocal
    from app.services.demo_accounts import parse_demo_accounts, seed_demo_accounts

    auth = get_auth_port()
    if not isinstance(auth, FakeAuthAdapter) or not settings.demo_accounts:
        return
    db = SessionLocal()
    try:
        seeded = seed_demo_accounts(db, auth, parse_demo_accounts(settings.demo_accounts))
        # uvicorn.error is the logger uvicorn actually prints at INFO level
        logging.getLogger("uvicorn.error").info(
            "Demo accounts ready: %s", ", ".join(seeded) or "already registered"
        )
    finally:
        db.close()


async def _poll_printers(interval_s: float) -> None:
    while True:
        try:
            await asyncio.to_thread(sync_all_printers)
        except Exception:
            log.exception("Printer sync cycle failed")
        await asyncio.sleep(interval_s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    del app
    if settings.auth_adapter == "fake" and settings.demo_accounts:
        try:
            await asyncio.to_thread(_seed_demo_accounts)
        except Exception:
            log.exception("Could not seed DEMO_ACCOUNTS; check the format and database")
    poller = None
    if settings.printer_poll_interval_s > 0:
        poller = asyncio.create_task(_poll_printers(settings.printer_poll_interval_s))
    try:
        yield
    finally:
        if poller is not None:
            poller.cancel()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend API for the UWA 3D Printer Farm Management System. "
        "Provides authentication, G-code validation, print queue management, "
        "printer integration and usage reporting."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "service": "3d-print-farm-backend"}
