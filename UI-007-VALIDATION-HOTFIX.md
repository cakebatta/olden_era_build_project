# UI-007 Validation Hotfix

This hotfix addresses three issues found during Project Owner validation:

1. The desktop constructed `PlanningQueryService(canonical_data)`, which does
   not configure BE-011 localization. Startup now uses
   `PlanningQueryService.from_default_game_data()`.
2. The UI-007 view-boundary test falsely treated the presentation field
   `completion_date_text` as domain calculation. The assertion now rejects
   backend-object access while explicitly requiring supplied presentation text.
3. The legacy diagnostic pipeline `RecordingService` lacked the new documented
   Query Layer localization operation. The test double now implements it.

No planner, Query Layer, Planning Workspace, coordinator, presenter lifecycle,
or summary behavior changes are included.

Apply from the repository root:

```powershell
python apply_ui007_validation_hotfix.py
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

Remove `apply_ui007_validation_hotfix.py` after successful validation.
