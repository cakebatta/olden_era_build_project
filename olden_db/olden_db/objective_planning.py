from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Iterator, Mapping, TypeAlias

from .graph import (
    DependencyGraph,
    DependencyCycleError,
    MissingBuildingError,
    iter_topological_orders,
)
from .income_timeline import DailyIncome, IncomeTimeline, calculate_income_timeline
from .models import BuildingKey, FactionCity
from .planner import (
    BuildPlan,
    DailyConstructionCost,
    GameDate,
    PlannerResult,
    PlanningFailure,
    plan_build_order_result,
)
from .planner_diagnostics import PlannerDiagnostic
from .scenario import PlanningScenario


@dataclass(frozen=True, slots=True, order=True)
class BuildingCompletionObjective:
    """Require one canonical building level to be complete."""

    building: BuildingKey

    def __post_init__(self) -> None:
        if not isinstance(self.building, BuildingKey):
            raise TypeError("building must be a BuildingKey")


Objective: TypeAlias = BuildingCompletionObjective


class ObjectivePlanningRequestError(ValueError):
    """Base exception for structurally invalid objective-planning requests."""

    def __init__(
        self,
        message: str,
        *,
        objectives: tuple[object, ...] = (),
        affected_entities: tuple[BuildingKey, ...] = (),
    ) -> None:
        super().__init__(message)
        self.objectives = tuple(objectives)
        self.affected_entities = tuple(affected_entities)


class EmptyObjectiveSetError(ObjectivePlanningRequestError):
    pass


class UnsupportedObjectiveTypeError(ObjectivePlanningRequestError):
    pass


class UnknownObjectiveTargetError(ObjectivePlanningRequestError):
    pass


class CrossTownObjectiveError(ObjectivePlanningRequestError):
    pass


class IncompatibleObjectivesError(ObjectivePlanningRequestError):
    pass


class InvalidTownStateError(ObjectivePlanningRequestError):
    pass


class InvalidStartingDateError(ObjectivePlanningRequestError):
    pass


class IncompatiblePlanningScenarioError(ObjectivePlanningRequestError):
    pass


def objective_sort_key(objective: Objective) -> tuple[object, ...]:
    """Return the stable canonical ordering key for a supported Objective."""

    if isinstance(objective, BuildingCompletionObjective):
        building = objective.building
        return ("building_completion", building.faction, building.sid, building.level)
    raise UnsupportedObjectiveTypeError(
        "Unsupported Objective variant",
        objectives=(objective,),
    )


@dataclass(frozen=True, slots=True)
class ObjectiveSet:
    """Normalized immutable membership of explicit planning objectives."""

    objectives: tuple[Objective, ...]

    def __post_init__(self) -> None:
        normalized = tuple(self.objectives)
        unsupported = tuple(
            item
            for item in normalized
            if not isinstance(item, BuildingCompletionObjective)
        )
        if unsupported:
            raise UnsupportedObjectiveTypeError(
                "ObjectiveSet contains an unsupported Objective variant",
                objectives=unsupported,
            )
        object.__setattr__(
            self,
            "objectives",
            tuple(sorted(set(normalized), key=objective_sort_key)),
        )

    @classmethod
    def from_iterable(cls, objectives: Iterable[Objective]) -> "ObjectiveSet":
        return cls(tuple(objectives))

    def __iter__(self) -> Iterator[Objective]:
        return iter(self.objectives)

    def __len__(self) -> int:
        return len(self.objectives)

    def __contains__(self, objective: object) -> bool:
        return objective in self.objectives


@dataclass(frozen=True, slots=True)
class TownState:
    """Immutable deterministic context for one town-planning request."""

    faction: str
    starting_date: GameDate = GameDate(1, 1, 1)
    planning_scenario: PlanningScenario = PlanningScenario()

    def __post_init__(self) -> None:
        if not isinstance(self.faction, str) or not self.faction.strip():
            raise InvalidTownStateError("town faction must be a non-blank string")
        if not isinstance(self.starting_date, GameDate):
            raise InvalidStartingDateError("starting_date must be a GameDate")
        if not isinstance(self.planning_scenario, PlanningScenario):
            raise IncompatiblePlanningScenarioError(
                "planning_scenario must be a PlanningScenario"
            )


@dataclass(frozen=True, slots=True)
class TownPlanningRequest:
    """Canonical immutable input to single-town objective planning."""

    town_state: TownState
    objective_set: ObjectiveSet

    def __post_init__(self) -> None:
        if not isinstance(self.town_state, TownState):
            raise InvalidTownStateError("town_state must be a TownState")
        if not isinstance(self.objective_set, ObjectiveSet):
            raise ObjectivePlanningRequestError(
                "objective_set must be an ObjectiveSet"
            )


