from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from .config import load_config
from .manager import PrinterManager
from .models import ConsumableUpdate, FaultRequest, PrinterStatus, ValidationResult

config = load_config()
manager = PrinterManager(config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    manager.start()
    yield
    manager.shutdown()


app = FastAPI(
    title="Prusa Farm Mock Printer",
    version="1.0.0",
    description=(
        "Multi-printer simulator using Prusa-Connect-SDK-Printer. "
        "The /control API is for test/operator control only; production print "
        "commands arrive from the Connect-compatible backend as responses to telemetry."
    ),
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, object]:
    return {"ok": True, "printers": len(manager.workers)}


@app.get("/control/printers", response_model=list[PrinterStatus])
def list_printers() -> list[PrinterStatus]:
    return [worker.status() for worker in manager.workers.values()]


@app.get("/control/printers/{printer_id}", response_model=PrinterStatus)
def get_printer(printer_id: str) -> PrinterStatus:
    try:
        return manager.get(printer_id).status()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post(
    "/control/printers/{printer_id}/validate",
    response_model=ValidationResult,
    summary="Validate an already-downloaded virtual file",
)
def validate_file(printer_id: str, virtual_path: str) -> ValidationResult:
    try:
        return manager.get(printer_id).validate_virtual_path(virtual_path)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/control/printers/{printer_id}/fault")
def inject_fault(printer_id: str, request: FaultRequest) -> dict[str, bool]:
    try:
        manager.inject_fault(printer_id, request.state, request.reason)
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/control/printers/{printer_id}/reset")
def reset_printer(printer_id: str) -> dict[str, bool]:
    try:
        manager.get(printer_id).reset()
        return {"ok": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/control/printers/{printer_id}/consumables")
def update_consumables(
    printer_id: str,
    update: ConsumableUpdate,
) -> PrinterStatus:
    try:
        manager.update_consumables(printer_id, update)
        return manager.get(printer_id).status()
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
