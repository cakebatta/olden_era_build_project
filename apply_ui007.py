from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRESENTER = ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
WORKSPACE_PRESENTATION = ROOT / "olden_db" / "olden_db" / "desktop" / "workspace_presentation.py"
SUMMARY_PRESENTATION = ROOT / "olden_db" / "olden_db" / "desktop" / "planning_summary.py"
FORMATTING = ROOT / "olden_db" / "olden_db" / "desktop" / "formatting.py"
ARCH_DOC = ROOT / "docs" / "desktop_application_architecture.md"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one reviewed baseline block, found {count}. "
            "Confirm main includes BE-011 and UI-006 before applying UI-007."
        )
    return text.replace(old, new, 1)


SUMMARY_SOURCE = '''from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DailyScheduleRowPresentation:
    date_text: str
    building_text: str
    cost_text: str


@dataclass(frozen=True, slots=True)
class PlanningSummaryPresentation:
    lifecycle_status: str
    result_status: str
    faction_text: str | None
    target_text: str | None
    starting_date_text: str | None
    displayed_result_target_text: str | None
    step_count_text: str | None
    completion_date_text: str | None
    total_cost_text: str | None
    daily_schedule_rows: tuple[DailyScheduleRowPresentation, ...]
    diagnostic_summary: str
    failure_message: str | None
    missing_inputs_text: str | None
    is_retained_previous_result: bool
'''

WORKSPACE_SOURCE = '''from __future__ import annotations

from dataclasses import dataclass

from olden_db.planning_workspace import PlanningExecutionStatus

from .planner_diagnostics import PlannerDiagnosticPresentation
from .planning_summary import PlanningSummaryPresentation


@dataclass(frozen=True, slots=True)
class PlanningWorkspacePresentation:
    """Immutable presentation projection for the single active workspace entry."""

    execution_status: PlanningExecutionStatus
    status_heading: str
    status_detail: str
    selection_summary: str
    summary: PlanningSummaryPresentation
    failure_message: str | None
    diagnostics: tuple[PlannerDiagnosticPresentation, ...]
    selection_revision: int
    result_revision: int | None

    @property
    def is_pending(self) -> bool:
        return self.execution_status is PlanningExecutionStatus.PENDING
'''


def patch_formatting() -> None:
    text = FORMATTING.read_text(encoding="utf-8")
    if "def format_step_count(" not in text:
        text += '''\n\ndef format_step_count(count: int) -> str:\n    noun = "construction step" if count == 1 else "construction steps"\n    return f"{count} {noun}"\n\n\ndef format_diagnostic_summary(diagnostics: tuple[object, ...]) -> str:\n    if not diagnostics:\n        return "No diagnostics requiring attention."\n    count = len(diagnostics)\n    noun = "diagnostic" if count == 1 else "diagnostics"\n    titles = tuple(str(getattr(item, "title", "Planner diagnostic")) for item in diagnostics)\n    return f"{count} {noun}: " + "; ".join(titles)\n'''
    FORMATTING.write_text(text, encoding="utf-8")


