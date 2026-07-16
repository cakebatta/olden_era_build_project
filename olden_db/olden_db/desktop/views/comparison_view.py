from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from olden_db.comparison import PlanComparison

from ..formatting import (
    format_building_key,
    format_game_date,
    format_resource_cost,
)

COMPARISON_NARROW_BREAKPOINT = 760


def comparison_layout_for_width(width: int) -> str:
    return "narrow" if width < COMPARISON_NARROW_BREAKPOINT else "wide"


class _Side(ttk.LabelFrame):
    def __init__(
        self,
        parent,
        side,
        title,
        handlers,
    ) -> None:
        super().__init__(parent, text=title, padding=10)
        self.side = side
        self.handlers = handlers
        self.columnconfigure(1, weight=1)

        self.f = tk.StringVar()
        self.b = tk.StringVar()
        self.l = tk.StringVar()
        self.mode = tk.StringVar(
            value="Planning mode: Canonical"
        )

        ttk.Label(self, text="Faction").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.fc = ttk.Combobox(
            self,
            textvariable=self.f,
            state="readonly",
        )
        self.fc.grid(row=0, column=1, sticky="ew")
        self.fc.bind(
            "<<ComboboxSelected>>",
            lambda _event: handlers["faction"](
                side,
                self.f.get(),
            ),
        )

        ttk.Label(self, text="Building SID").grid(
            row=1,
            column=0,
            sticky="w",
        )
        self.bc = ttk.Combobox(
            self,
            textvariable=self.b,
            state="disabled",
        )
        self.bc.grid(row=1, column=1, sticky="ew")
        self.bc.bind(
            "<<ComboboxSelected>>",
            lambda _event: handlers["building"](
                side,
                self.b.get(),
            ),
        )

        ttk.Label(self, text="Level").grid(
            row=2,
            column=0,
            sticky="w",
        )
        self.lc = ttk.Combobox(
            self,
            textvariable=self.l,
            state="disabled",
        )
        self.lc.grid(row=2, column=1, sticky="ew")
        self.lc.bind(
            "<<ComboboxSelected>>",
            lambda _event: handlers["level"](
                side,
                int(self.l.get()),
            ),
        )

        header = ttk.Frame(self)
        header.grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(8, 2),
        )
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            textvariable=self.mode,
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Reset Scenario",
            command=lambda: handlers["reset"](side),
        ).grid(row=0, column=1)

        self.canvas = tk.Canvas(
            self,
            height=140,
            highlightthickness=0,
        )
        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.canvas.configure(
            yscrollcommand=scrollbar.set
        )
        self.canvas.grid(
            row=4,
            column=0,
            columnspan=2,
            sticky="ew",
        )
        scrollbar.grid(row=4, column=2, sticky="ns")

        self.inner = ttk.Frame(self.canvas)
        self.window = self.canvas.create_window(
            (0, 0),
            window=self.inner,
            anchor="nw",
        )
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(
                self.window,
                width=event.width,
            ),
        )
        self.clear_candidates()

    def set_factions(self, values) -> None:
        self.fc.configure(values=values)

    def set_buildings(self, values) -> None:
        self.b.set("")
        self.bc.configure(
            values=values,
            state="readonly" if values else "disabled",
        )
        self.l.set("")
        self.lc.configure(values=(), state="disabled")

    def set_levels(self, values) -> None:
        self.l.set("")
        self.lc.configure(
            values=tuple(map(str, values)),
            state="readonly" if values else "disabled",
        )

    def set_candidates(self, buildings, scenario) -> None:
        self._clear()
        overrides = {
            override.building: override.available_at_start
            for override in scenario.starting_building_overrides
        }
        for row, building in enumerate(buildings):
            variable = tk.BooleanVar(
                value=overrides.get(
                    building.key,
                    building.constructed_on_start,
                )
            )
            canonical = (
                "available"
                if building.constructed_on_start
                else "construct"
            )
            ttk.Checkbutton(
                self.inner,
                text=(
                    f"{building.key.sid} level "
                    f"{building.key.level} — Canonical: {canonical}"
                ),
                variable=variable,
                command=lambda key=building.key, var=variable: (
                    self.handlers["scenario"](
                        self.side,
                        key,
                        var.get(),
                    )
                ),
            ).grid(row=row, column=0, sticky="w")

    def clear_candidates(self) -> None:
        self._clear()
        ttk.Label(
            self.inner,
            text=(
                "Select a faction to configure "
                "starting buildings."
            ),
        ).grid(row=0, column=0, sticky="w")

    def set_mode(self, count) -> None:
        self.mode.set(
            "Planning mode: Canonical"
            if count == 0
            else (
                "Planning mode: Custom Starting State\n"
                f"Overrides: {count}"
            )
        )

    def _clear(self) -> None:
        for widget in self.inner.winfo_children():
            widget.destroy()


