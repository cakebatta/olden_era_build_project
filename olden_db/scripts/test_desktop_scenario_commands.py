from __future__ import annotations

import inspect

from olden_db.desktop.app import (
    DesktopApplication,
    scenario_shortcut_bindings,
)
from olden_db.desktop.scenario_controller import ScenarioController
from olden_db.desktop.views.scenario_manager_view import ScenarioManagerView


class IntentOnlyView:
    def __init__(self):
        self.handlers = {}
        self.enabled = {key: True for key in (
            "new", "open", "save", "save_as", "rename", "duplicate",
            "import", "export", "delete",
        )}

    def invoke_command(self, key):
        if not self.enabled[key]:
            return False
        handler = self.handlers.get(key)
        if handler is None:
            return False
        handler()
        return True


class ShortcutApplication:
    _dispatch_scenario_command = DesktopApplication._dispatch_scenario_command

    def __init__(self, view):
        self.scenario_manager_view = view


def main() -> None:
    calls = []
    view = ScenarioManagerView.__new__(ScenarioManagerView)
    view._command_enabled = {key: True for key in (
        "new", "open", "save", "save_as", "rename", "duplicate",
        "import", "export", "delete",
    )}
    view._handlers = {
        key: (lambda command=key: calls.append(command))
        for key in view._command_enabled
    }

    for key in view._command_enabled:
        assert view.invoke_command(key) is True
    assert calls == list(view._command_enabled)

    calls.clear()
    application = ShortcutApplication(view)
    for key in ("new", "open", "save", "save_as"):
        assert application._dispatch_scenario_command(key) == "break"
    assert calls == ["new", "open", "save", "save_as"]

    view._command_enabled["save"] = False
    calls.clear()
    assert application._dispatch_scenario_command("save") == "break"
    assert calls == []

    assert scenario_shortcut_bindings("win32") == (
        ("<Control-n>", "new"),
        ("<Control-o>", "open"),
        ("<Control-s>", "save"),
        ("<Control-Shift-S>", "save_as"),
    )
    assert scenario_shortcut_bindings("aqua") == (
        ("<Command-n>", "new"),
        ("<Command-o>", "open"),
        ("<Command-s>", "save"),
        ("<Command-Shift-S>", "save_as"),
    )

    view_source = inspect.getsource(ScenarioManagerView)
    required_hierarchy = (
        'PRIMARY_COMMANDS = (',
        '("New", "new")',
        '("Open", "open")',
        '("Save", "save")',
        'text="Scenario ▾"',
        'self._scenario_menu.add_separator()',
        '("Save As…", "save_as", "save_as")',
        '"Command+Shift+S"',
        '"Ctrl+Shift+S"',
        '("Rename…", "rename", "")',
        '("Duplicate…", "duplicate", "")',
        '("Import…", "import", "")',
        '("Export…", "export", "")',
        '("Delete…", "delete", "")',
        'width=1',
        'takefocus=True',
    )
    missing = tuple(
        fragment
        for fragment in required_hierarchy
        if fragment not in view_source
    )
    if missing:
        raise RuntimeError(f"Scenario command hierarchy missing: {missing!r}")

    if len(ScenarioManagerView.PRIMARY_COMMANDS) != 3:
        raise RuntimeError("Persistent header must expose exactly three buttons")
    if view_source.count("ttk.Button(") != 1:
        raise RuntimeError("Primary commands must share one button construction path")
    if "LocalScenarioRepository" in view_source:
        raise RuntimeError("View initiated repository ownership")
    if any(fragment in view_source for fragment in (
        "save_scenario(", "delete_scenario(", "import_scenario(", "Path("
    )):
        raise RuntimeError("View contains persistence or filesystem behavior")

    app_source = inspect.getsource(DesktopApplication._bind_shortcuts)
    dispatch_source = inspect.getsource(
        DesktopApplication._dispatch_scenario_command
    )
    if "bind_all" not in app_source:
        raise RuntimeError("Shortcuts are not application-level")
    if 'return "break"' not in dispatch_source:
        raise RuntimeError("Shortcut propagation is not stopped")
    if "invoke_command(key)" not in dispatch_source:
        raise RuntimeError("Shortcuts bypass the visible-command intent path")

    controller_initialize = inspect.getsource(ScenarioController.initialize)
    for key in view._command_enabled:
        if f'"{key}": self.' not in controller_initialize:
            raise RuntimeError(f"Controller handler route missing: {key}")

    controller_source = inspect.getsource(ScenarioController)
    required_protections = (
        "self._protect()",
        "ScenarioConflictError",
        "mark_invalid_edit",
        "reconcile_dirty_state",
        "detach_after_delete",
    )
    missing_protections = tuple(
        fragment
        for fragment in required_protections
        if fragment not in controller_source
    )
    if missing_protections:
        raise RuntimeError(
            f"Controller regression contracts missing: {missing_protections!r}"
        )

    print("Desktop scenario command hierarchy validation completed successfully.")
    print("Three primary commands and one grouped Scenario menu are present.")
    print("Visible commands and shortcuts share one intent-routing path.")
    print("Controller/session lifecycle ownership remains unchanged.")


if __name__ == "__main__":
    main()
