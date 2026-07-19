from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"
QUERY = ROOT / "olden_db" / "query.py"
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
ADAPTER = ROOT / "olden_db" / "desktop" / "planner_diagnostics.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_scope_is_view_only() -> None:
    view = source(VIEW)
    require("Diagnostic.Error.TLabel" in view, "View polish is missing")
    require("generate_planner_result" in source(QUERY), "Query contract unexpectedly changed")
    require("adapt_planner_diagnostics" in source(PRESENTER), "Presenter contract unexpectedly changed")
    require("explanation=diagnostic.canonical_explanation" in source(ADAPTER), "Adapter contract changed")


def test_responsive_wrapping() -> None:
    text = source(VIEW)
    require("self._diagnostic_wrap_labels" in text, "Responsive label tracking missing")
    require("wraplength = max(140, width - 48)" in text, "Responsive wrap calculation missing")
    require("self._resize_diagnostic_content" in text, "Resize handling missing")
    require("wraplength=720" not in text, "Fixed diagnostic wrap width remains")


def test_scrollbar_only_when_needed() -> None:
    text = source(VIEW)
    require("self._diagnostic_scrollbar.grid_remove()" in text, "Scrollbar hide behavior missing")
    require("first <= 0.0 and last >= 1.0" in text, "Overflow check missing")
    require("yscrollcommand=self._set_diagnostic_scrollbar" in text, "Scrollbar callback missing")


def test_empty_state_hierarchy() -> None:
    text = source(VIEW)
    require('text="[i] No diagnostics"' in text, "Empty-state heading missing")
    require("Generate a plan to review planner-provided explanations." in text, "Empty-state guidance missing")


def test_structured_severity_presentation() -> None:
    text = source(VIEW)
    for token in (
        "Diagnostic.Error.TLabel",
        "Diagnostic.Warning.TLabel",
        "Diagnostic.Information.TLabel",
        "style_by_severity",
        "_DIAGNOSTIC_MARKERS[diagnostic.severity]",
    ):
        require(token in text, f"Missing structured severity presentation: {token}")
    require("diagnostic.explanation.lower" not in text, "Severity must not be inferred from text")


def test_keyboard_and_focus_preserved() -> None:
    text = source(VIEW)
    for token in ('"<Up>"', '"<Down>"', '"<Home>"', '"<End>"', '"<Prior>"', '"<Next>"', "takefocus=True", "highlightthickness=2", "yview_moveto"):
        require(token in text, f"Missing keyboard/focus behavior: {token}")


def test_accessibility_guidance() -> None:
    text = source(VIEW)
    require("Read-only. Use Up/Down, Home/End, or Page Up/Page Down" in text, "Keyboard guidance missing")
    require("diagnostic.severity.value" in text, "Severity text must accompany styling")


def test_diagnostic_state_initialized() -> None:
    text = source(VIEW)
    require("self._diagnostic_items: list[tk.Frame] = []" in text, "Diagnostic item state missing")
    require("self._diagnostic_wrap_labels: list[ttk.Label] = []" in text, "Wrap label state missing")


def test_syntax() -> None:
    ast.parse(source(VIEW), filename=str(VIEW))


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused UI-018 checks")


if __name__ == "__main__":
    main()
