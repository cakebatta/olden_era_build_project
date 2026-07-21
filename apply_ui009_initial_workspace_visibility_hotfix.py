from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label} already applied")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed block, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def patch_view() -> None:
    replace_once(
        VIEW,
        '        panel = ttk.LabelFrame(self._content, padding=8)\n        panel.grid(row=0, column=len(self._panels), sticky="ns", padx=(0, 12))\n        panel.configure(width=820)\n        panel.grid_propagate(False)\n        panel.columnconfigure(0, weight=1)\n        panel.rowconfigure(1, weight=1)\n',
        '        panel = ttk.LabelFrame(self._content, padding=8)\n        panel.grid(\n            row=0,\n            column=len(self._panels),\n            sticky="nsew",\n            padx=(0, 12),\n        )\n        # Let the composed PlannerView determine the panel\'s requested height.\n        # Disabling geometry propagation with only a fixed width collapses the\n        # panel vertically on startup, leaving the comparison area empty.\n        panel.grid_propagate(True)\n        panel.columnconfigure(0, weight=1)\n        panel.rowconfigure(1, weight=1)\n',
        "workspace panel geometry propagation",
    )
    replace_once(
        VIEW,
        '        for column, member in enumerate(presentation.members):\n            panel = self._panels[member.workspace_id]\n            panel.grid_configure(column=column)\n',
        '        for column, member in enumerate(presentation.members):\n            panel = self._panels[member.workspace_id]\n            panel.grid_configure(column=column)\n            self._content.columnconfigure(column, minsize=820)\n',
        "workspace panel minimum width",
    )


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    if "def test_workspace_panels_preserve_composed_view_height()" in text:
        print("SKIP: workspace panel geometry regression test already applied")
        return
    marker = "def test_view_is_passive() -> None:\n"
    if marker not in text:
        raise RuntimeError("test insertion anchor not found")
    TEST.write_text(
        text.replace(marker, 'def test_workspace_panels_preserve_composed_view_height() -> None:\n    text = VIEW.read_text(encoding="utf-8")\n    require(\n        "panel.grid_propagate(False)" not in text,\n        "Workspace panel must not suppress the composed PlannerView height",\n    )\n    require(\n        "panel.grid_propagate(True)" in text,\n        "Workspace panel must allow geometry propagation",\n    )\n    require(\n        "self._content.columnconfigure(column, minsize=820)" in text,\n        "Workspace columns must retain a usable comparison width",\n    )\n\n\n' + marker, 1),
        encoding="utf-8",
    )
    print("UPDATED: workspace panel geometry regression test")


def validate() -> None:
    for path in (VIEW, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_view()
    patch_test()
    validate()
    print("UI-009 initial workspace visibility hotfix applied successfully.")


if __name__ == "__main__":
    main()
