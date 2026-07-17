from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from olden_db.scenario_document_export import export_scenario_document
from olden_db.scenario_persistence import LocalScenarioRepository
from scripts._scenario_test_support import (
    NOW,
    load_managed,
    make_controller,
    make_document,
)


def main():
    with TemporaryDirectory() as directory:
        root = Path(directory)
        repository = LocalScenarioRepository(root / "repository")
        controller, _planner, economy, view = make_controller(repository)

        first = load_managed(controller, repository, make_document())
        first_path = repository.scenario_directory / (
            f"{first.document.scenario_id}.json"
        )

        # Invalid edits prompt on New, Open, Import, and Close.
        export_path = root / "import.json"
        export_scenario_document(first.document, export_path)
        for operation in ("new", "open", "import", "close"):
            view.name = ""
            controller.on_user_edit()
            view.unsaved_action = "cancel"
            before = controller.session
            if operation == "new":
                result = controller.new()
            elif operation == "open":
                result = controller.open()
            elif operation == "import":
                view.import_source = str(export_path)
                result = controller.import_document()
            else:
                result = controller.can_close()
            assert result is False
            assert controller.session is before
            assert view.name == ""

        # Stale Save preserves stored bytes.
        view.name = first.document.name
        controller.on_user_edit()
        external = repository.get_scenario(first.document.scenario_id)
        from dataclasses import replace
        repository.save_scenario(
            replace(external.document, name="External Update"),
            expected_token=external.conflict_token,
            now=NOW,
        )
        stored_before = first_path.read_bytes()
        view.name = "Local stale edit"
        controller.on_user_edit()
        view.conflict_copy = False
        assert controller.save() is False
        assert first_path.read_bytes() == stored_before

        # Save As after conflict creates a new identity.
        view.conflict_copy = True
        view.next_name = "Conflict Copy"
        assert controller.save() is True
        assert controller.session.active_document.scenario_id != first.document.scenario_id
        assert controller.session.repository_membership

        # Stale Delete preserves bytes and membership.
        active_id = controller.session.active_document.scenario_id
        active_path = repository.scenario_directory / f"{active_id}.json"
        active_loaded = repository.get_scenario(active_id)
        repository.save_scenario(
            replace(active_loaded.document, description="External Update"),
            expected_token=active_loaded.conflict_token,
            now=NOW,
        )
        bytes_before_delete = active_path.read_bytes()
        assert controller.delete() is False
        assert active_path.read_bytes() == bytes_before_delete
        assert controller.session.repository_membership

        # Complete document -> UI -> document round trip.
        reloaded = repository.get_scenario(active_id)
        controller._apply(reloaded.document, False)
        controller.session.accept_loaded(
            reloaded.document,
            reloaded.conflict_token,
        )
        round_trip = controller._build()
        assert round_trip == reloaded.document

        # Export valid unsaved content without changing session or repository.
        view.name = "Unsaved Export Name"
        controller.on_user_edit()
        session_before = controller.session
        repository_before = active_path.read_bytes()
        destination = root / "unsaved-export.json"
        view.export_destination = str(destination)
        assert controller.export() is True
        assert destination.exists()
        assert controller.session is session_before
        assert controller.session.dirty
        assert active_path.read_bytes() == repository_before

        # Invalid recruitment state remains protected.
        economy.mark_recruitment_invalid(
            "Recruitment quantities cannot be negative."
        )
        controller.on_user_edit()
        assert controller.session.invalid
        assert controller.session.has_unsaved_risk
        assert view.title.endswith(" *")

        print("Desktop scenario-workflow behavioral validation completed successfully.")


if __name__ == "__main__":
    main()
