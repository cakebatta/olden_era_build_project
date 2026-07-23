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


def verify_repository() -> None:
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if actual != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository HEAD does not match the reviewed UI-012 baseline.\n"
            f"Expected: {EXPECTED_HEAD}\nActual:   {actual}"
        )


def verify_or_finish_view_fix() -> None:
    text = VIEW.read_text(encoding="utf-8")
    if LEGACY_BLOCK in text:
        text = text.replace(LEGACY_BLOCK, "", 1)
        VIEW.write_text(text, encoding="utf-8")
        print("UPDATED: removed obsolete timeline auto-selection block")
    else:
        print("CONFIRMED: timeline source correction already applied")

    text = VIEW.read_text(encoding="utf-8")
    required = (
        "_timeline_item_id(step.identity)",
        "self._last_timeline_presentation = timeline",
        "self._on_build_step_selected(step.identity)",
    )
    for token in required:
        if token not in text:
            raise RuntimeError(f"Required semantic event-flow token missing: {token}")
    forbidden = (
        "_show_timeline_step_detail",
        "first = str(timeline.steps[0].step_number)",
        "selection_set(first)",
    )
    for token in forbidden:
        if token in text:
            raise RuntimeError(f"Obsolete timeline behavior remains: {token}")
    ast.parse(text, filename=str(VIEW))


def patch_real_test_structure() -> None:
    text = TEST.read_text(encoding="utf-8")
    marker = "def test_timeline_selection_event_flow_regression() -> None:"
    if marker not in text:
        function = """
def test_timeline_selection_event_flow_regression() -> None:
    view = (ROOT / "olden_db/desktop/views/planner_view.py").read_text()
    render_start = view.index("    def _render_timeline(")
    handler_start = view.index(
        "    def _handle_timeline_selection(", render_start
    )
    render_body = view[render_start:handler_start]

    assert "_timeline_item_id(step.identity)" in render_body
    assert "self._last_timeline_presentation = timeline" in render_body
    assert render_body.count(
        "self._last_timeline_presentation = timeline"
    ) == 1
    assert "first = str(timeline.steps[0].step_number)" not in render_body
    assert "selection_set(first)" not in render_body
    assert "_show_timeline_step_detail" not in view

    handler_end = view.index("    @staticmethod", handler_start)
    handler_body = view[handler_start:handler_end]
    assert "timeline = self._last_timeline_presentation" in handler_body
    assert "self._on_build_step_selected(step.identity)" in handler_body

"""
        main_anchor = "def main() -> None:\n"
        if main_anchor not in text:
            raise RuntimeError("Focused test main function missing.")
        text = text.replace(main_anchor, function + main_anchor, 1)

    old_loop = (
        "    for check in (test_identity_is_immutable, "
        "test_presenter_and_view_boundaries, test_syntax):\n"
    )
    new_loop = """    for check in (
        test_identity_is_immutable,
        test_presenter_and_view_boundaries,
        test_timeline_selection_event_flow_regression,
        test_syntax,
    ):
"""
    if old_loop in text:
        text = text.replace(old_loop, new_loop, 1)
    elif "test_timeline_selection_event_flow_regression," not in text:
        raise RuntimeError("Could not update the focused test check tuple.")

    ast.parse(text, filename=str(TEST))
    TEST.write_text(text, encoding="utf-8")
    print("UPDATED: focused event-flow regression test")


def validate() -> None:
    for path in (VIEW, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    verify_repository()
    verify_or_finish_view_fix()
    patch_real_test_structure()
    validate()
    print("UI-012A resume patch applied successfully.")
    print("Next: cd olden_db")
    print("Then: python -m scripts.test_desktop_build_plan_explanation")
    print("Then: python -m scripts.run_desktop")


if __name__ == "__main__":
    main()
