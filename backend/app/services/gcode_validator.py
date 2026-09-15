from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.printer import Printer
from app.services.gcode_parser import (
    TextGCodeParseError,
    ValidationError,
    parse_gcode,
    validate_file_format,
)

SUPPORTED_PROFILES: dict[str, dict[str, Any]] = {
    "core_one_hf04": {
        "display_name": "Prusa CORE One HF0.4 nozzle",
        "printer_model": "COREONE",
        "printer_variant": "HF0.4",
        "printer_settings_keywords": ["CORE One", "HF0.4"],
        "nozzle_diameter": [0.4],
        "nozzle_high_flow": [1],
        "allow_abrasive": False,
        "required_features": {"input shaper"},
        "build_volume_mm": (250.0, 220.0, 270.0),
        "max_nozzle_temperature": 290.0,
        "max_bed_temperature": 120.0,
    },
    "xl_5t_is_04": {
        "display_name": "Original Prusa XL - 5T Input Shaper 0.4 nozzle",
        "printer_model": "XL5IS",
        "printer_variant": "0.4",
        "printer_settings_keywords": ["XL", "5T", "Input Shaper", "0.4"],
        "nozzle_diameter": [0.4, 0.4, 0.4, 0.4, 0.4],
        "nozzle_high_flow": None,
        "allow_abrasive": False,
        "required_features": {"input shaper"},
        "build_volume_mm": (360.0, 360.0, 360.0),
        "max_nozzle_temperature": 290.0,
        "max_bed_temperature": 120.0,
    },
}


def _csv_floats(value: str | None) -> list[float]:
    if not value:
        return []
    parts = re.split(r"[,;]", value)
    try:
        return [float(part.strip()) for part in parts if part.strip()]
    except ValueError:
        return []


def _csv_ints(value: str | None) -> list[int]:
    if not value:
        return []
    parts = re.split(r"[,;]", value)
    try:
        return [int(float(part.strip())) for part in parts if part.strip()]
    except ValueError:
        return []


def _same_floats(actual: list[float], expected: list[float]) -> bool:
    return len(actual) == len(expected) and all(abs(a - b) <= 1e-6 for a, b in zip(actual, expected))


def _single_float(value: str | None, field_name: str) -> float:
    values = _csv_floats(value)
    if len(values) != 1:
        raise ValidationError(f"{field_name} must contain exactly one numeric value; got {value!r}.")
    return values[0]


def _parse_bed_shape(value: str | None) -> tuple[float, float, float, float]:
    if not value:
        raise ValidationError("bed_shape metadata is missing.")
    points = re.findall(r"(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)", value)
    if len(points) < 3:
        raise ValidationError(f"Cannot parse bed_shape={value!r}.")
    xs = [float(x) for x, _ in points]
    ys = [float(y) for _, y in points]
    return min(xs), min(ys), max(xs), max(ys)


def _object_xy_bounds(objects_info: str | None) -> tuple[float, float, float, float] | None:
    if not objects_info:
        return None
    try:
        data = json.loads(objects_info)
    except json.JSONDecodeError:
        return None

    points: list[tuple[float, float]] = []

    def add_pairs(value: Any) -> None:
        if isinstance(value, list):
            if (
                len(value) >= 2
                and isinstance(value[0], (int, float))
                and isinstance(value[1], (int, float))
            ):
                points.append((float(value[0]), float(value[1])))
                return
            for item in value:
                add_pairs(item)
        elif isinstance(value, dict):
            for subvalue in value.values():
                add_pairs(subvalue)

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for key, subvalue in value.items():
                key_lower = key.lower()
                if any(token in key_lower for token in ("polygon", "bounding_box", "convex_hull", "object_center")):
                    add_pairs(subvalue)
                elif key_lower == "objects":
                    visit(subvalue)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    if not points:
        return None

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _validate_temperature_list(
    value: str | None,
    field_name: str,
    maximum: float,
    allow_zero: bool = False,
) -> list[float]:
    if value in (None, ""):
        return []
    values = _csv_floats(value)
    if not values:
        raise ValidationError(f"Cannot parse {field_name}={value!r}.")

    for temp in values:
        if temp < 0 or (temp == 0 and not allow_zero):
            raise ValidationError(f"{field_name} contains invalid temperature {temp}°C.")
        if temp > maximum:
            raise ValidationError(
                f"{field_name}={temp}°C exceeds configured printer maximum {maximum}°C."
            )
    return values


