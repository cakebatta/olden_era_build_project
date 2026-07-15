from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.query import QueryError
from olden_db.scenario import PlanningScenario, PrerequisiteStatus
K=BuildingKey("nature","Target",1); P=BuildingKey("nature","Pre",1); S=BuildingKey("nature","Start",1)
PRE=BuildingLevel(P,"Test",None,None,ResourceCost(gold=1))
TARGET=BuildingLevel(K,"Test",None,None,ResourceCost(gold=2),prerequisites=(P,))
START=BuildingLevel(S,"Test",None,None,ResourceCost(),constructed_on_start=True)
PLAN=BuildPlan("nature",K,1,(BuildStep(1,GameDate(1,1,1),P,PRE.cost,PRE.cost),BuildStep(2,GameDate(1,1,2),K,TARGET.cost,ResourceCost(gold=3))),ResourceCost(gold=3),GameDate(1,1,1))
ZERO=BuildPlan("nature",S,1,(),ResourceCost(),GameDate(1,1,1))
class Service:
    def __init__(self): self.calls=[]; self.fail=False
    def list_factions(self): return ("nature",)
    def list_buildings(self,f): return ("Pre","Start","Target")
    def list_building_levels(self,f,s): return (1,)
    def get_building(self,f,s,l): return {"Pre":PRE,"Start":START,"Target":TARGET}[s]
    def get_prerequisite_statuses(self,f,s,l,*,scenario):
        self.calls.append(("statuses",scenario))
        if self.fail: raise QueryError("simulated")
        return () if s=="Start" else (PrerequisiteStatus(PRE,False,False),)
    def generate_build_plan(self,f,s,l,*,scenario): self.calls.append(("plan",scenario)); return ZERO if s=="Start" else PLAN
    def get_cumulative_cost(self,f,s,l,*,scenario): self.calls.append(("cost",scenario)); return ResourceCost() if s=="Start" else PLAN.total_cost
    def enumerate_build_orders(self,f,s,l,*,scenario): self.calls.append(("orders",scenario)); p=ZERO if s=="Start" else PLAN; return (tuple(x.building for x in p.steps),)
class View:
    def __init__(self): self.enabled=False; self.target=None; self.statuses=None; self.plan=None; self.cost=None; self.error=None
    def set_event_handlers(self,**kwargs): pass
    def set_factions(self,x): pass
    def set_buildings(self,x): pass
    def set_levels(self,x): pass
    def clear_building_selection(self): pass
    def clear_level_selection(self): pass
    def set_generate_enabled(self,x): self.enabled=x
    def set_starting_buildings(self,b,s): pass
    def clear_starting_buildings(self): pass
    def set_planning_mode(self,n): pass
    def clear_results(self): self.target=self.statuses=self.plan=self.cost=self.error=None
    def show_target(self,x): self.target=x
    def show_prerequisites(self,x): self.statuses=x
    def show_plan(self,p,c): self.plan=p; self.cost=c
    def show_error(self,m): self.error=m
def select(p,s="Target"): p.on_faction_changed("nature"); p.on_building_changed(s); p.on_level_changed(1)
def main():
    service=Service(); state=PlannerState(); view=View(); p=PlannerPresenter(service,state,view,lambda x:None)  # type: ignore[arg-type]
    p.initialize(); p.on_generate_plan()
    if service.calls: raise RuntimeError("Incomplete state called planning")
    select(p); p.on_generate_plan(); scenario=state.active_scenario
    if view.target!=TARGET or view.plan!=PLAN or view.cost!=PLAN.total_cost: raise RuntimeError("Plan display failed")
    if view.statuses!=(PrerequisiteStatus(PRE,False,False),): raise RuntimeError("Status display failed")
    if not all(s is scenario for _,s in service.calls[-4:]): raise RuntimeError("Scenario instance not reused")
    first=(view.target,view.statuses,view.plan,view.cost); service.calls.clear(); p.on_generate_plan()
    if first!=(view.target,view.statuses,view.plan,view.cost): raise RuntimeError("Nondeterministic generation")
    p.on_level_changed(1)
    if state.current_plan is not None or view.plan is not None: raise RuntimeError("Stale results remained")
    select(p,"Start"); p.on_generate_plan()
    if (view.target,view.statuses,view.plan,view.cost)!=(START,(),ZERO,ResourceCost()): raise RuntimeError("Zero action failed")
    service.fail=True; select(p); p.on_generate_plan()
    if view.error is None or state.current_plan is not None or not state.has_complete_target: raise RuntimeError("Error handling failed")
    print("Desktop plan-generation validation completed successfully.")
    print("One active scenario was reused across planning queries.")
    print("Effective prerequisite, zero-action, and error behavior remained correct.")
if __name__ == "__main__": main()
