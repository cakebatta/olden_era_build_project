from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "f10e2a445de44512d29aaa10b74575218b0e151f"
QUERY = ROOT / "olden_db" / "olden_db" / "query.py"
MODELS = ROOT / "olden_db" / "olden_db" / "objective_query_models.py"
TEST = ROOT / "olden_db" / "scripts" / "test_multi_objective_query_layer.py"


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
            "Repository HEAD does not match the synchronized BE-016 baseline.\n"
            f"Expected: {EXPECTED_HEAD}\nActual:   {actual}"
        )

    for path in (QUERY, MODELS, TEST):
        if not path.is_file():
            raise FileNotFoundError(path)

    text = QUERY.read_text(encoding="utf-8")

    import_anchor = "from .objective_planning import (\n"
    import_replacement = """from .objective_query_models import (
    BuildStepExplanation,
    MultiObjectivePlanningResultView,
    ObjectiveCompletionView,
    ObjectivePlanningSummary,
    ObjectiveSummary,
    PrerequisiteProvenance,
)
from .objective_planning import (
"""
    text = replace_once(
        text,
        import_anchor,
        import_replacement,
        "query model imports",
    )

    method_anchor = """        return plan_objective_request(
            city,
            request,
            starting_buildings=starting_buildings,
        )

    @staticmethod
    def _single_objective_request(
"""

    method_replacement = """        return plan_objective_request(
            city,
            request,
            starting_buildings=starting_buildings,
        )

    def generate_objective_plan_view(
        self,
        request: TownPlanningRequest,
    ) -> MultiObjectivePlanningResultView | ObjectivePlanningFailure:
        \"\"\"Return immutable display-ready multi-objective Query Layer models.\"\"\"
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
"""

    text = replace_once(
        text,
        method_anchor,
        method_replacement,
        "objective view operation",
    )

    ast.parse(text, filename=str(QUERY))
    QUERY.write_text(text, encoding="utf-8")

    for path in (MODELS, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    print("BE-016 applied successfully.")
    print("Next: cd olden_db")
    print("Then: python -m scripts.test_multi_objective_query_layer")


if __name__ == "__main__":
    main()
