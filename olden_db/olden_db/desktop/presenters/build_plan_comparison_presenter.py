from __future__ import annotations

from olden_db.comparison import (
    AcceptedBuildPlanInput,
    BuildPlanComparison,
    BuildPlanComparisonStatus,
    BuildStepRelationship,
)
from olden_db.constants import RESOURCE_NAMES
from olden_db.planning_workspace import DEFAULT_BASE_PLAN_ID
from olden_db.query import PlanningQueryService
from olden_db.scenario_comparison import ComparisonRole, ScenarioComparisonCollection

from ..build_plan_comparison_presentation import (
    AlignedStepComparisonPresentation,
    BuildPlanComparisonPresentation,
    BuildPlanComparisonSummaryPresentation,
    ComparisonActionPresentation,
    ComparisonPresentationStatus,
    ComparisonSideStepPresentation,
    ResourceDeltaPresentation,
)
from ..formatting import format_game_date
from ..scenario_presenters import ScenarioAwarePlannerPresenter


_RELATIONSHIP_TEXT = {
    BuildStepRelationship.MATCHED: "Matched",
    BuildStepRelationship.DIFFERENT: "Different",
    BuildStepRelationship.LEFT_ONLY: "Left Only",
    BuildStepRelationship.RIGHT_ONLY: "Right Only",
}


