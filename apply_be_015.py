from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "78de2b77f7f643b06a71d77f82a585738900781a"
QUERY = ROOT / "olden_db" / "olden_db" / "query.py"
OBJECTIVE = ROOT / "olden_db" / "olden_db" / "objective_planning.py"
TEST = ROOT / "olden_db" / "scripts" / "test_multi_objective_planning.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def main() -> None:
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if actual != EXPECTED_HEAD:
        raise RuntimeError(
            f"Expected repository HEAD {EXPECTED_HEAD}, found {actual}"
        )

    for path in (QUERY, OBJECTIVE, TEST):
        if not path.is_file():
            raise FileNotFoundError(path)

    text = QUERY.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost\n",
        """from .models import BuildingKey, BuildingLevel, FactionCity, ResourceCost
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
""",
        "imports",
    )

    old = """    def generate_build_plan(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> BuildPlan:
        city, graph = self._build_graph(faction, sid, level, scenario=scenario)
        order = next(iter_topological_orders(graph))
        return plan_build_order(city, graph, order, starting_date=starting_date)

    def generate_planner_result(
        self,
        faction: str,
        sid: str,
        level: int,
        *,
        starting_date: GameDate = GameDate(1, 1, 1),
        scenario: PlanningScenario | None = None,
    ) -> PlannerResult:
        \"\"\"Return the canonical planner result without presentation translation.\"\"\"
        city, graph = self._build_graph(faction, sid, level, scenario=scenario)
        order = next(iter_topological_orders(graph))
        return plan_build_order_result(
            city,
            graph,
            order,
            starting_date=starting_date,
        )
"""

    new = """    def generate_objective_plan(
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
"""

    text = replace_once(text, old, new, "planning methods")
    QUERY.write_text(text, encoding="utf-8")

    for path in (QUERY, OBJECTIVE, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    print("BE-015 applied successfully.")
    print("Next: cd olden_db")
    print("Then: python -m scripts.test_multi_objective_planning")


if __name__ == "__main__":
    main()
