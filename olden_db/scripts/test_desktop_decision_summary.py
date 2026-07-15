from __future__ import annotations
from olden_db.comparison import PlanComparison
from olden_db.decision_summary import ActionDeltaObservation,BuildingAddedObservation,BuildingRemovedObservation,CompletionDeltaObservation,DecisionSummary,PlansDifferObservation,PlansIdenticalObservation,ResourceDeltaObservation
from olden_db.desktop.comparison_state import ComparisonState
from olden_db.desktop.presenters.comparison_presenter import ComparisonPresenter
from olden_db.models import BuildingKey,BuildingLevel,ResourceCost
from olden_db.planner import BuildPlan,GameDate
TARGET=BuildingKey('undead','Build_Tier_6',1); WALL=BuildingKey('undead','Build_Wall',1); MARKET=BuildingKey('undead','Build_Marketplace',1)
BUILDING=BuildingLevel(key=TARGET,category='Dwelling',name_key=None,scene_slot=None,cost=ResourceCost())
PLAN=BuildPlan(faction='undead',target=TARGET,order_number=1,steps=(),total_cost=ResourceCost(),starting_date=GameDate(1,1,1))
C=PlanComparison(PLAN,PLAN,1,2,ResourceCost(gold=3500,wood=5,ore=5),(WALL,),(MARKET,),False)
S=DecisionSummary(C,(PlansDifferObservation(),ActionDeltaObservation(1),CompletionDeltaObservation(2),ResourceDeltaObservation('gold',3500),ResourceDeltaObservation('wood',5),ResourceDeltaObservation('ore',5),BuildingAddedObservation(WALL),BuildingRemovedObservation(MARKET)))
I=DecisionSummary(C,(PlansIdenticalObservation(),))
class Service:
    def __init__(self): self.summary=S; self.calls=[]
    def list_factions(self): return ('undead',)
    def list_buildings(self,f): return ('Build_Tier_6',)
    def list_building_levels(self,f,s): return (1,)
    def get_building(self,f,s,l): return BUILDING
    def compare_plans(self,*a,**k): return C
    def generate_decision_summary(self,*a,**k): self.calls.append((a,k)); return self.summary
class View:
    def __init__(self): self.o=None; self.c=None
    def set_event_handlers(self,**h): pass
    def set_factions(self,x): pass
    def set_buildings(self,s,x): pass
    def set_levels(self,s,x): pass
    def set_scenario_candidates(self,s,b,sc): pass
    def set_mode(self,s,n): pass
    def set_compare_enabled(self,e): pass
    def clear_results(self): self.o=None; self.c=None
    def show_comparison(self,c): self.c=c
    def show_decision_summary(self,o): self.o=o
    def show_error(self,m): raise RuntimeError(m)
def select(p,s): p.on_faction_changed(s,'undead'); p.on_building_changed(s,'Build_Tier_6'); p.on_level_changed(s,1)
def main():
    service=Service(); state=ComparisonState(); view=View(); p=ComparisonPresenter(service,state,view,lambda m:None); p.initialize(); select(p,'left'); select(p,'right'); p.on_compare()
    expected=('The selected plans differ.','The right plan requires 1 additional construction action.','The right plan finishes 2 days later.','Gold changes by +3500.','Wood changes by +5.','Ore changes by +5.','Construction added: Build_Wall level 1.','Construction removed: Build_Marketplace level 1.')
    if view.o!=expected: raise RuntimeError('Observation mapping/order failed')
    if len(service.calls)!=1 or state.current_decision_summary is not S: raise RuntimeError('Summary retrieval/state failed')
    right=state.right.scenario; p.on_level_changed('left',1)
    if state.current_decision_summary is not None or view.o is not None: raise RuntimeError('Stale summary retained')
    if state.right.scenario is not right: raise RuntimeError('Independent state changed')
    service.summary=I; p.on_compare()
    if view.o!=('The selected plans are identical.',): raise RuntimeError('Identical summary incorrect')
    print('Desktop decision-summary validation completed successfully.')
    print('generate_decision_summary was the sole summary source.')
    print('All observation types mapped to readable presentation.')
    print('Backend observation ordering was preserved exactly.')
    print('Identical plans produced one identity observation only.')
    print('Selection changes cleared stale summaries.')
    print('Independent comparison-side state remained preserved.')
if __name__=='__main__': main()
