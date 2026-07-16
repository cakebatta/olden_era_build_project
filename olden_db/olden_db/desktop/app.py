from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from olden_db.query import PlanningQueryService

from .comparison_state import ComparisonState
from .economy_state import EconomyTimelineState
from .presenters.comparison_presenter import ComparisonPresenter
from .presenters.economy_presenter import EconomyTimelinePresenter
from .presenters.planner_presenter import PlannerPresenter
from .state import PlannerState
from .views.comparison_view import ComparisonView
from .views.economy_view import EconomyTimelineView
from .views.planner_view import PlannerView

APPLICATION_TITLE = "Olden Era Build Planner"


class DesktopApplication:
    def __init__(self, root, service):
        self.root = root
        self.status_text = tk.StringVar(value="Starting…")
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

    def _configure(self):
        self.root.title(APPLICATION_TITLE)
        self.root.geometry("1100x760")
        self.root.minsize(820, 560)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)

    def _shell(self):
        shell = ttk.Frame(self.root, padding=12)
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
            pady=(4, 14),
        )

        nav = ttk.Frame(shell, padding=(8, 12))
        nav.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        ttk.Label(
            nav,
            text="Navigation",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        ttk.Button(
            nav,
            text="Build Planner",
            command=lambda: self.show("planner"),
        ).grid(row=1, column=0, sticky="ew")
        ttk.Button(
            nav,
            text="Economy Timeline",
            command=lambda: self.show("economy"),
        ).grid(row=2, column=0, sticky="ew", pady=2)
        ttk.Button(
            nav,
            text="Plan Comparison",
            command=lambda: self.show("comparison"),
        ).grid(row=3, column=0, sticky="ew", pady=2)

        content = ttk.Frame(shell, relief="groove", padding=1)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        planner = PlannerView(content)
        comparison = ComparisonView(content)
        economy = EconomyTimelineView(content)
        for view in (planner, comparison, economy):
            view.grid(row=0, column=0, sticky="nsew")

        self.work = {
            "planner": planner,
            "comparison": comparison,
            "economy": economy,
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
            pady=(12, 0),
        )
        return planner, comparison, economy

    def show(self, name):
        if name == "economy":
            self.economy_presenter.refresh_context()
        self.work[name].tkraise()

    def set_status(self, message):
        self.status_text.set(message)


def run_desktop_application():
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
