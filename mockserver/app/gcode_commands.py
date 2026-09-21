from __future__ import annotations

import re
from dataclasses import dataclass, field

from .models import ApprovedProfile, PrinterConfig, ValidationIssue

_COMMAND = re.compile(
    r"^(?:N\d+\s+)?([GMT]\d+(?:\.\d+)?|T\d+|P\d+)\b", re.IGNORECASE
)
_PARAM = re.compile(r"\b([A-Z])\s*([-+]?\d+(?:\.\d+)?)", re.IGNORECASE)


@dataclass
class CommandAnalysis:
    issues: list[ValidationIssue] = field(default_factory=list)
    used_tools: set[int] = field(default_factory=set)


def analyze_commands(
    commands: str,
    printer: PrinterConfig,
    profile: ApprovedProfile,
) -> CommandAnalysis:
    policy = profile.command_policy
    issues: dict[str, ValidationIssue] = {}
    tools = {tool.slot: tool for tool in printer.toolheads}
    used_tools: set[int] = set()
    nozzle_checks: dict[int, tuple[float | None, int | None]] = {}
    firmware_model: str | None = None
    input_shaper = False
    absolute = True
    position = {"X": 0.0, "Y": 0.0, "Z": 0.0}
    forbidden_commands = {item.upper() for item in policy.forbidden_commands}

    def add(rule_id: str, message: str, actual=None, expected=None) -> None:
        issues.setdefault(
            rule_id,
            ValidationIssue(
                rule_id=rule_id,
                metadata_key="gcode",
                message=message,
                actual=actual,
                expected=expected,
            ),
        )

    for line_number, raw_line in enumerate(commands.splitlines(), start=1):
        code = raw_line.split(";", 1)[0].strip()
        match = _COMMAND.match(code)
        if not match:
            continue
        command = match.group(1).upper()
        params = {name.upper(): float(value) for name, value in _PARAM.findall(code)}

        if command in forbidden_commands:
            add(
                "forbidden-command",
                "G-code contains a command forbidden by the approved profile",
                {"line": line_number, "command": command},
                policy.forbidden_commands,
            )
        if command == "G90":
            absolute = True
        elif command == "G91":
            absolute = False
        elif command == "G92":
            for axis in position:
                if axis in params:
                    position[axis] = params[axis]
        elif command in {"G0", "G1", "G2", "G3"}:
            for axis in position:
                if axis not in params:
                    continue
                value = params[axis] if absolute else position[axis] + params[axis]
                position[axis] = value
                minimum = getattr(policy, f"motion_min_{axis.lower()}_mm")
                maximum = getattr(policy.build_volume_mm, axis.lower())
                if value < minimum or value > maximum:
                    add(
                        f"motion-bound-{axis.lower()}",
                        f"{axis}-axis movement exceeds the approved machine envelope",
                        {"line": line_number, "value": value},
                        {"min": minimum, "max": maximum},
                    )

        if command in {"M104", "M109"}:
            if "T" in params:
                used_tools.add(int(params["T"]))
            target = params.get("S", params.get("R"))
            if target is not None and target > policy.max_nozzle_temperature_c:
                add(
                    "nozzle-temperature-limit",
                    "Nozzle target exceeds the printer hardware limit",
                    {"line": line_number, "value": target},
                    policy.max_nozzle_temperature_c,
                )
        elif command in {"M140", "M190"}:
            target = params.get("S", params.get("R"))
            if target is not None and target > policy.max_bed_temperature_c:
                add(
                    "bed-temperature-limit",
                    "Bed target exceeds the printer hardware limit",
                    {"line": line_number, "value": target},
                    policy.max_bed_temperature_c,
                )
        elif command in {"M141", "M191"}:
            target = params.get("S", params.get("R"))
            limit = policy.max_chamber_temperature_c
            if target is not None and (limit is None or target > limit):
                add(
                    "chamber-temperature-limit",
                    "Chamber target is not supported by the approved printer profile",
                    {"line": line_number, "value": target},
                    limit,
                )

        if command.startswith("T") and command[1:].isdigit():
            used_tools.add(int(command[1:]))
        elif command == "M862.1":
            slot = int(params.get("T", 0))
            nozzle_checks[slot] = (params.get("P"), int(params["F"]) if "F" in params else None)
        elif command == "M862.3":
            model = re.search(r"\bP\s*[\"']?([^\s\"']+)", code, re.IGNORECASE)
            if model:
                firmware_model = model.group(1)
        elif command == "M862.6":
            feature = re.search(r"\bP\s*[\"']?([^\"']+)", code, re.IGNORECASE)
            if feature and feature.group(1).strip().casefold() == "input shaper":
                input_shaper = True

    if printer.gcode_printer_model == "COREONE":
        used_tools.add(0)
    for slot in used_tools:
        tool = tools.get(slot)
        if tool is None:
            add(
                "unknown-tool",
                "G-code references a toolhead that is not installed",
                slot,
                sorted(tools),
            )
            continue
        check = nozzle_checks.get(slot)
        if check is None:
            add(
                "missing-nozzle-check",
                "Used toolhead has no M862.1 nozzle compatibility check",
                slot,
                {"diameter": tool.nozzle_diameter_mm, "high_flow": tool.high_flow},
            )
            continue
        diameter, high_flow = check
        if diameter != tool.nozzle_diameter_mm or high_flow != int(tool.high_flow):
            add(
                "nozzle-command-mismatch",
                "M862.1 nozzle check does not match the installed toolhead",
                {"slot": slot, "diameter": diameter, "high_flow": high_flow},
                {
                    "slot": slot,
                    "diameter": tool.nozzle_diameter_mm,
                    "high_flow": int(tool.high_flow),
                },
            )

    if firmware_model != policy.firmware_model:
        add(
            "firmware-model-command",
            "M862.3 printer compatibility check is missing or incorrect",
            firmware_model,
            policy.firmware_model,
        )
    if policy.input_shaper_required and not input_shaper:
        add(
            "input-shaper-command",
            "M862.6 Input Shaper compatibility check is missing",
            None,
            "Input shaper",
        )
    return CommandAnalysis(issues=list(issues.values()), used_tools=used_tools)
