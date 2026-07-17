# BE-025 Installation and Validation

Extract this archive into:

```text
C:\Users\BB BOBBY\Documents\GitHub\olden_era_build_project
```

Preserve the included directory structure.

## Files added

```text
olden_db/olden_db/scenario_persistence.py
olden_db/scripts/test_scenario_serialization.py
olden_db/scripts/test_scenario_validation.py
olden_db/scripts/test_scenario_repository.py
docs/scenario_persistence_implementation.md
```

No parser, planner, income, Recruitment Stock, Resource Ledger, Query Layer, or desktop production files are modified.

## Focused validation

```powershell
cd "C:\Users\BB BOBBY\Documents\GitHub\olden_era_build_project\olden_db"

python -m scripts.test_scenario_serialization
python -m scripts.test_scenario_validation
python -m scripts.test_scenario_repository
```

## Relevant regressions

```powershell
python -m scripts.test_query_scenarios
python -m scripts.test_query_resource_ledger
python -m scripts.test_query_income_resource_ledger
python -m scripts.test_resource_ledger
python -m scripts.test_desktop_income_timeline
```


## v2 repository-test correction

The original export assertion compared a `ScenarioLoadResult` directly with a
`ScenarioSaveResult`. Those are intentionally distinct immutable result types,
so dataclass equality is false even when both contain the same document and
conflict token. The corrected test compares their `document` and
`conflict_token` fields explicitly.

Production persistence code is unchanged.
