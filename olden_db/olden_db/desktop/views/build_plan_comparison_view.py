from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ..build_plan_comparison_presentation import BuildPlanComparisonPresentation


class BuildPlanComparisonView(ttk.LabelFrame):
    """Read-only presentation of immutable accepted-plan comparison facts."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, text="Build Plan Comparison", padding=8)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self._last_presentation = None
        self._heading = tk.StringVar(value="Comparison unavailable")
        self._detail = tk.StringVar(
            value="Assign both Left and Right comparison workspaces."
        )
        self._summary = tk.StringVar(value="")
        self._resource_summary = tk.StringVar(value="")

        ttk.Label(
            self,
            textvariable=self._heading,
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            self,
            textvariable=self._detail,
            justify="left",
            wraplength=1100,
        ).grid(row=1, column=0, sticky="ew", pady=(3, 5))

        summary = ttk.LabelFrame(self, text="Comparison Summary", padding=8)
        summary.grid(row=2, column=0, sticky="ew")
        summary.columnconfigure(0, weight=1)
        ttk.Label(
            summary,
            textvariable=self._summary,
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            summary,
            textvariable=self._resource_summary,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))

        table_shell = ttk.LabelFrame(
            self,
            text="Aligned Construction Actions",
            padding=8,
        )
        table_shell.grid(row=3, column=0, sticky="nsew", pady=(6, 0))
        table_shell.columnconfigure(0, weight=1)
        table_shell.rowconfigure(0, weight=1)

        columns = (
            "position",
            "left_building",
            "left_level",
            "left_date",
            "relationship",
            "right_building",
            "right_level",
            "right_date",
        )
        self._rows = ttk.Treeview(
            table_shell,
            columns=columns,
            show="headings",
            selectmode="browse",
            height=10,
        )
        headings = (
            ("position", "#", 48),
            ("left_building", "Left building", 180),
            ("left_level", "Level", 62),
            ("left_date", "Date", 150),
            ("relationship", "Relationship", 105),
            ("right_building", "Right building", 180),
            ("right_level", "Level", 62),
            ("right_date", "Date", 150),
        )
        for column, text, width in headings:
            self._rows.heading(column, text=text)
            self._rows.column(
                column,
                width=width,
                minwidth=48,
                stretch=column in {
                    "left_building",
                    "left_date",
                    "right_building",
                    "right_date",
                },
                anchor="w",
            )
        scrollbar = tk.Scrollbar(
            table_shell,
            orient="vertical",
            command=self._rows.yview,
            width=18,
            relief="raised",
        )
        self._rows.configure(yscrollcommand=scrollbar.set)
        self._rows.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self._rows.tag_configure("matched", background="#E9F4E9")
        self._rows.tag_configure("different", background="#FFF1D6")
        self._rows.tag_configure("left_only", background="#F8E3E3")
        self._rows.tag_configure("right_only", background="#E4ECFA")

        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        for column in range(3):
            actions.columnconfigure(column, weight=1)
        self._shared = self._make_action_list(actions, "Shared actions", 0)
        self._left_only = self._make_action_list(actions, "Left-only actions", 1)
        self._right_only = self._make_action_list(actions, "Right-only actions", 2)

    def _make_action_list(self, parent, title: str, column: int):
        frame = ttk.LabelFrame(parent, text=title, padding=6)
        frame.grid(row=0, column=column, sticky="nsew", padx=(0, 8))
        frame.columnconfigure(0, weight=1)
        tree = ttk.Treeview(
            frame,
            columns=("building", "level", "date"),
            show="headings",
            height=4,
        )
        for key, label, width in (
            ("building", "Building", 170),
            ("level", "Level", 55),
            ("date", "Date", 130),
        ):
            tree.heading(key, text=label)
            tree.column(key, width=width, minwidth=48, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew")
        return tree

    def render_comparison(
        self,
        presentation: BuildPlanComparisonPresentation,
    ) -> None:
        if presentation == self._last_presentation:
            return
        selected = self._rows.selection()
        previous_position = selected[0] if selected else None

        self._heading.set(presentation.heading)
        self._detail.set(presentation.detail)
        summary = presentation.summary
        if summary is None:
            self._summary.set("")
            self._resource_summary.set("")
        else:
            self._summary.set(
                f"{summary.equivalent_text}\n"
                f"{summary.left_label}: completion {summary.left_completion_date}; "
                f"{summary.left_construction_count} actions\n"
                f"{summary.right_label}: completion {summary.right_completion_date}; "
                f"{summary.right_construction_count} actions\n"
                f"Completion-date delta: {summary.completion_date_delta} days; "
                f"construction-count delta: {summary.construction_count_delta}"
            )
            self._resource_summary.set(
                "Final cumulative resource deltas: "
                + ", ".join(
                    f"{item.resource_name}: {item.value_text}"
                    for item in presentation.resource_deltas
                )
            )

        for item in self._rows.get_children():
            self._rows.delete(item)
        for row in presentation.aligned_steps:
            left = row.left
            right = row.right
            self._rows.insert(
                "",
                "end",
                iid=str(row.position),
                values=(
                    row.position,
                    left.building_name if left else "",
                    left.level_text if left else "",
                    left.date_text if left else "",
                    row.relationship,
                    right.building_name if right else "",
                    right.level_text if right else "",
                    right.date_text if right else "",
                ),
                tags=(row.relationship_key,),
            )

        self._render_actions(self._shared, presentation.shared_actions)
        self._render_actions(self._left_only, presentation.left_only_actions)
        self._render_actions(self._right_only, presentation.right_only_actions)

        if previous_position and self._rows.exists(previous_position):
            self._rows.selection_set(previous_position)
            self._rows.focus(previous_position)
            self._rows.see(previous_position)
        elif presentation.aligned_steps:
            first = str(presentation.aligned_steps[0].position)
            self._rows.selection_set(first)
            self._rows.focus(first)

        self._last_presentation = presentation

    @staticmethod
    def _render_actions(tree, actions) -> None:
        for item in tree.get_children():
            tree.delete(item)
        for index, action in enumerate(actions, start=1):
            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    action.building_name,
                    action.level_text,
                    action.date_text,
                ),
            )
