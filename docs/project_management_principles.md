# Project Management Principles

## Purpose

This document defines the enduring project-management principles for the Heroes of Might & Magic: Olden Era Build Planner.

These principles guide roadmap decisions, work-order design, role coordination, acceptance, and the balance between product delivery and technical governance.

They apply unless superseded by a later repository-approved governance decision.

## 1. Product Goal

The project exists to provide a fast, trustworthy, and understandable planning workspace for players.

The application should make it easy to:

- select desired buildings;
- see valid build orders;
- understand total and per-day resource costs;
- revise a plan with minimal friction;
- compare or coordinate plans across multiple bases;
- understand why a requested plan succeeds or fails.

The planner engine, architecture, diagnostics, scenarios, testing, and documentation all exist to support this product goal.

## 2. Player Workflow Drives the Roadmap

Roadmap priorities should be stated in terms of what the player can accomplish, not only in terms of internal technical capabilities.

The primary near-term workflow is interactive planning:

1. The player changes planning selections.
2. The application updates automatically.
3. The current build order, costs, schedule, and diagnostics remain visible.
4. The player can revise the plan without repeatedly submitting a separate generation action.

The next major product capability is multi-base planning, initially supporting two bases and designed to scale to as many as five.

For each base, the workspace should ultimately provide:

- selected buildings;
- legal build order or orders;
- per-base total cost;
- per-base daily cost;
- per-base schedule.

The workspace should also provide combined resource requirements across all active bases.

Visualization, including charts, is valuable but secondary to a clear and correct planning workflow.

## 3. Repository Authority

The GitHub `main` branch is the authoritative engineering baseline.

Repository documentation defines current project standards. Conversation history may explain how a decision was reached, but it does not override repository truth.

When governance records and repository state diverge, Project Management must reconcile the records to the repository.

## 4. Governance Enables Delivery

Governance is valuable when it:

- clarifies ownership;
- prevents architectural drift;
- protects correctness;
- improves maintainability;
- makes future work easier;
- supports confident delivery.

Governance must not become a substitute for product progress.

A governance task should not block unrelated product work unless the unresolved issue creates a concrete risk to correctness, safety, architecture, or delivery.

## 5. Prefer Evolution Over Redesign

The project should evolve existing conventions where practical.

New structures, abstractions, documents, or processes should be introduced only when they remove a real ambiguity, support a planned capability, or reduce meaningful risk.

Project Management should resist broad redesigns when a smaller additive change can meet the same need.

## 6. Product Value Before Architectural Perfection

Architecture must remain coherent, but perfection is not the acceptance standard.

When an implementation:

- satisfies the product requirement;
- respects active architectural boundaries;
- is testable;
- is maintainable;
- avoids known correctness defects;

it should not be delayed solely for speculative elegance.

Technical debt should be recorded and prioritized alongside product work. It should neither be ignored nor automatically treated as more urgent than player-facing value.

## 7. Interaction Independence

The application must model player intent rather than a specific UI control.

Checkboxes are the preferred initial selection mechanism because they are simple, dependable, and do not depend on future art assets. Their use does not make checkbox state a backend or domain concept.

Planning contracts should use semantic concepts such as selected buildings, planning selections, active city plans, and workspace state.

This preserves the option to add drag-and-drop, search, menus, or other interaction models later without redesigning the planner.

## 8. Automatic Feedback Is a Core Product Principle

The planning workspace should feel responsive rather than transactional.

Where performance and correctness permit, changes to planning selections should automatically update:

- build-order results;
- total cost;
- per-day cost;
- resource breakdown;
- completion information;
- diagnostics.

A separate Generate action should not remain necessary for ordinary planning edits once interactive planning is implemented.

Debouncing or similar UI techniques may be used if needed, but they must not alter the semantic planning model.

## 9. Multi-Base Planning Is an N-Base Workspace

The architecture should not model the future feature as a special two-base planner.

It should model a planning workspace containing a collection of city or base plans.

The initial product release may expose two bases, but the architecture should support increasing the limit to five without replacing the core model.

Per-base results and combined results must remain distinguishable.

## 10. Clear Role Ownership

Project Management owns roadmap, priority, scope, sequencing, governance, and acceptance.

Architecture Engineering owns architectural records and structural consistency.

Backend Engineering owns domain behavior, planner behavior, Query Layer implementation, and backend validation.

UI Engineering owns presentation, interaction, accessibility implementation, and UI validation instructions.

QA owns independent static certification, regression analysis, architecture review, repository hygiene, and test-quality assessment.

The Project Owner performs local runtime validation using commands and scenarios supplied by the implementing engineer.

Roles should not duplicate one another's work without a specific reason.

## 11. Runtime Verification Is Collaborative

Runtime verification is not delegated to QA.

The implementing engineer supplies exact commands, expected behavior, and test scenarios. The Project Owner runs them locally and reports observations. The engineer diagnoses any failures. Project Management incorporates those results into acceptance.

QA may identify runtime risks, but it must not claim runtime certification from source inspection.

## 12. Evidence-Based Status

Reports must distinguish:

- confirmed repository facts;
- executed validation results;
- static findings;
- inferences;
- recommendations;
- unresolved ambiguity;
- tooling limitations.

No role should present illustrative screenshots, source-token checks, or inferred behavior as runtime proof.

## 13. Documentation Should Be Proportional

Documentation should preserve decisions that future contributors need to know.

Update an existing canonical document when a change refines an existing subsystem. Create a new document when the subject is independently important, likely to grow, or would make an existing document unclear.

Temporary delivery reports, patch utilities, and one-off artifacts should not become permanent canonical documentation without a clear maintenance purpose.

## 14. Work Orders Should Match the Risk

Major features, architecture changes, cross-team work, and governance changes require formal work orders.

Small fixes and contained improvements may use shorter assignments.

Every assignment must still define:

- objective;
- scope;
- constraints;
- required validation;
- deliverables;
- ownership;
- acceptance conditions.

Process weight should be proportional to implementation risk.

## 15. Current Product Priorities

Unless changed by a later roadmap decision, the current priority order is:

1. Interactive planning workspace
2. Automatically updating plan summary
3. Build-order and daily-cost presentation
4. Multi-base planning, beginning with two bases and scaling to five
5. Combined resource accounting across bases
6. Resource timeline and visualization
7. Optimization modes

Optimization and advanced visualization should not displace the basic interactive planning workflow.

## 16. Decision Test

Before approving a significant task, Project Management should ask:

1. What player problem does this solve?
2. Is it required for a planned capability?
3. Does it preserve repository and architectural truth?
4. Is the proposed process proportional to the risk?
5. Can the result be validated clearly?
6. Does it move the product forward, or only make the process more elaborate?

A task that cannot answer these questions should be revised, deferred, or rejected.
