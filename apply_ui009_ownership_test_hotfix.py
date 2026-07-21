from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_planning_workspace_presenter.py"
APP = ROOT / "olden_db" / "olden_db" / "desktop" / "app.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"SKIP: {label} already applied")
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed block, found {count}")
    print(f"UPDATED: {label}")
    return text.replace(old, new, 1)


def main() -> None:
    text = TEST.read_text(encoding="utf-8")
    text = replace_once(
        text,
        'def test_application_owns_single_workspace_and_coordinator() -> None:\n    text = source(APP)\n    require(text.count("PlanningWorkspace.create()") == 1, "Exactly one workspace required")\n    require(text.count("PlanningExecutionCoordinator(") == 1, "Exactly one coordinator required")\n    require("self.planning_workspace" in text, "Workspace must be application-owned")\n',
        'def test_application_owns_single_comparison_collection_and_coordinator() -> None:\n    text = source(APP)\n    require(\n        text.count("ScenarioComparisonCollection.create()") == 1,\n        "Exactly one application-scoped comparison collection required",\n    )\n    require(\n        text.count("ScenarioComparisonExecutionCoordinator(") == 1,\n        "Exactly one comparison execution coordinator required",\n    )\n    require(\n        "PlanningWorkspace.create()" not in text,\n        "Application must not construct workspaces outside the collection",\n    )\n    require(\n        "self.planning_workspace = (" in text\n        and "self.scenario_comparison_collection.workspace(" in text,\n        "Primary compatibility workspace must resolve from the collection",\n    )\n',
        "UI-006 ownership regression for UI-009 composition",
    )
    TEST.write_text(text, encoding="utf-8")

    ast.parse(TEST.read_text(encoding="utf-8"), filename=str(TEST))
    ast.parse(APP.read_text(encoding="utf-8"), filename=str(APP))
    print("PASS: updated regression-test syntax")
    print("UI-009 ownership regression hotfix applied.")


if __name__ == "__main__":
    main()
