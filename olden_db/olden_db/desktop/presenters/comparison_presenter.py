from __future__ import annotations
from olden_db.models import BuildingKey
from olden_db.query import QueryError
from olden_db.scenario import PlanningScenario, ScenarioError, StartingBuildingOverride
from ..comparison_state import ComparisonState

class ComparisonPresenter:
    def __init__(self,service,state:ComparisonState,view,set_status): self.s=service; self.state=state; self.v=view; self.status=set_status
    def initialize(self):
        self.v.set_event_handlers(on_faction_changed=self.on_faction_changed,on_building_changed=self.on_building_changed,on_level_changed=self.on_level_changed,on_scenario_changed=self.on_scenario_changed,on_reset_scenario=self.on_reset_scenario,on_compare=self.on_compare); self.v.set_factions(self.s.list_factions()); self.v.set_mode('left',0); self.v.set_mode('right',0); self.v.set_compare_enabled(False); self.v.clear_results()
    def side(self,name): return self.state.left if name=='left' else self.state.right
    def on_faction_changed(self,name,faction):
        try: sids=self.s.list_buildings(faction); c=tuple(sorted((self.s.get_building(faction,sid,l) for sid in sids for l in self.s.list_building_levels(faction,sid)),key=lambda b:(b.key.sid,b.key.level)))
        except QueryError as e: return self._error(e)
        x=self.side(name); x.select_faction(faction,c); self.v.set_buildings(name,sids); self.v.set_scenario_candidates(name,c,x.scenario); self.v.set_mode(name,0); self._changed()
    def on_building_changed(self,name,sid):
        x=self.side(name)
        if x.faction is None:return
        try: levels=self.s.list_building_levels(x.faction,sid)
        except QueryError as e:return self._error(e)
        x.select_building(sid); self.v.set_levels(name,levels); self._changed()
    def on_level_changed(self,name,level): self.side(name).select_level(level); self._changed()
    def on_scenario_changed(self,name,key:BuildingKey,available):
        x=self.side(name); b=next((i for i in x.scenario_candidates if i.key==key),None)
        if b is None:return self.status('Unknown comparison scenario building.')
        d={o.building:o.available_at_start for o in x.scenario.starting_building_overrides}; d.pop(key,None) if available==b.constructed_on_start else d.__setitem__(key,available)
        try: sc=PlanningScenario(tuple(StartingBuildingOverride(k,v) for k,v in d.items()))
        except ScenarioError as e:return self._error(e)
        x.scenario=sc; self.v.set_scenario_candidates(name,x.scenario_candidates,sc); self.v.set_mode(name,len(sc.starting_building_overrides)); self._changed()
    def on_reset_scenario(self,name):
        x=self.side(name); x.scenario=PlanningScenario(); self.v.set_scenario_candidates(name,x.scenario_candidates,x.scenario); self.v.set_mode(name,0); self._changed()
    def on_compare(self):
        if not self.state.can_compare:return self.status('Complete both comparison targets first.')
        l,r=self.state.left,self.state.right
        try:c=self.s.compare_plans(l.faction,l.building_sid,l.level,right_faction=r.faction,right_sid=r.building_sid,right_level=r.level,left_scenario=l.scenario,right_scenario=r.scenario)
        except (QueryError,ScenarioError) as e:return self._error(e)
        self.state.current_comparison=c; self.v.show_comparison(c); self.status('Plan comparison generated successfully.')
    def _changed(self): self.state.clear_result(); self.v.clear_results(); self.v.set_compare_enabled(self.state.can_compare)
    def _error(self,e): self.state.clear_result(); m=f'Comparison could not be completed: {e}'; self.v.show_error(m); self.status(m)
