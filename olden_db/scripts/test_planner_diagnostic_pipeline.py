from __future__ import annotations

from dataclasses import replace

import olden_db.query as query_module
from olden_db.desktop.planner_diagnostics import (
    DiagnosticSeverity,
    PlannerDiagnosticPresentation,
    adapt_planner_diagnostics,
)
from olden_db.desktop.presenters.planner_presenter import PlannerPresenter
from olden_db.desktop.state import PlannerState
from olden_db.graph import DependencyGraph, build_dependency_graph
from olden_db.models import (
    BuildingKey,
    BuildingLevel,
    FactionCity,
    ResourceCost,
)
from olden_db.planner import (
    BuildPlan,
    BuildStep,
    GameDate,
    InvalidBuildOrderError,
    PlannerResult,
    PlanningFailure,
    plan_build_order_result,
    validate_plan_set,
)
from olden_db.planning_execution import PlanningExecutionCoordinator
from olden_db.planning_workspace import PlanningWorkspace
from olden_db.planner_diagnostics import (
    PlannerDiagnostic,
    PlannerDiagnosticCategory,
)
from olden_db.query import PlanningQueryService


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def make_building(
    key: BuildingKey,
    *,
    prerequisites: tuple[BuildingKey, ...] = (),
    cost: ResourceCost = ResourceCost(),
) -> BuildingLevel:
    return BuildingLevel(
        key=key,
        category="test",
        name_key=None,
        scene_slot=None,
        cost=cost,
        prerequisites=prerequisites,
    )


def make_city() -> tuple[
    FactionCity,
    BuildingKey,
    BuildingKey,
    BuildingLevel,
    BuildingLevel,
]:
    base_key = BuildingKey("Test", "Base", 1)
    target_key = BuildingKey("Test", "Target", 1)
    base = make_building(base_key, cost=ResourceCost(gold=100))
    target = make_building(
        target_key,
        prerequisites=(base_key,),
        cost=ResourceCost(gold=200),
    )
    city = FactionCity("Test", "test-city")
    city.add_building(base)
    city.add_building(target)
    return city, base_key, target_key, base, target


def expect_planning_failure(
    action,
    *,
    exception_type: type[PlanningFailure] = PlanningFailure,
    code: str,
    category: PlannerDiagnosticCategory,
) -> PlannerDiagnostic:
    try:
        action()
    except exception_type as exc:
        require(len(exc.diagnostics) == 1, f"{code} must emit exactly one diagnostic")
        diagnostic = exc.diagnostics[0]
        require(diagnostic.diagnostic_code == code, f"Unexpected code: {diagnostic}")
        require(diagnostic.category is category, f"Unexpected category for {code}")
        require(bool(diagnostic.canonical_explanation.strip()), f"{code} explanation is blank")
        require(isinstance(diagnostic.affected_entities, tuple), f"{code} entities are not a tuple")
        require(isinstance(diagnostic.metadata, tuple), f"{code} metadata is not a tuple")
        return diagnostic
    except PlanningFailure as exc:
        raise AssertionError(
            f"Expected {exception_type.__name__}, received {type(exc).__name__}"
        ) from exc
    raise AssertionError(f"Expected {exception_type.__name__} for {code}")


def make_graph(
    *,
    faction: str,
    target: BuildingKey,
    nodes: frozenset[BuildingKey],
    prerequisites: dict[BuildingKey, frozenset[BuildingKey]],
) -> DependencyGraph:
    dependents_mutable = {node: set() for node in nodes}
    for node, required in prerequisites.items():
        for prerequisite in required:
            dependents_mutable[prerequisite].add(node)
    return DependencyGraph(
        faction=faction,
        target=target,
        nodes=nodes,
        prerequisites=prerequisites,
        dependents={
            node: frozenset(dependents)
            for node, dependents in dependents_mutable.items()
        },
        satisfied_starting_nodes=frozenset(),
    )


