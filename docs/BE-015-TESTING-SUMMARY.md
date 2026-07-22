# BE-015 Testing Summary

Focused command:

```powershell
cd olden_db
python -m scripts.test_multi_objective_planning
```

This checks immutability, duplicate normalization, deterministic ordering,
validation separation, integrated scheduling, provenance, and one-objective
compatibility.

Run the repository's full existing test suite afterward. This package does not
claim local runtime execution; the Project Owner supplies runtime evidence.
