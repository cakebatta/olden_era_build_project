from __future__ import annotations

from collections import defaultdict

from olden_db.constants import RESOURCE_NAMES
from olden_db.models import ResourceCost
from olden_db.query import ResourceLedger

from .formatting import format_building_key, format_game_date


def format_resource_vector(resources: ResourceCost) -> str:
    """Format a complete authoritative resource vector."""
    return ", ".join(
        f"{name}: {getattr(resources, name)}"
        for name in RESOURCE_NAMES
    )


def format_event_cost(resources: ResourceCost) -> str:
    """Format only nonzero resources for compact event presentation."""
    values = tuple(
        f"{name}: {getattr(resources, name)}"
        for name in RESOURCE_NAMES
        if getattr(resources, name) != 0
    )
    return ", ".join(values) if values else "None"


def _ordered_events(
    ledger: ResourceLedger,
) -> tuple[tuple[str, object], ...]:
    construction_by_date = {
        entry.date: entry
        for entry in ledger.construction_entries
    }
    recruitment_by_date: dict[
        object,
        list[object],
    ] = defaultdict(list)
    for entry in ledger.recruitment_entries:
        recruitment_by_date[entry.date].append(entry)

    events: list[tuple[str, object]] = []
    for daily in ledger.daily_balances:
        construction = construction_by_date.get(daily.date)
        if construction is not None:
            events.append(("Construction", construction))
        events.extend(
            ("Recruitment", entry)
            for entry in recruitment_by_date.get(
                daily.date,
                (),
            )
        )
    return tuple(events)


def _deficit_trigger(ledger: ResourceLedger) -> str:
    deficit = ledger.first_deficit
    if deficit is None:
        return ""
    events = _ordered_events(ledger)
    index = deficit.entry_index - 1
    return (
        events[index][0]
        if 0 <= index < len(events)
        else "Unknown"
    )


def format_resource_ledger(
    ledger: ResourceLedger,
) -> str:
    construction_by_date = {
        entry.date: entry
        for entry in ledger.construction_entries
    }
    recruitment_by_date: dict[
        object,
        list[object],
    ] = defaultdict(list)
    for entry in ledger.recruitment_entries:
        recruitment_by_date[entry.date].append(entry)

    sections: list[str] = []
    for daily in ledger.daily_balances:
        lines = [format_game_date(daily.date)]
        if daily.date.day == 1:
            lines.append("Week boundary")

        construction = construction_by_date.get(daily.date)
        if construction is None:
            lines.append("Construction events: None")
        else:
            lines.extend(
                (
                    "Construction event: "
                    f"{format_building_key(construction.building)}",
                    "Construction cost: "
                    f"{format_event_cost(construction.cost)}",
                )
            )

        recruitment = recruitment_by_date.get(
            daily.date,
            (),
        )
        if not recruitment:
            lines.append("Recruitment events: None")
        else:
            for entry in recruitment:
                action = entry.action
                lines.extend(
                    (
                        "Recruitment event: "
                        f"{format_building_key(action.dwelling)}",
                        f"  Base quantity: {action.base_quantity}",
                        "  Upgraded quantity: "
                        f"{action.upgraded_quantity}",
                        "  Recruitment cost: "
                        f"{format_event_cost(entry.cost)}",
                        f"  Stock before: {entry.stock_before}",
                        f"  Stock after: {entry.stock_after}",
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
                "Triggering entry: "
                f"{_deficit_trigger(ledger)}",
            )
        )

    return "\n\n".join(
        sections + ["\n".join(summary)]
    )
