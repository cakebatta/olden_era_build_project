from olden_db.models import BuildingKey
from olden_db.query import PlanningQueryService

def require(value,message):
    if not value: raise AssertionError(message)

def test_building_names_for_every_faction():
    service=PlanningQueryService.from_default_game_data()
    for faction in service.list_factions():
        for sid in service.list_buildings(faction):
            for level in service.list_building_levels(faction,sid):
                require(bool(service.get_building_display_text(BuildingKey(faction,sid,level))),f'Missing building name: {faction}/{sid}/{level}')

def test_missing_localization_fallbacks():
    configured=PlanningQueryService.from_default_game_data(); service=PlanningQueryService(configured._data,None)
    require(service.get_faction_display_text('demon')=='demon','Faction fallback changed')
    unit=configured._data.units.faction_units('demon')[0]
    require(service.get_unit_display_text(unit.sid)==unit.sid,'Unit fallback changed')

def main():
    checks=[test_building_names_for_every_faction,test_missing_localization_fallbacks]
    for check in checks: check(); print(f'PASS: {check.__name__}')
    print(f'PASS: {len(checks)} UI-011 integration checks')

if __name__=='__main__': main()