def patch_presenter() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from ..formatting import format_faction_status\n",
        '''from ..formatting import (\n    format_diagnostic_summary,\n    format_faction_status,\n    format_game_date,\n    format_resource_cost,\n    format_step_count,\n)\n''',
        "presenter formatting imports",
    )
    text = replace_once(
        text,
        "from ..state import PlannerState\n",
        '''from ..planning_summary import (\n    DailyScheduleRowPresentation,\n    PlanningSummaryPresentation,\n)\nfrom ..state import PlannerState\n''',
        "summary presentation imports",
    )
    text = replace_once(
        text,
        '''        self._set_status = set_status\n        self._on_context_changed = on_context_changed or (lambda: None)\n''',
        '''        self._set_status = set_status\n        self._on_context_changed = on_context_changed or (lambda: None)\n        self._last_workspace_presentation: (\n            PlanningWorkspacePresentation | None\n        ) = None\n        self._display_text_cache: dict[BuildingKey, str] = {}\n''',
        "presenter presentation cache",
    )
    start = text.index("    def _render_snapshot(")
    end = text.index("    def _load_candidates(", start)
    replacement = '''    def _render_snapshot(self, snapshot: PlanningWorkspaceSnapshot) -> None:\n        base = snapshot.base(DEFAULT_BASE_PLAN_ID)\n        result = base.accepted_result\n        diagnostics = self._diagnostics_for(base)\n        failure_message = (\n            base.latest_failure.message\n            if base.latest_failure is not None\n            else None\n        )\n        selection = base.selection\n        faction_text = selection.faction if selection is not None else self._state.selected_faction\n        target_text = self._display_text(selection.target) if selection is not None else None\n        starting_date_text = (\n            format_game_date(selection.starting_date)\n            if selection is not None\n            else format_game_date(self._state.starting_date)\n        )\n        missing_inputs = self._missing_input_text()\n        selection_summary = (\n            missing_inputs\n            if selection is None\n            else f"{selection.faction} / {target_text} / starts {starting_date_text}"\n        )\n        retained = base.retains_previous_result\n        summary = self._build_summary(\n            base=base,\n            result=result,\n            diagnostics=diagnostics,\n            faction_text=faction_text,\n            target_text=target_text,\n            starting_date_text=starting_date_text,\n            failure_message=failure_message,\n            missing_inputs=missing_inputs,\n        )\n        if base.execution_status is PlanningExecutionStatus.PENDING:\n            heading = "Planning in progress"\n            detail = (\n                "Evaluating the current selection."\n                if not retained\n                else "Evaluating the current selection while retaining the Previous Accepted Plan."\n            )\n        elif base.execution_status is PlanningExecutionStatus.READY:\n            heading = "Current plan ready"\n            detail = f"Revision {base.selection_revision} is accepted."\n        elif base.execution_status is PlanningExecutionStatus.FAILED:\n            heading = "Current request failed"\n            detail = (\n                "The current selection could not be planned."\n                if not retained\n                else "The current selection failed. The displayed summary is the Previous Accepted Plan."\n            )\n        else:\n            heading = "Planning selection incomplete"\n            detail = missing_inputs\n        presentation = PlanningWorkspacePresentation(\n            execution_status=base.execution_status,\n            status_heading=heading,\n            status_detail=detail,\n            selection_summary=selection_summary,\n            summary=summary,\n            failure_message=failure_message,\n            diagnostics=diagnostics,\n            selection_revision=base.selection_revision,\n            result_revision=base.result_revision,\n        )\n        if base.result_is_current and result is not None:\n            self._state.store_workspace_result(result.plan)\n        else:\n            self._state.clear_results()\n        if presentation != self._last_workspace_presentation:\n            self._view.render_workspace(presentation)\n            self._last_workspace_presentation = presentation\n        if base.execution_status is PlanningExecutionStatus.READY:\n            self._set_status(f"Planning revision {base.selection_revision} completed.")\n        elif base.execution_status is PlanningExecutionStatus.FAILED:\n            self._set_status(\n                "Current planning request failed"\n                + (f": {failure_message}" if failure_message else ".")\n            )\n\n    def _diagnostics_for(self, base):\n        result = base.accepted_result\n        if (\n            base.execution_status is PlanningExecutionStatus.FAILED\n            and base.latest_failure is not None\n        ):\n            return adapt_planner_diagnostics(base.latest_failure.diagnostics)\n        if result is not None:\n            return adapt_planner_diagnostics(result.diagnostics)\n        return ()\n\n    def _display_text(self, key: BuildingKey) -> str:\n        cached = self._display_text_cache.get(key)\n        if cached is not None:\n            return cached\n        text = self._service.get_building_display_text(key)\n        self._display_text_cache[key] = text\n        return text\n\n    def _missing_input_text(self) -> str:\n        missing: list[str] = []\n        if self._state.selected_faction is None:\n            missing.append("faction")\n        if self._state.selected_building_sid is None:\n            missing.append("target building")\n        if self._state.selected_level is None:\n            missing.append("target level")\n        return "Planning selection is complete." if not missing else "Missing: " + ", ".join(missing) + "."\n\n    def _build_summary(\n        self,\n        *,\n        base,\n        result,\n        diagnostics,\n        faction_text,\n        target_text,\n        starting_date_text,\n        failure_message,\n        missing_inputs,\n    ) -> PlanningSummaryPresentation:\n        retained = base.retains_previous_result\n        if result is None:\n            return PlanningSummaryPresentation(\n                lifecycle_status=base.execution_status.value,\n                result_status=(\n                    "Planning in progress"\n                    if base.execution_status is PlanningExecutionStatus.PENDING\n                    else "No accepted plan"\n                ),\n                faction_text=faction_text,\n                target_text=target_text,\n                starting_date_text=starting_date_text,\n                displayed_result_target_text=None,\n                step_count_text=None,\n                completion_date_text=None,\n                total_cost_text=None,\n                daily_schedule_rows=(),\n                diagnostic_summary=format_diagnostic_summary(diagnostics),\n                failure_message=failure_message,\n                missing_inputs_text=missing_inputs,\n                is_retained_previous_result=False,\n            )\n        plan = result.plan\n        rows = tuple(\n            DailyScheduleRowPresentation(\n                date_text=format_game_date(item.date),\n                building_text=self._display_text(item.building),\n                cost_text=format_resource_cost(item.cost),\n            )\n            for item in result.daily_construction_schedule\n        )\n        return PlanningSummaryPresentation(\n            lifecycle_status=base.execution_status.value,\n            result_status=("Previous Accepted Plan" if retained else "Current Accepted Plan"),\n            faction_text=faction_text,\n            target_text=target_text,\n            starting_date_text=starting_date_text,\n            displayed_result_target_text=self._display_text(plan.target),\n            step_count_text=format_step_count(plan.build_actions),\n            completion_date_text=format_game_date(plan.completion_date),\n            total_cost_text=format_resource_cost(plan.total_cost),\n            daily_schedule_rows=rows,\n            diagnostic_summary=format_diagnostic_summary(diagnostics),\n            failure_message=failure_message,\n            missing_inputs_text=(missing_inputs if base.execution_status is PlanningExecutionStatus.EMPTY else None),\n            is_retained_previous_result=retained,\n        )\n\n'''
    PRESENTER.write_text(text[:start] + replacement + text[end:], encoding="utf-8")


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '''        self._workspace_detail_var = tk.StringVar(\n            value="Choose one canonical target to plan automatically."\n        )\n''',
        '''        self._workspace_detail_var = tk.StringVar(\n            value="Choose one canonical target to plan automatically."\n        )\n        self._summary_result_status_var = tk.StringVar(value="No accepted plan")\n        self._summary_selection_var = tk.StringVar(value="Missing: faction, target building, target level.")\n        self._summary_metrics_var = tk.StringVar(value="No planning values available.")\n        self._summary_diagnostics_var = tk.StringVar(value="No diagnostics requiring attention.")\n        self._summary_failure_var = tk.StringVar(value="")\n''',
        "summary variables",
    )
    text = replace_once(
        text,
        '''        ttk.Label(\n            workspace_status,\n            textvariable=self._workspace_detail_var,\n            justify="left",\n            wraplength=720,\n        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))\n\n        self._results_text = tk.Text(\n''',
        '''        ttk.Label(\n            workspace_status,\n            textvariable=self._workspace_detail_var,\n            justify="left",\n            wraplength=720,\n        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))\n        ttk.Separator(workspace_status).grid(row=2, column=0, sticky="ew", pady=8)\n        ttk.Label(workspace_status, text="Persistent Planning Summary", font=("TkDefaultFont", 11, "bold")).grid(row=3, column=0, sticky="w")\n        ttk.Label(workspace_status, textvariable=self._summary_result_status_var, font=("TkDefaultFont", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(5, 0))\n        ttk.Label(workspace_status, textvariable=self._summary_selection_var, justify="left", wraplength=720).grid(row=5, column=0, sticky="ew", pady=(4, 0))\n        ttk.Label(workspace_status, textvariable=self._summary_metrics_var, justify="left", wraplength=720).grid(row=6, column=0, sticky="ew", pady=(4, 0))\n        ttk.Label(workspace_status, textvariable=self._summary_diagnostics_var, justify="left", wraplength=720).grid(row=7, column=0, sticky="ew", pady=(4, 0))\n        self._summary_failure_label = ttk.Label(workspace_status, textvariable=self._summary_failure_var, justify="left", wraplength=720, style="Diagnostic.Error.TLabel")\n        self._summary_failure_label.grid(row=8, column=0, sticky="ew", pady=(4, 0))\n        self._summary_failure_label.grid_remove()\n\n        self._results_text = tk.Text(\n''',
        "persistent summary layout",
    )
    start = text.index("    def render_workspace(")
    end = text.index("    def set_diagnostics(", start)
    render = '''    def render_workspace(\n        self,\n        presentation: PlanningWorkspacePresentation,\n    ) -> None:\n        self._workspace_status_var.set(presentation.status_heading)\n        self._workspace_detail_var.set(presentation.status_detail)\n        summary = presentation.summary\n        self._summary_result_status_var.set(summary.result_status)\n        selection_lines = []\n        if summary.faction_text:\n            selection_lines.append(f"Faction: {summary.faction_text}")\n        if summary.target_text:\n            selection_lines.append(f"Selected target: {summary.target_text}")\n        if summary.starting_date_text:\n            selection_lines.append(f"Starting date: {summary.starting_date_text}")\n        if summary.missing_inputs_text:\n            selection_lines.append(summary.missing_inputs_text)\n        self._summary_selection_var.set("\\n".join(selection_lines) or "No semantic selection.")\n        metric_lines = []\n        if summary.displayed_result_target_text:\n            metric_lines.append(f"Displayed plan target: {summary.displayed_result_target_text}")\n        if summary.step_count_text:\n            metric_lines.append(f"Construction: {summary.step_count_text}")\n        if summary.completion_date_text:\n            metric_lines.append(f"Completion: {summary.completion_date_text}")\n        if summary.total_cost_text:\n            metric_lines.append(f"Total cost: {summary.total_cost_text}")\n        if summary.daily_schedule_rows:\n            metric_lines.append("Daily construction schedule:")\n            metric_lines.extend(\n                f"  {row.date_text} — {row.building_text} — {row.cost_text}"\n                for row in summary.daily_schedule_rows\n            )\n        self._summary_metrics_var.set("\\n".join(metric_lines) or "No planning values available.")\n        self._summary_diagnostics_var.set(summary.diagnostic_summary)\n        if summary.failure_message:\n            self._summary_failure_var.set(f"Current failure: {summary.failure_message}")\n            self._summary_failure_label.grid()\n        else:\n            self._summary_failure_var.set("")\n            self._summary_failure_label.grid_remove()\n        self._replace_results()\n        self._append_section(summary.result_status, presentation.selection_summary)\n        if summary.displayed_result_target_text:\n            self._append_section("Displayed Plan Target", summary.displayed_result_target_text)\n        if summary.failure_message:\n            self._append_section("Current Request Failed", summary.failure_message)\n        self.set_diagnostics(presentation.diagnostics)\n        self._results_text.see("1.0")\n        if presentation.is_pending:\n            self.update_idletasks()\n\n'''
    VIEW.write_text(text[:start] + render + text[end:], encoding="utf-8")


