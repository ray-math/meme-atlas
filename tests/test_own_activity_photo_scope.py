import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_own_activity_photo_scope import evaluate

class OwnActivityPhotoScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'P-record','P-other','P-details','P-private','P-consent','A07','A26','E18'})
        # Candidate behavior is observed before semantic review.

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        for identity, expected in {'P-record':['proof-photo'],'A07':['look-at-this-hand'],
                                   'E18':['space-behind-pillar']}.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']],expected)
        for identity in ('P-other','P-details','P-private','P-consent','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        for identity in ('P-record','A07'):
            self.assertEqual(rows[identity]['retrieval']['mode'],'recommend')
        self.assertEqual(rows['E18']['retrieval']['mode'],'lookup')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/own-activity-photo-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/own-activity-photo-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
