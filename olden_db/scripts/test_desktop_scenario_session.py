from dataclasses import replace

from olden_db.desktop.scenario_session import ScenarioSession
from scripts._scenario_test_support import make_document


def main():
    document = make_document()
    session = ScenarioSession(document)
    assert session.has_unsaved_risk
    assert not session.dirty

    session.accept_saved(document, "opaque")
    assert not session.has_unsaved_risk
    assert session.display_name == "Managed Scenario"

    session.mark_ui_edited()
    session.mark_invalid_edit(ValueError("name cannot be blank"))
    assert session.invalid
    assert session.has_unsaved_risk
    assert session.display_name == "Managed Scenario *"
    assert session.last_valid_candidate == document

    changed = replace(document, name="Changed")
    session.update_candidate(changed)
    session.reconcile_dirty_state()
    assert session.dirty
    assert session.display_name == "Changed *"

    session.update_candidate(document)
    session.reconcile_dirty_state()
    assert not session.dirty
    assert not session.has_unsaved_risk
    assert session.display_name == "Managed Scenario"

    session.detach_after_delete()
    assert session.has_unsaved_risk
    assert session.display_name.endswith(" *")

    print("Desktop scenario-session behavioral validation completed successfully.")


if __name__ == "__main__":
    main()
