from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan, GameDate
from olden_db.scenario import PlanningScenario, PrerequisiteStatus

from ..formatting import (
    format_build_plan,
    format_planning_mode,
    format_prerequisite_statuses,
    format_resource_cost,
    format_target,
)
from ..planner_diagnostics import (
    DiagnosticSeverity,
    PlannerDiagnosticPresentation,
)
from ..workspace_presentation import PlanningWorkspacePresentation


_DIAGNOSTIC_MARKERS = {
    DiagnosticSeverity.ERROR: "[!]",
    DiagnosticSeverity.WARNING: "[Warning]",
    DiagnosticSeverity.INFORMATION: "[i]",
}


class PlannerView(ttk.Frame):
    """Target selection, scenario controls, planning results, and diagnostics."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=24)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._faction_var = tk.StringVar()
        self._building_var = tk.StringVar()
        self._level_var = tk.StringVar()
        self._start_month_var = tk.StringVar(value="1")
        self._start_week_var = tk.StringVar(value="1")
        self._start_day_var = tk.StringVar(value="1")
        self._workspace_status_var = tk.StringVar(
            value="Planning selection incomplete"
        )
        self._workspace_detail_var = tk.StringVar(
            value="Choose one canonical target to plan automatically."
        )
        self._summary_result_status_var = tk.StringVar(value="No accepted plan")
        self._summary_selection_var = tk.StringVar(value="Missing: faction, target building, target level.")
        self._summary_metrics_var = tk.StringVar(value="No planning values available.")
        self._summary_diagnostics_var = tk.StringVar(value="No diagnostics requiring attention.")
        self._summary_failure_var = tk.StringVar(value="")
        self._mode_var = tk.StringVar(value=format_planning_mode(0))
        self._scenario_vars: dict[BuildingKey, tk.BooleanVar] = {}
        self._diagnostic_inspector_expanded = False
        self._diagnostics: tuple[
            PlannerDiagnosticPresentation, ...
        ] = ()
        self._diagnostic_items: list[tk.Frame] = []
        self._diagnostic_wrap_labels: list[ttk.Label] = []

        self._on_faction_changed: Callable[[str], None] | None = None
        self._on_building_changed: Callable[[str], None] | None = None
        self._on_level_changed: Callable[[int], None] | None = None
        self._on_starting_date_changed: (
            Callable[[int, int, int], None] | None
        ) = None
        self._on_generate_plan: Callable[[], None] | None = None
        self._on_starting_building_changed: Callable[[BuildingKey, bool], None] | None = None
        self._on_reset_scenario: Callable[[], None] | None = None

        ttk.Label(self, text="Build Planner", font=("TkDefaultFont", 16, "bold")).grid(
            row=0, column=0, sticky="w"
        )

        target = ttk.LabelFrame(self, text="Target Selection", padding=16)
        target.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        target.columnconfigure(1, weight=1)

        ttk.Label(target, text="Faction").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        self._faction_selector = ttk.Combobox(target, textvariable=self._faction_var, state="readonly")
        self._faction_selector.grid(row=0, column=1, sticky="ew", pady=5)
        self._faction_selector.bind("<<ComboboxSelected>>", self._handle_faction_event)

        ttk.Label(target, text="Building SID").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        self._building_selector = ttk.Combobox(target, textvariable=self._building_var, state="disabled")
        self._building_selector.grid(row=1, column=1, sticky="ew", pady=5)
        self._building_selector.bind("<<ComboboxSelected>>", self._handle_building_event)

        ttk.Label(target, text="Level").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        self._level_selector = ttk.Combobox(target, textvariable=self._level_var, state="disabled")
        self._level_selector.grid(row=2, column=1, sticky="ew", pady=5)
        self._level_selector.bind("<<ComboboxSelected>>", self._handle_level_event)

        ttk.Label(target, text="Starting Date").grid(
            row=3, column=0, sticky="w", padx=(0, 12), pady=5
        )
        date_controls = ttk.Frame(target)
        date_controls.grid(row=3, column=1, sticky="w", pady=5)
        for column, (label, variable, upper) in enumerate((
            ("Month", self._start_month_var, 99),
            ("Week", self._start_week_var, 4),
            ("Day", self._start_day_var, 7),
        )):
            ttk.Label(date_controls, text=label).grid(
                row=0,
                column=column * 2,
                padx=(0 if column == 0 else 10, 4),
            )
            control = ttk.Spinbox(
                date_controls,
                from_=1,
                to=upper,
                width=4,
                textvariable=variable,
                command=self._handle_starting_date_event,
            )
            control.grid(row=0, column=column * 2 + 1)
            control.bind("<FocusOut>", self._handle_starting_date_event)
            control.bind("<Return>", self._handle_starting_date_event)

        ttk.Label(
            target,
            text="Plans update automatically when the semantic selection changes.",
            justify="left",
        ).grid(row=4, column=1, sticky="w", pady=(8, 0))

        self._generate_button = ttk.Button(
            target,
            text="Generate Plan",
            command=self._handle_generate_plan,
            state="disabled",
        )
        self._generate_button.grid(row=5, column=1, sticky="e")
        self._generate_button.grid_remove()

        scenario = ttk.LabelFrame(self, text="Starting Buildings", padding=10)
        scenario.grid(row=2, column=0, sticky="ew", pady=(18, 0))
        scenario.columnconfigure(0, weight=1)

        header = ttk.Frame(scenario)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, textvariable=self._mode_var, justify="left").grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Reset to Canonical Starting State",
            command=self._handle_reset_scenario,
        ).grid(row=0, column=1, sticky="e")

        shell = ttk.Frame(scenario)
        shell.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        shell.columnconfigure(0, weight=1)
        self._scenario_canvas = tk.Canvas(shell, height=180, highlightthickness=0)
        scrollbar = ttk.Scrollbar(shell, orient="vertical", command=self._scenario_canvas.yview)
        self._scenario_canvas.configure(yscrollcommand=scrollbar.set)
        self._scenario_canvas.grid(row=0, column=0, sticky="ew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._scenario_content = ttk.Frame(self._scenario_canvas)
        self._scenario_window = self._scenario_canvas.create_window(
            (0, 0), window=self._scenario_content, anchor="nw"
        )
        self._scenario_content.bind(
            "<Configure>",
            lambda _event: self._scenario_canvas.configure(
                scrollregion=self._scenario_canvas.bbox("all")
            ),
        )
        self._scenario_canvas.bind(
            "<Configure>",
            lambda event: self._scenario_canvas.itemconfigure(
                self._scenario_window, width=event.width
            ),
        )
        self.clear_starting_buildings()

        results = ttk.LabelFrame(self, text="Planning Results", padding=8)
        results.grid(row=3, column=0, sticky="nsew", pady=(18, 0))
        results.columnconfigure(0, weight=1)
        results.rowconfigure(1, weight=1)

        workspace_status = ttk.Frame(results, padding=(10, 8))
        workspace_status.grid(row=0, column=0, columnspan=2, sticky="ew")
        workspace_status.columnconfigure(0, weight=1)
        ttk.Label(
            workspace_status,
            textvariable=self._workspace_status_var,
            font=("TkDefaultFont", 11, "bold"),
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            workspace_status,
            textvariable=self._workspace_detail_var,
            justify="left",
            wraplength=720,
        ).grid(row=1, column=0, sticky="ew", pady=(3, 0))
        ttk.Separator(workspace_status).grid(row=2, column=0, sticky="ew", pady=8)
        ttk.Label(workspace_status, text="Persistent Planning Summary", font=("TkDefaultFont", 11, "bold")).grid(row=3, column=0, sticky="w")
        ttk.Label(workspace_status, textvariable=self._summary_result_status_var, font=("TkDefaultFont", 10, "bold")).grid(row=4, column=0, sticky="w", pady=(5, 0))
        ttk.Label(workspace_status, textvariable=self._summary_selection_var, justify="left", wraplength=720).grid(row=5, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(workspace_status, textvariable=self._summary_metrics_var, justify="left", wraplength=720).grid(row=6, column=0, sticky="ew", pady=(4, 0))
        ttk.Label(workspace_status, textvariable=self._summary_diagnostics_var, justify="left", wraplength=720).grid(row=7, column=0, sticky="ew", pady=(4, 0))
        self._summary_failure_label = ttk.Label(workspace_status, textvariable=self._summary_failure_var, justify="left", wraplength=720, style="Diagnostic.Error.TLabel")
        self._summary_failure_label.grid(row=8, column=0, sticky="ew", pady=(4, 0))
        self._summary_failure_label.grid_remove()

        self._results_text = tk.Text(
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

        self._diagnostic_header = ttk.Button(
            self,
            text="▶ Diagnostic Inspector",
            command=self._toggle_diagnostic_inspector,
        )
        self._diagnostic_header.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        self._diagnostic_panel = ttk.LabelFrame(
            self,
            text="Planner diagnostics",
            padding=8,
        )
        self._diagnostic_panel.columnconfigure(0, weight=1)
        self._diagnostic_panel.rowconfigure(0, weight=1)

        diagnostic_style = ttk.Style(self)
        diagnostic_style.configure("Diagnostic.Error.TLabel", foreground="#9F1D20")
        diagnostic_style.configure("Diagnostic.Warning.TLabel", foreground="#8A5A00")
        diagnostic_style.configure("Diagnostic.Information.TLabel", foreground="#1F5A7A")

        canvas_background = diagnostic_style.lookup("TFrame", "background")
        self._diagnostic_canvas = tk.Canvas(
            self._diagnostic_panel,
            height=180,
            takefocus=True,
            highlightthickness=2,
            highlightcolor="SystemHighlight",
            highlightbackground=canvas_background or "SystemButtonFace",
            background=canvas_background or "SystemButtonFace",
        )
        self._diagnostic_scrollbar = ttk.Scrollbar(
            self._diagnostic_panel,
            orient="vertical",
            command=self._diagnostic_canvas.yview,
        )
        self._diagnostic_canvas.configure(
            yscrollcommand=self._set_diagnostic_scrollbar
        )
        self._diagnostic_canvas.grid(row=0, column=0, sticky="nsew")
        self._diagnostic_scrollbar.grid(row=0, column=1, sticky="ns")
        self._diagnostic_scrollbar.grid_remove()
        self._diagnostic_content = ttk.Frame(self._diagnostic_canvas)
        self._diagnostic_window = self._diagnostic_canvas.create_window(
            (0, 0),
            window=self._diagnostic_content,
            anchor="nw",
        )
        self._diagnostic_content.bind(
            "<Configure>",
            self._update_diagnostic_scroll_region,
        )
        self._diagnostic_canvas.bind(
            "<Configure>",
            self._resize_diagnostic_content,
        )
        self._diagnostic_canvas.bind("<Up>", self._focus_previous_diagnostic)
        self._diagnostic_canvas.bind("<Down>", self._focus_next_diagnostic)
        self._diagnostic_canvas.bind("<Home>", self._focus_first_diagnostic)
        self._diagnostic_canvas.bind("<End>", self._focus_last_diagnostic)
        self._diagnostic_canvas.bind("<Prior>", self._page_diagnostics_up)
        self._diagnostic_canvas.bind("<Next>", self._page_diagnostics_down)
        self._diagnostic_canvas.bind("<MouseWheel>", self._scroll_diagnostics)
        self._diagnostic_canvas.bind("<Button-4>", self._scroll_diagnostics)
        self._diagnostic_canvas.bind("<Button-5>", self._scroll_diagnostics)

        ttk.Label(
            self._diagnostic_panel,
            text=(
                "Read-only. Use Up/Down, Home/End, or Page Up/Page Down "
                "to review diagnostics."
            ),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self.set_diagnostics(())
        self._show_instruction()

    def set_event_handlers(
        self,
        *,
        on_faction_changed: Callable[[str], None],
        on_building_changed: Callable[[str], None],
        on_level_changed: Callable[[int], None],
        on_starting_date_changed: Callable[[int, int, int], None],
        on_generate_plan: Callable[[], None],
        on_starting_building_changed: Callable[[BuildingKey, bool], None],
        on_reset_scenario: Callable[[], None],
    ) -> None:
        self._on_faction_changed = on_faction_changed
        self._on_building_changed = on_building_changed
        self._on_level_changed = on_level_changed
        self._on_starting_date_changed = on_starting_date_changed
        self._on_generate_plan = on_generate_plan
        self._on_starting_building_changed = on_starting_building_changed
        self._on_reset_scenario = on_reset_scenario

    def set_factions(self, factions: tuple[str, ...]) -> None:
        self._faction_selector.configure(values=factions)

    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        self._building_var.set("")
        self._building_selector.configure(values=buildings, state="readonly" if buildings else "disabled")

    def set_levels(self, levels: tuple[int, ...]) -> None:
        self._level_var.set("")
        self._level_selector.configure(
            values=tuple(str(level) for level in levels),
            state="readonly" if levels else "disabled",
        )

    def clear_building_selection(self) -> None:
        self._building_var.set("")
        self._building_selector.configure(values=(), state="disabled")

    def clear_level_selection(self) -> None:
        self._level_var.set("")
        self._level_selector.configure(values=(), state="disabled")

    def set_generate_enabled(self, enabled: bool) -> None:
        self._generate_button.configure(state="disabled")

    def set_starting_date(self, date: GameDate) -> None:
        self._start_month_var.set(str(date.month))
        self._start_week_var.set(str(date.week))
        self._start_day_var.set(str(date.day))

    def set_selection_values(
        self,
        faction: str,
        sid: str,
        level: int,
    ) -> None:
        self._faction_var.set(faction)
        self._building_var.set(sid)
        self._level_var.set(str(level))

    def set_starting_buildings(
        self,
        buildings: tuple[BuildingLevel, ...],
        scenario: PlanningScenario,
    ) -> None:
        self._clear_scenario_content()
        overrides = {
            override.building: override.available_at_start
            for override in scenario.starting_building_overrides
        }
        for row, building in enumerate(buildings):
            effective = overrides.get(building.key, building.constructed_on_start)
            variable = tk.BooleanVar(value=effective)
            self._scenario_vars[building.key] = variable
            canonical = "available" if building.constructed_on_start else "must construct"
            ttk.Checkbutton(
                self._scenario_content,
                text=f"{building.key.sid} level {building.key.level} — Canonical: {canonical}",
                variable=variable,
                command=lambda key=building.key, var=variable: self._handle_starting_building_changed(
                    key, var.get()
                ),
            ).grid(row=row, column=0, sticky="w", pady=2)

    def clear_starting_buildings(self) -> None:
        self._clear_scenario_content()
        ttk.Label(
            self._scenario_content,
            text="Select a faction to configure starting buildings.",
        ).grid(row=0, column=0, sticky="w")

    def set_planning_mode(self, override_count: int) -> None:
        self._mode_var.set(format_planning_mode(override_count))

    def clear_results(self) -> None:
        self.set_diagnostics(())
        self._show_instruction()

    def show_target(self, building: BuildingLevel) -> None:
        self.set_diagnostics(())
        self._replace_results()
        self._append_section("Target", format_target(building))

    def show_prerequisites(self, statuses: tuple[PrerequisiteStatus, ...]) -> None:
        self._append_section("Direct Prerequisites", format_prerequisite_statuses(statuses))

    def show_plan(self, plan: BuildPlan, cumulative_cost: ResourceCost) -> None:
        self._append_section("Deterministic Build Plan", format_build_plan(plan))
        self._append_section("Total Cost", format_resource_cost(cumulative_cost))
        self._results_text.see("1.0")

    def show_error(self, message: str) -> None:
        self.set_diagnostics((
            PlannerDiagnosticPresentation(
                title="Planning request failed",
                explanation=message,
                severity=DiagnosticSeverity.ERROR,
            ),
        ))
        self._replace_results()
        self._append_section("Unable to Generate Plan", message)

    def render_workspace(
        self,
        presentation: PlanningWorkspacePresentation,
    ) -> None:
        self._workspace_status_var.set(presentation.status_heading)
        self._workspace_detail_var.set(presentation.status_detail)
        summary = presentation.summary
        self._summary_result_status_var.set(summary.result_status)
        selection_lines = []
        if summary.faction_text:
            selection_lines.append(f"Faction: {summary.faction_text}")
        if summary.target_text:
            selection_lines.append(f"Selected target: {summary.target_text}")
        if summary.starting_date_text:
            selection_lines.append(f"Starting date: {summary.starting_date_text}")
        if summary.missing_inputs_text:
            selection_lines.append(summary.missing_inputs_text)
        self._summary_selection_var.set("\n".join(selection_lines) or "No semantic selection.")
        metric_lines = []
        if summary.displayed_result_target_text:
            metric_lines.append(f"Displayed plan target: {summary.displayed_result_target_text}")
        if summary.step_count_text:
            metric_lines.append(f"Construction: {summary.step_count_text}")
        if summary.completion_date_text:
            metric_lines.append(f"Completion: {summary.completion_date_text}")
        if summary.total_cost_text:
            metric_lines.append(f"Total cost: {summary.total_cost_text}")
        if summary.daily_schedule_rows:
            metric_lines.append("Daily construction schedule:")
            metric_lines.extend(
                f"  {row.date_text} — {row.building_text} — {row.cost_text}"
                for row in summary.daily_schedule_rows
            )
        self._summary_metrics_var.set("\n".join(metric_lines) or "No planning values available.")
        self._summary_diagnostics_var.set(summary.diagnostic_summary)
        if summary.failure_message:
            self._summary_failure_var.set(f"Current failure: {summary.failure_message}")
            self._summary_failure_label.grid()
        else:
            self._summary_failure_var.set("")
            self._summary_failure_label.grid_remove()
        self._replace_results()
        self._append_section(summary.result_status, presentation.selection_summary)
        if summary.displayed_result_target_text:
            self._append_section("Displayed Plan Target", summary.displayed_result_target_text)
        if summary.failure_message:
            self._append_section("Current Request Failed", summary.failure_message)
        self.set_diagnostics(presentation.diagnostics)
        self._results_text.see("1.0")
        if presentation.is_pending:
            self.update_idletasks()

    def set_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self._diagnostics = tuple(diagnostics)
        for widget in self._diagnostic_content.winfo_children():
            widget.destroy()
        self._diagnostic_items.clear()
        self._diagnostic_wrap_labels.clear()
        self._diagnostic_canvas.yview_moveto(0.0)

        if not self._diagnostics:
            empty_state = ttk.Frame(self._diagnostic_content, padding=(18, 22))
            empty_state.grid(row=0, column=0, sticky="nsew")
            empty_state.columnconfigure(0, weight=1)
            ttk.Label(
                empty_state,
                text="[i] No diagnostics",
                font=("TkDefaultFont", 11, "bold"),
                justify="center",
                style="Diagnostic.Information.TLabel",
            ).grid(row=0, column=0)
            ttk.Label(
                empty_state,
                text="Generate a plan to review planner-provided explanations.",
                justify="center",
            ).grid(row=1, column=0, pady=(6, 0))
            self._diagnostic_content.columnconfigure(0, weight=1)
            self.after_idle(self._update_diagnostic_scrollbar)
            return

        style_by_severity = {
            DiagnosticSeverity.ERROR: "Diagnostic.Error.TLabel",
            DiagnosticSeverity.WARNING: "Diagnostic.Warning.TLabel",
            DiagnosticSeverity.INFORMATION: "Diagnostic.Information.TLabel",
        }
        self._diagnostic_content.columnconfigure(0, weight=1)

        for row, diagnostic in enumerate(self._diagnostics):
            item = tk.Frame(
                self._diagnostic_content,
                padx=10,
                pady=9,
                takefocus=True,
                borderwidth=1,
                relief="solid",
                highlightthickness=2,
                highlightcolor="SystemHighlight",
                highlightbackground="SystemButtonFace",
            )
            item.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=(2, 6),
                pady=(2 if row == 0 else 5, 2),
            )
            item.columnconfigure(1, weight=1)
            self._bind_diagnostic_navigation(item)
            self._diagnostic_items.append(item)

            marker = _DIAGNOSTIC_MARKERS[diagnostic.severity]
            severity_style = style_by_severity[diagnostic.severity]
            severity_label = ttk.Label(
                item,
                text=f"{marker} {diagnostic.severity.value}",
                font=("TkDefaultFont", 9, "bold"),
                style=severity_style,
                justify="left",
            )
            severity_label.grid(row=0, column=0, sticky="nw", padx=(0, 10))
            title_label = ttk.Label(
                item,
                text=diagnostic.title,
                font=("TkDefaultFont", 10, "bold"),
                justify="left",
            )
            title_label.grid(row=0, column=1, sticky="ew")

            explanation_label = ttk.Label(
                item,
                text=diagnostic.explanation,
                justify="left",
                anchor="w",
                wraplength=1,
            )
            explanation_label.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(7, 0),
            )
            self._diagnostic_wrap_labels.append(explanation_label)

            for widget in (severity_label, title_label, explanation_label):
                widget.bind("<MouseWheel>", self._scroll_diagnostics)
                widget.bind("<Button-4>", self._scroll_diagnostics)
                widget.bind("<Button-5>", self._scroll_diagnostics)

        self.after_idle(self._refresh_diagnostic_layout)

    def _bind_diagnostic_navigation(self, item: tk.Frame) -> None:
        item.bind("<Up>", self._focus_previous_diagnostic)
        item.bind("<Down>", self._focus_next_diagnostic)
        item.bind("<Home>", self._focus_first_diagnostic)
        item.bind("<End>", self._focus_last_diagnostic)
        item.bind("<Prior>", self._page_diagnostics_up)
        item.bind("<Next>", self._page_diagnostics_down)
        item.bind("<MouseWheel>", self._scroll_diagnostics)
        item.bind("<Button-4>", self._scroll_diagnostics)
        item.bind("<Button-5>", self._scroll_diagnostics)

    def _refresh_diagnostic_layout(self) -> None:
        self.update_idletasks()
        self._resize_diagnostic_content()
        self._update_diagnostic_scrollbar()

    def _resize_diagnostic_content(
        self,
        event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        width = int(event.width) if event is not None else self._diagnostic_canvas.winfo_width()
        width = max(180, width)
        self._diagnostic_canvas.itemconfigure(self._diagnostic_window, width=width)
        wraplength = max(140, width - 48)
        for label in self._diagnostic_wrap_labels:
            label.configure(wraplength=wraplength)
        self.after_idle(self._update_diagnostic_scrollbar)

    def _update_diagnostic_scroll_region(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        bounds = self._diagnostic_canvas.bbox("all")
        if bounds is not None:
            self._diagnostic_canvas.configure(scrollregion=bounds)
        self._update_diagnostic_scrollbar()

    def _set_diagnostic_scrollbar(self, first: str, last: str) -> None:
        self._diagnostic_scrollbar.set(first, last)
        self._update_diagnostic_scrollbar(float(first), float(last))

    def _update_diagnostic_scrollbar(
        self,
        first: float | None = None,
        last: float | None = None,
    ) -> None:
        if first is None or last is None:
            first, last = self._diagnostic_canvas.yview()
        if first <= 0.0 and last >= 1.0:
            self._diagnostic_scrollbar.grid_remove()
        else:
            self._diagnostic_scrollbar.grid()

    def set_diagnostic_inspector_expanded(self, expanded: bool) -> None:
        self._diagnostic_inspector_expanded = bool(expanded)
        if self._diagnostic_inspector_expanded:
            self._diagnostic_header.configure(text="▼ Diagnostic Inspector")
            self._diagnostic_panel.grid(
                row=5,
                column=0,
                sticky="nsew",
                pady=(4, 0),
            )
        else:
            self._diagnostic_header.configure(text="▶ Diagnostic Inspector")
            self._diagnostic_panel.grid_remove()

    @property
    def diagnostic_inspector_expanded(self) -> bool:
        return self._diagnostic_inspector_expanded

    def _toggle_diagnostic_inspector(self) -> None:
        self.set_diagnostic_inspector_expanded(
            not self._diagnostic_inspector_expanded
        )

    def _focused_diagnostic_index(self) -> int:
        focused = self.focus_get()
        try:
            return self._diagnostic_items.index(focused)
        except ValueError:
            return -1

    def _focus_diagnostic(self, index: int) -> str:
        if not self._diagnostic_items:
            self._diagnostic_canvas.focus_set()
            return "break"
        index = max(0, min(index, len(self._diagnostic_items) - 1))
        item = self._diagnostic_items[index]
        item.focus_set()
        self.update_idletasks()
        content_height = max(1, self._diagnostic_content.winfo_reqheight())
        viewport_height = max(1, self._diagnostic_canvas.winfo_height())
        item_top = item.winfo_y()
        item_bottom = item_top + item.winfo_height()
        visible_top = self._diagnostic_canvas.canvasy(0)
        visible_bottom = visible_top + viewport_height
        if item_top < visible_top:
            self._diagnostic_canvas.yview_moveto(item_top / content_height)
        elif item_bottom > visible_bottom:
            target = max(0, item_bottom - viewport_height)
            self._diagnostic_canvas.yview_moveto(target / content_height)
        return "break"

    def _focus_previous_diagnostic(self, _event: tk.Event[tk.Misc]) -> str:
        return self._focus_diagnostic(self._focused_diagnostic_index() - 1)

    def _focus_next_diagnostic(self, _event: tk.Event[tk.Misc]) -> str:
        return self._focus_diagnostic(self._focused_diagnostic_index() + 1)

    def _focus_first_diagnostic(self, _event: tk.Event[tk.Misc]) -> str:
        return self._focus_diagnostic(0)

    def _focus_last_diagnostic(self, _event: tk.Event[tk.Misc]) -> str:
        return self._focus_diagnostic(len(self._diagnostic_items) - 1)

    def _page_diagnostics_up(self, _event: tk.Event[tk.Misc]) -> str:
        self._diagnostic_canvas.yview_scroll(-1, "pages")
        return "break"

    def _page_diagnostics_down(self, _event: tk.Event[tk.Misc]) -> str:
        self._diagnostic_canvas.yview_scroll(1, "pages")
        return "break"

    def _scroll_diagnostics(self, event: tk.Event[tk.Misc]) -> str:
        first, last = self._diagnostic_canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return "break"

        if getattr(event, "num", None) == 4:
            units = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"
            magnitude = max(1, abs(delta) // 120)
            units = -magnitude if delta > 0 else magnitude

        self._diagnostic_canvas.yview_scroll(units, "units")
        return "break"

    def _clear_scenario_content(self) -> None:
        for widget in self._scenario_content.winfo_children():
            widget.destroy()
        self._scenario_vars.clear()

    def _show_instruction(self) -> None:
        self._replace_results()
        self._append_text(
            "Select a faction, building, and level to begin automatic planning."
        )

    def _replace_results(self) -> None:
        self._results_text.configure(state="normal")
        self._results_text.delete("1.0", "end")
        self._results_text.configure(state="disabled")

    def _append_section(self, heading: str, content: str) -> None:
        self._results_text.configure(state="normal")
        self._results_text.insert("end", heading + "\n", "section")
        self._results_text.insert("end", content + "\n")
        self._results_text.configure(state="disabled")

    def _append_text(self, content: str) -> None:
        self._results_text.configure(state="normal")
        self._results_text.insert("end", content)
        self._results_text.configure(state="disabled")

    def _handle_faction_event(self, _event: tk.Event[tk.Misc]) -> None:
        if self._on_faction_changed is not None:
            self._on_faction_changed(self._faction_var.get())

    def _handle_building_event(self, _event: tk.Event[tk.Misc]) -> None:
        if self._on_building_changed is not None:
            self._on_building_changed(self._building_var.get())

    def _handle_level_event(self, _event: tk.Event[tk.Misc]) -> None:
        if self._on_level_changed is not None:
            self._on_level_changed(int(self._level_var.get()))

    def _handle_starting_date_event(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> str | None:
        if self._on_starting_date_changed is None:
            return None
        try:
            month = int(self._start_month_var.get())
            week = int(self._start_week_var.get())
            day = int(self._start_day_var.get())
        except ValueError:
            return "break"
        self._on_starting_date_changed(month, week, day)
        return "break" if _event is not None else None

    def _handle_generate_plan(self) -> None:
        if self._on_generate_plan is not None:
            self._on_generate_plan()

    def _handle_starting_building_changed(self, key: BuildingKey, available: bool) -> None:
        if self._on_starting_building_changed is not None:
            self._on_starting_building_changed(key, available)

    def _handle_reset_scenario(self) -> None:
        if self._on_reset_scenario is not None:
            self._on_reset_scenario()
