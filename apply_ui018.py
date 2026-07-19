from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"


def replace_once(text: str, old: str, new: str, description: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"Expected exactly one {description} block, found {count}. "
            "Confirm the checkout is synchronized with UI-017 main."
        )
    return text.replace(old, new, 1)


def main() -> None:
    text = VIEW.read_text(encoding="utf-8")

    text = replace_once(
        text,
        '''        self._diagnostics: tuple[
            PlannerDiagnosticPresentation, ...
        ] = ()
''',
        '''        self._diagnostics: tuple[
            PlannerDiagnosticPresentation, ...
        ] = ()
        self._diagnostic_items: list[tk.Frame] = []
        self._diagnostic_wrap_labels: list[ttk.Label] = []
''',
        "diagnostic state",
    )

    text = replace_once(
        text,
        '''        self._diagnostic_canvas = tk.Canvas(
            self._diagnostic_panel,
            height=150,
            takefocus=True,
            highlightthickness=2,
            highlightcolor="SystemHighlight",
            highlightbackground="SystemButtonFace",
        )
        self._diagnostic_scrollbar = ttk.Scrollbar(
            self._diagnostic_panel,
            orient="vertical",
            command=self._diagnostic_canvas.yview,
        )
        self._diagnostic_canvas.configure(
            yscrollcommand=self._diagnostic_scrollbar.set
        )
        self._diagnostic_canvas.grid(row=0, column=0, sticky="nsew")
        self._diagnostic_scrollbar.grid(row=0, column=1, sticky="ns")
        self._diagnostic_content = ttk.Frame(self._diagnostic_canvas)
        self._diagnostic_window = self._diagnostic_canvas.create_window(
            (0, 0),
            window=self._diagnostic_content,
            anchor="nw",
        )
        self._diagnostic_content.bind(
            "<Configure>",
            lambda _event: self._diagnostic_canvas.configure(
                scrollregion=self._diagnostic_canvas.bbox("all")
            ),
        )
        self._diagnostic_canvas.bind(
            "<Configure>",
            lambda event: self._diagnostic_canvas.itemconfigure(
                self._diagnostic_window,
                width=event.width,
            ),
        )
''',
        '''        diagnostic_style = ttk.Style(self)
        diagnostic_style.configure("Diagnostic.Error.TLabel", foreground="#9F1D20")
        diagnostic_style.configure("Diagnostic.Warning.TLabel", foreground="#8A5A00")
        diagnostic_style.configure("Diagnostic.Information.TLabel", foreground="#1F5A7A")

        canvas_background = diagnostic_style.lookup("TFrame", "background")
        self._diagnostic_canvas = tk.Canvas(
            self._diagnostic_panel,
            height=180,
            takefocus=True,
            highlightthickness=2,
            highlightcolor="SystemHighlight",
            highlightbackground=canvas_background or "SystemButtonFace",
            background=canvas_background or "SystemButtonFace",
        )
        self._diagnostic_scrollbar = ttk.Scrollbar(
            self._diagnostic_panel,
            orient="vertical",
            command=self._diagnostic_canvas.yview,
        )
        self._diagnostic_canvas.configure(
            yscrollcommand=self._set_diagnostic_scrollbar
        )
        self._diagnostic_canvas.grid(row=0, column=0, sticky="nsew")
        self._diagnostic_scrollbar.grid(row=0, column=1, sticky="ns")
        self._diagnostic_scrollbar.grid_remove()
        self._diagnostic_content = ttk.Frame(self._diagnostic_canvas)
        self._diagnostic_window = self._diagnostic_canvas.create_window(
            (0, 0),
            window=self._diagnostic_content,
            anchor="nw",
        )
        self._diagnostic_content.bind(
            "<Configure>",
            self._update_diagnostic_scroll_region,
        )
        self._diagnostic_canvas.bind(
            "<Configure>",
            self._resize_diagnostic_content,
        )
        self._diagnostic_canvas.bind("<Up>", self._focus_previous_diagnostic)
        self._diagnostic_canvas.bind("<Down>", self._focus_next_diagnostic)
        self._diagnostic_canvas.bind("<Home>", self._focus_first_diagnostic)
        self._diagnostic_canvas.bind("<End>", self._focus_last_diagnostic)
        self._diagnostic_canvas.bind("<Prior>", self._page_diagnostics_up)
        self._diagnostic_canvas.bind("<Next>", self._page_diagnostics_down)
        self._diagnostic_canvas.bind("<MouseWheel>", self._scroll_diagnostics)
        self._diagnostic_canvas.bind("<Button-4>", self._scroll_diagnostics)
        self._diagnostic_canvas.bind("<Button-5>", self._scroll_diagnostics)

        ttk.Label(
            self._diagnostic_panel,
            text=(
                "Read-only. Use Up/Down, Home/End, or Page Up/Page Down "
                "to review diagnostics."
            ),
            justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))
''',
        "diagnostic canvas",
    )

    start = text.index("    def set_diagnostics(")
    end = text.index("    def set_diagnostic_inspector_expanded", start)
    replacement = '''    def set_diagnostics(
        self,
        diagnostics: tuple[PlannerDiagnosticPresentation, ...],
    ) -> None:
        self._diagnostics = tuple(diagnostics)
        for widget in self._diagnostic_content.winfo_children():
            widget.destroy()
        self._diagnostic_items.clear()
        self._diagnostic_wrap_labels.clear()
        self._diagnostic_canvas.yview_moveto(0.0)

        if not self._diagnostics:
            empty_state = ttk.Frame(self._diagnostic_content, padding=(18, 22))
            empty_state.grid(row=0, column=0, sticky="nsew")
            empty_state.columnconfigure(0, weight=1)
            ttk.Label(
                empty_state,
                text="[i] No diagnostics",
                font=("TkDefaultFont", 11, "bold"),
                justify="center",
                style="Diagnostic.Information.TLabel",
            ).grid(row=0, column=0)
            ttk.Label(
                empty_state,
                text="Generate a plan to review planner-provided explanations.",
                justify="center",
            ).grid(row=1, column=0, pady=(6, 0))
            self._diagnostic_content.columnconfigure(0, weight=1)
            self.after_idle(self._update_diagnostic_scrollbar)
            return

        style_by_severity = {
            DiagnosticSeverity.ERROR: "Diagnostic.Error.TLabel",
            DiagnosticSeverity.WARNING: "Diagnostic.Warning.TLabel",
            DiagnosticSeverity.INFORMATION: "Diagnostic.Information.TLabel",
        }
        self._diagnostic_content.columnconfigure(0, weight=1)

        for row, diagnostic in enumerate(self._diagnostics):
            item = tk.Frame(
                self._diagnostic_content,
                padx=10,
                pady=9,
                takefocus=True,
                borderwidth=1,
                relief="solid",
                highlightthickness=2,
                highlightcolor="SystemHighlight",
                highlightbackground="SystemButtonFace",
            )
            item.grid(
                row=row,
                column=0,
                sticky="ew",
                padx=(2, 6),
                pady=(2 if row == 0 else 5, 2),
            )
            item.columnconfigure(1, weight=1)
            self._bind_diagnostic_navigation(item)
            self._diagnostic_items.append(item)

            marker = _DIAGNOSTIC_MARKERS[diagnostic.severity]
            severity_style = style_by_severity[diagnostic.severity]
            severity_label = ttk.Label(
                item,
                text=f"{marker} {diagnostic.severity.value}",
                font=("TkDefaultFont", 9, "bold"),
                style=severity_style,
                justify="left",
            )
            severity_label.grid(row=0, column=0, sticky="nw", padx=(0, 10))
            title_label = ttk.Label(
                item,
                text=diagnostic.title,
                font=("TkDefaultFont", 10, "bold"),
                justify="left",
            )
            title_label.grid(row=0, column=1, sticky="ew")

            explanation_label = ttk.Label(
                item,
                text=diagnostic.explanation,
                justify="left",
                anchor="w",
                wraplength=1,
            )
            explanation_label.grid(
                row=1,
                column=0,
                columnspan=2,
                sticky="ew",
                pady=(7, 0),
            )
            self._diagnostic_wrap_labels.append(explanation_label)

            for widget in (severity_label, title_label, explanation_label):
                widget.bind("<MouseWheel>", self._scroll_diagnostics)
                widget.bind("<Button-4>", self._scroll_diagnostics)
                widget.bind("<Button-5>", self._scroll_diagnostics)

        self.after_idle(self._refresh_diagnostic_layout)

    def _bind_diagnostic_navigation(self, item: tk.Frame) -> None:
        item.bind("<Up>", self._focus_previous_diagnostic)
        item.bind("<Down>", self._focus_next_diagnostic)
        item.bind("<Home>", self._focus_first_diagnostic)
        item.bind("<End>", self._focus_last_diagnostic)
        item.bind("<Prior>", self._page_diagnostics_up)
        item.bind("<Next>", self._page_diagnostics_down)
        item.bind("<MouseWheel>", self._scroll_diagnostics)
        item.bind("<Button-4>", self._scroll_diagnostics)
        item.bind("<Button-5>", self._scroll_diagnostics)

    def _refresh_diagnostic_layout(self) -> None:
        self.update_idletasks()
        self._resize_diagnostic_content()
        self._update_diagnostic_scrollbar()

    def _resize_diagnostic_content(
        self,
        event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        width = int(event.width) if event is not None else self._diagnostic_canvas.winfo_width()
        width = max(180, width)
        self._diagnostic_canvas.itemconfigure(self._diagnostic_window, width=width)
        wraplength = max(140, width - 48)
        for label in self._diagnostic_wrap_labels:
            label.configure(wraplength=wraplength)
        self.after_idle(self._update_diagnostic_scrollbar)

    def _update_diagnostic_scroll_region(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        bounds = self._diagnostic_canvas.bbox("all")
        if bounds is not None:
            self._diagnostic_canvas.configure(scrollregion=bounds)
        self._update_diagnostic_scrollbar()

    def _set_diagnostic_scrollbar(self, first: str, last: str) -> None:
        self._diagnostic_scrollbar.set(first, last)
        self._update_diagnostic_scrollbar(float(first), float(last))

    def _update_diagnostic_scrollbar(
        self,
        first: float | None = None,
        last: float | None = None,
    ) -> None:
        if first is None or last is None:
            first, last = self._diagnostic_canvas.yview()
        if first <= 0.0 and last >= 1.0:
            self._diagnostic_scrollbar.grid_remove()
        else:
            self._diagnostic_scrollbar.grid()

'''
    text = text[:start] + replacement + text[end:]

    text = replace_once(
        text,
        '''    def _scroll_diagnostics(self, event: tk.Event[tk.Misc]) -> str:
        if getattr(event, "num", None) == 4:
            units = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            units = -1 if delta > 0 else 1
        self._diagnostic_canvas.yview_scroll(units, "units")
        return "break"
''',
        '''    def _page_diagnostics_up(self, _event: tk.Event[tk.Misc]) -> str:
        self._diagnostic_canvas.yview_scroll(-1, "pages")
        return "break"

    def _page_diagnostics_down(self, _event: tk.Event[tk.Misc]) -> str:
        self._diagnostic_canvas.yview_scroll(1, "pages")
        return "break"

    def _scroll_diagnostics(self, event: tk.Event[tk.Misc]) -> str:
        first, last = self._diagnostic_canvas.yview()
        if first <= 0.0 and last >= 1.0:
            return "break"

        if getattr(event, "num", None) == 4:
            units = -1
        elif getattr(event, "num", None) == 5:
            units = 1
        else:
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return "break"
            magnitude = max(1, abs(delta) // 120)
            units = -magnitude if delta > 0 else magnitude

        self._diagnostic_canvas.yview_scroll(units, "units")
        return "break"
''',
        "diagnostic scrolling",
    )

    VIEW.write_text(text, encoding="utf-8")
    print(f"Applied UI-018 presentation polish to {VIEW}")


if __name__ == "__main__":
    main()
