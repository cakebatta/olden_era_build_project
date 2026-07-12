from __future__ import annotations

import argparse
from olden_db.graph import (
    all_topological_orders,
    build_dependency_graph,
    is_valid_topological_order,
)
from olden_db.models import BuildingKey
from olden_db.parser import parse_city_directory
from olden_db.paths import require_city_directory


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Load the Olden Era city database and print every valid "
            "topological build order for one target building level."
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
        "--max-orders",
        type=int,
        default=10000,
        help=(
            "Safety limit for generated orders. The script fails rather than "
            "silently truncating if this number is exceeded (default: 10000)."
        ),
    )
    return parser.parse_args()


def format_key(key: BuildingKey) -> str:
    return f"{key.sid} L{key.level}"


def main() -> None:
    args = parse_arguments()

    city_dir = require_city_directory()

    print(f"Loading city files from:\n  {city_dir}\n")

    database = parse_city_directory(city_dir)
    city = database.city(args.faction)

    target = BuildingKey(
        faction=args.faction,
        sid=args.sid,
        level=args.level,
    )

    graph = build_dependency_graph(city, target)
    orders = all_topological_orders(
        graph,
        max_orders=args.max_orders,
    )

    print("=" * 72)
    print(f"Faction: {args.faction}")
    print(f"Target: {format_key(target)}")
    print(f"Required build actions: {graph.build_actions}")
    print(
        "Target already constructed on start: "
        f"{graph.target_is_already_constructed}"
    )

    if graph.satisfied_starting_nodes:
        print("Starting buildings treated as already satisfied:")
        for key in sorted(
            graph.satisfied_starting_nodes,
            key=lambda item: (item.sid, item.level),
        ):
            print(f"  - {format_key(key)}")
    else:
        print("Starting buildings treated as already satisfied: None")

    print(f"Valid topological orders found: {len(orders)}")
    print("=" * 72)
    print()

    for order_number, order in enumerate(orders, start=1):
        valid = is_valid_topological_order(graph, order)
        status = "VALID" if valid else "INVALID"

        print(f"Order {order_number} [{status}]")

        if not order:
            print("  No construction required.")
        else:
            for step_number, key in enumerate(order, start=1):
                building = city.buildings[key]
                prerequisites = graph.prerequisites[key]

                print(
                    f"  {step_number:>2}. {format_key(key)} "
                    f"({building.category})"
                )

                if prerequisites:
                    requirement_text = ", ".join(
                        format_key(prerequisite)
                        for prerequisite in sorted(
                            prerequisites,
                            key=lambda item: (item.sid, item.level),
                        )
                    )
                    print(f"      Requires in this build: {requirement_text}")
                else:
                    print("      Requires in this build: None")

        print()

    if not all(is_valid_topological_order(graph, order) for order in orders):
        raise RuntimeError("At least one generated order failed validation")

    if len(set(orders)) != len(orders):
        raise RuntimeError("Duplicate topological orders were generated")

    print("Graph test completed successfully.")
    print("All generated orders are valid and unique.")


if __name__ == "__main__":
    main()