class ObjectivePlanningFailureKind(str, Enum):
    UNSATISFIED_PREREQUISITES = "unsatisfied_prerequisites"
    NO_LEGAL_INTEGRATED_ORDER = "no_legal_integrated_order"
    RESOURCE_INFEASIBILITY = "resource_infeasibility"
    OBJECTIVE_NOT_COMPLETABLE = "objective_not_completable"


@dataclass(frozen=True, slots=True)
class ObjectivePlanningFailure:
    """Immutable typed infeasibility outcome for a valid request."""

    kind: ObjectivePlanningFailureKind
    affected_objectives: tuple[Objective, ...]
    affected_entities: tuple[BuildingKey, ...] = ()
    diagnostics: tuple[PlannerDiagnostic, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ObjectivePlanningFailureKind):
            raise TypeError("kind must be an ObjectivePlanningFailureKind")
        objectives = tuple(self.affected_objectives)
        entities = tuple(self.affected_entities)
        diagnostics = tuple(self.diagnostics)
        if any(not isinstance(item, BuildingCompletionObjective) for item in objectives):
            raise TypeError("affected_objectives must contain supported Objective values")
        if any(not isinstance(item, BuildingKey) for item in entities):
            raise TypeError("affected_entities must contain BuildingKey values")
        if any(not isinstance(item, PlannerDiagnostic) for item in diagnostics):
            raise TypeError("diagnostics must contain PlannerDiagnostic values")
        object.__setattr__(
            self,
            "affected_objectives",
            tuple(sorted(set(objectives), key=objective_sort_key)),
        )
        object.__setattr__(self, "affected_entities", tuple(sorted(set(entities))))
        object.__setattr__(self, "diagnostics", diagnostics)


