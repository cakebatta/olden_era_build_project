from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TIMELINE = ROOT / "olden_db" / "desktop" / "planning_timeline.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"
WORKSPACE = ROOT / "olden_db" / "desktop" / "workspace_presentation.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_timeline_models_are_immutable() -> None:
    namespace: dict[str, object] = {}
    exec(source(TIMELINE), namespace)
    step_type = namespace["TimelineStepPresentation"]
    timeline_type = namespace["BuildPlanTimelinePresentation"]
    step = step_type(1, "Step 1 of 1", "Hall", "Level 1", "Date", "Cost", "Cost", "Completes first")
    timeline = timeline_type("Current Accepted Plan", None, (step,), False)
    try:
        timeline.result_status = "changed"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Timeline presentation must be frozen")


def test_authoritative_projection_and_localization() -> None:
    text = source(PRESENTER)
    for token in (
        "for step in result.plan.steps",
        "step.step_number",
        "step.date",
        "step.individual_cost",
        "step.cumulative_cost",
        "self._display_text(step.building)",
    ):
        require(token in text, f"Missing authoritative timeline token: {token}")
    require("sorted(result.plan.steps" not in text, "Presenter must not infer ordering")


def test_lifecycle_and_noop_behavior() -> None:
    presenter = source(PRESENTER)
    view = source(VIEW)
    require('"Previous Accepted Plan"' in presenter, "Retained label missing")
    require('"Current Accepted Plan"' in presenter, "Current label missing")
    require("timeline == self._last_timeline_presentation" in view, "No-op guard missing")
    require("self._timeline_tree.insert" in view, "Timeline rows not rendered")


def test_workspace_constructor_compatibility() -> None:
    require(
        "timeline: BuildPlanTimelinePresentation = EMPTY_BUILD_PLAN_TIMELINE"
        in source(WORKSPACE),
        "Timeline default missing",
    )


def test_view_does_not_localize_or_sort() -> None:
    tree = ast.parse(source(VIEW))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            function = node.func
            name = (
                function.attr if isinstance(function, ast.Attribute)
                else function.id if isinstance(function, ast.Name)
                else None
            )
            require(name not in {"get_building_display_text", "sorted"}, f"Passive view violation: {name}")


def test_syntax() -> None:
    for path in (TIMELINE, PRESENTER, VIEW, WORKSPACE):
        ast.parse(source(path), filename=str(path))


def main() -> None:
    items = [v for n, v in globals().items() if n.startswith("test_") and callable(v)]
    for item in items:
        item()
        print(f"PASS: {item.__name__}")
    print(f"PASS: {len(items)} focused UI-008 timeline checks")


if __name__ == "__main__":
    main()
