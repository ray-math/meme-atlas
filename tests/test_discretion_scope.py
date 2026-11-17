import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_discretion_scope import evaluate
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary
from search_usage import search

class DiscretionScopeTests(unittest.TestCase):
    def test_shared_conditions_do_not_replace_missing_information(self):
        trace=evaluate(ROOT)
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        self.assertEqual([h['entry_id'] for h in rows['D-shared']['retrieval']['results']],['aljaltakkalsen'])
        self.assertEqual(rows['D-missing']['action'],'clarify')
        for case in ('D-missing','A20','A22','A23'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertFalse(any(h['entry_id']=='aljaltakkalsen' for h in rows['A08']['retrieval']['results']))
    def test_shared_criteria_and_actor_direction_are_both_required(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        entry=next(e for e in index['entries'] if e['id']=='aljaltakkalsen')
        entry['review_status']='reviewed'
        required=entry['usages'][0]['retrieval_requirements']
        def contains(filters,mode='lookup'):
            return any(h['entry_id']==entry['id'] for h in search(index,vocab,mode=mode,**filters)['results'])
        self.assertTrue(contains(required));self.assertFalse(contains(required,'recommend'))
        for axis in required:
            missing=copy.deepcopy(required);missing.pop(axis)
            self.assertFalse(contains(missing))
            broad=copy.deepcopy(required);broad[axis].append('자기' if axis=='targets' else '일완료')
            self.assertFalse(contains(broad))
        self.assertFalse(contains({'intents':['재량요청']}))
        hit=next(h for h in search(index,vocab,entry['title'],mode='lookup')['results'] if h['entry_id']==entry['id'])
        self.assertTrue(hit['retrieval_scope']['exact_lookup_only'])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/discretion-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/discretion-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])
