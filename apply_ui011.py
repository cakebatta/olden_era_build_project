from __future__ import annotations
import ast
import subprocess
from pathlib import Path

EXPECTED='56e8d1fb01e493873516b9dc7c38fb57a61356e2'
ROOT=Path(__file__).resolve().parent
QUERY=ROOT/'olden_db'/'olden_db'/'query.py'
PRESENTER=ROOT/'olden_db'/'olden_db'/'desktop'/'presenters'/'planner_presenter.py'
VIEW=ROOT/'olden_db'/'olden_db'/'desktop'/'views'/'planner_view.py'
ARCH=ROOT/'docs'/'desktop_application_architecture.md'
QUERY_DOC=ROOT/'docs'/'query_layer.md'

def replace_once(path,old,new,label):
    text=path.read_text(encoding='utf-8')
    if new in text:
        print('SKIP:',label); return
    count=text.count(old)
    if count!=1: raise RuntimeError(f'{label}: expected one reviewed anchor, found {count}')
    path.write_text(text.replace(old,new,1),encoding='utf-8')
    print('UPDATED:',label)

def patch_query():
    replace_once(QUERY,'from .localization import LocalizationCatalog, parse_localization_file\n','from .localization import LocalizationCatalog, parse_localization_directory\n','localization import')
    replace_once(QUERY,'from .paths import require_english_cities_localization_file\n','from .paths import require_english_localization_directory\n','localization path')
    replace_once(QUERY,'            parse_localization_file(\n                require_english_cities_localization_file(),\n                language="english",\n            ),\n','            parse_localization_directory(\n                require_english_localization_directory(),\n                language="english",\n            ),\n','complete localization catalog')
    anchor='    def list_factions(self) -> tuple[str, ...]:\n        return tuple(sorted(self._data.cities.cities))\n\n'
    methods='''    def list_factions(self) -> tuple[str, ...]:
        return tuple(sorted(self._data.cities.cities))

    def get_faction_display_text(self, faction: str) -> str:
        city = self._get_city(faction)
        if self._localization is None:
            return faction
        for candidate in (city.city_id, faction):
            if candidate and self._localization.contains(candidate):
                return self._localization.get(candidate)
        return faction

    def get_unit_display_text(self, unit_sid: str) -> str:
        definition = self._data.units.get(unit_sid)
        if self._localization is None:
            return definition.sid
        return self._localization.resolve(definition.sid, fallback=definition.sid) or definition.sid

    def list_faction_unit_display_texts(self, faction: str) -> tuple[tuple[int, str, str], ...]:
        self._get_city(faction)
        return tuple(
            (definition.tier, definition.sid, self.get_unit_display_text(definition.sid))
            for definition in self._data.units.faction_units(faction)
        )

'''
    replace_once(QUERY,anchor,methods,'Query Layer display-name operations')
    replace_once(QUERY,'        if self._localization is None:\n            raise QueryError("localization is not configured for this query service")\n        fallback = definition.name_key or building.sid\n','        fallback = definition.name_key or building.sid\n        if self._localization is None:\n            return fallback\n','building fallback')