def test_planner_generated_build_order_diagnostics() -> None:
    city, base_key, target_key, _, _ = make_city()
    graph = build_dependency_graph(city, target_key)

    other_target = BuildingKey("Other", "Target", 1)
    other_graph = make_graph(
        faction="Other",
        target=other_target,
        nodes=frozenset((other_target,)),
        prerequisites={other_target: frozenset()},
    )
    faction_diagnostic = expect_planning_failure(
        lambda: plan_build_order_result(city, other_graph, (other_target,)),
        code="PLANNER_FACTION_MISMATCH",
        category=PlannerDiagnosticCategory.INVALID_REQUEST,
    )
    require(
        faction_diagnostic.metadata
        == (("city_faction", "Test"), ("graph_faction", "Other")),
        "Faction mismatch metadata changed",
    )

    invalid_order_diagnostic = expect_planning_failure(
        lambda: plan_build_order_result(city, graph, (target_key, base_key)),
        exception_type=InvalidBuildOrderError,
        code="PLANNER_INVALID_BUILD_ORDER",
        category=PlannerDiagnosticCategory.INVALID_BUILD_ORDER,
    )
    require(
        invalid_order_diagnostic.affected_entities
        == (target_key, target_key, base_key),
        "Invalid-order affected entities changed",
    )
    require(
        invalid_order_diagnostic.metadata == (("target", str(target_key)),),
        "Invalid-order metadata changed",
    )

    missing_key = BuildingKey("Test", "Missing", 1)
    missing_graph = make_graph(
        faction="Test",
        target=target_key,
        nodes=frozenset((missing_key, target_key)),
        prerequisites={
            missing_key: frozenset(),
            target_key: frozenset((missing_key,)),
        },
    )
    missing_diagnostic = expect_planning_failure(
        lambda: plan_build_order_result(
            city,
            missing_graph,
            (missing_key, target_key),
        ),
        code="PLANNER_GRAPH_NODE_MISSING_FROM_CITY",
        category=PlannerDiagnosticCategory.DATA_INTEGRITY,
    )
    require(
        missing_diagnostic.affected_entities == (missing_key,),
        "Missing-node affected entities changed",
    )
    require(
        missing_diagnostic.metadata == (("graph_target", str(target_key)),),
        "Missing-node metadata changed",
    )


def make_plan(
    *,
    faction: str = "Test",
    target: BuildingKey | None = None,
    starting_date: GameDate = GameDate(1, 1, 1),
    steps: tuple[BuildStep, ...] = (),
    total_cost: ResourceCost = ResourceCost(),
) -> BuildPlan:
    target = target or BuildingKey(faction, "Target", 1)
    return BuildPlan(
        faction=faction,
        target=target,
        order_number=1,
        steps=steps,
        total_cost=total_cost,
        starting_date=starting_date,
    )


def one_step(
    key: BuildingKey,
    *,
    date: GameDate = GameDate(1, 1, 1),
    cost: ResourceCost = ResourceCost(gold=100),
) -> tuple[BuildStep, ...]:
    return (
        BuildStep(
            step_number=1,
            date=date,
            building=key,
            individual_cost=cost,
            cumulative_cost=cost,
        ),
    )


def test_planner_generated_plan_set_diagnostics() -> None:
    target = BuildingKey("Test", "Target", 1)
    base = make_plan(target=target)

    expect_planning_failure(
        lambda: validate_plan_set(()),
        code="PLANNER_EMPTY_PLAN_SET",
        category=PlannerDiagnosticCategory.CONSISTENCY,
    )

    other_target = BuildingKey("Other", "Target", 1)
    cases = (
        (
            "PLANNER_PLAN_SET_MULTIPLE_FACTIONS",
            make_plan(faction="Other", target=other_target),
        ),
        (
            "PLANNER_PLAN_SET_MULTIPLE_TARGETS",
            make_plan(target=BuildingKey("Test", "OtherTarget", 1)),
        ),
        (
            "PLANNER_PLAN_SET_MULTIPLE_STARTING_DATES",
            make_plan(target=target, starting_date=GameDate(1, 1, 2)),
        ),
        (
            "PLANNER_PLAN_SET_INCONSISTENT_ACTION_COUNTS",
            make_plan(target=target, steps=one_step(target)),
        ),
        (
            "PLANNER_PLAN_SET_INCONSISTENT_TOTAL_COSTS",
            make_plan(target=target, total_cost=ResourceCost(gold=1)),
        ),
        (
            "PLANNER_PLAN_SET_INCONSISTENT_COMPLETION_DATES",
            make_plan(
                target=target,
                steps=one_step(target, date=GameDate(1, 1, 2)),
                total_cost=ResourceCost(gold=100),
            ),
        ),
        (
            "PLANNER_PLAN_SET_DUPLICATE_ORDER",
            base,
        ),
    )

    completion_baseline = make_plan(
        target=target,
        steps=one_step(target, date=GameDate(1, 1, 1)),
        total_cost=ResourceCost(gold=100),
    )

    for code, candidate in cases:
        first = completion_baseline if code == "PLANNER_PLAN_SET_INCONSISTENT_COMPLETION_DATES" else base
        diagnostic = expect_planning_failure(
            lambda first=first, candidate=candidate: validate_plan_set(
                (first, candidate)
            ),
            code=code,
            category=PlannerDiagnosticCategory.CONSISTENCY,
        )
        require(
            diagnostic.affected_entities == (candidate.target,),
            f"{code} affected entities changed",
        )


