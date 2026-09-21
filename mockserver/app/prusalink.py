"""PrusaLink API v1 facade over the mock printers.

Spec: https://github.com/prusa3d/Prusa-Link-Web/blob/master/spec/openapi.yaml

Real PrusaLink is one API per printer host. The mock hosts several printers in
one process, so each is mounted under its own prefix:

    /prusalink/{printer_id}/api/v1/status

Auth is HTTP Digest, as in the spec: username ``maker``, password = the
printer's ``token`` from config/printers.yaml (synthetic values).
"""

from __future__ import annotations

import hashlib
import re
import secrets
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response

USERNAME = "maker"
REALM = "Prusa Farm Mock"
_AUTH_PARAM = re.compile(r'(\w+)=(?:"([^"]*)"|([^,\s]*))')
_KNOWN_STATES = {
    "IDLE", "BUSY", "PRINTING", "PAUSED", "FINISHED", "STOPPED", "ERROR", "ATTENTION", "READY",
}


def _md5(value: str) -> str:
    return hashlib.md5(value.encode()).hexdigest()  # noqa: S324 - Digest auth mandates MD5


def _challenge() -> HTTPException:
    header = (
        f'Digest realm="{REALM}", nonce="{secrets.token_hex(16)}", '
        f'opaque="{secrets.token_hex(8)}", qop="auth", algorithm=MD5'
    )
    return HTTPException(status_code=401, detail="Unauthorized", headers={"WWW-Authenticate": header})


def _digest_ok(request: Request, password: str) -> bool:
    header = request.headers.get("authorization", "")
    if not header.lower().startswith("digest "):
        return False
    params = {k.lower(): quoted or bare for k, quoted, bare in _AUTH_PARAM.findall(header[7:])}
    if params.get("username") != USERNAME or params.get("qop") != "auth":
        return False
    uri = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    if params.get("uri") != uri:
        return False
    ha1 = _md5(f"{USERNAME}:{params.get('realm', '')}:{password}")
    ha2 = _md5(f"{request.method}:{uri}")
    expected = _md5(
        f"{ha1}:{params.get('nonce', '')}:{params.get('nc', '')}:{params.get('cnonce', '')}:auth:{ha2}"
    )
    return secrets.compare_digest(expected, params.get("response", ""))


def build_router(manager: Any) -> APIRouter:
    """Build the router. ``manager`` needs ``get(printer_id)`` returning a worker."""
    router = APIRouter(prefix="/prusalink/{printer_id}")
    job_ids: dict[str, int] = {}

    def worker_for(printer_id: str, request: Request) -> Any:
        try:
            worker = manager.get(printer_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"Unknown printer {printer_id}") from exc
        if not _digest_ok(request, worker.config.token):
            raise _challenge()
        return worker

    Worker = Depends(worker_for)

    def state_of(worker: Any) -> str:
        state = str(worker.status().state).split(".")[-1].upper()
        return state if state in _KNOWN_STATES else "IDLE"

    def active_job(worker: Any, printer_id: str) -> dict[str, Any] | None:
        if not worker.simulator.running:
            return None
        status = worker.status()
        return {
            "id": job_ids.setdefault(printer_id, 1),
            "state": state_of(worker),
            "progress": status.progress_percent,
            "time_remaining": int(status.time_remaining_s or 0),
            "time_printing": int(status.elapsed_s),
        }

    def target_of(worker: Any, storage: str, path: str) -> Path:
        if storage != "usb":
            raise HTTPException(status_code=404, detail=f"Unknown storage {storage}")
        try:
            return worker.storage_path(path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def begin(worker: Any, printer_id: str, path: str, print_after: bool) -> None:
        worker.handle_upload(path, print_after)
        if print_after:
            job_ids[printer_id] = job_ids.get(printer_id, 0) + 1

    @router.get("/api/version")
    def version(printer_id: str, worker: Any = Worker) -> dict[str, Any]:
        return {
            "api": "2.0.0",
            "server": "mock",
            "version": "1.0.0",
            "printer": worker.config.gcode_printer_model,
            "text": f"PrusaLink mock ({printer_id})",
        }

    @router.get("/api/v1/status")
    def status(printer_id: str, worker: Any = Worker) -> dict[str, Any]:
        snapshot = worker.status()
        tool = next((t for t in snapshot.toolheads if t.slot == snapshot.active_tool), None)
        tool = tool or (snapshot.toolheads[0] if snapshot.toolheads else None)
        body: dict[str, Any] = {
            "printer": {
                "state": state_of(worker),
                "temp_nozzle": tool.temperature_c if tool else 0,
                "target_nozzle": (tool.target_temperature_c or 0) if tool else 0,
                "temp_bed": snapshot.temp_bed_c,
                "target_bed": snapshot.target_bed_c or 0,
            }
        }
        job = active_job(worker, printer_id)
        if job:
            body["job"] = {k: job[k] for k in ("id", "progress", "time_remaining", "time_printing")}
        return body

    @router.get("/api/v1/job")
    def get_job(printer_id: str, worker: Any = Worker) -> Any:
        job = active_job(worker, printer_id)
        return job if job else Response(status_code=204)

    @router.put("/api/v1/files/{storage}/{path:path}", status_code=201)
    async def upload(
        printer_id: str, storage: str, path: str, request: Request, worker: Any = Worker
    ) -> Response:
        target = target_of(worker, storage, path)
        overwrite = request.headers.get("overwrite", "?0") == "?1"
        print_after = request.headers.get("print-after-upload", "?0") == "?1"
        if target.exists() and not overwrite:
            raise HTTPException(status_code=409, detail="File exists")
        if print_after and worker.simulator.running:
            raise HTTPException(status_code=409, detail="A job is already running")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(await request.body())
        begin(worker, printer_id, path, print_after)
        return Response(status_code=201)

    @router.post("/api/v1/files/{storage}/{path:path}", status_code=204)
    def start_print(
        printer_id: str, storage: str, path: str, worker: Any = Worker
    ) -> Response:
        if not target_of(worker, storage, path).exists():
            raise HTTPException(status_code=404, detail="File not found")
        if worker.simulator.running:
            raise HTTPException(status_code=409, detail="A job is already running")
        begin(worker, printer_id, path, True)
        return Response(status_code=204)

    def _control(printer_id: str, job_id: int, worker: Any, action: str) -> Response:
        job = active_job(worker, printer_id)
        if job is None:
            raise HTTPException(status_code=404, detail="No active job")
        if job["id"] != job_id:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        try:
            getattr(worker.simulator, action)()
        except RuntimeError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return Response(status_code=204)

    @router.delete("/api/v1/job/{job_id}", status_code=204)
    def stop_job(printer_id: str, job_id: int, worker: Any = Worker) -> Response:
        return _control(printer_id, job_id, worker, "stop")

    @router.put("/api/v1/job/{job_id}/pause", status_code=204)
    def pause_job(printer_id: str, job_id: int, worker: Any = Worker) -> Response:
        return _control(printer_id, job_id, worker, "pause")

    @router.put("/api/v1/job/{job_id}/resume", status_code=204)
    def resume_job(printer_id: str, job_id: int, worker: Any = Worker) -> Response:
        return _control(printer_id, job_id, worker, "resume")

    return router
