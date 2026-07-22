# BE-016 Runtime Verification

Apply and test:

```powershell
python apply_be_016.py
cd olden_db
python -m scripts.test_multi_objective_query_layer
```

Then run the complete existing test suite and launch the desktop application
using the repository's established command.

Confirm manually that:

- every objective has a non-empty localized display name;
- every objective has one completion and provenance record;
- every plan step has canonical identity and localized text;
- supporting objectives agree with objective-facing required buildings;
- repeated calls return equal immutable views;
- the final remaining construction-cost balance is zero;
- income changes equal canonical building income;
- existing single-target planning and desktop behavior remain unchanged.
