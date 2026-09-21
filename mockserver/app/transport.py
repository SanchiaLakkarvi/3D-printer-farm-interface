from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from prusa.connect.printer import Printer, const
from prusa.connect.printer.command import Command

from .models import PrinterConfig

log = logging.getLogger(__name__)


class PrinterTransport(Protocol):
    @property
    def state(self) -> str: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def set_state(
        self, state: const.State, source: const.Source, **kwargs: Any
    ) -> None: ...

    def event(
        self, event: const.Event, source: const.Source, **kwargs: Any
    ) -> None: ...

    def telemetry(self, **kwargs: Any) -> None: ...

    def resolve_virtual_path(self, virtual_path: str) -> str: ...

    def set_download_finished(self, callback: Callable[[Any], None]) -> None: ...

    def set_printed_file_callback(self, callback: Callable[[], str | None]) -> None: ...

    def set_command_handler(
        self, command: const.Command, callback: Callable[[Command], dict[str, Any]]
    ) -> None: ...


@dataclass(frozen=True)
class SyntheticSdkPrinterType:
    value: tuple[int, int, int]
    header: str

    def __str__(self) -> str:
        return self.header


class LegacySdkMockTransport:
    """Legacy HTTP-polling SDK adapter used only by the simulator."""

    def __init__(self, config: PrinterConfig, connect_server: str):
        if config.sdk_identity.header.upper() != "MOCK":
            raise ValueError("LegacySdkMockTransport requires a synthetic MOCK identity")
        if ".bgcode" not in const.GCODE_EXTENSIONS:
            const.GCODE_EXTENSIONS = (*const.GCODE_EXTENSIONS, ".bgcode")
        identity = SyntheticSdkPrinterType(
            value=(
                config.sdk_identity.type,
                config.sdk_identity.version,
                config.sdk_identity.subversion,
            ),
            header=config.sdk_identity.header,
        )
        self._config = config
        self._client = Printer(
            identity,  # type: ignore[arg-type]
            config.serial_number,
            config.fingerprint,
            mmu_supported=False,
        )
        self._client.firmware = "mock-printer"
        self._client.software = "prusa-farm-mock/1.0"
        self._client.set_connection(connect_server.rstrip("/"), config.token)
        storage = Path(config.storage_dir).resolve()
        storage.mkdir(parents=True, exist_ok=True)
        self._client.attach(str(storage), "usb")
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    @property
    def state(self) -> str:
        return self._client.state.value

    def start(self) -> None:
        self._stop.clear()
        self.set_state(const.State.READY, const.Source.FIRMWARE, ready=True)
        targets = [
            (self._client.loop, "sdk-loop"),
            (self._client.download_mgr.loop, "download-loop"),
            (self._command_loop, "command-loop"),
            (self._inotify_loop, "inotify-loop"),
        ]
        for target, suffix in targets:
            thread = threading.Thread(
                target=target,
                name=f"{self._config.id}-{suffix}",
                daemon=True,
            )
            thread.start()
            self._threads.append(thread)

    def stop(self) -> None:
        self._stop.set()
        self._client.stop_loop()
        self._client.download_mgr.stop_loop()
        for thread in self._threads:
            thread.join(timeout=2)

    def set_state(
        self, state: const.State, source: const.Source, **kwargs: Any
    ) -> None:
        self._client.set_state(state, source, **kwargs)

    def event(self, event: const.Event, source: const.Source, **kwargs: Any) -> None:
        self._client.event_cb(event, source, **kwargs)

    def telemetry(self, **kwargs: Any) -> None:
        self._client.telemetry(**kwargs)

    def resolve_virtual_path(self, virtual_path: str) -> str:
        return self._client.fs.get_os_path(virtual_path)

    def set_download_finished(self, callback: Callable[[Any], None]) -> None:
        self._client.download_finished_cb = callback
        self._client.download_mgr.download_finished_cb = callback

    def set_printed_file_callback(self, callback: Callable[[], str | None]) -> None:
        self._client.printed_file_cb = callback

    def set_command_handler(
        self, command: const.Command, callback: Callable[[Command], dict[str, Any]]
    ) -> None:
        self._client.set_handler(command, callback)

    def _command_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._client.command()
            except Exception:
                log.exception("Command handler failed for %s", self._config.id)
            time.sleep(0.1)

    def _inotify_loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._client.inotify_handler()
            except Exception:
                log.exception("Inotify failure for %s", self._config.id)
            time.sleep(0.2)
