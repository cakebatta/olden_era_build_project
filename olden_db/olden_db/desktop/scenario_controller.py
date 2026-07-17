from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from olden_db.models import BuildingKey
from olden_db.scenario_document_export import export_scenario_document
from olden_db.scenario_persistence import (
    LocalScenarioRepository,
    ScenarioConflictError,
    ScenarioDocumentValidationError,
    ScenarioPersistenceError,
    create_scenario_document,
    duplicate_scenario_document,
    rename_scenario_document,
)

from .scenario_session import ScenarioSession, ScenarioSource


EXPECTED_EDIT_ERRORS = (
    ValueError,
    TypeError,
    ScenarioDocumentValidationError,
)


class ScenarioController:
    def __init__(
        self,
        repository,
        planner_state,
        economy_state,
        planner_presenter,
        economy_presenter,
        view,
        set_status,
        *,
        now=None,
    ):
        self.repository = repository
        self.planner_state = planner_state
        self.economy_state = economy_state
        self.planner_presenter = planner_presenter
        self.economy_presenter = economy_presenter
        self.view = view
        self.set_status = set_status
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.session = None
        self._applying = False

    def _timestamp(self) -> datetime:
        return self.now().replace(microsecond=0)

    def initialize(self):
        self.view.set_handlers(
            **{
                "new": self.new,
                "open": self.open,
                "save": self.save,
                "save_as": self.save_as,
                "rename": self.rename,
                "duplicate": self.duplicate,
                "delete": self.delete,
                "import": self.import_document,
                "export": self.export,
                "edited": self.on_user_edit,
            }
        )
        self.new(force=True)

    def _default_document(self):
        faction = self.planner_presenter.available_factions()[0]
        sid = self.planner_presenter.available_buildings(faction)[0]
        level = self.planner_presenter.available_levels(faction, sid)[0]
        return create_scenario_document(
            name="Untitled Scenario",
            faction=faction,
            target_sid=sid,
            target_level=level,
            now=self._timestamp(),
        )

    def _protect(self):
        if not self.session or not self.session.has_unsaved_risk:
            return True

        action = self.view.choose_unsaved_action(
            self.session.display_name.rstrip(" *")
        )
        if action == "cancel":
            return False
        if action == "discard":
            return True
        return self.save()

    def new(self, force=False):
        if not force and not self._protect():
            return False
        try:
            document = self._default_document()
        except Exception as exc:
            return self._fail("New scenario", exc)

        self.session = ScenarioSession(document)
        self._apply(document, False)
        self._refresh()
        self.set_status("New unsaved scenario created.")
        return True

    def open(self):
        if not self._protect():
            return False
        try:
            chosen = self.view.choose_scenario(
                self.repository.list_scenarios()
            )
            if chosen is None:
                return False
            loaded = self.repository.get_scenario(chosen.scenario_id)
        except Exception as exc:
            return self._fail("Open", exc)

        self.session = ScenarioSession(loaded.document)
        self.session.accept_loaded(
            loaded.document,
            loaded.conflict_token,
        )
        self._apply(loaded.document, True)
        self._refresh()
        return True

    def save(self):
        if not self.session:
            return False
        document = self._candidate("Save")
        if document is None:
            return False

        try:
            result = self.repository.save_scenario(
                document,
                expected_token=(
                    self.session.repository_token
                    if self.session.repository_membership
                    else None
                ),
                now=self._timestamp(),
            )
        except ScenarioConflictError as exc:
            self._fail("Save", exc)
            return (
                self.save_as()
                if self.view.choose_conflict_copy()
                else False
            )
        except Exception as exc:
            return self._fail("Save", exc)

        self.session.accept_saved(
            result.document,
            result.conflict_token,
        )
        self._apply_metadata(result.document)
        self._refresh()
        self.set_status(f"Saved scenario: {result.document.name}.")
        return True

    def save_as(self):
        document = self._candidate("Save As")
        if document is None:
            return False

        name = self.view.ask_name(
            "Save Scenario As",
            document.name,
        )
        if name is None:
            return False

        try:
            timestamp = self._timestamp()
            copied = duplicate_scenario_document(
                document,
                now=timestamp,
                name=name,
            )
            result = self.repository.save_scenario(
                copied,
                expected_token=None,
                now=timestamp,
            )
        except Exception as exc:
            return self._fail("Save As", exc)

        self.session = ScenarioSession(result.document)
        self.session.accept_saved(
            result.document,
            result.conflict_token,
        )
        self._apply(result.document, True)
        self._refresh()
        return True

    def rename(self):
        document = self._candidate("Rename")
        if document is None:
            return False

        name = self.view.ask_name(
            "Rename Scenario",
            document.name,
        )
        if name is None:
            return False

        try:
            renamed = rename_scenario_document(document, name)
        except Exception as exc:
            return self._fail("Rename", exc)

        self.session.mark_ui_edited()
        self.session.update_candidate(renamed)
        self.session.reconcile_dirty_state()
        self._apply_metadata(renamed)
        self._refresh()
        return True

    def duplicate(self):
        document = self._candidate("Duplicate")
        if document is None:
            return False

        name = self.view.ask_name(
            "Duplicate Scenario",
            f"{document.name} Copy",
        )
        if name is None:
            return False

        try:
            timestamp = self._timestamp()
            copied = duplicate_scenario_document(
                document,
                now=timestamp,
                name=name,
            )
            result = self.repository.save_scenario(
                copied,
                expected_token=None,
                now=timestamp,
            )
        except Exception as exc:
            return self._fail("Duplicate", exc)

        self.session = ScenarioSession(result.document)
        self.session.accept_saved(
            result.document,
            result.conflict_token,
        )
        self._apply(result.document, True)
        self._refresh()
        return True

    def delete(self):
        if (
            not self.session
            or not self.session.repository_membership
        ):
            self.view.show_info(
                "The active scenario is not stored in the local library."
            )
            return False

        document = self._candidate("Delete")
        if document is None:
            return False
        if not self.view.confirm_delete(document.name):
            return False

        try:
            self.repository.delete_scenario(
                document.scenario_id,
                expected_token=self.session.repository_token,
            )
        except Exception as exc:
            return self._fail("Delete", exc)

        self.session.update_candidate(document)
        self.session.detach_after_delete()
        self._refresh()
        self.set_status(
            "Scenario deleted; current content retained as unsaved."
        )
        return True

    def import_document(self):
        if not self._protect():
            return False

        source = self.view.import_path()
        if not source:
            return False

        try:
            result = self.repository.import_scenario(
                source,
                now=self._timestamp(),
            )
        except Exception as exc:
            return self._fail("Import", exc)

        self.session = ScenarioSession(result.document)
        self.session.accept_saved(
            result.document,
            result.conflict_token,
            source=ScenarioSource.IMPORTED,
        )
        self._apply(result.document, True)
        self._refresh()
        return True

    def export(self):
        document = self._candidate("Export")
        if document is None:
            return False

        destination = self.view.export_path(
            f"{document.name}.json"
        )
        if not destination:
            return False

        path = Path(destination)
        overwrite = (
            path.exists()
            and self.view.confirm_overwrite(path.name)
        )
        if path.exists() and not overwrite:
            return False

        try:
            export_scenario_document(
                document,
                path,
                overwrite=overwrite,
            )
        except Exception as exc:
            return self._fail("Export", exc)

        self.set_status(
            "Scenario exported without changing save state."
        )
        self._refresh()
        return True

    def can_close(self):
        return self._protect()

    def on_user_edit(self):
        if self._applying or not self.session:
            return

        self.session.mark_ui_edited()
        try:
            candidate = self._build()
        except EXPECTED_EDIT_ERRORS as exc:
            self.session.mark_invalid_edit(exc)
        else:
            self.session.update_candidate(candidate)
            self.session.reconcile_dirty_state()

        self._refresh()

    def _build(self):
        if not self.session:
            raise ValueError("No active scenario")
        if not self.planner_state.has_complete_target:
            raise ValueError(
                "Faction, target, and level are required"
            )
        if not self.economy_state.starting_resources_valid:
            raise (
                self.economy_state.starting_resources_issue
                or ValueError("Starting resources are invalid.")
            )
        if self.economy_state.recruitment_issue is not None:
            raise self.economy_state.recruitment_issue

        base = (
            self.session.current_document
            or self.session.active_document
        )
        name, description, notes = self.view.metadata()

        return replace(
            base,
            name=name,
            description=description,
            notes=notes,
            faction=self.planner_state.selected_faction,
            target=BuildingKey(
                self.planner_state.selected_faction,
                self.planner_state.selected_building_sid,
                self.planner_state.selected_level,
            ),
            starting_date=self.planner_state.starting_date,
            planning_scenario=self.planner_state.active_scenario,
            starting_resources=self.economy_state.starting_resources,
            recruitment_actions=(
                self.economy_state.recruitment_actions
            ),
        )

    def _candidate(self, action):
        try:
            candidate = self._build()
        except EXPECTED_EDIT_ERRORS as exc:
            if self.session:
                self.session.mark_invalid_edit(exc)
                self._refresh()
            self._fail(action, exc)
            return None

        if self.session:
            self.session.update_candidate(candidate)
            self.session.reconcile_dirty_state()
        return candidate

    def _apply(self, document, regenerate):
        self._applying = True
        try:
            self._apply_metadata(document)
            self.planner_presenter.apply_document(document)
            self.economy_presenter.apply_document(document)
        finally:
            self._applying = False

        if regenerate:
            self.planner_presenter.on_generate_plan()
            self.economy_presenter.on_generate()

    def _apply_metadata(self, document):
        self.view.apply_metadata(
            document.name,
            document.description,
            document.notes,
        )

    def _refresh(self):
        self.view.set_title(
            self.session.display_name
            if self.session
            else "No active scenario"
        )

    def _fail(self, action, exc):
        detail = getattr(exc, "detail", str(exc))
        if isinstance(exc, ScenarioConflictError):
            message = (
                f"{action} detected a stored-scenario conflict. "
                "Nothing was overwritten."
            )
        elif detail:
            message = (
                f"{action} failed: {detail}. "
                "Your current scenario and edits were preserved."
            )
        else:
            message = (
                f"{action} could not be completed. "
                "Your current scenario and edits were preserved."
            )
        self.view.show_error(message)
        return False
