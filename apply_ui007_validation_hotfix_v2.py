from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "olden_db" / "olden_db" / "desktop" / "app.py"
SUMMARY_TEST = ROOT / "olden_db" / "scripts" / "test_desktop_planning_summary.py"
DIAGNOSTIC_TEST = ROOT / "olden_db" / "scripts" / "test_planner_diagnostic_pipeline.py"


def patch_desktop_startup() -> None:
    text = APP.read_text(encoding="utf-8")
    new = "service = PlanningQueryService.from_default_game_data()"
    old = "service = PlanningQueryService(canonical_data)"
    if new in text:
        print("SKIP: desktop localization-enabled Query Layer construction already applied")
        return
    if old not in text:
        raise RuntimeError(
            "Desktop startup service construction was not recognized. "
            "Inspect olden_db/olden_db/desktop/app.py."
        )
    APP.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("UPDATED: desktop localization-enabled Query Layer construction")


def patch_summary_boundary_test() -> None:
    text = SUMMARY_TEST.read_text(encoding="utf-8")
    if '"summary.completion_date_text" in text' in text:
        print("SKIP: summary view-boundary regression already applied")
        return

    function_marker = "def test_view_renders_only_presentation_values"
    function_start = text.find(function_marker)
    if function_start < 0:
        raise RuntimeError("Could not find summary view-boundary test function.")

    next_function = text.find("\ndef ", function_start + len(function_marker))
    function_end = next_function if next_function >= 0 else len(text)
    function_text = text[function_start:function_end]

    loop_start = function_text.find("    for forbidden in (")
    if loop_start < 0:
        raise RuntimeError("Could not find forbidden-name loop in summary test.")

    one_line = 'require(forbidden not in text, f"View derives authoritative value: {forbidden}")'
    assertion_pos = function_text.find(one_line, loop_start)
    if assertion_pos >= 0:
        loop_end = assertion_pos + len(one_line)
    else:
        assertion_pos = function_text.find("        require(", loop_start)
        if assertion_pos < 0:
            raise RuntimeError("Could not locate forbidden-name assertion.")
        closing = function_text.find("\n        )", assertion_pos)
        if closing < 0:
            raise RuntimeError("Could not locate end of forbidden-name assertion.")
        loop_end = closing + len("\n        )")

    replacement = """    for forbidden in (
        ".completion_date",
        ".total_cost",
        ".daily_construction_schedule",
        "get_building_display_text(",
    ):
        require(
            forbidden not in text,
            f"View derives authoritative value: {forbidden}",
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
    )"""

    patched_function = function_text[:loop_start] + replacement + function_text[loop_end:]
    SUMMARY_TEST.write_text(
        text[:function_start] + patched_function + text[function_end:],
        encoding="utf-8",
    )
    print("UPDATED: summary view-boundary regression")


def patch_recording_service() -> None:
    text = DIAGNOSTIC_TEST.read_text(encoding="utf-8")
    class_marker = "class RecordingService:"
    start = text.find(class_marker)
    if start < 0:
        raise RuntimeError("Could not find RecordingService.")

    next_class = text.find("\nclass ", start + len(class_marker))
    block_end = next_class if next_class >= 0 else len(text)
    block = text[start:block_end]

    if "def get_building_display_text(" in block:
        print("SKIP: diagnostic RecordingService localization contract already applied")
        return

    first_method = text.find("\n    def ", start, block_end)
    if first_method < 0:
        raise RuntimeError("RecordingService contains no method insertion point.")

    insertion = """
    def get_building_display_text(self, building):
        return f"{building.sid} level {building.level}"

"""
    DIAGNOSTIC_TEST.write_text(
        text[:first_method] + insertion + text[first_method:],
        encoding="utf-8",
    )
    print("UPDATED: diagnostic RecordingService localization contract")


def main() -> None:
    patch_desktop_startup()
    patch_summary_boundary_test()
    patch_recording_service()
    print("UI-007 validation hotfix v2 applied.")


if __name__ == "__main__":
    main()
