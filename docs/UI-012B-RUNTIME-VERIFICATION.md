# UI-012B Runtime Verification

From the repository root:

```powershell
python apply_ui012b_hotfix.py
cd olden_db
python -m scripts.test_desktop_build_plan_explanation
python -m scripts.run_desktop
```

Expected focused-test output additionally includes:

```text
PASS: test_selection_reentrancy_is_bounded
```

Generate a multi-step plan and click each row repeatedly. The application must
remain responsive, the explanation must update once per semantic selection, and
no repeated callback traceback or continuous CPU use should occur.

Also test Up/Down plus Enter or Space and automatic replanning.
