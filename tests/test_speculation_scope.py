import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_speculation_scope import evaluate
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary
from search_usage import search

class SpeculationScopeTests(unittest.TestCase):
    def test_distinct_functions_and_existing_candidates(self):
        trace=evaluate(ROOT)
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        for case,uid in [('B-disclose','disclose-personal-guess'),('B-critique','criticize-unsupported-claim')]:
            self.assertEqual([(h['entry_id'],h['usage_id']) for h in rows[case]['retrieval']['results']],[('noepisyeol',uid)])
        for case in ('K-inference','N-criteria','A12'):
            self.assertFalse(any(h['entry_id']=='noepisyeol' for h in rows[case]['retrieval']['results']))
        self.assertIn('king-reasonable-suspicion',[h['entry_id'] for h in rows['K-inference']['retrieval']['results']])
        self.assertIn('naeronambul',[h['entry_id'] for h in rows['N-criteria']['retrieval']['results']])
        for case in ('A19','A21','A23'):self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
    def test_requires_claim_focus_and_specific_function_or_condition(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        entry=next(e for e in index['entries'] if e['id']=='noepisyeol')
        entry['review_status']='reviewed'
        for usage in entry['usages']:
            def contains(filters,mode='lookup'):
                return any(h['entry_id']==entry['id'] and h['usage_id']==usage['id']
                           for h in search(index,vocab,mode=mode,**filters)['results'])
            required=usage['retrieval_requirements']
            self.assertTrue(contains(required))
            self.assertFalse(contains(required,'recommend'))
            for axis in required:
                missing=copy.deepcopy(required);missing.pop(axis)
                self.assertFalse(contains(missing))
                broad=copy.deepcopy(required)
                broad[axis].append({'intents':'추측표현','situations':'불완전한정보','targets':'상대'}[axis])
                self.assertFalse(contains(broad))
            wrong=copy.deepcopy(required);wrong['targets']=['자기']
            self.assertFalse(contains(wrong))
        result=search(index,vocab,entry['title'],mode='lookup')
        hits=[h for h in result['results'] if h['entry_id']==entry['id']]
        self.assertEqual(len(hits),2)
        self.assertTrue(all(h['retrieval_scope']['exact_lookup_only'] for h in hits))

    def test_frozen_trace_replays_with_type_preserving_comparison(self):
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/speculation-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
