from __future__ import annotations

from olden_db.desktop.planner_diagnostics import (
    DiagnosticSeverity,
    adapt_planner_diagnostic,
)
from olden_db.models import BuildingKey, ResourceCost
from olden_db.planner import BuildPlan, GameDate, PlannerResult, PlanningFailure
from olden_db.planner_diagnostics import (
    PlannerDiagnostic,
    PlannerDiagnosticCategory,
)


def main() -> None:
    key = BuildingKey(faction="Test", sid="TownHall", level=1)
    diagnostic = PlannerDiagnostic(
        diagnostic_code="PLANNER_INVALID_BUILD_ORDER",
        category=PlannerDiagnosticCategory.INVALID_BUILD_ORDER,
        canonical_explanation="The supplied order violates prerequisites.",
        affected_entities=(key,),
        metadata=(("target", "Test/TownHall/1"),),
    )

    assert diagnostic.affected_entities == (key,)
    assert diagnostic.metadata == (("target", "Test/TownHall/1"),)

    presentation = adapt_planner_diagnostic(diagnostic)
    assert presentation.title == "Invalid build order"
    assert presentation.explanation == diagnostic.canonical_explanation
    assert presentation.severity is DiagnosticSeverity.ERROR

    plan = BuildPlan(
        faction="Test",
        target=key,
        order_number=1,
        steps=(),
        total_cost=ResourceCost(),
        starting_date=GameDate(1, 1, 1),
    )
    result = PlannerResult(plan=plan, diagnostics=(diagnostic,))
    assert result.plan is plan
    assert result.diagnostics == (diagnostic,)

    failure = PlanningFailure("failed", diagnostics=(diagnostic,))
    assert str(failure) == "failed"
    assert failure.diagnostics == (diagnostic,)

    try:
        PlanningFailure("missing diagnostics", diagnostics=())
    except ValueError:
        pass
    else:
        raise AssertionError("PlanningFailure accepted an empty diagnostic tuple")

    print("Planner diagnostic interface tests passed.")


if __name__ == "__main__":
    main()
