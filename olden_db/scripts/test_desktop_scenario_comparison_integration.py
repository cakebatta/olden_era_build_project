from __future__ import annotations

from olden_db.models import BuildingKey
from olden_db.planner import GameDate
from olden_db.planning_workspace import PlanningSelection
from olden_db.scenario import PlanningScenario
from olden_db.scenario_comparison import (
    ComparisonRole,
    ScenarioComparisonCollection,
)


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def selection(sid: str) -> PlanningSelection:
    return PlanningSelection(
        faction="test",
        target=BuildingKey("test", sid, 1),
        starting_date=GameDate(1, 1, 1),
        scenario=PlanningScenario(),
    )


def test_creation_removal_and_stable_identity() -> None:
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace()
    third = collection.create_workspace()
    collection.remove_workspace(second)
    require(collection.workspace_ids == (first, third), "remaining identities changed")


def test_duplication_is_semantic_only() -> None:
    collection = ScenarioComparisonCollection.create()
    source = collection.workspace_ids[0]
    collection.workspace(source).replace_selection(selection("hall"))
    duplicate = collection.duplicate_workspace(source)
    source_base = collection.workspace(source).base()
    duplicate_base = collection.workspace(duplicate).base()
    require(duplicate_base.selection == source_base.selection, "selection not duplicated")
    require(duplicate_base.accepted_result is None, "lifecycle result copied")
    require(duplicate_base.selection_revision == 1, "duplicate lifecycle not independent")


def test_roles_are_metadata_only() -> None:
    collection = ScenarioComparisonCollection.create()
    first = collection.workspace_ids[0]
    second = collection.create_workspace()
    collection.workspace(first).replace_selection(selection("hall"))
    revision = collection.workspace(first).base().selection_revision
    collection.set_comparison_role(first, ComparisonRole.LEFT)
    collection.set_comparison_role(second, ComparisonRole.RIGHT)
    require(
        collection.workspace(first).base().selection_revision == revision,
        "role assignment changed planning revision",
    )


def test_deterministic_repeated_snapshot() -> None:
    collection = ScenarioComparisonCollection.create()
    require(collection.snapshot() == collection.snapshot(), "snapshot is not deterministic")


def main() -> None:
    tests = [
        test_creation_removal_and_stable_identity,
        test_duplication_is_semantic_only,
        test_roles_are_metadata_only,
        test_deterministic_repeated_snapshot,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} UI-009 collection integration checks")


if __name__ == "__main__":
    main()
