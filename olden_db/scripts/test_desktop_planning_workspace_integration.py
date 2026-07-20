from __future__ import annotations

from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, GameDate, PlannerResult
from olden_db.planning_execution import PlanningExecutionCoordinator
from olden_db.planning_workspace import (
    PlanningExecutionStatus,
    PlanningSelection,
    PlanningWorkspace,
)
from olden_db.scenario import PlanningScenario


class StubPlanningService:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self.fail_next = False

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
        if self.fail_next:
            self.fail_next = False
            from olden_db.query import QueryError
            raise QueryError("simulated workspace failure")
        target = BuildingKey(faction, sid, level)
        return PlannerResult(
            BuildPlan(
                faction=faction,
                target=target,
                order_number=1,
                steps=(),
                total_cost=ResourceCost(gold=100),
                starting_date=starting_date,
            )
        )


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def selection(level: int, date: GameDate = GameDate(1, 1, 1)):
    return PlanningSelection(
        faction="test",
        target=BuildingKey("test", "town_hall", level),
        starting_date=date,
        scenario=PlanningScenario(),
    )


def test_automatic_ready_lifecycle() -> None:
    service = StubPlanningService()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    pending = workspace.replace_selection(selection(1))
    require(
        pending.base().execution_status is PlanningExecutionStatus.PENDING,
        "Selection replacement must enter pending",
    )
    outcome = coordinator.execute(workspace)
    require(outcome.accepted, "Matching execution must be accepted")
    require(
        outcome.snapshot.base().execution_status is PlanningExecutionStatus.READY,
        "Successful execution must enter ready",
    )
    require(outcome.snapshot.base().result_is_current, "Accepted result must be current")


def test_retained_previous_result_during_pending_and_failure() -> None:
    service = StubPlanningService()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    workspace.replace_selection(selection(1))
    coordinator.execute(workspace)
    pending = workspace.replace_selection(selection(2, GameDate(1, 1, 2)))
    require(pending.base().retains_previous_result, "Pending must retain previous result")
    service.fail_next = True
    failed = coordinator.execute(workspace).snapshot.base()
    require(failed.execution_status is PlanningExecutionStatus.FAILED, "Failure state missing")
    require(failed.retains_previous_result, "Failure must retain previous result")
    require(failed.latest_failure is not None, "Failure projection missing")


def test_repeated_equivalent_selection_is_deterministic_noop() -> None:
    service = StubPlanningService()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    current = selection(1)
    workspace.replace_selection(current)
    first = coordinator.execute(workspace).snapshot.base()
    unchanged = workspace.replace_selection(current).base()
    require(
        unchanged.selection_revision == first.selection_revision,
        "Equivalent replacement must not increment revision",
    )
    require(
        unchanged.accepted_result == first.accepted_result,
        "Equivalent replacement must preserve result",
    )
    require(len(service.calls) == 1, "Equivalent selection should not re-execute")


def test_repeated_selection_changes_increment_revisions() -> None:
    service = StubPlanningService()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    for level in (1, 2, 3):
        workspace.replace_selection(selection(level))
        coordinator.execute(workspace)
    state = workspace.base()
    require(state.selection_revision == 3, "Each semantic change must revise")
    require(state.result_revision == 3, "Latest result revision mismatch")
    require(len(service.calls) == 3, "Each distinct selection must execute")


def main() -> None:
    tests = [
        test_automatic_ready_lifecycle,
        test_retained_previous_result_during_pending_and_failure,
        test_repeated_equivalent_selection_is_deterministic_noop,
        test_repeated_selection_changes_increment_revisions,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} UI-006 workspace integration checks")


if __name__ == "__main__":
    main()
