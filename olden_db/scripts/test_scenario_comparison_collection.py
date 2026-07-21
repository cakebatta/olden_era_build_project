from __future__ import annotations

from dataclasses import FrozenInstanceError

from olden_db.models import BuildingKey
from olden_db.planning_workspace import (
    PlanningExecutionStatus,
    PlanningFailureState,
    PlanningSelection,
    PlanningWorkspace,
)
from olden_db.query import PlanningQueryService
from olden_db.scenario_comparison import (
    ComparisonRole,
    ScenarioComparisonCollection,
    ScenarioComparisonExecutionCoordinator,
)


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def representative_selection(service: PlanningQueryService) -> PlanningSelection:
    faction = service.list_factions()[0]
    sid = service.list_buildings(faction)[0]
    level = service.list_building_levels(faction, sid)[0]
    return PlanningSelection(
        faction=faction,
        target=BuildingKey(faction, sid, level),
    )


def test_workspace_identity_membership_and_ordering() -> None:
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace(label="Second")
    third = collection.create_workspace(label="Third")

    require(len({first, second, third}) == 3, "WorkspaceId values are not unique")
    require(collection.workspace_ids == (first, second, third), "Insertion order changed")

    collection.reorder_workspace(third, 0)
    require(collection.workspace_ids == (third, first, second), "Reordering failed")

    collection.set_label(first, "Primary")
    collection.set_comparison_role(first, ComparisonRole.LEFT)
    collection.set_comparison_role(second, ComparisonRole.RIGHT)
    snapshot = collection.snapshot()
    require(snapshot.member(first).label == "Primary", "Label was not retained")
    require(
        snapshot.member(first).comparison_role is ComparisonRole.LEFT,
        "Left role was not retained",
    )


def test_independent_revisions_pending_and_failures() -> None:
    service = PlanningQueryService.from_default_game_data()
    selection = representative_selection(service)
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace()

    first_workspace = collection.workspace(first)
    second_workspace = collection.workspace(second)
    first_workspace.replace_selection(selection)

    require(first_workspace.base().selection_revision == 1, "First revision did not advance")
    require(second_workspace.base().selection_revision == 0, "Second revision changed")
    require(
        first_workspace.base().execution_status is PlanningExecutionStatus.PENDING,
        "First did not become pending",
    )
    require(
        second_workspace.base().execution_status is PlanningExecutionStatus.EMPTY,
        "Second lifecycle changed",
    )

    request = collection.capture_execution(first)
    failure = PlanningFailureState("TestFailure", "isolated failure")
    require(collection.accept_failure(request, failure), "Failure not accepted")
    require(
        first_workspace.base().execution_status is PlanningExecutionStatus.FAILED,
        "First did not fail",
    )
    require(
        second_workspace.base().execution_status is PlanningExecutionStatus.EMPTY,
        "Failure leaked to second workspace",
    )


def test_duplication_copies_semantics_only() -> None:
    service = PlanningQueryService.from_default_game_data()
    selection = representative_selection(service)
    coordinator = ScenarioComparisonExecutionCoordinator(service)
    collection = ScenarioComparisonCollection.create()
    source_id = collection.workspace_ids[0]
    source = collection.workspace(source_id)

    source.replace_selection(selection)
    require(coordinator.execute(collection, source_id).accepted, "Source execution failed")
    source.replace_selection(
        PlanningSelection(
            faction=selection.faction,
            target=selection.target,
            starting_date=selection.starting_date.add_days(1),
            scenario=selection.scenario,
        )
    )
    require(source.base().retains_previous_result, "Source did not retain result")

    duplicate_id = collection.duplicate_workspace(source_id, label="Duplicate")
    duplicate_state = collection.workspace(duplicate_id).base()

    require(duplicate_id != source_id, "Identity was reused")
    require(duplicate_state.selection == source.base().selection, "Selection not copied")
    require(duplicate_state.selection_revision == 1, "Revision counter was copied")
    require(
        duplicate_state.execution_status is PlanningExecutionStatus.PENDING,
        "Duplicate did not begin pending",
    )
    require(duplicate_state.accepted_result is None, "Accepted result copied")
    require(duplicate_state.result_revision is None, "Result revision copied")
    require(duplicate_state.latest_failure is None, "Failure copied")
    require(not duplicate_state.retains_previous_result, "Retained result copied")


