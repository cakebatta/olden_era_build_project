from __future__ import annotations

import ast
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXPECTED_HEAD = "19de06c360df2023a1335b3f007ca0e136cdfde1"
PRESENTER = ROOT / "olden_db/olden_db/desktop/presenters/planner_presenter.py"
VIEW = ROOT / "olden_db/olden_db/desktop/views/planner_view.py"
TIMELINE = ROOT / "olden_db/olden_db/desktop/planning_timeline.py"
WORKSPACE_PRESENTATION = ROOT / "olden_db/olden_db/desktop/workspace_presentation.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        print(f"SKIP: {label}")
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    print(f"UPDATED: {label}")
    return text.replace(old, new, 1)


def verify() -> None:
    actual = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if actual != EXPECTED_HEAD:
        raise RuntimeError(
            "Repository HEAD does not match the synchronized UI-012 baseline.\n"
            f"Expected: {EXPECTED_HEAD}\nActual:   {actual}"
        )


def patch_timeline() -> None:
    text = TIMELINE.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from dataclasses import dataclass\n",
        "from dataclasses import dataclass\n\nfrom .build_plan_explanation import BuildStepIdentity\n",
        "timeline identity import",
    )
    text = replace_once(
        text,
        "class TimelineStepPresentation:\n    step_number: int\n",
        "class TimelineStepPresentation:\n    identity: BuildStepIdentity\n    step_number: int\n",
        "timeline identity field",
    )
    ast.parse(text, filename=str(TIMELINE))
    TIMELINE.write_text(text, encoding="utf-8")


def patch_workspace() -> None:
    text = WORKSPACE_PRESENTATION.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from .planner_diagnostics import PlannerDiagnosticPresentation\n",
        "from .build_plan_explanation import (\n"
        "    BuildPlanExplanationPresentation,\n"
        "    EMPTY_BUILD_PLAN_EXPLANATION,\n"
        ")\n"
        "from .planner_diagnostics import PlannerDiagnosticPresentation\n",
        "workspace explanation import",
    )
    text = replace_once(
        text,
        "    timeline: BuildPlanTimelinePresentation = EMPTY_BUILD_PLAN_TIMELINE\n",
        "    timeline: BuildPlanTimelinePresentation = EMPTY_BUILD_PLAN_TIMELINE\n"
        "    explanation: BuildPlanExplanationPresentation = EMPTY_BUILD_PLAN_EXPLANATION\n",
        "workspace explanation field",
    )
    ast.parse(text, filename=str(WORKSPACE_PRESENTATION))
    WORKSPACE_PRESENTATION.write_text(text, encoding="utf-8")


