import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_exercise_scope import evaluate
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary
from search_usage import search

class ExerciseScopeTests(unittest.TestCase):
    IDS={'hellchang','jumo-cheer'}
    def test_public_plans_preserve_existing_candidates_and_bounded_positives(self):
        trace=evaluate(ROOT)
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        for case,entry in [('X-exercise','hellchang'),('J-international','jumo-cheer')]:
            self.assertEqual([h['entry_id'] for h in rows[case]['retrieval']['results']],[entry])
        for case in ('A01','A02','A16'):
            self.assertFalse(any(h['entry_id'] in self.IDS for h in rows[case]['retrieval']['results']))
        for case in ('A18','A21','A23'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
    def test_required_direction_and_situation_cannot_be_replaced_by_broad_or(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        entries=[e for e in index['entries'] if e['id'] in self.IDS]
        for e in entries:e['review_status']='reviewed'
        for e in entries:
            required=e['usages'][0]['retrieval_requirements']
            def contains(filters,mode='lookup'):
                return any(h['entry_id']==e['id'] for h in search(index,vocab,mode=mode,**filters)['results'])
            self.assertTrue(contains(required))
            self.assertFalse(contains(required,'recommend'))
            for axis in ('situations','targets'):
                absent=copy.deepcopy(required);absent.pop(axis)
                self.assertFalse(contains(absent))
                broad=copy.deepcopy(required)
                broad[axis].append('성과' if axis=='situations' else '제삼자')
                self.assertFalse(contains(broad))
            wrong=copy.deepcopy(required);wrong['targets']=['상대']
            self.assertFalse(contains(wrong))
            lookup=search(index,vocab,e['title'],mode='lookup')
            hit=next(h for h in lookup['results'] if h['entry_id']==e['id'])
            self.assertTrue(hit['retrieval_scope']['exact_lookup_only'])
