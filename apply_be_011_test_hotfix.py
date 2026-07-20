from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / "olden_db" / "scripts" / "test_planner_diagnostic_pipeline.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"SKIP: {label} already updated")
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one baseline block, found {count}")
    print(f"UPDATED: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TARGET.read_text(encoding="utf-8")

    text = replace_once(
        text,
        "from olden_db.planner_diagnostics import (\n",
        "from olden_db.planning_execution import PlanningExecutionCoordinator\n"
        "from olden_db.planning_workspace import PlanningWorkspace\n"
        "from olden_db.planner_diagnostics import (\n",
        "workspace imports",
    )

    text = replace_once(
        text,
        """        self.diagnostic_batches: list[
            tuple[PlannerDiagnosticPresentation, ...]
        ] = []
""",
        """        self.diagnostic_batches: list[
            tuple[PlannerDiagnosticPresentation, ...]
        ] = []
        self.workspace_presentations: list[object] = []
""",
        "recording view state",
    )

    text = replace_once(
        text,
        """    def set_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self.diagnostic_batches.append(tuple(diagnostics))
""",
        """    def set_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self.diagnostic_batches.append(tuple(diagnostics))

    def render_workspace(self, presentation) -> None:
        self.workspace_presentations.append(presentation)
        self.diagnostic_batches.append(tuple(presentation.diagnostics))
        if presentation.failure_message:
            self.errors.append(presentation.failure_message)
""",
        "recording workspace rendering",
    )

    text = replace_once(
        text,
        """        *,
        scenario,
    ) -> PlannerResult:
""",
        """        *,
        starting_date=GameDate(1, 1, 1),
        scenario,
    ) -> PlannerResult:
""",
        "recording service signature",
    )

    text = replace_once(
        text,
        """    presenter = PlannerPresenter(service, state, view, statuses.append)

    presenter.on_generate_plan()

    require(service.generate_calls == 1, "Presenter did not use planner-result query")
    require(state.current_plan is result.plan, "Presenter did not store canonical plan")
    require(view.plans == [(result.plan, result.plan.total_cost)], "Plan was not rendered")
    require(not view.errors, "Successful planning displayed an error")
    require(len(view.diagnostic_batches) == 1, "Success diagnostics were not delivered")
""",
        """    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    presenter = PlannerPresenter(
        service,
        workspace,
        coordinator,
        state,
        view,
        statuses.append,
    )

    presenter.on_generate_plan()

    require(service.generate_calls == 1, "Presenter did not use planner-result query")
    require(state.current_plan is result.plan, "Presenter did not store canonical plan")
    require(len(view.workspace_presentations) == 2, "Pending and ready states were not rendered")
    require(
        view.workspace_presentations[-1].accepted_plan is result.plan,
        "Accepted plan was not rendered through workspace presentation",
    )
    require(not view.errors, "Successful planning displayed an error")
    require(len(view.diagnostic_batches) == 2, "Workspace diagnostics were not delivered")
""",
        "success presenter construction and assertions",
    )

    text = replace_once(
        text,
        """    require(view.diagnostic_batches[0] == expected, "Success adapter output changed")
    require(
        tuple(item.explanation for item in view.diagnostic_batches[0])
""",
        """    require(view.diagnostic_batches[-1] == expected, "Success adapter output changed")
    require(
        tuple(item.explanation for item in view.diagnostic_batches[-1])
""",
        "success diagnostic batch selection",
    )

    text = replace_once(
        text,
        """    presenter = PlannerPresenter(service, state, view, statuses.append)

    presenter.on_generate_plan()

    require(state.current_plan is None, "Failure did not clear stale planner state")
    require(len(view.errors) == 1, "Failure did not use the view error contract")
""",
        """    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    presenter = PlannerPresenter(
        service,
        workspace,
        coordinator,
        state,
        view,
        statuses.append,
    )

    presenter.on_generate_plan()

    require(state.current_plan is None, "Failure did not clear stale planner state")
    require(len(view.workspace_presentations) == 2, "Pending and failed states were not rendered")
    require(len(view.errors) == 1, "Failure did not use the workspace error contract")
""",
        "failure presenter construction and assertions",
    )

    text = replace_once(
        text,
        """    require(len(view.diagnostic_batches) == 1, "Failure diagnostics were not delivered")
    require(
        view.diagnostic_batches[0] == adapt_planner_diagnostics(diagnostics),
""",
        """    require(len(view.diagnostic_batches) == 2, "Failure diagnostics were not delivered")
    require(
        view.diagnostic_batches[-1] == adapt_planner_diagnostics(diagnostics),
""",
        "failure diagnostic count",
    )

    text = replace_once(
        text,
        """        tuple(item.explanation for item in view.diagnostic_batches[0])
""",
        """        tuple(item.explanation for item in view.diagnostic_batches[-1])
""",
        "failure diagnostic batch selection",
    )

    TARGET.write_text(text, encoding="utf-8")
    print("BE-011 regression-test hotfix applied.")


if __name__ == "__main__":
    main()
