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



def test_timeline_selection_event_flow_regression() -> None:
    view = (ROOT / "olden_db/desktop/views/planner_view.py").read_text()
    render_start = view.index("    def _render_timeline(")
    handler_start = view.index(
        "    def _handle_timeline_selection(", render_start
    )
    render_body = view[render_start:handler_start]

    assert "_timeline_item_id(step.identity)" in render_body
    assert "self._last_timeline_presentation = timeline" in render_body
    assert render_body.count(
        "self._last_timeline_presentation = timeline"
    ) == 1
    assert "first = str(timeline.steps[0].step_number)" not in render_body
    assert "selection_set(first)" not in render_body
    assert "_show_timeline_step_detail" not in view

    handler_end = view.index("    @staticmethod", handler_start)
    handler_body = view[handler_start:handler_end]
    assert "timeline = self._last_timeline_presentation" in handler_body
    assert "self._on_build_step_selected(step.identity)" in handler_body


def test_selection_reentrancy_is_bounded() -> None:
    presenter = (
        ROOT / "olden_db/desktop/presenters/planner_presenter.py"
    ).read_text()
    view = (ROOT / "olden_db/desktop/views/planner_view.py").read_text()

    selection_start = presenter.index(
        "    def on_build_step_selected("
    )
    selection_end = presenter.index(
        "    def on_build_step_selection_cleared(", selection_start
    )
    selection_body = presenter[selection_start:selection_end]
    assert "if self._selected_build_step == identity:" in selection_body
    assert selection_body.count("restore_build_step_focus(identity)") == 0

    restore_start = view.index("    def restore_build_step_focus(")
    restore_end = view.index("    def render_explanation(", restore_start)
    restore_body = view[restore_start:restore_end]
    assert "current = self._timeline_tree.selection()" in restore_body
    assert "if current != (item_id,):" in restore_body
    assert "self._timeline_tree.selection_set(item_id)" in restore_body

def main() -> None:
    for check in (
        test_identity_is_immutable,
        test_presenter_and_view_boundaries,
        test_timeline_selection_event_flow_regression,
        test_selection_reentrancy_is_bounded,
        test_syntax,
    ):
        check()
        print(f"PASS: {check.__name__}")


if __name__ == "__main__":
    main()
