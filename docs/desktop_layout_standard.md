# Desktop Layout and Scrolling Standard

## Purpose

This document defines the shared responsive-layout and scrolling behavior for
the tkinter desktop application. It supplements
`desktop_application_architecture.md` and
`desktop_application_workflows.md`.

## Supported Window Sizes

The desktop shell uses:

- default geometry: `1100 × 700`;
- minimum operational geometry: `960 × 640`.

Larger windows should use the available space. The application must remain
operational at the minimum size through vertical scrolling rather than by
hiding primary actions or requiring fullscreen mode.

## Shell Ownership

`desktop/app.py` owns:

- root geometry and minimum dimensions;
- navigation;
- workspace replacement;
- activation and deactivation of workspace scrolling;
- clean shutdown.

Every workspace is placed inside one `ScrollableWorkspace`. The workspace
container expands with the root window and keeps its inner content width equal
to the visible canvas width.

## Wheel-Event Scope

Supported wheel sequences are:

- `<MouseWheel>`;
- `<Button-4>`;
- `<Button-5>`.

Wheel handlers are workspace-scoped. The active workspace attaches handlers to
its current descendants. Navigation deactivates the prior workspace and removes
those handlers before activating the next workspace.

Do not use permanent `bind_all` wheel handlers. Dynamic workspace content may
request a binding refresh after adding or replacing widgets.

Nested text and list controls retain their own scrolling while they can still
scroll. The outer workspace receives the wheel when the nested control reaches
its vertical boundary.

## Responsive Workspaces

### Build Planner

The selected target and starting-state context remain above results. The whole
workspace can scroll vertically, while long scenario and result regions retain
their focused internal scrollbars.

### Plan Comparison

Comparison uses two deterministic layouts:

- wide: Left and Right panels side by side;
- narrow: Left and Right panels stacked vertically.

The transition depends only on available viewport width and must not alter
selection, scenario, comparison, or decision-summary state.

### Economy Timeline

Planning context and starting resources remain at the top. Recruitment controls
and ledger output remain accessible through workspace scrolling at reduced
window heights.

Resize events must not regenerate ledgers, plans, comparisons, or summaries.

## Information Density

Economy event costs show only nonzero resources. Authoritative balances and
summary totals remain complete resource vectors and are never changed or
recalculated for layout purposes.

## State Preservation

Resizing and workspace switching are presentation operations only. They must
not clear or replace:

- planner target;
- planner scenario;
- comparison-side targets or scenarios;
- Decision Summary;
- starting treasury;
- recruitment schedule.

Existing workflow-specific invalidation rules remain authoritative.

## Validation

Responsive validation should verify contracts rather than pixel-perfect
screenshots:

- root minimum size and default geometry;
- weighted `nsew` shell expansion;
- wheel sequence support and cleanup;
- absence of permanent global wheel bindings;
- deterministic narrow/wide comparison layout;
- primary-action presence;
- nonzero event-cost formatting;
- absence of backend calls in resize and workspace-layout methods.

Manual checks remain required at the accepted size and aspect-ratio matrix.
