from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "olden_db" / "desktop" / "build_plan_comparison_presentation.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "build_plan_comparison_presenter.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "build_plan_comparison_view.py"
COLLECTION_PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "scenario_comparison_workspace_presenter.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_presentation_models_are_immutable() -> None:
    namespace = {}
    exec(MODEL.read_text(encoding="utf-8"), namespace)
    status = namespace["ComparisonPresentationStatus"].UNAVAILABLE
    value = namespace["BuildPlanComparisonPresentation"](
        status=status,
        heading="Unavailable",
        detail="Waiting",
    )
    try:
        value.heading = "Changed"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Comparison presentation must be immutable")


def test_presenter_consumes_authoritative_backend_contracts() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require(
        "self._service.compare_accepted_build_plans(" in text,
        "Presenter must call the BE-013 Query Layer operation",
    )
    for forbidden in (
        "_align_steps",
        "_lcs_matches",
        "compare_build_plans(",
        "final_cumulative_cost_delta=",
        "step_count_delta=",
    ):
        require(forbidden not in text, f"Presenter duplicates comparison logic: {forbidden}")


def test_backend_order_and_relationships_are_projected_directly() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require(
        "for item in comparison.step_comparisons" in text,
        "Aligned backend order must be consumed directly",
    )
    require(
        "_RELATIONSHIP_TEXT[item.relationship]" in text,
        "Backend relationships must drive presentation",
    )
    require("sorted(" not in text, "Presenter must not reorder comparison facts")


def test_retained_comparison_lifecycle() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require("self._last_successful" in text, "Successful comparison retention missing")
    require("retained_previous_comparison=True" in text, "Pending retained state missing")
    require(
        "if left_base.accepted_result is None or right_base.accepted_result is None" in text,
        "Unavailable accepted-result lifecycle missing",
    )


def test_view_is_passive_and_accessible() -> None:
    text = VIEW.read_text(encoding="utf-8")
    for forbidden in (
        "compare_accepted_build_plans",
        "ResourceCost",
        "BuildStepRelationship",
    ):
        require(forbidden not in text, f"View exposes backend behavior: {forbidden}")
    require('selectmode="browse"' in text, "Keyboard row selection missing")
    require("yscrollcommand=scrollbar.set" in text, "Long-plan scrolling missing")


def test_collection_presenter_integrates_automatic_updates() -> None:
    text = COLLECTION_PRESENTER.read_text(encoding="utf-8")
    require("BuildPlanComparisonPresenter(" in text, "Comparison presenter not composed")
    require("ComparisonAwarePlannerPresenter(" in text, "Completion notification not composed")
    require(
        "self._build_plan_comparison_presenter.refresh()" in text,
        "Automatic comparison refresh missing",
    )


def test_syntax() -> None:
    for path in (MODEL, PRESENTER, VIEW, COLLECTION_PRESENTER):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def main() -> None:
    checks = [
        value for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for check in checks:
        check()
        print(f"PASS: {check.__name__}")
    print(f"PASS: {len(checks)} focused UI-010 comparison checks")


if __name__ == "__main__":
    main()
