from __future__ import annotations
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUERY = ROOT / 'olden_db' / 'query.py'
PRESENTER = ROOT / 'olden_db' / 'desktop' / 'presenters' / 'planner_presenter.py'
VIEW = ROOT / 'olden_db' / 'desktop' / 'views' / 'planner_view.py'
ADAPTER = ROOT / 'olden_db' / 'desktop' / 'planner_diagnostics.py'


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def source(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def test_additive_query_contract() -> None:
    text = source(QUERY)
    require('def generate_planner_result(' in text, 'Missing additive Query Layer method')
    require('-> PlannerResult:' in text, 'Additive method must return PlannerResult')
    require('return plan_build_order_result(' in text, 'Query Layer must delegate to planner result API')
    require('def generate_build_plan(' in text and '-> BuildPlan:' in text, 'Compatibility API changed')


def test_presenter_consumes_result() -> None:
    text = source(PRESENTER)
    require('self._service.generate_planner_result(' in text, 'Presenter must use Query Layer result API')
    require('planner_result.plan' in text, 'Presenter must use canonical plan')
    require('adapt_planner_diagnostics(planner_result.diagnostics)' in text, 'Success diagnostics must use adapter')
    require('plan_build_order_result' not in text, 'Presenter must not call planner directly')


def test_failure_diagnostics() -> None:
    text = source(PRESENTER)
    require('getattr(exc, "diagnostics", ())' in text, 'Planning failure diagnostics missing')
    require('adapt_planner_diagnostics(tuple(diagnostics))' in text, 'Failure diagnostics must use adapter')


def test_empty_state() -> None:
    require('text="No diagnostics."' in source(VIEW), 'Explicit empty state missing')


def test_order_and_read_only() -> None:
    text = source(VIEW)
    require('for row, diagnostic in enumerate(self._diagnostics):' in text, 'Backend ordering must be preserved')
    block = text[text.index('    def set_diagnostics'):text.index('    def set_diagnostic_inspector_expanded')]
    require('.sort(' not in block and 'sorted(' not in block, 'View must not reorder diagnostics')
    require('Entry(' not in block and 'Text(' not in block, 'Inspector must remain read-only')


def test_keyboard_navigation_and_scrolling() -> None:
    text = source(VIEW)
    for token in ('<Up>', '<Down>', '<Home>', '<End>', 'takefocus=True', 'highlightthickness=2'):
        require(token in text, f'Missing accessibility behavior: {token}')
    require('yview_moveto' in text and 'yview_scroll' in text, 'Navigation must preserve or update scrolling')


def test_refresh_and_stale_removal() -> None:
    text = source(PRESENTER)
    require('self._clear_generated_results()' in text, 'Every planning attempt must clear stale results')
    require('self._view.set_diagnostics(' in text, 'Presenter must replace diagnostics')


def test_adapter_preserves_explanation() -> None:
    text = source(ADAPTER)
    require('explanation=diagnostic.canonical_explanation' in text, 'Adapter must preserve canonical explanation')


def test_syntax() -> None:
    for path in (QUERY, PRESENTER, VIEW, ADAPTER):
        ast.parse(source(path), filename=str(path))


def main() -> None:
    tests = [value for name, value in globals().items() if name.startswith('test_') and callable(value)]
    for test in tests:
        test()
        print(f'PASS: {test.__name__}')
    print(f'PASS: {len(tests)} focused UI-017 checks')


if __name__ == '__main__':
    main()
