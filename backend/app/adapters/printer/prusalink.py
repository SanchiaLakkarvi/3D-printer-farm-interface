"""PrusaLink HTTP adapter (PrusaLink API v1, HTTP Digest auth).

Spec: https://github.com/prusa3d/Prusa-Link-Web/blob/master/spec/openapi.yaml
The same adapter talks to the mock server and, later, to real printers.
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import httpx

from app.adapters.printer.port import (
    PrinterAuthError,
    PrinterConflictError,
    PrinterError,
    PrinterSnapshot,
    PrinterState,
    PrinterUnreachableError,
)


class PrusaLinkAdapter:
    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        *,
        storage: str = "usb",
        timeout_s: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._storage = storage
        self._client = client or httpx.Client(
            base_url=base_url.rstrip("/"),
            auth=httpx.DigestAuth(username, password),
            timeout=timeout_s,
        )

    def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        try:
            response = self._client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            raise PrinterUnreachableError(f"Cannot reach printer: {exc}") from exc
        if response.status_code == 401:
            raise PrinterAuthError("Printer rejected the credentials.")
        if response.status_code == 409:
            raise PrinterConflictError("Printer refused the action in its current state.")
        if response.status_code >= 400:
            raise PrinterError(f"Printer returned HTTP {response.status_code} for {method} {url}.")
        return response

    def get_status(self) -> PrinterSnapshot:
        body = self._request("GET", "/api/v1/status").json()
        printer = body.get("printer") or {}
        job = body.get("job") or {}
        try:
            state = PrinterState(printer.get("state"))
        except ValueError:
            state = PrinterState.UNKNOWN
        return PrinterSnapshot(
            state=state,
            temp_nozzle=printer.get("temp_nozzle"),
            temp_bed=printer.get("temp_bed"),
            job_id=job.get("id"),
            progress_pct=job.get("progress"),
            time_remaining_s=job.get("time_remaining"),
            time_printing_s=job.get("time_printing"),
        )

    def upload_and_start(self, remote_name: str, local_path: Path) -> None:
        url = f"/api/v1/files/{quote(self._storage)}/{quote(remote_name)}"
        with open(local_path, "rb") as fh:
            self._request(
                "PUT",
                url,
                content=fh,
                headers={
                    "Content-Type": "application/octet-stream",
                    "Content-Length": str(Path(local_path).stat().st_size),
                    "Print-After-Upload": "?1",
                    "Overwrite": "?1",
                },
            )

    def stop_job(self, job_id: int) -> None:
        self._request("DELETE", f"/api/v1/job/{job_id}")

    def pause_job(self, job_id: int) -> None:
        self._request("PUT", f"/api/v1/job/{job_id}/pause")

    def resume_job(self, job_id: int) -> None:
        self._request("PUT", f"/api/v1/job/{job_id}/resume")

    def close(self) -> None:
        self._client.close()