def patch_docs() -> None:
    text = ARCH_DOC.read_text(encoding="utf-8")
    marker = "## Planning Workspace Ownership\n"
    addition = '''## Sprint 14 Persistent Planning Summary\n\nThe planner presenter maps immutable Planning Workspace snapshots into an\nimmutable `PlanningSummaryPresentation`. Values come only from the accepted\n`PlannerResult`, BE-011 `daily_construction_schedule`, the Query Layer\nlocalization operation, and existing diagnostic adapters.\n\nThe presenter caches localized text and suppresses view updates when the full\nimmutable presentation is unchanged. The view renders labels and grouping only;\nit does not derive schedules, dates, costs, diagnostics, or localization. A\nretained result is always labeled `Previous Accepted Plan`.\n\n'''
    if addition not in text:
        text = text.replace(marker, addition + marker, 1)
    ARCH_DOC.write_text(text, encoding="utf-8")


def main() -> None:
    SUMMARY_PRESENTATION.write_text(SUMMARY_SOURCE, encoding="utf-8")
    WORKSPACE_PRESENTATION.write_text(WORKSPACE_SOURCE, encoding="utf-8")
    patch_formatting()
    patch_presenter()
    patch_view()
    patch_docs()
    print("Applied UI-007 Persistent Planning Summary.")


if __name__ == "__main__":
    main()
