from datetime import datetime, timezone
from uuid import UUID
from olden_db.models import ResourceCost
from olden_db.planner import GameDate
from olden_db.scenario import PlanningScenario
from olden_db.scenario_persistence import create_scenario_document, rename_scenario_document
from olden_db.desktop.scenario_session import ScenarioSession

def main():
    now=datetime(2026,1,1,tzinfo=timezone.utc)
    doc=create_scenario_document(name="A",faction="nature",target_sid="Build_Tier_1",target_level=1,now=now,
        scenario_id_factory=lambda:UUID("00000000-0000-0000-0000-000000000001"))
    session=ScenarioSession(doc)
    assert session.has_unsaved_risk and not session.dirty
    session.update_candidate(rename_scenario_document(doc,"B"))
    assert session.dirty
    session.accept_saved(session.current_document,"opaque-token")
    assert not session.dirty and session.repository_membership and session.repository_token=="opaque-token"
    session.detach_after_delete()
    assert session.has_unsaved_risk and not session.repository_membership and session.repository_token is None
    print("Desktop scenario-session validation completed successfully.")
if __name__=="__main__":main()
