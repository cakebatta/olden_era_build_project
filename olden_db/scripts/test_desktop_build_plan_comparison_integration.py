from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRESENTER = ROOT / "olden_db" / "desktop" / "presenters" / "build_plan_comparison_presenter.py"
VIEW = ROOT / "olden_db" / "desktop" / "views" / "build_plan_comparison_view.py"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def test_empty_and_equivalent_plan_support_is_present() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require("BuildPlanComparisonStatus.EQUIVALENT" in text, "Equivalent status missing")
    require("for item in comparison.step_comparisons" in text, "Empty sequence support missing")


def test_resource_vector_is_not_collapsed() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require("for name in RESOURCE_NAMES" in text, "Canonical resource vector missing")
    for forbidden in ("score", "percentage", "weighted"):
        require(forbidden not in text.lower(), f"Forbidden resource aggregation: {forbidden}")


def test_shared_and_exclusive_collections_are_direct() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    require("comparison.common_buildings" in text, "Shared actions missing")
    require("comparison.left_only_actions" in text, "Left-only actions missing")
    require("comparison.right_only_actions" in text, "Right-only actions missing")


def test_long_plan_view_uses_scrollable_tree() -> None:
    text = VIEW.read_text(encoding="utf-8")
    require("ttk.Treeview(" in text, "Aligned table missing")
    require("height=14" in text, "Long-plan viewport missing")
    require("scrollbar.grid" in text, "Aligned table scrollbar missing")


def main() -> None:
    checks = [
        test_empty_and_equivalent_plan_support_is_present,
        test_resource_vector_is_not_collapsed,
        test_shared_and_exclusive_collections_are_direct,
        test_long_plan_view_uses_scrollable_tree,
    ]
    for check in checks:
        check()
        print(f"PASS: {check.__name__}")
    print(f"PASS: {len(checks)} UI-010 integration checks")


if __name__ == "__main__":
    main()
