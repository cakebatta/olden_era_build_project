from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from olden_db.constants import RESOURCE_NAMES
from olden_db.models import BuildingKey
from olden_db.query import ResourceLedger

from ..economy_formatting import format_resource_ledger
from ..formatting import (
    format_building_key,
    format_planning_mode,
)


class EconomyTimelineView(ttk.Frame):
    """Starting-resource controls and construction-only ledger results."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=20)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        self._on_resources_changed: (
            Callable[[dict[str, str]], None] | None
        ) = None
        self._on_generate: Callable[[], None] | None = None
        self._resource_vars = {
            name: tk.StringVar(value="0") for name in RESOURCE_NAMES
        }
        self._context_var = tk.StringVar(
            value="Select a complete target in Build Planner."
        )
        self._mode_var = tk.StringVar(value=format_planning_mode(0))
        self._input_error_var = tk.StringVar()

        ttk.Label(
            self,
            text="Economy Timeline",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")

        context = ttk.LabelFrame(
            self, text="Planning Context", padding=10
        )
        context.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        ttk.Label(context, textvariable=self._context_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(context, textvariable=self._mode_var).grid(
            row=1, column=0, sticky="w", pady=(4, 0)
        )

        controls = ttk.LabelFrame(
            self, text="Starting Resources", padding=10
        )
        controls.grid(row=2, column=0, sticky="ew", pady=(14, 0))

        for index, name in enumerate(RESOURCE_NAMES):
            row = index // 4
            column = (index % 4) * 2
            ttk.Label(
                controls, text=name.capitalize()
            ).grid(
                row=row,
                column=column,
                sticky="w",
                padx=(0, 5),
                pady=3,
            )
            entry = ttk.Entry(
                controls,
                textvariable=self._resource_vars[name],
                width=10,
            )
            entry.grid(
                row=row,
                column=column + 1,
                sticky="w",
                padx=(0, 14),
                pady=3,
            )
            entry.bind(
                "<KeyRelease>",
                lambda _event: self._emit_resource_change(),
            )

        ttk.Label(
            controls, textvariable=self._input_error_var
        ).grid(
            row=2,
            column=0,
            columnspan=6,
            sticky="w",
            pady=(8, 0),
        )

        self._generate_button = ttk.Button(
            controls,
            text="Generate Economy Timeline",
            state="disabled",
            command=self._handle_generate,
        )
        self._generate_button.grid(
            row=2,
            column=6,
            columnspan=2,
            sticky="e",
            pady=(8, 0),
        )

        results = ttk.LabelFrame(
            self, text="Resource Ledger", padding=8
        )
        results.grid(
            row=3, column=0, sticky="nsew", pady=(14, 0)
        )
        results.columnconfigure(0, weight=1)
        results.rowconfigure(0, weight=1)

        self._text = tk.Text(
            results, wrap="word", state="disabled"
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
        on_resources_changed: Callable[[dict[str, str]], None],
        on_generate: Callable[[], None],
    ) -> None:
        self._on_resources_changed = on_resources_changed
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
            format_building_key(BuildingKey(faction, sid, level))
        )
        self._mode_var.set(format_planning_mode(override_count))

    def clear_planning_context(self) -> None:
        self._context_var.set(
            "Select a complete target in Build Planner."
        )
        self._mode_var.set(format_planning_mode(0))

    def set_generate_enabled(self, enabled: bool) -> None:
        self._generate_button.configure(
            state="normal" if enabled else "disabled"
        )

    def show_input_error(self, message: str) -> None:
        self._input_error_var.set(message)

    def clear_input_error(self) -> None:
        self._input_error_var.set("")

    def clear_ledger(self) -> None:
        self._replace(
            "Enter a starting treasury, then generate the economy timeline."
        )

    def show_ledger(self, ledger: ResourceLedger) -> None:
        self._replace(format_resource_ledger(ledger))
        self._text.see("1.0")

    def show_error(self, message: str) -> None:
        self._replace(
            "Unable to Generate Economy Timeline\n" + message
        )

    def _emit_resource_change(self) -> None:
        if self._on_resources_changed is not None:
            self._on_resources_changed(
                {
                    name: variable.get()
                    for name, variable in self._resource_vars.items()
                }
            )

    def _handle_generate(self) -> None:
        if self._on_generate is not None:
            self._on_generate()

    def _replace(self, content: str) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("end", content)
        self._text.configure(state="disabled")
