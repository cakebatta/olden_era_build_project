from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from olden_db.query import PlanningQueryService

from .comparison_state import ComparisonState
from .economy_state import EconomyTimelineState
from .presenters.comparison_presenter import ComparisonPresenter
from .presenters.economy_presenter import EconomyTimelinePresenter
from .presenters.planner_presenter import PlannerPresenter
from .scrolling import ScrollableWorkspace
from .state import PlannerState
from .views.comparison_view import ComparisonView
from .views.economy_view import EconomyTimelineView
from .views.planner_view import PlannerView

APPLICATION_TITLE = "Olden Era Build Planner"
DEFAULT_ROOT_GEOMETRY = "1100x700"
ROOT_MINIMUM_SIZE = (960, 640)


class DesktopApplication:
    """Own the responsive shell, navigation, and workspace lifecycle."""

    def __init__(
        self,
        root: tk.Tk,
        service: PlanningQueryService,
    ) -> None:
        self.root = root
        self.status_text = tk.StringVar(value="Starting…")
        self._active_workspace: str | None = None
        self._configure()

        planner_view, comparison_view, economy_view = self._shell()
        planner_state = PlannerState()

        self.economy_presenter = EconomyTimelinePresenter(
            service,
            planner_state,
            EconomyTimelineState(),
            economy_view,
            self.set_status,
        )
        self.planner_presenter = PlannerPresenter(
            service,
            planner_state,
            planner_view,
            self.set_status,
            on_context_changed=(
                self.economy_presenter.on_planning_context_changed
            ),
        )
        self.comparison_presenter = ComparisonPresenter(
            service,
            ComparisonState(),
            comparison_view,
            self.set_status,
        )

        self.planner_presenter.initialize()
        self.comparison_presenter.initialize()
        self.economy_presenter.initialize()
        self.show("planner")

    def _configure(self) -> None:
        self.root.title(APPLICATION_TITLE)
        self.root.geometry(DEFAULT_ROOT_GEOMETRY)
        self.root.minsize(*ROOT_MINIMUM_SIZE)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _shell(
        self,
    ) -> tuple[PlannerView, ComparisonView, EconomyTimelineView]:
        shell = ttk.Frame(self.root, padding=10)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        ttk.Label(
            shell,
            text=APPLICATION_TITLE,
            font=("TkDefaultFont", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 10),
        )

        navigation = ttk.Frame(shell, padding=(6, 8))
        navigation.grid(
            row=1,
            column=0,
            sticky="nsw",
            padx=(0, 10),
        )
        navigation.columnconfigure(0, weight=1)
        ttk.Label(
            navigation,
            text="Navigation",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="w",
            pady=(0, 8),
        )

        ttk.Button(
            navigation,
            text="Build Planner",
            command=lambda: self.show("planner"),
        ).grid(row=1, column=0, sticky="ew")
        ttk.Button(
            navigation,
            text="Economy Timeline",
            command=lambda: self.show("economy"),
        ).grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Button(
            navigation,
            text="Plan Comparison",
            command=lambda: self.show("comparison"),
        ).grid(row=3, column=0, sticky="ew", pady=2)

        content = ttk.Frame(
            shell,
            relief="groove",
            padding=1,
        )
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        planner_shell = ScrollableWorkspace(content)
        comparison_shell = ScrollableWorkspace(content)
        economy_shell = ScrollableWorkspace(content)
        for workspace in (
            planner_shell,
            comparison_shell,
            economy_shell,
        ):
            workspace.grid(row=0, column=0, sticky="nsew")

        planner = PlannerView(planner_shell.content)
        comparison = ComparisonView(comparison_shell.content)
        economy = EconomyTimelineView(economy_shell.content)
        for view in (planner, comparison, economy):
            view.grid(row=0, column=0, sticky="nsew")

        self.workspaces = {
            "planner": planner_shell,
            "comparison": comparison_shell,
            "economy": economy_shell,
        }

        ttk.Label(
            shell,
            textvariable=self.status_text,
            relief="sunken",
            anchor="w",
            padding=(8, 5),
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )
        return planner, comparison, economy

    def show(self, name: str) -> None:
        if name not in self.workspaces:
            raise ValueError(f"Unknown workspace: {name!r}")

        if self._active_workspace is not None:
            self.workspaces[
                self._active_workspace
            ].deactivate()

        if name == "economy":
            self.economy_presenter.refresh_context()

        workspace = self.workspaces[name]
        workspace.tkraise()
        workspace.activate()
        self._active_workspace = name

    def set_status(self, message: str) -> None:
        self.status_text.set(message)

    def close(self) -> None:
        for workspace in self.workspaces.values():
            workspace.deactivate()
        self.root.destroy()


def run_desktop_application() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        service = PlanningQueryService.from_default_game_data()
    except (FileNotFoundError, OSError, ValueError) as exc:
        messagebox.showerror(
            APPLICATION_TITLE,
            "The application could not load the required canonical game data."
            "\n\n"
            + str(exc),
            parent=root,
        )
        root.destroy()
        return

    DesktopApplication(root, service)
    root.deiconify()
    root.mainloop()
