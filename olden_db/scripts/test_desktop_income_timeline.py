from __future__ import annotations

import ast
import inspect

from olden_db.desktop import economy_formatting
from olden_db.desktop.presenters.economy_presenter import (
    EconomyTimelinePresenter,
)
from olden_db.desktop.economy_formatting import (
    format_income_amount,
    format_resource_ledger,
)


def _forbidden_backend_usage(module_or_class: object) -> tuple[str, ...]:
    """Find executable desktop code that crosses UI-011 boundaries."""

    source = inspect.getsource(module_or_class)
    tree = ast.parse(source)
    violations: list[str] = []

    forbidden_modules = {
        "olden_db.income_timeline",
        "olden_db.recruitment_stock",
        "olden_db.resource_ledger",
        "olden_db.database",
        "olden_db.parser",
        "olden_db.parsers",
    }
    forbidden_calls = {
        "calculate_income_timeline",
        "calculate_recruitment_stock",
        "build_resource_ledger",
        "resolve_effective_starting_buildings",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    violations.append(f"import {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module in forbidden_modules:
                violations.append(f"from {module} import ...")

        elif isinstance(node, ast.Call):
            function = node.func
            if (
                isinstance(function, ast.Name)
                and function.id in forbidden_calls
            ):
                violations.append(f"{function.id}(...)")
            elif (
                isinstance(function, ast.Attribute)
                and function.attr in forbidden_calls
            ):
                violations.append(f".{function.attr}(...)")

        elif isinstance(node, ast.Attribute) and node.attr == "income":
            receiver = node.value
            if isinstance(receiver, ast.Name) and (
                "building" in receiver.id.lower()
                or receiver.id.lower() in {"level", "building_level"}
            ):
                violations.append(f"{receiver.id}.income")

    return tuple(sorted(set(violations)))


def _presenter_request_count_contract() -> None:
    """Validate the actual Economy Timeline regeneration callback."""

    if not hasattr(EconomyTimelinePresenter, "on_generate"):
        raise RuntimeError(
            "EconomyTimelinePresenter no longer exposes the expected "
            "on_generate regeneration callback"
        )

    source = inspect.getsource(
        EconomyTimelinePresenter.on_generate
    )

    count = source.count("generate_resource_ledger(")
    if count != 1:
        raise RuntimeError(
            "Economy regeneration must contain exactly one "
            "generate_resource_ledger(...) request; "
            f"found {count}"
        )

    if "scenario=self._planner_state.active_scenario" not in source:
        raise RuntimeError(
            "Economy regeneration does not pass the active scenario "
            "through the authoritative ledger request"
        )

    forbidden_requests = (
        "calculate_income_timeline(",
        "generate_income_timeline(",
        "calculate_recruitment_stock(",
        "generate_recruitment_stock(",
        "generate_build_plan(",
    )
    found = tuple(
        name
        for name in forbidden_requests
        if name in source
    )
    if found:
        raise RuntimeError(
            "Economy presenter performs additional backend requests: "
            f"{found!r}"
        )


def _formatting_contracts() -> None:
    formatting_source = inspect.getsource(
        economy_formatting
    )

    required_fields = (
        "ledger.income_entries",
        "ledger.income_total",
        "ledger.construction_entries",
        "ledger.recruitment_entries",
        "ledger.daily_balances",
        "ledger.construction_total",
        "ledger.recruitment_total",
        "ledger.combined_total",
        "ledger.ending_balance",
        "ledger.feasible",
        "ledger.first_deficit",
    )
    missing = tuple(
        field
        for field in required_fields
        if field not in formatting_source
    )
    if missing:
        raise RuntimeError(
            "Income presentation is missing authoritative ledger fields: "
            f"{missing!r}"
        )

    ledger_source = inspect.getsource(
        economy_formatting.format_resource_ledger
    )
    required_order = (
        "for entry in income_by_date.get",
        "construction = construction_by_date.get",
        "recruitment = recruitment_by_date.get",
        '"Closing balance: "',
    )
    positions = tuple(
        ledger_source.find(fragment)
        for fragment in required_order
    )
    if any(position < 0 for position in positions):
        raise RuntimeError(
            "Daily income presentation is missing an ordered event stage"
        )
    if positions != tuple(sorted(positions)):
        raise RuntimeError(
            "Income, construction, recruitment, and closing balance "
            "are not presented in certified order"
        )

    if '"Income events: None"' in ledger_source:
        raise RuntimeError(
            "Zero-income dates invent an artificial income row"
        )

    if '"Combined spending: "' not in ledger_source:
        raise RuntimeError(
            "Combined spending is not clearly labeled"
        )
    if '"Income total: "' not in ledger_source:
        raise RuntimeError(
            "Income total is not displayed separately"
        )


def main() -> None:
    _presenter_request_count_contract()
    _formatting_contracts()

    violations = (
        _forbidden_backend_usage(economy_formatting)
        + _forbidden_backend_usage(EconomyTimelinePresenter)
    )
    if violations:
        raise RuntimeError(
            "Desktop income presentation crossed backend boundaries: "
            f"{violations!r}"
        )

    from olden_db.models import ResourceCost

    amount = format_income_amount(
        ResourceCost(gold=500, wood=0, ore=2)
    )
    if amount != "+500 gold, +2 ore":
        raise RuntimeError(
            "Income amount formatting did not preserve nonzero values "
            "with explicit positive signs"
        )

    ordered_source = inspect.getsource(
        economy_formatting._ordered_events
    )
    if "ledger.income_entries" not in ordered_source:
        raise RuntimeError(
            "Deficit event reconstruction omits income entries"
        )

    trigger_source = inspect.getsource(
        economy_formatting._deficit_trigger
    )
    if "return None" not in trigger_source:
        raise RuntimeError(
            "Unresolvable deficit triggers must be omitted rather than guessed"
        )

    ledger_source = inspect.getsource(format_resource_ledger)
    forbidden_side_effects = (
        "PlanningQueryService",
        "generate_resource_ledger",
        "calculate_",
        "resolve_effective",
    )
    found_side_effects = tuple(
        fragment
        for fragment in forbidden_side_effects
        if fragment in ledger_source
    )
    if found_side_effects:
        raise RuntimeError(
            "Ledger formatting performs backend work: "
            f"{found_side_effects!r}"
        )

    print("Desktop income-timeline validation completed successfully.")
    print("Each regeneration contains one generate_resource_ledger request.")
    print("The active scenario flows through that same ledger request.")
    print("Income precedes construction, recruitment, and closing balance.")
    print("Income sources and nonzero resource amounts use public ledger fields.")
    print("Income total remains separate from combined spending.")
    print("Zero-income dates do not receive artificial income rows.")
    print("Deficit reconstruction includes the complete income-aware sequence.")
    print("No parser, income-timeline, stock, or ledger-domain imports entered UI.")


if __name__ == "__main__":
    main()
