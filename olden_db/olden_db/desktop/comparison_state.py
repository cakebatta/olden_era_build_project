from __future__ import annotations
from dataclasses import dataclass, field
from olden_db.comparison import PlanComparison
from olden_db.decision_summary import DecisionSummary
from olden_db.models import BuildingLevel
from olden_db.scenario import PlanningScenario

@dataclass(slots=True)
class ComparisonSideState:
    faction: str | None = None
    building_sid: str | None = None
    level: int | None = None
    scenario: PlanningScenario = field(default_factory=PlanningScenario)
    scenario_candidates: tuple[BuildingLevel, ...] = ()
    @property
    def complete(self) -> bool:
        return self.faction is not None and self.building_sid is not None and self.level is not None
    def select_faction(self, faction: str, candidates: tuple[BuildingLevel, ...]) -> None:
        self.faction = faction; self.building_sid = None; self.level = None
        self.scenario = PlanningScenario(); self.scenario_candidates = candidates
    def select_building(self, sid: str) -> None:
        self.building_sid = sid; self.level = None
    def select_level(self, level: int) -> None:
        self.level = level

@dataclass(slots=True)
class ComparisonState:
    left: ComparisonSideState = field(default_factory=ComparisonSideState)
    right: ComparisonSideState = field(default_factory=ComparisonSideState)
    current_comparison: PlanComparison | None = None
    current_decision_summary: DecisionSummary | None = None
    @property
    def can_compare(self) -> bool:
        return self.left.complete and self.right.complete
    def clear_result(self) -> None:
        self.current_comparison = None; self.current_decision_summary = None