class ComparisonAwarePlannerPresenter(ScenarioAwarePlannerPresenter):
    """Existing workspace presenter with comparison lifecycle notifications."""

    def __init__(self, *args, on_comparison_changed=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._on_comparison_changed = on_comparison_changed or (lambda: None)

    def _render_snapshot(self, snapshot) -> None:
        super()._render_snapshot(snapshot)
        self._on_comparison_changed()


class BuildPlanComparisonPresenter:
    """Request and project authoritative BE-013 accepted-plan comparisons."""

    def __init__(
        self,
        service: PlanningQueryService,
        collection: ScenarioComparisonCollection,
        view,
    ) -> None:
        self._service = service
        self._collection = collection
        self._view = view
        self._last_successful: BuildPlanComparisonPresentation | None = None
        self._last_rendered: BuildPlanComparisonPresentation | None = None
        self._display_text_cache = {}

    def refresh(self) -> None:
        presentation = self._build_presentation()
        if presentation != self._last_rendered:
            self._view.render_comparison(presentation)
            self._last_rendered = presentation

    def _build_presentation(self) -> BuildPlanComparisonPresentation:
        snapshot = self._collection.snapshot()
        left_member = next(
            (member for member in snapshot.members if member.comparison_role is ComparisonRole.LEFT),
            None,
        )
        right_member = next(
            (member for member in snapshot.members if member.comparison_role is ComparisonRole.RIGHT),
            None,
        )

        if left_member is None or right_member is None:
            return BuildPlanComparisonPresentation(
                status=ComparisonPresentationStatus.UNAVAILABLE,
                heading="Comparison unavailable",
                detail="Assign both Left and Right comparison workspaces.",
            )

        left_base = left_member.workspace.base(DEFAULT_BASE_PLAN_ID)
        right_base = right_member.workspace.base(DEFAULT_BASE_PLAN_ID)

        if left_base.accepted_result is None or right_base.accepted_result is None:
            return BuildPlanComparisonPresentation(
                status=ComparisonPresentationStatus.UNAVAILABLE,
                heading="Comparison unavailable",
                detail="Both comparison workspaces require an accepted plan.",
            )

        if not left_base.result_is_current or not right_base.result_is_current:
            if self._last_successful is not None:
                previous = self._last_successful
                return BuildPlanComparisonPresentation(
                    status=ComparisonPresentationStatus.WAITING,
                    heading="Waiting for current accepted plans",
                    detail=(
                        "The previous successful comparison remains visible "
                        "while one or both workspaces update."
                    ),
                    retained_previous_comparison=True,
                    summary=previous.summary,
                    resource_deltas=previous.resource_deltas,
                    aligned_steps=previous.aligned_steps,
                    shared_actions=previous.shared_actions,
                    left_only_actions=previous.left_only_actions,
                    right_only_actions=previous.right_only_actions,
                )
            return BuildPlanComparisonPresentation(
                status=ComparisonPresentationStatus.WAITING,
                heading="Waiting for accepted plans",
                detail="Planning must finish in both comparison workspaces.",
            )

        outcome = self._service.compare_accepted_build_plans(
            AcceptedBuildPlanInput(
                left_base.accepted_result,
                correlation_id=left_member.workspace_id.value,
            ),
            AcceptedBuildPlanInput(
                right_base.accepted_result,
                correlation_id=right_member.workspace_id.value,
            ),
        )

        if outcome.failure is not None:
            return BuildPlanComparisonPresentation(
                status=ComparisonPresentationStatus.FAILURE,
                heading="Comparison could not be completed",
                detail=outcome.failure.message,
            )

        assert outcome.comparison is not None
        presentation = self._project(
            outcome.comparison,
            left_member.label,
            right_member.label,
        )
        self._last_successful = presentation
        return presentation

    def _project(
        self,
        comparison: BuildPlanComparison,
        left_label: str,
        right_label: str,
    ) -> BuildPlanComparisonPresentation:
        equivalent = comparison.status is BuildPlanComparisonStatus.EQUIVALENT
        summary = BuildPlanComparisonSummaryPresentation(
            left_label=left_label,
            right_label=right_label,
            left_completion_date=format_game_date(comparison.left_completion_date),
            right_completion_date=format_game_date(comparison.right_completion_date),
            completion_date_delta=self._signed(comparison.completion_date_delta),
            left_construction_count=str(comparison.left_step_count),
            right_construction_count=str(comparison.right_step_count),
            construction_count_delta=self._signed(comparison.step_count_delta),
            equivalent_text=(
                "Both accepted plans are equivalent."
                if equivalent
                else "The accepted plans contain factual differences."
            ),
        )
        resource_deltas = tuple(
            ResourceDeltaPresentation(
                resource_name=name.replace("_", " ").title(),
                value_text=self._signed(
                    getattr(comparison.final_cumulative_cost_delta, name)
                ),
            )
            for name in RESOURCE_NAMES
        )
        aligned = tuple(
            AlignedStepComparisonPresentation(
                position=item.comparison_position,
                left=self._step_side(item.left_step),
                relationship=_RELATIONSHIP_TEXT[item.relationship],
                relationship_key=item.relationship.value,
                right=self._step_side(item.right_step),
            )
            for item in comparison.step_comparisons
        )
        shared = tuple(
            ComparisonActionPresentation(
                building_name=self._display_text(building),
                level_text=str(building.level),
                date_text="",
            )
            for building in comparison.common_buildings
        )
        left_only = tuple(self._action(step) for step in comparison.left_only_actions)
        right_only = tuple(self._action(step) for step in comparison.right_only_actions)

        return BuildPlanComparisonPresentation(
            status=ComparisonPresentationStatus.READY,
            heading=(
                "Accepted plans are equivalent"
                if equivalent
                else "Accepted plan comparison ready"
            ),
            detail=(
                "All values below are authoritative backend facts using "
                "the backend's right-minus-left sign convention."
            ),
            summary=summary,
            resource_deltas=resource_deltas,
            aligned_steps=aligned,
            shared_actions=shared,
            left_only_actions=left_only,
            right_only_actions=right_only,
        )

    def _step_side(self, step):
        if step is None:
            return None
        return ComparisonSideStepPresentation(
            building_name=self._display_text(step.building),
            level_text=str(step.building.level),
            date_text=format_game_date(step.date),
        )

    def _action(self, step) -> ComparisonActionPresentation:
        return ComparisonActionPresentation(
            building_name=self._display_text(step.building),
            level_text=str(step.building.level),
            date_text=format_game_date(step.date),
        )

    def _display_text(self, building) -> str:
        cached = self._display_text_cache.get(building)
        if cached is None:
            cached = self._service.get_building_display_text(building)
            self._display_text_cache[building] = cached
        return cached

    @staticmethod
    def _signed(value: int) -> str:
        return f"+{value}" if value > 0 else str(value)
