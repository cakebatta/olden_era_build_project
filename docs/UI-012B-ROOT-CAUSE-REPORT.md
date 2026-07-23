# UI-012B Root Cause Report

Selecting a timeline row emitted `<<TreeviewSelect>>`, causing the view to send
`BuildStepIdentity` to the presenter. The presenter accepted it, rerendered the
workspace, and restored focus programmatically. `Treeview.selection_set(...)`
could emit another selection event for the same identity, re-entering the
presenter indefinitely.

The synchronous callback loop blocked Tk's event loop and caused Windows to mark
the application as not responding.

UI-012B bounds the loop at both ownership layers:

- the presenter treats selection of the already-selected immutable identity as a
  no-op;
- the view changes Treeview selection only when the desired semantic item is not
  already selected;
- the redundant presenter-side focus restoration after `_render_snapshot()` is
  removed, leaving one deterministic restoration path.

No planning or Query Layer behavior is changed.
