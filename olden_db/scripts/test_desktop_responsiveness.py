from __future__ import annotations

import inspect

from olden_db.desktop import app
from olden_db.desktop.economy_formatting import (
    format_event_cost,
    format_resource_vector,
)
from olden_db.desktop.scrolling import (
    ScrollableWorkspace,
    WHEEL_SEQUENCES,
)
from olden_db.desktop.views.comparison_view import (
    COMPARISON_NARROW_BREAKPOINT,
    ComparisonView,
    comparison_layout_for_width,
)
from olden_db.models import ResourceCost


def main() -> None:
    if app.DEFAULT_ROOT_GEOMETRY != "1100x700":
        raise RuntimeError(
            "Default desktop geometry is not the required 1100x700"
        )
    if app.ROOT_MINIMUM_SIZE != (960, 640):
        raise RuntimeError(
            "Minimum desktop dimensions are not deliberately set"
        )

    app_source = inspect.getsource(app.DesktopApplication)
    required_shell_contracts = (
        'sticky="nsew"',
        "columnconfigure(1, weight=1)",
        "rowconfigure(1, weight=1)",
        "ScrollableWorkspace",
        'text="Build Planner"',
        'text="Economy Timeline"',
        'text="Plan Comparison"',
    )
    missing = tuple(
        contract
        for contract in required_shell_contracts
        if contract not in app_source
    )
    if missing:
        raise RuntimeError(
            f"Responsive shell contracts are missing: {missing!r}"
        )

    show_source = inspect.getsource(
        app.DesktopApplication.show
    )
    forbidden_state_changes = (
        "clear_recruitment",
        "clear_result",
        "replace_starting_resources",
        "generate_resource_ledger",
        "generate_decision_summary",
        "generate_build_plan",
    )
    if any(
        fragment in show_source
        for fragment in forbidden_state_changes
    ):
        raise RuntimeError(
            "Workspace switching performs workflow or backend work"
        )

    if WHEEL_SEQUENCES != (
        "<MouseWheel>",
        "<Button-4>",
        "<Button-5>",
    ):
        raise RuntimeError(
            "Shared scroll container does not support all wheel events"
        )

    scrolling_source = inspect.getsource(
        ScrollableWorkspace
    )
    if "bind_all" in scrolling_source:
        raise RuntimeError(
            "Scroll container uses a permanent global wheel binding"
        )
    required_cleanup = (
        "activate",
        "deactivate",
        "_clear_bindings",
        "unbind",
    )
    if any(
        item not in scrolling_source
        for item in required_cleanup
    ):
        raise RuntimeError(
            "Workspace wheel-binding cleanup is incomplete"
        )

    if comparison_layout_for_width(
        COMPARISON_NARROW_BREAKPOINT - 1
    ) != "narrow":
        raise RuntimeError(
            "Comparison does not enter narrow stacked layout"
        )
    if comparison_layout_for_width(
        COMPARISON_NARROW_BREAKPOINT
    ) != "wide":
        raise RuntimeError(
            "Comparison does not enter wide side-by-side layout"
        )

    comparison_source = inspect.getsource(ComparisonView)
    if "grid_forget" not in comparison_source:
        raise RuntimeError(
            "Comparison layout does not transition deterministically"
        )
    if "Compare Plans" not in comparison_source:
        raise RuntimeError(
            "Primary comparison action is not retained"
        )
    resize_source = inspect.getsource(
        ComparisonView._on_configure
    ) + inspect.getsource(
        ComparisonView._apply_layout
    )
    backend_fragments = (
        "service.",
        "generate_",
        "compare_plans",
        "QueryLayer",
    )
    if any(
        fragment in resize_source
        for fragment in backend_fragments
    ):
        raise RuntimeError(
            "Comparison resizing causes backend activity"
        )

    event_cost = ResourceCost(
        gold=1200,
        wood=0,
        ore=4,
    )
    compact = format_event_cost(event_cost)
    if compact != "gold: 1200, ore: 4":
        raise RuntimeError(
            "Economy event costs do not omit zero resources"
        )

    complete = format_resource_vector(event_cost)
    if "wood: 0" not in complete:
        raise RuntimeError(
            "Authoritative balances or totals lost zero resources"
        )

    print("Desktop responsiveness validation completed successfully.")
    print("Root geometry and minimum size match the layout standard.")
    print("Active workspaces expand through weighted nsew shell geometry.")
    print("Wheel bindings are scoped, cross-platform, and removable.")
    print("Comparison transitions deterministically between wide and narrow.")
    print("Resize and workspace switching perform no backend requests.")
    print("Primary actions remain present in responsive workspaces.")
    print("Economy event costs omit zeros without changing full balances.")


if __name__ == "__main__":
    main()
