from __future__ import annotations

from dataclasses import dataclass

from .comparison import (
    AcceptedBuildPlanInput,
    BuildPlanComparisonOutcome,
    PlanComparison,
    compare_accepted_build_plans,
    compare_build_plans,
)
from .database import LoadedGameData, load_default_game_data
from .decision_summary import DecisionSummary, summarize_plan_comparison
from .graph import DependencyGraph, build_dependency_graph, iter_topological_orders
from .income_timeline import calculate_income_timeline
from .localization import parse_localization_file
from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
from .objective_query_models import (
    BuildStepExplanation,
    MultiObjectivePlanningResultView,
    ObjectiveCompletionView,
    ObjectivePlanningSummary,
    ObjectiveSummary,
    PrerequisiteProvenance,
)
from .objective_planning import (
    BuildingCompletionObjective,
    CrossTownObjectiveError,
    EmptyObjectiveSetError,
    IncompatiblePlanningScenarioError,
    MultiObjectivePlannerResult,
    ObjectivePlanningFailure,
    ObjectiveSet,
    TownPlanningRequest,
    TownState,
    UnknownObjectiveTargetError,
    UnsupportedObjectiveTypeError,
    plan_objective_request,
)
from .paths import require_english_planner_localization_file
from .planner_localization import (
    PlannerLocalizationCatalog,
    build_planner_localization_catalog,
)
from .planner import (
    BuildPlan,
    GameDate,
    PlannerResult,
    plan_build_order,
    plan_build_order_result,
)
from .recruitment_stock import calculate_recruitment_stock
from .resource_ledger import (
    RecruitmentAction,
    ResourceLedger,
    build_resource_ledger,
)
from .scenario import (
    PlanningScenario,
    PrerequisiteStatus,
    resolve_effective_starting_buildings,
)


class QueryError(ValueError):
    """Base exception for invalid Query Layer requests."""


class UnknownFactionError(QueryError):
    """Raised when a requested faction is not present."""


class UnknownBuildingError(QueryError):
    """Raised when a requested building level is not present."""


class UnknownUnitError(QueryError):
    """Raised when a requested unit identity is not present."""


