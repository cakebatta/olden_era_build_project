# BE-014 Runtime Verification

From `olden_db`, run:

```powershell
python -m scripts.test_planner_localization_catalog
python -m scripts.test_localization
python -m scripts.test_query_layer
python -m scripts.test_build_plan_comparison_service
```

Then run:

```powershell
python -c "from olden_db.query import PlanningQueryService; q=PlanningQueryService.from_default_game_data(); f=q.list_factions()[0]; b=q.list_buildings(f)[0]; l=q.list_building_levels(f,b)[0]; from olden_db.models import BuildingKey; k=BuildingKey(f,b,l); u=q._data.units.faction_units(f)[0]; print(q.get_faction_display_name(f)); print(q.get_building_display_name(k)); print(q.get_unit_display_name(f,u.sid)); print(q.get_unit_display_name(f,u.sid))"
python -m scripts.run_desktop
```

Confirm startup succeeds, lookups are non-empty and repeatable, and planner, comparison, and persistence behavior remain unchanged.
