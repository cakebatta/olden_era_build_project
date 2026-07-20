from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUMMARY_TEST = ROOT / "olden_db" / "scripts" / "test_desktop_planning_summary.py"
DIAGNOSTIC_TEST = ROOT / "olden_db" / "scripts" / "test_planner_diagnostic_pipeline.py"


def replace_function_body(
    path: Path,
    function_name: str,
    replacement_source: str,
) -> None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    target = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        ),
        None,
    )
    if target is None:
        raise RuntimeError(f"{path}: function {function_name!r} not found")

    lines = text.splitlines(keepends=True)
    start = target.lineno - 1
    end = target.end_lineno
    replacement = replacement_source.rstrip() + "\n\n"
    path.write_text(
        "".join(lines[:start]) + replacement + "".join(lines[end:]),
        encoding="utf-8",
    )
    print(f"UPDATED: {path.name}:{function_name}")


def patch_summary_boundary_test() -> None:
    replacement = '''def test_view_renders_only_presentation_values() -> None:
    view_path = (
        ROOT
        / "olden_db"
        / "desktop"
        / "views"
        / "planner_view.py"
    )
    text = view_path.read_text(encoding="utf-8")
    tree = ast.parse(text)

    forbidden_attributes = {
        "accepted_plan",
        "plan",
        "completion_date",
        "total_cost",
        "daily_construction_schedule",
    }
    forbidden_calls = {"get_building_display_text"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            require(
                node.attr not in forbidden_attributes,
                f"View derives authoritative value: {node.attr}",
            )
        if isinstance(node, ast.Call):
            function = node.func
            called_name = (
                function.attr
                if isinstance(function, ast.Attribute)
                else function.id
                if isinstance(function, ast.Name)
                else None
            )
            require(
                called_name not in forbidden_calls,
                f"View resolves localization directly: {called_name}",
            )

    require(
        "summary.completion_date_text" in text,
        "View must render supplied completion-date presentation text",
    )
    require(
        "summary.total_cost_text" in text,
        "View must render supplied total-cost presentation text",
    )
    require(
        "summary.daily_schedule_rows" in text,
        "View must render supplied daily-schedule presentation rows",
    )
'''
    replace_function_body(
        SUMMARY_TEST,
        "test_view_renders_only_presentation_values",
        replacement,
    )


def patch_diagnostic_success_assertion() -> None:
    text = DIAGNOSTIC_TEST.read_text(encoding="utf-8")

    replacement = '''    summary = view.workspace_presentations[-1].summary
    require(
        summary.result_status == "Current Accepted Plan",
        "Presenter did not identify the accepted result as current",
    )
    require(
        summary.step_count_text is not None,
        "Presenter did not deliver accepted-plan summary values",
    )'''

    if replacement in text:
        print("SKIP: diagnostic success assertion already updated")
        return

    marker = "view.workspace_presentations[-1].accepted_plan"
    pos = text.find(marker)
    if pos < 0:
        raise RuntimeError(
            "Could not find the stale accepted_plan assertion in "
            "test_planner_diagnostic_pipeline.py."
        )

    call_start = text.rfind("    require(", 0, pos)
    call_end = text.find("\n    )", pos)
    if call_start < 0 or call_end < 0:
        raise RuntimeError("Could not determine stale assertion boundaries.")
    call_end += len("\n    )")

    DIAGNOSTIC_TEST.write_text(
        text[:call_start] + replacement + text[call_end:],
        encoding="utf-8",
    )
    print("UPDATED: diagnostic success assertion")


def main() -> None:
    patch_summary_boundary_test()
    patch_diagnostic_success_assertion()
    print("UI-007 validation hotfix v3 applied.")


if __name__ == "__main__":
    main()
