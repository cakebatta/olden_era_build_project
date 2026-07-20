from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

EXPECTED = "f6fd26fec4fe3ef213d4163131800fa3999e9ae9"
ROOT = Path(__file__).resolve().parent
PAYLOAD = ROOT / "payload"
PKG = ROOT / "olden_db" / "olden_db" / "desktop"
PRESENTER = PKG / "presenters" / "planner_presenter.py"
VIEW = PKG / "views" / "planner_view.py"
WORKSPACE = PKG / "workspace_presentation.py"
ARCH = ROOT / "docs" / "desktop_application_architecture.md"


def replace(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label}")
        return
    if text.count(old) != 1:
        raise RuntimeError(f"{label}: reviewed anchor not found exactly once")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def copy(relative: str) -> None:
    source = PAYLOAD / relative
    target = ROOT / relative
    if target.exists():
        if target.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
            raise RuntimeError(f"{relative} exists with different content")
        print(f"SKIP: {relative}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    print(f"CREATED: {relative}")


def main() -> None:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if head != EXPECTED:
        raise RuntimeError(f"Expected HEAD {EXPECTED}; found {head}")

    for relative in (
        "olden_db/olden_db/desktop/planning_timeline.py",
        "olden_db/scripts/test_desktop_planning_timeline.py",
        "olden_db/scripts/test_desktop_planning_timeline_integration.py",
        "docs/ui008_runtime_verification.md",
        "docs/UI-008-IMPLEMENTATION-REPORT.md",
    ):
        copy(relative)

    replace(
        WORKSPACE,
        "from .planning_summary import PlanningSummaryPresentation\n",
        "from .planning_summary import PlanningSummaryPresentation\n"
        "from .planning_timeline import BuildPlanTimelinePresentation, EMPTY_BUILD_PLAN_TIMELINE\n",
        "workspace imports",
    )
    replace(
        WORKSPACE,
        "    result_revision: int | None\n",
        "    result_revision: int | None\n"
        "    timeline: BuildPlanTimelinePresentation = EMPTY_BUILD_PLAN_TIMELINE\n",
        "workspace timeline",
    )
    replace(
        PRESENTER,
        "from ..planning_summary import (\n"
        "    DailyScheduleRowPresentation,\n"
        "    PlanningSummaryPresentation,\n"
        ")\n",
        "from ..planning_summary import (\n"
        "    DailyScheduleRowPresentation,\n"
        "    PlanningSummaryPresentation,\n"
        ")\n"
        "from ..planning_timeline import BuildPlanTimelinePresentation, TimelineStepPresentation\n",
        "presenter imports",
    )
    replace(
        PRESENTER,
        "            result_revision=base.result_revision,\n"
        "        )\n",
        "            result_revision=base.result_revision,\n"
        "            timeline=self._build_timeline(base=base, result=result),\n"
        "        )\n",
        "presenter projection",
    )
    replace(
        PRESENTER,
        "    def _load_candidates(\n",
        (PAYLOAD / "_fragments/presenter_methods.txt").read_text(encoding="utf-8")
        + "    def _load_candidates(\n",
        "presenter timeline builder",
    )
    replace(
        VIEW,
        "from ..planner_diagnostics import (\n"
        "    DiagnosticSeverity,\n"
        "    PlannerDiagnosticPresentation,\n"
        ")\n",
        "from ..planner_diagnostics import (\n"
        "    DiagnosticSeverity,\n"
        "    PlannerDiagnosticPresentation,\n"
        ")\n"
        "from ..planning_timeline import BuildPlanTimelinePresentation\n",
        "view import",
    )
    replace(
        VIEW,
        '        self._summary_failure_var = tk.StringVar(value="")\n',
        '        self._summary_failure_var = tk.StringVar(value="")\n'
        '        self._timeline_status_var = tk.StringVar(value="No accepted plan")\n'
        '        self._timeline_empty_var = tk.StringVar(value="Complete the planning selection to view the build timeline.")\n'
        '        self._timeline_detail_var = tk.StringVar(value="")\n'
        '        self._last_timeline_presentation: BuildPlanTimelinePresentation | None = None\n',
        "view state",
    )
    old_layout = '''        self._results_text = tk.Text(
            results,
            wrap="word",
            state="disabled",
            padx=12,
            pady=12,
            borderwidth=0,
            highlightthickness=0,
        )
        results_scrollbar = ttk.Scrollbar(results, orient="vertical", command=self._results_text.yview)
        self._results_text.configure(yscrollcommand=results_scrollbar.set)
        self._results_text.grid(row=1, column=0, sticky="nsew")
        results_scrollbar.grid(row=1, column=1, sticky="ns")
        self._results_text.tag_configure(
            "section", font=("TkDefaultFont", 11, "bold"), spacing1=12, spacing3=6
        )
'''
    replace(
        VIEW,
        old_layout,
        (PAYLOAD / "_fragments/view_layout.txt").read_text(encoding="utf-8"),
        "timeline layout",
    )
    old_tail = '''        self._replace_results()
        self._append_section(summary.result_status, presentation.selection_summary)
        if summary.displayed_result_target_text:
            self._append_section("Displayed Plan Target", summary.displayed_result_target_text)
        if summary.failure_message:
            self._append_section("Current Request Failed", summary.failure_message)
        self.set_diagnostics(presentation.diagnostics)
        self._results_text.see("1.0")
        if presentation.is_pending:
            self.update_idletasks()
'''
    replace(
        VIEW,
        old_tail,
        "        self._render_timeline(presentation.timeline)\n"
        "        self.set_diagnostics(presentation.diagnostics)\n"
        "        if presentation.is_pending:\n"
        "            self.update_idletasks()\n",
        "timeline render call",
    )
    replace(
        VIEW,
        "    def set_diagnostics(\n",
        (PAYLOAD / "_fragments/view_methods.txt").read_text(encoding="utf-8")
        + "    def set_diagnostics(\n",
        "timeline interactions",
    )

    doc = ARCH.read_text(encoding="utf-8")
    heading = "## Interactive Build Plan Timeline (UI-008)"
    if heading not in doc:
        ARCH.write_text(
            doc.rstrip()
            + "\n\n"
            + heading
            + "\n\n"
            + "The presenter projects accepted `BuildPlan.steps` into immutable timeline "
              "presentation values. The passive view renders a focusable chronological "
              "Treeview and independently suppresses equivalent timeline rebuilds. "
              "Retained timelines are explicitly labeled as previous.\n",
            encoding="utf-8",
        )
        print("UPDATED: architecture documentation")
    print("UI-008 applied.")


if __name__ == "__main__":
    main()
