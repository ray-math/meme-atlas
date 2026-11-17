import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_abbreviation_food_rule_scope import evaluate

class AbbreviationFoodRuleScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'B-abbrev','F-rule','B-meaning','B-person','B-public',
                          'F-missing','F-force','F-fact','F-health','A08','A26','E22'})
        self.assertTrue(trace['requirements_enabled'])
        # Observe actual caution lookup, abstention and candidate behavior before promotion.

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        self.assertEqual([h['entry_id'] for h in rows['F-rule']['retrieval']['results']],['guk-rule'])
        self.assertEqual([h['entry_id'] for h in rows['A08']['retrieval']['results']],['carrot-of-course','injeong'])
        for identity in ('B-abbrev','B-meaning','B-person','B-public','F-missing','F-force','F-fact','F-health','A26','E22'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['B-abbrev']['action'],'clarify')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        # B-abbrev is a clarification, not a successful positive use recommendation.

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/abbreviation-food-rule-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/abbreviation-food-rule-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
