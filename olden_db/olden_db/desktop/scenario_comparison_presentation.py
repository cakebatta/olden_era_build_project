from __future__ import annotations

from dataclasses import dataclass

from olden_db.scenario_comparison import ComparisonRole, WorkspaceId


@dataclass(frozen=True, slots=True)
class ScenarioComparisonMemberPresentation:
    workspace_id: WorkspaceId
    order_index: int
    label: str
    comparison_role: ComparisonRole | None
    identity_text: str
    can_remove: bool


@dataclass(frozen=True, slots=True)
class ScenarioComparisonPresentation:
    collection_revision: int
    members: tuple[ScenarioComparisonMemberPresentation, ...]
    left_workspace_id: WorkspaceId | None
    right_workspace_id: WorkspaceId | None
