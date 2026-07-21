from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "olden_db" / "desktop" / "app.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
SCENARIO = ROOT / "olden_db" / "desktop" / "scenario_presenters.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"
PRESENTATION = ROOT / "olden_db" / "desktop" / "workspace_presentation.py"
QUERY = ROOT / "olden_db" / "query.py"
PLANNER = ROOT / "olden_db" / "planner.py"


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_application_owns_single_comparison_collection_and_coordinator() -> None:
    text = source(APP)
    require(
        text.count("ScenarioComparisonCollection.create()") == 1,
        "Exactly one application-scoped comparison collection required",
    )
    require(
        text.count("ScenarioComparisonExecutionCoordinator(") == 1,
        "Exactly one comparison execution coordinator required",
    )
    require(
        "PlanningWorkspace.create()" not in text,
        "Application must not construct workspaces outside the collection",
    )
    require(
        "self.planning_workspace = (" in text
        and "self.scenario_comparison_collection.workspace(" in text,
        "Primary compatibility workspace must resolve from the collection",
    )


def test_presenter_uses_workspace_orchestration() -> None:
    text = source(PRESENTER)
    require("PlanningSelection(" in text, "Semantic selection missing")
    require("self._workspace.replace_selection(" in text, "Workspace update missing")
    require("self._execution_coordinator.execute(" in text, "Coordinator execution missing")
    require("generate_planner_result(" not in text, "Presenter must not plan directly")
    require("get_prerequisite_statuses(" not in text, "Presenter must not compute prerequisites")
    require("enumerate_build_orders(" not in text, "Presenter must not duplicate planner logic")


def test_semantic_changes_trigger_planning() -> None:
    text = source(PRESENTER)
    for method in (
        "on_level_changed",
        "on_starting_date_changed",
        "on_starting_building_changed",
        "on_reset_scenario",
    ):
        start = text.index(f"    def {method}")
        end = text.find("\n    def ", start + 8)
        block = text[start:end if end != -1 else None]
        require("self._submit_current_selection()" in block, f"{method} must replan")


def test_compound_restore_executes_once() -> None:
    text = source(PRESENTER)
    start = text.index("    def apply_semantic_selection")
    end = text.index("    def _selection_became_incomplete", start)
    block = text[start:end]
    require(block.count("self._submit_current_selection()") == 1, "Restore must execute once")
    require("self.apply_semantic_selection(" in source(SCENARIO), "Scenario restore must batch")


def test_workspace_states_rendered() -> None:
    text = source(PRESENTER)
    for token in (
        "PlanningExecutionStatus.PENDING",
        "PlanningExecutionStatus.READY",
        "PlanningExecutionStatus.FAILED",
        "base.retains_previous_result",
        "base.result_is_current",
    ):
        require(token in text, f"Missing lifecycle handling: {token}")


def test_view_is_passive_and_generate_is_hidden() -> None:
    text = source(VIEW)
    require("render_workspace(" in text, "View must render presentation model")
    require("self._generate_button.grid_remove()" in text, "Generate must be hidden")
    require("Plans update automatically" in text, "Automatic planning guidance missing")
    for forbidden in ("PlanningWorkspace(", "PlanningExecutionCoordinator(", "generate_planner_result("):
        require(forbidden not in text, f"View boundary violation: {forbidden}")


def test_no_backend_changes() -> None:
    require("class PlanningQueryService" in source(QUERY), "Query Layer missing")
    require("def plan_build_order_result" in source(PLANNER), "Planner contract missing")


def test_syntax() -> None:
    for path in (APP, PRESENTER, SCENARIO, VIEW, PRESENTATION):
        ast.parse(source(path), filename=str(path))


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused UI-006 presenter checks")


if __name__ == "__main__":
    main()
