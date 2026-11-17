import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_first_greeting_promotion_scope import evaluate

class FirstGreetingInterestScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'I-first','I-interest','I-formal','I-pressure','W-welcome','A13','A23','A26'})
        # Candidate behavior is observed first, then explicitly frozen.
        # No selected candidate or general accuracy is assumed here.

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        expected={'I-first':['manbanjalbu'],'I-interest':['mangwanbu'],
                  'W-welcome':['bangga-bangga'],'A13':['hug-me-animal']}
        for identity, entries in expected.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']], entries)
        for identity in ('I-formal','I-pressure','A23','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        for identity in ('I-first','I-interest','W-welcome'):
            self.assertEqual(rows[identity]['retrieval']['mode'],'recommend')
        self.assertEqual(rows['A13']['retrieval']['mode'],'lookup')

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/first-greeting-promotion-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
