from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from olden_db.database import LoadedGameData, load_default_game_data
from olden_db.planning_execution import PlanningExecutionCoordinator
from olden_db.planning_workspace import PlanningWorkspace
from olden_db.query import PlanningQueryService
from olden_db.scenario_persistence import (
    LocalScenarioRepository,
    validate_document_against_game_data,
)

from .app_paths import application_data_root
from .comparison_state import ComparisonState
from .economy_state import EconomyTimelineState
from .presenters.comparison_presenter import ComparisonPresenter
from .inline_validation_controller import InlineValidationScenarioController
from .scenario_presenters import (
    ScenarioAwareEconomyPresenter,
    ScenarioAwarePlannerPresenter,
)
from .scrolling import ScrollableWorkspace
from .state import PlannerState
from .views.comparison_view import ComparisonView
from .views.economy_view import EconomyTimelineView
from .views.planner_view import PlannerView
from .views.scenario_manager_view import ScenarioManagerView


APPLICATION_TITLE = "Olden Era Build Planner"
DEFAULT_ROOT_GEOMETRY = "1100x700"
ROOT_MINIMUM_SIZE = (960, 640)


def scenario_shortcut_bindings(windowing_system: str):
    """Return platform-appropriate lifecycle shortcut registrations."""
    modifier = "Command" if windowing_system == "aqua" else "Control"
    return (
        (f"<{modifier}-n>", "new"),
        (f"<{modifier}-o>", "open"),
        (f"<{modifier}-s>", "save"),
        (f"<{modifier}-Shift-S>", "save_as"),
    )


class DesktopApplication:
    """Own the responsive shell, navigation, and workspace lifecycle."""

    def __init__(
        self,
        root: tk.Tk,
        service: PlanningQueryService,
        canonical_data: LoadedGameData,
    ) -> None:
        self.root = root
        self.status_text = tk.StringVar(value="Starting…")
        self._active_workspace: str | None = None
        self._configure()

        (
            manager_view,
            planner_view,
            comparison_view,
            economy_view,
        ) = self._shell()
        self.scenario_manager_view = manager_view

        planner_state = PlannerState()
        economy_state = EconomyTimelineState()
        self.planning_workspace = PlanningWorkspace.create()
        self.planning_execution_coordinator = PlanningExecutionCoordinator(
            service
        )

        self.economy_presenter = ScenarioAwareEconomyPresenter(
            service,
            planner_state,
            economy_state,
            economy_view,
            self.set_status,
        )
        self.planner_presenter = ScenarioAwarePlannerPresenter(
            service,
            self.planning_workspace,
            self.planning_execution_coordinator,
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

        repository = LocalScenarioRepository(
            application_data_root(),
            canonical_validator=lambda document: (
                validate_document_against_game_data(
                    document,
                    canonical_data,
                )
            ),
        )
        self.scenario_controller = InlineValidationScenarioController(
            repository,
            planner_state,
            economy_state,
            self.planner_presenter,
            self.economy_presenter,
            manager_view,
            self.set_status,
        )

        self.planner_presenter.set_persisted_change_handler(
            self.scenario_controller.on_user_edit
        )
        self.economy_presenter.set_persisted_change_handler(
            self.scenario_controller.on_user_edit
        )

        self.planner_presenter.initialize()
        self.comparison_presenter.initialize()
        self.economy_presenter.initialize()
        self.scenario_controller.initialize()
        self._bind_shortcuts()
        self.show("planner")

    def _configure(self) -> None:
        self.root.title(APPLICATION_TITLE)
        self.root.geometry(DEFAULT_ROOT_GEOMETRY)
        self.root.minsize(*ROOT_MINIMUM_SIZE)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def _bind_shortcuts(self) -> None:
        windowing_system = self.root.tk.call("tk", "windowingsystem")
        for sequence, command in scenario_shortcut_bindings(
            windowing_system
        ):
            self.root.bind_all(
                sequence,
                lambda _event, key=command: (
                    self._dispatch_scenario_command(key)
                ),
            )

    def _dispatch_scenario_command(self, key):
        """Route a shortcut through the same view intent as visible commands."""
        self.scenario_manager_view.invoke_command(key)
        return "break"

    def _shell(
        self,
    ) -> tuple[
        ScenarioManagerView,
        PlannerView,
        ComparisonView,
        EconomyTimelineView,
    ]:
        shell = ttk.Frame(self.root, padding=10)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(1, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell)
        header.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(2, 8),
        )
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text=APPLICATION_TITLE,
            font=("TkDefaultFont", 18, "bold"),
        ).grid(
            row=0,
            column=0,
            sticky="ew",
            pady=(0, 6),
        )

        manager = ScenarioManagerView(header)
        manager.grid(row=1, column=0, sticky="ew")

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

        return manager, planner, comparison, economy

    def show(self, name: str) -> None:
        if name not in self.workspaces:
            raise ValueError(f"Unknown workspace: {name!r}")

        if self._active_workspace is not None:
            self.workspaces[self._active_workspace].deactivate()

        if name == "economy":
            self.economy_presenter.refresh_context()

        workspace = self.workspaces[name]
        workspace.tkraise()
        workspace.activate()
        self._active_workspace = name

    def set_status(self, message: str) -> None:
        self.status_text.set(message)

    def close(self) -> None:
        if not self.scenario_controller.can_close():
            return
        for workspace in self.workspaces.values():
            workspace.deactivate()
        self.root.destroy()


def run_desktop_application() -> None:
    root = tk.Tk()
    root.withdraw()
    try:
        canonical_data = load_default_game_data()
        service = PlanningQueryService.from_default_game_data()
    except (FileNotFoundError, OSError, ValueError) as exc:
        messagebox.showerror(
            APPLICATION_TITLE,
            "The application could not load required canonical game data."
            "\n\n"
            + str(exc),
            parent=root,
        )
        root.destroy()
        return

    DesktopApplication(root, service, canonical_data)
    root.deiconify()
    root.mainloop()