@dataclass(frozen=True, slots=True)
class UnsatisfiedPrerequisites(ObjectivePlanningFailure):
    kind: ObjectivePlanningFailureKind = field(
        default=ObjectivePlanningFailureKind.UNSATISFIED_PREREQUISITES,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class NoLegalIntegratedOrder(ObjectivePlanningFailure):
    kind: ObjectivePlanningFailureKind = field(
        default=ObjectivePlanningFailureKind.NO_LEGAL_INTEGRATED_ORDER,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class ResourceInfeasibility(ObjectivePlanningFailure):
    kind: ObjectivePlanningFailureKind = field(
        default=ObjectivePlanningFailureKind.RESOURCE_INFEASIBILITY,
        init=False,
    )


@dataclass(frozen=True, slots=True)
class ObjectiveNotCompletable(ObjectivePlanningFailure):
    kind: ObjectivePlanningFailureKind = field(
        default=ObjectivePlanningFailureKind.OBJECTIVE_NOT_COMPLETABLE,
        init=False,
    )


class ObjectiveSetCompletionState(str, Enum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class ObjectiveCompletion:
    objective: Objective
    completed: bool
    completion_date: GameDate | None
    satisfied_at_start: bool
    completing_action: BuildingKey | None


@dataclass(frozen=True, slots=True)
class ObjectiveDependencySummary:
    objective: Objective
    required_buildings: tuple[BuildingKey, ...]
    constructed_buildings: tuple[BuildingKey, ...]
    satisfied_at_start: tuple[BuildingKey, ...]


@dataclass(frozen=True, slots=True)
class BuildStepObjectiveProvenance:
    building: BuildingKey
    required_by: tuple[Objective, ...]
    objective_targets: tuple[Objective, ...]


@dataclass(frozen=True, slots=True)
class MultiObjectivePlannerResult:
    request: TownPlanningRequest
    plan: BuildPlan
    objective_completions: tuple[ObjectiveCompletion, ...]
    objective_dependencies: tuple[ObjectiveDependencySummary, ...]
    step_provenance: tuple[BuildStepObjectiveProvenance, ...]
    daily_construction_schedule: tuple[DailyConstructionCost, ...]
    resource_timeline: tuple[DailyIncome, ...]
    diagnostics: tuple[PlannerDiagnostic, ...]
    completion_state: ObjectiveSetCompletionState


def build_integrated_dependency_graph(
    city: FactionCity,
    targets: Iterable[BuildingKey],
    *,
    starting_buildings: frozenset[BuildingKey] | None = None,
) -> tuple[DependencyGraph, Mapping[BuildingKey, frozenset[BuildingKey]]]:
    normalized_targets = tuple(sorted(set(targets)))
    if not normalized_targets:
        raise ValueError("at least one target is required")

    effective_starting = (
        frozenset(
            key
            for key, building in city.buildings.items()
            if building.constructed_on_start
        )
        if starting_buildings is None
        else frozenset(starting_buildings)
    )

    union_nodes: set[BuildingKey] = set()
    union_starting: set[BuildingKey] = set()
    closure_by_target: dict[BuildingKey, frozenset[BuildingKey]] = {}

    def closure(target: BuildingKey) -> frozenset[BuildingKey]:
        local: set[BuildingKey] = set()
        visiting: list[BuildingKey] = []
        seen: set[BuildingKey] = set()

        def visit(node: BuildingKey) -> None:
            if node in seen:
                return
            if node not in city.buildings:
                parent = visiting[-1] if visiting else target
                raise MissingBuildingError(
                    f"Missing prerequisite node {node} referenced by {parent}"
                )
            if node in visiting:
                cycle_start = visiting.index(node)
                cycle = visiting[cycle_start:] + [node]
                cycle_text = " -> ".join(
                    f"{item.sid} L{item.level}" for item in cycle
                )
                raise DependencyCycleError(
                    f"Dependency cycle detected: {cycle_text}"
                )
            if node in effective_starting:
                union_starting.add(node)
                local.add(node)
                seen.add(node)
                return
            visiting.append(node)
            for prerequisite in city.buildings[node].prerequisites:
                visit(prerequisite)
            visiting.pop()
            union_nodes.add(node)
            local.add(node)
            seen.add(node)

        visit(target)
        return frozenset(local)

    for target in normalized_targets:
        if target.faction != city.faction:
            raise ValueError("all targets must match the city faction")
        closure_by_target[target] = closure(target)

    prerequisites = {
        node: frozenset(
            prerequisite
            for prerequisite in city.buildings[node].prerequisites
            if prerequisite in union_nodes
        )
        for node in union_nodes
    }
    dependents_mutable = {node: set() for node in union_nodes}
    for node, required in prerequisites.items():
        for prerequisite in required:
            dependents_mutable[prerequisite].add(node)

    graph = DependencyGraph(
        faction=city.faction,
        target=normalized_targets[-1],
        nodes=frozenset(union_nodes),
        prerequisites=prerequisites,
        dependents={
            node: frozenset(children)
            for node, children in dependents_mutable.items()
        },
        satisfied_starting_nodes=frozenset(union_starting),
    )
    return graph, MappingProxyType(closure_by_target)


def plan_objective_request(
    city: FactionCity,
    request: TownPlanningRequest,
    *,
    starting_buildings: frozenset[BuildingKey],
) -> MultiObjectivePlannerResult | ObjectivePlanningFailure:
    objectives = request.objective_set.objectives
    targets = tuple(objective.building for objective in objectives)
    try:
        graph, closure_by_target = build_integrated_dependency_graph(
            city,
            targets,
            starting_buildings=starting_buildings,
        )
        order = next(iter_topological_orders(graph))
        planner_result = plan_build_order_result(
            city,
            graph,
            order,
            starting_date=request.town_state.starting_date,
        )
    except (MissingBuildingError, DependencyCycleError):
        return UnsatisfiedPrerequisites(
            affected_objectives=objectives,
            affected_entities=targets,
        )
    except StopIteration:
        return NoLegalIntegratedOrder(
            affected_objectives=objectives,
            affected_entities=targets,
        )
    except PlanningFailure as exc:
        return ObjectiveNotCompletable(
            affected_objectives=objectives,
            affected_entities=targets,
            diagnostics=exc.diagnostics,
        )

    plan = planner_result.plan
    step_dates = {step.building: step.date for step in plan.steps}
    objective_dependencies = []
    objective_completions = []
    for objective in objectives:
        closure = closure_by_target[objective.building]
        constructed = tuple(sorted(key for key in closure if key in graph.nodes))
        satisfied = tuple(
            sorted(key for key in closure if key in graph.satisfied_starting_nodes)
        )
        objective_dependencies.append(
            ObjectiveDependencySummary(
                objective,
                tuple(sorted(closure)),
                constructed,
                satisfied,
            )
        )
        target_at_start = objective.building in starting_buildings
        objective_completions.append(
            ObjectiveCompletion(
                objective,
                True,
                request.town_state.starting_date
                if target_at_start
                else step_dates[objective.building],
                target_at_start,
                None if target_at_start else objective.building,
            )
        )

    step_provenance = tuple(
        BuildStepObjectiveProvenance(
            step.building,
            tuple(
                objective
                for objective in objectives
                if step.building in closure_by_target[objective.building]
            ),
            tuple(
                objective
                for objective in objectives
                if objective.building == step.building
            ),
        )
        for step in plan.steps
    )

    income_timeline: IncomeTimeline = calculate_income_timeline(
        city,
        plan,
        through_date=plan.completion_date,
        starting_buildings=starting_buildings,
    )

    return MultiObjectivePlannerResult(
        request,
        plan,
        tuple(objective_completions),
        tuple(objective_dependencies),
        step_provenance,
        planner_result.daily_construction_schedule,
        income_timeline.daily_income,
        planner_result.diagnostics,
        ObjectiveSetCompletionState.COMPLETE,
    )