def patch_presenter():
    replace_once(PRESENTER,'from ..formatting import (\n','from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\nfrom ..formatting import (\n','display imports')
    replace_once(PRESENTER,'    def set_factions(self, factions: tuple[str, ...]) -> None: ...\n    def set_buildings(self, buildings: tuple[str, ...]) -> None: ...\n','    def set_factions(self, factions: tuple[CanonicalDisplayOption, ...]) -> None: ...\n    def set_buildings(self, buildings: tuple[CanonicalDisplayOption, ...]) -> None: ...\n','selector contracts')
    replace_once(PRESENTER,'        buildings: tuple[BuildingLevel, ...],\n','        buildings: tuple[StartingBuildingPresentation, ...],\n','starting-building contract')
    replace_once(PRESENTER,'        self._display_text_cache: dict[BuildingKey, str] = {}\n','        self._display_text_cache: dict[BuildingKey, str] = {}\n        self._faction_text_cache: dict[str, str] = {}\n','faction cache')
    replace_once(PRESENTER,'        self._view.set_factions(factions)\n','        self._view.set_factions(self._faction_options(factions))\n','faction selector')
    text=PRESENTER.read_text(encoding='utf-8')
    text=text.replace('self._view.set_buildings(sids)','self._view.set_buildings(self._building_options(faction, sids))')
    text=text.replace('self._view.set_buildings(self._building_options(faction, sids))\n        self._view.set_levels(levels)\n        self._view.set_selection_values(selection.faction','self._view.set_buildings(self._building_options(selection.faction, sids))\n        self._view.set_levels(levels)\n        self._view.set_selection_values(selection.faction')
    text=text.replace('self._view.set_starting_buildings(candidates,','self._view.set_starting_buildings(self._starting_building_presentations(candidates),')
    text=text.replace('self._view.set_starting_buildings(self._state.scenario_candidates,','self._view.set_starting_buildings(self._starting_building_presentations(self._state.scenario_candidates),')
    text=text.replace('self._set_status(f"Faction selected: {faction}. Select a building.")','self._set_status(f"Faction selected: {self._faction_display(faction)}. Select a building.")')
    text=text.replace('self._set_status(f"Building selected: {sid}. Select a level.")','self._set_status(f"Building selected: {self._building_family_display(faction, sid)}. Select a level.")')
    text=text.replace('faction_text = selection.faction if selection is not None else self._state.selected_faction','faction_text = (self._faction_display(selection.faction) if selection is not None else (self._faction_display(self._state.selected_faction) if self._state.selected_faction else None))')
    helper_anchor='    def _display_text(self, building: BuildingKey) -> str:\n'
    helpers='''    def _faction_options(self, factions: tuple[str, ...]) -> tuple[CanonicalDisplayOption, ...]:
        return tuple(CanonicalDisplayOption(item, self._faction_display(item)) for item in factions)

    def _building_options(self, faction: str, sids: tuple[str, ...]) -> tuple[CanonicalDisplayOption, ...]:
        return tuple(CanonicalDisplayOption(sid, self._building_family_display(faction, sid)) for sid in sids)

    def _building_family_display(self, faction: str, sid: str) -> str:
        levels = self._service.list_building_levels(faction, sid)
        return self._display_text(BuildingKey(faction, sid, levels[0]))

    def _starting_building_presentations(self, buildings: tuple[BuildingLevel, ...]) -> tuple[StartingBuildingPresentation, ...]:
        return tuple(StartingBuildingPresentation(item.key, self._display_text(item.key), str(item.key.level), "available" if item.constructed_on_start else "must construct", item.constructed_on_start) for item in buildings)

    def _faction_display(self, faction: str) -> str:
        cached = self._faction_text_cache.get(faction)
        if cached is None:
            cached = self._service.get_faction_display_text(faction)
            self._faction_text_cache[faction] = cached
        return cached

'''
    if helpers not in text:
        if helper_anchor not in text: raise RuntimeError('Presenter helper anchor missing')
        text=text.replace(helper_anchor,helpers+helper_anchor,1)
    PRESENTER.write_text(text,encoding='utf-8')
    print('UPDATED: presenter display projection')

