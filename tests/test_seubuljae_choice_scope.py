import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_seubuljae_choice_scope import evaluate

class SeubuljaeChoiceScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound_and_profiles_unchanged(self):
        before=(ROOT/'data/usage-profiles.json').read_bytes()
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'S-choice','S-missing','S-forced','S-victim','S-serious','S-luck',
                          'O-disappointment','B-memory','R-gap','U-upside','A26'})
        self.assertTrue(trace['requirements_enabled'])
        self.assertEqual((ROOT/'data/usage-profiles.json').read_bytes(),before)
        # Candidate behavior is observed from actual Python output before freezing it.

    def test_requirements_control_is_strict_boolean(self):
        for value in (None,0,1,'false',[],{}):
            with self.assertRaises(ValueError):
                evaluate(ROOT,enforce_requirements=value)

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        expected={'S-choice':'seubuljae','O-disappointment':'otl',
                  'B-memory':'blanket-kick','R-gap':'reality-is-gutter','U-upside':'ohiryeo-joa'}
        for identity,entry in expected.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']],[entry])
        for identity in ('S-missing','S-forced','S-victim','S-serious','S-luck','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/seubuljae-choice-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
