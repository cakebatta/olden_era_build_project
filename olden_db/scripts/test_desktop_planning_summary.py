from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = ROOT / "olden_db" / "desktop" / "planning_summary.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"
FORMATTING = ROOT / "olden_db" / "desktop" / "formatting.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_summary_models_are_immutable() -> None:
    namespace: dict[str, object] = {}
    exec(source(SUMMARY), namespace)
    row_type = namespace["DailyScheduleRowPresentation"]
    summary_type = namespace["PlanningSummaryPresentation"]
    row = row_type("Day", "Building", "gold: 1")
    summary = summary_type(
        "ready", "Current Accepted Plan", "faction", "target", "date",
        "target", "1 construction step", "date", "gold: 1", (row,),
        "No diagnostics requiring attention.", None, None, False,
    )
    try:
        summary.result_status = "changed"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Summary presentation must be frozen")


def test_authoritative_contracts_are_consumed() -> None:
    text = source(PRESENTER)
    require("result.daily_construction_schedule" in text, "BE-011 schedule not consumed")
    require("get_building_display_text" in text, "BE-011 localization not consumed")
    require("item.cost" in text, "Authoritative schedule cost not formatted")
    require("item.date" in text, "Authoritative schedule date not formatted")
    require("item.building" in text, "Authoritative schedule building not localized")


def test_lifecycle_and_retained_labels() -> None:
    text = source(PRESENTER)
    for token in (
        "PlanningExecutionStatus.PENDING",
        "PlanningExecutionStatus.READY",
        "PlanningExecutionStatus.FAILED",
        '"Previous Accepted Plan"',
        '"Current Accepted Plan"',
        '"No accepted plan"',
    ):
        require(token in text, f"Missing summary lifecycle token: {token}")


def test_equivalent_presentations_are_suppressed() -> None:
    text = source(PRESENTER)
    require(
        "presentation != self._last_workspace_presentation" in text,
        "Equivalent presentation no-op guard missing",
    )
    require(
        "self._last_workspace_presentation = presentation" in text,
        "Presentation cache not updated",
    )


def test_view_renders_only_presentation_values() -> None:
    view_path = (
        ROOT
        / "olden_db"
        / "desktop"
        / "views"
        / "planner_view.py"
    )
    text = view_path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    forbidden_attributes = {
        "accepted_plan",
        "plan",
        "completion_date",
        "total_cost",
        "daily_construction_schedule",
    }
    forbidden_calls = {"get_building_display_text"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            require(
                node.attr not in forbidden_attributes,
                f"View derives authoritative value: {node.attr}",
            )
        if isinstance(node, ast.Call):
            function = node.func
            called_name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id
                if isinstance(function, ast.Name)
                else None
            )
            require(
                called_name not in forbidden_calls,
                f"View resolves localization directly: {called_name}",
            )

    require(
        "summary.completion_date_text" in text,
        "View must render supplied completion-date presentation text",
    )
    require(
        "summary.total_cost_text" in text,
        "View must render supplied total-cost presentation text",
    )
    require(
        "summary.daily_schedule_rows" in text,
        "View must render supplied daily-schedule presentation rows",
    )



def test_formatting_helpers_exist() -> None:
    text = source(FORMATTING)
    require("def format_step_count" in text, "Step-count formatter missing")
    require("def format_diagnostic_summary" in text, "Diagnostic summary formatter missing")


def test_syntax() -> None:
    for path in (SUMMARY, PRESENTER, VIEW, FORMATTING):
        ast.parse(source(path), filename=str(path))


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused UI-007 summary checks")


if __name__ == "__main__":
    main()
