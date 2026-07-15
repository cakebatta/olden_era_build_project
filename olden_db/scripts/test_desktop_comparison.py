from __future__ import annotations
from olden_db.comparison import PlanComparison
from olden_db.desktop.comparison_state import ComparisonState
from olden_db.desktop.presenters.comparison_presenter import ComparisonPresenter
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, BuildStep, GameDate
from olden_db.scenario import PlanningScenario
W=BuildingKey('undead','Build_Wall',1); T=BuildingKey('undead','Build_Tier_6',1); B=BuildingLevel(W,'Fortification',None,None,ResourceCost(gold=2500),constructed_on_start=True); X=BuildingLevel(T,'Dwelling',None,None,ResourceCost(gold=6000)); L=BuildPlan('undead',T,1,(BuildStep(1,GameDate(1,1,1),T,X.cost,X.cost),),X.cost,GameDate(1,1,1)); R=BuildPlan('undead',T,1,(BuildStep(1,GameDate(1,1,1),W,B.cost,B.cost),BuildStep(2,GameDate(1,1,2),T,X.cost,ResourceCost(gold=8500))),ResourceCost(gold=8500),GameDate(1,1,1)); D=PlanComparison(L,R,1,1,ResourceCost(gold=2500),(W,),(),False); I=PlanComparison(L,L,0,0,ResourceCost(),(),(),True)
class S:
 def __init__(self): self.calls=[]
 def list_factions(self): return ('undead',)
 def list_buildings(self,f): return ('Build_Tier_6','Build_Wall')
 def list_building_levels(self,f,s): return (1,)
 def get_building(self,f,s,l): return B if s=='Build_Wall' else X
 def compare_plans(self,lf,ls,ll,*,right_faction,right_sid,right_level,left_scenario,right_scenario): self.calls.append((lf,ls,ll,right_faction,right_sid,right_level,left_scenario,right_scenario)); return D if right_scenario.starting_building_overrides else I
class V:
 def __init__(self): self.enabled=False; self.comp=None; self.sc={}
 def set_event_handlers(self,**h): self.h=h
 def set_factions(self,x): pass
 def set_buildings(self,s,x): pass
 def set_levels(self,s,x): pass
 def set_scenario_candidates(self,s,b,sc): self.sc[s]=sc
 def set_mode(self,s,n): pass
 def set_compare_enabled(self,e): self.enabled=e
 def clear_results(self): self.comp=None
 def show_comparison(self,c): self.comp=c
 def show_error(self,m): raise RuntimeError(m)
def sel(p,s): p.on_faction_changed(s,'undead'); p.on_building_changed(s,'Build_Tier_6'); p.on_level_changed(s,1)
def main():
 s=S(); st=ComparisonState(); v=V(); p=ComparisonPresenter(s,st,v,lambda m:None); p.initialize(); sel(p,'left'); assert st.right.faction is None and not v.enabled; sel(p,'right'); assert st.can_compare and v.enabled; left=st.left.scenario; old=st.right.scenario; p.on_scenario_changed('right',W,False); new=st.right.scenario; assert new is not old and st.left.scenario is left and st.current_comparison is None; p.on_compare(); assert v.comp is D and s.calls[-1][-2] is left and s.calls[-1][-1] is new; p.on_level_changed('left',1); assert st.current_comparison is None and st.right.level==1; p.on_reset_scenario('right'); p.on_compare(); assert v.comp is I and not st.right.scenario.starting_building_overrides
 print('Desktop comparison validation completed successfully.'); print('Left and right selections remained independent.'); print('Independent immutable scenarios were passed to compare_plans.'); print('Backend PlanComparison results were displayed without recalculation.'); print('Selection changes cleared stale comparison results.')
if __name__=='__main__': main()
