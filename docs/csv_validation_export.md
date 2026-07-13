# CSV Validation Export

The CSV export is a developer validation tool. It serializes the connected backend data without changing parser or planner behavior.

From the `olden_db/` directory, run:

```bash
python -m scripts.export_validation_csvs
```

The command writes four deterministic files under `output/validation_csv/`:

- `buildings.csv`
- `units.csv`
- `building_dependency_graph.csv`
- `representative_plan.csv`

Rows are sorted by stable identifiers. Re-running the command against unchanged game data produces directly comparable output.

The `source` column in `units.csv` contains a logical game asset path rather than an absolute filesystem path. Canonical assets retain their path beginning at `Core/`; archive-backed sources retain both the logical archive path and the archive member separated by `!`. This keeps the field traceable while making exports portable across development machines.

Validate the export with:

```bash
python -m scripts.test_csv_export
```
