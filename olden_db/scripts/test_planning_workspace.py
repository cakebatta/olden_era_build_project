from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.models import BuildingKey
from olden_db.planner import BuildPlan, GameDate, PlannerResult, PlanningFailure
from olden_db.planner_diagnostics import (
    PlannerDiagnostic,
    PlannerDiagnosticCategory,
)
from olden_db.planning_execution import PlanningExecutionCoordinator
from olden_db.planning_workspace import (
    DEFAULT_BASE_PLAN_ID,
    PlanningExecutionStatus,
    PlanningSelection,
    PlanningWorkspace,
)
from olden_db.query import PlanningQueryService
from olden_db.scenario import PlanningScenario


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def sample_selection(
    sid: str = "Target",
    *,
    starting_date: GameDate = GameDate(1, 1, 1),
) -> PlanningSelection:
    return PlanningSelection(
        faction="Test",
        target=BuildingKey("Test", sid, 1),
        starting_date=starting_date,
        scenario=PlanningScenario(),
    )


def sample_plan(selection: PlanningSelection) -> BuildPlan:
    return BuildPlan(
        faction=selection.faction,
        target=selection.target,
        order_number=1,
        steps=(),
        total_cost=__import__("olden_db.models", fromlist=["ResourceCost"]).ResourceCost(),
        starting_date=selection.starting_date,
    )


def sample_result(selection: PlanningSelection) -> PlannerResult:
    return PlannerResult(sample_plan(selection))


def test_workspace_lifecycle_and_selection_immutability() -> None:
    workspace = PlanningWorkspace.create()
    initial = workspace.base()
    require(initial.base_id == DEFAULT_BASE_PLAN_ID, "Default base id changed")
    require(initial.selection is None, "New workspace unexpectedly has a selection")
    require(initial.selection_revision == 0, "New workspace revision must be zero")
    require(
        initial.execution_status is PlanningExecutionStatus.EMPTY,
        "New workspace must be EMPTY",
    )

    selection = sample_selection()
    try:
        selection.faction = "Other"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("PlanningSelection is mutable")

    snapshot = workspace.replace_selection(selection)
    current = snapshot.base()
    require(current.selection is selection, "Workspace did not store selection")
    require(current.selection_revision == 1, "First mutation did not increment revision")
    require(
        current.execution_status is PlanningExecutionStatus.PENDING,
        "Complete selection must become PENDING",
    )

    unchanged = workspace.replace_selection(selection).base()
    require(
        unchanged.selection_revision == 1,
        "Equivalent selection incorrectly incremented revision",
    )

    second = sample_selection("OtherTarget")
    updated = workspace.replace_selection(second).base()
    require(updated.selection_revision == 2, "Second mutation did not increment revision")
    require(updated.selection == second, "Selection replacement failed")


def test_matching_result_is_accepted_and_stale_result_is_rejected() -> None:
    workspace = PlanningWorkspace.create()
    first = sample_selection()
    workspace.replace_selection(first)
    first_request = workspace.capture_execution()

    second = sample_selection("OtherTarget")
    workspace.replace_selection(second)

    stale_accepted = workspace.accept_result(first_request, sample_result(first))
    require(not stale_accepted, "Stale result was accepted")
    current = workspace.base()
    require(current.selection == second, "Stale completion changed current selection")
    require(current.selection_revision == 2, "Stale completion changed revision")
    require(current.accepted_result is None, "Stale completion installed a result")
    require(
        current.execution_status is PlanningExecutionStatus.PENDING,
        "Stale completion changed current execution status",
    )

    current_request = workspace.capture_execution()
    result = sample_result(second)
    require(
        workspace.accept_result(current_request, result),
        "Current result was rejected",
    )
    ready = workspace.base()
    require(ready.accepted_result is result, "Current result was not stored")
    require(ready.result_revision == ready.selection_revision == 2, "Result revision mismatch")
    require(ready.result_is_current, "Current result not recognized")
    require(
        ready.execution_status is PlanningExecutionStatus.READY,
        "Accepted result did not set READY",
    )


class SuccessfulService:
    def __init__(self, result: PlannerResult) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []

    def generate_planner_result(
        self,
        faction,
        sid,
        level,
        *,
        starting_date,
        scenario,
    ):
        self.calls.append((faction, sid, level, starting_date, scenario))
        return self.result


class MutatingService:
    def __init__(
        self,
        workspace: PlanningWorkspace,
        replacement: PlanningSelection,
        old_result: PlannerResult,
    ) -> None:
        self.workspace = workspace
        self.replacement = replacement
        self.old_result = old_result

    def generate_planner_result(self, *args, **kwargs):
        self.workspace.replace_selection(self.replacement)
        return self.old_result


