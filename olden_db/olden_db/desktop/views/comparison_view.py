from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from olden_db.comparison import PlanComparison
from ..formatting import format_building_key, format_game_date, format_resource_cost

class _Side(ttk.LabelFrame):
    def __init__(self,parent,side,title,handlers):
        super().__init__(parent,text=title,padding=10); self.side=side; self.handlers=handlers; self.columnconfigure(1,weight=1)
        self.f=tk.StringVar(); self.b=tk.StringVar(); self.l=tk.StringVar(); self.mode=tk.StringVar(value='Planning mode: Canonical')
        ttk.Label(self,text='Faction').grid(row=0,column=0,sticky='w'); self.fc=ttk.Combobox(self,textvariable=self.f,state='readonly'); self.fc.grid(row=0,column=1,sticky='ew'); self.fc.bind('<<ComboboxSelected>>',lambda e:handlers['faction'](side,self.f.get()))
        ttk.Label(self,text='Building SID').grid(row=1,column=0,sticky='w'); self.bc=ttk.Combobox(self,textvariable=self.b,state='disabled'); self.bc.grid(row=1,column=1,sticky='ew'); self.bc.bind('<<ComboboxSelected>>',lambda e:handlers['building'](side,self.b.get()))
        ttk.Label(self,text='Level').grid(row=2,column=0,sticky='w'); self.lc=ttk.Combobox(self,textvariable=self.l,state='disabled'); self.lc.grid(row=2,column=1,sticky='ew'); self.lc.bind('<<ComboboxSelected>>',lambda e:handlers['level'](side,int(self.l.get())))
        h=ttk.Frame(self); h.grid(row=3,column=0,columnspan=2,sticky='ew',pady=(8,2)); h.columnconfigure(0,weight=1); ttk.Label(h,textvariable=self.mode).grid(row=0,column=0,sticky='w'); ttk.Button(h,text='Reset Scenario',command=lambda:handlers['reset'](side)).grid(row=0,column=1)
        self.canvas=tk.Canvas(self,height=140,highlightthickness=0); sb=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview); self.canvas.configure(yscrollcommand=sb.set); self.canvas.grid(row=4,column=0,columnspan=2,sticky='ew'); sb.grid(row=4,column=2,sticky='ns')
        self.inner=ttk.Frame(self.canvas); self.win=self.canvas.create_window((0,0),window=self.inner,anchor='nw'); self.inner.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all'))); self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.win,width=e.width)); self.clear_candidates()
    def set_factions(self,x): self.fc.configure(values=x)
    def set_buildings(self,x): self.b.set(''); self.bc.configure(values=x,state='readonly' if x else 'disabled'); self.l.set(''); self.lc.configure(values=(),state='disabled')
    def set_levels(self,x): self.l.set(''); self.lc.configure(values=tuple(map(str,x)),state='readonly' if x else 'disabled')
    def set_candidates(self,buildings,scenario):
        self._clear(); overrides={o.building:o.available_at_start for o in scenario.starting_building_overrides}
        for r,b in enumerate(buildings):
            v=tk.BooleanVar(value=overrides.get(b.key,b.constructed_on_start)); text=f'{b.key.sid} level {b.key.level} — Canonical: '+('available' if b.constructed_on_start else 'construct')
            ttk.Checkbutton(self.inner,text=text,variable=v,command=lambda k=b.key,var=v:self.handlers['scenario'](self.side,k,var.get())).grid(row=r,column=0,sticky='w')
    def clear_candidates(self): self._clear(); ttk.Label(self.inner,text='Select a faction to configure starting buildings.').grid(row=0,column=0,sticky='w')
    def set_mode(self,n): self.mode.set('Planning mode: Canonical' if n==0 else f'Planning mode: Custom Starting State\nOverrides: {n}')
    def _clear(self):
        for w in self.inner.winfo_children(): w.destroy()

