"""Pydantic response schemas for Admin + Basic Usage Reporting endpoints.

Each schema maps to one of the 5 reporting endpoints and includes both
KPI card values and chart-ready data series for the frontend dashboard.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------------------
# Shared chart data models
# ---------------------------------------------------------------------------

class TimeSeriesPoint(BaseModel):
    """Single data point for line charts (Jobs Over Time, Filament Over Time)."""
    date: str       # ISO date string, e.g. "2026-09-01"
    count: int      # job count or filament grams (int for simplicity)


class StatusBreakdown(BaseModel):
    """Single slice for the Job Status donut/pie chart."""
    status: str     # e.g. "completed", "failed", "queued"
    count: int


# ---------------------------------------------------------------------------
# Report 1: Overall Farm Usage  (GET /api/reports/usage)
# ---------------------------------------------------------------------------

class OverallUsageResponse(BaseModel):
    """KPI cards + chart data for the overall farm summary."""

    # KPI cards
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    cancelled_jobs: int            # status == "removed"
    active_queued_jobs: int        # submitted + queued + printing
    success_rate_pct: float        # (completed / total) * 100
    total_print_hours: float       # rounded to 2 dp
    total_filament_g: float        # grams; frontend converts to kg
    avg_print_duration_min: float  # average across all jobs

    # Chart: Jobs Over Time (line chart)
    jobs_over_time: list[TimeSeriesPoint]
    # Chart: Job Status Breakdown (donut/pie chart)
    status_breakdown: list[StatusBreakdown]


# ---------------------------------------------------------------------------
# Report 2: Printer Utilization & Hardware  (GET /api/reports/printers)
# ---------------------------------------------------------------------------

class PrinterReportItem(BaseModel):
    """One row in the printer utilization table + bar chart data."""
    model_config = ConfigDict(from_attributes=True)

    printer_id: uuid.UUID
    model: str
    location: str | None = None
    status: str                    # current printer status
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_print_hours: float
    total_filament_g: float
    utilization_pct: float         # (printer_hours / farm_hours) * 100
    queue_length: int              # live count of waiting jobs


# ---------------------------------------------------------------------------
# Report 3: Material & Filament Consumption  (GET /api/reports/materials)
# ---------------------------------------------------------------------------

class MaterialReportItem(BaseModel):
    """One row in the material consumption table + bar chart data."""
    model_config = ConfigDict(from_attributes=True)

    material_id: uuid.UUID
    material_name: str
    type: str                      # PLA, PETG, ABS, TPU
    colour: str
    total_jobs: int
    total_filament_g: float


class MaterialReportResponse(BaseModel):
    """Wraps per-material items plus time-series for the line chart."""
    materials: list[MaterialReportItem]
    # Chart: Filament Usage Over Time (line chart, grams per day)
    filament_over_time: list[TimeSeriesPoint]


# ---------------------------------------------------------------------------
# Report 4: User & Student Usage  (GET /api/reports/users)
# ---------------------------------------------------------------------------

class UserReportItem(BaseModel):
    """One row in the searchable/sortable user activity table."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    first_name: str
    last_name: str
    email: str
    student_number: str | None = None
    department: str | None = None
    role: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_print_hours: float
    total_filament_g: float


# ---------------------------------------------------------------------------
# Report 5: Department Usage  (GET /api/reports/departments)
# ---------------------------------------------------------------------------

class DepartmentReportItem(BaseModel):
    """One row in the department cost-allocation table + bar chart data."""

    department: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    total_print_hours: float
    total_filament_g: float
