"""Pricing service implementing client's pricing formula:
$2.00 for the first hour + $0.50 for each additional hour (pro-rated).
"""

from __future__ import annotations


def calculate_print_cost(duration_min: float | None) -> float:
    """Calculate USD cost for a print job based on duration in minutes.

    Formula:
    - Duration <= 0 or None: $0.00
    - Duration <= 60 min (1 hour): $2.00
    - Duration > 60 min: $2.00 + ((duration_min - 60) / 60) * $0.50
    Result rounded to 2 decimal places.
    """
    if duration_min is None or duration_min <= 0:
        return 0.0

    if duration_min <= 60.0:
        return 2.00

    additional_hours = (duration_min - 60.0) / 60.0
    cost = 2.00 + (additional_hours * 0.50)
    return round(cost, 2)
