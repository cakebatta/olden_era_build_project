# UI-006 Interactive Planning Workspace Runtime Verification

Run from the repository root:

```powershell
python apply_ui006.py
cd olden_db
python -m scripts.test_desktop_planning_workspace_presenter
python -m scripts.test_desktop_planning_workspace_integration
python -m scripts.test_planning_workspace
python -m scripts.test_desktop_planner_diagnostic_inspector
python -m olden_db.desktop
```

In the running application, verify that startup succeeds; selecting faction,
building, and level plans automatically; starting-date and scenario changes
replan automatically; pending, ready, failed, and retained-previous-result
states are visible; failures do not open traceback dialogs; repeated distinct
changes advance revisions; equivalent selections do not execute twice; the
Generate button is absent; and only one workspace entry is exposed.

The coordinator remains synchronous. The view flushes Tkinter idle presentation
before execution so pending state can be painted without introducing threads,
async execution, debounce, or an event bus.
