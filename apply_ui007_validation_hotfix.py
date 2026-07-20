from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
APP = ROOT / "olden_db" / "olden_db" / "desktop" / "app.py"
SUMMARY_TEST = ROOT / "olden_db" / "scripts" / "test_desktop_planning_summary.py"
DIAGNOSTIC_TEST = ROOT / "olden_db" / "scripts" / "test_planner_diagnostic_pipeline.py"


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"SKIP: {label} already applied")
        return
    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            f"{label}: expected one exact block, found {count}. "
            "Confirm UI-007 and BE-011 are applied before using this hotfix."
        )
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"UPDATED: {label}")


def patch_desktop_startup() -> None:
    replace_once(
        APP,
        """    try:
        canonical_data = load_default_game_data()
        service = PlanningQueryService(canonical_data)
""",
        """    try:
        canonical_data = load_default_game_data()
        service = PlanningQueryService.from_default_game_data()
""",
        "desktop localization-enabled Query Layer construction",
    )


def patch_summary_boundary_test() -> None:
    replace_once(
        SUMMARY_TEST,
        """    for forbidden in (
        "completion_date",
        "total_cost",
        "daily_construction_schedule",
        "get_building_display_text",
    ):
        require(forbidden not in text, f"View derives authoritative value: {forbidden}")
""",
        """    for forbidden in (
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
    )
""",
        "summary view-boundary regression",
    )


def patch_recording_service() -> None:
    text = DIAGNOSTIC_TEST.read_text(encoding="utf-8")
    marker = "class RecordingService:"
    start = text.index(marker)
    next_class = text.find("\nclass ", start + len(marker))
    block = text[start:next_class if next_class != -1 else len(text)]

    if "def get_building_display_text(" in block:
        print("SKIP: diagnostic RecordingService localization contract already applied")
        return

    insertion_point = text.index("\n    def ", start)
    insertion = """
    def get_building_display_text(self, building):
        return f"{building.sid} level {building.level}"

"""
    updated = text[:insertion_point] + insertion + text[insertion_point:]
    DIAGNOSTIC_TEST.write_text(updated, encoding="utf-8")
    print("UPDATED: diagnostic RecordingService localization contract")


def main() -> None:
    patch_desktop_startup()
    patch_summary_boundary_test()
    patch_recording_service()
    print("UI-007 validation hotfix applied.")


if __name__ == "__main__":
    main()
