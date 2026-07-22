from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRESENTER = ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
ARCH = ROOT / "docs" / "desktop_application_architecture.md"
QUERY_DOC = ROOT / "docs" / "query_layer.md"
DISPLAY = ROOT / "olden_db" / "olden_db" / "desktop" / "display_names.py"
QUERY = ROOT / "olden_db" / "olden_db" / "query.py"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label} already applied")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed anchor, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def patch_presenter() -> None:
    text = PRESENTER.read_text(encoding="utf-8")

    simple = [
        (
            "self._view.set_buildings(sids)",
            "self._view.set_buildings(self._building_options(faction, sids))",
            "building selector projection",
        ),
        (
            "self._view.set_starting_buildings(candidates,",
            "self._view.set_starting_buildings(self._starting_building_presentations(candidates),",
            "candidate starting-building projection",
        ),
        (
            "self._view.set_starting_buildings(self._state.scenario_candidates,",
            "self._view.set_starting_buildings(self._starting_building_presentations(self._state.scenario_candidates),",
            "state starting-building projection",
        ),
        (
            'self._set_status(f"Faction selected: {faction}. Select a building.")',
            'self._set_status(f"Faction selected: {self._faction_display(faction)}. Select a building.")',
            "localized faction status",
        ),
        (
            'self._set_status(f"Building selected: {sid}. Select a level.")',
            'self._set_status(f"Building selected: {self._building_family_display(faction, sid)}. Select a level.")',
            "localized building status",
        ),
        (
            "faction_text = selection.faction if selection is not None else self._state.selected_faction",
            "faction_text = (self._faction_display(selection.faction) if selection is not None else (self._faction_display(self._state.selected_faction) if self._state.selected_faction else None))",
            "localized workspace faction text",
        ),
        (
            'else f"{selection.faction} / {target_text} / starts {starting_date_text}"',
            'else f"{faction_text} / {target_text} / starts {starting_date_text}"',
            "localized selection summary",
        ),
    ]

    for old, new, label in simple:
        if new in text:
            print(f"SKIP: {label} already applied")
            continue
        count = text.count(old)
        if count:
            text = text.replace(old, new)
            print(f"UPDATED: {label} ({count} occurrence(s))")
        else:
            print(f"NOTE: {label} source form not present")

    hydration_old = (
        "self._view.set_buildings(self._building_options(faction, sids))\n"
        "        self._view.set_levels(levels)\n"
        "        self._view.set_selection_values(\n"
        "            selection.faction,"
    )
    hydration_new = (
        "self._view.set_buildings(self._building_options(selection.faction, sids))\n"
        "        self._view.set_levels(levels)\n"
        "        self._view.set_selection_values(\n"
        "            selection.faction,"
    )
    if hydration_new not in text and hydration_old in text:
        text = text.replace(hydration_old, hydration_new, 1)
        print("UPDATED: restored-selection building projection")

    helpers = '''    def _faction_options(
        self,
        factions: tuple[str, ...],
    ) -> tuple[CanonicalDisplayOption, ...]:
        return tuple(
            CanonicalDisplayOption(item, self._faction_display(item))
            for item in factions
        )

    def _building_options(
        self,
        faction: str,
        sids: tuple[str, ...],
    ) -> tuple[CanonicalDisplayOption, ...]:
        return tuple(
            CanonicalDisplayOption(
                sid,
                self._building_family_display(faction, sid),
            )
            for sid in sids
        )

    def _building_family_display(self, faction: str, sid: str) -> str:
        levels = self._service.list_building_levels(faction, sid)
        return self._display_text(BuildingKey(faction, sid, levels[0]))

    def _starting_building_presentations(
        self,
        buildings: tuple[BuildingLevel, ...],
    ) -> tuple[StartingBuildingPresentation, ...]:
        return tuple(
            StartingBuildingPresentation(
                building=item.key,
                display_name=self._display_text(item.key),
                level_text=str(item.key.level),
                canonical_state_text=(
                    "available" if item.constructed_on_start else "must construct"
                ),
                constructed_on_start=item.constructed_on_start,
            )
            for item in buildings
        )

    def _faction_display(self, faction: str) -> str:
        cached = self._faction_text_cache.get(faction)
        if cached is None:
            cached = self._service.get_faction_display_text(faction)
            self._faction_text_cache[faction] = cached
        return cached

'''

    if "    def _faction_options(" not in text:
        anchor = "    def _display_text(self, key: BuildingKey) -> str:\n"
        if anchor not in text:
            raise RuntimeError("Could not locate _display_text(self, key: BuildingKey)")
        text = text.replace(anchor, helpers + anchor, 1)
        print("UPDATED: presenter display-name helpers")

    PRESENTER.write_text(text, encoding="utf-8")


