from __future__ import annotations

from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.scenario import PrerequisiteStatus


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
        f"Canonically constructed at game start: {'Yes' if building.constructed_on_start else 'No'}",
        f"Target building cost: {format_resource_cost(building.cost)}",
    ))


def format_prerequisite_statuses(statuses: tuple[PrerequisiteStatus, ...]) -> str:
    if not statuses:
        return "No direct prerequisites."
    lines = [
        "Buildings available at the active scenario start satisfy prerequisites but do not appear as construction actions.",
        "",
    ]
    for index, status in enumerate(statuses, start=1):
        if status.available_at_start:
            wording = "Available at scenario start"
            if status.overridden:
                wording += " (user override)"
        else:
            wording = "Requires construction"
        lines.extend((
            f"{index}. {format_building_key(status.building.key)}",
            f"   Status: {wording}",
            "",
        ))
    return "\n".join(lines).rstrip()


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
        lines.extend(("", "No construction actions are required because the target is available at the active scenario start."))
    else:
        lines.extend(("", "\n\n".join(format_build_step(step) for step in plan.steps)))
    return "\n".join(lines)


def format_planning_mode(override_count: int) -> str:
    if override_count == 0:
        return "Planning mode: Canonical"
    return f"Planning mode: Custom Starting State\nOverrides: {override_count}"


def format_step_count(count: int) -> str:
    noun = "construction step" if count == 1 else "construction steps"
    return f"{count} {noun}"


def format_diagnostic_summary(diagnostics: tuple[object, ...]) -> str:
    if not diagnostics:
        return "No diagnostics requiring attention."
    count = len(diagnostics)
    noun = "diagnostic" if count == 1 else "diagnostics"
    titles = tuple(str(getattr(item, "title", "Planner diagnostic")) for item in diagnostics)
    return f"{count} {noun}: " + "; ".join(titles)
