from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class RuleOperator(str, Enum):
    PRESENT = "present"
    EQUALS = "equals"
    ONE_OF = "one_of"
    NUMERIC_RANGE = "numeric_range"
    SEQUENCE_EQUALS = "sequence_equals"


class ExpectedFrom(str, Enum):
    LITERAL = "literal"
    GCODE_PRINTER_MODEL = "gcode_printer_model"
    TOOL_MATERIALS = "tool_materials"
    NOZZLE_DIAMETERS = "nozzle_diameters"
    NOZZLE_HIGH_FLOW = "nozzle_high_flow"


class ValidationRule(BaseModel):
    id: str
    metadata_key: str
    operator: RuleOperator
    required: bool = True
    expected_from: ExpectedFrom = ExpectedFrom.LITERAL
    expected: Any | None = None
    min_value: float | None = None
    max_value: float | None = None
    case_sensitive: bool = False
    remove_all_whitespace: bool = False
    description: str | None = None

    @model_validator(mode="after")
    def check_rule(self) -> "ValidationRule":
        if self.operator == RuleOperator.NUMERIC_RANGE:
            if self.min_value is None and self.max_value is None:
                raise ValueError("numeric_range needs min_value and/or max_value")
        if (
            self.expected_from == ExpectedFrom.LITERAL
            and self.operator in {RuleOperator.EQUALS, RuleOperator.ONE_OF, RuleOperator.SEQUENCE_EQUALS}
            and self.expected is None
        ):
            raise ValueError(f"rule {self.id} needs expected")
        return self


class MetricKeys(BaseModel):
    estimated_print_duration: str | None = None
    estimated_filament_usage: str | None = None
    filament_length: str | None = None
    filament_density: str | None = None
    estimated_filament_weight: str | None = None


class BuildVolume(BaseModel):
    x: float = Field(gt=0)
    y: float = Field(gt=0)
    z: float = Field(gt=0)


class CommandPolicy(BaseModel):
    firmware_model: str
    input_shaper_required: bool = True
    build_volume_mm: BuildVolume
    max_nozzle_temperature_c: float = Field(gt=0)
    max_bed_temperature_c: float = Field(gt=0)
    max_chamber_temperature_c: float | None = Field(default=None, gt=0)
    motion_min_x_mm: float = -10
    motion_min_y_mm: float = -10
    motion_min_z_mm: float = 0
    forbidden_commands: list[str] = Field(
        default_factory=lambda: ["M42", "M500", "M502", "M997"]
    )


class ApprovedProfile(BaseModel):
    id: str
    enabled: bool = True
    physical_models: list[str]
    rules: list[ValidationRule] = Field(default_factory=list)
    metrics: MetricKeys = Field(default_factory=MetricKeys)
    command_policy: CommandPolicy


class SpoolConfig(BaseModel):
    material: str
    colour: str | None = None
    remaining_g: float | None = Field(default=None, ge=0)


class ToolheadConfig(BaseModel):
    slot: int = Field(ge=0)
    nozzle_diameter_mm: float = Field(gt=0)
    high_flow: bool = False
    spool: SpoolConfig | None = None


class SdkIdentity(BaseModel):
    """Synthetic SDK identity for the Python SDK transport.

    The current SDK enum does not contain XL/CORE One. These values must not be
    interpreted as the physical printer model. For mock instances a clearly
    synthetic value such as 0.0.0 is acceptable; the backend should identify a
    printer by its registered fingerprint/token and its own printer registry.
    """

    type: int = 0
    version: int = 0
    subversion: int = 0
    header: str = "MOCK"


