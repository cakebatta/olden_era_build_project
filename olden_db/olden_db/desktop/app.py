from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, ttk
from olden_db.query import PlanningQueryService
from olden_db.scenario_persistence import LocalScenarioRepository, validate_document_against_game_data
from .app_paths import application_data_root
from .comparison_state import ComparisonState
from .economy_state import EconomyTimelineState
from .presenters.comparison_presenter import ComparisonPresenter
from .scenario_presenters import ScenarioAwareEconomyPresenter, ScenarioAwarePlannerPresenter
from .scenario_controller import ScenarioController
from .scrolling import ScrollableWorkspace
from .state import PlannerState
from .views.comparison_view import ComparisonView
from .views.economy_view import EconomyTimelineView
from .views.planner_view import PlannerView
from .views.scenario_manager_view import ScenarioManagerView

APPLICATION_TITLE="Olden Era Build Planner";DEFAULT_ROOT_GEOMETRY="1180x780";ROOT_MINIMUM_SIZE=(960,640)

class DesktopApplication:
    def __init__(self,root,service):
        self.root=root;self.status_text=tk.StringVar(value="Starting…");self._active_workspace=None
        self._configure();manager_view,planner_view,comparison_view,economy_view=self._shell()
        planner_state=PlannerState();economy_state=EconomyTimelineState()
        self.economy_presenter=ScenarioAwareEconomyPresenter(service,planner_state,economy_state,economy_view,self.set_status)
        self.planner_presenter=ScenarioAwarePlannerPresenter(service,planner_state,planner_view,self.set_status,
            on_context_changed=self.economy_presenter.on_planning_context_changed)
        self.comparison_presenter=ComparisonPresenter(service,ComparisonState(),comparison_view,self.set_status)
        repository=LocalScenarioRepository(application_data_root(),
            canonical_validator=lambda document:validate_document_against_game_data(document,service._data))
        self.scenario_controller=ScenarioController(repository,planner_state,economy_state,
            self.planner_presenter,self.economy_presenter,manager_view,self.set_status)
        self.planner_presenter.set_persisted_change_handler(self.scenario_controller.on_user_edit)
        self.economy_presenter.set_persisted_change_handler(self.scenario_controller.on_user_edit)
        self.planner_presenter.initialize();self.comparison_presenter.initialize();self.economy_presenter.initialize()
        self.scenario_controller.initialize();self._bind_shortcuts();self.show("planner")
    def _configure(self):
        self.root.title(APPLICATION_TITLE);self.root.geometry(DEFAULT_ROOT_GEOMETRY);self.root.minsize(*ROOT_MINIMUM_SIZE)
        self.root.columnconfigure(0,weight=1);self.root.rowconfigure(0,weight=1);self.root.protocol("WM_DELETE_WINDOW",self.close)
    def _bind_shortcuts(self):
        self.root.bind_all("<Control-n>",lambda _e:self.scenario_controller.new())
        self.root.bind_all("<Control-o>",lambda _e:self.scenario_controller.open())
        self.root.bind_all("<Control-s>",lambda _e:self.scenario_controller.save())
        self.root.bind_all("<Control-Shift-S>",lambda _e:self.scenario_controller.save_as())
    def _shell(self):
        shell=ttk.Frame(self.root,padding=10);shell.grid(row=0,column=0,sticky="nsew")
        shell.columnconfigure(1,weight=1);shell.rowconfigure(2,weight=1)
        ttk.Label(shell,text=APPLICATION_TITLE,font=("TkDefaultFont",18,"bold")).grid(row=0,column=0,columnspan=2,sticky="ew",pady=(2,6))
        manager=ScenarioManagerView(shell);manager.grid(row=1,column=0,columnspan=2,sticky="ew",pady=(0,8))
        nav=ttk.Frame(shell,padding=(6,8));nav.grid(row=2,column=0,sticky="nsw",padx=(0,10))
        ttk.Label(nav,text="Navigation",font=("TkDefaultFont",10,"bold")).grid(row=0,column=0,sticky="w",pady=(0,8))
        for row,(label,key) in enumerate((("Build Planner","planner"),("Economy Timeline","economy"),("Plan Comparison","comparison")),1):
            ttk.Button(nav,text=label,command=lambda k=key:self.show(k)).grid(row=row,column=0,sticky="ew",pady=2)
        content=ttk.Frame(shell,relief="groove",padding=1);content.grid(row=2,column=1,sticky="nsew")
        content.columnconfigure(0,weight=1);content.rowconfigure(0,weight=1)
        planner_shell=ScrollableWorkspace(content);comparison_shell=ScrollableWorkspace(content);economy_shell=ScrollableWorkspace(content)
        for w in (planner_shell,comparison_shell,economy_shell):w.grid(row=0,column=0,sticky="nsew")
        planner=PlannerView(planner_shell.content);comparison=ComparisonView(comparison_shell.content);economy=EconomyTimelineView(economy_shell.content)
        for v in (planner,comparison,economy):v.grid(row=0,column=0,sticky="nsew")
        self.workspaces={"planner":planner_shell,"comparison":comparison_shell,"economy":economy_shell}
        ttk.Label(shell,textvariable=self.status_text,relief="sunken",anchor="w",padding=(8,5)).grid(row=3,column=0,columnspan=2,sticky="ew",pady=(10,0))
        return manager,planner,comparison,economy
    def show(self,name):
        if self._active_workspace is not None:self.workspaces[self._active_workspace].deactivate()
        if name=="economy":self.economy_presenter.refresh_context()
        workspace=self.workspaces[name];workspace.tkraise();workspace.activate();self._active_workspace=name
    def set_status(self,message):self.status_text.set(message)
    def close(self):
        if not self.scenario_controller.can_close():return
        for workspace in self.workspaces.values():workspace.deactivate()
        self.root.destroy()

def run_desktop_application():
    root=tk.Tk();root.withdraw()
    try:service=PlanningQueryService.from_default_game_data()
    except (FileNotFoundError,OSError,ValueError) as exc:
        messagebox.showerror(APPLICATION_TITLE,"The application could not load required canonical game data.\n\n"+str(exc),parent=root);root.destroy();return
    DesktopApplication(root,service);root.deiconify();root.mainloop()
