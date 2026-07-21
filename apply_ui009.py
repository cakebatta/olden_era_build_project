from __future__ import annotations

import subprocess
from pathlib import Path

EXPECTED = "4248e8aa1ee3e68d1ee2824508ed6d984efce0e3"
ROOT = Path(__file__).resolve().parent
APP = ROOT / "olden_db" / "olden_db" / "desktop" / "app.py"
PLANNER_PRESENTER = (
    ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
)
ARCH = ROOT / "docs" / "desktop_application_architecture.md"

PLANNER_HOOKS = '    def hydrate_semantic_selection(\n        self,\n        selection: PlanningSelection,\n    ) -> None:\n        """Synchronize controls and presenter-local state without replacing selection."""\n        sids = self._service.list_buildings(selection.faction)\n        candidates = self._load_candidates(selection.faction, sids)\n        levels = self._service.list_building_levels(\n            selection.faction,\n            selection.target.sid,\n        )\n        self._state.select_faction(selection.faction, candidates)\n        self._state.select_building(selection.target.sid)\n        self._state.select_level(selection.target.level)\n        self._state.starting_date = selection.starting_date\n        self._state.replace_scenario(selection.scenario)\n        self._view.set_buildings(sids)\n        self._view.set_levels(levels)\n        self._view.set_selection_values(\n            selection.faction,\n            selection.target.sid,\n            selection.target.level,\n        )\n        self._view.set_starting_date(selection.starting_date)\n        self._view.set_starting_buildings(candidates, selection.scenario)\n        self._view.set_planning_mode(self._state.override_count)\n\n    def render_workspace_snapshot(\n        self,\n        snapshot: PlanningWorkspaceSnapshot,\n    ) -> None:\n        """Render one supplied immutable collection-member snapshot."""\n        selection = snapshot.base(DEFAULT_BASE_PLAN_ID).selection\n        if selection is not None:\n            self.hydrate_semantic_selection(selection)\n        self._render_snapshot(snapshot)\n\n'
APP_PRESENTERS_OLD = '        self.economy_presenter = ScenarioAwareEconomyPresenter(\n            service,\n            planner_state,\n            economy_state,\n            economy_view,\n            self.set_status,\n        )\n        self.planner_presenter = ScenarioAwarePlannerPresenter(\n            service,\n            self.planning_workspace,\n            self.planning_execution_coordinator,\n            planner_state,\n            planner_view,\n            self.set_status,\n            on_context_changed=(\n                self.economy_presenter.on_planning_context_changed\n            ),\n        )\n'
APP_PRESENTERS_NEW = '        self.scenario_comparison_workspace_presenter = (\n            ScenarioComparisonWorkspacePresenter(\n                service,\n                self.scenario_comparison_collection,\n                self.scenario_comparison_execution_coordinator,\n                scenario_comparison_workspace_view,\n                self.set_status,\n            )\n        )\n        planner_state = (\n            self.scenario_comparison_workspace_presenter.primary_state\n        )\n        self.economy_presenter = ScenarioAwareEconomyPresenter(\n            service,\n            planner_state,\n            economy_state,\n            economy_view,\n            self.set_status,\n        )\n        self.scenario_comparison_workspace_presenter.set_primary_context_changed_handler(\n            self.economy_presenter.on_planning_context_changed\n        )\n        self.planner_presenter = (\n            self.scenario_comparison_workspace_presenter.primary_presenter\n        )\n        self.planning_workspace = (\n            self.scenario_comparison_collection.workspace(\n                self.scenario_comparison_workspace_presenter.primary_workspace_id\n            )\n        )\n'


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label}")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def require_delivered_files() -> None:
    required = (
        ROOT / "olden_db" / "olden_db" / "desktop" / "scenario_comparison_presentation.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "comparison_execution_adapter.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "scenario_comparison_workspace_presenter.py",
        ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py",
        ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_integration.py",
        ROOT / "docs" / "ui009_runtime_verification.md",
        ROOT / "docs" / "UI-009-IMPLEMENTATION-REPORT.md",
    )
    missing = tuple(str(path.relative_to(ROOT)) for path in required if not path.is_file())
    if missing:
        raise RuntimeError("Extract the full UI-009 archive first. Missing: " + ", ".join(missing))


def patch_planner_presenter() -> None:
    replace_once(
        PLANNER_PRESENTER,
        "    def _selection_became_incomplete(self) -> None:\n",
        PLANNER_HOOKS + "    def _selection_became_incomplete(self) -> None:\n",
        "planner composition hooks",
    )


