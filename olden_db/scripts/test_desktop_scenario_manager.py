from pathlib import Path
from tempfile import TemporaryDirectory

from olden_db.scenario_persistence import LocalScenarioRepository
from scripts._scenario_test_support import (
    load_managed,
    make_controller,
    make_document,
)


def main():
    with TemporaryDirectory() as directory:
        repository = LocalScenarioRepository(directory)
        controller, _planner, economy, view = make_controller(repository)
        saved = load_managed(controller, repository, make_document())
        managed_path = repository.scenario_directory / (
            f"{saved.document.scenario_id}.json"
        )
        original_bytes = managed_path.read_bytes()

        view.name = ""
        controller.on_user_edit()
        assert controller.session.invalid
        assert controller.session.has_unsaved_risk
        assert view.title.endswith(" *")

        assert controller.save() is False
        assert managed_path.read_bytes() == original_bytes
        assert view.name == ""
        assert view.errors

        view.unsaved_action = "cancel"
        old_session = controller.session
        assert controller.new() is False
        assert controller.session is old_session
        assert view.name == ""

        view.unsaved_action = "discard"
        assert controller.new() is True
        assert controller.session is not old_session

        load_managed(controller, repository, saved.document)
        economy.invalidate_starting_resources(
            "Starting resources must be whole numbers."
        )
        controller.on_user_edit()
        assert controller.session.invalid
        assert controller.session.has_unsaved_risk
        assert controller.save() is False
        assert managed_path.read_bytes() == original_bytes

        economy.replace_starting_resources(
            saved.document.starting_resources
        )
        view.name = saved.document.name
        controller.on_user_edit()
        assert not controller.session.invalid
        assert not controller.session.dirty
        assert not controller.session.has_unsaved_risk
        assert not view.title.endswith(" *")

        view.name = "Valid Change"
        controller.on_user_edit()
        assert controller.session.dirty
        assert view.title.endswith(" *")

        print("Desktop scenario-manager behavioral validation completed successfully.")


if __name__ == "__main__":
    main()
