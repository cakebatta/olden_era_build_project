from __future__ import annotations

import argparse
from olden_db.graph import build_dependency_graph
from olden_db.models import BuildingKey, ResourceCost
from olden_db.parser import parse_city_directory
from olden_db.paths import require_city_directory
from olden_db.planner import (
    GameDate,
    plan_all_orders,
    validate_plan_set,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Print every valid dated and costed build plan for one "
            "Olden Era target building."
        )
    )
    parser.add_argument(
        "--faction",
        default="nature",
        help="Faction ID, such as nature, human, or unfrozen (default: nature).",
    )
    parser.add_argument(
        "--sid",
        default="Build_Tier_4",
        help="Target building SID (default: Build_Tier_4).",
    )
    parser.add_argument(
        "--level",
        type=int,
        default=2,
        help="Target building level (default: 2).",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=111,
        help="Starting MWD date code (default: 111).",
    )
    parser.add_argument(
        "--max-orders",
        type=int,
        default=10000,
        help=(
            "Safety limit for generated plans. The script fails rather than "
            "silently truncating if exceeded (default: 10000)."
        ),
    )
    return parser.parse_args()


def parse_date_code(code: int) -> GameDate:
    text = str(code)

    if len(text) != 3 or not text.isdigit():
        raise ValueError(
            f"Starting date must be a three-digit MWD code, received {code!r}"
        )

    return GameDate(
        month=int(text[0]),
        week=int(text[1]),
        day=int(text[2]),
    )


def format_key(key: BuildingKey) -> str:
    return f"{key.sid} L{key.level}"


def nonzero_cost_parts(cost: ResourceCost) -> list[str]:
    return [
        f"{name}={amount}"
        for name, amount in cost.as_dict().items()
        if amount != 0
    ]


def format_cost(cost: ResourceCost) -> str:
    parts = nonzero_cost_parts(cost)
    return ", ".join(parts) if parts else "No cost"


def print_plan_summary(plan_number: int, build_actions: int, completion: int) -> None:
    print(f"Plan {plan_number}")
    print(f"  Build actions: {build_actions}")
    print(f"  Completion date: {completion}")


def main() -> None:
    args = parse_arguments()

    city_dir = require_city_directory()

    starting_date = parse_date_code(args.start)

    print(f"Loading city files from:\n  {city_dir}\n")

    database = parse_city_directory(city_dir)
    city = database.city(args.faction)

    target = BuildingKey(
        faction=args.faction,
        sid=args.sid,
        level=args.level,
    )

    graph = build_dependency_graph(city, target)
    plans = plan_all_orders(
        city,
        graph,
        starting_date=starting_date,
        max_orders=args.max_orders,
    )
    validate_plan_set(plans)

    print("=" * 80)
    print(f"Faction: {args.faction}")
    print(f"Target: {format_key(target)}")
    print(f"Starting date: {starting_date.code}")
    print(f"Valid plans found: {len(plans)}")
    print(f"Required build actions: {graph.build_actions}")

    if graph.satisfied_starting_nodes:
        print("Starting buildings treated as already satisfied:")
        for key in sorted(
            graph.satisfied_starting_nodes,
            key=lambda item: (item.sid, item.level),
        ):
            print(f"  - {format_key(key)}")
    else:
        print("Starting buildings treated as already satisfied: None")

    print("=" * 80)
    print()

    for plan in plans:
        print_plan_summary(
            plan_number=plan.order_number,
            build_actions=plan.build_actions,
            completion=plan.completion_date.code,
        )
        print(f"  Total cost: {format_cost(plan.total_cost)}")
        print()

        if not plan.steps:
            print("  No construction required.")
            print()
            continue

        for step in plan.steps:
            building = city.buildings[step.building]

            print(
                f"  {step.step_number:>2}. Date {step.date.code} | "
                f"{format_key(step.building)} | {building.category}"
            )
            print(f"      Step cost: {format_cost(step.individual_cost)}")
            print(f"      Running total: {format_cost(step.cumulative_cost)}")

        print()
        print("-" * 80)
        print()

    reference = plans[0]

    print("Shared final result across all valid plans")
    print(f"  Build actions: {reference.build_actions}")
    print(f"  Completion date: {reference.completion_date.code}")
    print(f"  Total cost: {format_cost(reference.total_cost)}")
    print()

    if len(plans) > 1:
        print(
            "The final cost and completion date are identical, while the "
            "intermediate unlock sequence differs between plans."
        )
        print()

    print("Planner test completed successfully.")
    print("All plans are valid, unique, and internally consistent.")


if __name__ == "__main__":
    main()
