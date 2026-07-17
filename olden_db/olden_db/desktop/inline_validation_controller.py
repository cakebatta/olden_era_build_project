from __future__ import annotations

from .scenario_controller import ScenarioController


class InlineValidationScenarioController(ScenarioController):
    """Expose session-owned validation metadata to the desktop view."""

    def on_user_edit(self):
        """Record raw edits without constructing or validating a candidate."""
        if self._applying or not self.session:
            return
        self.session.mark_ui_edited()
        self._refresh()

    def _candidate(self, action):
        candidate = super()._candidate(action)
        if candidate is not None:
            self._refresh()
        return candidate

    def _fail(self, action, exc):
        result = super()._fail(action, exc)
        if self.session and self.session.validation_issue is exc:
            self._refresh()
        return result

    def _refresh(self):
        super()._refresh()
        issue = self.session.validation_issue if self.session else None
        self.view.set_validation_state(
            getattr(issue, "path", "") if issue else "",
            getattr(issue, "detail", str(issue)) if issue else "",
        )
