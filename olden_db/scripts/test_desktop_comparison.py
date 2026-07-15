from __future__ import annotations
from olden_db.comparison import PlanComparison
from olden_db.decision_summary import DecisionSummary,PlansDifferObservation
from olden_db.desktop.comparison_state import ComparisonState
from olden_db.desktop.presenters.comparison_presenter import ComparisonPresenter
from olden_db.models import BuildingKey,BuildingLevel,ResourceCost
from olden_db.planner import BuildPlan,GameDate
K=BuildingKey('undead','Build_Tier_6',1); B=BuildingLevel(key=K,category='Dwelling',name_key=None,scene_slot=None,cost=ResourceCost()); P=BuildPlan(faction='undead',target=K,order_number=1,steps=(),total_cost=ResourceCost(),starting_date=GameDate(1,1,1)); C=PlanComparison(P,P,0,0,ResourceCost(),(),(),False); S=DecisionSummary(C,(PlansDifferObservation(),))
class Service:
    def __init__(self): self.cc=0; self.sc=0
    def list_factions(self): return ('undead',)
    def list_buildings(self,f): return ('Build_Tier_6',)
    def list_building_levels(self,f,s): return (1,)
    def get_building(self,f,s,l): return B
    def compare_plans(self,*a,**k): self.cc+=1; return C
    def generate_decision_summary(self,*a,**k): self.sc+=1; return S
class View:
    def __init__(self): self.c=None; self.o=None; self.enabled=False
    def set_event_handlers(self,**h): pass
    def set_factions(self,x): pass
    def set_buildings(self,s,x): pass
    def set_levels(self,s,x): pass
    def set_scenario_candidates(self,s,b,sc): pass
    def set_mode(self,s,n): pass
    def set_compare_enabled(self,e): self.enabled=e
    def clear_results(self): self.c=None; self.o=None
    def show_comparison(self,c): self.c=c
    def show_decision_summary(self,o): self.o=o
    def show_error(self,m): raise RuntimeError(m)
def select(p,s): p.on_faction_changed(s,'undead'); p.on_building_changed(s,'Build_Tier_6'); p.on_level_changed(s,1)
def main():
    service=Service(); state=ComparisonState(); view=View(); p=ComparisonPresenter(service,state,view,lambda m:None); p.initialize(); select(p,'left')
    if state.right.faction is not None: raise RuntimeError('Left modified right')
    select(p,'right'); p.on_compare()
    if (service.cc,service.sc)!=(1,1) or view.c is not C or view.o!=('The selected plans differ.',): raise RuntimeError('Pipelines/display failed')
    p.on_level_changed('left',1)
    if state.current_comparison is not None or state.current_decision_summary is not None or state.right.level!=1: raise RuntimeError('Stale/independent state failed')
    print('Desktop comparison validation completed successfully.')
    print('Independent left and right state remained preserved.')
    print('Raw PlanComparison display remained intact.')
    print('DecisionSummary retrieval was integrated.')
    print('Selection changes cleared comparison and summary results.')
if __name__=='__main__': main()
