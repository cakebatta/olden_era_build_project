from __future__ import annotations

from datetime import datetime, timezone
import inspect
from uuid import UUID

from olden_db.desktop.scenario_controller import ScenarioController
from olden_db.desktop.views.scenario_library_dialog import (
    ScenarioLibraryDialog,
    format_target,
    sorted_summaries,
)
from olden_db.desktop.views.scenario_manager_view import ScenarioManagerView
from olden_db.models import BuildingKey
from olden_db.scenario_persistence import ScenarioSummary


def _summary(
    scenario_id: str,
    name: str,
    faction: str,
    sid: str,
    level: int,
    hour: int,
    description: str = "",
) -> ScenarioSummary:
    return ScenarioSummary(
        scenario_id=UUID(scenario_id),
        name=name,
        description=description,
        modified_at=datetime(
            2026,
            7,
            17,
            hour,
            tzinfo=timezone.utc,
        ),
        faction=faction,
        target=BuildingKey(faction, sid, level),
    )


def main() -> None:
    early = _summary(
        "00000000-0000-0000-0000-000000000001",
        "Early Castle",
        "castle",
        "capitol",
        1,
        10,
        "Fast economy opening.",
    )
    arena = _summary(
        "00000000-0000-0000-0000-000000000002",
        "Arena Build",
        "necropolis",
        "mage_guild",
        2,
        11,
    )
    summaries = (early, arena)

    assert sorted_summaries(summaries, "name") == (arena, early)
    assert sorted_summaries(
        summaries,
        "modified",
        descending=True,
    ) == (arena, early)
    assert format_target(arena) == "mage_guild L2"

    dialog_source = inspect.getsource(ScenarioLibraryDialog)
    required_dialog_contracts = (
        "ttk.Treeview",
        'selectmode="browse"',
        'self.bind("<Escape>"',
        'self.bind("<Return>"',
        'self.tree.bind("<Double-1>"',
        "yscrollcommand",
        "summary.description",
        "summary.scenario_id",
    )
    missing = tuple(
        contract
        for contract in required_dialog_contracts
        if contract not in dialog_source
    )
    if missing:
        raise RuntimeError(
            f"Scenario Library contracts are missing: {missing!r}"
        )

    forbidden_dialog_fragments = (
        "LocalScenarioRepository",
        "get_scenario(",
        "list_scenarios(",
        "save_scenario(",
        "delete_scenario(",
        "Path(",
    )
    if any(
        fragment in dialog_source
        for fragment in forbidden_dialog_fragments
    ):
        raise RuntimeError(
            "Scenario Library owns repository or filesystem behavior"
        )

    chooser_source = inspect.getsource(
        ScenarioManagerView.choose_scenario
    )
    if "askinteger" in chooser_source:
        raise RuntimeError("Numeric scenario picker is still present")
    if "ScenarioLibraryDialog.choose" not in chooser_source:
        raise RuntimeError("Scenario Library dialog is not launched")

    open_source = inspect.getsource(ScenarioController.open)
    if "get_scenario(" not in open_source:
        raise RuntimeError(
            "ScenarioController no longer owns repository lookup"
        )
    if ".document" in chooser_source:
        raise RuntimeError("Scenario chooser returns or inspects documents")

    print("Desktop Scenario Library validation completed successfully.")
    print("The dialog receives immutable summaries and returns only an ID.")
    print("Open, Cancel, Enter, Escape, double-click, and sorting are present.")
    print("No repository or filesystem behavior is owned by the dialog.")


if __name__ == "__main__":
    main()
