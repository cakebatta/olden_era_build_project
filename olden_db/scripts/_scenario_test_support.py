from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from olden_db.desktop.economy_state import EconomyTimelineState
from olden_db.desktop.scenario_controller import ScenarioController
from olden_db.desktop.scenario_session import ScenarioSession
from olden_db.desktop.state import PlannerState
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import GameDate
from olden_db.scenario import PlanningScenario
from olden_db.scenario_persistence import (
    LocalScenarioRepository,
    ScenarioNotFoundError,
    create_scenario_document,
)


NOW = datetime(2026, 7, 16, 12, 0, 0, tzinfo=timezone.utc)
KEY = BuildingKey("test", "town_hall", 1)


def make_document(
    name: str = "Managed Scenario",
    scenario_id=None,
):
    factory = (
        (lambda: scenario_id)
        if scenario_id is not None
        else (
            lambda: UUID(
                "00000000-0000-0000-0000-000000000001"
            )
        )
    )
    return create_scenario_document(
        name=name,
        faction="test",
        target_sid="town_hall",
        target_level=1,
        now=NOW,
        scenario_id_factory=factory,
        starting_date=GameDate(1, 1, 1),
        planning_scenario=PlanningScenario(),
        starting_resources=ResourceCost(gold=1000),
    )


class FakeView:
    def __init__(self):
        self.name = "Managed Scenario"
        self.description = ""
        self.notes = ""
        self.title = ""
        self.errors = []
        self.infos = []
        self.unsaved_action = "cancel"
        self.unsaved_prompts = 0
        self.selected_summary = None
        self.import_source = ""
        self.export_destination = ""
        self.next_name = None
        self.conflict_copy = False
        self.delete_confirmation = True
        self.handlers = {}

    def set_handlers(self, **handlers):
        self.handlers = handlers

    def metadata(self):
        return self.name, self.description, self.notes

    def apply_metadata(
        self,
        name,
        description,
        notes,
    ):
        self.name = name
        self.description = description
        self.notes = notes

    def set_title(self, title):
        self.title = title

    def show_error(self, message):
        self.errors.append(message)

    def show_info(self, message):
        self.infos.append(message)

    def choose_unsaved_action(self, _name):
        self.unsaved_prompts += 1
        return self.unsaved_action

    def choose_scenario(self, listing):
        return self.selected_summary or (
            listing.scenarios[0]
            if listing.scenarios
            else None
        )

    def ask_name(self, _title, initial):
        return (
            initial
            if self.next_name is None
            else self.next_name
        )

    def choose_conflict_copy(self):
        return self.conflict_copy

    def confirm_delete(self, _name):
        return self.delete_confirmation

    def import_path(self):
        return self.import_source

    def export_path(self, _name):
        return self.export_destination

    def confirm_overwrite(self, _name):
        return True


class FakePresenter:
    def available_factions(self):
        return ("test",)

    def available_buildings(self, _faction):
        return ("town_hall",)

    def available_levels(self, _faction, _sid):
        return (1,)

    def apply_document(self, _document):
        pass

    def on_generate_plan(self):
        pass

    def on_generate(self):
        pass


def make_controller(
    repository: LocalScenarioRepository,
):
    planner = PlannerState(
        selected_faction="test",
        selected_building_sid="town_hall",
        selected_level=1,
        starting_date=GameDate(1, 1, 1),
        active_scenario=PlanningScenario(),
    )
    economy = EconomyTimelineState(
        starting_resources=ResourceCost(gold=1000),
    )
    view = FakeView()
    presenter = FakePresenter()
    controller = ScenarioController(
        repository,
        planner,
        economy,
        presenter,
        presenter,
        view,
        lambda _message: None,
        now=lambda: NOW,
    )
    return controller, planner, economy, view


def load_managed(
    controller,
    repository,
    document,
):
    """Load a managed scenario, creating it only when absent."""

    try:
        loaded = repository.get_scenario(
            document.scenario_id
        )
    except ScenarioNotFoundError:
        loaded = repository.save_scenario(
            document,
            expected_token=None,
            now=NOW,
        )

    controller.session = ScenarioSession(
        loaded.document
    )
    controller.session.accept_loaded(
        loaded.document,
        loaded.conflict_token,
    )
    controller.view.apply_metadata(
        loaded.document.name,
        loaded.document.description,
        loaded.document.notes,
    )
    controller._refresh()
    return loaded
