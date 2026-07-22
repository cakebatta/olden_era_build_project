from __future__ import annotations
import ast
from pathlib import Path
from olden_db.query import PlanningQueryService

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'olden_db' / 'query.py'
PRESENTER = ROOT / 'olden_db' / 'desktop' / 'presenters' / 'planner_presenter.py'
VIEW = ROOT / 'olden_db' / 'desktop' / 'views' / 'planner_view.py'
DISPLAY = ROOT / 'olden_db' / 'desktop' / 'display_names.py'
COMPARISON = ROOT / 'olden_db' / 'desktop' / 'presenters' / 'build_plan_comparison_presenter.py'

def require(value, message):
    if not value: raise AssertionError(message)

def test_query_layer_owns_display_name_resolution():
    text=QUERY.read_text(encoding='utf-8')
    for token in ('get_faction_display_text','get_building_display_text','get_unit_display_text','parse_localization_directory'):
        require(token in text, f'Missing Query Layer display contract: {token}')

def test_demon_resolves_to_hive():
    service=PlanningQueryService.from_default_game_data()
    require(service.get_faction_display_text('demon')=='Hive','demon must display as Hive')

def test_all_supported_factions_and_units_resolve():
    service=PlanningQueryService.from_default_game_data()
    for faction in service.list_factions():
        require(bool(service.get_faction_display_text(faction)), f'Missing faction name: {faction}')
        units=service.list_faction_unit_display_texts(faction)
        require({tier for tier,_sid,_name in units} >= set(range(1,8)), f'Missing unit tiers: {faction}')
        require(all(name for _tier,_sid,name in units), f'Missing unit name: {faction}')

def test_selectors_submit_canonical_identity():
    presenter=PRESENTER.read_text(encoding='utf-8'); view=VIEW.read_text(encoding='utf-8')
    require('CanonicalDisplayOption' in presenter,'Presenter display options missing')
    require('_faction_display_to_id' in view,'Faction canonical binding missing')
    require('_building_display_to_id' in view,'Building canonical binding missing')
    require('self._faction_display_to_id[self._faction_var.get()]' in view,'Faction callback not canonical')
    require('self._building_display_to_id[self._building_var.get()]' in view,'Building callback not canonical')

def test_starting_buildings_are_display_ready():
    presenter=PRESENTER.read_text(encoding='utf-8'); view=VIEW.read_text(encoding='utf-8')
    require('StartingBuildingPresentation' in presenter,'Starting presentation missing')
    require('item.display_name' in view,'View does not render display-ready name')
    require('get_building_display_text' not in view,'View performs localization')

def test_comparison_uses_query_layer_names():
    require('self._service.get_building_display_text(building)' in COMPARISON.read_text(encoding='utf-8'),'UI-010 localization missing')

def test_no_handwritten_mapping():
    text=VIEW.read_text(encoding='utf-8')
    require('"demon": "Hive"' not in text,'UI-owned mapping detected')
    require('parse_localization' not in text,'View reads localization storage')

def test_syntax():
    for path in (QUERY,PRESENTER,VIEW,DISPLAY,COMPARISON): ast.parse(path.read_text(encoding='utf-8'),filename=str(path))

def main():
    checks=[v for n,v in globals().items() if n.startswith('test_') and callable(v)]
    for check in checks: check(); print(f'PASS: {check.__name__}')
    print(f'PASS: {len(checks)} focused UI-011 canonical-name checks')

if __name__=='__main__': main()
