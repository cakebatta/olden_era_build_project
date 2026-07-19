# Planner Diagnostic Integration Tests

BE-009 adds executable architectural integration coverage for the planner
diagnostic pipeline without starting Tkinter or inspecting rendered widgets.

## Executable coverage

Run from the repository's `olden_db` directory:

```text
python -m scripts.test_planner_diagnostic_pipeline
```

The integration script executes the following boundaries:

```text
Planner
→ PlannerResult or PlanningFailure
→ Query Layer
→ PlannerPresenter
→ desktop diagnostic adapter
→ recording view contract
```

It verifies:

- every current planner diagnostic creation branch;
- canonical code, category, explanation, affected entities, and metadata;
- `PlannerResult` diagnostic transport;
- `PlanningFailure` diagnostic transport;
- Query Layer propagation without replacement or translation;
- presenter use of `generate_planner_result`;
- successful and failed presenter orchestration;
- adapter explanation preservation and stable ordering;
- delivery through `set_diagnostics` on a recording view;
- stale planner-state clearing after a failed attempt.

## Source-inspection reduction

`test_desktop_planner_diagnostic_inspector` now retains only checks that are
specific to the view source and are not covered by the executable architectural
test:

- explicit empty-state presence;
- supplied-order rendering;
- read-only widget choice;
- keyboard and scrolling hooks;
- syntax.

Source-string assertions for Query Layer delegation, result consumption,
failure transport, adapter translation, and presenter refresh behavior were
removed because those behaviors are now executed directly.

## Excluded validation

These tests intentionally do not cover:

- Tkinter startup;
- runtime widget rendering;
- layout or visual appearance;
- keyboard interaction at runtime;
- mouse interaction;
- manual accessibility validation.

Those concerns remain manual desktop validation responsibilities.
