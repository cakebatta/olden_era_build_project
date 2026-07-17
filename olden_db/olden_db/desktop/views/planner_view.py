from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from olden_db.models import BuildingKey, BuildingLevel, ResourceCost
from olden_db.planner import BuildPlan
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
        self._mode_var = tk.StringVar(value=format_planning_mode(0))
        self._scenario_vars: dict[BuildingKey, tk.BooleanVar] = {}
        self._constraint_inspector_expanded = False
        self._constraint_diagnostics: tuple[
            PlannerDiagnosticPresentation, ...
        ] = ()

        self._on_faction_changed: Callable[[str], None] | None = None
        self._on_building_changed: Callable[[str], None] | None = None
        self._on_level_changed: Callable[[int], None] | None = None
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

        self._generate_button = ttk.Button(
            target,
            text="Generate Plan",
            command=self._handle_generate_plan,
            state="disabled",
        )
        self._generate_button.grid(row=3, column=1, sticky="e", pady=(14, 0))

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
        results.rowconfigure(0, weight=1)
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
        self._results_text.grid(row=0, column=0, sticky="nsew")
        results_scrollbar.grid(row=0, column=1, sticky="ns")
        self._results_text.tag_configure(
            "section", font=("TkDefaultFont", 11, "bold"), spacing1=12, spacing3=6
        )

        self._constraint_header = ttk.Button(
            self,
            text="▶ Constraint Inspector",
            command=self._toggle_constraint_inspector,
        )
        self._constraint_header.grid(
            row=4,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )

        self._constraint_panel = ttk.LabelFrame(
            self,
            text="Planner-provided diagnostics",
            padding=8,
        )
        self._constraint_panel.columnconfigure(0, weight=1)
        self._constraint_panel.rowconfigure(0, weight=1)

        self._constraint_canvas = tk.Canvas(
            self._constraint_panel,
            height=150,
            highlightthickness=0,
        )
        self._constraint_scrollbar = ttk.Scrollbar(
            self._constraint_panel,
            orient="vertical",
            command=self._constraint_canvas.yview,
        )
        self._constraint_canvas.configure(
            yscrollcommand=self._constraint_scrollbar.set
        )
        self._constraint_canvas.grid(row=0, column=0, sticky="nsew")
        self._constraint_scrollbar.grid(row=0, column=1, sticky="ns")
        self._constraint_content = ttk.Frame(self._constraint_canvas)
        self._constraint_window = self._constraint_canvas.create_window(
            (0, 0),
            window=self._constraint_content,
            anchor="nw",
        )
        self._constraint_content.bind(
            "<Configure>",
            lambda _event: self._constraint_canvas.configure(
                scrollregion=self._constraint_canvas.bbox("all")
            ),
        )
        self._constraint_canvas.bind(
            "<Configure>",
            lambda event: self._constraint_canvas.itemconfigure(
                self._constraint_window,
                width=event.width,
            ),
        )
        self.set_constraint_diagnostics(())
        self._show_instruction()

    def set_event_handlers(
        self,
        *,
        on_faction_changed: Callable[[str], None],
        on_building_changed: Callable[[str], None],
        on_level_changed: Callable[[int], None],
        on_generate_plan: Callable[[], None],
        on_starting_building_changed: Callable[[BuildingKey, bool], None],
        on_reset_scenario: Callable[[], None],
    ) -> None:
        self._on_faction_changed = on_faction_changed
        self._on_building_changed = on_building_changed
        self._on_level_changed = on_level_changed
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
        self._generate_button.configure(state="normal" if enabled else "disabled")

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
        self.set_constraint_diagnostics(())
        self._show_instruction()

    def show_target(self, building: BuildingLevel) -> None:
        self.set_constraint_diagnostics(())
        self._replace_results()
        self._append_section("Target", format_target(building))

    def show_prerequisites(self, statuses: tuple[PrerequisiteStatus, ...]) -> None:
        self._append_section("Direct Prerequisites", format_prerequisite_statuses(statuses))

    def show_plan(self, plan: BuildPlan, cumulative_cost: ResourceCost) -> None:
        self._append_section("Deterministic Build Plan", format_build_plan(plan))
        self._append_section("Total Cost", format_resource_cost(cumulative_cost))
        self._results_text.see("1.0")

    def show_error(self, message: str) -> None:
        self.set_constraint_diagnostics((
            PlannerDiagnosticPresentation(
                title="Planning request failed",
                explanation=message,
                severity=DiagnosticSeverity.ERROR,
            ),
        ))
        self._replace_results()
        self._append_section("Unable to Generate Plan", message)

    def set_constraint_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self._constraint_diagnostics = tuple(diagnostics)
        for widget in self._constraint_content.winfo_children():
            widget.destroy()

        if not self._constraint_diagnostics:
            ttk.Label(
                self._constraint_content,
                text="No planner constraints to display.",
                justify="left",
            ).grid(row=0, column=0, sticky="w", padx=4, pady=4)
            return

        self._constraint_content.columnconfigure(0, weight=1)
        for row, diagnostic in enumerate(self._constraint_diagnostics):
            item = ttk.Frame(self._constraint_content, padding=(4, 6))
            item.grid(row=row, column=0, sticky="ew")
            item.columnconfigure(0, weight=1)
            marker = _DIAGNOSTIC_MARKERS[diagnostic.severity]
            ttk.Label(
                item,
                text=f"{marker} {diagnostic.severity.value}: {diagnostic.title}",
                font=("TkDefaultFont", 10, "bold"),
                justify="left",
            ).grid(row=0, column=0, sticky="w")
            ttk.Label(
                item,
                text=diagnostic.explanation,
                justify="left",
                wraplength=720,
            ).grid(row=1, column=0, sticky="ew", pady=(3, 0))

    def set_constraint_inspector_expanded(self, expanded: bool) -> None:
        self._constraint_inspector_expanded = bool(expanded)
        if self._constraint_inspector_expanded:
            self._constraint_header.configure(text="▼ Constraint Inspector")
            self._constraint_panel.grid(
                row=5,
                column=0,
                sticky="nsew",
                pady=(4, 0),
            )
        else:
            self._constraint_header.configure(text="▶ Constraint Inspector")
            self._constraint_panel.grid_remove()

    @property
    def constraint_inspector_expanded(self) -> bool:
        return self._constraint_inspector_expanded

    def _toggle_constraint_inspector(self) -> None:
        self.set_constraint_inspector_expanded(
            not self._constraint_inspector_expanded
        )

    def _clear_scenario_content(self) -> None:
        for widget in self._scenario_content.winfo_children():
            widget.destroy()
        self._scenario_vars.clear()

    def _show_instruction(self) -> None:
        self._replace_results()
        self._append_text("Select a faction, building, and level to generate a build plan.")

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

    def _handle_generate_plan(self) -> None:
        if self._on_generate_plan is not None:
            self._on_generate_plan()

    def _handle_starting_building_changed(self, key: BuildingKey, available: bool) -> None:
        if self._on_starting_building_changed is not None:
            self._on_starting_building_changed(key, available)

    def _handle_reset_scenario(self) -> None:
        if self._on_reset_scenario is not None:
            self._on_reset_scenario()
