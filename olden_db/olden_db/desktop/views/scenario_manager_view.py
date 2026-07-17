from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from .scenario_library_dialog import ScenarioLibraryDialog


class ScenarioManagerView(ttk.Frame):
    """Present scenario metadata and emit lifecycle-command intent."""

    PRIMARY_COMMANDS = (
        ("New", "new"),
        ("Open", "open"),
        ("Save", "save"),
    )
    SECONDARY_COMMANDS = (
        ("Save As…", "save_as", "save_as"),
        ("Rename…", "rename", ""),
        ("Duplicate…", "duplicate", ""),
    )
    TRANSFER_COMMANDS = (
        ("Import…", "import", ""),
        ("Export…", "export", ""),
    )
    DESTRUCTIVE_COMMANDS = (("Delete…", "delete", ""),)

    def __init__(self, parent):
        super().__init__(parent, padding=(8, 6))
        self.columnconfigure(0, weight=1)

        self._handlers = {}
        self._suspend = False
        windowing_system = self.tk.call("tk", "windowingsystem")
        self._shortcut_labels = {
            "save_as": (
                "Command+Shift+S"
                if windowing_system == "aqua"
                else "Ctrl+Shift+S"
            )
        }
        self._command_enabled = {
            key: True
            for _label, key in self.PRIMARY_COMMANDS
        }
        self._command_enabled.update({
            key: True
            for group in (
                self.SECONDARY_COMMANDS,
                self.TRANSFER_COMMANDS,
                self.DESTRUCTIVE_COMMANDS,
            )
            for _label, key, _accelerator in group
        })
        self._primary_buttons = {}
        self._menu_indices = {}
        self._title = tk.StringVar(value="No active scenario")

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        header.columnconfigure(0, weight=1)

        self._title_label = ttk.Label(
            header,
            textvariable=self._title,
            font=("TkDefaultFont", 11, "bold"),
            anchor="w",
            width=1,
        )
        self._title_label.grid(
            row=0,
            column=0,
            sticky="ew",
            padx=(0, 8),
        )

        for column, (label, key) in enumerate(
            self.PRIMARY_COMMANDS,
            start=1,
        ):
            button = ttk.Button(
                header,
                text=label,
                command=lambda command=key: self.invoke_command(command),
                takefocus=True,
            )
            button.grid(row=0, column=column, padx=(0, 3))
            self._primary_buttons[key] = button

        self._scenario_menu = tk.Menu(self, tearoff=False)
        self._build_scenario_menu()
        self._menu_button = ttk.Menubutton(
            header,
            text="Scenario ▾",
            menu=self._scenario_menu,
            takefocus=True,
        )
        self._menu_button.grid(row=0, column=4)

        box = ttk.LabelFrame(
            self,
            text="Scenario Document",
            padding=6,
        )
        box.grid(row=1, column=0, sticky="ew")
        box.columnconfigure(1, weight=1)

        self._validation_labels = {}
        self._validation_widgets = {}
        style = ttk.Style(self)
        style.configure(
            "ScenarioInvalid.TEntry",
            fieldbackground="#fff3cd",
        )

        self._name_var = tk.StringVar()
        self._description_var = tk.StringVar()

        ttk.Label(box, text="Name").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self._name_entry = ttk.Entry(
            box,
            textvariable=self._name_var,
        )
        self._name_entry.grid(
            row=0,
            column=1,
            sticky="ew",
        )
        self._name_validation = ttk.Label(
            box,
            text="",
            foreground="#8a4b00",
            anchor="w",
        )
        self._name_validation.grid(
            row=1,
            column=1,
            sticky="ew",
            pady=(1, 3),
        )
        ttk.Label(box, text="Description").grid(
            row=2,
            column=0,
            sticky="w",
        )
        self._description_entry = ttk.Entry(
            box,
            textvariable=self._description_var,
        )
        self._description_entry.grid(
            row=2,
            column=1,
            sticky="ew",
        )
        self._description_validation = ttk.Label(
            box,
            text="",
            foreground="#8a4b00",
            anchor="w",
        )
        self._description_validation.grid(
            row=3,
            column=1,
            sticky="ew",
            pady=(1, 3),
        )
        ttk.Label(box, text="Notes").grid(
            row=4,
            column=0,
            sticky="nw",
        )
        self._notes = tk.Text(
            box,
            height=3,
            wrap="word",
            highlightthickness=1,
        )
        self._notes.grid(row=4, column=1, sticky="ew")
        self._notes_validation = ttk.Label(
            box,
            text="",
            foreground="#8a4b00",
            anchor="w",
        )
        self._notes_validation.grid(
            row=5,
            column=1,
            sticky="ew",
            pady=(1, 0),
        )

        self._validation_labels.update({
            "name": self._name_validation,
            "description": self._description_validation,
            "notes": self._notes_validation,
        })
        self._validation_widgets.update({
            "name": self._name_entry,
            "description": self._description_entry,
            "notes": self._notes,
        })

        self._name_var.trace_add("write", self._edited)
        self._description_var.trace_add("write", self._edited)
        self._notes.bind("<KeyRelease>", self._edited)

    def _build_scenario_menu(self) -> None:
        groups = (
            self.SECONDARY_COMMANDS,
            self.TRANSFER_COMMANDS,
            self.DESTRUCTIVE_COMMANDS,
        )
        for group_number, group in enumerate(groups):
            if group_number:
                self._scenario_menu.add_separator()
            for label, key, accelerator in group:
                self._scenario_menu.add_command(
                    label=label,
                    accelerator=self._shortcut_labels.get(
                        accelerator, accelerator
                    ),
                    command=lambda command=key: self.invoke_command(command),
                )
                self._menu_indices[key] = self._scenario_menu.index("end")

    def set_handlers(self, **handlers):
        self._handlers = handlers

    def invoke_command(self, key):
        """Emit one command intent through the controller-provided handler."""
        if not self._command_enabled.get(key, False):
            return False
        handler = self._handlers.get(key)
        if handler is None:
            return False
        handler()
        return True

    def set_command_enabled(self, key, enabled):
        """Keep a command's visible entry points in the same state."""
        if key not in self._command_enabled:
            raise KeyError(key)
        self._command_enabled[key] = bool(enabled)
        state = "normal" if enabled else "disabled"
        button = self._primary_buttons.get(key)
        if button is not None:
            button.configure(state=state)
        menu_index = self._menu_indices.get(key)
        if menu_index is not None:
            self._scenario_menu.entryconfigure(menu_index, state=state)

    def set_title(self, value):
        self._title.set(value)

    def apply_metadata(self, name, description, notes):
        self._suspend = True
        try:
            self._name_var.set(name)
            self._description_var.set(description)
            self._notes.delete("1.0", "end")
            self._notes.insert("1.0", notes)
        finally:
            self._suspend = False

    def metadata(self):
        return (
            self._name_var.get(),
            self._description_var.get(),
            self._notes.get("1.0", "end-1c"),
        )

    def _edited(self, *_):
        if not self._suspend and "edited" in self._handlers:
            self._handlers["edited"]()


    def set_validation_state(self, path, message):
        """Render controller-provided validation metadata without validating."""
        for field, label in self._validation_labels.items():
            label.configure(text="")
            widget = self._validation_widgets[field]
            if isinstance(widget, ttk.Entry):
                widget.configure(style="TEntry")
            else:
                widget.configure(highlightthickness=0)

        field = (path or "").split(".", 1)[0]
        label = self._validation_labels.get(field)
        widget = self._validation_widgets.get(field)
        if label is None or widget is None:
            return

        label.configure(text=f"⚠ {message}")
        if isinstance(widget, ttk.Entry):
            widget.configure(style="ScenarioInvalid.TEntry")
        else:
            widget.configure(
                highlightthickness=1,
                highlightbackground="#b36b00",
                highlightcolor="#b36b00",
            )
        self.after_idle(widget.focus_set)

    def choose_unsaved_action(self, name):
        result = messagebox.askyesnocancel(
            "Unsaved Scenario",
            f"{name} has unsaved work.\n\nSave before continuing?",
            parent=self.winfo_toplevel(),
        )
        if result is True:
            return "save"
        if result is False:
            return "discard"
        return "cancel"

    def choose_scenario(self, listing):
        if listing.diagnostics:
            messagebox.showwarning(
                "Scenario Library",
                "Some scenario files could not be loaded.\n\n"
                + "\n".join(
                    f"{diagnostic.filename}: {diagnostic.message}"
                    for diagnostic in listing.diagnostics[:8]
                ),
                parent=self.winfo_toplevel(),
            )
        if not listing.scenarios:
            messagebox.showinfo(
                "Scenario Library",
                "No saved scenarios are available.",
                parent=self.winfo_toplevel(),
            )
            return None
        selected_id = ScenarioLibraryDialog.choose(
            self.winfo_toplevel(),
            listing.scenarios,
        )
        if selected_id is None:
            return None
        return next(
            summary
            for summary in listing.scenarios
            if summary.scenario_id == selected_id
        )

    def ask_name(self, title, initial):
        return simpledialog.askstring(
            title,
            "Scenario name:",
            initialvalue=initial,
            parent=self.winfo_toplevel(),
        )

    def confirm_delete(self, name):
        return messagebox.askyesno(
            "Delete Scenario",
            f'Delete "{name}" from the local library?\n\n'
            "Current content will remain as an unsaved copy.",
            parent=self.winfo_toplevel(),
        )

    def choose_conflict_copy(self):
        return messagebox.askyesno(
            "Scenario Conflict",
            "Stored content changed after opening.\n\n"
            "Save current work as a new copy?",
            parent=self.winfo_toplevel(),
        )

    def import_path(self):
        return filedialog.askopenfilename(
            title="Import Scenario",
            filetypes=(
                ("Scenario JSON", "*.json"),
                ("All files", "*.*"),
            ),
            parent=self.winfo_toplevel(),
        )

    def export_path(self, name):
        return filedialog.asksaveasfilename(
            title="Export Scenario",
            defaultextension=".json",
            initialfile=name,
            filetypes=(("Scenario JSON", "*.json"),),
            parent=self.winfo_toplevel(),
        )

    def confirm_overwrite(self, name):
        return messagebox.askyesno(
            "Replace Export",
            f"{name} already exists. Replace it?",
            parent=self.winfo_toplevel(),
        )

    def show_error(self, message):
        messagebox.showerror(
            "Scenario Manager",
            message,
            parent=self.winfo_toplevel(),
        )

    def show_info(self, message):
        messagebox.showinfo(
            "Scenario Manager",
            message,
            parent=self.winfo_toplevel(),
        )
