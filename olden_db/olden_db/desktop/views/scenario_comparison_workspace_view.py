from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

from olden_db.scenario_comparison import ComparisonRole, WorkspaceId

from ..scenario_comparison_presentation import ScenarioComparisonPresentation
from .planner_view import PlannerView


_ROLE_TO_TEXT = {
    None: "Unassigned",
    ComparisonRole.LEFT: "Left",
    ComparisonRole.RIGHT: "Right",
}
_TEXT_TO_ROLE = {value: key for key, value in _ROLE_TO_TEXT.items()}


class ScenarioComparisonWorkspaceView(ttk.Frame):
    """Compose existing PlannerView panels in one horizontal workspace."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, padding=14)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._handlers: dict[str, Callable[..., None]] = {}
        self._panels: dict[WorkspaceId, tuple[ttk.Frame, ttk.Button]] = {}
        self._planner_views: dict[WorkspaceId, PlannerView] = {}
        self._label_vars: dict[WorkspaceId, tk.StringVar] = {}
        self._role_vars: dict[WorkspaceId, tk.StringVar] = {}
        self._last_presentation: ScenarioComparisonPresentation | None = None

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(
            header,
            text="Scenario Comparison Workspace",
            font=("TkDefaultFont", 16, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Button(
            header,
            text="Add Empty Scenario",
            command=lambda: self._invoke("create"),
        ).grid(row=0, column=1, sticky="e")

        self._role_summary = ttk.Label(
            self,
            text="Left: Unassigned    |    Right: Unassigned",
            justify="left",
        )
        self._role_summary.grid(row=1, column=0, sticky="w", pady=(8, 10))

        shell = ttk.Frame(self)
        shell.grid(row=2, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(0, weight=1)
        self._canvas = tk.Canvas(shell, highlightthickness=0)
        scrollbar = ttk.Scrollbar(
            shell,
            orient="horizontal",
            command=self._canvas.xview,
        )
        self._canvas.configure(xscrollcommand=scrollbar.set)
        self._canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=1, column=0, sticky="ew")

        self._content = ttk.Frame(self._canvas)
        self._content_window = self._canvas.create_window(
            (0, 0),
            window=self._content,
            anchor="nw",
        )
        self._content.bind("<Configure>", self._refresh_scroll_region)
        self._canvas.bind("<Shift-MouseWheel>", self._scroll_horizontally)

    def set_event_handlers(self, **handlers: Callable[..., None]) -> None:
        self._handlers = dict(handlers)

    def create_workspace_panel(self, workspace_id: WorkspaceId) -> PlannerView:
        existing = self._planner_views.get(workspace_id)
        if existing is not None:
            return existing

        panel = ttk.LabelFrame(self._content, padding=8, width=820)
        panel.grid(
            row=0,
            column=len(self._panels),
            sticky="ns",
            padx=(0, 12),
        )
        panel.grid_propagate(False)
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        controls = ttk.Frame(panel)
        controls.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        controls.columnconfigure(0, weight=1)

        label_var = tk.StringVar()
        label_entry = ttk.Entry(controls, textvariable=label_var)
        label_entry.grid(row=0, column=0, sticky="ew")
        label_entry.bind(
            "<Return>",
            lambda _event, wid=workspace_id: self._commit_label(wid),
        )
        label_entry.bind(
            "<FocusOut>",
            lambda _event, wid=workspace_id: self._commit_label(wid),
        )

        role_var = tk.StringVar(value="Unassigned")
        role_box = ttk.Combobox(
            controls,
            textvariable=role_var,
            values=("Unassigned", "Left", "Right"),
            state="readonly",
            width=12,
        )
        role_box.grid(row=0, column=1, padx=6)
        role_box.bind(
            "<<ComboboxSelected>>",
            lambda _event, wid=workspace_id: self._commit_role(wid),
        )

        ttk.Button(
            controls,
            text="Duplicate",
            command=lambda wid=workspace_id: self._invoke("duplicate", wid),
        ).grid(row=0, column=2, padx=3)
        remove_button = ttk.Button(
            controls,
            text="Remove",
            command=lambda wid=workspace_id: self._invoke("remove", wid),
        )
        remove_button.grid(row=0, column=3, padx=3)

        planner_view = PlannerView(panel)
        planner_view.grid(row=1, column=0, sticky="nsew")

        self._panels[workspace_id] = (panel, remove_button)
        self._planner_views[workspace_id] = planner_view
        self._label_vars[workspace_id] = label_var
        self._role_vars[workspace_id] = role_var
        return planner_view

    def remove_workspace_panel(self, workspace_id: WorkspaceId) -> None:
        pair = self._panels.pop(workspace_id, None)
        if pair is not None:
            pair[0].destroy()
        self._planner_views.pop(workspace_id, None)
        self._label_vars.pop(workspace_id, None)
        self._role_vars.pop(workspace_id, None)

    def render_collection(
        self,
        presentation: ScenarioComparisonPresentation,
    ) -> None:
        if presentation == self._last_presentation:
            return

        member_ids = {member.workspace_id for member in presentation.members}
        for workspace_id in tuple(self._panels):
            if workspace_id not in member_ids:
                self.remove_workspace_panel(workspace_id)

        for column, member in enumerate(presentation.members):
            panel, remove_button = self._panels[member.workspace_id]
            panel.grid_configure(column=column)
            self._label_vars[member.workspace_id].set(member.label)
            self._role_vars[member.workspace_id].set(
                _ROLE_TO_TEXT[member.comparison_role]
            )
            remove_button.configure(
                state="normal" if member.can_remove else "disabled"
            )

        labels = {
            member.workspace_id: member.label
            for member in presentation.members
        }
        self._role_summary.configure(
            text=(
                f"Left: {labels.get(presentation.left_workspace_id, 'Unassigned')}"
                "    |    "
                f"Right: {labels.get(presentation.right_workspace_id, 'Unassigned')}"
            )
        )
        self._last_presentation = presentation
        self.after_idle(self._refresh_scroll_region)

    def _invoke(self, name: str, *args: object) -> None:
        handler = self._handlers.get(f"on_{name}")
        if handler is not None:
            handler(*args)

    def _commit_label(self, workspace_id: WorkspaceId) -> None:
        self._invoke(
            "label",
            workspace_id,
            self._label_vars[workspace_id].get(),
        )

    def _commit_role(self, workspace_id: WorkspaceId) -> None:
        self._invoke(
            "role",
            workspace_id,
            _TEXT_TO_ROLE[self._role_vars[workspace_id].get()],
        )

    def _refresh_scroll_region(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        bounds = self._canvas.bbox("all")
        if bounds is not None:
            self._canvas.configure(scrollregion=bounds)

    def _scroll_horizontally(self, event: tk.Event[tk.Misc]) -> str:
        self._canvas.xview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"
