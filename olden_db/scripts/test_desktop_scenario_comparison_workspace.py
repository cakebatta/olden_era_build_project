from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

from olden_db.scenario_comparison import ScenarioComparisonCollection

ROOT = Path(__file__).resolve().parents[1]
PRESENTATION = ROOT / "olden_db" / "desktop" / "scenario_comparison_presentation.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "scenario_comparison_workspace_presenter.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_collection_presentation_models_are_immutable() -> None:
    namespace: dict[str, object] = {}
    exec(PRESENTATION.read_text(encoding="utf-8"), namespace)
    collection = ScenarioComparisonCollection.create()
    workspace_id = collection.workspace_ids[0]
    member = namespace["ScenarioComparisonMemberPresentation"](
        workspace_id,
        0,
        "Scenario 1",
        None,
        "identity",
        False,
    )
    value = namespace["ScenarioComparisonPresentation"](
        0,
        (member,),
        None,
        None,
    )
    try:
        value.collection_revision = 1
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("comparison presentation must be frozen")


def test_backend_collection_operations_are_used() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    for token in (
        "self._collection.create_workspace()",
        "self._collection.duplicate_workspace(",
        "self._collection.remove_workspace(workspace_id)",
        "self._collection.set_label(workspace_id, resolved)",
        "self._collection.set_comparison_role",
        "self._collection.snapshot()",
    ):
        require(token in text, f"missing backend operation: {token}")


def test_presenter_composes_existing_workspace_components() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require("ScenarioAwarePlannerPresenter(" in text, "existing presenter not reused")
    require("PlannerState()" in text, "independent planner state missing")
    require("create_workspace_panel" in text, "existing planner view not composed")
    require("generate_planner_result" not in text, "collection presenter performs planning")


def test_role_changes_do_not_execute() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    start = text.index("    def on_role_changed(")
    end = text.index("    def refresh(", start)
    require("_coordinator.execute" not in text[start:end], "role change triggered planning")


def test_view_is_passive() -> None:
    text = VIEW.read_text(encoding="utf-8")
    for forbidden in (
        "generate_planner_result",
        "PlanningWorkspace.create",
        "duplicate_workspace(",
        "remove_workspace(",
    ):
        require(forbidden not in text, f"view owns backend behavior: {forbidden}")


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused UI-009 comparison workspace checks")


if __name__ == "__main__":
    main()
