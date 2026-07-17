from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import subprocess
import sys
import types


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = ROOT.parent
DESKTOP = ROOT / "olden_db" / "desktop"
VIEW_PATH = DESKTOP / "views" / "scenario_manager_view.py"
CONTROLLER_PATH = DESKTOP / "inline_validation_controller.py"
APP_PATH = DESKTOP / "app.py"
DOC_PATH = REPOSITORY_ROOT / "docs" / "desktop_scenario_manager.md"
IGNORE_PATH = REPOSITORY_ROOT / ".gitignore"


COMMIT_COMMANDS = ("save", "save_as", "rename", "duplicate", "delete", "export")
PENDING_TRANSITIONS = ("new", "open", "import_document", "can_close")


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
            self._refresh()
            return object()

        def _fail(self, action, exc):
            self.events.append(("dialog", action, exc))
            self.base_fail_calls.append((action, exc))
            return False

        def _refresh(self):
            self.view.set_title(self.session.display_name)

        def _protect(self):
            if not self.pending_transition_requires_save:
                return True
            self.events.append(("guard", self.pending_transition))
            return self.save()

        def save(self):
            return self._candidate("Save") is not None

        def save_as(self):
            return self._candidate("Save As") is not None

        def rename(self):
            return self._candidate("Rename") is not None

        def duplicate(self):
            return self._candidate("Duplicate") is not None

        def delete(self):
            return self._candidate("Delete") is not None

        def export(self):
            return self._candidate("Export") is not None

        def new(self):
            if not self._protect():
                return False
            self.events.append(("transition", "new"))
            return True

        def open(self):
            if not self._protect():
                return False
            self.events.append(("transition", "open"))
            return True

        def import_document(self):
            if not self._protect():
                return False
            self.events.append(("transition", "import"))
            return True

        def can_close(self):
            if not self._protect():
                return False
            self.events.append(("transition", "close"))
            return True

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


class DescriptionIssue(Exception):
    path = "description"
    detail = "must contain at most 500 Unicode code points"


class FakeSession:
    def __init__(self):
        self.display_name = "Scenario *"
        self.validation_issue = None
        self.marked = 0

    def mark_ui_edited(self):
        self.marked += 1


class FakeView:
    def __init__(self, events):
        self.events = events
        self.titles = []
        self.validation_states = []

    def set_title(self, value):
        self.titles.append(value)

    def set_validation_state(self, path, message):
        state = (path, message)
        self.validation_states.append(state)
        self.events.append(("validation", *state))


class FakeWidget:
    def __init__(self):
        self.focus_calls = 0
        self.configurations = []

    def focus_set(self):
        self.focus_calls += 1

    def configure(self, **kwargs):
        self.configurations.append(kwargs)


class FakeRoot:
    def __init__(self):
        self.idle_callbacks = []

    def after_idle(self, callback):
        self.idle_callbacks.append(callback)

    def run_idle(self):
        callbacks = list(self.idle_callbacks)
        self.idle_callbacks.clear()
        for callback in callbacks:
            callback()


class FakeMessage:
    def __init__(self):
        self.values = []

    def configure(self, **kwargs):
        self.values.append(kwargs)


def controller_fixture():
    cls = load_controller_class()
    controller = object.__new__(cls)
    controller._applying = False
    controller.session = FakeSession()
    controller.events = []
    controller.view = FakeView(controller.events)
    controller.base_candidate_calls = []
    controller.base_fail_calls = []
    controller.candidate_error = None
    controller.pending_transition_requires_save = False
    controller.pending_transition = None
    return controller


