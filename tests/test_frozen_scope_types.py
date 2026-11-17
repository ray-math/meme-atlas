"""Exercise the actual three frozen-test guards, not a parallel comparison."""
import copy
import importlib
import json
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
CASES = (
    ('context-scope', 'test_context_scope_rehearsal', 'PublicScopeRehearsalTests',
     'test_frozen_scope_trace_keeps_actual_candidates'),
    ('direction-scope', 'test_direction_rehearsal', 'PublicDirectionRehearsalTests',
     'test_frozen_trace_and_selection_are_preserved'),
    ('memory-scope', 'test_memory_rehearsal', 'PublicMemoryRehearsalTests',
     'test_frozen_trace_and_selection_are_preserved'),
)


class FrozenScopeTypeBoundaryTests(unittest.TestCase):
    def invoke_guard(self, case, actual):
        folder, module_name, class_name, method = case
        module = importlib.import_module(module_name)
        guard = getattr(module, class_name)(methodName=method)
        # Patch only replay output; the guard still reads the unchanged frozen file.
        with patch.object(module, 'evaluate', return_value=actual):
            getattr(guard, method)()

    def frozen(self, case):
        return json.loads((ROOT/'eval'/case[0]/'retrieval.json').read_text(encoding='utf-8'))

    def test_actual_guards_reject_bool_int_float_type_drift(self):
        for case in CASES:
            frozen = self.frozen(case)
            for mutation in ('boolean-to-int', 'boolean-to-float', 'integer-to-float'):
                actual = copy.deepcopy(frozen)
                hit = next(hit for row in actual['results']
                           for hit in row['retrieval']['results'])
                if mutation == 'integer-to-float':
                    self.assertIs(type(hit['score']), int)
                    hit['score'] = float(hit['score'])
                else:
                    self.assertIs(type(hit['requires_context_check']), bool)
                    value = int(hit['requires_context_check'])
                    hit['requires_context_check'] = value if mutation == 'boolean-to-int' else float(value)
                # Demonstrate the exact old equality hole on these real public rows.
                self.assertEqual(actual['results'], frozen['results'])
                with self.subTest(scope=case[0], mutation=mutation), self.assertRaises(AssertionError):
                    self.invoke_guard(case, actual)

    def test_unchanged_rows_and_only_coverage_changes_remain_allowed(self):
        for case in CASES:
            frozen = self.frozen(case)
            for coverage_only in (False, True):
                actual = copy.deepcopy(frozen)
                if coverage_only:
                    for row in actual['results']:
                        row['retrieval']['coverage'] = {'test_only_changed_count': 999}
                with self.subTest(scope=case[0], coverage_only=coverage_only):
                    self.invoke_guard(case, actual)