def patch_presenter() -> None:
    text = PRESENTER.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from olden_db.models import BuildingKey, BuildingLevel\n",
        "from olden_db.models import BuildingKey, BuildingLevel\n"
        "from olden_db.objective_planning import (\n"
        "    BuildingCompletionObjective,\n"
        "    ObjectivePlanningFailure,\n"
        "    ObjectiveSet,\n"
        "    TownPlanningRequest,\n"
        "    TownState,\n"
        ")\n",
        "objective contract imports",
    )
    text = replace_once(
        text,
        "from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\n",
        "from ..build_plan_explanation import (\n"
        "    BuildPlanExplanationPresentation,\n"
        "    BuildStepIdentity,\n"
        "    ExplanationPanelStatus,\n"
        "    ExplanationSectionPresentation,\n"
        ")\n"
        "from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\n",
        "explanation imports",
    )
    text = replace_once(
        text,
        "    def render_workspace(\n"
        "        self,\n"
        "        presentation: PlanningWorkspacePresentation,\n"
        "    ) -> None: ...\n",
        "    def render_workspace(\n"
        "        self,\n"
        "        presentation: PlanningWorkspacePresentation,\n"
        "    ) -> None: ...\n"
        "    def restore_build_step_focus(self, identity: BuildStepIdentity | None) -> None: ...\n",
        "focus contract",
    )
    text = replace_once(
        text,
        "        self._faction_text_cache: dict[str, str] = {}\n",
        "        self._faction_text_cache: dict[str, str] = {}\n"
        "        self._selected_build_step: BuildStepIdentity | None = None\n"
        "        self._objective_view_cache: dict[tuple[object, int], object] = {}\n",
        "presenter explanation state",
    )
    text = replace_once(
        text,
        "            on_reset_scenario=self.on_reset_scenario,\n",
        "            on_reset_scenario=self.on_reset_scenario,\n"
        "            on_build_step_selected=self.on_build_step_selected,\n"
        "            on_build_step_selection_cleared=self.on_build_step_selection_cleared,\n",
        "semantic handlers",
    )
    methods = '''    def on_build_step_selected(self, identity: BuildStepIdentity) -> None:
        base = self._workspace.base(identity.base_plan_id)
        if base.result_revision != identity.result_revision:
            return
        explanation_view = self._objective_view_for(base)
        if explanation_view is None:
            return
        if not any(
            step.step_number == identity.step_number
            and step.building == identity.building
            for step in explanation_view.build_steps
        ):
            return
        self._selected_build_step = identity
        self._render_snapshot(self._workspace.snapshot())
        self._view.restore_build_step_focus(identity)

    def on_build_step_selection_cleared(self) -> None:
        self._selected_build_step = None
        self._render_snapshot(self._workspace.snapshot())

'''
    text = replace_once(text, "    def on_generate_plan(self) -> None:\n", methods + "    def on_generate_plan(self) -> None:\n", "selection methods")
    text = replace_once(
        text,
        "            timeline=self._build_timeline(base=base, result=result),\n",
        "            timeline=self._build_timeline(base=base, result=result),\n"
        "            explanation=self._build_explanation(base),\n",
        "explanation projection",
    )
    text = replace_once(
        text,
        "        if presentation != self._last_workspace_presentation:\n"
        "            self._view.render_workspace(presentation)\n"
        "            self._last_workspace_presentation = presentation\n",
        "        if presentation != self._last_workspace_presentation:\n"
        "            self._view.render_workspace(presentation)\n"
        "            self._last_workspace_presentation = presentation\n"
        "        self._view.restore_build_step_focus(presentation.explanation.selected_step)\n",
        "focus restoration",
    )
    text = replace_once(
        text,
        "            TimelineStepPresentation(\n"
        "                step_number=step.step_number,\n",
        "            TimelineStepPresentation(\n"
        "                identity=BuildStepIdentity(\n"
        "                    base_plan_id=base.base_id,\n"
        "                    result_revision=base.result_revision,\n"
        "                    step_number=step.step_number,\n"
        "                    building=step.building,\n"
        "                ),\n"
        "                step_number=step.step_number,\n",
        "timeline semantic identities",
    )
    helpers = '''    def _objective_view_for(self, base):
        if base.accepted_result is None or base.result_revision is None or base.selection is None:
            return None
        cache_key = (base.base_id, base.result_revision)
        cached = self._objective_view_cache.get(cache_key)
        if cached is not None:
            return cached
        selection = base.selection
        request = TownPlanningRequest(
            TownState(
                faction=selection.faction,
                starting_date=selection.starting_date,
                planning_scenario=selection.scenario,
            ),
            ObjectiveSet((BuildingCompletionObjective(selection.target),)),
        )
        outcome = self._service.generate_objective_plan_view(request)
        if isinstance(outcome, ObjectivePlanningFailure):
            return None
        self._objective_view_cache[cache_key] = outcome
        return outcome

    def _reconcile_build_step_selection(self, base, explanation_view):
        selected = self._selected_build_step
        if selected is None:
            return None
        if selected.result_revision == base.result_revision:
            return selected
        matches = tuple(
            step for step in explanation_view.build_steps
            if step.building == selected.building
        )
        if len(matches) != 1:
            self._selected_build_step = None
            return None
        step = matches[0]
        rebound = BuildStepIdentity(
            base_plan_id=base.base_id,
            result_revision=base.result_revision,
            step_number=step.step_number,
            building=step.building,
        )
        self._selected_build_step = rebound
        return rebound

    def _build_explanation(self, base) -> BuildPlanExplanationPresentation:
        explanation_view = self._objective_view_for(base)
        if explanation_view is None or base.result_revision is None:
            self._selected_build_step = None
            return BuildPlanExplanationPresentation(
                base_plan_id=base.base_id,
                result_revision=base.result_revision,
                status=ExplanationPanelStatus.EMPTY,
                selected_step=None,
                heading="Build Step Explanation",
                sections=(),
                is_current_result=False,
                message="Select a construction step after a plan is accepted.",
            )
        selected = self._reconcile_build_step_selection(base, explanation_view)
        if selected is None:
            return BuildPlanExplanationPresentation(
                base_plan_id=base.base_id,
                result_revision=base.result_revision,
                status=ExplanationPanelStatus.EMPTY,
                selected_step=None,
                heading="Build Step Explanation",
                sections=(),
                is_current_result=base.result_is_current,
                message="Select a construction step to review why it appears in the accepted plan.",
            )
        step = next(
            (
                item for item in explanation_view.build_steps
                if item.step_number == selected.step_number
                and item.building == selected.building
            ),
            None,
        )
        if step is None:
            self._selected_build_step = None
            return BuildPlanExplanationPresentation(
                base_plan_id=base.base_id,
                result_revision=base.result_revision,
                status=ExplanationPanelStatus.EMPTY,
                selected_step=None,
                heading="Build Step Explanation",
                sections=(),
                is_current_result=base.result_is_current,
                message="The previously selected step is not present in the current plan.",
            )
        prerequisites = tuple(self._display_text(item) for item in step.prerequisite_buildings)
        supported = tuple(item.display_name for item in step.required_by_objectives)
        completed = tuple(item.display_name for item in step.objective_targets)
        downstream = tuple(self._display_text(item) for item in step.downstream_buildings_enabled)
        sections = (
            ExplanationSectionPresentation(
                "Build Information",
                (
                    f"Building: {step.display_name}",
                    f"Construction day: {format_game_date(step.construction_day)}",
                    f"Construction cost: {format_resource_cost(step.resource_cost)}",
                ),
            ),
            ExplanationSectionPresentation(
                "Construction Requirements",
                (
                    "Prerequisite buildings: " + (", ".join(prerequisites) if prerequisites else "None"),
                    "Remaining construction requirement before: " + format_resource_cost(step.resource_balance_before),
                    "Remaining construction requirement after: " + format_resource_cost(step.resource_balance_after),
                ),
            ),
            ExplanationSectionPresentation("Supported Objectives", supported or ("None",)),
            ExplanationSectionPresentation("Objectives Completed", completed or ("None",)),
            ExplanationSectionPresentation("Buildings Enabled", downstream or ("None",)),
            ExplanationSectionPresentation(
                "Economic Effects",
                ("Income change: " + format_resource_cost(step.income_change),),
            ),
        )
        retained = base.retains_previous_result
        return BuildPlanExplanationPresentation(
            base_plan_id=base.base_id,
            result_revision=base.result_revision,
            status=(
                ExplanationPanelStatus.RETAINED_PREVIOUS_RESULT
                if retained else ExplanationPanelStatus.READY
            ),
            selected_step=selected,
            heading=step.display_name,
            sections=sections,
            is_current_result=base.result_is_current,
            message=(
                "This explanation belongs to the Previous Accepted Plan."
                if retained else None
            ),
        )

'''
    text = replace_once(text, "    def _diagnostics_for(self, base):\n", helpers + "    def _diagnostics_for(self, base):\n", "explanation helpers")
    ast.parse(text, filename=str(PRESENTER))
    PRESENTER.write_text(text, encoding="utf-8")


