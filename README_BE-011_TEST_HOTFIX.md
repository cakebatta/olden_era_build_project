# BE-011 Regression-Test Hotfix

This updates only:

`olden_db/scripts/test_planner_diagnostic_pipeline.py`

It aligns the BE-009 presenter integration tests with the UI-006 Planning
Workspace constructor and `render_workspace(...)` contract.

Run from the repository root:

```text
python apply_be_011_test_hotfix.py
```

Then, from `olden_db`:

```text
python -m scripts.test_planner_diagnostic_pipeline
```

No production files are changed.
