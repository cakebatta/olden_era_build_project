from __future__ import annotations
from collections.abc import Callable
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

class ScenarioManagerView(ttk.Frame):
    COMMANDS=(("New","new"),("Open","open"),("Save","save"),("Save As","save_as"),
              ("Rename","rename"),("Duplicate","duplicate"),("Delete","delete"),
              ("Import","import"),("Export","export"))
    def __init__(self,parent):
        super().__init__(parent,padding=(8,6)); self.columnconfigure(0,weight=1)
        self._handlers={}; self._suspend=False; self._title=tk.StringVar(value="No active scenario")
        ttk.Label(self,textvariable=self._title,font=("TkDefaultFont",11,"bold")).grid(row=0,column=0,sticky="w")
        bar=ttk.Frame(self);bar.grid(row=1,column=0,sticky="ew",pady=4)
        for i,(label,key) in enumerate(self.COMMANDS):
            ttk.Button(bar,text=label,command=lambda k=key:self._invoke(k)).grid(row=0,column=i,padx=(0,3))
        box=ttk.LabelFrame(self,text="Scenario Document",padding=6);box.grid(row=2,column=0,sticky="ew");box.columnconfigure(1,weight=1)
        self._name=tk.StringVar();self._description=tk.StringVar()
        ttk.Label(box,text="Name").grid(row=0,column=0,sticky="w");ttk.Entry(box,textvariable=self._name).grid(row=0,column=1,sticky="ew")
        ttk.Label(box,text="Description").grid(row=1,column=0,sticky="w");ttk.Entry(box,textvariable=self._description).grid(row=1,column=1,sticky="ew")
        ttk.Label(box,text="Notes").grid(row=2,column=0,sticky="nw");self._notes=tk.Text(box,height=3,wrap="word");self._notes.grid(row=2,column=1,sticky="ew")
        self._name.trace_add("write",self._edited);self._description.trace_add("write",self._edited);self._notes.bind("<KeyRelease>",self._edited)
    def set_handlers(self,**handlers): self._handlers=handlers
    def _invoke(self,key):
        if key in self._handlers:self._handlers[key]()
    def set_title(self,value): self._title.set(value)
    def apply_metadata(self,name,description,notes):
        self._suspend=True
        try:
            self._name.set(name);self._description.set(description);self._notes.delete("1.0","end");self._notes.insert("1.0",notes)
        finally:self._suspend=False
    def metadata(self): return self._name.get(),self._description.get(),self._notes.get("1.0","end-1c")
    def _edited(self,*_):
        if not self._suspend and "edited" in self._handlers:self._handlers["edited"]()
    def choose_unsaved_action(self,name):
        r=messagebox.askyesnocancel("Unsaved Scenario",f"{name} has unsaved work.\n\nSave before continuing?",parent=self.winfo_toplevel())
        return "save" if r is True else "discard" if r is False else "cancel"
    def choose_scenario(self,listing):
        if listing.diagnostics:
            messagebox.showwarning("Scenario Library","Some scenario files could not be loaded.\n\n"+"\n".join(f"{d.filename}: {d.message}" for d in listing.diagnostics[:8]),parent=self.winfo_toplevel())
        if not listing.scenarios:
            messagebox.showinfo("Scenario Library","No saved scenarios are available.",parent=self.winfo_toplevel());return None
        text="\n".join(f"{i+1}. {s.name} — {s.modified_at:%Y-%m-%d %H:%M} — {s.faction}/{s.target.sid} L{s.target.level}" for i,s in enumerate(listing.scenarios))
        n=simpledialog.askinteger("Open Scenario","Select scenario number:\n\n"+text,minvalue=1,maxvalue=len(listing.scenarios),parent=self.winfo_toplevel())
        return None if n is None else listing.scenarios[n-1]
    def ask_name(self,title,initial): return simpledialog.askstring(title,"Scenario name:",initialvalue=initial,parent=self.winfo_toplevel())
    def confirm_delete(self,name): return messagebox.askyesno("Delete Scenario",f'Delete "{name}" from the local library?\n\nCurrent content will remain as an unsaved copy.',parent=self.winfo_toplevel())
    def choose_conflict_copy(self): return messagebox.askyesno("Scenario Conflict","Stored content changed after opening.\n\nSave current work as a new copy?",parent=self.winfo_toplevel())
    def import_path(self): return filedialog.askopenfilename(title="Import Scenario",filetypes=(("Scenario JSON","*.json"),("All files","*.*")),parent=self.winfo_toplevel())
    def export_path(self,name): return filedialog.asksaveasfilename(title="Export Scenario",defaultextension=".json",initialfile=name,filetypes=(("Scenario JSON","*.json"),),parent=self.winfo_toplevel())
    def confirm_overwrite(self,name): return messagebox.askyesno("Replace Export",f"{name} already exists. Replace it?",parent=self.winfo_toplevel())
    def show_error(self,message): messagebox.showerror("Scenario Manager",message,parent=self.winfo_toplevel())
    def show_info(self,message): messagebox.showinfo("Scenario Manager",message,parent=self.winfo_toplevel())