def sample_diagnostic(
    code: str = "PLANNER_INVALID_BUILD_ORDER",
    *,
    explanation: str = "The supplied order violates prerequisites.",
) -> PlannerDiagnostic:
    return PlannerDiagnostic(
        diagnostic_code=code,
        category=PlannerDiagnosticCategory.INVALID_BUILD_ORDER,
        canonical_explanation=explanation,
        affected_entities=(BuildingKey("Test", "Target", 1),),
        metadata=(("target", "Test/Target/1"),),
    )


def sample_plan() -> BuildPlan:
    return make_plan(target=BuildingKey("Test", "Target", 1))


def test_planner_result_and_failure_transport() -> None:
    first = sample_diagnostic()
    second = sample_diagnostic(
        "PLANNER_SECOND_TEST_DIAGNOSTIC",
        explanation="A second diagnostic preserves ordering.",
    )
    diagnostics = (first, second)

    result = PlannerResult(sample_plan(), diagnostics)
    require(result.diagnostics is diagnostics, "PlannerResult replaced the diagnostic tuple")
    require(result.diagnostics == diagnostics, "PlannerResult changed diagnostic values")

    failure = PlanningFailure("planning failed", diagnostics=diagnostics)
    require(failure.diagnostics is diagnostics, "PlanningFailure replaced the diagnostic tuple")
    require(failure.diagnostics == diagnostics, "PlanningFailure changed diagnostic values")


def query_target(
    service: PlanningQueryService,
) -> tuple[str, str, int]:
    faction = service.list_factions()[0]
    sid = service.list_buildings(faction)[0]
    level = service.list_building_levels(faction, sid)[0]
    return faction, sid, level


def test_query_layer_propagates_result_and_failure() -> None:
    service = PlanningQueryService.from_default_game_data()
    faction, sid, level = query_target(service)
    result = PlannerResult(sample_plan(), (sample_diagnostic(),))

    original = query_module.plan_build_order_result
    try:
        query_module.plan_build_order_result = lambda *args, **kwargs: result
        returned = service.generate_planner_result(faction, sid, level)
        require(returned is result, "Query Layer replaced PlannerResult")
        require(
            returned.diagnostics is result.diagnostics,
            "Query Layer replaced successful diagnostics",
        )

        failure = PlanningFailure(
            "delegated failure",
            diagnostics=(sample_diagnostic(),),
        )

        def raise_failure(*args, **kwargs):
            raise failure

        query_module.plan_build_order_result = raise_failure
        try:
            service.generate_planner_result(faction, sid, level)
        except PlanningFailure as caught:
            require(caught is failure, "Query Layer replaced PlanningFailure")
            require(
                caught.diagnostics is failure.diagnostics,
                "Query Layer replaced failure diagnostics",
            )
        else:
            raise AssertionError("Query Layer swallowed PlanningFailure")
    finally:
        query_module.plan_build_order_result = original


class RecordingView:
    def __init__(self) -> None:
        self.clear_count = 0
        self.targets: list[BuildingLevel] = []
        self.prerequisite_batches: list[tuple[object, ...]] = []
        self.plans: list[tuple[BuildPlan, ResourceCost]] = []
        self.errors: list[str] = []
        self.diagnostic_batches: list[
            tuple[PlannerDiagnosticPresentation, ...]
        ] = []
        self.workspace_presentations: list[object] = []

    def clear_results(self) -> None:
        self.clear_count += 1

    def show_target(self, building: BuildingLevel) -> None:
        self.targets.append(building)

    def show_prerequisites(self, statuses: tuple[object, ...]) -> None:
        self.prerequisite_batches.append(statuses)

    def show_plan(
        self,
        plan: BuildPlan,
        cumulative_cost: ResourceCost,
    ) -> None:
        self.plans.append((plan, cumulative_cost))

    def show_error(self, message: str) -> None:
        self.errors.append(message)

    def set_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self.diagnostic_batches.append(tuple(diagnostics))

    def render_workspace(self, presentation) -> None:
        self.workspace_presentations.append(presentation)
        self.diagnostic_batches.append(tuple(presentation.diagnostics))
        if presentation.failure_message:
            self.errors.append(presentation.failure_message)


