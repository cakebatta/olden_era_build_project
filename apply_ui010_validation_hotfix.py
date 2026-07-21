from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UI009_TEST = ROOT / "olden_db" / "scripts" / "test_desktop_scenario_comparison_workspace.py"
COLLECTION_PRESENTER = ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "scenario_comparison_workspace_presenter.py"
COMPARISON_PRESENTER = ROOT / "olden_db" / "olden_db" / "desktop" / "presenters" / "build_plan_comparison_presenter.py"
RUNTIME_DOC = ROOT / "docs" / "ui010_runtime_verification.md"


def patch_ui009_regression() -> None:
    text = UI009_TEST.read_text(encoding="utf-8")
    old = '    require("ScenarioAwarePlannerPresenter(" in text, "existing presenter not reused")\n'
    new = '    comparison_presenter = (\n        ROOT\n        / "olden_db"\n        / "desktop"\n        / "presenters"\n        / "build_plan_comparison_presenter.py"\n    ).read_text(encoding="utf-8")\n    require(\n        "ComparisonAwarePlannerPresenter(" in text,\n        "comparison-aware existing workspace presenter not composed",\n    )\n    require(\n        "class ComparisonAwarePlannerPresenter(ScenarioAwarePlannerPresenter):"\n        in comparison_presenter,\n        "comparison-aware presenter must reuse ScenarioAwarePlannerPresenter",\n    )\n'

    if new in text:
        print("SKIP: UI-009 presenter reuse regression already updated")
        return

    count = text.count(old)
    if count != 1:
        raise RuntimeError(
            "UI-009 presenter reuse assertion: expected one reviewed line, "
            f"found {count}"
        )

    UI009_TEST.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("UPDATED: UI-009 presenter reuse regression")


def discover_backend_comparison_test() -> str | None:
    scripts = ROOT / "olden_db" / "scripts"
    candidates = []

    for path in sorted(scripts.glob("test_*.py")):
        if path.stem.startswith("test_desktop_"):
            continue
        content = path.read_text(encoding="utf-8")
        if (
            "compare_accepted_build_plans" in content
            or "BuildPlanComparisonOutcome" in content
            or "BuildStepRelationship" in content
        ):
            candidates.append(path)

    if not candidates:
        return None

    candidates.sort(
        key=lambda path: (
            "accepted" not in path.stem,
            "comparison" not in path.stem,
            len(path.stem),
            path.stem,
        )
    )
    return f"scripts.{candidates[0].stem}"


def patch_runtime_command() -> None:
    if not RUNTIME_DOC.exists():
        print("NOTE: UI-010 runtime document not found; no command updated")
        return

    text = RUNTIME_DOC.read_text(encoding="utf-8")
    incorrect = "python -m scripts.test_accepted_build_plan_comparison"
    discovered = discover_backend_comparison_test()

    if incorrect not in text:
        if discovered:
            print(f"NOTE: backend comparison suite discovered as {discovered}")
        else:
            print("NOTE: no standalone backend comparison suite discovered")
        return

    if discovered is None:
        text = text.replace(incorrect + "\n", "", 1)
        print(
            "UPDATED: removed nonexistent BE-013 command; "
            "no standalone backend comparison test module exists"
        )
    else:
        replacement = f"python -m {discovered}"
        text = text.replace(incorrect, replacement, 1)
        print(f"UPDATED: BE-013 test command -> {replacement}")

    RUNTIME_DOC.write_text(text, encoding="utf-8")


def validate() -> None:
    for path in (UI009_TEST, COLLECTION_PRESENTER, COMPARISON_PRESENTER):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    patch_ui009_regression()
    patch_runtime_command()
    validate()
    print("UI-010 validation hotfix applied successfully.")


if __name__ == "__main__":
    main()