def patch_view() -> None:
    replace_once(
        VIEW,
        "from ..formatting import (\n",
        "from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\nfrom ..formatting import (\n",
        "view display imports",
    )
    replace_once(
        VIEW,
        "        self._faction_var = tk.StringVar()\n        self._building_var = tk.StringVar()\n",
        "        self._faction_var = tk.StringVar()\n        self._building_var = tk.StringVar()\n        self._faction_display_to_id: dict[str, str] = {}\n        self._faction_id_to_display: dict[str, str] = {}\n        self._building_display_to_id: dict[str, str] = {}\n        self._building_id_to_display: dict[str, str] = {}\n",
        "selector identity maps",
    )
    replace_once(
        VIEW,
        'ttk.Label(target, text="Building SID")',
        'ttk.Label(target, text="Target Building")',
        "target-building label",
    )

    old = '''    def set_factions(self, factions: tuple[str, ...]) -> None:
        self._faction_selector.configure(values=factions)
        self._fit_combobox_to_values(self._faction_selector, factions)

    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        self._building_var.set("")
        self._building_selector.configure(
            values=buildings,
            state="readonly" if buildings else "disabled",
        )
        self._fit_combobox_to_values(self._building_selector, buildings)
'''
    new = '''    def set_factions(
        self,
        factions: tuple[CanonicalDisplayOption, ...],
    ) -> None:
        self._faction_display_to_id = {
            item.display_name: item.canonical_id for item in factions
        }
        self._faction_id_to_display = {
            item.canonical_id: item.display_name for item in factions
        }
        values = tuple(item.display_name for item in factions)
        self._faction_selector.configure(values=values)
        self._fit_combobox_to_values(self._faction_selector, values)

    def set_buildings(
        self,
        buildings: tuple[CanonicalDisplayOption, ...],
    ) -> None:
        self._building_var.set("")
        self._building_display_to_id = {
            item.display_name: item.canonical_id for item in buildings
        }
        self._building_id_to_display = {
            item.canonical_id: item.display_name for item in buildings
        }
        values = tuple(item.display_name for item in buildings)
        self._building_selector.configure(
            values=values,
            state="readonly" if values else "disabled",
        )
        self._fit_combobox_to_values(self._building_selector, values)
'''
    replace_once(VIEW, old, new, "display-ready selectors")

    replace_once(
        VIEW,
        "        self._faction_var.set(faction)\n        self._building_var.set(sid)\n",
        "        self._faction_var.set(self._faction_id_to_display.get(faction, faction))\n        self._building_var.set(self._building_id_to_display.get(sid, sid))\n",
        "localized selection restoration",
    )

    old_start = '''        buildings: tuple[BuildingLevel, ...],
        scenario: PlanningScenario,
    ) -> None:
        self._clear_scenario_content()
        overrides = {
            override.building: override.available_at_start
            for override in scenario.starting_building_overrides
        }
        for row, building in enumerate(buildings):
            effective = overrides.get(building.key, building.constructed_on_start)
            variable = tk.BooleanVar(value=effective)
            self._scenario_vars[building.key] = variable
            canonical = "available" if building.constructed_on_start else "must construct"
            ttk.Checkbutton(
                self._scenario_content,
                text=f"{building.key.sid} level {building.key.level} — Canonical: {canonical}",
                variable=variable,
                command=lambda key=building.key, var=variable: self._handle_starting_building_changed(
                    key, var.get()
                ),
            ).grid(row=row, column=0, sticky="w", pady=2)
'''
    new_start = '''        buildings: tuple[StartingBuildingPresentation, ...],
        scenario: PlanningScenario,
    ) -> None:
        self._clear_scenario_content()
        overrides = {
            override.building: override.available_at_start
            for override in scenario.starting_building_overrides
        }
        for row, item in enumerate(buildings):
            effective = overrides.get(item.building, item.constructed_on_start)
            variable = tk.BooleanVar(value=effective)
            self._scenario_vars[item.building] = variable
            ttk.Checkbutton(
                self._scenario_content,
                text=(
                    f"{item.display_name} level {item.level_text} — "
                    f"Canonical: {item.canonical_state_text}"
                ),
                variable=variable,
                command=lambda key=item.building, var=variable: (
                    self._handle_starting_building_changed(key, var.get())
                ),
            ).grid(row=row, column=0, sticky="w", pady=2)
'''
    replace_once(VIEW, old_start, new_start, "localized starting-building rows")

    replace_once(
        VIEW,
        "            self._on_faction_changed(self._faction_var.get())\n",
        "            display = self._faction_var.get()\n            self._on_faction_changed(self._faction_display_to_id[display])\n",
        "canonical faction callback",
    )
    replace_once(
        VIEW,
        "            self._on_building_changed(self._building_var.get())\n",
        "            display = self._building_var.get()\n            self._on_building_changed(self._building_display_to_id[display])\n",
        "canonical building callback",
    )


def patch_docs() -> None:
    section = """## Canonical Game Name Presentation (UI-011)

Canonical identities remain backend-owned. The Query Layer resolves locale-aware
names with deterministic fallback. Presenters produce immutable canonical/display
options, and views map display text back to canonical identities for callbacks.
Persistence, equality, comparison correlation, and planning remain canonical.
"""
    for path in (ARCH, QUERY_DOC):
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        if "## Canonical Game Name Presentation (UI-011)" in text:
            print(f"SKIP: {path.relative_to(ROOT)} already updated")
            continue
        path.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8")
        print(f"UPDATED: {path.relative_to(ROOT)}")


def validate() -> None:
    for path in (QUERY, PRESENTER, VIEW, DISPLAY):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_presenter()
    patch_view()
    patch_docs()
    validate()
    print("UI-011 resume hotfix applied successfully.")


if __name__ == "__main__":
    main()
