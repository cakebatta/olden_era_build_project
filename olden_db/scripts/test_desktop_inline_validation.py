from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "olden_db" / "desktop"
VIEW_PATH = DESKTOP / "views" / "scenario_manager_view.py"
CONTROLLER_PATH = DESKTOP / "inline_validation_controller.py"
APP_PATH = DESKTOP / "app.py"


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def function_node(path, class_name, function_name):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == function_name:
                    return item
    raise AssertionError(f"Missing {class_name}.{function_name}")


def load_controller_class():
    package = types.ModuleType("olden_db")
    package.__path__ = []
    desktop = types.ModuleType("olden_db.desktop")
    desktop.__path__ = []
    base_module = types.ModuleType("olden_db.desktop.scenario_controller")

    class BaseController:
        def _candidate(self, action):
            self.base_candidate_calls.append(action)
            if self.candidate_error is not None:
                self.session.validation_issue = self.candidate_error
                self._refresh()
                self._fail(action, self.candidate_error)
                return None
            self.session.validation_issue = None
            return object()

        def _fail(self, action, exc):
            self.base_fail_calls.append((action, exc))
            return False

        def _refresh(self):
            self.view.set_title(self.session.display_name)

    base_module.ScenarioController = BaseController
    sys.modules.update({
        "olden_db": package,
        "olden_db.desktop": desktop,
        "olden_db.desktop.scenario_controller": base_module,
    })
    spec = importlib.util.spec_from_file_location(
        "olden_db.desktop.inline_validation_controller",
        CONTROLLER_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.InlineValidationScenarioController


class FakeIssue(Exception):
    path = "name"
    detail = "cannot be blank"


class FakeSession:
    def __init__(self):
        self.display_name = "Scenario *"
        self.validation_issue = None
        self.marked = 0

    def mark_ui_edited(self):
        self.marked += 1


class FakeView:
    def __init__(self):
        self.titles = []
        self.validation_states = []

    def set_title(self, value):
        self.titles.append(value)

    def set_validation_state(self, path, message):
        self.validation_states.append((path, message))


def controller_fixture():
    cls = load_controller_class()
    controller = object.__new__(cls)
    controller._applying = False
    controller.session = FakeSession()
    controller.view = FakeView()
    controller.base_candidate_calls = []
    controller.base_fail_calls = []
    controller.candidate_error = None
    return controller


def test_typing_does_not_validate():
    controller = controller_fixture()
    controller.on_user_edit()
    require(controller.session.marked == 1, "Typing must mark the session edited")
    require(controller.base_candidate_calls == [], "Typing must not construct a candidate")
    require(controller.view.validation_states[-1] == ("", ""), "Typing must not create validation feedback")


def test_failed_commit_exposes_session_issue_after_dialog():
    controller = controller_fixture()
    issue = FakeIssue()
    controller.candidate_error = issue
    result = controller._candidate("Save")
    require(result is None, "Invalid candidate should fail")
    require(controller.session.validation_issue is issue, "Session must retain the domain issue")
    require(controller.base_fail_calls == [("Save", issue)], "Existing error path must run once")
    require(controller.view.validation_states[-1] == ("name", "cannot be blank"), "View must receive field metadata")


def test_successful_candidate_clears_feedback():
    controller = controller_fixture()
    controller.session.validation_issue = FakeIssue()
    result = controller._candidate("Save")
    require(result is not None, "Valid candidate should be returned")
    require(controller.view.validation_states[-1] == ("", ""), "Successful reconstruction must clear feedback")


def test_view_has_precreated_field_feedback():
    source = VIEW_PATH.read_text(encoding="utf-8")
    for field in ("name", "description", "notes"):
        require(f'"{field}": self._' in source, f"Missing {field} validation mapping")
    require("after_idle(widget.focus_set)" in source, "First invalid field must receive focus")
    require("add_command" not in source[source.index("def set_validation_state"):source.index("def choose_unsaved_action")], "Repeated feedback must not create widgets")


def test_view_does_not_validate_on_edit():
    node = function_node(VIEW_PATH, "ScenarioManagerView", "_edited")
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
    require(len(calls) == 1, "Edit callback should only emit existing edit intent")


def test_app_uses_validation_controller():
    source = APP_PATH.read_text(encoding="utf-8")
    require("InlineValidationScenarioController" in source, "Desktop composition must use validation-aware controller")
    require("self.scenario_controller = ScenarioController(" not in source, "Composition must not bypass validation presentation adapter")


def main():
    tests = [
        test_typing_does_not_validate,
        test_failed_commit_exposes_session_issue_after_dialog,
        test_successful_candidate_clears_feedback,
        test_view_has_precreated_field_feedback,
        test_view_does_not_validate_on_edit,
        test_app_uses_validation_controller,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} focused inline-validation checks")


if __name__ == "__main__":
    main()
