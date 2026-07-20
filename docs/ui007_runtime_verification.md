# UI-007 Persistent Planning Summary Runtime Verification

From the repository root:

```powershell
python apply_ui007.py
cd olden_db
python -m scripts.test_desktop_planning_summary
python -m scripts.test_desktop_planning_summary_integration
python -m scripts.test_planning_summary_support
python -m scripts.test_desktop_planning_workspace_presenter
python -m scripts.test_desktop_planning_workspace_integration
python -m scripts.test_planning_workspace
python -m scripts.test_desktop_planner_diagnostic_inspector
python -m scripts.test_planner_diagnostic_pipeline
python -m scripts.run_desktop
```

Verify these visible states in the Build Planner:

1. At startup, `Persistent Planning Summary` is visible with `No accepted plan` and missing faction, target building, and target level.
2. Selecting only a faction keeps the summary visible and lists the remaining missing inputs.
3. Completing faction, building, and level briefly shows `Planning in progress`, then `Current Accepted Plan`.
4. A current result shows localized selected and displayed target text, starting date, construction-step count, completion date, total cost, daily construction schedule, and diagnostic summary.
5. Change the level, starting date, or a starting-building override. During replacement, the previous values remain visible under `Previous Accepted Plan` with a planning-in-progress message.
6. After successful replacement, the label changes to `Current Accepted Plan` and the replacement values appear.
7. Trigger an expected planning failure. The summary shows `Current request failed`, displays the failure without a traceback dialog, and retains the prior result as `Previous Accepted Plan` when available.
8. Trigger a first-request failure from a fresh session. No fabricated plan metrics or schedule should appear.
9. Restore a saved scenario document. The summary should transition as one semantic replacement without showing an intermediate partial selection as current.
10. Re-select an equivalent semantic selection. No additional execution, revision, summary clearing, or visible flicker should occur.
