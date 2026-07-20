# UI-007 Validation Hotfix v3

This corrects the final two stale validation assertions:

- The planner-view boundary test now uses Python AST inspection, so presentation
  fields such as `completion_date_text` are not mistaken for backend access to
  `completion_date`.
- The diagnostic pipeline regression now validates the UI-007 nested
  `PlanningSummaryPresentation` contract instead of the removed UI-006
  `PlanningWorkspacePresentation.accepted_plan` field.

No production code is changed by this hotfix.

Apply from the repository root:

```powershell
python apply_ui007_validation_hotfix_v3.py
```

Then run from `olden_db`:

```powershell
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
