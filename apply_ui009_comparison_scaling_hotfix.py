from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "scenario_comparison_workspace_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")

    compact_old = """    def _refresh_scroll(self):
        bounds=self._canvas.bbox("all")
        if bounds: self._canvas.configure(scrollregion=bounds)
"""
    compact_new = """    def _refresh_scroll(self):
        self._content.update_idletasks()
        requested_height = self._content.winfo_reqheight()
        if requested_height > 1:
            self._canvas.configure(height=requested_height)
        bounds=self._canvas.bbox("all")
        if bounds: self._canvas.configure(scrollregion=bounds)
"""

    formatted_old = """    def _refresh_scroll_region(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        bounds = self._canvas.bbox("all")
        if bounds is not None:
            self._canvas.configure(scrollregion=bounds)
"""
    formatted_new = """    def _refresh_scroll_region(
        self,
        _event: tk.Event[tk.Misc] | None = None,
    ) -> None:
        self._content.update_idletasks()
        requested_height = self._content.winfo_reqheight()
        if requested_height > 1:
            self._canvas.configure(height=requested_height)
        bounds = self._canvas.bbox("all")
        if bounds is not None:
            self._canvas.configure(scrollregion=bounds)
"""

    if "requested_height = self._content.winfo_reqheight()" in text:
        print("SKIP: comparison canvas height synchronization already applied")
    elif compact_old in text:
        text = text.replace(compact_old, compact_new, 1)
        print("UPDATED: compact comparison canvas height synchronization")
    elif formatted_old in text:
        text = text.replace(formatted_old, formatted_new, 1)
        print("UPDATED: comparison canvas height synchronization")
    else:
        raise RuntimeError("Could not locate the comparison canvas refresh method.")

    VIEW.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    if "def test_comparison_canvas_tracks_full_workspace_height()" in text:
        print("SKIP: canvas-height regression test already applied")
        return

    marker = "def test_view_is_passive() -> None:\n"
    if marker not in text:
        raise RuntimeError("Could not locate focused-test insertion point")

    test = """def test_comparison_canvas_tracks_full_workspace_height() -> None:
    text = VIEW.read_text(encoding="utf-8")
    require(
        "requested_height = self._content.winfo_reqheight()" in text,
        "Comparison canvas must use the full composed workspace height",
    )
    require(
        "self._canvas.configure(height=requested_height)" in text,
        "Comparison canvas must not retain Tkinter's default clipped height",
    )


"""
    TEST.write_text(text.replace(marker, test + marker, 1), encoding="utf-8")
    print("UPDATED: comparison canvas height regression test")


def validate() -> None:
    for path in (VIEW, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_view()
    patch_test()
    validate()
    print("UI-009 comparison scaling hotfix applied successfully.")


if __name__ == "__main__":
    main()
