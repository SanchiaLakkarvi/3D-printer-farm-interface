"""PrusaLink adapter tests against faked HTTP responses (no printer needed)."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.adapters.printer.port import (
    PrinterAuthError,
    PrinterConflictError,
    PrinterError,
    PrinterState,
    PrinterUnreachableError,
)
from app.adapters.printer.prusalink import PrusaLinkAdapter


def _adapter(handler) -> PrusaLinkAdapter:
    client = httpx.Client(base_url="http://printer.test", transport=httpx.MockTransport(handler))
    return PrusaLinkAdapter("http://printer.test", "maker", "pw", client=client)


def test_get_status_maps_printing_job() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/status"
        return httpx.Response(200, json={
            "printer": {"state": "PRINTING", "temp_nozzle": 214.9, "temp_bed": 59.5},
            "job": {"id": 42, "progress": 12.5, "time_remaining": 3000, "time_printing": 400},
        })

    snap = _adapter(handler).get_status()
    assert snap.state is PrinterState.PRINTING
    assert (snap.job_id, snap.progress_pct, snap.time_remaining_s) == (42, 12.5, 3000)
    assert snap.temp_nozzle == 214.9


def test_get_status_idle_without_job_and_unknown_state() -> None:
    idle = _adapter(lambda r: httpx.Response(200, json={"printer": {"state": "IDLE"}})).get_status()
    assert idle.state is PrinterState.IDLE and idle.job_id is None
    odd = _adapter(lambda r: httpx.Response(200, json={"printer": {"state": "WEIRD"}})).get_status()
    assert odd.state is PrinterState.UNKNOWN


def test_upload_and_start_sends_print_after_upload(tmp_path: Path) -> None:
    f = tmp_path / "job.gcode"
    f.write_bytes(b"G28\n")
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.raw_path.decode(),
                    headers=request.headers, body=request.read())
        return httpx.Response(201)

    _adapter(handler).upload_and_start("my job.gcode", f)
    assert seen["method"] == "PUT"
    assert seen["path"] == "/api/v1/files/usb/my%20job.gcode"
    assert seen["headers"]["print-after-upload"] == "?1"
    assert seen["headers"]["content-length"] == "4"
    assert seen["body"] == b"G28\n"


def test_stop_job_calls_delete() -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path)
        return httpx.Response(204)

    _adapter(handler).stop_job(7)
    assert seen == {"method": "DELETE", "path": "/api/v1/job/7"}


@pytest.mark.parametrize("action", ["pause", "resume"])
def test_pause_and_resume_call_put(action: str) -> None:
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(method=request.method, path=request.url.path)
        return httpx.Response(204)

    getattr(_adapter(handler), f"{action}_job")(7)
    assert seen == {"method": "PUT", "path": f"/api/v1/job/7/{action}"}


@pytest.mark.parametrize(
    ("status", "exc"),
    [(401, PrinterAuthError), (409, PrinterConflictError), (500, PrinterError)],
)
def test_http_errors_are_mapped(status: int, exc: type[Exception]) -> None:
    with pytest.raises(exc):
        _adapter(lambda r: httpx.Response(status)).stop_job(1)


def test_network_failure_is_unreachable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route", request=request)

    with pytest.raises(PrinterUnreachableError):
        _adapter(handler).get_status()