class FailingService:
    def __init__(self, failure: PlanningFailure) -> None:
        self.failure = failure

    def generate_planner_result(self, *args, **kwargs):
        raise self.failure


def test_execution_coordinator_query_contract_and_stale_rejection() -> None:
    selection = sample_selection()
    result = sample_result(selection)
    service = SuccessfulService(result)
    workspace = PlanningWorkspace.create()
    workspace.replace_selection(selection)

    outcome = PlanningExecutionCoordinator(service).execute(workspace)
    require(outcome.accepted, "Synchronous current result was not accepted")
    require(workspace.base().accepted_result is result, "Coordinator lost PlannerResult")
    require(
        service.calls
        == [
            (
                selection.faction,
                selection.target.sid,
                selection.target.level,
                selection.starting_date,
                selection.scenario,
            )
        ],
        "Coordinator did not map selection to Query Layer arguments",
    )

    stale_workspace = PlanningWorkspace.create()
    stale_workspace.replace_selection(selection)
    replacement = sample_selection("Replacement")
    stale_service = MutatingService(stale_workspace, replacement, result)
    stale_outcome = PlanningExecutionCoordinator(stale_service).execute(stale_workspace)
    require(not stale_outcome.accepted, "Coordinator accepted a stale completion")
    require(
        stale_workspace.base().selection == replacement,
        "Coordinator stale handling changed newer selection",
    )
    require(
        stale_workspace.base().accepted_result is None,
        "Coordinator installed stale result",
    )


def test_failure_transport_and_previous_result_retention() -> None:
    selection = sample_selection()
    workspace = PlanningWorkspace.create()
    workspace.replace_selection(selection)
    current_result = sample_result(selection)
    request = workspace.capture_execution()
    require(workspace.accept_result(request, current_result), "Setup result was rejected")

    replacement = sample_selection("Replacement")
    workspace.replace_selection(replacement)

    diagnostic = PlannerDiagnostic(
        diagnostic_code="PLANNER_TEST_FAILURE",
        category=PlannerDiagnosticCategory.INVALID_REQUEST,
        canonical_explanation="Test failure.",
    )
    failure = PlanningFailure("failed", diagnostics=(diagnostic,))
    outcome = PlanningExecutionCoordinator(FailingService(failure)).execute(workspace)

    require(outcome.accepted, "Current failure was rejected")
    failed = workspace.base()
    require(
        failed.execution_status is PlanningExecutionStatus.FAILED,
        "Failure did not set FAILED",
    )
    require(failed.latest_failure is not None, "Failure state was not recorded")
    require(
        failed.latest_failure.diagnostics == (diagnostic,),
        "Canonical diagnostics were not preserved",
    )
    require(
        failed.accepted_result is current_result,
        "Previous accepted result was not retained",
    )
    require(
        failed.retains_previous_result,
        "Retained previous result was represented as current",
    )


def test_real_query_layer_integration_and_legacy_compatibility() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction = service.list_factions()[0]
    sid = service.list_buildings(faction)[0]
    level = service.list_building_levels(faction, sid)[0]
    building = service.get_building(faction, sid, level)
    selection = PlanningSelection(
        faction=faction,
        target=building.key,
        starting_date=GameDate(1, 1, 1),
        scenario=PlanningScenario(),
    )

    direct_first = service.generate_build_plan(
        faction,
        sid,
        level,
        starting_date=selection.starting_date,
        scenario=selection.scenario,
    )
    direct_second = service.generate_build_plan(
        faction,
        sid,
        level,
        starting_date=selection.starting_date,
        scenario=selection.scenario,
    )
    require(direct_first == direct_second, "Legacy planner result is not deterministic")

    direct_result = service.generate_planner_result(
        faction,
        sid,
        level,
        starting_date=selection.starting_date,
        scenario=selection.scenario,
    )
    require(
        direct_result.plan == direct_first,
        "PlannerResult changed legacy BuildPlan behavior",
    )

    workspace = PlanningWorkspace.create()
    workspace.replace_selection(selection)
    outcome = PlanningExecutionCoordinator(service).execute(workspace)
    require(outcome.accepted, "Real Query Layer result was not accepted")
    require(
        workspace.base().accepted_result == direct_result,
        "Workspace execution differs from direct Query Layer execution",
    )


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} planning workspace foundation checks")


if __name__ == "__main__":
    main()
