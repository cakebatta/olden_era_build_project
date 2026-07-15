from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
class S:
    def list_factions(self): return ("a","b")
class V:
    def __init__(self): self.handlers={}; self.factions=(); self.enabled=True; self.mode=-1; self.cleared=0
    def set_event_handlers(self,**kwargs): self.handlers=kwargs
    def set_factions(self,x): self.factions=x
    def set_buildings(self,x): pass
    def set_levels(self,x): pass
    def clear_building_selection(self): pass
    def clear_level_selection(self): pass
    def set_generate_enabled(self,x): self.enabled=x
    def set_starting_buildings(self,b,s): raise RuntimeError("unexpected")
    def clear_starting_buildings(self): pass
    def set_planning_mode(self,n): self.mode=n
    def clear_results(self): self.cleared+=1
    def show_target(self,x): raise RuntimeError("unexpected")
    def show_prerequisites(self,x): raise RuntimeError("unexpected")
    def show_plan(self,p,c): raise RuntimeError("unexpected")
    def show_error(self,m): raise RuntimeError("unexpected")
def main():
    st=PlannerState(); v=V(); messages=[]; PlannerPresenter(S(),st,v,messages.append).initialize()  # type: ignore[arg-type]
    if messages != ["Ready — 2 factions available."] or v.factions != ("a","b") or v.enabled or v.mode != 0 or v.cleared != 1: raise RuntimeError("Skeleton initialization failed")
    if st != PlannerState(): raise RuntimeError("Initial state changed")
    print("Desktop skeleton validation completed successfully.")
    print("Canonical scenario controls initialized correctly.")
if __name__ == "__main__": main()
