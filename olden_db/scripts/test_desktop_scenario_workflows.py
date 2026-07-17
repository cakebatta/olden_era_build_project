import inspect
from olden_db.desktop.scenario_controller import ScenarioController
from olden_db.desktop.scenario_presenters import ScenarioAwarePlannerPresenter,ScenarioAwareEconomyPresenter

def main():
    controller=inspect.getsource(ScenarioController)
    assert "choose_unsaved_action" in controller
    assert "list_scenarios()" in controller and "get_scenario(" in controller
    assert "import_scenario(" in controller and "delete_scenario(" in controller
    assert "duplicate_scenario_document(" in controller
    assert "repository_token" in controller
    planner=inspect.getsource(ScenarioAwarePlannerPresenter.on_generate_plan)
    economy=inspect.getsource(ScenarioAwareEconomyPresenter.on_generate)
    assert "starting_date=self._state.starting_date" in planner
    assert "starting_date=self._planner_state.starting_date" in economy
    assert economy.count("generate_resource_ledger(")==1
    print("Desktop scenario-workflow validation completed successfully.")
if __name__=="__main__":main()
