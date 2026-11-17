import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_future_wish_appearance_scope import evaluate

class FutureWishAppearanceScopeTests(unittest.TestCase):
    def test_context_only_inputs_preserve_function_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        self.assertEqual({h['entry_id'] for h in rows['F-wish']['retrieval']['results']},{'flower-road','haengshow'})
        self.assertEqual([h['entry_id'] for h in rows['F-appearance']['retrieval']['results']],['gaptuk-twi'])
        for case in ('F-wish','F-appearance'):
            self.assertEqual(rows[case]['retrieval']['mode'],'recommend')
        for case in ('F-pressure','F-danger','A20','A23','A26'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertFalse(any(h['entry_id'] in {'flower-road','gaptuk-twi'} for h in rows['A01']['retrieval']['results']))
        self.assertEqual(rows['A23']['action'],'clarify')
        self.assertEqual(rows['A26']['action'],'clarify')
        # Historical candidate drift is measured in the trace, not silently
        # declared an error or allowed expansion before individual review.

    def test_observed_historical_candidate_drift_is_empty(self):
        self.assertEqual(evaluate(ROOT)['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/future-wish-appearance-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
