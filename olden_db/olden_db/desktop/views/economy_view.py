from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from olden_db.constants import RESOURCE_NAMES
from olden_db.models import BuildingKey
from olden_db.planner import GameDate
from olden_db.query import ResourceLedger

from ..economy_formatting import format_resource_ledger
from ..economy_state import RecruitmentSelection
from ..formatting import (
    format_building_key,
    format_game_date,
    format_planning_mode,
)

QUANTITY_SLIDER_MAXIMUM = 9999


class _QuantityControl(ttk.Frame):
    """One non-negative quantity with synchronized slider and spinbox."""

    def __init__(
        self,
        parent,
        *,
        label: str,
        enabled: bool,
        initial: int,
        on_change: Callable[[int], None],
    ) -> None:
        super().__init__(parent)
        self._on_change = on_change
        self._ready = False
        self._changing = False
        self._var = tk.IntVar(value=initial)

        ttk.Label(self, text=label, width=18).grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._scale = ttk.Scale(
            self,
            from_=0,
            to=QUANTITY_SLIDER_MAXIMUM,
            orient="horizontal",
            command=self._scale_changed,
        )
        self._scale.grid(row=0, column=1, sticky="ew", padx=5)
        self._spinbox = ttk.Spinbox(
            self,
            from_=0,
            to=QUANTITY_SLIDER_MAXIMUM,
            textvariable=self._var,
            width=7,
            command=self._spinbox_changed,
        )
        self._spinbox.grid(row=0, column=2)
        self.columnconfigure(1, weight=1)

        self._scale.set(min(initial, QUANTITY_SLIDER_MAXIMUM))
        self._var.trace_add("write", self._entry_changed)
        self._ready = True
        self.set_enabled(enabled)

    def value(self) -> int:
        try:
            return int(self._var.get())
        except (tk.TclError, ValueError):
            return 0

    def set_value(self, value: int) -> None:
        self._changing = True
        self._var.set(value)
        self._scale.set(
            max(0, min(value, QUANTITY_SLIDER_MAXIMUM))
        )
        self._changing = False

    def set_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self._scale.configure(state=state)
        self._spinbox.configure(state=state)

    def _scale_changed(self, raw_value: str) -> None:
        if not self._ready or self._changing:
            return
        value = max(0, int(round(float(raw_value))))
        if value == self.value():
            return
        self._changing = True
        self._var.set(value)
        self._changing = False
        self._on_change(value)

    def _spinbox_changed(self) -> None:
        if self._ready and not self._changing:
            self._emit_entry_value()

    def _entry_changed(self, *_args) -> None:
        if self._ready and not self._changing:
            self.after_idle(self._emit_entry_value)

    def _emit_entry_value(self) -> None:
        if self._changing:
            return
        value = self.value()
        if value >= 0:
            self._changing = True
            self._scale.set(
                min(value, QUANTITY_SLIDER_MAXIMUM)
            )
            self._changing = False
        self._on_change(value)


class _RecruitmentRow:
    """Widgets for one backend-provided dated dwelling entry."""

    def __init__(
        self,
        parent,
        *,
        stock_entry,
        initial: RecruitmentSelection,
        on_change,
    ) -> None:
        self.date = stock_entry.date
        self.dwelling = stock_entry.dwelling
        self.frame = ttk.LabelFrame(
            parent,
            text=(
                f"{format_game_date(stock_entry.date)} — "
                f"{stock_entry.dwelling.sid}"
            ),
            padding=6,
        )
        self.frame.columnconfigure(0, weight=1)

        ttk.Label(
            self.frame,
            text=(
                "Backend-reported available stock: "
                f"{stock_entry.available}"
            ),
        ).grid(row=0, column=0, sticky="w")

        self.requested_var = tk.StringVar()
        ttk.Label(
            self.frame,
            textvariable=self.requested_var,
        ).grid(row=0, column=1, sticky="e")

        controls: dict[str, _QuantityControl] = {}

        def emit(_value: int = 0) -> None:
            on_change(
                self.date,
                self.dwelling,
                controls["base"].value(),
                controls["upgraded"].value(),
            )

        controls["base"] = _QuantityControl(
            self.frame,
            label=stock_entry.unit_family.base_sid,
            enabled=True,
            initial=initial.base_quantity,
            on_change=emit,
        )
        controls["base"].grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        controls["upgraded"] = _QuantityControl(
            self.frame,
            label="Upgraded units",
            enabled=True,
            initial=initial.upgraded_quantity,
            on_change=emit,
        )
        controls["upgraded"].grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
        )

        ttk.Label(
            self.frame,
            text=(
                "Recruitment legality and upgrade availability "
                "are validated when the timeline is generated."
            ),
        ).grid(
            row=3,
            column=0,
            columnspan=2,
            sticky="w",
        )

        self.base = controls["base"]
        self.upgraded = controls["upgraded"]
        self.apply(initial)

    def apply(self, selection: RecruitmentSelection) -> None:
        self.base.set_value(selection.base_quantity)
        self.upgraded.set_value(selection.upgraded_quantity)
        self.requested_var.set(
            f"Requested total: {selection.total_quantity}"
        )