class ComparisonView(ttk.Frame):
    """Responsive pairwise comparison and decision summary workspace."""

    def __init__(self, parent) -> None:
        super().__init__(parent, padding=18)
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.handlers = {}
        self.left = None
        self.right = None
        self._layout_mode: str | None = None

        ttk.Label(
            self,
            text="Plan Comparison",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.button = ttk.Button(
            self,
            text="Compare Plans",
            state="disabled",
            command=self._compare,
        )

        self.results_box = ttk.LabelFrame(
            self,
            text="Comparison Results",
            padding=8,
        )
        self.results_box.columnconfigure(0, weight=1)
        self.results_box.rowconfigure(0, weight=1)

        self.text = tk.Text(
            self.results_box,
            wrap="word",
            state="disabled",
            height=18,
        )
        scrollbar = ttk.Scrollbar(
            self.results_box,
            orient="vertical",
            command=self.text.yview,
        )
        self.text.configure(
            yscrollcommand=scrollbar.set
        )
        self.text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.tag_configure(
            "h",
            font=("TkDefaultFont", 11, "bold"),
        )
        self.clear_results()
        self.bind("<Configure>", self._on_configure)

    def set_event_handlers(self, **handlers) -> None:
        self.handlers = handlers
        mapped = {
            "faction": handlers["on_faction_changed"],
            "building": handlers["on_building_changed"],
            "level": handlers["on_level_changed"],
            "scenario": handlers["on_scenario_changed"],
            "reset": handlers["on_reset_scenario"],
        }
        self.left = _Side(
            self,
            "left",
            "Left Plan",
            mapped,
        )
        self.right = _Side(
            self,
            "right",
            "Right Plan",
            mapped,
        )
        self._apply_layout(
            comparison_layout_for_width(self.winfo_width())
        )

    def set_factions(self, values) -> None:
        self.left.set_factions(values)
        self.right.set_factions(values)

    def set_buildings(self, side, values) -> None:
        getattr(self, side).set_buildings(values)

    def set_levels(self, side, values) -> None:
        getattr(self, side).set_levels(values)

    def set_scenario_candidates(
        self,
        side,
        buildings,
        scenario,
    ) -> None:
        getattr(self, side).set_candidates(
            buildings,
            scenario,
        )

    def set_mode(self, side, count) -> None:
        getattr(self, side).set_mode(count)

    def set_compare_enabled(self, enabled) -> None:
        self.button.configure(
            state="normal" if enabled else "disabled"
        )

    def clear_results(self) -> None:
        self._replace(
            "Select complete left and right targets, then compare."
        )

    def show_error(self, message) -> None:
        self._replace(
            "Unable to Compare Plans\n" + message
        )

    def show_comparison(
        self,
        comparison: PlanComparison,
    ) -> None:
        left = "\n".join(
            (
                "Target: "
                f"{format_building_key(comparison.left_plan.target)}",
                "Completion date: "
                f"{format_game_date(comparison.left_plan.completion_date)}",
                "Total cost: "
                f"{format_resource_cost(comparison.left_plan.total_cost)}",
                "Construction actions: "
                f"{comparison.left_plan.build_actions}",
            )
        )
        right = "\n".join(
            (
                "Target: "
                f"{format_building_key(comparison.right_plan.target)}",
                "Completion date: "
                f"{format_game_date(comparison.right_plan.completion_date)}",
                "Total cost: "
                f"{format_resource_cost(comparison.right_plan.total_cost)}",
                "Construction actions: "
                f"{comparison.right_plan.build_actions}",
            )
        )
        added = (
            "None"
            if not comparison.added_buildings
            else "\n".join(
                format_building_key(item)
                for item in comparison.added_buildings
            )
        )
        removed = (
            "None"
            if not comparison.removed_buildings
            else "\n".join(
                format_building_key(item)
                for item in comparison.removed_buildings
            )
        )
        summary = "\n".join(
            (
                f"Identical: {'Yes' if comparison.identical else 'No'}",
                f"Action-count delta: {comparison.action_delta}",
                "Completion-date delta: "
                f"{comparison.completion_date_delta}",
                "Resource delta: "
                f"{format_resource_cost(comparison.resource_delta)}",
                "",
                "Added buildings:",
                added,
                "",
                "Removed buildings:",
                removed,
            )
        )
        self._replace("")
        self._section("Left Plan", left)
        self._section("Right Plan", right)
        self._section("Comparison Summary", summary)

    def show_decision_summary(
        self,
        observations: tuple[str, ...],
    ) -> None:
        self._section(
            "Decision Summary",
            "\n".join(
                f"{index}. {text}"
                for index, text in enumerate(
                    observations,
                    start=1,
                )
            ),
        )

    def _on_configure(
        self,
        event: tk.Event[tk.Misc],
    ) -> None:
        self._apply_layout(
            comparison_layout_for_width(event.width)
        )

    def _apply_layout(self, mode: str) -> None:
        if (
            mode == self._layout_mode
            or self.left is None
            or self.right is None
        ):
            return

        self.left.grid_forget()
        self.right.grid_forget()
        self.button.grid_forget()
        self.results_box.grid_forget()

        if mode == "wide":
            self.left.grid(
                row=1,
                column=0,
                sticky="nsew",
                padx=(0, 5),
            )
            self.right.grid(
                row=1,
                column=1,
                sticky="nsew",
                padx=(5, 0),
            )
            self.button.grid(
                row=2,
                column=0,
                columnspan=2,
                pady=8,
            )
            self.results_box.grid(
                row=3,
                column=0,
                columnspan=2,
                sticky="nsew",
            )
        else:
            self.left.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="nsew",
                pady=(0, 6),
            )
            self.right.grid(
                row=2,
                column=0,
                columnspan=2,
                sticky="nsew",
                pady=(0, 6),
            )
            self.button.grid(
                row=3,
                column=0,
                columnspan=2,
                pady=8,
            )
            self.results_box.grid(
                row=4,
                column=0,
                columnspan=2,
                sticky="nsew",
            )

        self._layout_mode = mode

    def _compare(self) -> None:
        callback = self.handlers.get("on_compare")
        if callback:
            callback()

    def _replace(self, content) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", content)
        self.text.configure(state="disabled")

    def _section(self, heading, body) -> None:
        self.text.configure(state="normal")
        self.text.insert("end", heading + "\n", "h")
        self.text.insert("end", body + "\n")
        self.text.configure(state="disabled")
