import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_preference_scope import evaluate
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary
from search_usage import search
class PreferenceScopeTests(unittest.TestCase):
    IDS={'chwijon','dapjeongneo'}
    def test_distinguishes_respect_agreement_and_criticism_grounds(self):
        trace=evaluate(ROOT);self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        for case,entry in [('P-taste','chwijon'),('P-dialogue','dapjeongneo')]:
            self.assertEqual([h['entry_id'] for h in rows[case]['retrieval']['results']],[entry])
        for case in ('A08','N-criteria','B-critique'):
            self.assertFalse(any(h['entry_id'] in self.IDS for h in rows[case]['retrieval']['results']))
        for case in ('P-coercion','P-single','A23'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['P-coercion']['action'],'abstain')
        self.assertEqual(rows['P-single']['action'],'clarify')
    def test_specific_function_or_observed_condition_and_focus_required(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        for e in index['entries']:
            if e['id'] in self.IDS:e['review_status']='reviewed'
        for e in index['entries']:
            if e['id'] not in self.IDS:continue
            required=e['usages'][0]['retrieval_requirements']
            def contains(filters,mode='lookup'):
                return any(h['entry_id']==e['id'] for h in search(index,vocab,mode=mode,**filters)['results'])
            self.assertTrue(contains(required));self.assertFalse(contains(required,'recommend'))
            for axis in required:
                absent=copy.deepcopy(required);absent.pop(axis);self.assertFalse(contains(absent))
                broad=copy.deepcopy(required);broad[axis].append({'intents':'동조','situations':'반복질문','targets':'상대'}[axis]);self.assertFalse(contains(broad))
            hit=next(h for h in search(index,vocab,e['title'],mode='lookup')['results'] if h['entry_id']==e['id'])
            self.assertTrue(hit['retrieval_scope']['exact_lookup_only'])

    def test_frozen_python_trace_reexecutes(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/preference-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
