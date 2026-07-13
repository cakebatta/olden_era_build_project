from __future__ import annotations

from collections.abc import Callable

from olden_db.database import load_default_game_data
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, GameDate
from olden_db.query import PlanningQueryService, QueryError

DEFAULT_ORDER_LIMIT = 10
MAX_ORDER_LIMIT = 100


def format_building(building: BuildingLevel) -> str:
    """Format one building while retaining its canonical identity."""
    lines = [
        format_building_key(building.key),
        f"Category: {building.category}",
        f"Name key: {building.name_key or '(none)'}",
        f"Constructed on start: {'yes' if building.constructed_on_start else 'no'}",
        f"Individual cost: {format_resource_cost(building.cost)}",
    ]
    return "\n".join(lines)


def format_building_key(key: BuildingKey) -> str:
    return f"Faction: {key.faction} | SID: {key.sid} | Level: {key.level}"


def format_prerequisites(prerequisites: tuple[BuildingLevel, ...]) -> str:
    if not prerequisites:
        return "Direct prerequisites: none"

    lines = ["Direct prerequisites:"]
    lines.extend(
        f"  {index}. {format_building_key(building.key)}"
        for index, building in enumerate(prerequisites, start=1)
    )
    return "\n".join(lines)


def format_resource_cost(cost: ResourceCost) -> str:
    nonzero = [
        f"{resource}={amount}"
        for resource, amount in cost.as_dict().items()
        if amount
    ]
    return ", ".join(nonzero) if nonzero else "none"


def format_game_date(date: GameDate) -> str:
    return f"month {date.month}, week {date.week}, day {date.day} ({date.code})"


def format_build_plan(plan: BuildPlan) -> str:
    lines = [
        "Deterministic build plan",
        f"Target: {format_building_key(plan.target)}",
        f"Starting date: {format_game_date(plan.starting_date)}",
        f"Completion date: {format_game_date(plan.completion_date)}",
        f"Build actions: {plan.build_actions}",
    ]

    if not plan.steps:
        lines.append("Steps: none (target is already constructed on start)")
    else:
        lines.append("Steps:")
        for step in plan.steps:
            lines.extend(
                [
                    f"  {step.step_number}. {format_game_date(step.date)}",
                    f"     {format_building_key(step.building)}",
                    f"     Cost: {format_resource_cost(step.individual_cost)}",
                    f"     Cumulative: {format_resource_cost(step.cumulative_cost)}",
                ]
            )

    lines.append(f"Total cost: {format_resource_cost(plan.total_cost)}")
    return "\n".join(lines)


def format_build_orders(
    orders: tuple[tuple[BuildingKey, ...], ...],
    *,
    limit: int,
) -> str:
    if not orders:
        return "Legal build orders: none"

    lines = [f"Legal build orders (showing up to {limit}):"]
    for order_number, order in enumerate(orders, start=1):
        lines.append(f"  Order {order_number}:")
        if not order:
            lines.append("    (no construction actions)")
            continue
        lines.extend(
            f"    {step_number}. {format_building_key(key)}"
            for step_number, key in enumerate(order, start=1)
        )
    return "\n".join(lines)


def prompt_target(
    input_fn: Callable[[str], str] = input,
) -> tuple[str, str, int]:
    faction = input_fn("Faction: ").strip()
    sid = input_fn("Building SID: ").strip()

    while True:
        raw_level = input_fn("Level: ").strip()
        try:
            level = int(raw_level)
        except ValueError:
            print("Level must be a whole number.")
            continue
        if level < 1:
            print("Level must be at least 1.")
            continue
        return faction, sid, level


def prompt_order_limit(
    input_fn: Callable[[str], str] = input,
) -> int:
    while True:
        raw_limit = input_fn(
            f"Maximum orders to display [{DEFAULT_ORDER_LIMIT}]: "
        ).strip()
        if not raw_limit:
            return DEFAULT_ORDER_LIMIT
        try:
            limit = int(raw_limit)
        except ValueError:
            print("Limit must be a whole number.")
            continue
        if not 1 <= limit <= MAX_ORDER_LIMIT:
            print(f"Limit must be between 1 and {MAX_ORDER_LIMIT}.")
            continue
        return limit


def run_query(query: Callable[[], str]) -> None:
    try:
        output = query()
    except QueryError as exc:
        print(f"Request could not be completed: {exc}")
    else:
        print(output)


def run_playground(
    service: PlanningQueryService,
    input_fn: Callable[[str], str] = input,
) -> None:
    print("Olden Era Planning Query Playground")
    print("Engineering validation client; canonical identifiers are required.\n")

    faction, sid, level = prompt_target(input_fn)

    while True:
        print(
            "\n1. Building information\n"
            "2. Direct prerequisites\n"
            "3. Deterministic build plan\n"
            "4. Cumulative cost\n"
            "5. Legal build orders\n"
            "6. Change target\n"
            "7. Exit"
        )
        choice = input_fn("Choice: ").strip()

        if choice == "1":
            run_query(lambda: format_building(service.get_building(faction, sid, level)))
        elif choice == "2":
            run_query(lambda: format_prerequisites(service.get_prerequisites(faction, sid, level)))
        elif choice == "3":
            run_query(lambda: format_build_plan(service.generate_build_plan(faction, sid, level)))
        elif choice == "4":
            run_query(
                lambda: "Cumulative cost\n"
                f"Target: Faction: {faction} | SID: {sid} | Level: {level}\n"
                f"Total: {format_resource_cost(service.get_cumulative_cost(faction, sid, level))}"
            )
        elif choice == "5":
            limit = prompt_order_limit(input_fn)
            run_query(
                lambda: format_build_orders(
                    service.enumerate_build_orders(faction, sid, level, max_orders=limit),
                    limit=limit,
                )
            )
        elif choice == "6":
            faction, sid, level = prompt_target(input_fn)
        elif choice == "7":
            print("Exiting query playground.")
            return
        else:
            print("Enter a menu choice from 1 through 7.")


def main() -> None:
    service = PlanningQueryService(load_default_game_data())
    run_playground(service)


if __name__ == "__main__":
    main()
