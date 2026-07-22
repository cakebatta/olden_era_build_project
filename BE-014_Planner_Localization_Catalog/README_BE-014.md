# BE-014 Delivery Package

Expected baseline:

`cb62414eaff8ced20cb74ec35e90f4a087bec747`

Extract into the repository root, then run:

```powershell
python apply_be_014.py
```

After application:

```powershell
cd olden_db
python -m scripts.test_planner_localization_catalog
```

Then follow `docs/be014_runtime_verification.md`.
