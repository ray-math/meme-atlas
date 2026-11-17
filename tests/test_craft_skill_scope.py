import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_craft_skill_scope import evaluate

class CraftSkillScopeTests(unittest.TestCase):
    def test_craft_is_not_generic_praise_or_self_deprecation(self):
        trace=evaluate(ROOT)
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        for case,entry in [('C-praise','geumson'),('C-self','ttongson')]:
            self.assertEqual([h['entry_id'] for h in rows[case]['retrieval']['results']],[entry])
        self.assertEqual(rows['C-praise']['retrieval']['mode'],'recommend')
        self.assertEqual(rows['C-self']['retrieval']['mode'],'lookup')
        for case in ('C-inference','C-harm','A22','A23'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['A23']['action'],'clarify')
        for case in ('A01','A16'):
            self.assertFalse(any(h['entry_id'] in {'geumson','ttongson'} for h in rows[case]['retrieval']['results']))
        self.assertTrue(any(h['entry_id']=='reality-is-gutter' for h in rows['A16']['retrieval']['results']))

    def test_frozen_trace_reexecutes_without_type_drift(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/craft-skill-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/craft-skill-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
