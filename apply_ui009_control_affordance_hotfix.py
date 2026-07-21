from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLANNER = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
SCROLLING = ROOT / "olden_db" / "olden_db" / "desktop" / "scrolling.py"
COMPARISON = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"


def patch_comboboxes() -> None:
    text = PLANNER.read_text(encoding="utf-8")
    helper_anchor = "    def set_factions(self, factions: tuple[str, ...]) -> None:\n"
    helper = '''    @staticmethod
    def _fit_combobox_to_values(
        selector: ttk.Combobox,
        values,
        *,
        minimum: int = 8,
        maximum: int = 42,
    ) -> None:
        displayed = tuple(str(value) for value in values)
        longest = max((len(value) for value in displayed), default=minimum)
        selector.configure(width=max(minimum, min(maximum, longest + 2)))

'''
    if "_fit_combobox_to_values(" not in text:
        if helper_anchor not in text:
            raise RuntimeError("Could not locate selector-method anchor")
        text = text.replace(helper_anchor, helper + helper_anchor, 1)
        print("UPDATED: adaptive combobox sizing helper")

    old = '''    def set_factions(self, factions: tuple[str, ...]) -> None:
        self._faction_selector.configure(values=factions)
'''
    new = '''    def set_factions(self, factions: tuple[str, ...]) -> None:
        self._faction_selector.configure(values=factions)
        self._fit_combobox_to_values(self._faction_selector, factions)
'''
    if new not in text:
        if old not in text: raise RuntimeError("Could not locate faction selector method")
        text = text.replace(old, new, 1)

    old = '''    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        self._building_var.set("")
        self._building_selector.configure(values=buildings, state="readonly" if buildings else "disabled")
'''
    new = '''    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        self._building_var.set("")
        self._building_selector.configure(
            values=buildings,
            state="readonly" if buildings else "disabled",
        )
        self._fit_combobox_to_values(self._building_selector, buildings)
'''
    if new not in text:
        if old not in text: raise RuntimeError("Could not locate building selector method")
        text = text.replace(old, new, 1)

    old = '''    def set_levels(self, levels: tuple[int, ...]) -> None:
        self._level_var.set("")
        self._level_selector.configure(
            values=tuple(str(level) for level in levels),
            state="readonly" if levels else "disabled",
        )
'''
    new = '''    def set_levels(self, levels: tuple[int, ...]) -> None:
        self._level_var.set("")
        displayed_levels = tuple(str(level) for level in levels)
        self._level_selector.configure(
            values=displayed_levels,
            state="readonly" if levels else "disabled",
        )
        self._fit_combobox_to_values(
            self._level_selector,
            displayed_levels,
            minimum=6,
            maximum=12,
        )
'''
    if new not in text:
        if old not in text: raise RuntimeError("Could not locate level selector method")
        text = text.replace(old, new, 1)

    for selector in ("_faction_selector", "_building_selector", "_level_selector"):
        start = text.find(f"self.{selector}.grid(")
        if start == -1: raise RuntimeError(f"Could not locate {selector} grid statement")
        end = text.find("\n", start)
        line = text[start:end]
        if 'sticky="ew"' in line:
            text = text[:start] + line.replace('sticky="ew"', 'sticky="w"') + text[end:]

    PLANNER.write_text(text, encoding="utf-8")


def patch_scrollbars() -> None:
    text = SCROLLING.read_text(encoding="utf-8")
    old = '''        self.scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )
'''
    new = '''        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            width=18,
            borderwidth=1,
            relief="raised",
        )
'''
    if new not in text:
        if old not in text: raise RuntimeError("Could not locate outer workspace scrollbar")
        text = text.replace(old, new, 1)
    SCROLLING.write_text(text, encoding="utf-8")

    text = PLANNER.read_text(encoding="utf-8")
    old = '        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self._scenario_canvas.yview)\n'
    new = '''        scrollbar = tk.Scrollbar(
            shell,
            orient="vertical",
            command=self._scenario_canvas.yview,
            width=18,
            borderwidth=1,
            relief="raised",
        )
'''
    if new not in text and old in text:
        text = text.replace(old, new, 1)

    old = '''        timeline_scrollbar = ttk.Scrollbar(
            timeline,
            orient="vertical",
            command=self._timeline_tree.yview,
        )
'''
    new = '''        timeline_scrollbar = tk.Scrollbar(
            timeline,
            orient="vertical",
            command=self._timeline_tree.yview,
            width=18,
            borderwidth=1,
            relief="raised",
        )
'''
    if new not in text and old in text:
        text = text.replace(old, new, 1)

    if "self._diagnostic_scrollbar = ttk.Scrollbar(" in text:
        text = text.replace("self._diagnostic_scrollbar = ttk.Scrollbar(", "self._diagnostic_scrollbar = tk.Scrollbar(", 1)
        anchor = "            command=self._diagnostic_canvas.yview,\n"
        pos = text.find(anchor, text.find("self._diagnostic_scrollbar = tk.Scrollbar("))
        if pos != -1:
            insert = pos + len(anchor)
            text = text[:insert] + '            width=18,\n            borderwidth=1,\n            relief="raised",\n' + text[insert:]
    PLANNER.write_text(text, encoding="utf-8")

    text = COMPARISON.read_text(encoding="utf-8")
    compact = 'scroll=ttk.Scrollbar(shell,orient="horizontal",command=self._canvas.xview)'
    if compact in text:
        text = text.replace(compact, 'scroll=tk.Scrollbar(shell,orient="horizontal",command=self._canvas.xview,width=18,borderwidth=1,relief="raised")', 1)
    formatted = '''        self._xscroll = ttk.Scrollbar(
            shell,
            orient="horizontal",
            command=self._canvas.xview,
        )
'''
    replacement = '''        self._xscroll = tk.Scrollbar(
            shell,
            orient="horizontal",
            command=self._canvas.xview,
            width=18,
            borderwidth=1,
            relief="raised",
        )
'''
    if formatted in text:
        text = text.replace(formatted, replacement, 1)
    COMPARISON.write_text(text, encoding="utf-8")


def validate() -> None:
    for path in (PLANNER, SCROLLING, COMPARISON, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_comboboxes()
    patch_scrollbars()
    validate()
    print("UI-009 control sizing and scrollbar hotfix applied successfully.")


if __name__ == "__main__":
    main()
