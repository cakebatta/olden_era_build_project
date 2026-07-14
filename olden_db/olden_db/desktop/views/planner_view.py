from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class PlannerView(ttk.Frame):
    """Minimal Build Planner content area for the desktop skeleton."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=24)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        heading = ttk.Label(
            self,
            text="Build Planner",
            font=("TkDefaultFont", 16, "bold"),
        )
        heading.grid(row=0, column=0, sticky="w")

        empty_state = ttk.Frame(self, padding=(0, 28, 0, 0))
        empty_state.grid(row=1, column=0, sticky="nsew")
        empty_state.columnconfigure(0, weight=1)

        instruction = ttk.Label(
            empty_state,
            text="Select a faction, building, and level to generate a build plan.",
            wraplength=560,
            justify="left",
        )
        instruction.grid(row=0, column=0, sticky="nw")

        detail = ttk.Label(
            empty_state,
            text=(
                "Target-selection controls and planning results will be added "
                "in the next functional desktop milestone."
            ),
            wraplength=560,
            justify="left",
        )
        detail.grid(row=1, column=0, sticky="nw", pady=(10, 0))