class EconomyTimelineView(ttk.Frame):
    """Treasury, recruitment requests, and authoritative ledger results."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=16)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(4, weight=1)

        self._on_resources_changed = None
        self._on_recruitment_changed = None
        self._on_generate = None
        self._resource_vars = {
            name: tk.StringVar(value="0")
            for name in RESOURCE_NAMES
        }
        self._context_var = tk.StringVar(
            value="Select a complete target in Build Planner."
        )
        self._mode_var = tk.StringVar(
            value=format_planning_mode(0)
        )
        self._input_error_var = tk.StringVar()
        self._recruitment_error_var = tk.StringVar()
        self._rows: dict[
            tuple[GameDate, BuildingKey],
            _RecruitmentRow,
        ] = {}

        ttk.Label(
            self,
            text="Economy Timeline",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        context = ttk.LabelFrame(
            self,
            text="Planning Context",
            padding=8,
        )
        context.grid(
            row=1,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )
        ttk.Label(
            context,
            textvariable=self._context_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            context,
            textvariable=self._mode_var,
        ).grid(row=1, column=0, sticky="w")

        resources = ttk.LabelFrame(
            self,
            text="Starting Resources",
            padding=8,
        )
        resources.grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )
        for index, name in enumerate(RESOURCE_NAMES):
            row = index // 4
            column = (index % 4) * 2
            ttk.Label(
                resources,
                text=name.capitalize(),
            ).grid(row=row, column=column, sticky="w")
            entry = ttk.Entry(
                resources,
                textvariable=self._resource_vars[name],
                width=9,
            )
            entry.grid(
                row=row,
                column=column + 1,
                padx=(4, 12),
            )
            entry.bind(
                "<KeyRelease>",
                lambda _event: self._emit_resources(),
            )

        ttk.Label(
            resources,
            textvariable=self._input_error_var,
        ).grid(
            row=2,
            column=0,
            columnspan=6,
            sticky="w",
        )
        self._generate_button = ttk.Button(
            resources,
            text="Generate Economy Timeline",
            state="disabled",
            command=self._handle_generate,
        )
        self._generate_button.grid(
            row=2,
            column=6,
            columnspan=2,
            sticky="e",
        )

        recruitment = ttk.LabelFrame(
            self,
            text="Recruitment Schedule",
            padding=8,
        )
        recruitment.grid(
            row=3,
            column=0,
            sticky="ew",
            pady=(10, 0),
        )
        recruitment.columnconfigure(0, weight=1)

        self._schedule_canvas = tk.Canvas(
            recruitment,
            height=230,
            highlightthickness=0,
        )
        schedule_scrollbar = ttk.Scrollbar(
            recruitment,
            orient="vertical",
            command=self._schedule_canvas.yview,
        )
        self._schedule_canvas.configure(
            yscrollcommand=schedule_scrollbar.set
        )
        self._schedule_canvas.grid(
            row=0,
            column=0,
            sticky="ew",
        )
        schedule_scrollbar.grid(row=0, column=1, sticky="ns")

        self._schedule_content = ttk.Frame(
            self._schedule_canvas
        )
        self._schedule_window = (
            self._schedule_canvas.create_window(
                (0, 0),
                window=self._schedule_content,
                anchor="nw",
            )
        )
        self._schedule_content.bind(
            "<Configure>",
            lambda _event: self._schedule_canvas.configure(
                scrollregion=self._schedule_canvas.bbox("all")
            ),
        )
        self._schedule_canvas.bind(
            "<Configure>",
            lambda event: self._schedule_canvas.itemconfigure(
                self._schedule_window,
                width=event.width,
            ),
        )
        self._bind_mousewheel(self._schedule_canvas)
        self._bind_mousewheel(self._schedule_content)

        ttk.Label(
            recruitment,
            textvariable=self._recruitment_error_var,
        ).grid(row=1, column=0, sticky="w")
        self.clear_recruitment_controls()

        results = ttk.LabelFrame(
            self,
            text="Resource Ledger",
            padding=8,
        )
        results.grid(
            row=4,
            column=0,
            sticky="nsew",
            pady=(10, 0),
        )
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)
        self._text = tk.Text(
            results,
            wrap="word",
            state="disabled",
        )
        scrollbar = ttk.Scrollbar(
            results,
            orient="vertical",
            command=self._text.yview,
        )
        self._text.configure(yscrollcommand=scrollbar.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.clear_ledger()

    def set_event_handlers(
        self,
        *,
        on_resources_changed,
        on_recruitment_changed,
        on_generate,
    ) -> None:
        self._on_resources_changed = on_resources_changed
        self._on_recruitment_changed = on_recruitment_changed
        self._on_generate = on_generate

    def set_planning_context(
        self,
        *,
        faction: str,
        sid: str,
        level: int,
        override_count: int,
    ) -> None:
        self._context_var.set(
            format_building_key(
                BuildingKey(faction, sid, level)
            )
        )
        self._mode_var.set(
            format_planning_mode(override_count)
        )

    def clear_planning_context(self) -> None:
        self._context_var.set(
            "Select a complete target in Build Planner."
        )
        self._mode_var.set(format_planning_mode(0))

    def set_generate_enabled(self, enabled: bool) -> None:
        self._generate_button.configure(
            state="normal" if enabled else "disabled"
        )

    def set_recruitment_controls(
        self,
        ledger: ResourceLedger,
        selections: tuple[RecruitmentSelection, ...],
    ) -> None:
        self._clear_schedule()
        self._rows = {}
        selected = {
            (item.date, item.dwelling): item
            for item in selections
        }

        row_index = 0
        for stock_entry in ledger.stock.entries:
            if stock_entry.available <= 0:
                continue
            key = (
                stock_entry.date,
                stock_entry.dwelling,
            )
            selection = selected.get(
                key,
                RecruitmentSelection(
                    stock_entry.date,
                    stock_entry.dwelling,
                ),
            )
            row = _RecruitmentRow(
                self._schedule_content,
                stock_entry=stock_entry,
                initial=selection,
                on_change=self._on_recruitment_changed,
            )
            row.frame.grid(
                row=row_index,
                column=0,
                sticky="ew",
                pady=3,
            )
            self._bind_mousewheel(row.frame)
            self._rows[key] = row
            row_index += 1

        if row_index == 0:
            ttk.Label(
                self._schedule_content,
                text=(
                    "No backend recruitment entries are available "
                    "for this ledger."
                ),
            ).grid(row=0, column=0, sticky="w")

        self.apply_recruitment_state(selections)

    def apply_recruitment_state(
        self,
        selections: tuple[RecruitmentSelection, ...],
    ) -> None:
        selected = {
            (item.date, item.dwelling): item
            for item in selections
        }
        for key, row in self._rows.items():
            row.apply(
                selected.get(
                    key,
                    RecruitmentSelection(*key),
                )
            )

    def clear_recruitment_controls(self) -> None:
        self._clear_schedule()
        self._rows = {}
        ttk.Label(
            self._schedule_content,
            text=(
                "Generate the Economy Timeline once to load "
                "backend-provided recruitment dates and dwellings."
            ),
        ).grid(row=0, column=0, sticky="w")

    def show_recruitment_error(
        self,
        message: str,
    ) -> None:
        self._recruitment_error_var.set(message)

    def clear_recruitment_error(self) -> None:
        self._recruitment_error_var.set("")

    def show_input_error(self, message: str) -> None:
        self._input_error_var.set(message)

    def clear_input_error(self) -> None:
        self._input_error_var.set("")

    def clear_ledger(self) -> None:
        self._replace(
            "Recruitment schedule changed. "
            "Regenerate to update the ledger."
        )

    def show_ledger(
        self,
        ledger: ResourceLedger,
    ) -> None:
        self._replace(format_resource_ledger(ledger))
        self._text.see("1.0")

    def show_error(self, message: str) -> None:
        self._replace(
            "Unable to Generate Economy Timeline\n"
            + message
        )

    def _emit_resources(self) -> None:
        self._on_resources_changed(
            {
                name: variable.get()
                for name, variable
                in self._resource_vars.items()
            }
        )

    def _handle_generate(self) -> None:
        self._on_generate()

    def _clear_schedule(self) -> None:
        for widget in (
            self._schedule_content.winfo_children()
        ):
            widget.destroy()

    def _bind_mousewheel(
        self,
        widget: tk.Misc,
    ) -> None:
        widget.bind(
            "<MouseWheel>",
            lambda event: (
                self._schedule_canvas.yview_scroll(
                    int(-event.delta / 120),
                    "units",
                )
            ),
        )
        widget.bind(
            "<Button-4>",
            lambda _event: (
                self._schedule_canvas.yview_scroll(
                    -1,
                    "units",
                )
            ),
        )
        widget.bind(
            "<Button-5>",
            lambda _event: (
                self._schedule_canvas.yview_scroll(
                    1,
                    "units",
                )
            ),
        )

    def _replace(self, content: str) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("end", content)
        self._text.configure(state="disabled")
