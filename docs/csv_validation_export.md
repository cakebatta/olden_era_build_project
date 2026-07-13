# CSV Validation Export

The CSV export is a developer validation tool. It serializes the connected backend data without changing parser or planner behavior.

From the `olden_db/` directory, run:

```bash
python scripts/export_validation_csvs.py
```

The command writes four deterministic files under `output/validation_csv/`:

- `buildings.csv`
- `units.csv`
- `building_dependency_graph.csv`
- `representative_plan.csv`

Rows are sorted by stable identifiers. Re-running the command against unchanged game data produces directly comparable output.
