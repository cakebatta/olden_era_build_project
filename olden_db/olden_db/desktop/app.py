from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from olden_db.query import PlanningQueryService

from .presenters.planner_presenter import PlannerPresenter
from .state import PlannerState
from .views.planner_view import PlannerView

APPLICATION_TITLE = "Olden Era Build Planner"


class DesktopApplication:
    """Own the primary window and top-level desktop dependency wiring."""

    def __init__(
        self,
        root: tk.Tk,
        service: PlanningQueryService,
    ) -> None:
        self._root = root
        self._service = service
        self._state = PlannerState()
        self._status_text = tk.StringVar(value="Starting…")

        self._configure_root()
        planner_view = self._build_application_shell()

        self._presenter = PlannerPresenter(
            service=self._service,
            state=self._state,
            view=planner_view,
            set_status=self.set_status,
        )
        self._presenter.initialize()

    def _configure_root(self) -> None:
        self._root.title(APPLICATION_TITLE)
        self._root.geometry("900x600")
        self._root.minsize(680, 440)
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)
        self._root.protocol("WM_DELETE_WINDOW", self.close)

    def _build_application_shell(self) -> PlannerView:
        shell = ttk.Frame(self._root, padding=12)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        title = ttk.Label(
            shell,
            text=APPLICATION_TITLE,
            font=("TkDefaultFont", 18, "bold"),
        )
        title.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=8,
            pady=(4, 14),
        )

        navigation = ttk.Frame(shell, padding=(8, 12))
        navigation.grid(row=1, column=0, sticky="nsw", padx=(0, 12))
        navigation.columnconfigure(0, weight=1)

        ttk.Label(
            navigation,
            text="Navigation",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        active_module = ttk.Label(
            navigation,
            text="Build Planner",
            relief="sunken",
            padding=(12, 8),
            anchor="w",
        )
        active_module.grid(row=1, column=0, sticky="ew")

        content = ttk.Frame(shell, relief="groove", padding=1)
        content.grid(row=1, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(0, weight=1)

        planner_view = PlannerView(content)
        planner_view.grid(row=0, column=0, sticky="nsew")

        status = ttk.Label(
            shell,
            textvariable=self._status_text,
            relief="sunken",
            anchor="w",
            padding=(8, 5),
        )
        status.grid(
            row=2,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(12, 0),
        )

        return planner_view

    def set_status(self, message: str) -> None:
        self._status_text.set(message)

    def close(self) -> None:
        self._root.destroy()


def run_desktop_application() -> None:
    """Create one root window, initialize the Query Layer, and run the UI."""

    root = tk.Tk()
    root.withdraw()

    try:
        service = PlanningQueryService.from_default_game_data()
    except (FileNotFoundError, OSError, ValueError) as exc:
        messagebox.showerror(
            APPLICATION_TITLE,
            "The application could not load the required canonical game data.\n\n"
            f"{exc}",
            parent=root,
        )
        root.destroy()
        return

    DesktopApplication(root, service)
    root.deiconify()
    root.mainloop()
