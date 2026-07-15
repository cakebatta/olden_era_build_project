from __future__ import annotations
import tkinter as tk
from tkinter import messagebox, ttk
from olden_db.query import PlanningQueryService
from .comparison_state import ComparisonState
from .presenters.comparison_presenter import ComparisonPresenter
from .presenters.planner_presenter import PlannerPresenter
from .state import PlannerState
from .views.comparison_view import ComparisonView
from .views.planner_view import PlannerView
APPLICATION_TITLE='Olden Era Build Planner'
class DesktopApplication:
    def __init__(self,root,service):
        self.root=root; self.status_text=tk.StringVar(value='Starting…'); self._configure(); p,c=self._shell(); self.pp=PlannerPresenter(service,PlannerState(),p,self.set_status); self.cp=ComparisonPresenter(service,ComparisonState(),c,self.set_status); self.pp.initialize(); self.cp.initialize(); self.show('planner')
    def _configure(self): self.root.title(APPLICATION_TITLE); self.root.geometry('1100x760'); self.root.minsize(820,560); self.root.columnconfigure(0,weight=1); self.root.rowconfigure(0,weight=1); self.root.protocol('WM_DELETE_WINDOW',self.root.destroy)
    def _shell(self):
        shell=ttk.Frame(self.root,padding=12); shell.grid(row=0,column=0,sticky='nsew'); shell.columnconfigure(1,weight=1); shell.rowconfigure(1,weight=1); ttk.Label(shell,text=APPLICATION_TITLE,font=('TkDefaultFont',18,'bold')).grid(row=0,column=0,columnspan=2,sticky='ew',pady=(4,14))
        nav=ttk.Frame(shell,padding=(8,12)); nav.grid(row=1,column=0,sticky='nsw',padx=(0,12)); ttk.Label(nav,text='Navigation',font=('TkDefaultFont',10,'bold')).grid(row=0,column=0,sticky='w',pady=(0,10)); ttk.Button(nav,text='Build Planner',command=lambda:self.show('planner')).grid(row=1,column=0,sticky='ew'); ttk.Button(nav,text='Plan Comparison',command=lambda:self.show('comparison')).grid(row=2,column=0,sticky='ew',pady=2)
        content=ttk.Frame(shell,relief='groove',padding=1); content.grid(row=1,column=1,sticky='nsew'); content.columnconfigure(0,weight=1); content.rowconfigure(0,weight=1); p=PlannerView(content); c=ComparisonView(content); p.grid(row=0,column=0,sticky='nsew'); c.grid(row=0,column=0,sticky='nsew'); self.work={'planner':p,'comparison':c}; ttk.Label(shell,textvariable=self.status_text,relief='sunken',anchor='w',padding=(8,5)).grid(row=2,column=0,columnspan=2,sticky='ew',pady=(12,0)); return p,c
    def show(self,name): self.work[name].tkraise()
    def set_status(self,m): self.status_text.set(m)
def run_desktop_application():
    root=tk.Tk(); root.withdraw()
    try:s=PlanningQueryService.from_default_game_data()
    except (FileNotFoundError,OSError,ValueError) as e: messagebox.showerror(APPLICATION_TITLE,'The application could not load the required canonical game data.\n\n'+str(e),parent=root); root.destroy(); return
    DesktopApplication(root,s); root.deiconify(); root.mainloop()
