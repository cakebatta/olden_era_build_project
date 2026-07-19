from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "olden_db" / "desktop" / "views" / "planner_view.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_empty_state() -> None:
    require("No diagnostics" in source(VIEW), "Explicit empty state missing")


def test_order_and_read_only() -> None:
    text = source(VIEW)
    require(
        "for row, diagnostic in enumerate(self._diagnostics):" in text,
        "View must render the supplied presentation order",
    )
    block = text[
        text.index("    def set_diagnostics"):
        text.index("    def set_diagnostic_inspector_expanded")
    ]
    require(
        ".sort(" not in block and "sorted(" not in block,
        "View must not reorder presentation values",
    )
    require(
        "Entry(" not in block and "Text(" not in block,
        "Inspector must remain read-only",
    )


def test_keyboard_navigation_and_scrolling() -> None:
    text = source(VIEW)
    for token in (
        "<Up>",
        "<Down>",
        "<Home>",
        "<End>",
        "takefocus=True",
        "highlightthickness=2",
    ):
        require(token in text, f"Missing accessibility behavior: {token}")
    require(
        "yview_moveto" in text and "yview_scroll" in text,
        "Navigation must preserve or update scrolling",
    )


def test_syntax() -> None:
    ast.parse(source(VIEW), filename=str(VIEW))


def main() -> None:
    tests = [
        value
        for name, value in globals().items()
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused diagnostic-inspector source checks")


if __name__ == "__main__":
    main()
