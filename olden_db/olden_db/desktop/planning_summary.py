from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DailyScheduleRowPresentation:
    date_text: str
    building_text: str
    cost_text: str


@dataclass(frozen=True, slots=True)
class PlanningSummaryPresentation:
    lifecycle_status: str
    result_status: str
    faction_text: str | None
    target_text: str | None
    starting_date_text: str | None
    displayed_result_target_text: str | None
    step_count_text: str | None
    completion_date_text: str | None
    total_cost_text: str | None
    daily_schedule_rows: tuple[DailyScheduleRowPresentation, ...]
    diagnostic_summary: str
    failure_message: str | None
    missing_inputs_text: str | None
    is_retained_previous_result: bool
