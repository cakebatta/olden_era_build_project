from __future__ import annotations
from collections.abc import Callable
from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.query import QueryError

TARGET_KEY=BuildingKey("nature","Build_Tier_4",2); PRE_KEY=BuildingKey("nature","Build_Hall",1); START_KEY=BuildingKey("nature","Build_Start",1)
TARGET=BuildingLevel(key=TARGET_KEY,category="Dwelling",name_key=None,scene_slot=None,cost=ResourceCost(gold=3000,wood=5),prerequisites=(PRE_KEY,))
PRE=BuildingLevel(key=PRE_KEY,category="Hall",name_key=None,scene_slot=None,cost=ResourceCost(gold=1000))
START=BuildingLevel(key=START_KEY,category="Starting",name_key=None,scene_slot=None,cost=ResourceCost(),constructed_on_start=True)
PLAN=BuildPlan(faction="nature",target=TARGET_KEY,order_number=1,steps=(BuildStep(1,GameDate(1,1,1),PRE_KEY,ResourceCost(gold=1000),ResourceCost(gold=1000)),BuildStep(2,GameDate(1,1,2),TARGET_KEY,ResourceCost(gold=3000,wood=5),ResourceCost(gold=4000,wood=5))),total_cost=ResourceCost(gold=4000,wood=5),starting_date=GameDate(1,1,1))
ZERO=BuildPlan(faction="nature",target=START_KEY,order_number=1,steps=(),total_cost=ResourceCost(),starting_date=GameDate(1,1,1))

class Service:
    def __init__(self): self.calls=[]; self.fail=False
    def list_factions(self): return ("nature",)
    def list_buildings(self,faction): return ("Build_Start","Build_Tier_4")
    def list_building_levels(self,faction,sid): return (1,) if sid=="Build_Start" else (2,)
    def get_building(self,f,s,l):
        self.calls.append(("get_building",f,s,l))
        if self.fail: raise QueryError("simulated generation failure")
        return START if s=="Build_Start" else TARGET
    def get_prerequisites(self,f,s,l): self.calls.append(("get_prerequisites",f,s,l)); return () if s=="Build_Start" else (PRE,)
    def generate_build_plan(self,f,s,l): self.calls.append(("generate_build_plan",f,s,l)); return ZERO if s=="Build_Start" else PLAN
    def get_cumulative_cost(self,f,s,l): self.calls.append(("get_cumulative_cost",f,s,l)); return ResourceCost() if s=="Build_Start" else PLAN.total_cost

class View:
    def __init__(self): self.generate_enabled=False; self.target=None; self.prerequisites=None; self.plan=None; self.cost=None; self.error=None
    def set_event_handlers(self,**kwargs): pass
    def set_factions(self,x): pass
    def set_buildings(self,x): pass
    def set_levels(self,x): pass
    def clear_building_selection(self): pass
    def clear_level_selection(self): pass
    def set_generate_enabled(self,x): self.generate_enabled=x
    def clear_results(self): self.target=self.prerequisites=self.plan=self.cost=self.error=None
    def show_target(self,x): self.target=x
    def show_prerequisites(self,x): self.prerequisites=x
    def show_plan(self,p,c): self.plan=p; self.cost=c
    def show_error(self,m): self.error=m

def select(p,sid="Build_Tier_4",level=2): p.on_faction_changed("nature"); p.on_building_changed(sid); p.on_level_changed(level)

def main():
    s=Service(); st=PlannerState(); v=View(); statuses=[]; p=PlannerPresenter(s,st,v,statuses.append)  # type: ignore[arg-type]
    p.initialize(); p.on_generate_plan()
    if s.calls or v.generate_enabled: raise RuntimeError("Incomplete state was not rejected")
    select(p); p.on_generate_plan()
    expected=[("get_building","nature","Build_Tier_4",2),("get_prerequisites","nature","Build_Tier_4",2),("generate_build_plan","nature","Build_Tier_4",2),("get_cumulative_cost","nature","Build_Tier_4",2)]
    if s.calls!=expected: raise RuntimeError(f"Unexpected calls: {s.calls}")
    if (v.target,v.prerequisites,v.plan,v.cost)!=(TARGET,(PRE,),PLAN,PLAN.total_cost): raise RuntimeError("Results not displayed")
    first=(v.target,v.prerequisites,v.plan,v.cost,statuses[-1]); s.calls.clear(); p.on_generate_plan(); second=(v.target,v.prerequisites,v.plan,v.cost,statuses[-1])
    if first!=second or s.calls!=expected: raise RuntimeError("Repeated generation was not deterministic")
    p.on_level_changed(2)
    if st.current_plan is not None or v.plan is not None: raise RuntimeError("Level change did not clear results")
    select(p,"Build_Start",1); p.on_generate_plan()
    if (v.target,v.prerequisites,v.plan,v.cost)!=(START,(),ZERO,ResourceCost()): raise RuntimeError("Zero-action result incorrect")
    if "no construction actions" not in statuses[-1].lower(): raise RuntimeError("Zero-action status unclear")
    s.fail=True; select(p); p.on_generate_plan()
    if st.current_plan is not None or v.plan is not None or v.target is not None: raise RuntimeError("Failure retained stale results")
    if v.error is None or not st.has_complete_target: raise RuntimeError("Failure handling incorrect")
    print("Desktop plan-generation validation completed successfully.")
    print("All four Query Layer planning operations used canonical arguments.")
    print("Target, prerequisites, dated plan, and cumulative cost were displayed.")
    print("Repeated generation returned deterministic results.")
    print("Constructed-at-start targets produced understandable zero-action output.")
    print("Selection changes and Query errors cleared stale results.")
    print("Presenter logic was validated without live tkinter widgets.")

if __name__=="__main__": main()