def patch_view() -> None:
    text = VIEW.read_text(encoding="utf-8")
    text = replace_once(
        text,
        "from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\n",
        "from ..build_plan_explanation import (\n"
        "    BuildPlanExplanationPresentation,\n"
        "    BuildStepIdentity,\n"
        "    ExplanationPanelStatus,\n"
        ")\n"
        "from ..display_names import CanonicalDisplayOption, StartingBuildingPresentation\n",
        "view explanation imports",
    )
    text = replace_once(
        text,
        "        self._on_reset_scenario: Callable[[], None] | None = None\n",
        "        self._on_reset_scenario: Callable[[], None] | None = None\n"
        "        self._on_build_step_selected: Callable[[BuildStepIdentity], None] | None = None\n"
        "        self._on_build_step_selection_cleared: Callable[[], None] | None = None\n",
        "view handler state",
    )
    text = replace_once(
        text,
        "        self._timeline_tree.bind(\"<<TreeviewSelect>>\", self._handle_timeline_selection)\n",
        "        self._timeline_tree.bind(\"<<TreeviewSelect>>\", self._handle_timeline_selection)\n"
        "        self._timeline_tree.bind(\"<Return>\", self._activate_focused_timeline_step)\n"
        "        self._timeline_tree.bind(\"<space>\", self._activate_focused_timeline_step)\n",
        "keyboard activation",
    )
    panel = '''
        explanation = ttk.LabelFrame(results, text="Build Step Explanation", padding=(10, 8))
        explanation.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        explanation.columnconfigure(0, weight=1)
        explanation.rowconfigure(2, weight=1)
        self._explanation_heading_var = tk.StringVar(value="Build Step Explanation")
        self._explanation_message_var = tk.StringVar(
            value="Select a construction step to review why it appears in the accepted plan."
        )
        ttk.Label(
            explanation,
            textvariable=self._explanation_heading_var,
            font=("TkDefaultFont", 11, "bold"),
            justify="left",
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            explanation,
            textvariable=self._explanation_message_var,
            justify="left",
            wraplength=700,
        ).grid(row=1, column=0, sticky="ew", pady=(3, 6))
        self._explanation_text = tk.Text(
            explanation,
            height=13,
            wrap="word",
            state="disabled",
            takefocus=True,
            highlightthickness=2,
            highlightcolor="SystemHighlight",
        )
        self._explanation_text.tag_configure(
            "section",
            font=("TkDefaultFont", 10, "bold"),
            spacing1=8,
            spacing3=3,
        )
        explanation_scroll = tk.Scrollbar(
            explanation,
            orient="vertical",
            command=self._explanation_text.yview,
            width=18,
        )
        self._explanation_text.configure(yscrollcommand=explanation_scroll.set)
        self._explanation_text.grid(row=2, column=0, sticky="nsew")
        explanation_scroll.grid(row=2, column=1, sticky="ns")

'''
    text = replace_once(
        text,
        "        self._results_text = tk.Text(results, state=\"disabled\", height=1)\n",
        panel + "        self._results_text = tk.Text(results, state=\"disabled\", height=1)\n",
        "explanation panel",
    )
    text = replace_once(
        text,
        "        on_reset_scenario: Callable[[], None],\n    ) -> None:\n",
        "        on_reset_scenario: Callable[[], None],\n"
        "        on_build_step_selected: Callable[[BuildStepIdentity], None],\n"
        "        on_build_step_selection_cleared: Callable[[], None],\n"
        "    ) -> None:\n",
        "view handler contract",
    )
    text = replace_once(
        text,
        "        self._on_reset_scenario = on_reset_scenario\n",
        "        self._on_reset_scenario = on_reset_scenario\n"
        "        self._on_build_step_selected = on_build_step_selected\n"
        "        self._on_build_step_selection_cleared = on_build_step_selection_cleared\n",
        "view handler assignment",
    )
    text = replace_once(
        text,
        "        self._render_timeline(presentation.timeline)\n"
        "        self.set_diagnostics(presentation.diagnostics)\n",
        "        self._render_timeline(presentation.timeline)\n"
        "        self.render_explanation(presentation.explanation)\n"
        "        self.set_diagnostics(presentation.diagnostics)\n",
        "render explanation",
    )
    text = replace_once(
        text,
        "                iid=str(step.step_number),\n",
        "                iid=self._timeline_item_id(step.identity),\n",
        "semantic item ids",
    )
    old_auto = '''        if timeline.steps:
            first = str(timeline.steps[0].step_number)
            self._timeline_tree.selection_set(first)
            self._timeline_tree.focus(first)
            self._timeline_tree.see(first)
            self._show_timeline_step_detail(timeline.steps[0])
'''
    text = replace_once(text, old_auto, "", "remove view-owned default selection")
    old_handler = '''        step_number = int(selection[0])
        step = next(
            (item for item in timeline.steps if item.step_number == step_number),
            None,
        )
        if step is not None:
            self._show_timeline_step_detail(step)

    def _show_timeline_step_detail(self, step) -> None:
        self._timeline_detail_var.set(
            f"{step.position_text} — {step.completion_order_text} — "
            f"{step.building_name} {step.level_text} — "
            f"builds {step.construction_date_text}."
        )
'''
    new_handler = '''        item_id = selection[0]
        step = next(
            (
                item for item in timeline.steps
                if self._timeline_item_id(item.identity) == item_id
            ),
            None,
        )
        if step is not None and self._on_build_step_selected is not None:
            self._on_build_step_selected(step.identity)

    @staticmethod
    def _timeline_item_id(identity: BuildStepIdentity) -> str:
        building = identity.building
        return (
            f"{identity.base_plan_id.value}|{identity.result_revision}|"
            f"{identity.step_number}|{building.faction}|{building.sid}|{building.level}"
        )

    def _activate_focused_timeline_step(self, _event: tk.Event[tk.Misc]) -> str:
        focused = self._timeline_tree.focus()
        if focused:
            self._timeline_tree.selection_set(focused)
            self._handle_timeline_selection()
        return "break"

    def restore_build_step_focus(self, identity: BuildStepIdentity | None) -> None:
        if identity is None:
            self._timeline_tree.selection_remove(*self._timeline_tree.selection())
            return
        item_id = self._timeline_item_id(identity)
        if self._timeline_tree.exists(item_id):
            self._timeline_tree.selection_set(item_id)
            self._timeline_tree.focus(item_id)
            self._timeline_tree.see(item_id)

    def render_explanation(self, presentation: BuildPlanExplanationPresentation) -> None:
        self._explanation_heading_var.set(presentation.heading)
        message = presentation.message or (
            "Current accepted result."
            if presentation.status is ExplanationPanelStatus.READY
            else ""
        )
        self._explanation_message_var.set(message)
        self._explanation_text.configure(state="normal")
        self._explanation_text.delete("1.0", "end")
        for section in presentation.sections:
            self._explanation_text.insert("end", section.heading + "\\n", "section")
            for line in section.lines:
                self._explanation_text.insert("end", line + "\\n")
        if not presentation.sections and presentation.message:
            self._explanation_text.insert("end", presentation.message)
        self._explanation_text.configure(state="disabled")
        self._explanation_text.see("1.0")
'''
    text = replace_once(text, old_handler, new_handler, "semantic selection and panel rendering")
    ast.parse(text, filename=str(VIEW))
    VIEW.write_text(text, encoding="utf-8")