def patch_app() -> None:
    replace_once(
        APP,
        "from olden_db.planning_execution import PlanningExecutionCoordinator\n"
        "from olden_db.planning_workspace import PlanningWorkspace\n",
        "from olden_db.scenario_comparison import (\n"
        "    ScenarioComparisonCollection,\n"
        "    ScenarioComparisonExecutionCoordinator,\n"
        ")\n",
        "comparison backend imports",
    )
    replace_once(
        APP,
        "from .presenters.comparison_presenter import ComparisonPresenter\n",
        "from .presenters.comparison_presenter import ComparisonPresenter\n"
        "from .presenters.scenario_comparison_workspace_presenter import (\n"
        "    ScenarioComparisonWorkspacePresenter,\n"
        ")\n",
        "comparison workspace presenter import",
    )
    replace_once(
        APP,
        "from .views.planner_view import PlannerView\n",
        "from .views.scenario_comparison_workspace_view import (\n"
        "    ScenarioComparisonWorkspaceView,\n"
        ")\n",
        "comparison workspace view import",
    )
    replace_once(APP, "            planner_view,\n", "            scenario_comparison_workspace_view,\n", "shell planner binding")
    replace_once(
        APP,
        "        planner_state = PlannerState()\n"
        "        economy_state = EconomyTimelineState()\n"
        "        self.planning_workspace = PlanningWorkspace.create()\n"
        "        self.planning_execution_coordinator = PlanningExecutionCoordinator(\n"
        "            service\n"
        "        )\n",
        "        economy_state = EconomyTimelineState()\n"
        "        self.scenario_comparison_collection = (\n"
        "            ScenarioComparisonCollection.create()\n"
        "        )\n"
        "        self.scenario_comparison_execution_coordinator = (\n"
        "            ScenarioComparisonExecutionCoordinator(service)\n"
        "        )\n",
        "application-scoped comparison collection",
    )
    replace_once(APP, APP_PRESENTERS_OLD, APP_PRESENTERS_NEW, "application presenter composition")
    replace_once(APP, "        self.planner_presenter.initialize()\n", "        self.scenario_comparison_workspace_presenter.initialize()\n", "comparison workspace initialization")
    replace_once(APP, "        PlannerView,\n", "        ScenarioComparisonWorkspaceView,\n", "shell return annotation")
    replace_once(APP, '            text="Build Planner",\n', '            text="Scenario Comparison",\n', "navigation label")
    replace_once(
        APP,
        "        planner = PlannerView(planner_shell.content)\n",
        "        planner = ScenarioComparisonWorkspaceView(\n"
        "            planner_shell.content\n"
        "        )\n",
        "comparison workspace construction",
    )
    replace_once(
        APP,
        '        if name == "economy":\n'
        "            self.economy_presenter.refresh_context()\n",
        '        if name == "planner":\n'
        "            self.scenario_comparison_workspace_presenter.refresh()\n"
        '        if name == "economy":\n'
        "            self.economy_presenter.refresh_context()\n",
        "comparison workspace refresh",
    )


def patch_architecture() -> None:
    heading = "## Sprint 15 Desktop Scenario Comparison Workspace (UI-009)"
    text = ARCH.read_text(encoding="utf-8")
    if heading in text:
        print("SKIP: architecture documentation")
        return
    section = f"""

{heading}

The desktop composition root owns one `ScenarioComparisonCollection` and one
`ScenarioComparisonExecutionCoordinator`. The first collection member is also
the persisted primary workspace used by scenario persistence and economy context;
no standalone `PlanningWorkspace` exists outside the collection.

The collection presenter composes one existing `PlannerPresenter`, `PlannerState`,
and `PlannerView` per `WorkspaceId`. A thin member execution adapter routes the
existing presenter execution contract through BE-012 identity-and-revision
correlation. Collection-level controls mutate only membership, labels, ordering,
and comparison roles. Label and role changes never invoke planning.
"""
    ARCH.write_text(text.rstrip() + section + "\n", encoding="utf-8")
    print("UPDATED: architecture documentation")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != EXPECTED:
        raise RuntimeError(f"Expected HEAD {EXPECTED}; found {head}")
    require_delivered_files()
    patch_planner_presenter()
    patch_app()
    patch_architecture()
    print("UI-009 Scenario Comparison Workspace applied.")


if __name__ == "__main__":
    main()
