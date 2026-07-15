from __future__ import annotations

from collections.abc import Callable

from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.scenario import InvalidStartingBuildingOverrideError, PlanningScenario, PrerequisiteStatus

WALL_KEY = BuildingKey("undead", "Build_Wall", 1)
TIER_KEY = BuildingKey("undead", "Build_Tier_3", 1)
TARGET_KEY = BuildingKey("undead", "Build_Tier_6", 1)
WALL = BuildingLevel(WALL_KEY, "Fortification", None, None, ResourceCost(gold=2500, wood=5, ore=5), constructed_on_start=True)
TIER = BuildingLevel(TIER_KEY, "Dwelling", None, None, ResourceCost(gold=3000, wood=5, ore=5))
TARGET = BuildingLevel(TARGET_KEY, "Dwelling", None, None, ResourceCost(gold=6000, wood=10, ore=5), prerequisites=(TIER_KEY, WALL_KEY))
CANONICAL = BuildPlan("undead", TARGET_KEY, 1, (
    BuildStep(1, GameDate(1,1,1), TIER_KEY, TIER.cost, TIER.cost),
    BuildStep(2, GameDate(1,1,2), TARGET_KEY, TARGET.cost, ResourceCost(gold=9000, wood=15, ore=10)),
), ResourceCost(gold=9000, wood=15, ore=10), GameDate(1,1,1))
CUSTOM = BuildPlan("undead", TARGET_KEY, 1, (
    BuildStep(1, GameDate(1,1,1), TIER_KEY, TIER.cost, TIER.cost),
    BuildStep(2, GameDate(1,1,2), WALL_KEY, WALL.cost, ResourceCost(gold=5500, wood=10, ore=10)),
    BuildStep(3, GameDate(1,1,3), TARGET_KEY, TARGET.cost, ResourceCost(gold=11500, wood=20, ore=15)),
), ResourceCost(gold=11500, wood=20, ore=15), GameDate(1,1,1))

class Service:
    def __init__(self): self.calls=[]; self.fail=False
    def list_factions(self): return ("undead",)
    def list_buildings(self, faction): return ("Build_Tier_3", "Build_Tier_6", "Build_Wall")
    def list_building_levels(self, faction, sid): return (1,)
    def get_building(self, faction, sid, level): return {"Build_Tier_3":TIER,"Build_Tier_6":TARGET,"Build_Wall":WALL}[sid]
    def _record(self, name, scenario):
        self.calls.append((name, scenario))
        if self.fail: raise InvalidStartingBuildingOverrideError("simulated invalid override")
    def get_prerequisite_statuses(self, f,s,l,*,scenario):
        self._record("statuses", scenario)
        custom=bool(scenario.starting_building_overrides)
        return (PrerequisiteStatus(TIER,False,False),PrerequisiteStatus(WALL,not custom,custom))
    def generate_build_plan(self,f,s,l,*,scenario): self._record("plan",scenario); return CUSTOM if scenario.starting_building_overrides else CANONICAL
    def get_cumulative_cost(self,f,s,l,*,scenario): self._record("cost",scenario); return (CUSTOM if scenario.starting_building_overrides else CANONICAL).total_cost
    def enumerate_build_orders(self,f,s,l,*,scenario): self._record("orders",scenario); p=CUSTOM if scenario.starting_building_overrides else CANONICAL; return (tuple(x.building for x in p.steps),)

class View:
    def __init__(self): self.mode=-1; self.scenario=None; self.plan=None; self.error=None; self.generate=False; self.candidates=()
    def set_event_handlers(self,**kwargs): self.handlers=kwargs
    def set_factions(self,x): pass
    def set_buildings(self,x): pass
    def set_levels(self,x): pass
    def clear_building_selection(self): pass
    def clear_level_selection(self): pass
    def set_generate_enabled(self,x): self.generate=x
    def set_starting_buildings(self,b,s): self.candidates=b; self.scenario=s
    def clear_starting_buildings(self): self.candidates=()
    def set_planning_mode(self,n): self.mode=n
    def clear_results(self): self.plan=None; self.error=None
    def show_target(self,x): pass
    def show_prerequisites(self,x): self.statuses=x
    def show_plan(self,p,c): self.plan=p; self.cost=c
    def show_error(self,m): self.error=m

def main():
    service=Service(); state=PlannerState(); view=View(); messages=[]
    presenter=PlannerPresenter(service,state,view,messages.append)  # type: ignore[arg-type]
    presenter.initialize()
    if not state.is_canonical_mode or view.mode != 0: raise RuntimeError("Canonical startup failed")
    presenter.on_faction_changed("undead"); presenter.on_building_changed("Build_Tier_6"); presenter.on_level_changed(1); presenter.on_generate_plan()
    canonical=state.active_scenario
    if view.plan != CANONICAL: raise RuntimeError("Canonical plan failed")
    if not all(s is canonical for _,s in service.calls[-4:]): raise RuntimeError("Canonical scenario instance not reused")
    old=state.active_scenario; service.calls.clear(); presenter.on_starting_building_changed(WALL_KEY,False)
    custom=state.active_scenario
    if custom is old or old.starting_building_overrides: raise RuntimeError("Scenario was not immutably replaced")
    if state.override_count != 1 or view.mode != 1 or view.plan != CUSTOM: raise RuntimeError("Custom scenario did not regenerate")
    if not all(s is custom for _,s in service.calls[-4:]): raise RuntimeError("Custom scenario instance not reused")
    presenter.on_starting_building_changed(WALL_KEY,True)
    if not state.is_canonical_mode or view.plan != CANONICAL: raise RuntimeError("Redundant override was retained")
    presenter.on_starting_building_changed(WALL_KEY,False); presenter.on_reset_scenario()
    if not state.is_canonical_mode or view.mode != 0 or view.plan != CANONICAL: raise RuntimeError("Reset failed")
    service.fail=True; presenter.on_starting_building_changed(WALL_KEY,False)
    if view.error is None or state.current_plan is not None or not state.has_complete_target: raise RuntimeError("Scenario error handling failed")
    print("Desktop scenario validation completed successfully.")
    print("Canonical planning remained the startup default.")
    print("Scenario changes replaced immutable scenario objects.")
    print("Redundant canonical overrides were removed.")
    print("One scenario instance was reused across all Query Layer calls.")
    print("Scenario changes and reset regenerated the current plan.")
    print("Expected scenario exceptions cleared stale results safely.")

if __name__ == "__main__": main()
