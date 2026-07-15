from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
class S:
    def list_factions(self): return ("nature",)
    def list_buildings(self,f): return ("A","B")
    def list_building_levels(self,f,s): return (1,2) if s=="B" else (1,)
    def get_building(self,f,s,l): return BuildingLevel(BuildingKey(f,s,l),"Test",None,None,ResourceCost())
class V:
    def __init__(self): self.enabled=False; self.buildings=(); self.levels=(); self.candidates=()
    def set_event_handlers(self,**kwargs): pass
    def set_factions(self,x): pass
    def set_buildings(self,x): self.buildings=x
    def set_levels(self,x): self.levels=x
    def clear_building_selection(self): self.buildings=()
    def clear_level_selection(self): self.levels=()
    def set_generate_enabled(self,x): self.enabled=x
    def set_starting_buildings(self,b,s): self.candidates=b
    def clear_starting_buildings(self): self.candidates=()
    def set_planning_mode(self,n): pass
    def clear_results(self): pass
    def show_target(self,x): raise RuntimeError("unexpected")
    def show_prerequisites(self,x): raise RuntimeError("unexpected")
    def show_plan(self,p,c): raise RuntimeError("unexpected")
    def show_error(self,m): pass
def main():
    st=PlannerState(); v=V(); p=PlannerPresenter(S(),st,v,lambda x:None)  # type: ignore[arg-type]
    p.initialize(); p.on_faction_changed("nature")
    if v.buildings != ("A","B") or len(v.candidates)!=3 or not st.is_canonical_mode: raise RuntimeError("Faction workflow failed")
    p.on_building_changed("B"); p.on_level_changed(2)
    if not st.has_complete_target or not v.enabled: raise RuntimeError("Target completion failed")
    p.on_building_changed("A")
    if st.selected_level is not None or v.enabled: raise RuntimeError("Downstream reset failed")
    print("Desktop target-selection validation completed successfully.")
    print("Scenario candidates populated deterministically.")
if __name__ == "__main__": main()
