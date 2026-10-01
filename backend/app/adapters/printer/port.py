"""Printer port: what the backend needs from a printer, independent of transport."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class PrinterState(str, enum.Enum):
    """PrusaLink ``printer.state`` values, plus UNREACHABLE for connection failures."""

    IDLE = "IDLE"
    BUSY = "BUSY"
    PRINTING = "PRINTING"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"
    ATTENTION = "ATTENTION"
    READY = "READY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class PrinterSnapshot:
    state: PrinterState
    temp_nozzle: float | None = None
    temp_bed: float | None = None
    job_id: int | None = None
    progress_pct: float | None = None
    time_remaining_s: int | None = None
    time_printing_s: int | None = None


class PrinterError(Exception):
    """Base class for printer communication failures."""


class PrinterUnreachableError(PrinterError):
    """The printer could not be reached (network down, wrong network, timeout)."""


class PrinterAuthError(PrinterError):
    """The printer rejected the credentials."""


class PrinterConflictError(PrinterError):
    """The printer refused the action in its current state (e.g. already printing)."""


class PrinterPort(Protocol):
    def get_status(self) -> PrinterSnapshot: ...

    def upload_and_start(self, remote_name: str, local_path: Path) -> None:
        """Upload the file to the printer and start printing it."""

    def stop_job(self, job_id: int) -> None: ...

    def pause_job(self, job_id: int) -> None: ...

    def resume_job(self, job_id: int) -> None: ...

    def close(self) -> None: ...