def _first_value(parsed: Any, *keys: str) -> str | None:
    for mapping in (parsed.printer_metadata, parsed.slicer_metadata, parsed.print_metadata, parsed.file_metadata):
        for key in keys:
            value = mapping.get(key)
            if value not in (None, ""):
                return value
    return None


def _check_metadata_consistency(parsed: Any) -> None:
    if parsed.kind != "TEXT":
        return

    critical = {
        "printer_model",
        "printer_variant",
        "printer_settings_id",
        "nozzle_diameter",
        "nozzle_high_flow",
        "filament_type",
        "filament_abrasive",
        "bed_shape",
        "max_print_height",
        "max_layer_z",
    }
    numeric_csv_keys = {"nozzle_diameter", "nozzle_high_flow", "filament_abrasive", "max_print_height", "max_layer_z"}
    conflicts: list[str] = []

    for key in critical:
        values = [value.strip() for value in parsed.metadata_history.get(key, []) if value.strip()]
        if not values:
            continue
        if key in numeric_csv_keys:
            normalized_numeric: set[tuple[float, ...]] = set()
            parse_failed = False
            for value in values:
                parsed_values = _csv_floats(value)
                if not parsed_values:
                    parse_failed = True
                    break
                normalized_numeric.add(tuple(round(x, 8) for x in parsed_values))
            if parse_failed:
                normalized = set(values)
                if len(normalized) > 1:
                    conflicts.append(f"{key}={sorted(normalized)!r}")
            elif len(normalized_numeric) > 1:
                conflicts.append(f"{key}={values!r}")
        else:
            normalized = set(values)
            if len(normalized) > 1:
                conflicts.append(f"{key}={sorted(normalized)!r}")

    if conflicts:
        raise ValidationError("Conflicting critical metadata was found in the G-code: " + "; ".join(conflicts))


def extract_metadata(parsed: Any) -> dict[str, str | None]:
    _check_metadata_consistency(parsed)

    detected = {
        "producer": _first_value(parsed, "Producer", "producer"),
        "printer_model": _first_value(parsed, "printer_model"),
        "printer_variant": _first_value(parsed, "printer_variant"),
        "printer_settings_id": _first_value(parsed, "printer_settings_id"),
        "printer_technology": _first_value(parsed, "printer_technology"),
        "print_settings_id": _first_value(parsed, "print_settings_id"),
        "nozzle_diameter": _first_value(parsed, "nozzle_diameter"),
        "nozzle_high_flow": _first_value(parsed, "nozzle_high_flow"),
        "filament_type": _first_value(parsed, "filament_type"),
        "filament_abrasive": _first_value(parsed, "filament_abrasive"),
        "filament_colour": _first_value(parsed, "filament_colour"),
        "filament_settings_id": _first_value(parsed, "filament_settings_id"),
        "bed_shape": _first_value(parsed, "bed_shape"),
        "max_print_height": _first_value(parsed, "max_print_height"),
        "max_layer_z": _first_value(parsed, "max_layer_z"),
        "objects_info": _first_value(parsed, "objects_info"),
        "temperature": _first_value(parsed, "temperature"),
        "bed_temperature": _first_value(parsed, "bed_temperature"),
        "first_layer_temperature": _first_value(parsed, "first_layer_temperature"),
        "first_layer_bed_temperature": _first_value(parsed, "first_layer_bed_temperature"),
        "layer_height": _first_value(parsed, "layer_height"),
        "estimated_print_time": _first_value(parsed, "estimated printing time (normal mode)", "estimated printing time"),
        "filament_used_g": _first_value(parsed, "total filament used [g]", "filament used [g]"),
        "filament_used_mm": _first_value(parsed, "filament used [mm]"),
        "filament_used_cm3": _first_value(parsed, "filament used [cm3]"),
        "filament_cost": _first_value(parsed, "filament cost"),
    }

    required = (
        "printer_model",
        "printer_variant",
        "printer_settings_id",
        "nozzle_diameter",
        "filament_type",
        "filament_abrasive",
        "bed_shape",
        "max_print_height",
        "max_layer_z",
    )
    missing = [key for key in required if not detected.get(key)]
    if missing:
        raise ValidationError("Required printer/material/build metadata is missing: " + ", ".join(missing) + ".")

    return detected


