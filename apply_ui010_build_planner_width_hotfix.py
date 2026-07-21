from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WORKSPACE = (
    ROOT / "olden_db" / "olden_db" / "desktop" / "views"
    / "scenario_comparison_workspace_view.py"
)
PLANNER = (
    ROOT / "olden_db" / "olden_db" / "desktop" / "views"
    / "planner_view.py"
)
TEST = (
    ROOT / "olden_db" / "scripts"
    / "test_desktop_scenario_comparison_workspace.py"
)


def replace_value(
    text: str,
    candidates: tuple[str, ...],
    replacement: str,
    label: str,
) -> str:
    if replacement in text:
        print(f"SKIP: {label} already applied")
        return text
    matches = [candidate for candidate in candidates if candidate in text]
    if len(matches) != 1:
        raise RuntimeError(
            f"{label}: expected one supported source form, found {len(matches)}"
        )
    print(f"UPDATED: {label}")
    return text.replace(matches[0], replacement, 1)


def patch_workspace_width() -> None:
    text = WORKSPACE.read_text(encoding="utf-8")
    text = replace_value(
        text,
        (
            "        panel = ttk.LabelFrame(self._content, padding=5, width=680)\n",
            "        panel = ttk.LabelFrame(self._content, padding=8, width=820)\n",
        ),
        "        panel = ttk.LabelFrame(self._content, padding=5, width=480)\n",
        "Build Planner panel width",
    )
    text = replace_value(
        text,
        (
            "            self._content.columnconfigure(column, minsize=680)\n",
            "            self._content.columnconfigure(column, minsize=820)\n",
        ),
        "            self._content.columnconfigure(column, minsize=480)\n",
        "Build Planner column minimum width",
    )
    WORKSPACE.write_text(text, encoding="utf-8")


def patch_planner_width_drivers() -> None:
    text = PLANNER.read_text(encoding="utf-8")

    # Summary, status, timeline-detail, and diagnostic labels use these
    # wrap lengths. Reducing them prevents text widgets from requesting the
    # previous wide panel.
    if "wraplength=500" not in text:
        count = text.count("wraplength=720")
        if count < 3:
            raise RuntimeError(
                f"planner wrap lengths: expected at least 3, found {count}"
            )
        text = text.replace("wraplength=720", "wraplength=500")
        print(f"UPDATED: {count} planner wrap lengths")
    else:
        print("SKIP: planner wrap lengths already reduced")

    heading_replacements = (
        (
            '("position", "Position", 92)',
            '("position", "Position", 65)',
            "timeline position width",
        ),
        (
            '("building", "Building", 180)',
            '("building", "Building", 125)',
            "timeline building width",
        ),
        (
            '("level", "Level", 70)',
            '("level", "Level", 52)',
            "timeline level width",
        ),
        (
            '("date", "Construction date", 210)',
            '("date", "Construction date", 145)',
            "timeline date width",
        ),
        (
            '("cost", "Individual cost", 160)',
            '("cost", "Individual cost", 112)',
            "timeline individual cost width",
        ),
        (
            '("cumulative", "Cumulative cost", 170)',
            '("cumulative", "Cumulative cost", 120)',
            "timeline cumulative cost width",
        ),
    )
    for old, new, label in heading_replacements:
        if new in text:
            print(f"SKIP: {label} already applied")
        elif old in text:
            text = text.replace(old, new, 1)
            print(f"UPDATED: {label}")
        else:
            raise RuntimeError(f"Could not locate {label}")

    # The target selector frame should use only its natural requested width
    # inside the reduced panel, while still allowing its contents to fit.
    if 'target.columnconfigure(1, weight=1)' in text:
        text = text.replace(
            'target.columnconfigure(1, weight=1)',
            'target.columnconfigure(1, weight=0)',
            1,
        )
        print("UPDATED: target controls natural-width column")
    elif 'target.columnconfigure(1, weight=0)' in text:
        print("SKIP: target controls natural-width column already applied")
    else:
        raise RuntimeError("Could not locate target control column configuration")

    PLANNER.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    if "def test_build_planner_horizontal_density_reduction()" in text:
        print("SKIP: horizontal density regression test already applied")
        return

    marker = "def test_view_is_passive() -> None:\n"
    if marker not in text:
        raise RuntimeError("Could not locate focused-test insertion point")

    TEST.write_text(
        text.replace(marker, 'def test_build_planner_horizontal_density_reduction() -> None:\n    workspace = VIEW.read_text(encoding="utf-8")\n    planner = (\n        ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"\n    ).read_text(encoding="utf-8")\n    require(\n        "minsize=480" in workspace,\n        "Scenario workspace columns must use the reduced planner width",\n    )\n    require(\n        "wraplength=500" in planner,\n        "Planner summaries must wrap within the reduced width",\n    )\n    require(\n        \'("building", "Building", 125)\' in planner,\n        "Timeline columns must fit the reduced planner width",\n    )\n\n\n' + marker, 1),
        encoding="utf-8",
    )
    print("UPDATED: horizontal density regression test")


def validate() -> None:
    for path in (WORKSPACE, PLANNER, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_workspace_width()
    patch_planner_width_drivers()
    patch_test()
    validate()
    print("Build Planner horizontal-density hotfix applied successfully.")


if __name__ == "__main__":
    main()
