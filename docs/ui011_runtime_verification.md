# UI-011 Runtime Verification

Run `python -m scripts.run_desktop` from `olden_db`.

Verify every supported faction. Faction selectors must show game-facing names; Hive must appear instead of demon. Target and Starting Building selectors must show localized building names while planning callbacks, scenario save/load, and selection restoration continue using canonical identities. Planning Summary, Timeline, and UI-010 comparison rows/action lists must show localized names. Review unit/recruitment surfaces for tiers 1 through 7. Missing localization must fall back without crashing.

```powershell
python -m scripts.test_desktop_canonical_game_names
python -m scripts.test_desktop_canonical_game_names_integration
python -m scripts.test_desktop_build_plan_comparison
python -m scripts.test_desktop_scenario_comparison_workspace
python -m scripts.test_desktop_planning_timeline
python -m scripts.test_desktop_planning_summary
python -m scripts.test_desktop_planning_workspace_presenter
python -m scripts.test_desktop_planning_workspace_integration
python -m scripts.test_planning_workspace
python -m scripts.test_planner_diagnostic_pipeline
```
