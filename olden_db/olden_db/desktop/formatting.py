from __future__ import annotations

from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate


def format_faction_status(faction_count: int) -> str:
    noun = "faction" if faction_count == 1 else "factions"
    return f"Ready — {faction_count} {noun} available."


def format_building_key(key: BuildingKey) -> str:
    return f"Faction: {key.faction} | SID: {key.sid} | Level: {key.level}"


def format_game_date(date: GameDate) -> str:
    return f"Month {date.month}, Week {date.week}, Day {date.day} (date code {date.code})"


def format_resource_cost(cost: ResourceCost) -> str:
    values = [f"{resource}: {amount}" for resource, amount in cost.as_dict().items() if amount]
    return ", ".join(values) if values else "None"


def format_target(building: BuildingLevel) -> str:
    return "\n".join((
        format_building_key(building.key),
        f"Category: {building.category}",
        f"Constructed at game start: {'Yes' if building.constructed_on_start else 'No'}",
        f"Target building cost: {format_resource_cost(building.cost)}",
    ))


def format_prerequisites(prerequisites: tuple[BuildingLevel, ...]) -> str:
    if not prerequisites:
        return "No direct prerequisites."
    return "\n".join(f"{index}. {format_building_key(building.key)}" for index, building in enumerate(prerequisites, start=1))


def format_build_step(step: BuildStep) -> str:
    return "\n".join((
        f"Step {step.step_number}",
        f"  Date: {format_game_date(step.date)}",
        f"  Building: {format_building_key(step.building)}",
        f"  Individual cost: {format_resource_cost(step.individual_cost)}",
        f"  Cumulative cost: {format_resource_cost(step.cumulative_cost)}",
    ))


def format_build_plan(plan: BuildPlan) -> str:
    lines = [
        f"Starting date: {format_game_date(plan.starting_date)}",
        f"Completion date: {format_game_date(plan.completion_date)}",
        f"Total construction actions: {plan.build_actions}",
    ]
    if not plan.steps:
        lines.extend(("", "No construction actions are required because the target is constructed at game start."))
    else:
        lines.extend(("", "\n\n".join(format_build_step(step) for step in plan.steps)))
    return "\n".join(lines)
