"""Pydantic schemas for Print Queue, History, and Farm Statistics endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import JobStatus, PrinterStatus


class PrinterAssignedSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model: str
    location: str | None = None
    status: PrinterStatus


class QueueTileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    filename: str
    status: JobStatus
    assigned_printer: PrinterAssignedSummary | None = None
    est_duration_min: float | None = None
    est_duration_formatted: str
    est_start_time: datetime | None = None
    est_completion_time: datetime | None = None
    duration_is_default: bool = False
    submitted_at: datetime


class PrintHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    filename: str
    status: JobStatus
    material_name: str | None = None
    material_type: str | None = None
    colour: str | None = None
    printer_model: str | None = None
    printer_location: str | None = None
    department: str | None = None
    est_duration_min: float | None = None
    actual_duration_min: float | None = None
    est_filament_g: float | None = None
    actual_filament_g: float | None = None
    calculated_cost_usd: float
    submitted_at: datetime
    completed_at: datetime | None = None


class PrinterUtilStat(BaseModel):
    printer_id: uuid.UUID
    model: str
    location: str | None = None
    total_jobs: int
    total_hours: float
    utilization_pct: float


class MaterialUtilStat(BaseModel):
    material_id: uuid.UUID | None = None
    material_name: str
    type: str
    total_jobs: int
    total_filament_g: float


class DepartmentUtilStat(BaseModel):
    department: str
    total_jobs: int
    total_revenue_usd: float


class FarmStatisticsResponse(BaseModel):
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    active_queued_jobs: int
    total_revenue_usd: float
    total_print_time_hours: float
    total_filament_consumed_g: float
    printer_stats: list[PrinterUtilStat]
    material_stats: list[MaterialUtilStat]
    department_stats: list[DepartmentUtilStat]

