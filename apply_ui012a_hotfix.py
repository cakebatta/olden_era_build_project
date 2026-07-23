from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "365f4853ec7ae065601d17db0b80ae6308cb5d15"
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_build_plan_explanation.py"

LEGACY_BLOCK = """        if timeline.steps:
            first = str(timeline.steps[0].step_number)
            self._timeline_tree.selection_set(first)
            self._timeline_tree.focus(first)
            self._timeline_tree.see(first)
            self._show_timeline_step_detail(timeline.steps[0])
"""


def verify_baseline() -> None:
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if actual != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository HEAD does not match the reviewed UI-012A baseline.\n"
            f"Expected: {EXPECTED_HEAD}\nActual:   {actual}"
        )


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")
    count = text.count(LEGACY_BLOCK)
    if count != 1:
        raise RuntimeError(
            "Expected exactly one obsolete timeline auto-selection block; "
            f"found {count}."
        )
    text = text.replace(LEGACY_BLOCK, "", 1)

    if "_show_timeline_step_detail" in text:
        raise RuntimeError("Legacy timeline detail method reference remains.")
    if 'first = str(timeline.steps[0].step_number)' in text:
        raise RuntimeError("Numeric row-index auto-selection remains.")
    if text.count("self._last_timeline_presentation = timeline") != 1:
        raise RuntimeError(
            "Timeline presentation cache must be assigned exactly once."
        )

    ast.parse(text, filename=str(VIEW))
    VIEW.write_text(text, encoding="utf-8")
    print("UPDATED: timeline semantic selection event flow")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    marker = "def test_timeline_selection_event_flow_regression() -> None:"
    if marker in text:
        print("SKIP: regression test already present")
        return

    test_func = """
def test_timeline_selection_event_flow_regression() -> None:
    view_text = VIEW.read_text(encoding="utf-8")
    render_start = view_text.index("    def _render_timeline(")
    handler_start = view_text.index(
        "    def _handle_timeline_selection(", render_start
    )
    render_body = view_text[render_start:handler_start]

    assert "_timeline_item_id(step.identity)" in render_body
    assert "self._last_timeline_presentation = timeline" in render_body
    assert render_body.count(
        "self._last_timeline_presentation = timeline"
    ) == 1
    assert "selection_set(first)" not in render_body
    assert "first = str(timeline.steps[0].step_number)" not in render_body
    assert "_show_timeline_step_detail" not in view_text

    handler_end = view_text.index("    @staticmethod", handler_start)
    handler_body = view_text[handler_start:handler_end]
    assert "timeline = self._last_timeline_presentation" in handler_body
    assert "self._on_build_step_selected(step.identity)" in handler_body

"""
    anchor = "def main() -> None:\n"
    if anchor not in text:
        raise RuntimeError("Focused test main anchor missing.")
    text = text.replace(anchor, test_func + anchor, 1)

    checks_anchor = "        test_syntax,\n"
    if checks_anchor not in text:
        raise RuntimeError("Focused test check-list anchor missing.")
    text = text.replace(
        checks_anchor,
        "        test_timeline_selection_event_flow_regression,\n"
        + checks_anchor,
        1,
    )

    ast.parse(text, filename=str(TEST))
    TEST.write_text(text, encoding="utf-8")
    print("UPDATED: timeline event-flow regression test")


def validate() -> None:
    for path in (VIEW, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    verify_baseline()
    patch_view()
    patch_test()
    validate()
    print("UI-012A hotfix applied successfully.")
    print("Next: cd olden_db")
    print("Then: python -m scripts.test_desktop_build_plan_explanation")
    print("Then: python -m scripts.run_desktop")


if __name__ == "__main__":
    main()
