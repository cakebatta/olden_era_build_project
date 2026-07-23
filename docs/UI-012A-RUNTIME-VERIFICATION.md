# UI-012A Runtime Verification

From the repository root:

```powershell
python apply_ui012a_hotfix.py
cd olden_db
python -m scripts.test_desktop_build_plan_explanation
python -m scripts.run_desktop
```

The focused test should additionally report:

```text
PASS: test_timeline_selection_event_flow_regression
```

Then generate a multi-step plan and verify:

1. Clicking each timeline row updates the explanation heading and all six sections.
2. Up/Down followed by Enter or Space updates the same explanation panel.
3. No Tk callback traceback appears in the launch terminal.
4. Replanning preserves or clears selection according to ARCH-023.
