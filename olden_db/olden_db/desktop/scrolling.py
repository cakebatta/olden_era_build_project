from __future__ import annotations

from collections.abc import Callable
import tkinter as tk
from tkinter import ttk

WHEEL_SEQUENCES = ("<MouseWheel>", "<Button-4>", "<Button-5>")


def _wheel_units(event: tk.Event[tk.Misc]) -> int:
    if getattr(event, "num", None) == 4:
        return -1
    if getattr(event, "num", None) == 5:
        return 1
    delta = getattr(event, "delta", 0)
    if delta == 0:
        return 0
    return -1 if delta > 0 else 1


class ScrollableWorkspace(ttk.Frame):
    """A vertically scrollable workspace with scoped wheel bindings.

    Wheel handlers are attached only while the workspace is active and are
    removed when another workspace becomes active. No global bind_all calls
    are used.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        padding: int = 0,
    ) -> None:
        super().__init__(parent)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.canvas = tk.Canvas(
            self,
            highlightthickness=0,
            borderwidth=0,
        )
        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
            width=18,
            borderwidth=1,
            relief="raised",
        )
        self.canvas.configure(
            yscrollcommand=self.scrollbar.set
        )
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")

        self.content = ttk.Frame(
            self.canvas,
            padding=padding,
        )
        self.content.columnconfigure(0, weight=1)
        self._window = self.canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )
        self.content.bind(
            "<Configure>",
            self._sync_scrollregion,
        )
        self.canvas.bind(
            "<Configure>",
            self._sync_width,
        )

        self._active = False
        self._binding_ids: list[
            tuple[tk.Misc, str, str]
        ] = []

    def activate(self) -> None:
        self._active = True
        self._refresh_bindings()
        self.canvas.focus_set()

    def deactivate(self) -> None:
        self._active = False
        self._clear_bindings()

    def refresh_bindings(self) -> None:
        if self._active:
            self._refresh_bindings()

    def scroll_to_top(self) -> None:
        self.canvas.yview_moveto(0.0)

    def _refresh_bindings(self) -> None:
        self._clear_bindings()
        for widget in self._walk_widgets(self):
            for sequence in WHEEL_SEQUENCES:
                func_id = widget.bind(
                    sequence,
                    self._handle_wheel,
                    add="+",
                )
                if func_id:
                    self._binding_ids.append(
                        (widget, sequence, func_id)
                    )

    def _clear_bindings(self) -> None:
        for widget, sequence, func_id in self._binding_ids:
            try:
                widget.unbind(sequence, func_id)
            except tk.TclError:
                pass
        self._binding_ids.clear()

    def _handle_wheel(
        self,
        event: tk.Event[tk.Misc],
    ) -> str | None:
        if not self._active:
            return None

        widget = event.widget
        if isinstance(widget, (tk.Text, tk.Listbox)):
            first, last = widget.yview()
            units = _wheel_units(event)
            if (
                units < 0 and first > 0.0
            ) or (
                units > 0 and last < 1.0
            ):
                return None

        units = _wheel_units(event)
        if units:
            self.canvas.yview_scroll(units, "units")
            return "break"
        return None

    def _sync_scrollregion(
        self,
        _event: tk.Event[tk.Misc],
    ) -> None:
        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )
        if self._active:
            self.after_idle(self._refresh_bindings)

    def _sync_width(
        self,
        event: tk.Event[tk.Misc],
    ) -> None:
        self.canvas.itemconfigure(
            self._window,
            width=event.width,
        )

    @classmethod
    def _walk_widgets(
        cls,
        widget: tk.Misc,
    ) -> tuple[tk.Misc, ...]:
        descendants: list[tk.Misc] = [widget]
        for child in widget.winfo_children():
            descendants.extend(cls._walk_widgets(child))
        return tuple(descendants)
