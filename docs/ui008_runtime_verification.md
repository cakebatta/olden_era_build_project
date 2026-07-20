# UI-008 Runtime Verification

Run `python -m scripts.run_desktop` from `olden_db`.

Verify accepted chronological rows, localized names, level, date, individual
cost, cumulative cost, retained previous-plan labeling during replanning,
failure retention, incomplete empty state, equivalent-selection no flicker,
keyboard/mouse row selection, and scenario restoration.

Run:

```powershell
python -m scripts.test_desktop_planning_timeline
python -m scripts.test_desktop_planning_timeline_integration
python -m scripts.test_desktop_planning_summary
python -m scripts.test_desktop_planning_summary_integration
python -m scripts.test_desktop_planning_workspace_presenter
python -m scripts.test_desktop_planning_workspace_integration
python -m scripts.test_planning_workspace
python -m scripts.test_desktop_planner_diagnostic_inspector
python -m scripts.test_planner_diagnostic_pipeline
```
