from __future__ import annotations

from prusa.connect.printer import const

from .models import AppConfig, ConsumableUpdate, SpoolConfig
from .sdk_worker import MockPrinterWorker
from .validator import GCodeValidator


class PrinterManager:
    def __init__(self, config: AppConfig):
        profiles = {profile.id: profile for profile in config.approved_profiles}
        validator = GCodeValidator(config.gcode_tail_bytes)
        self.workers: dict[str, MockPrinterWorker] = {}
        for printer in config.printers:
            if not printer.enabled:
                continue
            worker = MockPrinterWorker(
                config=printer,
                profile=profiles[printer.approved_profile_id],
                connect_server=config.connect.server,
                validator=validator,
            )
            self.workers[printer.id] = worker

    def start(self) -> None:
        for worker in self.workers.values():
            worker.start()

    def shutdown(self) -> None:
        for worker in self.workers.values():
            worker.shutdown()

    def get(self, printer_id: str) -> MockPrinterWorker:
        try:
            return self.workers[printer_id]
        except KeyError as exc:
            raise KeyError(f"Unknown printer: {printer_id}") from exc

    def inject_fault(self, printer_id: str, state: str, reason: str) -> None:
        self.get(printer_id).inject_fault(const.State(state), reason)

    def update_consumables(self, printer_id: str, update: ConsumableUpdate) -> None:
        config = self.get(printer_id).config
        tool = next((item for item in config.toolheads if item.slot == update.slot), None)
        if tool is None:
            raise ValueError(f"Unknown tool slot {update.slot} for printer {printer_id}")
        if tool.spool is None:
            if update.material is None:
                raise ValueError("material is required when assigning a new spool")
            tool.spool = SpoolConfig(
                material=update.material,
                colour=update.colour,
                remaining_g=update.remaining_g,
            )
            return
        if update.material is not None:
            tool.spool.material = update.material
        if update.colour is not None:
            tool.spool.colour = update.colour
        if update.remaining_g is not None:
            tool.spool.remaining_g = update.remaining_g