@dataclass(frozen=True, slots=True)
class PlanningQueryService:
    """Stable public interface for deterministic building-planning queries."""

    _data: LoadedGameData
    _planner_localization: PlannerLocalizationCatalog | None = None

    @classmethod
    def from_default_game_data(cls) -> "PlanningQueryService":
        """Create a ready-to-use service from the canonical game data."""
        data = load_default_game_data()
        localization = parse_localization_file(
            require_english_planner_localization_file(),
            language="english",
        )
        return cls(
            data,
            build_planner_localization_catalog(data, localization),
        )

    def list_factions(self) -> tuple[str, ...]:
        return tuple(sorted(self._data.cities.cities))

    def get_faction_display_name(self, faction: str) -> str:
        self._get_city(faction)
        if self._planner_localization is None:
            return faction
        return self._planner_localization.get_faction_display_name(faction)

    def get_faction_display_text(self, faction: str) -> str:
        """Compatibility alias for the planner faction display-name operation."""
        return self.get_faction_display_name(faction)

    def get_unit_display_name(self, faction: str, unit_sid: str) -> str:
        definition = self._get_unit(faction, unit_sid)
        if self._planner_localization is None:
            return definition.sid
        return self._planner_localization.get_unit_display_name(faction, unit_sid)

    def get_unit_display_text(self, faction_or_unit_sid: str, unit_sid: str | None = None) -> str:
        """Return a unit display name while preserving the legacy one-argument form."""
        if unit_sid is None:
            definition = self._get_unit_by_sid(faction_or_unit_sid)
            return self.get_unit_display_name(definition.faction, definition.sid)
        return self.get_unit_display_name(faction_or_unit_sid, unit_sid)

    def get_upgrade_display_name(self, faction: str, upgrade_sid: str) -> str:
        definition = self._get_unit(faction, upgrade_sid)
        if self._planner_localization is None:
            return definition.sid
        try:
            return self._planner_localization.get_upgrade_display_name(faction, upgrade_sid)
        except KeyError:
            return self._planner_localization.get_unit_display_name(faction, upgrade_sid)

    def get_upgrade_display_text(self, faction: str, upgrade_sid: str) -> str:
        return self.get_upgrade_display_name(faction, upgrade_sid)

    def list_faction_unit_display_texts(self, faction: str) -> tuple[tuple[int, str, str], ...]:
        self._get_city(faction)
        return tuple(
            (definition.tier, definition.sid, self.get_unit_display_text(definition.sid))
            for definition in self._data.units.faction_units(faction)
        )

    def list_buildings(self, faction: str) -> tuple[str, ...]:
        city = self._get_city(faction)
        return tuple(sorted({key.sid for key in city.buildings}))

    def list_building_levels(self, faction: str, sid: str) -> tuple[int, ...]:
        city = self._get_city(faction)
        if not sid:
            raise QueryError("sid cannot be empty")
        levels = tuple(sorted(key.level for key in city.buildings if key.sid == sid))
        if not levels:
            raise UnknownBuildingError(
                f"Unknown building SID: faction={faction!r}, sid={sid!r}"
            )
        return levels

    def get_building(self, faction: str, sid: str, level: int) -> BuildingLevel:
        city = self._get_city(faction)
        key = self._make_key(faction, sid, level)
        try:
            return city.buildings[key]
        except KeyError as exc:
            raise UnknownBuildingError(
                f"Unknown building: faction={faction!r}, sid={sid!r}, level={level}"
            ) from exc

    def get_building_display_name(self, building: BuildingKey) -> str:
        """Return planner-facing text without changing canonical BuildingKey identity."""
        if not isinstance(building, BuildingKey):
            raise TypeError("building must be a BuildingKey")
        self.get_building(building.faction, building.sid, building.level)
        if self._planner_localization is None:
            return building.sid
        return self._planner_localization.get_building_display_name(building)

    def get_building_display_text(self, building: BuildingKey) -> str:
        """Compatibility alias for the planner building display-name operation."""
        return self.get_building_display_name(building)

    def get_prerequisites(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> tuple[BuildingLevel, ...]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        return tuple(
            city.buildings[key]
            for key in sorted(
                building.prerequisites,
                key=lambda item: (item.sid, item.level),
            )
        )

    def get_prerequisite_statuses(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> tuple[PrerequisiteStatus, ...]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        effective_starting = self._effective_starting_buildings(city, scenario)
        return tuple(
            PrerequisiteStatus(
                building=city.buildings[key],
                available_at_start=key in effective_starting,
                overridden=(
                    (key in effective_starting)
                    != city.buildings[key].constructed_on_start
                ),
            )
            for key in sorted(
                building.prerequisites,
                key=lambda item: (item.sid, item.level),
            )
        )

    def generate_objective_plan(
        self,
        request: TownPlanningRequest,
    ) -> MultiObjectivePlannerResult | ObjectivePlanningFailure:
        if not isinstance(request, TownPlanningRequest):
            raise TypeError("request must be a TownPlanningRequest")
        if not request.objective_set.objectives:
            raise EmptyObjectiveSetError("objective_set cannot be empty")

        town_state = request.town_state
        city = self._get_city(town_state.faction)
        try:
            starting_buildings = resolve_effective_starting_buildings(
                city,
                town_state.planning_scenario,
            )
        except (TypeError, ValueError) as exc:
            raise IncompatiblePlanningScenarioError(str(exc)) from exc

        for objective in request.objective_set:
            if not isinstance(objective, BuildingCompletionObjective):
                raise UnsupportedObjectiveTypeError(
                    "Unsupported Objective variant",
                    objectives=(objective,),
                )
            building = objective.building
            if building.faction != town_state.faction:
                raise CrossTownObjectiveError(
                    "Objective faction does not match request town",
                    objectives=(objective,),
                    affected_entities=(building,),
                )
            if building not in city.buildings:
                raise UnknownObjectiveTargetError(
                    f"Unknown objective target: {building}",
                    objectives=(objective,),
                    affected_entities=(building,),
                )

        return plan_objective_request(
            city,
            request,
            starting_buildings=starting_buildings,
        )

    def generate_objective_plan_view(
        self,
        request: TownPlanningRequest,
    ) -> MultiObjectivePlanningResultView | ObjectivePlanningFailure:
        """Return immutable display-ready multi-objective Query Layer models."""
        outcome = self.generate_objective_plan(request)
        if isinstance(outcome, ObjectivePlanningFailure):
            return outcome

        city = self._get_city(request.town_state.faction)
        objective_summaries = tuple(
            ObjectiveSummary(
                objective=objective,
                canonical_building=objective.building,
                display_name=self.get_building_display_name(objective.building),
            )
            for objective in request.objective_set
        )
        summary_by_objective = {
            item.objective: item for item in objective_summaries
        }

        provenance_views = []
        completion_views = []
        for dependency, completion in zip(
            outcome.objective_dependencies,
            outcome.objective_completions,
            strict=True,
        ):
            required = tuple(sorted(dependency.required_buildings))
            required_set = set(required)
            relationships = tuple(
                sorted(
                    (prerequisite, building)
                    for building in required
                    for prerequisite in city.buildings[building].prerequisites
                    if prerequisite in required_set
                )
            )
            provenance = PrerequisiteProvenance(
                objective=summary_by_objective[dependency.objective],
                required_buildings=required,
                required_build_steps=tuple(sorted(dependency.constructed_buildings)),
                satisfied_at_start=tuple(sorted(dependency.satisfied_at_start)),
                prerequisite_relationships=relationships,
            )
            provenance_views.append(provenance)
            completion_views.append(
                ObjectiveCompletionView(
                    objective=summary_by_objective[completion.objective],
                    completed=completion.completed,
                    completion_day=completion.completion_date,
                    satisfied_at_start=completion.satisfied_at_start,
                    completing_action=completion.completing_action,
                    provenance=provenance,
                )
            )

        provenance_by_building = {
            item.building: item for item in outcome.step_provenance
        }
        plan_buildings = set(outcome.plan.order)
        remaining = outcome.plan.total_cost
        step_views = []
        for step in outcome.plan.steps:
            balance_before = remaining
            balance_after = balance_before - step.individual_cost
            remaining = balance_after
            direct_prerequisites = tuple(
                sorted(
                    prerequisite
                    for prerequisite in city.buildings[step.building].prerequisites
                    if prerequisite in plan_buildings
                )
            )
            downstream = tuple(
                sorted(
                    candidate
                    for candidate in outcome.plan.order
                    if step.building in city.buildings[candidate].prerequisites
                )
            )
            provenance = provenance_by_building[step.building]
            step_views.append(
                BuildStepExplanation(
                    step_number=step.step_number,
                    building=step.building,
                    display_name=self.get_building_display_name(step.building),
                    construction_day=step.date,
                    resource_cost=step.individual_cost,
                    prerequisite_buildings=direct_prerequisites,
                    required_by_objectives=tuple(
                        summary_by_objective[objective]
                        for objective in provenance.required_by
                    ),
                    objective_targets=tuple(
                        summary_by_objective[objective]
                        for objective in provenance.objective_targets
                    ),
                    downstream_buildings_enabled=downstream,
                    resource_balance_before=balance_before,
                    resource_balance_after=balance_after,
                    income_change=city.buildings[step.building].income,
                )
            )

        summary = ObjectivePlanningSummary(
            request=request,
            objectives=objective_summaries,
            completion_state=outcome.completion_state,
            starting_day=outcome.plan.starting_date,
            completion_day=outcome.plan.completion_date,
            total_cost=outcome.plan.total_cost,
            build_action_count=outcome.plan.build_actions,
        )
        return MultiObjectivePlanningResultView(
            summary=summary,
            objective_completions=tuple(completion_views),
            prerequisite_provenance=tuple(provenance_views),
            build_steps=tuple(step_views),
            diagnostics=outcome.diagnostics,
        )

    @staticmethod
    def _single_objective_request(
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate,
        scenario: PlanningScenario | None,
    ) -> TownPlanningRequest:
        return TownPlanningRequest(
            TownState(
                faction=faction,
                starting_date=starting_date,
                planning_scenario=PlanningScenario() if scenario is None else scenario,
            ),
            ObjectiveSet(
                (
                    BuildingCompletionObjective(
                        BuildingKey(faction=faction, sid=sid, level=level)
                    ),
                )
            ),
        )

    def generate_build_plan(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> BuildPlan:
        outcome = self.generate_objective_plan(
            self._single_objective_request(
                faction, sid, level,
                starting_date=starting_date,
                scenario=scenario,
            )
        )
        if isinstance(outcome, ObjectivePlanningFailure):
            raise QueryError(f"Single-target planning failed: {outcome.kind.value}")
        return outcome.plan

    def generate_planner_result(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> PlannerResult:
        outcome = self.generate_objective_plan(
            self._single_objective_request(
                faction, sid, level,
                starting_date=starting_date,
                scenario=scenario,
            )
        )
        if isinstance(outcome, ObjectivePlanningFailure):
            raise QueryError(f"Single-target planning failed: {outcome.kind.value}")
        return PlannerResult(
            plan=outcome.plan,
            diagnostics=outcome.diagnostics,
            daily_construction_schedule=outcome.daily_construction_schedule,
        )

    def get_cumulative_cost(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> ResourceCost:
        return self.generate_build_plan(
            faction,
            sid,
            level,
            scenario=scenario,
        ).total_cost

    def enumerate_build_orders(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        max_orders: int | None = None,
        scenario: PlanningScenario | None = None,
    ) -> tuple[tuple[BuildingKey, ...], ...]:
        _, graph = self._build_graph(faction, sid, level, scenario=scenario)
        return tuple(iter_topological_orders(graph, max_orders=max_orders))

    def compare_plans(
        self,
        left_faction: str,
        left_sid: str,
        left_level: int,
        *,
        right_faction: str,
        right_sid: str,
        right_level: int,
        left_scenario: PlanningScenario | None = None,
        right_scenario: PlanningScenario | None = None,
        starting_date: GameDate = GameDate(1, 1, 1),
    ) -> PlanComparison:
        left_plan = self.generate_build_plan(
            left_faction,
            left_sid,
            left_level,
            starting_date=starting_date,
            scenario=left_scenario,
        )
        right_plan = self.generate_build_plan(
            right_faction,
            right_sid,
            right_level,
            starting_date=starting_date,
            scenario=right_scenario,
        )
        return compare_build_plans(left_plan, right_plan)

    def compare_accepted_build_plans(
        self,
        left: AcceptedBuildPlanInput | None,
        right: AcceptedBuildPlanInput | None,
    ) -> BuildPlanComparisonOutcome:
        """Compare two already accepted planner results without regenerating plans."""
        return compare_accepted_build_plans(left, right)

    def generate_decision_summary(
        self,
        left_faction: str,
        left_sid: str,
        left_level: int,
        *,
        right_faction: str,
        right_sid: str,
        right_level: int,
        left_scenario: PlanningScenario | None = None,
        right_scenario: PlanningScenario | None = None,
        starting_date: GameDate = GameDate(1, 1, 1),
    ) -> DecisionSummary:
        comparison = self.compare_plans(
            left_faction,
            left_sid,
            left_level,
            right_faction=right_faction,
            right_sid=right_sid,
            right_level=right_level,
            left_scenario=left_scenario,
            right_scenario=right_scenario,
            starting_date=starting_date,
        )
        return summarize_plan_comparison(comparison)

    def generate_resource_ledger(
        self,
        faction: str,
        sid: str,
        level: int,
        recruitment_actions: tuple[RecruitmentAction, ...],
        starting_resources: ResourceCost,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> ResourceLedger:
        """Generate one scenario-consistent income, construction, and recruitment ledger."""
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        effective_starting = self._effective_starting_buildings(city, scenario)

        graph = build_dependency_graph(
            city,
            building.key,
            starting_buildings=effective_starting,
        )
        order = next(iter_topological_orders(graph))
        plan = plan_build_order(
            city,
            graph,
            order,
            starting_date=starting_date,
        )

        through_date = plan.completion_date
        for action in recruitment_actions:
            if (
                isinstance(action, RecruitmentAction)
                and action.date.day_index > through_date.day_index
            ):
                through_date = action.date

        income_timeline = calculate_income_timeline(
            city,
            plan,
            through_date=through_date,
            starting_buildings=effective_starting,
        )
        stock = calculate_recruitment_stock(
            city,
            plan,
            through_date=through_date,
            starting_buildings=effective_starting,
        )
        return build_resource_ledger(
            city,
            plan,
            stock,
            recruitment_actions,
            starting_resources,
            starting_buildings=effective_starting,
            income_timeline=income_timeline,
        )

    def _get_city(self, faction: str) -> FactionCity:
        if not faction:
            raise QueryError("faction cannot be empty")
        try:
            return self._data.cities.city(faction)
        except KeyError as exc:
            raise UnknownFactionError(f"Unknown faction: {faction!r}") from exc

    def _get_unit_by_sid(self, unit_sid: str):
        if not unit_sid:
            raise QueryError("unit_sid cannot be empty")
        try:
            return self._data.units.get(unit_sid)
        except KeyError as exc:
            raise UnknownUnitError(f"Unknown unit SID: {unit_sid!r}") from exc

    def _get_unit(self, faction: str, unit_sid: str):
        self._get_city(faction)
        definition = self._get_unit_by_sid(unit_sid)
        if definition.faction != faction:
            raise UnknownUnitError(
                f"Unknown unit for faction: faction={faction!r}, unit_sid={unit_sid!r}"
            )
        return definition

    def _build_graph(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario: PlanningScenario | None = None,
    ) -> tuple[FactionCity, DependencyGraph]:
        city = self._get_city(faction)
        building = self.get_building(faction, sid, level)
        starting_buildings = (
            None
            if scenario is None
            else resolve_effective_starting_buildings(city, scenario)
        )
        return city, build_dependency_graph(
            city,
            building.key,
            starting_buildings=starting_buildings,
        )

    @staticmethod
    def _effective_starting_buildings(
        city: FactionCity,
        scenario: PlanningScenario | None,
    ) -> frozenset[BuildingKey]:
        if scenario is not None:
            return resolve_effective_starting_buildings(city, scenario)
        return frozenset(
            key
            for key, building in city.buildings.items()
            if building.constructed_on_start
        )

    @staticmethod
    def _make_key(faction: str, sid: str, level: int) -> BuildingKey:
        if not sid:
            raise QueryError("sid cannot be empty")
        if level < 1:
            raise QueryError("level must be at least 1")
        return BuildingKey(faction=faction, sid=sid, level=level)