def validate_m862_cross_check(
    metadata: dict[str, str | None],
    executable: Any,
    profile: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []

    if not executable.m862_1:
        errors.append("Missing M862.1 nozzle compatibility command.")
    if not executable.m862_3_models:
        errors.append("Missing M862.3 printer-model compatibility command.")
    if not executable.m862_5_levels:
        errors.append("Missing M862.5 G-code-level compatibility command.")
    if not executable.m862_6_features:
        errors.append("Missing M862.6 firmware-feature compatibility command.")

    metadata_model = metadata.get("printer_model")
    if executable.m862_3_models and metadata_model not in executable.m862_3_models:
        errors.append(
            f"M862.3 model {executable.m862_3_models!r} does not match metadata printer_model={metadata_model!r}."
        )

    metadata_nozzles = _csv_floats(metadata.get("nozzle_diameter"))
    m862_nozzles = [
        entry["nozzle_diameter"] for entry in executable.m862_1 if entry.get("nozzle_diameter") is not None
    ]
    if metadata_nozzles and m862_nozzles:
        expected_set = {round(x, 6) for x in metadata_nozzles}
        command_set = {round(float(x), 6) for x in m862_nozzles}
        if not command_set.issubset(expected_set):
            errors.append(
                f"M862.1 nozzle values {sorted(command_set)!r} do not agree with metadata nozzle_diameter={metadata_nozzles!r}."
            )

    abrasive_meta = _csv_ints(metadata.get("filament_abrasive"))
    high_flow_meta = _csv_ints(metadata.get("nozzle_high_flow"))

    for entry in executable.m862_1:
        if entry.get("abrasive") is not None and abrasive_meta:
            if entry["abrasive"] not in abrasive_meta:
                errors.append(
                    f"M862.1 abrasive flag A{entry['abrasive']} disagrees with filament_abrasive={abrasive_meta!r}."
                )
        if entry.get("high_flow") is not None and high_flow_meta:
            if entry["high_flow"] not in high_flow_meta:
                errors.append(
                    f"M862.1 high-flow flag F{entry['high_flow']} disagrees with nozzle_high_flow={high_flow_meta!r}."
                )

    required_features = {feature.lower() for feature in profile.get("required_features", set())}
    actual_features = {feature.lower() for feature in executable.m862_6_features}
    missing_features = sorted(required_features - actual_features)
    if missing_features:
        errors.append("Missing required M862.6 feature check(s): " + ", ".join(missing_features))

    if errors:
        raise ValidationError(" ".join(errors))

    return {
        "m862_1": executable.m862_1,
        "m862_3_models": executable.m862_3_models,
        "m862_5_levels": executable.m862_5_levels,
        "m862_6_features": executable.m862_6_features,
    }


def _match_profile(metadata: dict[str, str | None], profile_id: str) -> tuple[bool, list[str], dict[str, Any]]:
    expected = SUPPORTED_PROFILES[profile_id]
    reasons: list[str] = []
    details: dict[str, Any] = {}

    model = metadata.get("printer_model")
    variant = metadata.get("printer_variant")
    settings_id = metadata.get("printer_settings_id") or ""
    nozzles = _csv_floats(metadata.get("nozzle_diameter"))
    high_flow = _csv_ints(metadata.get("nozzle_high_flow"))
    abrasive = _csv_ints(metadata.get("filament_abrasive"))

    if model != expected["printer_model"]:
        reasons.append(f"printer_model={model!r}; expected {expected['printer_model']!r}")
    if variant != expected["printer_variant"]:
        reasons.append(f"printer_variant={variant!r}; expected {expected['printer_variant']!r}")
    if not _same_floats(nozzles, expected["nozzle_diameter"]):
        reasons.append(f"nozzle_diameter={nozzles}; expected {expected['nozzle_diameter']}")

    expected_hf = expected["nozzle_high_flow"]
    if expected_hf is not None and high_flow != expected_hf:
        reasons.append(f"nozzle_high_flow={high_flow}; expected {expected_hf}")

    for keyword in expected.get("printer_settings_keywords", []):
        if keyword.lower() not in settings_id.lower():
            reasons.append(f"printer_settings_id={settings_id!r} is missing keyword {keyword!r}")

    if not expected.get("allow_abrasive", True) and any(value != 0 for value in abrasive):
        reasons.append(
            "filament_abrasive indicates an abrasive material, but this configured standard nozzle profile does not allow abrasive filament."
        )

    try:
        bed_min_x, bed_min_y, bed_max_x, bed_max_y = _parse_bed_shape(metadata.get("bed_shape"))
        bed_width = bed_max_x - bed_min_x
        bed_depth = bed_max_y - bed_min_y
        profile_x, profile_y, profile_z = expected["build_volume_mm"]
        details["bed_shape_mm"] = [bed_width, bed_depth]
        details["printer_build_volume_mm"] = list(expected["build_volume_mm"])

        if bed_width > profile_x + 1e-6 or bed_depth > profile_y + 1e-6:
            reasons.append(f"bed_shape {bed_width}x{bed_depth} mm exceeds printer build area {profile_x}x{profile_y} mm.")

        max_print_height = _single_float(metadata.get("max_print_height"), "max_print_height")
        max_layer_z = _single_float(metadata.get("max_layer_z"), "max_layer_z")
        details["max_print_height_mm"] = max_print_height
        details["job_max_layer_z_mm"] = max_layer_z

        if max_print_height > profile_z + 1e-6:
            reasons.append(f"max_print_height={max_print_height} mm exceeds printer Z={profile_z} mm.")
        if max_layer_z > profile_z + 1e-6:
            reasons.append(f"max_layer_z={max_layer_z} mm exceeds printer Z={profile_z} mm.")

        object_bounds = _object_xy_bounds(metadata.get("objects_info"))
        if object_bounds is not None:
            min_x, min_y, max_x, max_y = object_bounds
            details["object_xy_bounds_mm"] = [min_x, min_y, max_x, max_y]
            if min_x < bed_min_x - 1e-6 or min_y < bed_min_y - 1e-6 or max_x > bed_max_x + 1e-6 or max_y > bed_max_y + 1e-6:
                reasons.append("Object XY bounds fall outside the G-code bed_shape.")
    except ValidationError as exc:
        reasons.append(str(exc))

    try:
        details["temperature_c"] = _validate_temperature_list(metadata.get("temperature"), "temperature", expected["max_nozzle_temperature"])
        details["first_layer_temperature_c"] = _validate_temperature_list(metadata.get("first_layer_temperature"), "first_layer_temperature", expected["max_nozzle_temperature"])
        details["bed_temperature_c"] = _validate_temperature_list(metadata.get("bed_temperature"), "bed_temperature", expected["max_bed_temperature"], allow_zero=True)
        details["first_layer_bed_temperature_c"] = _validate_temperature_list(metadata.get("first_layer_bed_temperature"), "first_layer_bed_temperature", expected["max_bed_temperature"], allow_zero=True)
    except ValidationError as exc:
        reasons.append(str(exc))

    return not reasons, reasons, details


def check_both_printers(metadata: dict[str, str | None]) -> tuple[dict[str, dict[str, Any]], list[str]]:
    checks: dict[str, dict[str, Any]] = {}
    matches: list[str] = []

    for profile_id, profile in SUPPORTED_PROFILES.items():
        matched, reasons, details = _match_profile(metadata, profile_id)
        checks[profile_id] = {
            "printer": profile["display_name"],
            "matched": matched,
            "result": "MATCH" if matched else "NO_MATCH",
            "reasons": reasons,
            "details": details,
        }
        if matched:
            matches.append(profile_id)

    return checks, matches


def _not_checked_printers(reason: str) -> dict[str, dict[str, Any]]:
    return {
        profile_id: {
            "printer": profile["display_name"],
            "matched": False,
            "result": "NOT_CHECKED",
            "reasons": [reason],
        }
        for profile_id, profile in SUPPORTED_PROFILES.items()
    }


def _stage(number: int, name: str, status: str, **details: Any) -> dict[str, Any]:
    result = {"stage": number, "name": name, "status": status}
    if details:
        result["details"] = details
    return result


def _failure(
    *,
    path: Path,
    stage_number: int,
    stages: list[dict[str, Any]],
    message: str,
    error: str,
    printer_checks: dict[str, dict[str, Any]] | None = None,
    detected: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "FAIL",
        "passed": False,
        "failed_stage": stage_number,
        "file": path.name,
        "message": message,
        "errors": [error],
        "validation_stages": stages,
        "printer_checks": printer_checks if printer_checks is not None else _not_checked_printers("Not checked because an earlier validation stage failed."),
        "compatible_profiles": [],
        "compatible_printers": [],
        "next_step": "UPLOAD_GCODE",
    }
    if detected is not None:
        result["detected"] = detected
    return result


def validate_upload(path: str | Path) -> dict[str, Any]:
    path = Path(path)
    stages: list[dict[str, Any]] = []
    temp_dir: Path | None = None

    try:
        try:
            fmt = validate_file_format(path)
        except (OSError, ValidationError) as exc:
            stages.append(_stage(1, "FILE_FORMAT_VALIDATION", "FAIL", reason=str(exc)))
            return _failure(path=path, stage_number=1, stages=stages, message="Invalid G-code file format.", error=str(exc))

        stages.append(_stage(1, "FILE_FORMAT_VALIDATION", "PASS", detected_format="BGCODE" if fmt.kind == "BINARY" else "GCODE", extension=fmt.extension))

        try:
            parsed, executable, temp_dir = parse_gcode(path, fmt)
        except (OSError, UnicodeDecodeError, ValidationError, TextGCodeParseError) as exc:
            stages.append(_stage(2, "PARSE_AND_INTEGRITY", "FAIL", reason=str(exc)))
            return _failure(path=path, stage_number=2, stages=stages, message="G-code could not be parsed or failed integrity validation.", error=str(exc))

        if executable is None:
            stages.append(
                _stage(
                    2,
                    "PARSE_AND_INTEGRITY",
                    "PASS",
                    parsed_format=parsed.kind,
                    gcode_blocks_or_commands=parsed.gcode_blocks,
                    integrity_ok=parsed.integrity_ok,
                )
            )
        else:
            stages.append(
                _stage(
                    2,
                    "PARSE_AND_INTEGRITY",
                    "PASS",
                    parsed_format=parsed.kind,
                    gcode_blocks_or_commands=parsed.gcode_blocks,
                    integrity_ok=parsed.integrity_ok,
                    config_complete=executable.config_complete,
                    safe_end=executable.safe_end,
                    warnings=executable.warnings,
                )
            )

        try:
            metadata = extract_metadata(parsed)
        except ValidationError as exc:
            stages.append(_stage(3, "READ_METADATA", "FAIL", reason=str(exc)))
            return _failure(path=path, stage_number=3, stages=stages, message="Required printer/material/build metadata could not be read.", error=str(exc))

        stages.append(
            _stage(
                3,
                "READ_METADATA",
                "PASS",
                printer_model=metadata.get("printer_model"),
                printer_variant=metadata.get("printer_variant"),
                printer_settings_id=metadata.get("printer_settings_id"),
                nozzle_diameter=metadata.get("nozzle_diameter"),
                nozzle_high_flow=metadata.get("nozzle_high_flow"),
                filament_type=metadata.get("filament_type"),
                filament_abrasive=metadata.get("filament_abrasive"),
                max_layer_z=metadata.get("max_layer_z"),
            )
        )

        printer_checks, candidate_matches = check_both_printers(metadata)

        if len(candidate_matches) == 0:
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "NOT_CHECKED", reason="No printer profile matched the metadata."))
            stages.append(_stage(5, "CHECK_BOTH_PRINTERS", "PASS", printers_checked=list(SUPPORTED_PROFILES.keys()), matching_profiles=[]))
            stages.append(_stage(6, "SUPPORTED_PRINTER_MATCH", "FAIL", reason="Neither supported printer profile matched."))
            return _failure(
                path=path,
                stage_number=6,
                stages=stages,
                message="G-code is structurally valid, but it is not compatible with either supported printer profile. Re-slice for CORE One HF0.4 or XL 5T Input Shaper 0.4.",
                error="Neither supported printer profile matched the uploaded G-code.",
                printer_checks=printer_checks,
                detected=metadata,
            )

        if len(candidate_matches) > 1:
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "NOT_CHECKED", reason="Metadata matches more than one profile."))
            stages.append(_stage(5, "CHECK_BOTH_PRINTERS", "PASS", printers_checked=list(SUPPORTED_PROFILES.keys()), matching_profiles=candidate_matches))
            stages.append(_stage(6, "SUPPORTED_PRINTER_MATCH", "FAIL", reason="More than one printer profile matched; definitions are ambiguous."))
            return _failure(
                path=path,
                stage_number=6,
                stages=stages,
                message="Printer profile definitions are ambiguous.",
                error="More than one supported printer profile matched.",
                printer_checks=printer_checks,
                detected=metadata,
            )

        candidate_profile = candidate_matches[0]

        if executable is None:
            exc = ValidationError("Executable-command validation is unavailable for this BGCode file.")
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "FAIL", reason=str(exc)))
            return _failure(path=path, stage_number=4, stages=stages, message="Could not verify executable printer compatibility commands.", error=str(exc), printer_checks=printer_checks, detected=metadata)

        try:
            m862_details = validate_m862_cross_check(metadata, executable, SUPPORTED_PROFILES[candidate_profile])
        except ValidationError as exc:
            stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "FAIL", reason=str(exc)))
            return _failure(path=path, stage_number=4, stages=stages, message="G-code metadata does not agree with executable compatibility checks.", error=str(exc), printer_checks=printer_checks, detected=metadata)

        stages.append(_stage(4, "M862_EXECUTABLE_CROSS_CHECK", "PASS", **m862_details))
        stages.append(_stage(5, "CHECK_BOTH_PRINTERS", "PASS", printers_checked=list(SUPPORTED_PROFILES.keys()), matching_profiles=candidate_matches))

        matched_profile = candidate_profile
        matched_printer = SUPPORTED_PROFILES[matched_profile]["display_name"]
        stages.append(_stage(6, "SUPPORTED_PRINTER_MATCH", "PASS", compatible_profile=matched_profile, compatible_printer=matched_printer))

        return {
            "status": "PASS",
            "passed": True,
            "file": path.name,
            "format": "BGCODE" if fmt.kind == "BINARY" else "GCODE",
            "message": "G-code validation passed. Continue to compatible printer selection.",
            "detected": metadata,
            "validation_stages": stages,
            "printer_checks": printer_checks,
            "compatible_profiles": [matched_profile],
            "compatible_printers": [matched_printer],
            "compatible_profile": matched_profile,
            "compatible_printer": matched_printer,
            "required_material": metadata.get("filament_type"),
            "slicer_filament_colour": metadata.get("filament_colour"),
            "estimated_print_time": metadata.get("estimated_print_time"),
            "filament_used_g": metadata.get("filament_used_g"),
            "next_step": "SELECT_PRINTER",
        }
    finally:
        if temp_dir is not None:
            import shutil as _shutil
            _shutil.rmtree(temp_dir, ignore_errors=True)


validate_gcode = validate_upload
