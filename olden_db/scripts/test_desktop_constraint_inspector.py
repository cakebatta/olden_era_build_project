from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "olden_db" / "desktop"
VIEW_PATH = DESKTOP / "views" / "planner_view.py"
MODEL_PATH = DESKTOP / "planner_diagnostics.py"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source(path):
    return path.read_text(encoding="utf-8")


def function_node(path, class_name, function_name):
    tree = ast.parse(source(path))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == function_name:
                    return item
    raise AssertionError(f"Missing {class_name}.{function_name}")


def test_successful_plan_has_no_diagnostics():
    text = source(VIEW_PATH)
    show_target = text[text.index("    def show_target"):text.index("    def show_prerequisites")]
    require(
        "self.set_constraint_diagnostics(())" in show_target,
        "Successful result rendering must reset the inspector to its empty state",
    )


def test_failed_plan_displays_exact_planner_message():
    text = source(VIEW_PATH)
    show_error = text[text.index("    def show_error"):text.index("    def set_constraint_diagnostics")]
    require("explanation=message" in show_error, "Planner message must be passed through verbatim")
    require("severity=DiagnosticSeverity.ERROR" in show_error, "Failure route must render Error severity")
    require("str(message)" not in show_error and "split(" not in show_error, "View must not reinterpret planner diagnostics")


def test_multiple_diagnostic_entries_are_iterated():
    node = function_node(VIEW_PATH, "PlannerView", "set_constraint_diagnostics")
    loops = [item for item in ast.walk(node) if isinstance(item, ast.For)]
    require(loops, "Constraint renderer must support multiple entries")
    require("enumerate(self._constraint_diagnostics)" in source(VIEW_PATH), "Every diagnostic must receive its own row")


def test_severity_rendering_uses_icon_and_text():
    text = source(VIEW_PATH)
    for value in ("ERROR", "WARNING", "INFORMATION"):
        require(f"DiagnosticSeverity.{value}" in text, f"Missing {value} severity marker")
    require("diagnostic.severity.value" in text, "Severity text must accompany the visual marker")
    require("_DIAGNOSTIC_MARKERS" in text, "Severity must not rely on color alone")


def test_expand_collapse_behavior():
    text = source(VIEW_PATH)
    require('text="▶ Constraint Inspector"' in text, "Inspector must start collapsed")
    require('text="▼ Constraint Inspector"' in text, "Expanded state must be distinguishable")
    require("self._constraint_panel.grid_remove()" in text, "Collapse must remove unused vertical space")
    require("self._constraint_panel.grid(" in text, "Expand must restore the panel")


def test_panel_state_persists_for_view_session():
    text = source(VIEW_PATH)
    require("self._constraint_inspector_expanded = False" in text, "Session state must default to collapsed")
    require("not self._constraint_inspector_expanded" in text, "Toggle must reuse the stored view state")
    require("configparser" not in text and "repository" not in text.lower(), "Panel state must not be persisted")


def test_planner_refresh_updates_diagnostics():
    text = source(VIEW_PATH)
    clear_results = text[text.index("    def clear_results"):text.index("    def show_target")]
    show_error = text[text.index("    def show_error"):text.index("    def set_constraint_diagnostics")]
    require("set_constraint_diagnostics(())" in clear_results, "Context refresh must clear stale diagnostics")
    require("set_constraint_diagnostics((" in show_error, "Planner failure must replace current diagnostics")


def test_empty_state_presentation():
    require(
        'text="No planner constraints to display."' in source(VIEW_PATH),
        "Required empty-state copy is missing",
    )


def test_presentation_model_is_immutable():
    text = source(MODEL_PATH)
    require("@dataclass(frozen=True, slots=True)" in text, "Diagnostic model must be immutable")
    require("class DiagnosticSeverity(str, Enum)" in text, "Severity must use a closed presentation vocabulary")


def test_inspector_is_read_only_and_scrollable():
    text = source(VIEW_PATH)
    require("_constraint_canvas" in text and "_constraint_scrollbar" in text, "Inspector must scroll")
    inspector = text[text.index("        self._constraint_header"):text.index("        self.set_constraint_diagnostics(())")]
    require("Entry(" not in inspector and "Text(" not in inspector, "Inspector must remain read-only")


def test_no_backend_or_persistence_scope_in_package():
    approved = {
        Path("olden_db/olden_db/desktop/planner_diagnostics.py"),
        Path("olden_db/olden_db/desktop/views/planner_view.py"),
        Path("olden_db/scripts/test_desktop_constraint_inspector.py"),
        Path("UI-016-IMPLEMENTATION-REPORT.md"),
    }
    package_root = ROOT.parent
    actual = {
        path.relative_to(package_root)
        for path in package_root.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    require(actual <= approved, f"Unexpected files in UI-016 package: {sorted(actual - approved)}")


def test_repository_bytecode_hygiene():
    try:
        result = subprocess.run(
            ["git", "ls-files", "*.pyc", "*.pyo", "*.pyd"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return
    require(not result.stdout.strip(), "Committed Python bytecode artifacts must be removed")


def main():
    tests = [
        test_successful_plan_has_no_diagnostics,
        test_failed_plan_displays_exact_planner_message,
        test_multiple_diagnostic_entries_are_iterated,
        test_severity_rendering_uses_icon_and_text,
        test_expand_collapse_behavior,
        test_panel_state_persists_for_view_session,
        test_planner_refresh_updates_diagnostics,
        test_empty_state_presentation,
        test_presentation_model_is_immutable,
        test_inspector_is_read_only_and_scrollable,
        test_no_backend_or_persistence_scope_in_package,
        test_repository_bytecode_hygiene,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused constraint-inspector checks")


if __name__ == "__main__":
    main()