def patch_view():
    replace_once(VIEW,'from ..formatting import (\n','from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\nfrom ..formatting import (\n','view display imports')
    replace_once(VIEW,'        self._faction_var = tk.StringVar()\n        self._building_var = tk.StringVar()\n','        self._faction_var = tk.StringVar()\n        self._building_var = tk.StringVar()\n        self._faction_display_to_id: dict[str, str] = {}\n        self._faction_id_to_display: dict[str, str] = {}\n        self._building_display_to_id: dict[str, str] = {}\n        self._building_id_to_display: dict[str, str] = {}\n','selector maps')
    replace_once(VIEW,'ttk.Label(target, text="Building SID")','ttk.Label(target, text="Target Building")','building label')
    old='''    def set_factions(self, factions: tuple[str, ...]) -> None:
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
    new='''    def set_factions(self, factions: tuple[CanonicalDisplayOption, ...]) -> None:
        self._faction_display_to_id = {item.display_name: item.canonical_id for item in factions}
        self._faction_id_to_display = {item.canonical_id: item.display_name for item in factions}
        values = tuple(item.display_name for item in factions)
        self._faction_selector.configure(values=values)
        self._fit_combobox_to_values(self._faction_selector, values)

    def set_buildings(self, buildings: tuple[CanonicalDisplayOption, ...]) -> None:
        self._building_var.set("")
        self._building_display_to_id = {item.display_name: item.canonical_id for item in buildings}
        self._building_id_to_display = {item.canonical_id: item.display_name for item in buildings}
        values = tuple(item.display_name for item in buildings)
        self._building_selector.configure(values=values, state="readonly" if values else "disabled")
        self._fit_combobox_to_values(self._building_selector, values)
'''
    replace_once(VIEW,old,new,'display-ready selectors')
    replace_once(VIEW,'        self._faction_var.set(faction)\n        self._building_var.set(sid)\n','        self._faction_var.set(self._faction_id_to_display.get(faction, faction))\n        self._building_var.set(self._building_id_to_display.get(sid, sid))\n','selection restoration')
    old_start='''        buildings: tuple[BuildingLevel, ...],
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
    new_start='''        buildings: tuple[StartingBuildingPresentation, ...],
        scenario: PlanningScenario,
    ) -> None:
        self._clear_scenario_content()
        overrides = {override.building: override.available_at_start for override in scenario.starting_building_overrides}
        for row, item in enumerate(buildings):
            effective = overrides.get(item.building, item.constructed_on_start)
            variable = tk.BooleanVar(value=effective)
            self._scenario_vars[item.building] = variable
            ttk.Checkbutton(
                self._scenario_content,
                text=f"{item.display_name} level {item.level_text} — Canonical: {item.canonical_state_text}",
                variable=variable,
                command=lambda key=item.building, var=variable: self._handle_starting_building_changed(key, var.get()),
            ).grid(row=row, column=0, sticky="w", pady=2)
'''
    replace_once(VIEW,old_start,new_start,'starting-building rows')
    replace_once(VIEW,'            self._on_faction_changed(self._faction_var.get())\n','            self._on_faction_changed(self._faction_display_to_id[self._faction_var.get()])\n','faction callback')
    replace_once(VIEW,'            self._on_building_changed(self._building_var.get())\n','            self._on_building_changed(self._building_display_to_id[self._building_var.get()])\n','building callback')

def patch_docs():
    section='\n\n## Canonical Game Name Presentation (UI-011)\n\nCanonical identities remain backend-owned. The Query Layer resolves locale-aware display names and deterministic fallback. Presenters produce immutable canonical/display options; views render display names and map selector text back to canonical IDs.\n'
    for path in (ARCH,QUERY_DOC):
        if path.exists():
            text=path.read_text(encoding='utf-8')
            if 'Canonical Game Name Presentation (UI-011)' not in text:
                path.write_text(text.rstrip()+section+'\n',encoding='utf-8'); print('UPDATED:',path.relative_to(ROOT))

def validate():
    for path in (QUERY,PRESENTER,VIEW,ROOT/'olden_db'/'olden_db'/'desktop'/'display_names.py'):
        ast.parse(path.read_text(encoding='utf-8'),filename=str(path)); print('PASS: syntax',path.relative_to(ROOT))

def main():
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    if head!=EXPECTED: raise RuntimeError(f'Expected HEAD {EXPECTED}; found {head}')
    patch_query(); patch_presenter(); patch_view(); patch_docs(); validate(); print('UI-011 applied successfully.')

if __name__=='__main__': main()
