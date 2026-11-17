import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_otl_finger_heart_scope import evaluate

class OtlFingerHeartScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'G-otl','G-heart','G-crisis','G-mock','G-body','G-done',
                          'G-consent','G-romance','G-force','A16','A26','E06'})
        self.assertTrue(trace['requirements_enabled'])
        # Observe broad OTL collisions before deciding review readiness.

    def test_observed_candidates_and_boundaries_after_function_gate(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        for identity, expected in {'G-otl':['otl'],'G-heart':['finger-heart'],
                                   'A16':['reality-is-gutter'],'E06':['haengshow']}.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']],expected)
        for identity in ('G-crisis','G-mock','G-body','G-done','G-consent','G-romance','G-force','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/otl-finger-heart-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_original_candidate_drift_is_preserved(self):
        from usage_profiles import blob_sha
        path=ROOT/'eval/otl-finger-heart-scope/v1-retrieval.json'
        self.assertEqual(blob_sha(path),'77328254604794baa6df7790da947d6ee8f09613')
        original=json.loads(path.read_text())
        self.assertEqual(original['current_baseline_candidate_drift'],
            [{'set':'regression-v3/audit','id':'A16',
              'before':['reality-is-gutter:expectation-gap'],
              'after':['otl:minor-own-disappointment','reality-is-gutter:expectation-gap']}])
