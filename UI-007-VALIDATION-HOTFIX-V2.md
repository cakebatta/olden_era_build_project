# UI-007 Validation Hotfix v2

This replaces the original hotfix's brittle exact-whitespace test patch.

The first hotfix already updated desktop startup before stopping. This v2 utility is idempotent: it detects that completed change, skips it, and continues with the remaining test corrections.

Apply from the repository root:

```powershell
python apply_ui007_validation_hotfix_v2.py
```

Then, from `olden_db`, rerun:

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

Expected application messages include:

```text
SKIP: desktop localization-enabled Query Layer construction already applied
UPDATED: summary view-boundary regression
UPDATED: diagnostic RecordingService localization contract
UI-007 validation hotfix v2 applied.
```