def test_identity_and_revision_execution_correlation() -> None:
    service = PlanningQueryService.from_default_game_data()
    selection = representative_selection(service)
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace()

    collection.workspace(first).replace_selection(selection)
    collection.workspace(second).replace_selection(selection)

    first_request = collection.capture_execution(first)
    second_request = collection.capture_execution(second)
    result = service.generate_planner_result(
        selection.faction,
        selection.target.sid,
        selection.target.level,
    )

    require(collection.accept_result(second_request, result), "Second result rejected")
    require(
        collection.workspace(second).base().accepted_result is result,
        "Result did not update addressed workspace",
    )
    require(
        collection.workspace(first).base().accepted_result is None,
        "Result leaked to first workspace",
    )

    collection.workspace(first).replace_selection(
        PlanningSelection(
            faction=selection.faction,
            target=selection.target,
            starting_date=selection.starting_date.add_days(1),
            scenario=selection.scenario,
        )
    )
    require(
        not collection.accept_result(first_request, result),
        "Stale request was accepted",
    )


def test_removed_identity_and_shared_service() -> None:
    service = PlanningQueryService.from_default_game_data()
    coordinator = ScenarioComparisonExecutionCoordinator(service)
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace()
    selection = representative_selection(service)
    collection.workspace(second).replace_selection(selection)
    request = collection.capture_execution(second)
    collection.remove_workspace(second)
    result = service.generate_planner_result(
        selection.faction,
        selection.target.sid,
        selection.target.level,
    )
    require(not collection.accept_result(request, result), "Removed identity accepted result")
    require(collection.workspace_ids == (first,), "Remaining identity changed")
    require(coordinator.service is service, "Shared service ownership changed")


def test_independent_results_determinism_and_retention() -> None:
    service = PlanningQueryService.from_default_game_data()
    coordinator = ScenarioComparisonExecutionCoordinator(service)
    selection = representative_selection(service)
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.duplicate_workspace(first)

    collection.workspace(first).replace_selection(selection)
    collection.workspace(second).replace_selection(selection)
    require(coordinator.execute(collection, first).accepted, "First execution failed")
    require(coordinator.execute(collection, second).accepted, "Second execution failed")

    first_result = collection.workspace(first).base().accepted_result
    second_result = collection.workspace(second).base().accepted_result
    require(first_result == second_result, "Determinism changed")
    require(first_result is not second_result, "Accepted result ownership was shared")

    collection.workspace(first).replace_selection(
        PlanningSelection(
            faction=selection.faction,
            target=selection.target,
            starting_date=selection.starting_date.add_days(1),
            scenario=selection.scenario,
        )
    )
    require(collection.workspace(first).base().retains_previous_result, "First lost retention")
    require(
        collection.workspace(second).base().execution_status is PlanningExecutionStatus.READY,
        "Second lifecycle changed",
    )


def test_immutable_collection_snapshots() -> None:
    collection = ScenarioComparisonCollection.create()
    snapshot = collection.snapshot()

    try:
        snapshot.collection_revision = 99  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Collection snapshot is mutable")

    try:
        snapshot.members[0].label = "Changed"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("Member snapshot is mutable")

    collection.set_label(collection.workspace_ids[0], "Renamed")
    require(snapshot.members[0].label != "Renamed", "Existing snapshot mutated")


def test_single_workspace_compatibility() -> None:
    service = PlanningQueryService.from_default_game_data()
    selection = representative_selection(service)
    standalone = PlanningWorkspace.create()
    collection = ScenarioComparisonCollection.create()
    collected = collection.workspace(collection.workspace_ids[0])

    standalone.replace_selection(selection)
    collected.replace_selection(selection)
    require(standalone.snapshot() == collected.snapshot(), "Pending behavior diverged")

    standalone_request = standalone.capture_execution()
    collected_request = collection.capture_execution(collection.workspace_ids[0])
    result = service.generate_planner_result(
        selection.faction,
        selection.target.sid,
        selection.target.level,
    )
    require(standalone.accept_result(standalone_request, result), "Standalone rejected result")
    require(collection.accept_result(collected_request, result), "Collection rejected result")
    require(standalone.snapshot() == collected.snapshot(), "Ready behavior diverged")


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} scenario comparison collection checks")


if __name__ == "__main__":
    main()
