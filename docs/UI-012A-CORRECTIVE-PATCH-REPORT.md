# UI-012A Corrective Patch Report

Reviewed against repository `main` commit
`365f4853ec7ae065601d17db0b80ae6308cb5d15`.

UI-012 changed timeline Treeview item identifiers from numeric step numbers to
semantic `BuildStepIdentity` strings, but retained a legacy block that attempted
to select the numeric row `"1"` and call the removed
`_show_timeline_step_detail(...)` method.

That callback error interrupted `_render_timeline()` before
`_last_timeline_presentation` was assigned. Later row selections therefore had no
active immutable timeline model and returned without notifying the presenter.

UI-012A removes the obsolete automatic selection block. Selection remains
presenter-owned, and the view now completes timeline rendering before accepting
click or keyboard selection intent.

The focused test is expanded to reject numeric row selection, obsolete local
detail behavior, missing timeline-model caching, and failure to forward
`step.identity` to the presenter.
