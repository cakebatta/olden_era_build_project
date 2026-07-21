# UI-010 Runtime Verification

Run from `olden_db`:

```powershell
python -m scripts.run_desktop
```

Verify:

1. With either Left or Right unassigned, the comparison panel displays `Comparison unavailable`; this is not an error.
2. Assign Left and Right to workspaces without current accepted plans. The panel displays a waiting or unavailable state without stack traces.
3. Complete both workspace selections. Comparison updates automatically without a Generate or Compare button.
4. Confirm the summary displays each completion date, each action count, signed right-minus-left deltas, and every canonical resource independently.
5. Confirm aligned rows appear exactly in backend order and show Matched, Different, Left Only, or Right Only.
6. Confirm Shared actions, Left-only actions, and Right-only actions match the BE-013 result.
7. Compare equivalent plans. Confirm zero deltas, matched rows only, no exclusive actions, and an equivalent-plan indication.
8. Compare empty vs empty, empty vs populated, and populated vs empty accepted plans. Empty plans must not appear as failures.
9. Edit either workspace. The previous successful comparison remains visible while replanning, then updates automatically after acceptance.
10. Remove or invalidate a required accepted result. The panel transitions cleanly to unavailable.
11. Reassign Left and Right. Role changes do not invoke planning, but comparison refreshes from the newly selected accepted plans.
12. Use keyboard focus and arrow navigation in the aligned table. Confirm long comparisons remain scrollable and resizing remains usable.

Run:

```powershell
python -m scripts.test_desktop_build_plan_comparison
python -m scripts.test_desktop_build_plan_comparison_integration
python -m scripts.test_desktop_scenario_comparison_workspace
python -m scripts.test_desktop_scenario_comparison_integration
python -m scripts.test_build_plan_comparison_service
python -m scripts.test_scenario_comparison_collection
python -m scripts.test_desktop_planning_timeline
python -m scripts.test_desktop_planning_summary
python -m scripts.test_desktop_planning_workspace_presenter
python -m scripts.test_desktop_planning_workspace_integration
python -m scripts.test_planning_workspace
python -m scripts.test_planner_diagnostic_pipeline
```
