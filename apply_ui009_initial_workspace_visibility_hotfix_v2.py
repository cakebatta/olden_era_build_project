from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")

    compact = (
        'panel.grid(row=0,column=len(self._panels),sticky="ns",padx=(0,12)); '
        'panel.grid_propagate(False)'
    )

    if "panel.grid_propagate(True)" in text:
        print("SKIP: workspace panel geometry propagation already applied")
    elif compact in text:
        text = text.replace(
            compact,
            'panel.grid(row=0,column=len(self._panels),sticky="nsew",padx=(0,12)); '
            'panel.grid_propagate(True)',
            1,
        )
        print("UPDATED: compact workspace panel geometry propagation")
    elif "panel.grid_propagate(False)" in text:
        text = text.replace(
            "panel.grid_propagate(False)",
            "panel.grid_propagate(True)",
            1,
        )
        text = text.replace('sticky="ns"', 'sticky="nsew"', 1)
        print("UPDATED: workspace panel geometry propagation")
    else:
        raise RuntimeError(
            "Could not locate the workspace panel geometry statement. "
            "Please provide scenario_comparison_workspace_view.py."
        )

    if "self._content.columnconfigure(column, minsize=820)" not in text:
        compact_anchor = (
            "            panel.grid_configure(column=column)\n"
            "            self._labels[member.workspace_id].set(member.label)\n"
        )
        formatted_anchor = (
            "            panel.grid_configure(column=column)\n"
            "            self._label_vars[member.workspace_id].set(member.label)\n"
        )
        if compact_anchor in text:
            text = text.replace(
                compact_anchor,
                "            panel.grid_configure(column=column)\n"
                "            self._content.columnconfigure(column, minsize=820)\n"
                "            self._labels[member.workspace_id].set(member.label)\n",
                1,
            )
            print("UPDATED: compact workspace minimum width")
        elif formatted_anchor in text:
            text = text.replace(
                formatted_anchor,
                "            panel.grid_configure(column=column)\n"
                "            self._content.columnconfigure(column, minsize=820)\n"
                "            self._label_vars[member.workspace_id].set(member.label)\n",
                1,
            )
            print("UPDATED: workspace minimum width")
        else:
            raise RuntimeError(
                "Could not locate the workspace render block. "
                "Please provide scenario_comparison_workspace_view.py."
            )
    else:
        print("SKIP: workspace minimum width already applied")

    VIEW.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    name = "def test_workspace_panels_preserve_composed_view_height()"
    if name in text:
        print("SKIP: workspace panel regression test already applied")
        return

    marker = "def test_view_is_passive() -> None:\n"
    if marker not in text:
        raise RuntimeError("Could not locate the focused-test insertion point")

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
    print("UI-009 initial workspace visibility hotfix v2 applied successfully.")


if __name__ == "__main__":
    main()
