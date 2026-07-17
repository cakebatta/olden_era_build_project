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
    """Format only nonzero expense resources."""
    values = tuple(
        f"{name}: {getattr(resources, name)}"
        for name in RESOURCE_NAMES
        if getattr(resources, name) != 0
    )
    return ", ".join(values) if values else "None"


def format_income_amount(resources: ResourceCost) -> str:
    """Format only nonzero income resources with an explicit positive sign."""
    values = tuple(
        f"+{getattr(resources, name)} {name}"
        for name in RESOURCE_NAMES
        if getattr(resources, name) != 0
    )
    return ", ".join(values) if values else "None"


def _entries_by_date(entries: tuple[object, ...]) -> dict[object, list[object]]:
    grouped: dict[object, list[object]] = defaultdict(list)
    for entry in entries:
        grouped[entry.date].append(entry)
    return grouped


def _ordered_events(
    ledger: ResourceLedger,
) -> tuple[tuple[str, object], ...]:
    """Reconstruct the complete certified event-index sequence."""

    income_by_date = _entries_by_date(ledger.income_entries)
    construction_by_date = {
        entry.date: entry
        for entry in ledger.construction_entries
    }
    recruitment_by_date = _entries_by_date(
        ledger.recruitment_entries
    )

    events: list[tuple[str, object]] = []
    for daily in ledger.daily_balances:
        events.extend(
            ("Income", entry)
            for entry in income_by_date.get(daily.date, ())
        )

        construction = construction_by_date.get(daily.date)
        if construction is not None:
            events.append(("Construction", construction))

        events.extend(
            ("Recruitment", entry)
            for entry in recruitment_by_date.get(daily.date, ())
        )

    return tuple(events)


def _deficit_trigger(
    ledger: ResourceLedger,
) -> str | None:
    """Return a trigger only when the complete event index resolves."""

    deficit = ledger.first_deficit
    if deficit is None:
        return None

    events = _ordered_events(ledger)
    index = deficit.entry_index - 1
    if 0 <= index < len(events):
        return events[index][0]
    return None


def format_resource_ledger(
    ledger: ResourceLedger,
) -> str:
    income_by_date = _entries_by_date(ledger.income_entries)
    construction_by_date = {
        entry.date: entry
        for entry in ledger.construction_entries
    }
    recruitment_by_date = _entries_by_date(
        ledger.recruitment_entries
    )

    sections: list[str] = []
    for daily in ledger.daily_balances:
        lines = [format_game_date(daily.date)]
        if daily.date.day == 1:
            lines.append("Week boundary")

        # Backend-certified daily order begins with all income entries.
        for entry in income_by_date.get(daily.date, ()):
            lines.extend(
                (
                    "Beginning-of-day income",
                    "  Source: "
                    f"{format_building_key(entry.building)}",
                    "  Amount: "
                    f"{format_income_amount(entry.amount)}",
                )
            )

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
        "Combined spending: "
        f"{format_resource_vector(ledger.combined_total)}",
        "Income total: "
        f"{format_resource_vector(ledger.income_total)}",
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
            )
        )
        trigger = _deficit_trigger(ledger)
        if trigger is not None:
            summary.append(f"Triggering entry: {trigger}")

    return "\n\n".join(
        sections + ["\n".join(summary)]
    )
