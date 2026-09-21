from __future__ import annotations

from typing import Any

from .gcode_metadata import (
    normalize_key,
    parse_duration_seconds,
    parse_gcode_document,
    parse_number,
    parse_number_sequence,
    split_sequence,
)
from .gcode_commands import analyze_commands
from .models import (
    ApprovedProfile,
    ExpectedFrom,
    PrinterConfig,
    RuleOperator,
    ValidationIssue,
    ValidationResult,
    ValidationRule,
)


class GCodeValidator:
    def __init__(self, tail_bytes: int):
        self.tail_bytes = tail_bytes

    def validate(
        self,
        file_path: str,
        printer: PrinterConfig,
        profile: ApprovedProfile,
    ) -> ValidationResult:
        document = parse_gcode_document(file_path, self.tail_bytes)
        metadata = document.metadata
        issues: list[ValidationIssue] = []

        for rule in profile.rules:
            issue = self._apply_rule(rule, metadata, printer)
            if issue is not None:
                issues.append(issue)

        command_analysis = analyze_commands(document.commands, printer, profile)
        issues.extend(command_analysis.issues)

        metrics = self._extract_metrics(metadata, profile)
        issues.extend(
            self._check_filament_stock(
                metrics, printer, profile, command_analysis.used_tools
            )
        )
        return ValidationResult(
            valid=not issues,
            file_path=file_path,
            profile_id=profile.id,
            file_format=document.format,
            used_tools=sorted(command_analysis.used_tools),
            metadata=metadata,
            metrics=metrics,
            issues=issues,
        )

    def _expected(self, rule: ValidationRule, printer: PrinterConfig) -> Any:
        if rule.expected_from == ExpectedFrom.GCODE_PRINTER_MODEL:
            return printer.gcode_printer_model
        if rule.expected_from == ExpectedFrom.TOOL_MATERIALS:
            return [tool.spool.material if tool.spool else "" for tool in printer.toolheads]
        if rule.expected_from == ExpectedFrom.NOZZLE_DIAMETERS:
            return [tool.nozzle_diameter_mm for tool in printer.toolheads]
        if rule.expected_from == ExpectedFrom.NOZZLE_HIGH_FLOW:
            return [int(tool.high_flow) for tool in printer.toolheads]
        return rule.expected

    def _norm(self, value: Any, rule: ValidationRule) -> Any:
        if not isinstance(value, str):
            return value
        result = value.strip()
        if rule.remove_all_whitespace:
            result = "".join(result.split())
        if not rule.case_sensitive:
            result = result.casefold()
        return result

    def _apply_rule(
        self,
        rule: ValidationRule,
        metadata: dict[str, str],
        printer: PrinterConfig,
    ) -> ValidationIssue | None:
        key = normalize_key(rule.metadata_key)
        actual = metadata.get(key)
        expected = self._expected(rule, printer)

        if actual is None or actual == "":
            if rule.required:
                return ValidationIssue(
                    rule_id=rule.id,
                    metadata_key=rule.metadata_key,
                    message="Required G-code metadata is missing",
                    actual=actual,
                    expected=expected,
                )
            return None

        if rule.operator == RuleOperator.PRESENT:
            return None

        if rule.operator == RuleOperator.EQUALS:
            if self._norm(actual, rule) != self._norm(str(expected), rule):
                return self._mismatch(rule, actual, expected)
            return None

        if rule.operator == RuleOperator.ONE_OF:
            values = expected if isinstance(expected, list) else [expected]
            normalized = [self._norm(str(value), rule) for value in values]
            if self._norm(actual, rule) not in normalized:
                return self._mismatch(rule, actual, expected)
            return None

        if rule.operator == RuleOperator.NUMERIC_RANGE:
            try:
                numeric = parse_number(actual)
            except ValueError as exc:
                return ValidationIssue(
                    rule_id=rule.id,
                    metadata_key=rule.metadata_key,
                    message=str(exc),
                    actual=actual,
                    expected={"min": rule.min_value, "max": rule.max_value},
                )
            if rule.min_value is not None and numeric < rule.min_value:
                return self._mismatch(
                    rule, numeric, {"min": rule.min_value, "max": rule.max_value}
                )
            if rule.max_value is not None and numeric > rule.max_value:
                return self._mismatch(
                    rule, numeric, {"min": rule.min_value, "max": rule.max_value}
                )
            return None

        if rule.operator == RuleOperator.SEQUENCE_EQUALS:
            actual_parts = [self._norm(part, rule) for part in split_sequence(actual)]
            expected_values = expected if isinstance(expected, list) else split_sequence(str(expected))
            expected_parts = [self._norm(str(part), rule) for part in expected_values]
            if actual_parts != expected_parts:
                return self._mismatch(rule, actual_parts, expected_parts)
            return None

        return ValidationIssue(
            rule_id=rule.id,
            metadata_key=rule.metadata_key,
            message=f"Unsupported operator: {rule.operator}",
            actual=actual,
            expected=expected,
        )

    @staticmethod
    def _mismatch(rule: ValidationRule, actual: Any, expected: Any) -> ValidationIssue:
        return ValidationIssue(
            rule_id=rule.id,
            metadata_key=rule.metadata_key,
            message=rule.description or "G-code setting does not match approved printer/profile configuration",
            actual=actual,
            expected=expected,
        )

    @staticmethod
    def _extract_metrics(metadata: dict[str, str], profile: ApprovedProfile) -> dict[str, Any]:
        metrics: dict[str, Any] = {}
        mapping = profile.metrics.model_dump()
        for metric_name, metadata_key in mapping.items():
            if not metadata_key:
                continue
            raw = metadata.get(normalize_key(metadata_key))
            if raw is None:
                metrics[metric_name] = None
                continue
            value: Any = raw
            try:
                if metric_name == "estimated_print_duration":
                    value = parse_duration_seconds(raw)
                elif metric_name in {
                    "estimated_filament_usage",
                    "filament_length",
                    "filament_density",
                    "estimated_filament_weight",
                }:
                    parts = split_sequence(raw)
                    value = parse_number_sequence(raw) if len(parts) > 1 else parse_number(raw)
            except ValueError:
                value = raw
            metrics[metric_name] = value
        return metrics

    @staticmethod
    def _check_filament_stock(
        metrics: dict[str, Any],
        printer: PrinterConfig,
        profile: ApprovedProfile,
        used_tools: set[int],
    ) -> list[ValidationIssue]:
        estimated = metrics.get("estimated_filament_weight")
        if not isinstance(estimated, (int, float, list)):
            return []

        tools = {tool.slot: tool for tool in printer.toolheads}
        required_by_slot: dict[int, float]
        if isinstance(estimated, list):
            required_by_slot = {
                slot: float(weight)
                for slot, weight in enumerate(estimated)
                if isinstance(weight, (int, float)) and weight > 0
            }
        else:
            if len(used_tools) > 1:
                return [
                    ValidationIssue(
                        rule_id="filament-weight-per-tool",
                        metadata_key=profile.metrics.estimated_filament_weight or "",
                        message="Multi-tool G-code must report filament weight per tool",
                        actual=estimated,
                        expected={"tool_slots": sorted(used_tools)},
                    )
                ]
            slot = next(iter(used_tools), 0)
            required_by_slot = {slot: float(estimated)}

        issues: list[ValidationIssue] = []
        for slot, required_g in required_by_slot.items():
            tool = tools.get(slot)
            available_g = tool.spool.remaining_g if tool and tool.spool else None
            if available_g is not None and required_g > available_g:
                issues.append(
                    ValidationIssue(
                        rule_id=f"filament-stock-tool-{slot}",
                        metadata_key=profile.metrics.estimated_filament_weight or "",
                        message="Estimated filament weight exceeds the tracked spool remainder",
                        actual={"slot": slot, "required_g": required_g},
                        expected={"slot": slot, "max_g": available_g},
                    )
                )
        return issues
