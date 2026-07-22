# BE-015 Runtime Verification

Apply and run:

```powershell
python apply_be_015.py
cd olden_db
python -m scripts.test_multi_objective_planning
```

Then run the repository's complete existing test suite and launch the desktop
application using the established command.

Confirm:
- duplicates normalize to one objective;
- input order does not alter result order;
- each build action appears once;
- every objective has completion data;
- each build step exposes reverse provenance;
- one-objective results equal existing single-target API results;
- existing desktop planning, scenarios, persistence, comparison, and localized
  presentation remain unchanged.
