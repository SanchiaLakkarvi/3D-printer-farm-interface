"""Build the right PrinterPort for a Printer row."""

from __future__ import annotations

from app.adapters.printer.port import PrinterPort
from app.adapters.printer.prusalink import PrusaLinkAdapter
from app.models.printer import Printer

DEFAULT_USERNAME = "maker"


def build_printer_port(printer: Printer) -> PrinterPort | None:
    """Return a port for the printer, or None if it has no PrusaLink connection."""
    if not printer.prusalink_url:
        return None
    return PrusaLinkAdapter(
        base_url=printer.prusalink_url,
        username=printer.prusalink_username or DEFAULT_USERNAME,
        password=printer.prusalink_password or "",
    )
