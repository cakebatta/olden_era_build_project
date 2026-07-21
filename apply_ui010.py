from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASELINE = "b787f00b80383f8837e51cec1c57feba7e9c892c"
COLLECTION_PRESENTER = (
    ROOT / "olden_db" / "olden_db" / "desktop" / "presenters"
    / "scenario_comparison_workspace_presenter.py"
)
COLLECTION_VIEW = (
    ROOT / "olden_db" / "olden_db" / "desktop" / "views"
    / "scenario_comparison_workspace_view.py"
)
ARCHITECTURE = ROOT / "docs" / "desktop_application_architecture.md"


def require_baseline() -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASELINE, "HEAD"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip()
        raise RuntimeError(
            f"UI-010 requires BE-013 commit {BASELINE} as an ancestor; found {head}"
        )


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label} already applied")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one reviewed block, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def patch_collection_view() -> None:
    replace_once(
        COLLECTION_VIEW,
        "from .planner_view import PlannerView\n",
        "from .build_plan_comparison_view import BuildPlanComparisonView\n"
        "from .planner_view import PlannerView\n",
        "comparison view import",
    )
    replace_once(
        COLLECTION_VIEW,
        '''        self._content.bind("<Configure>", self._refresh_scroll_region)
        self._canvas.bind("<Shift-MouseWheel>", self._scroll_horizontally)
''',
        '''        self._content.bind("<Configure>", self._refresh_scroll_region)
        self._canvas.bind("<Shift-MouseWheel>", self._scroll_horizontally)

        self.comparison_view = BuildPlanComparisonView(self)
        self.comparison_view.grid(
            row=3,
            column=0,
            sticky="nsew",
            pady=(14, 0),
        )
''',
        "comparison panel composition",
    )


def patch_collection_presenter() -> None:
    replace_once(
        COLLECTION_PRESENTER,
        "from ..scenario_presenters import ScenarioAwarePlannerPresenter\n",
        "from .build_plan_comparison_presenter import (\n"
        "    BuildPlanComparisonPresenter,\n"
        "    ComparisonAwarePlannerPresenter,\n"
        ")\n",
        "comparison presenter imports",
    )
    replace_once(
        COLLECTION_PRESENTER,
        '''        self._primary_workspace_id = collection.workspace_ids[0]

        view.set_event_handlers(
''',
        '''        self._primary_workspace_id = collection.workspace_ids[0]
        self._build_plan_comparison_presenter = BuildPlanComparisonPresenter(
            service,
            collection,
            view.comparison_view,
        )

        view.set_event_handlers(
''',
        "comparison presenter construction",
    )
    replace_once(
        COLLECTION_PRESENTER,
        "            presenter = ScenarioAwarePlannerPresenter(\n",
        "            presenter = ComparisonAwarePlannerPresenter(\n",
        "comparison-aware workspace presenter",
    )
    replace_once(
        COLLECTION_PRESENTER,
        '''                planner_view,
                self._set_status,
                on_context_changed=(
''',
        '''                planner_view,
                self._set_status,
                on_comparison_changed=(
                    self._build_plan_comparison_presenter.refresh
                ),
                on_context_changed=(
''',
        "workspace comparison lifecycle callback",
    )
    replace_once(
        COLLECTION_PRESENTER,
        '''        if presentation != self._last_collection_presentation:
            self._view.render_collection(presentation)
            self._last_collection_presentation = presentation
''',
        '''        if presentation != self._last_collection_presentation:
            self._view.render_collection(presentation)
            self._last_collection_presentation = presentation
        self._build_plan_comparison_presenter.refresh()
''',
        "automatic comparison refresh",
    )


def patch_architecture() -> None:
    heading = "## Sprint 17 Build Plan Comparison Presentation (UI-010)"
    text = ARCHITECTURE.read_text(encoding="utf-8")
    if heading in text:
        print("SKIP: UI-010 architecture documentation already applied")
        return
    section = '''

## Sprint 17 Build Plan Comparison Presentation (UI-010)

The Scenario Comparison Workspace composes one read-only Build Plan Comparison
panel below the independent Planning Workspace panels. A dedicated comparison
presenter consumes immutable collection snapshots, resolves the assigned Left
and Right members, and calls only
`PlanningQueryService.compare_accepted_build_plans(...)` when both members have
current accepted results.

All signed deltas, aligned rows, relationship classifications, and
shared/exclusive collections remain authoritative BE-013 facts. The presenter
projects them into immutable UI-only models without alignment, membership,
resource, ranking, recommendation, or planner logic.

The most recent successful comparison remains visible while either role member
is pending with a retained accepted result. A new authoritative comparison
replaces it after synchronous planning acceptance. If an accepted result no
longer exists, the panel transitions to comparison unavailable.

The comparison view is passive and owns only layout, typography, row styling,
keyboard focus, and scrolling.
'''
    ARCHITECTURE.write_text(text.rstrip() + section + "\n", encoding="utf-8")
    print("UPDATED: UI-010 architecture documentation")


def validate() -> None:
    paths = (
        COLLECTION_PRESENTER,
        COLLECTION_VIEW,
        ROOT / "olden_db" / "olden_db" / "desktop"
        / "build_plan_comparison_presentation.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "presenters"
        / "build_plan_comparison_presenter.py",
        ROOT / "olden_db" / "olden_db" / "desktop" / "views"
        / "build_plan_comparison_view.py",
        ROOT / "olden_db" / "scripts" / "test_desktop_build_plan_comparison.py",
        ROOT / "olden_db" / "scripts"
        / "test_desktop_build_plan_comparison_integration.py",
    )
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"Missing UI-010 package file: {path.relative_to(ROOT)}")
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    require_baseline()
    patch_collection_view()
    patch_collection_presenter()
    patch_architecture()
    validate()
    print("UI-010 Build Plan Comparison Presentation applied successfully.")


if __name__ == "__main__":
    main()
