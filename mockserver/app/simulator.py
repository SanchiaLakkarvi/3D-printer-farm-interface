from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable

from prusa.connect.printer import const


@dataclass
class ToolSimulationSnapshot:
    slot: int
    state: str = "DOCKED"
    temperature_c: float = 24.0
    target_temperature_c: float | None = None


@dataclass
class SimulationSnapshot:
    phase: str = "IDLE"
    current_file: str | None = None
    progress_percent: float = 0.0
    estimated_duration_s: float | None = None
    elapsed_s: float = 0.0
    time_remaining_s: float | None = None
    temp_bed_c: float = 24.0
    target_bed_c: float | None = None
    chamber_temperature_c: float | None = None
    chamber_target_c: float | None = None
    active_tool: int | None = None
    toolheads: dict[int, ToolSimulationSnapshot] = field(default_factory=dict)


class PrintSimulator:
    def __init__(
        self,
        set_state: Callable[[const.State, const.Source], None],
        simulation_speed: float,
        tool_slots: list[int],
        chamber_supported: bool,
        on_finished: Callable[[dict[int, float]], None] | None = None,
    ):
        self._set_state = set_state
        self.simulation_speed = simulation_speed
        self._tool_slots = sorted(tool_slots)
        self._chamber_supported = chamber_supported
        self._on_finished = on_finished
        self.snapshot = self._new_snapshot()
        self._filament_used_g: dict[int, float] = {}
        self._used_tools: list[int] = []
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._thread: threading.Thread | None = None

    def _new_snapshot(self) -> SimulationSnapshot:
        return SimulationSnapshot(
            chamber_temperature_c=24.0 if self._chamber_supported else None,
            toolheads={slot: ToolSimulationSnapshot(slot=slot) for slot in self._tool_slots},
        )

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    @property
    def paused(self) -> bool:
        return self._pause.is_set()

    def start(
        self,
        virtual_path: str,
        estimated_duration_s: float,
        used_tools: list[int],
        tool_targets_c: dict[int, float],
        target_bed_c: float | None = None,
        chamber_target_c: float | None = None,
        filament_used_g: dict[int, float] | None = None,
    ) -> None:
        with self._lock:
            if self.running:
                raise RuntimeError("A print is already running")
            if estimated_duration_s <= 0:
                raise ValueError("Estimated print duration must be > 0")
            unknown_tools = set(used_tools) - set(self._tool_slots)
            if unknown_tools:
                raise ValueError(f"Unknown tool slots: {sorted(unknown_tools)}")
            self._stop.clear()
            self._pause.clear()
            self._used_tools = sorted(set(used_tools))
            self._filament_used_g = dict(filament_used_g or {})
            self.snapshot = self._new_snapshot()
            self.snapshot.phase = "PREHEATING"
            self.snapshot.current_file = virtual_path
            self.snapshot.estimated_duration_s = estimated_duration_s
            self.snapshot.time_remaining_s = estimated_duration_s
            self.snapshot.target_bed_c = target_bed_c
            self.snapshot.chamber_target_c = (
                chamber_target_c if self._chamber_supported else None
            )
            for slot in self._used_tools:
                tool = self.snapshot.toolheads[slot]
                tool.state = "PREHEATING"
                tool.target_temperature_c = tool_targets_c.get(slot)
            self.snapshot.active_tool = self._used_tools[0] if self._used_tools else None
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def pause(self) -> None:
        if not self.running:
            raise RuntimeError("No print is running")
        self._pause.set()
        self._set_state(const.State.PAUSED, const.Source.CONNECT)

    def resume(self) -> None:
        if not self.running:
            raise RuntimeError("No print is running")
        if not self._pause.is_set():
            raise RuntimeError("Print is not paused")
        self._pause.clear()
        self._set_state(const.State.PRINTING, const.Source.CONNECT)

    def stop(self) -> None:
        if not self.running:
            raise RuntimeError("No print is running")
        self._stop.set()

    def reset(self) -> None:
        if self.running:
            self._stop.set()
            if self._thread:
                self._thread.join(timeout=2)
        with self._lock:
            self._pause.clear()
            self.snapshot = self._new_snapshot()

    def _run(self) -> None:
        self._set_state(const.State.PRINTING, const.Source.CONNECT)
        last_tick = time.monotonic()
        while not self._stop.is_set() and not self._is_preheated():
            now = time.monotonic()
            if not self._pause.is_set():
                with self._lock:
                    self._ramp_temperatures((now - last_tick) * self.simulation_speed)
            last_tick = now
            time.sleep(0.1)

        if self._stop.is_set():
            self._finish_stopped()
            return

        with self._lock:
            self.snapshot.phase = "PRINTING"
            self._set_tool_states()

        started = time.monotonic()
        paused_total = 0.0
        pause_started: float | None = None
        while not self._stop.is_set():
            now = time.monotonic()
            if self._pause.is_set():
                if pause_started is None:
                    pause_started = now
                time.sleep(0.1)
                continue
            if pause_started is not None:
                paused_total += now - pause_started
                pause_started = None

            elapsed = max(0.0, now - started - paused_total) * self.simulation_speed
            duration = self.snapshot.estimated_duration_s or 1.0
            progress = min(100.0, elapsed / duration * 100.0)
            with self._lock:
                self.snapshot.elapsed_s = elapsed
                self.snapshot.progress_percent = progress
                self.snapshot.time_remaining_s = max(0.0, duration - elapsed)
                self._select_active_tool(progress)

            if progress >= 100.0:
                with self._lock:
                    self.snapshot.phase = "FINISHED"
                    self._clear_targets()
                if self._on_finished:
                    self._on_finished(dict(self._filament_used_g))
                self._set_state(const.State.FINISHED, const.Source.FIRMWARE)
                return
            time.sleep(0.1)

        self._finish_stopped()

    def _is_preheated(self) -> bool:
        with self._lock:
            targets = [
                (tool.temperature_c, tool.target_temperature_c)
                for slot, tool in self.snapshot.toolheads.items()
                if slot in self._used_tools
            ]
            targets.extend(
                [
                    (self.snapshot.temp_bed_c, self.snapshot.target_bed_c),
                    (
                        self.snapshot.chamber_temperature_c,
                        self.snapshot.chamber_target_c,
                    ),
                ]
            )
            return all(
                target is None or (current is not None and abs(target - current) <= 0.5)
                for current, target in targets
            )

    def _ramp_temperatures(self, simulated_delta_s: float) -> None:
        for slot in self._used_tools:
            tool = self.snapshot.toolheads[slot]
            tool.temperature_c = self._approach(
                tool.temperature_c, tool.target_temperature_c, 8.0 * simulated_delta_s
            )
        self.snapshot.temp_bed_c = self._approach(
            self.snapshot.temp_bed_c,
            self.snapshot.target_bed_c,
            3.0 * simulated_delta_s,
        )
        if self.snapshot.chamber_temperature_c is not None:
            self.snapshot.chamber_temperature_c = self._approach(
                self.snapshot.chamber_temperature_c,
                self.snapshot.chamber_target_c,
                0.5 * simulated_delta_s,
            )

    @staticmethod
    def _approach(current: float, target: float | None, delta: float) -> float:
        if target is None:
            return current
        return current + max(-delta, min(delta, target - current))

    def _select_active_tool(self, progress: float) -> None:
        if not self._used_tools:
            self.snapshot.active_tool = None
            return
        index = min(int(progress / 100 * len(self._used_tools)), len(self._used_tools) - 1)
        self.snapshot.active_tool = self._used_tools[index]
        self._set_tool_states()

    def _set_tool_states(self) -> None:
        for slot, tool in self.snapshot.toolheads.items():
            if slot == self.snapshot.active_tool:
                tool.state = "ACTIVE"
            elif slot in self._used_tools:
                tool.state = "STANDBY"
            else:
                tool.state = "DOCKED"

    def _clear_targets(self) -> None:
        self.snapshot.target_bed_c = None
        self.snapshot.chamber_target_c = None
        self.snapshot.active_tool = None
        for tool in self.snapshot.toolheads.values():
            tool.target_temperature_c = None
            tool.state = "DOCKED"

    def _finish_stopped(self) -> None:
        with self._lock:
            self.snapshot.phase = "STOPPED"
            self._clear_targets()
        self._set_state(const.State.STOPPED, const.Source.CONNECT)
