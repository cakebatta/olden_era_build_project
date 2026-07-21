from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLANNER = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
WORKSPACE = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"
COMPARISON = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "build_plan_comparison_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"


def replace_all_reviewed(path: Path, replacements) -> None:
    text = path.read_text(encoding="utf-8")
    for old, new, label in replacements:
        if new in text:
            print(f"SKIP: {label} already applied")
            continue
        count = text.count(old)
        if count != 1:
            raise RuntimeError(
                f"{label}: expected one reviewed occurrence, found {count}"
            )
        text = text.replace(old, new, 1)
        print(f"UPDATED: {label}")
    path.write_text(text, encoding="utf-8")


def patch_workspace_layout() -> None:
    replace_all_reviewed(
        WORKSPACE,
        (
            ("        super().__init__(parent, padding=14)\n",
             "        super().__init__(parent, padding=8)\n",
             "comparison workspace outer padding"),
            ('        self._role_summary.grid(row=1, column=0, sticky="w", pady=(8, 10))\n',
             '        self._role_summary.grid(row=1, column=0, sticky="w", pady=(4, 6))\n',
             "comparison role spacing"),
            ("        panel = ttk.LabelFrame(self._content, padding=8, width=820)\n",
             "        panel = ttk.LabelFrame(self._content, padding=5, width=680)\n",
             "workspace panel width and padding"),
            ("            padx=(0, 12),\n",
             "            padx=(0, 8),\n",
             "workspace panel separation"),
            ('        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))\n',
             '        controls.grid(row=0, column=0, sticky="ew", pady=(0, 4))\n',
             "workspace controls spacing"),
            ("            self._content.columnconfigure(column, minsize=820)\n",
             "            self._content.columnconfigure(column, minsize=680)\n",
             "workspace column minimum width"),
        ),
    )


def patch_planner_density() -> None:
    replace_all_reviewed(
        PLANNER,
        (
            ("        super().__init__(parent, padding=24)\n",
             "        super().__init__(parent, padding=12)\n",
             "planner outer padding"),
            ('        target = ttk.LabelFrame(self, text="Target Selection", padding=16)\n',
             '        target = ttk.LabelFrame(self, text="Target Selection", padding=10)\n',
             "target selection padding"),
            ('        target.grid(row=1, column=0, sticky="ew", pady=(18, 0))\n',
             '        target.grid(row=1, column=0, sticky="ew", pady=(10, 0))\n',
             "target selection spacing"),
            ('        scenario.grid(row=2, column=0, sticky="ew", pady=(18, 0))\n',
             '        scenario.grid(row=2, column=0, sticky="ew", pady=(10, 0))\n',
             "starting buildings spacing"),
            ('        shell.grid(row=1, column=0, sticky="ew", pady=(10, 0))\n',
             '        shell.grid(row=1, column=0, sticky="ew", pady=(6, 0))\n',
             "starting buildings internal spacing"),
            ("        self._scenario_canvas = tk.Canvas(shell, height=180, highlightthickness=0)\n",
             "        self._scenario_canvas = tk.Canvas(shell, height=140, highlightthickness=0)\n",
             "starting buildings viewport height"),
            ('        results.grid(row=3, column=0, sticky="nsew", pady=(18, 0))\n',
             '        results.grid(row=3, column=0, sticky="nsew", pady=(10, 0))\n',
             "planning results spacing"),
        ),
    )


def patch_comparison_density() -> None:
    if not COMPARISON.exists():
        print("NOTE: UI-010 comparison view not found; skipped its compact pass")
        return
    replace_all_reviewed(
        COMPARISON,
        (
            ('        super().__init__(parent, text="Build Plan Comparison", padding=12)\n',
             '        super().__init__(parent, text="Build Plan Comparison", padding=8)\n',
             "comparison panel padding"),
            ('        ).grid(row=1, column=0, sticky="ew", pady=(4, 8))\n',
             '        ).grid(row=1, column=0, sticky="ew", pady=(3, 5))\n',
             "comparison heading spacing"),
            ('        table_shell.grid(row=3, column=0, sticky="nsew", pady=(10, 0))\n',
             '        table_shell.grid(row=3, column=0, sticky="nsew", pady=(6, 0))\n',
             "aligned table spacing"),
            ("            height=14,\n",
             "            height=10,\n",
             "aligned comparison viewport height"),
            ('        actions.grid(row=4, column=0, sticky="ew", pady=(10, 0))\n',
             '        actions.grid(row=4, column=0, sticky="ew", pady=(6, 0))\n',
             "action groups spacing"),
            ("            height=6,\n",
             "            height=4,\n",
             "shared and exclusive viewport height"),
        ),
    )


def patch_regression_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    if "def test_compact_comparison_workspace_density()" in text:
        print("SKIP: compact-layout regression test already applied")
        return

    marker = "def test_view_is_passive() -> None:\n"
    if marker not in text:
        raise RuntimeError("Could not locate focused-test insertion point")

    TEST.write_text(
        text.replace(marker, 'def test_compact_comparison_workspace_density() -> None:\n    workspace = VIEW.read_text(encoding="utf-8")\n    planner = (\n        ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"\n    ).read_text(encoding="utf-8")\n    require(\n        "minsize=680" in workspace,\n        "Scenario columns must use the compact comparison width",\n    )\n    require(\n        "super().__init__(parent, padding=12)" in planner,\n        "Planner panels must use compact outer padding",\n    )\n    require(\n        "height=140" in planner,\n        "Starting-building viewport must preserve a compact height",\n    )\n\n\n' + marker, 1),
        encoding="utf-8",
    )
    print("UPDATED: compact-layout regression test")


def validate() -> None:
    paths = [PLANNER, WORKSPACE, TEST]
    if COMPARISON.exists():
        paths.append(COMPARISON)
    for path in paths:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_workspace_layout()
    patch_planner_density()
    patch_comparison_density()
    patch_regression_test()
    validate()
    print("UI compact-layout hotfix applied successfully.")


if __name__ == "__main__":
    main()
