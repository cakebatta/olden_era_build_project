from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "olden_db" / "olden_db" / "desktop" / "app.py"
ARCH = ROOT / "docs" / "desktop_application_architecture.md"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label} already applied")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one reviewed block, found {count}. "
            "Keep the successful partial edits and report this message."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def patch_app() -> None:
    replace_once(APP, '        (\n            manager_view,\n            planner_view,\n            comparison_view,\n            economy_view,\n        ) = self._shell()\n', '        (\n            manager_view,\n            scenario_comparison_workspace_view,\n            comparison_view,\n            economy_view,\n        ) = self._shell()\n', "shell planner binding")
    replace_once(APP, '        planner_state = PlannerState()\n        economy_state = EconomyTimelineState()\n        self.planning_workspace = PlanningWorkspace.create()\n        self.planning_execution_coordinator = PlanningExecutionCoordinator(\n            service\n        )\n', '        economy_state = EconomyTimelineState()\n        self.scenario_comparison_collection = (\n            ScenarioComparisonCollection.create()\n        )\n        self.scenario_comparison_execution_coordinator = (\n            ScenarioComparisonExecutionCoordinator(service)\n        )\n', "application-scoped comparison collection")
    replace_once(APP, '        self.economy_presenter = ScenarioAwareEconomyPresenter(\n            service,\n            planner_state,\n            economy_state,\n            economy_view,\n            self.set_status,\n        )\n        self.planner_presenter = ScenarioAwarePlannerPresenter(\n            service,\n            self.planning_workspace,\n            self.planning_execution_coordinator,\n            planner_state,\n            planner_view,\n            self.set_status,\n            on_context_changed=(\n                self.economy_presenter.on_planning_context_changed\n            ),\n        )\n', '        self.scenario_comparison_workspace_presenter = (\n            ScenarioComparisonWorkspacePresenter(\n                service,\n                self.scenario_comparison_collection,\n                self.scenario_comparison_execution_coordinator,\n                scenario_comparison_workspace_view,\n                self.set_status,\n            )\n        )\n        planner_state = (\n            self.scenario_comparison_workspace_presenter.primary_state\n        )\n        self.economy_presenter = ScenarioAwareEconomyPresenter(\n            service,\n            planner_state,\n            economy_state,\n            economy_view,\n            self.set_status,\n        )\n        self.scenario_comparison_workspace_presenter.set_primary_context_changed_handler(\n            self.economy_presenter.on_planning_context_changed\n        )\n        self.planner_presenter = (\n            self.scenario_comparison_workspace_presenter.primary_presenter\n        )\n        self.planning_workspace = (\n            self.scenario_comparison_collection.workspace(\n                self.scenario_comparison_workspace_presenter.primary_workspace_id\n            )\n        )\n', "application presenter composition")
    replace_once(
        APP,
        "        self.planner_presenter.initialize()\n",
        "        self.scenario_comparison_workspace_presenter.initialize()\n",
        "comparison workspace initialization",
    )
    replace_once(APP, '    ) -> tuple[\n        ScenarioManagerView,\n        PlannerView,\n        ComparisonView,\n        EconomyTimelineView,\n    ]:\n', '    ) -> tuple[\n        ScenarioManagerView,\n        ScenarioComparisonWorkspaceView,\n        ComparisonView,\n        EconomyTimelineView,\n    ]:\n', "shell return annotation")
    replace_once(
        APP,
        '            text="Build Planner",\n',
        '            text="Scenario Comparison",\n',
        "primary navigation label",
    )
    replace_once(
        APP,
        "        planner = PlannerView(planner_shell.content)\n",
        "        planner = ScenarioComparisonWorkspaceView(planner_shell.content)\n",
        "comparison workspace view construction",
    )
    replace_once(APP, '        if name == "economy":\n            self.economy_presenter.refresh_context()\n', '        if name == "planner":\n            self.scenario_comparison_workspace_presenter.refresh()\n        if name == "economy":\n            self.economy_presenter.refresh_context()\n', "comparison workspace refresh")


def patch_architecture() -> None:
    heading = "## Sprint 15 Desktop Scenario Comparison Workspace (UI-009)"
    text = ARCH.read_text(encoding="utf-8")
    if heading in text:
        print("SKIP: architecture documentation already applied")
        return
    section = """
## Sprint 15 Desktop Scenario Comparison Workspace (UI-009)

The desktop composition root owns one application-scoped
`ScenarioComparisonCollection` and one
`ScenarioComparisonExecutionCoordinator`. The first member remains the primary
persisted workspace used by scenario persistence and economy context; no
standalone `PlanningWorkspace` is constructed outside the collection.

The collection presenter composes one existing `PlannerState`,
`ScenarioAwarePlannerPresenter`, and `PlannerView` per stable `WorkspaceId`.
A thin execution adapter routes the existing presenter execution contract
through BE-012 identity-and-revision correlation.

Collection controls mutate backend membership, labels, and Left/Right
presentation roles. Semantic duplication uses the backend collection operation
and starts an independent lifecycle. Label and comparison-role changes never
invoke planning.
"""
    ARCH.write_text(text.rstrip() + "\n\n" + section.strip() + "\n", encoding="utf-8")
    print("UPDATED: architecture documentation")


def validate() -> None:
    files = (
        APP,
        ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "planner_presenter.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "scenario_comparison_workspace_presenter.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "comparison_execution_adapter.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "scenario_comparison_presentation.py",
    )
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_app()
    patch_architecture()
    validate()
    print("UI-009 resume hotfix applied successfully.")


if __name__ == "__main__":
    main()