class RecordingService:
    def __init__(
        self,
        building: BuildingLevel,
        result_or_failure: PlannerResult | PlanningFailure,
    ) -> None:
        self.building = building
        self.result_or_failure = result_or_failure
        self.generate_calls = 0

    def get_building(self, faction: str, sid: str, level: int) -> BuildingLevel:
        return self.building

    def get_prerequisite_statuses(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario,
    ) -> tuple[object, ...]:
        return ()

    def generate_planner_result(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date=GameDate(1, 1, 1),
        scenario,
    ) -> PlannerResult:
        self.generate_calls += 1
        if isinstance(self.result_or_failure, PlanningFailure):
            raise self.result_or_failure
        return self.result_or_failure

    def enumerate_build_orders(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        scenario,
    ) -> tuple[tuple[BuildingKey, ...], ...]:
        return (self.result_or_failure.plan.order,)  # type: ignore[union-attr]


def ready_state() -> PlannerState:
    return PlannerState(
        selected_faction="Test",
        selected_building_sid="Target",
        selected_level=1,
    )


def test_presenter_orchestrates_success_diagnostics_to_recording_view() -> None:
    _, _, _, _, target = make_city()
    diagnostics = (
        sample_diagnostic(),
        sample_diagnostic(
            "PLANNER_SECOND_TEST_DIAGNOSTIC",
            explanation="Second explanation.",
        ),
    )
    result = PlannerResult(sample_plan(), diagnostics)
    service = RecordingService(target, result)
    view = RecordingView()
    statuses: list[str] = []
    state = ready_state()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    presenter = PlannerPresenter(
        service,
        workspace,
        coordinator,
        state,
        view,
        statuses.append,
    )

    presenter.on_generate_plan()

    require(service.generate_calls == 1, "Presenter did not use planner-result query")
    require(state.current_plan is result.plan, "Presenter did not store canonical plan")
    require(len(view.workspace_presentations) == 2, "Pending and ready states were not rendered")
    require(
        view.workspace_presentations[-1].accepted_plan is result.plan,
        "Accepted plan was not rendered through workspace presentation",
    )
    require(not view.errors, "Successful planning displayed an error")
    require(len(view.diagnostic_batches) == 2, "Workspace diagnostics were not delivered")
    expected = adapt_planner_diagnostics(diagnostics)
    require(view.diagnostic_batches[-1] == expected, "Success adapter output changed")
    require(
        tuple(item.explanation for item in view.diagnostic_batches[-1])
        == tuple(item.canonical_explanation for item in diagnostics),
        "Presenter or adapter rewrote canonical explanations",
    )


def test_presenter_orchestrates_failure_diagnostics_to_recording_view() -> None:
    _, _, _, _, target = make_city()
    diagnostics = (
        sample_diagnostic(),
        sample_diagnostic(
            "PLANNER_SECOND_TEST_DIAGNOSTIC",
            explanation="Second explanation.",
        ),
    )
    failure = PlanningFailure("cannot plan", diagnostics=diagnostics)
    service = RecordingService(target, failure)
    view = RecordingView()
    statuses: list[str] = []
    state = ready_state()
    state.current_plan = sample_plan()
    workspace = PlanningWorkspace.create()
    coordinator = PlanningExecutionCoordinator(service)
    presenter = PlannerPresenter(
        service,
        workspace,
        coordinator,
        state,
        view,
        statuses.append,
    )

    presenter.on_generate_plan()

    require(state.current_plan is None, "Failure did not clear stale planner state")
    require(len(view.workspace_presentations) == 2, "Pending and failed states were not rendered")
    require(len(view.errors) == 1, "Failure did not use the workspace error contract")
    require("cannot plan" in view.errors[0], "Failure message was not preserved")
    require(len(view.diagnostic_batches) == 2, "Failure diagnostics were not delivered")
    require(
        view.diagnostic_batches[-1] == adapt_planner_diagnostics(diagnostics),
        "Failure adapter output changed",
    )
    require(
        tuple(item.explanation for item in view.diagnostic_batches[-1])
        == tuple(item.canonical_explanation for item in diagnostics),
        "Failure path rewrote canonical explanations",
    )


def test_adapter_translation_preserves_order_and_meaning() -> None:
    diagnostics = (
        sample_diagnostic(
            "PLANNER_FIRST",
            explanation="First canonical explanation.",
        ),
        sample_diagnostic(
            "PLANNER_SECOND",
            explanation="Second canonical explanation.",
        ),
    )
    presentations = adapt_planner_diagnostics(diagnostics)

    require(
        tuple(item.explanation for item in presentations)
        == ("First canonical explanation.", "Second canonical explanation."),
        "Adapter changed explanation text or ordering",
    )
    require(
        all(item.severity is DiagnosticSeverity.ERROR for item in presentations),
        "Adapter category-to-severity mapping changed",
    )
    require(
        tuple(item.title for item in presentations)
        == ("Planner First", "Planner Second"),
        "Adapter fallback title translation changed",
    )


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} executable planner diagnostic integration checks")


if __name__ == "__main__":
    main()
