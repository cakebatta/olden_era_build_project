# UI-012 Runtime Verification

From the repository root:

```powershell
python apply_ui012.py
cd olden_db
python -m scripts.test_desktop_build_plan_explanation
python -m scripts.run_desktop
```

Generate a multi-step plan. Select each timeline step and verify all six sections.
Use arrow keys plus Enter or Space. Trigger replanning and verify a uniquely
retained building stays selected with refreshed facts, while removed steps clear.
Confirm retained explanations are identified as previous and requirement values
are never labeled as inventory.
