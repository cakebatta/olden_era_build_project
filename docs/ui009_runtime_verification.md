# UI-009 Runtime Verification

Run from `olden_db`:

```powershell
python -m scripts.run_desktop
```

Verify:

1. Startup opens one primary scenario panel.
2. Add Empty Scenario creates a distinct empty workspace.
3. Complete selections in two panels; each plans independently.
4. Editing one panel does not alter another panel's selection, lifecycle, result, timeline, failure, or diagnostics.
5. Duplicate copies semantic inputs, receives a new identity, and runs its own automatic lifecycle.
6. Remove a non-primary workspace; remaining identities and results remain unchanged.
7. Edit labels without triggering planning.
8. Assign and reassign Left/Right roles without triggering planning.
9. Pending, failure, and retained-result states remain workspace-local.
10. Horizontal scrolling and focus traversal make all panels reachable.
11. Primary scenario persistence and economy context still operate.
12. Existing Planning Summary, timeline, diagnostics, and legacy plan-comparison behavior remain intact.

Run:

```powershell
python -m scripts.test_desktop_scenario_comparison_workspace
python -m scripts.test_desktop_scenario_comparison_integration
python -m scripts.test_scenario_comparison_collection
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
