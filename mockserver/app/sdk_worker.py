from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any

from prusa.connect.printer import const
from prusa.connect.printer.command import Command

from .gcode_metadata import normalize_key, parse_number_sequence
from .models import (
    ApprovedProfile,
    PrinterConfig,
    PrinterStatus,
    ToolheadStatus,
    ValidationResult,
)
from .simulator import PrintSimulator
from .transport import LegacySdkMockTransport, PrinterTransport
from .validator import GCodeValidator

log = logging.getLogger(__name__)


class MockPrinterWorker:
    def __init__(
        self,
        config: PrinterConfig,
        profile: ApprovedProfile,
        connect_server: str,
        validator: GCodeValidator,
    ):
        self.config = config
        self.profile = profile
        self.validator = validator
        self.connect_server = connect_server.rstrip("/")
        self.transport: PrinterTransport = LegacySdkMockTransport(
            config, self.connect_server
        )

        self.simulator = PrintSimulator(
            self.transport.set_state,
            config.simulation_speed,
            [tool.slot for tool in config.toolheads],
            config.chamber_supported,
            self._consume_filament,
        )
        self.last_validation: ValidationResult | None = None
        self._validation_by_virtual_path: dict[str, ValidationResult] = {}
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

        self.transport.set_download_finished(self._download_finished)
        self.transport.set_printed_file_callback(self._printed_os_path)
        self.transport.set_command_handler(const.Command.START_PRINT, self._start_print)
        self.transport.set_command_handler(const.Command.STOP_PRINT, self._stop_print)
        self.transport.set_command_handler(const.Command.PAUSE_PRINT, self._pause_print)
        self.transport.set_command_handler(const.Command.RESUME_PRINT, self._resume_print)

    def start(self) -> None:
        self._stop.clear()
        self.transport.start()
        thread = threading.Thread(
            target=self._telemetry_loop,
            name=f"{self.config.id}-telemetry-loop",
            daemon=True,
        )
        thread.start()
        self._threads.append(thread)

    def shutdown(self) -> None:
        self._stop.set()
        self.transport.stop()
        if self.simulator.running:
            try:
                self.simulator.stop()
            except RuntimeError:
                pass
        for thread in self._threads:
            thread.join(timeout=2)

    def status(self) -> PrinterStatus:
        snap = self.simulator.snapshot
        tool_configs = {tool.slot: tool for tool in self.config.toolheads}
        toolheads = []
        for slot, simulated in sorted(snap.toolheads.items()):
            configured = tool_configs[slot]
            spool = configured.spool
            toolheads.append(
                ToolheadStatus(
                    slot=slot,
                    state=simulated.state,
                    nozzle_diameter_mm=configured.nozzle_diameter_mm,
                    high_flow=configured.high_flow,
                    temperature_c=round(simulated.temperature_c, 1),
                    target_temperature_c=simulated.target_temperature_c,
                    material=spool.material if spool else None,
                    colour=spool.colour if spool else None,
                    filament_remaining_g=spool.remaining_g if spool else None,
                )
            )
        return PrinterStatus(
            id=self.config.id,
            physical_model=self.config.physical_model,
            state=self.transport.state,
            current_file=snap.current_file,
            progress_percent=round(snap.progress_percent, 2),
            estimated_duration_s=snap.estimated_duration_s,
            elapsed_s=round(snap.elapsed_s, 2),
            time_remaining_s=(
                round(snap.time_remaining_s, 2)
                if snap.time_remaining_s is not None
                else None
            ),
            temp_bed_c=round(snap.temp_bed_c, 1),
            target_bed_c=snap.target_bed_c,
            chamber_temperature_c=(
                round(snap.chamber_temperature_c, 1)
                if snap.chamber_temperature_c is not None
                else None
            ),
            chamber_target_c=snap.chamber_target_c,
            active_tool=snap.active_tool,
            toolheads=toolheads,
            last_validation=self.last_validation,
        )

    def validate_virtual_path(self, virtual_path: str) -> ValidationResult:
        os_path = self.transport.resolve_virtual_path(virtual_path)
        result = self.validator.validate(os_path, self.config, self.profile)
        self.last_validation = result
        self._validation_by_virtual_path[virtual_path] = result
        return result

    def inject_fault(self, state: const.State, reason: str) -> None:
        if state not in {const.State.ERROR, const.State.ATTENTION}:
            raise ValueError("Only ERROR or ATTENTION can be injected")
        self.transport.set_state(state, const.Source.HW, reason=reason)
        self.transport.event(const.Event.FAILED, const.Source.HW, reason=reason)

    def reset(self) -> None:
        self.simulator.reset()
        self.transport.set_state(const.State.READY, const.Source.FIRMWARE, ready=True)

    def _download_finished(self, transfer: Any) -> None:
        virtual_path = transfer.path
        if not virtual_path:
            return
        try:
            result = self.validator.validate(
                transfer.os_path,
                self.config,
                self.profile,
            )
        except Exception as exc:  # surface validation/parser failure to Connect
            log.exception("Validation crashed for %s", virtual_path)
            self.transport.set_state(const.State.ATTENTION, const.Source.FIRMWARE)
            self.transport.event(
                const.Event.FAILED,
                const.Source.FIRMWARE,
                reason=f"G-code validation error: {exc}",
                path=virtual_path,
            )
            return

        self.last_validation = result
        self._validation_by_virtual_path[virtual_path] = result
        if not result.valid:
            reason = "; ".join(issue.message for issue in result.issues[:5])
            self.transport.set_state(const.State.ATTENTION, const.Source.FIRMWARE)
            self.transport.event(
                const.Event.FAILED,
                const.Source.FIRMWARE,
                reason=f"G-code validation failed: {reason}",
                path=virtual_path,
                validation=result.model_dump(mode="json"),
            )
            return

        self.transport.set_state(const.State.READY, const.Source.FIRMWARE, ready=True)
        self.transport.event(
            const.Event.INFO,
            const.Source.FIRMWARE,
            path=virtual_path,
            validation={"valid": True, "profile_id": result.profile_id},
        )
        if transfer.to_print:
            self._start_validated_file(virtual_path)

    def _start_print(self, caller: Command) -> dict[str, Any]:
        virtual_path = self._command_path(caller)
        self._start_validated_file(virtual_path)
        return {"source": const.Source.CONNECT}

    def _start_validated_file(self, virtual_path: str) -> None:
        result = self._validation_by_virtual_path.get(virtual_path)
        if result is None:
            result = self.validate_virtual_path(virtual_path)
        if not result.valid:
            raise RuntimeError("Refusing START_PRINT: G-code validation failed")

        duration = result.metrics.get("estimated_print_duration")
        if not isinstance(duration, (int, float)) or duration <= 0:
            raise RuntimeError(
                "Refusing START_PRINT: approved profile must map a parseable estimated print duration"
            )

        temperature_values = self._metadata_numbers(
            result, ["temperature", "first_layer_temperature"]
        )
        tool_targets = self._values_by_tool(temperature_values, result.used_tools)
        target_bed = self._first_metadata_number(
            result, ["bed_temperature", "first_layer_bed_temperature"]
        )
        chamber_target = self._first_metadata_number(
            result, ["chamber_temperature"]
        )
        self.simulator.start(
            virtual_path,
            float(duration),
            used_tools=result.used_tools,
            tool_targets_c=tool_targets,
            target_bed_c=target_bed,
            chamber_target_c=chamber_target,
            filament_used_g=self._filament_usage_by_tool(result),
        )

    def _stop_print(self, caller: Command) -> dict[str, Any]:
        del caller
        self.simulator.stop()
        return {"source": const.Source.CONNECT}

    def _pause_print(self, caller: Command) -> dict[str, Any]:
        del caller
        self.simulator.pause()
        return {"source": const.Source.CONNECT}

    def _resume_print(self, caller: Command) -> dict[str, Any]:
        del caller
        self.simulator.resume()
        return {"source": const.Source.CONNECT}

    @staticmethod
    def _command_path(caller: Command) -> str:
        if caller.kwargs and caller.kwargs.get("path"):
            return str(caller.kwargs["path"])
        if caller.args and len(caller.args) > 0:
            return str(caller.args[0])
        raise ValueError("START_PRINT requires a virtual G-code path")

    @staticmethod
    def _metadata_numbers(
        result: ValidationResult, candidate_keys: list[str]
    ) -> list[float]:
        for key in candidate_keys:
            raw = result.metadata.get(normalize_key(key))
            if raw is not None:
                try:
                    return parse_number_sequence(raw)
                except ValueError:
                    continue
        return []

    @classmethod
    def _first_metadata_number(
        cls, result: ValidationResult, candidate_keys: list[str]
    ) -> float | None:
        values = cls._metadata_numbers(result, candidate_keys)
        return values[0] if values else None

    @staticmethod
    def _values_by_tool(values: list[float], used_tools: list[int]) -> dict[int, float]:
        if not values:
            return {}
        if len(values) == 1:
            return {slot: values[0] for slot in used_tools}
        return {slot: values[slot] for slot in used_tools if slot < len(values)}

    @staticmethod
    def _filament_usage_by_tool(result: ValidationResult) -> dict[int, float]:
        estimated = result.metrics.get("estimated_filament_weight")
        if isinstance(estimated, list):
            return {
                slot: float(weight)
                for slot, weight in enumerate(estimated)
                if isinstance(weight, (int, float)) and weight > 0
            }
        if isinstance(estimated, (int, float)) and len(result.used_tools) == 1:
            return {result.used_tools[0]: float(estimated)}
        return {}

    def _consume_filament(self, used_g: dict[int, float]) -> None:
        tools = {tool.slot: tool for tool in self.config.toolheads}
        for slot, amount in used_g.items():
            tool = tools.get(slot)
            if not tool or not tool.spool or tool.spool.remaining_g is None:
                continue
            tool.spool.remaining_g = max(0.0, tool.spool.remaining_g - amount)

    def _telemetry_loop(self) -> None:
        while not self._stop.is_set():
            snap = self.simulator.snapshot
            active = snap.toolheads.get(snap.active_tool) if snap.active_tool is not None else None
            payload: dict[str, Any] = {
                "temp_nozzle": round(active.temperature_c if active else 24.0, 1),
                "temp_bed": round(snap.temp_bed_c, 1),
            }
            if snap.current_file is not None:
                payload.update(
                    {
                        "progress": round(snap.progress_percent, 2),
                        "time_remaining": (
                            round(snap.time_remaining_s, 1)
                            if snap.time_remaining_s is not None
                            else None
                        ),
                    }
                )
            self.transport.telemetry(**payload)
            time.sleep(1.0)

    def _printed_os_path(self) -> str | None:
        virtual_path = self.simulator.snapshot.current_file
        if not virtual_path or not self.simulator.running:
            return None
        try:
            return str(Path(self.transport.resolve_virtual_path(virtual_path)).resolve())
        except Exception:
            return None