class PrinterConfig(BaseModel):
    id: str
    enabled: bool = True
    serial_number: str
    fingerprint: str
    token: str
    physical_model: str
    gcode_printer_model: str
    approved_profile_id: str
    storage_dir: str
    chamber_supported: bool = False
    toolheads: list[ToolheadConfig]
    simulation_speed: float = Field(default=60.0, gt=0)
    sdk_identity: SdkIdentity = Field(default_factory=SdkIdentity)

    @model_validator(mode="after")
    def validate_hardware_layout(self) -> "PrinterConfig":
        slots = [tool.slot for tool in self.toolheads]
        if len(slots) != len(set(slots)):
            raise ValueError(f"printer {self.id} toolhead slots must be unique")
        if self.gcode_printer_model == "XL5IS":
            if sorted(slots) != list(range(5)):
                raise ValueError(f"printer {self.id} XL5IS requires tool slots 0..4")
            if any(tool.nozzle_diameter_mm != 0.4 or tool.high_flow for tool in self.toolheads):
                raise ValueError(
                    f"printer {self.id} XL5IS profile requires five standard-flow 0.4 mm nozzles"
                )
        elif self.gcode_printer_model == "COREONE":
            if slots != [0]:
                raise ValueError(f"printer {self.id} COREONE requires exactly tool slot 0")
            tool = self.toolheads[0]
            if tool.nozzle_diameter_mm != 0.4 or not tool.high_flow:
                raise ValueError(
                    f"printer {self.id} COREONE HF0.4 profile requires one high-flow 0.4 mm nozzle"
                )
            if not self.chamber_supported:
                raise ValueError(f"printer {self.id} COREONE must enable chamber support")
        return self


class ConnectConfig(BaseModel):
    server: str


class AppConfig(BaseModel):
    connect: ConnectConfig
    printers: list[PrinterConfig]
    approved_profiles: list[ApprovedProfile]
    gcode_tail_bytes: int = Field(default=2 * 1024 * 1024, ge=4096)

    @model_validator(mode="after")
    def validate_references(self) -> "AppConfig":
        supported_hardware = {
            "PRUSA_XL_5T_INPUT_SHAPER": ("XL5IS", "XL"),
            "PRUSA_CORE_ONE": ("COREONE", "COREONE"),
        }
        profiles = {p.id: p for p in self.approved_profiles}
        if len(profiles) != len(self.approved_profiles):
            raise ValueError("approved profile ids must be unique")
        printer_ids = [p.id for p in self.printers]
        if len(set(printer_ids)) != len(printer_ids):
            raise ValueError("printer ids must be unique")
        for printer in self.printers:
            profile = profiles.get(printer.approved_profile_id)
            if profile is None:
                raise ValueError(
                    f"printer {printer.id} references unknown profile {printer.approved_profile_id}"
                )
            if printer.enabled and not profile.enabled:
                raise ValueError(
                    f"printer {printer.id} references disabled profile {profile.id}"
                )
            if printer.physical_model not in profile.physical_models:
                raise ValueError(
                    f"printer {printer.id} model {printer.physical_model} is not allowed by profile {profile.id}"
                )
            expected_identity = supported_hardware.get(printer.physical_model)
            if expected_identity is not None:
                gcode_model, firmware_model = expected_identity
                if printer.gcode_printer_model != gcode_model:
                    raise ValueError(
                        f"printer {printer.id} must use G-code model {gcode_model}"
                    )
                if profile.command_policy.firmware_model != firmware_model:
                    raise ValueError(
                        f"profile {profile.id} must check firmware model {firmware_model}"
                    )
        return self


class ValidationIssue(BaseModel):
    rule_id: str
    metadata_key: str
    message: str
    actual: Any | None = None
    expected: Any | None = None


class ValidationResult(BaseModel):
    valid: bool
    file_path: str
    profile_id: str
    file_format: Literal["ascii", "binary"]
    used_tools: list[int]
    metadata: dict[str, str]
    metrics: dict[str, Any]
    issues: list[ValidationIssue]


class ToolheadStatus(BaseModel):
    slot: int
    state: str
    nozzle_diameter_mm: float
    high_flow: bool
    temperature_c: float
    target_temperature_c: float | None
    material: str | None
    colour: str | None
    filament_remaining_g: float | None


class PrinterStatus(BaseModel):
    id: str
    physical_model: str
    state: str
    current_file: str | None
    progress_percent: float
    estimated_duration_s: float | None
    elapsed_s: float
    time_remaining_s: float | None
    temp_bed_c: float
    target_bed_c: float | None
    chamber_temperature_c: float | None
    chamber_target_c: float | None
    active_tool: int | None
    toolheads: list["ToolheadStatus"]
    last_validation: ValidationResult | None


class FaultRequest(BaseModel):
    state: Literal["ERROR", "ATTENTION"] = "ERROR"
    reason: str


class ConsumableUpdate(BaseModel):
    slot: int = Field(ge=0)
    material: str | None = None
    colour: str | None = None
    remaining_g: float | None = Field(default=None, ge=0)