def patch_docs() -> None:
    section = (
        "\n\n## UI-012 Interactive Build Plan Explanation\n\n"
        "The presenter owns semantic BuildStepIdentity selection and accepted-result "
        "revision reconciliation. The passive view renders immutable explanation "
        "sections and forwards semantic timeline intent. Remaining before/after "
        "values are labeled as integrated construction requirements, not inventory.\n"
    )
    for relative in (
        "docs/desktop_application_architecture.md",
        "docs/planning_workspace_architecture.md",
    ):
        path = ROOT / relative
        if path.exists():
            text = path.read_text(encoding="utf-8")
            if "## UI-012 Interactive Build Plan Explanation" not in text:
                path.write_text(text.rstrip() + section, encoding="utf-8")
                print(f"UPDATED: {relative}")


def validate() -> None:
    for path in (
        PRESENTER,
        VIEW,
        TIMELINE,
        WORKSPACE_PRESENTATION,
        ROOT / "olden_db/olden_db/desktop/build_plan_explanation.py",
        ROOT / "olden_db/scripts/test_desktop_build_plan_explanation.py",
    ):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        print(f"PASS: syntax {path.relative_to(ROOT)}")


def main() -> None:
    verify()
    patch_timeline()
    patch_workspace()
    patch_presenter()
    patch_view()
    patch_docs()
    validate()
    print("UI-012 applied successfully.")


if __name__ == "__main__":
    main()