def validation_view_fixture():
    module_name = "olden_db.desktop.views.scenario_manager_view_cert"
    views_package = types.ModuleType("olden_db.desktop.views")
    views_package.__path__ = []
    dialog_module = types.ModuleType("olden_db.desktop.views.scenario_library_dialog")
    dialog_module.ScenarioLibraryDialog = type("ScenarioLibraryDialog", (), {})
    sys.modules["olden_db.desktop.views"] = views_package
    sys.modules["olden_db.desktop.views.scenario_library_dialog"] = dialog_module
    # The method is exercised without constructing Tk widgets. Importing the full
    # module is safe because widget creation occurs only in __init__.
    spec = importlib.util.spec_from_file_location(module_name, VIEW_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    view = object.__new__(module.ScenarioManagerView)
    view.root = FakeRoot()
    view.after_idle = view.root.after_idle
    view._validation_widgets = {
        "name": FakeWidget(),
        "description": FakeWidget(),
        "notes": FakeWidget(),
    }
    view._validation_labels = {
        "name": FakeMessage(),
        "description": FakeMessage(),
        "notes": FakeMessage(),
    }
    return view


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
    dialog_index = controller.events.index(("dialog", "Save", issue))
    final_validation_index = len(controller.events) - 1
    require(dialog_index < final_validation_index, "Focus feedback must be refreshed after the modal dialog returns")


def test_commit_lifecycle_commands_share_candidate_path():
    for method_name in COMMIT_COMMANDS:
        controller = controller_fixture()
        result = getattr(controller, method_name)()
        require(result is True, f"{method_name} should succeed with a valid candidate")
        require(len(controller.base_candidate_calls) == 1, f"{method_name} must reconstruct exactly once")
        require(controller.view.validation_states[-1] == ("", ""), f"{method_name} must clear stale feedback")


def test_pending_transitions_cancel_after_failed_save():
    for method_name in PENDING_TRANSITIONS:
        controller = controller_fixture()
        controller.pending_transition_requires_save = True
        controller.pending_transition = method_name
        controller.candidate_error = FakeIssue()
        result = getattr(controller, method_name)()
        require(result is False, f"{method_name} must stop when its guarded Save fails")
        require(controller.base_candidate_calls == ["Save"], f"{method_name} must use the normal Save candidate path")
        require(not any(event[0] == "transition" for event in controller.events), f"{method_name} must not complete its pending transition")
        require(controller.view.validation_states[-1][0] == "name", f"{method_name} must preserve inline validation state")


def test_validation_lifecycle_failure_repeat_success():
    controller = controller_fixture()
    controller.candidate_error = FakeIssue()
    require(controller.save() is False, "First invalid Save should fail")
    require(controller.save() is False, "Repeated invalid Save should fail")
    invalid_states = [state for state in controller.view.validation_states if state[0] == "name"]
    require(invalid_states and set(invalid_states) == {("name", "cannot be blank")}, "Repeated commits must reuse one logical field/message state")
    controller.candidate_error = None
    require(controller.save() is True, "Corrected Save should succeed")
    require(controller.session.validation_issue is None, "Successful reconstruction must clear the session issue")
    require(controller.view.validation_states[-1] == ("", ""), "Successful reconstruction must clear presentation")


def test_focus_restoration_and_clear_lifecycle():
    view = validation_view_fixture()
    view.set_validation_state("description", DescriptionIssue.detail)
    require(view._validation_widgets["description"].focus_calls == 0, "Focus should be deferred until the UI is idle")
    require(len(view.root.idle_callbacks) == 1, "Invalid field should schedule one focus restoration")
    view.root.run_idle()
    require(view._validation_widgets["description"].focus_calls == 1, "First invalid field must receive focus")
    view.set_validation_state("description", DescriptionIssue.detail)
    require(len(view.root.idle_callbacks) == 1, "Repeated failure must schedule one restoration, not create widgets")
    view.root.run_idle()
    view.set_validation_state("", "")
    require(len(view.root.idle_callbacks) == 0, "Clearing validation must not steal focus")
    for message in view._validation_labels.values():
        require(message.values[-1].get("text") == "", "Successful validation must clear every inline message")


def test_view_has_only_metadata_feedback_mappings():
    source = VIEW_PATH.read_text(encoding="utf-8")
    for field in ("name", "description", "notes"):
        require(f'"{field}": self._' in source, f"Missing {field} validation mapping")
    require("after_idle(widget.focus_set)" in source, "First invalid field must receive deferred focus")
    method_source = source[source.index("def set_validation_state"):source.index("def choose_unsaved_action")]
    require("ttk.Entry(" not in method_source and "ttk.Label(" not in method_source, "Repeated feedback must not construct new Tk widgets")
    docs = DOC_PATH.read_text(encoding="utf-8")
    require("only the metadata fields `name`," in docs, "Documentation must state the view's metadata-only scope")
    require("Other visible planner and economy inputs" in docs, "Documentation must not broaden view responsibility")


def test_view_does_not_validate_on_edit():
    node = function_node(VIEW_PATH, "ScenarioManagerView", "_edited")
    calls = [n for n in ast.walk(node) if isinstance(n, ast.Call)]
    require(len(calls) == 1, "Edit callback should only emit existing edit intent")


def test_adapter_remains_architecturally_narrow():
    source = CONTROLLER_PATH.read_text(encoding="utf-8")
    require("class InlineValidationScenarioController(ScenarioController)" in source, "Adapter must preserve controller inheritance")
    require("repository" not in source, "Inline validation adapter must not access persistence")
    require("mark_ui_edited()" in source, "Typing must retain raw edit tracking")
    require("self._build(" not in source, "Typing adapter must not reconstruct candidates")


def test_app_uses_validation_controller():
    source = APP_PATH.read_text(encoding="utf-8")
    require("InlineValidationScenarioController" in source, "Desktop composition must use validation-aware controller")
    require("self.scenario_controller = ScenarioController(" not in source, "Composition must not bypass validation presentation adapter")


def test_documentation_certifies_commit_only_reconstruction():
    docs = DOC_PATH.read_text(encoding="utf-8")
    require("Normal typing does not reconstruct a `ScenarioDocument`" in docs, "Docs must describe commit-only reconstruction")
    require("Save, Save As, Rename, Duplicate, Delete, and\nExport" in docs, "Docs must identify lifecycle commit operations")
    require("pending transition is\ncancelled" in docs, "Docs must describe failed guarded transitions")


def test_python_bytecode_hygiene():
    ignore = IGNORE_PATH.read_text(encoding="utf-8")
    require("__pycache__/" in ignore, "Ignore rules must exclude Python cache directories")
    require("*.py[cod]" in ignore or all(pattern in ignore for pattern in ("*.pyc", "*.pyo", "*.pyd")), "Ignore rules must exclude compiled Python files")
    if (REPOSITORY_ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "-C", str(REPOSITORY_ROOT), "ls-files", "*.pyc", "*.pyo", "*.pyd"],
            check=True,
            capture_output=True,
            text=True,
        )
        require(not result.stdout.strip(), "Committed Python bytecode artifacts must be removed")


def main():
    tests = [
        test_typing_does_not_validate,
        test_failed_commit_exposes_session_issue_after_dialog,
        test_commit_lifecycle_commands_share_candidate_path,
        test_pending_transitions_cancel_after_failed_save,
        test_validation_lifecycle_failure_repeat_success,
        test_focus_restoration_and_clear_lifecycle,
        test_view_has_only_metadata_feedback_mappings,
        test_view_does_not_validate_on_edit,
        test_adapter_remains_architecturally_narrow,
        test_app_uses_validation_controller,
        test_documentation_certifies_commit_only_reconstruction,
        test_python_bytecode_hygiene,
    ]
    for test in tests:
        test()
        print(f"PASS: {test.__name__}")
    print(f"PASS: {len(tests)} UI-015A certification checks")


if __name__ == "__main__":
    main()
