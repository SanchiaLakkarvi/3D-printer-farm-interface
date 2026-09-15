from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FormatResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["TEXT", "BINARY"]
    extension: str


class BinaryGCodeBlock(BaseModel):
    model_config = ConfigDict(extra="allow")

    block_type: int
    compression: int
    uncompressed_size: int
    compressed_size: int
    params: bytes
    payload: bytes
    crc_ok: bool


class ParsedGCode(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["TEXT", "BINARY"]
    file_metadata: dict[str, str] = Field(default_factory=dict)
    printer_metadata: dict[str, str] = Field(default_factory=dict)
    print_metadata: dict[str, str] = Field(default_factory=dict)
    slicer_metadata: dict[str, str] = Field(default_factory=dict)
    gcode_blocks: int = 0
    integrity_ok: bool = False
    metadata_history: dict[str, list[str]] = Field(default_factory=dict)
    m862_1: list[dict[str, Any]] = Field(default_factory=list)
    m862_3_models: list[str] = Field(default_factory=list)
    m862_5_levels: list[int] = Field(default_factory=list)
    m862_6_features: list[str] = Field(default_factory=list)
    config_begin_count: int = 0
    config_end_count: int = 0
    config_complete: bool = False
    safe_end: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ValidationCheckResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    printer: str
    matched: bool
    result: str
    reasons: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class GCodeValidationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str = "FAIL"
    passed: bool = False
    failed_stage: int | None = None
    file: str = ""
    message: str = ""
    errors: list[str] = Field(default_factory=list)
    validation_stages: list[dict[str, Any]] = Field(default_factory=list)
    printer_checks: dict[str, ValidationCheckResult] | dict[str, Any] = Field(default_factory=dict)
    compatible_profiles: list[str] = Field(default_factory=list)
    compatible_printers: list[str] = Field(default_factory=list)
    compatible_profile: str | None = None
    compatible_printer: str | None = None
    required_material: str | None = None
    slicer_filament_colour: str | None = None
    estimated_print_time: str | None = None
    filament_used_g: str | None = None
    next_step: str | None = None
    detected: dict[str, Any] = Field(default_factory=dict)

    def __getitem__(self, item: str) -> Any:
        return self.model_dump().get(item)

    def get(self, item: str, default: Any = None) -> Any:
        return self.model_dump().get(item, default)
