from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

from olden_db.desktop.build_plan_explanation import BuildStepIdentity
from olden_db.models import BuildingKey
from olden_db.planning_workspace import DEFAULT_BASE_PLAN_ID

ROOT = Path(__file__).resolve().parents[1]


def test_identity_is_immutable() -> None:
    identity = BuildStepIdentity(
        DEFAULT_BASE_PLAN_ID, 2, 1, BuildingKey("demon", "dwelling_1", 1)
    )
    try:
        identity.step_number = 4
    except FrozenInstanceError:
        return
    raise AssertionError("BuildStepIdentity must be frozen")


def test_presenter_and_view_boundaries() -> None:
    presenter = (ROOT / "olden_db/desktop/presenters/planner_presenter.py").read_text()
    view = (ROOT / "olden_db/desktop/views/planner_view.py").read_text()
    timeline = (ROOT / "olden_db/desktop/planning_timeline.py").read_text()
    workspace = (ROOT / "olden_db/desktop/workspace_presentation.py").read_text()
    assert "generate_objective_plan_view" in presenter
    assert "_reconcile_build_step_selection" in presenter
    assert "on_build_step_selected" in view
    assert "generate_objective_plan_view" not in view
    assert "identity: BuildStepIdentity" in timeline
    assert "explanation: BuildPlanExplanationPresentation" in workspace
    for forbidden in ("build_dependency_graph", "iter_topological_orders"):
        assert forbidden not in presenter
        assert forbidden not in view


def test_syntax() -> None:
    for relative in (
        "olden_db/desktop/build_plan_explanation.py",
        "olden_db/desktop/planning_timeline.py",
        "olden_db/desktop/workspace_presentation.py",
        "olden_db/desktop/presenters/planner_presenter.py",
        "olden_db/desktop/views/planner_view.py",
    ):
        path = ROOT / relative
        ast.parse(path.read_text(), filename=str(path))


def main() -> None:
    for check in (test_identity_is_immutable, test_presenter_and_view_boundaries, test_syntax):
        check()
        print(f"PASS: {check.__name__}")


if __name__ == "__main__":
    main()
