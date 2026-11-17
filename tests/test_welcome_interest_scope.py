import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_welcome_interest_scope import evaluate

class WelcomeInterestScopeTests(unittest.TestCase):
    def test_public_directions_and_boundaries(self):
        result=evaluate(ROOT)
        self.assertEqual(result['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in result['results']}
        for case,entry in [('W-welcome','bangga-bangga'),('W-topic','anmul-angung')]:
            self.assertEqual([h['entry_id'] for h in rows[case]['retrieval']['results']],[entry])
        for case in ('W-formal','W-pain','A18','A23'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['A23']['action'],'clarify')
        self.assertTrue(any(h['entry_id']=='tmi' and h['usage_id']=='self-overdetail' for h in rows['A03']['retrieval']['results']))
        self.assertTrue(any(h['entry_id']=='haengshow' for h in rows['E06']['retrieval']['results']))
        for case in ('A03','E06'):
            self.assertFalse(any(h['entry_id'] in {'bangga-bangga','anmul-angung'} for h in rows[case]['retrieval']['results']))

    def test_frozen_trace_reexecutes_without_type_drift(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/welcome-interest-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/welcome-interest-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
