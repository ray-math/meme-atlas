import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_parody_turn_scope import evaluate

class ParodyTurnScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound_and_profiles_unchanged(self):
        before=(ROOT/'data/usage-profiles.json').read_bytes()
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'P-turn','P-missing','P-official','P-suspect','P-authority','P-voice',
                          'K-infer','A14','A23','A26'})
        self.assertTrue(trace['requirements_enabled'])
        self.assertEqual((ROOT/'data/usage-profiles.json').read_bytes(),before)
        # Candidate availability is not final permission to use a caution expression.

    def test_requirements_control_is_strict_boolean(self):
        for value in (None,0,1,'false',[],{}):
            with self.assertRaises(ValueError):
                evaluate(ROOT,enforce_requirements=value)

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        self.assertEqual([h['entry_id'] for h in rows['A14']['retrieval']['results']],
                         ['you-insulted-me','kingbatne'])
        for identity in ('P-turn','P-missing','P-official','P-suspect','P-authority','P-voice','K-infer','A23','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['P-turn']['action'],'clarify')
        self.assertEqual(rows['K-infer']['action'],'clarify')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        # No positive parody use was executed by these plans; do not call it validated.

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/parody-turn-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/parody-turn-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
