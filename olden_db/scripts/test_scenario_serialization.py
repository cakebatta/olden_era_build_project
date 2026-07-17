from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
import json
from uuid import UUID

from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.resource_ledger import RecruitmentAction
from olden_db.scenario import PlanningScenario, StartingBuildingOverride
from olden_db.scenario_persistence import (
    ScenarioDocumentValidationError,
    ScenarioSerializationError,
    UnsupportedScenarioVersionError,
    create_scenario_document,
    deserialize_scenario_document,
    duplicate_scenario_document,
    serialize_scenario_document,
)

NOW = datetime(2026, 7, 16, 22, 30, tzinfo=timezone.utc)
ID = UUID("550e8400-e29b-41d4-a716-446655440000")


def main() -> None:
    minimal = create_scenario_document(
        name="  Early Economy Rush  ", faction="human", target_sid="Build_Main",
        target_level=2, now=NOW, scenario_id_factory=lambda: ID,
    )
    if minimal.name != "Early Economy Rush":
        raise RuntimeError("Scenario name was not normalized")
    text = serialize_scenario_document(minimal)
    if not text.endswith("\n") or text.endswith("\n\n"):
        raise RuntimeError("Canonical JSON must have one final newline")
    if deserialize_scenario_document(text) != minimal:
        raise RuntimeError("Minimal document did not round-trip exactly")
    if serialize_scenario_document(minimal) != serialize_scenario_document(minimal):
        raise RuntimeError("Repeated serialization was not byte-identical")
    if "\\u00e9" in serialize_scenario_document(replace(minimal, notes="café")):
        raise RuntimeError("Unicode was unnecessarily escaped")

    full = create_scenario_document(
        name="Full", description="Description", faction="human",
        target_sid="Build_Main", target_level=3, now=NOW,
        scenario_id_factory=lambda: UUID("8992ba4a-326d-4e94-9820-f02a3407db71"),
        starting_date=GameDate(1, 1, 2),
        planning_scenario=PlanningScenario((
            StartingBuildingOverride(BuildingKey("human", "Build_Tier_1", 1), False),
            StartingBuildingOverride(BuildingKey("human", "Build_Main", 1), True),
        )),
        starting_resources=ResourceCost(gold=10000, wood=10, ore=10, gemstones=5, crystals=5, mercury=5, dust=50),
        recruitment_actions=(
            RecruitmentAction(GameDate(1, 1, 5), BuildingKey("human", "Build_Tier_1", 1), 2, 0),
            RecruitmentAction(GameDate(1, 1, 4), BuildingKey("human", "Build_Tier_1", 1), 1, 0),
        ), notes="Notes",
    )
    full_text = serialize_scenario_document(full)
    if deserialize_scenario_document(full_text) != full:
        raise RuntimeError("Fully populated document did not round-trip")
    decoded = json.loads(full_text)
    if list(decoded["starting_resources"]) != ["gold", "wood", "ore", "gemstones", "crystals", "mercury", "dust", "graal"]:
        raise RuntimeError("Resource ordering was not canonical")
    if decoded["planning_scenario"]["starting_building_overrides"][0]["sid"] != "Build_Main":
        raise RuntimeError("Building override ordering was not canonical")
    if decoded["recruitment_actions"][0]["date"]["day"] != 4:
        raise RuntimeError("Recruitment action ordering was not canonical")

    duplicate = duplicate_scenario_document(full, now=datetime(2026, 7, 17, tzinfo=timezone.utc),
                                            scenario_id_factory=lambda: UUID("11111111-1111-4111-8111-111111111111"))
    if duplicate.scenario_id == full.scenario_id or duplicate.created_at == full.created_at:
        raise RuntimeError("Duplication did not create new identity and timestamps")
    if duplicate.target != full.target or duplicate.recruitment_actions != full.recruitment_actions:
        raise RuntimeError("Duplication did not preserve user-authored planning content")

    _expect(ScenarioSerializationError, lambda: deserialize_scenario_document("{"))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document("[]"))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document('{"schema_version":1,"schema_version":1}'))
    _expect(UnsupportedScenarioVersionError, lambda: deserialize_scenario_document('{"schema_version":99}'))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document('{"schema_version":true}'))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document(full_text.replace('"notes": "Notes"', '"notes": "Notes",\n  "unknown": 1')))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document(full_text.replace('"notes": "Notes"', '"notes": null')))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document(full_text.replace(str(full.scenario_id), "not-a-uuid")))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document(full_text.replace("2026-07-16T22:30:00Z", "2026-07-16T22:30:00+00:00", 1)))
    _expect(ScenarioDocumentValidationError, lambda: deserialize_scenario_document(full_text.replace('"gold": 10000', '"gold": -1')))

    print("Scenario serialization validation completed successfully.")
    print("Minimal and fully populated Version 1 documents round-tripped exactly.")
    print("Repeated serialization was byte-identical and canonically ordered.")
    print("UUIDs and timestamps were preserved by pure serialization.")
    print("Malformed JSON, duplicate keys, unknown fields, nulls, and unsupported versions were rejected.")


def _expect(error_type, operation):
    try:
        operation()
    except error_type:
        return
    raise RuntimeError(f"Expected {error_type.__name__}")


if __name__ == "__main__":
    main()
