from __future__ import annotations

from datetime import datetime
import tkinter as tk
from tkinter import ttk
from uuid import UUID

from olden_db.scenario_persistence import ScenarioSummary


_COLUMNS = ("name", "faction", "target", "modified")
_SORT_KEYS = {
    "name": lambda summary: summary.name.casefold(),
    "faction": lambda summary: summary.faction.casefold(),
    "target": lambda summary: (
        summary.target.sid.casefold(),
        summary.target.level,
    ),
    "modified": lambda summary: summary.modified_at,
}


def format_target(summary: ScenarioSummary) -> str:
    return f"{summary.target.sid} L{summary.target.level}"


def format_modified_at(value: datetime) -> str:
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def sorted_summaries(
    summaries: tuple[ScenarioSummary, ...],
    column: str,
    descending: bool = False,
) -> tuple[ScenarioSummary, ...]:
    if column not in _SORT_KEYS:
        raise ValueError(
            f"Unknown scenario-library sort column: {column!r}"
        )
    return tuple(
        sorted(
            summaries,
            key=_SORT_KEYS[column],
            reverse=descending,
        )
    )


class ScenarioLibraryDialog(tk.Toplevel):
    """Present immutable summaries and return one selected scenario ID."""

    def __init__(
        self,
        parent: tk.Misc,
        summaries: tuple[ScenarioSummary, ...],
    ) -> None:
        super().__init__(parent)
        self.title("Scenario Library")
        self.geometry("760x480")
        self.minsize(620, 360)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._summaries = tuple(summaries)
        self._by_id = {
            str(summary.scenario_id): summary
            for summary in self._summaries
        }
        self._sort_column = "modified"
        self._sort_descending = True
        self.selected_id: UUID | None = None
        self._description = tk.StringVar(value="")

        self._build()
        self._populate()
        self.bind("<Escape>", self._cancel)
        self.bind("<Return>", self._open)

        self.grab_set()
        self.after_idle(self._focus_initial_row)

    @classmethod
    def choose(
        cls,
        parent: tk.Misc,
        summaries: tuple[ScenarioSummary, ...],
    ) -> UUID | None:
        dialog = cls(parent, summaries)
        parent.wait_window(dialog)
        return dialog.selected_id

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text="Scenario Library",
            font=("TkDefaultFont", 15, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(14, 8))

        list_frame = ttk.Frame(self)
        list_frame.grid(row=1, column=0, sticky="nsew", padx=14)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(
            list_frame,
            columns=_COLUMNS,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "name": "Scenario Name",
            "faction": "Faction",
            "target": "Target Building",
            "modified": "Last Modified",
        }
        widths = {
            "name": 210,
            "faction": 120,
            "target": 190,
            "modified": 150,
        }
        for column in _COLUMNS:
            self.tree.heading(
                column,
                text=headings[column],
                command=lambda selected=column: self._sort(selected),
            )
            self.tree.column(
                column,
                width=widths[column],
                minwidth=90,
                stretch=column in ("name", "target"),
            )

        scrollbar = ttk.Scrollbar(
            list_frame,
            orient="vertical",
            command=self.tree.yview,
        )
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", self._open)

        description_frame = ttk.LabelFrame(
            self,
            text="Description",
            padding=10,
        )
        description_frame.grid(
            row=2,
            column=0,
            sticky="ew",
            padx=14,
            pady=(10, 8),
        )
        description_frame.columnconfigure(0, weight=1)
        ttk.Label(
            description_frame,
            textvariable=self._description,
            wraplength=690,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        buttons = ttk.Frame(self)
        buttons.grid(
            row=3,
            column=0,
            sticky="e",
            padx=14,
            pady=(0, 14),
        )
        ttk.Button(
            buttons,
            text="Cancel",
            command=self._cancel,
        ).grid(row=0, column=0, padx=(0, 8))
        self.open_button = ttk.Button(
            buttons,
            text="Open",
            command=self._open,
            state="disabled",
        )
        self.open_button.grid(row=0, column=1)

    def _populate(self) -> None:
        selected = self.tree.selection()
        selected_id = selected[0] if selected else None
        for item in self.tree.get_children():
            self.tree.delete(item)

        ordered = sorted_summaries(
            self._summaries,
            self._sort_column,
            self._sort_descending,
        )
        for summary in ordered:
            item_id = str(summary.scenario_id)
            self.tree.insert(
                "",
                "end",
                iid=item_id,
                values=(
                    summary.name,
                    summary.faction,
                    format_target(summary),
                    format_modified_at(summary.modified_at),
                ),
            )

        if selected_id and self.tree.exists(selected_id):
            self.tree.selection_set(selected_id)
            self.tree.focus(selected_id)
            self.tree.see(selected_id)
        else:
            self._description.set("")
            self.open_button.configure(state="disabled")

    def _focus_initial_row(self) -> None:
        rows = self.tree.get_children()
        if rows:
            item_id = rows[0]
            self.tree.selection_set(item_id)
            self.tree.focus(item_id)
            self.tree.see(item_id)
        self.tree.focus_set()

    def _sort(self, column: str) -> None:
        if self._sort_column == column:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = column
            self._sort_descending = column == "modified"
        self._populate()

    def _selection_changed(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        selected = self.tree.selection()
        if not selected:
            self._description.set("")
            self.open_button.configure(state="disabled")
            return
        summary = self._by_id[selected[0]]
        self._description.set(
            summary.description or "No description provided."
        )
        self.open_button.configure(state="normal")

    def _open(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> str:
        selected = self.tree.selection()
        if selected:
            self.selected_id = self._by_id[selected[0]].scenario_id
            self.destroy()
        return "break"

    def _cancel(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> str:
        self.selected_id = None
        self.destroy()
        return "break"

