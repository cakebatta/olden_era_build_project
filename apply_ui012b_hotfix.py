from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "365f4853ec7ae065601d17db0b80ae6308cb5d15"
PRESENTER = ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "planner_presenter.py"
VIEW = ROOT / "olden_db" / "olden_db" / "desktop" / "views" / "planner_view.py"
TEST = ROOT / "olden_db" / "scripts" / "test_desktop_build_plan_explanation.py"


def verify_repository() -> None:
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if actual != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository HEAD does not match the reviewed UI-012 baseline.\n"
            f"Expected: {EXPECTED_HEAD}\nActual:   {actual}"
        )


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"SKIP: {label} already applied")
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    print(f"UPDATED: {label}")
    return text.replace(old, new, 1)


def patch_presenter() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    old = """    def on_build_step_selected(self, identity: BuildStepIdentity) -> None:
        base = self._workspace.base(identity.base_plan_id)
"""
    new = """    def on_build_step_selected(self, identity: BuildStepIdentity) -> None:
        if self._selected_build_step == identity:
            return
        base = self._workspace.base(identity.base_plan_id)
"""
    text = replace_once(text, old, new, "presenter re-entrancy guard")

    redundant = """        self._selected_build_step = identity
        self._render_snapshot(self._workspace.snapshot())
        self._view.restore_build_step_focus(identity)
"""
    replacement = """        self._selected_build_step = identity
        self._render_snapshot(self._workspace.snapshot())
"""
    text = replace_once(
        text,
        redundant,
        replacement,
        "remove redundant focus restoration",
    )
    ast.parse(text, filename=str(PRESENTER))
    PRESENTER.write_text(text, encoding="utf-8")


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")
    old = """        item_id = self._timeline_item_id(identity)
        if self._timeline_tree.exists(item_id):
            self._timeline_tree.selection_set(item_id)
            self._timeline_tree.focus(item_id)
            self._timeline_tree.see(item_id)
"""
    new = """        item_id = self._timeline_item_id(identity)
        if not self._timeline_tree.exists(item_id):
            return
        current = self._timeline_tree.selection()
        if current != (item_id,):
            self._timeline_tree.selection_set(item_id)
        if self._timeline_tree.focus() != item_id:
            self._timeline_tree.focus(item_id)
        self._timeline_tree.see(item_id)
"""
    text = replace_once(text, old, new, "idempotent focus restoration")
    ast.parse(text, filename=str(VIEW))
    VIEW.write_text(text, encoding="utf-8")


def patch_test() -> None:
    text = TEST.read_text(encoding="utf-8")
    marker = "def test_selection_reentrancy_is_bounded() -> None:"
    if marker not in text:
        function = """
def test_selection_reentrancy_is_bounded() -> None:
    presenter = (
        ROOT / "olden_db/desktop/presenters/planner_presenter.py"
    ).read_text()
    view = (ROOT / "olden_db/desktop/views/planner_view.py").read_text()

    selection_start = presenter.index(
        "    def on_build_step_selected("
    )
    selection_end = presenter.index(
        "    def on_build_step_selection_cleared(", selection_start
    )
    selection_body = presenter[selection_start:selection_end]
    assert "if self._selected_build_step == identity:" in selection_body
    assert selection_body.count("restore_build_step_focus(identity)") == 0

    restore_start = view.index("    def restore_build_step_focus(")
    restore_end = view.index("    def render_explanation(", restore_start)
    restore_body = view[restore_start:restore_end]
    assert "current = self._timeline_tree.selection()" in restore_body
    assert "if current != (item_id,):" in restore_body
    assert "self._timeline_tree.selection_set(item_id)" in restore_body

"""
        main_anchor = "def main() -> None:\n"
        if main_anchor not in text:
            raise RuntimeError("Focused test main function missing.")
        text = text.replace(main_anchor, function + main_anchor, 1)

    # Support either the original inline tuple or the expanded tuple from UI-012A.
    if "        test_selection_reentrancy_is_bounded,\n" not in text:
        syntax_entry = "        test_syntax,\n"
        if syntax_entry in text:
            text = text.replace(
                syntax_entry,
                "        test_selection_reentrancy_is_bounded,\n"
                + syntax_entry,
                1,
            )
        else:
            old_inline = (
                "    for check in (test_identity_is_immutable, "
                "test_presenter_and_view_boundaries, test_syntax):\n"
            )
            new_inline = """    for check in (
        test_identity_is_immutable,
        test_presenter_and_view_boundaries,
        test_selection_reentrancy_is_bounded,
        test_syntax,
    ):
"""
            if old_inline not in text:
                raise RuntimeError("Could not locate focused-test check tuple.")
            text = text.replace(old_inline, new_inline, 1)

    ast.parse(text, filename=str(TEST))
    TEST.write_text(text, encoding="utf-8")
    print("UPDATED: selection re-entrancy regression test")


def validate() -> None:
    for path in (PRESENTER, VIEW, TEST):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    verify_repository()
    patch_presenter()
    patch_view()
    patch_test()
    validate()
    print("UI-012B selection re-entrancy hotfix applied successfully.")
    print("Next: cd olden_db")
    print("Then: python -m scripts.test_desktop_build_plan_explanation")
    print("Then: python -m scripts.run_desktop")


if __name__ == "__main__":
    main()
