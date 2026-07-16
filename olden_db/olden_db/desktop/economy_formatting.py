from __future__ import annotations

from olden_db.constants import RESOURCE_NAMES
from olden_db.models import ResourceCost
from olden_db.query import ResourceLedger

from .formatting import format_building_key, format_game_date


def format_resource_vector(resources: ResourceCost) -> str:
    return ", ".join(
        f"{name}: {getattr(resources, name)}"
        for name in RESOURCE_NAMES
    )


def format_resource_ledger(ledger: ResourceLedger) -> str:
    construction_by_date = {
        entry.date: entry for entry in ledger.construction_entries
    }
    sections: list[str] = []

    for daily in ledger.daily_balances:
        lines = [format_game_date(daily.date)]
        if daily.date.day == 1:
            lines.append("Week boundary")

        construction = construction_by_date.get(daily.date)
        if construction is None:
            lines.extend(
                (
                    "Construction events: None",
                    "Construction cost: None",
                )
            )
        else:
            lines.extend(
                (
                    "Construction event: "
                    f"{format_building_key(construction.building)}",
                    "Construction cost: "
                    f"{format_resource_vector(construction.cost)}",
                )
            )

        lines.append(
            "Closing balance: "
            f"{format_resource_vector(daily.balance)}"
        )
        sections.append("\n".join(lines))

    summary = [
        "Economy Summary",
        "Total construction cost: "
        f"{format_resource_vector(ledger.construction_total)}",
        "Total recruitment cost: "
        f"{format_resource_vector(ledger.recruitment_total)}",
        "Combined total: "
        f"{format_resource_vector(ledger.combined_total)}",
        "Ending balance: "
        f"{format_resource_vector(ledger.ending_balance)}",
        f"Feasible: {'Yes' if ledger.feasible else 'No'}",
    ]

    if ledger.first_deficit is not None:
        deficit = ledger.first_deficit
        summary.extend(
            (
                "",
                "First Deficit",
                f"Date: {format_game_date(deficit.date)}",
                f"Resource: {deficit.resource}",
                f"Signed balance: {deficit.balance}",
                f"Deficit magnitude: {-deficit.balance}",
                "Triggering entry: Construction",
            )
        )

    return "\n\n".join(sections + ["\n".join(summary)])
