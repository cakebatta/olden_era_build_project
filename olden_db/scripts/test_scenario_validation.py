from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from uuid import UUID

from olden_db.database import load_default_game_data
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.resource_ledger import RecruitmentAction
from olden_db.scenario import PlanningScenario, StartingBuildingOverride
from olden_db.scenario_persistence import (
    ScenarioDocumentValidationError,
    create_scenario_document,
    validate_document_against_game_data,
)

NOW = datetime(2026, 7, 16, 22, 30, tzinfo=timezone.utc)


def main() -> None:
    data = load_default_game_data()
    city = data.cities.city("human")
    target = sorted(city.buildings)[0]
    dwelling = next(key for key, value in sorted(city.buildings.items()) if value.unit_family is not None)
    meaningful = next((key for key, value in sorted(city.buildings.items()) if value.constructed_on_start), None)
    overrides = () if meaningful is None else (StartingBuildingOverride(meaningful, False),)
    document = create_scenario_document(
        name="Canonical", faction="human", target_sid=target.sid, target_level=target.level,
        now=NOW, scenario_id_factory=lambda: UUID("22222222-2222-4222-8222-222222222222"),
        planning_scenario=PlanningScenario(overrides),
        starting_resources=ResourceCost(gold=1000),
        recruitment_actions=(RecruitmentAction(GameDate(1, 1, 1), dwelling, 1, 0),),
    )
    validate_document_against_game_data(document, data)

    _expect_path("game_context.faction", lambda: validate_document_against_game_data(
        replace(document, faction="unknown", target=BuildingKey("unknown", target.sid, target.level),
                planning_scenario=PlanningScenario(), recruitment_actions=()), data))
    _expect_path("game_context.target.sid", lambda: validate_document_against_game_data(
        replace(document, target=BuildingKey("human", "Build_Does_Not_Exist", 1)), data))
    _expect_path("game_context.target.level", lambda: validate_document_against_game_data(
        replace(document, target=BuildingKey("human", target.sid, 999)), data))
    _expect_path("planning_scenario.starting_building_overrides[0].sid", lambda: validate_document_against_game_data(
        replace(document, planning_scenario=PlanningScenario((StartingBuildingOverride(BuildingKey("human", "Missing", 1), True),))), data))
    nondwelling = next(key for key, value in sorted(city.buildings.items()) if value.unit_family is None)
    _expect_path("recruitment_actions[0].dwelling", lambda: validate_document_against_game_data(
        replace(document, recruitment_actions=(RecruitmentAction(GameDate(1, 1, 1), nondwelling, 1, 0),)), data))

    try:
        create_scenario_document(name=" ", faction="human", target_sid=target.sid, target_level=target.level, now=NOW)
    except ScenarioDocumentValidationError as exc:
        if exc.path != "name":
            raise RuntimeError("Blank-name validation did not report its field path")
    else:
        raise RuntimeError("Blank name was accepted")

    try:
        create_scenario_document(name="Bad resources", faction="human", target_sid=target.sid, target_level=target.level,
                                 now=NOW, starting_resources=ResourceCost(gold=-1))
    except ScenarioDocumentValidationError as exc:
        if exc.path != "starting_resources.gold":
            raise RuntimeError("Negative resource validation did not report its field path")
    else:
        raise RuntimeError("Negative starting resource was accepted")

    print("Scenario validation completed successfully.")
    print("Structural/domain document validation remained separate from canonical-data validation.")
    print("Canonical factions, targets, overrides, and recruitment dwellings were validated.")
    print("Validation failures included useful field-path context.")


def _expect_path(path, operation):
    try:
        operation()
    except ScenarioDocumentValidationError as exc:
        if exc.path != path:
            raise RuntimeError(f"Expected path {path!r}, received {exc.path!r}")
        return
    raise RuntimeError(f"Expected ScenarioDocumentValidationError at {path}")


if __name__ == "__main__":
    main()
