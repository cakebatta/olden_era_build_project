from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk


class PlannerView(ttk.Frame):
    """Build Planner target-selection controls and instructional state."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=24)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._faction_var = tk.StringVar()
        self._building_var = tk.StringVar()
        self._level_var = tk.StringVar()
        self._on_faction_changed: Callable[[str], None] | None = None
        self._on_building_changed: Callable[[str], None] | None = None
        self._on_level_changed: Callable[[int], None] | None = None
        self._on_generate_plan: Callable[[], None] | None = None

        ttk.Label(self, text="Build Planner", font=("TkDefaultFont", 16, "bold")).grid(row=0, column=0, sticky="w")
        controls = ttk.LabelFrame(self, text="Target Selection", padding=16)
        controls.grid(row=1, column=0, sticky="ew", pady=(18, 0))
        controls.columnconfigure(1, weight=1)

        ttk.Label(controls, text="Faction").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=5)
        self._faction_selector = ttk.Combobox(controls, textvariable=self._faction_var, state="readonly")
        self._faction_selector.grid(row=0, column=1, sticky="ew", pady=5)
        self._faction_selector.bind("<<ComboboxSelected>>", self._handle_faction_event)

        ttk.Label(controls, text="Building SID").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=5)
        self._building_selector = ttk.Combobox(controls, textvariable=self._building_var, state="disabled")
        self._building_selector.grid(row=1, column=1, sticky="ew", pady=5)
        self._building_selector.bind("<<ComboboxSelected>>", self._handle_building_event)

        ttk.Label(controls, text="Level").grid(row=2, column=0, sticky="w", padx=(0, 12), pady=5)
        self._level_selector = ttk.Combobox(controls, textvariable=self._level_var, state="disabled")
        self._level_selector.grid(row=2, column=1, sticky="ew", pady=5)
        self._level_selector.bind("<<ComboboxSelected>>", self._handle_level_event)

        self._generate_button = ttk.Button(controls, text="Generate Plan", command=self._handle_generate_plan, state="disabled")
        self._generate_button.grid(row=3, column=1, sticky="e", pady=(14, 0))

        empty_state = ttk.Frame(self, padding=(0, 28, 0, 0))
        empty_state.grid(row=2, column=0, sticky="nsew")
        empty_state.columnconfigure(0, weight=1)
        ttk.Label(empty_state, text="Select a faction, building, and level to generate a build plan.", wraplength=560, justify="left").grid(row=0, column=0, sticky="nw")
        ttk.Label(empty_state, text="Plan generation will be added in the next desktop milestone.", wraplength=560, justify="left").grid(row=1, column=0, sticky="nw", pady=(10, 0))

    def set_event_handlers(self, *, on_faction_changed: Callable[[str], None], on_building_changed: Callable[[str], None], on_level_changed: Callable[[int], None], on_generate_plan: Callable[[], None]) -> None:
        self._on_faction_changed = on_faction_changed
        self._on_building_changed = on_building_changed
        self._on_level_changed = on_level_changed
        self._on_generate_plan = on_generate_plan

    def set_factions(self, factions: tuple[str, ...]) -> None:
        self._faction_selector.configure(values=factions)

    def set_buildings(self, buildings: tuple[str, ...]) -> None:
        self._building_var.set("")
        self._building_selector.configure(values=buildings, state="readonly" if buildings else "disabled")

    def set_levels(self, levels: tuple[int, ...]) -> None:
        self._level_var.set("")
        self._level_selector.configure(values=tuple(str(level) for level in levels), state="readonly" if levels else "disabled")

    def clear_building_selection(self) -> None:
        self._building_var.set("")
        self._building_selector.configure(values=(), state="disabled")

    def clear_level_selection(self) -> None:
        self._level_var.set("")
        self._level_selector.configure(values=(), state="disabled")

    def set_generate_enabled(self, enabled: bool) -> None:
        self._generate_button.configure(state="normal" if enabled else "disabled")

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
