from __future__ import annotations

from olden_db.planning_workspace import DEFAULT_BASE_PLAN_ID
from olden_db.scenario_comparison import (
    ComparisonRole,
    ScenarioComparisonCollection,
    ScenarioComparisonExecutionCoordinator,
    WorkspaceId,
)

from ..comparison_execution_adapter import CollectionWorkspaceExecutionAdapter
from ..scenario_comparison_presentation import (
    ScenarioComparisonMemberPresentation,
    ScenarioComparisonPresentation,
)
from .build_plan_comparison_presenter import (
    BuildPlanComparisonPresenter,
    ComparisonAwarePlannerPresenter,
)
from ..state import PlannerState


class ScenarioComparisonWorkspacePresenter:
    """Compose one existing planner presenter/view pair per collection member."""

    def __init__(
        self,
        service,
        collection: ScenarioComparisonCollection,
        coordinator: ScenarioComparisonExecutionCoordinator,
        view,
        set_status,
        *,
        on_primary_context_changed=None,
    ) -> None:
        self._service = service
        self._collection = collection
        self._coordinator = coordinator
        self._view = view
        self._set_status = set_status
        self._on_primary_context_changed = (
            on_primary_context_changed or (lambda: None)
        )
        self._presenters: dict[
            WorkspaceId,
            ScenarioAwarePlannerPresenter,
        ] = {}
        self._states: dict[WorkspaceId, PlannerState] = {}
        self._last_collection_presentation: (
            ScenarioComparisonPresentation | None
        ) = None
        self._primary_workspace_id = collection.workspace_ids[0]
        self._build_plan_comparison_presenter = BuildPlanComparisonPresenter(
            service,
            collection,
            view.comparison_view,
        )

        view.set_event_handlers(
            on_create=self.on_create_workspace,
            on_duplicate=self.on_duplicate_workspace,
            on_remove=self.on_remove_workspace,
            on_label=self.on_label_changed,
            on_role=self.on_role_changed,
        )
        self._reconcile(collection.snapshot())

    @property
    def primary_workspace_id(self) -> WorkspaceId:
        return self._primary_workspace_id

    @property
    def primary_presenter(self) -> ScenarioAwarePlannerPresenter:
        return self._presenters[self._primary_workspace_id]

    @property
    def primary_state(self) -> PlannerState:
        return self._states[self._primary_workspace_id]

    def set_primary_context_changed_handler(self, handler) -> None:
        self._on_primary_context_changed = handler
        self.primary_presenter._on_context_changed = handler

    def initialize(self) -> None:
        for presenter in self._presenters.values():
            presenter.initialize()
        self._render_collection(self._collection.snapshot())

    def on_create_workspace(self) -> None:
        workspace_id = self._collection.create_workspace()
        snapshot = self._collection.snapshot()
        self._reconcile(snapshot)
        self._presenters[workspace_id].initialize()
        self._render_collection(snapshot)
        self._set_status("Created a new empty planning workspace.")

    def on_duplicate_workspace(
        self,
        source_workspace_id: WorkspaceId,
    ) -> None:
        workspace_id = self._collection.duplicate_workspace(
            source_workspace_id
        )
        snapshot = self._collection.snapshot()
        self._reconcile(snapshot)
        presenter = self._presenters[workspace_id]
        presenter.initialize()
        selection = snapshot.member(workspace_id).workspace.base(
            DEFAULT_BASE_PLAN_ID
        ).selection
        if selection is not None:
            presenter.hydrate_semantic_selection(selection)
            outcome = self._coordinator.execute(
                self._collection,
                workspace_id,
            )
            presenter.render_workspace_snapshot(
                outcome.collection_snapshot.member(workspace_id).workspace
            )
        self._render_collection(self._collection.snapshot())
        self._set_status(
            "Duplicated semantic planning inputs into a new workspace."
        )

    def on_remove_workspace(self, workspace_id: WorkspaceId) -> None:
        if workspace_id == self._primary_workspace_id:
            self._set_status(
                "The primary persisted workspace cannot be removed."
            )
            return
        self._collection.remove_workspace(workspace_id)
        self._presenters.pop(workspace_id, None)
        self._states.pop(workspace_id, None)
        self._view.remove_workspace_panel(workspace_id)
        self._render_collection(self._collection.snapshot())
        self._set_status("Removed the selected planning workspace.")

    def on_label_changed(
        self,
        workspace_id: WorkspaceId,
        label: str,
    ) -> None:
        resolved = label.strip()
        if not resolved:
            self._render_collection(self._collection.snapshot())
            self._set_status("Workspace labels cannot be blank.")
            return
        self._collection.set_label(workspace_id, resolved)
        self._render_collection(self._collection.snapshot())
        self._set_status(f"Workspace label updated to {resolved}.")

    def on_role_changed(
        self,
        workspace_id: WorkspaceId,
        role: ComparisonRole | None,
    ) -> None:
        snapshot = self._collection.snapshot()
        if role is not None:
            occupied = next(
                (
                    member.workspace_id
                    for member in snapshot.members
                    if member.comparison_role is role
                    and member.workspace_id != workspace_id
                ),
                None,
            )
            if occupied is not None:
                self._collection.set_comparison_role(occupied, None)
        self._collection.set_comparison_role(workspace_id, role)
        self._render_collection(self._collection.snapshot())
        self._set_status(
            "Comparison roles updated without replanning."
        )

    def refresh(self) -> None:
        snapshot = self._collection.snapshot()
        for member in snapshot.members:
            self._presenters[
                member.workspace_id
            ].render_workspace_snapshot(member.workspace)
        self._render_collection(snapshot)

    def _reconcile(self, snapshot) -> None:
        current_ids = {
            member.workspace_id
            for member in snapshot.members
        }
        for workspace_id in tuple(self._presenters):
            if workspace_id not in current_ids:
                self._presenters.pop(workspace_id, None)
                self._states.pop(workspace_id, None)
                self._view.remove_workspace_panel(workspace_id)

        for member in snapshot.members:
            if member.workspace_id in self._presenters:
                continue
            planner_view = self._view.create_workspace_panel(
                member.workspace_id
            )
            state = PlannerState()
            adapter = CollectionWorkspaceExecutionAdapter(
                self._collection,
                self._coordinator,
                member.workspace_id,
            )
            presenter = ComparisonAwarePlannerPresenter(
                self._service,
                self._collection.workspace(member.workspace_id),
                adapter,
                state,
                planner_view,
                self._set_status,
                on_comparison_changed=(
                    self._build_plan_comparison_presenter.refresh
                ),
                on_context_changed=(
                    self._on_primary_context_changed
                    if member.workspace_id == self._primary_workspace_id
                    else None
                ),
            )
            self._states[member.workspace_id] = state
            self._presenters[member.workspace_id] = presenter

    def _render_collection(self, snapshot) -> None:
        presentation = ScenarioComparisonPresentation(
            collection_revision=snapshot.collection_revision,
            members=tuple(
                ScenarioComparisonMemberPresentation(
                    workspace_id=member.workspace_id,
                    order_index=member.order_index,
                    label=member.label,
                    comparison_role=member.comparison_role,
                    identity_text=member.workspace_id.value[:8],
                    can_remove=(
                        len(snapshot.members) > 1
                        and member.workspace_id
                        != self._primary_workspace_id
                    ),
                )
                for member in snapshot.members
            ),
            left_workspace_id=next(
                (
                    member.workspace_id
                    for member in snapshot.members
                    if member.comparison_role is ComparisonRole.LEFT
                ),
                None,
            ),
            right_workspace_id=next(
                (
                    member.workspace_id
                    for member in snapshot.members
                    if member.comparison_role is ComparisonRole.RIGHT
                ),
                None,
            ),
        )
        if presentation != self._last_collection_presentation:
            self._view.render_collection(presentation)
            self._last_collection_presentation = presentation
        self._build_plan_comparison_presenter.refresh()