class ComparisonView(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent,padding=18); self.columnconfigure((0,1),weight=1); self.rowconfigure(3,weight=1); self.handlers={}; self.left=self.right=None
        ttk.Label(self,text='Plan Comparison',font=('TkDefaultFont',16,'bold')).grid(row=0,column=0,columnspan=2,sticky='w')
        self.button=ttk.Button(self,text='Compare Plans',state='disabled',command=self._compare); self.button.grid(row=2,column=0,columnspan=2,pady=8)
        box=ttk.LabelFrame(self,text='Comparison Results',padding=8); box.grid(row=3,column=0,columnspan=2,sticky='nsew'); box.columnconfigure(0,weight=1); box.rowconfigure(0,weight=1)
        self.text=tk.Text(box,wrap='word',state='disabled'); sb=ttk.Scrollbar(box,orient='vertical',command=self.text.yview); self.text.configure(yscrollcommand=sb.set); self.text.grid(row=0,column=0,sticky='nsew'); sb.grid(row=0,column=1,sticky='ns'); self.text.tag_configure('h',font=('TkDefaultFont',11,'bold')); self.clear_results()
    def set_event_handlers(self,**h):
        self.handlers=h; m={'faction':h['on_faction_changed'],'building':h['on_building_changed'],'level':h['on_level_changed'],'scenario':h['on_scenario_changed'],'reset':h['on_reset_scenario']}; self.left=_Side(self,'left','Left Plan',m); self.right=_Side(self,'right','Right Plan',m); self.left.grid(row=1,column=0,sticky='nsew',padx=(0,5)); self.right.grid(row=1,column=1,sticky='nsew',padx=(5,0))
    def set_factions(self,x): self.left.set_factions(x); self.right.set_factions(x)
    def set_buildings(self,s,x): getattr(self,s).set_buildings(x)
    def set_levels(self,s,x): getattr(self,s).set_levels(x)
    def set_scenario_candidates(self,s,b,sc): getattr(self,s).set_candidates(b,sc)
    def set_mode(self,s,n): getattr(self,s).set_mode(n)
    def set_compare_enabled(self,e): self.button.configure(state='normal' if e else 'disabled')
    def clear_results(self): self._replace('Select complete left and right targets, then compare.')
    def show_error(self,m): self._replace('Unable to Compare Plans\n'+m)
    def show_comparison(self,c:PlanComparison):
        left='\n'.join((f'Target: {format_building_key(c.left_plan.target)}',f'Completion date: {format_game_date(c.left_plan.completion_date)}',f'Total cost: {format_resource_cost(c.left_plan.total_cost)}',f'Construction actions: {c.left_plan.build_actions}'))
        right='\n'.join((f'Target: {format_building_key(c.right_plan.target)}',f'Completion date: {format_game_date(c.right_plan.completion_date)}',f'Total cost: {format_resource_cost(c.right_plan.total_cost)}',f'Construction actions: {c.right_plan.build_actions}'))
        added='None' if not c.added_buildings else '\n'.join(format_building_key(x) for x in c.added_buildings); removed='None' if not c.removed_buildings else '\n'.join(format_building_key(x) for x in c.removed_buildings)
        summary='\n'.join((f'Identical: {"Yes" if c.identical else "No"}',f'Action-count delta: {c.action_delta}',f'Completion-date delta: {c.completion_date_delta}',f'Resource delta: {format_resource_cost(c.resource_delta)}','','Added buildings:',added,'','Removed buildings:',removed))
        self._replace(''); self._section('Left Plan',left); self._section('Right Plan',right); self._section('Comparison Summary',summary)
    def show_decision_summary(self,observations:tuple[str,...])->None:
        self._section('Decision Summary','\n'.join(f'{i}. {text}' for i,text in enumerate(observations,start=1)))
    def _compare(self):
        cb=self.handlers.get('on_compare'); cb() if cb else None
    def _replace(self,s): self.text.configure(state='normal'); self.text.delete('1.0','end'); self.text.insert('end',s); self.text.configure(state='disabled')
    def _section(self,h,b): self.text.configure(state='normal'); self.text.insert('end',h+'\n','h'); self.text.insert('end',b+'\n'); self.text.configure(state='disabled')
