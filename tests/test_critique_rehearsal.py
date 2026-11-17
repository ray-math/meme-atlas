import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_critique_scope import evaluate
from compare_evaluation_expansion import strict_equal

class PublicCritiqueRehearsalTests(unittest.TestCase):
    def test_actual_python_distinguishes_inference_critique_and_confirmation(self):
        result=evaluate(ROOT)
        rows={r['id']:r for r in result['results']}
        self.assertEqual(len(rows),6)
        expected={'K-inference':('king-reasonable-suspicion','playful-inference'),
                  'N-criteria':('naeronambul','criticize-double-standard'),
                  'A12':('iwaejin','confirmed-surprise')}
        for identity,key in expected.items():
            self.assertEqual({(h['entry_id'],h['usage_id']) for h in rows[identity]['retrieval']['results']},{key})
        for identity in ['A19','A21','A23']:
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(result['current_baseline_candidate_drift'],[])

    def test_missing_case_or_changed_prompt_rejected(self):
        original=Path.read_text
        for change in ['missing','changed']:
            def edited(path,*args,**kwargs):
                value=original(path,*args,**kwargs)
                if str(path).endswith('eval/critique-scope/plans.json'):
                    data=json.loads(value)
                    if change=='missing':data['plans'].pop()
                    else:data['plans'][0]['prompt']='not the published text'
                    return json.dumps(data)
                return value
            with patch.object(Path,'read_text',edited):
                with self.assertRaises(ValueError):evaluate(ROOT)

    def test_frozen_trace_and_selection_are_preserved(self):
        actual=evaluate(ROOT)
        frozen=json.loads((ROOT/'eval/critique-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(actual['results']),behavior(frozen['results'])))
        trace={r['id']:r for r in frozen['results']}
        answers=json.loads((ROOT/'eval/critique-scope/answers.json').read_text())['answers']
        self.assertEqual(len(answers),len(trace))
        self.assertEqual({a['id'] for a in answers},set(trace))
        for answer in answers:
            self.assertEqual(answer['action'],trace[answer['id']]['action'])
            selected=(answer['selected_entry_id'],answer['selected_usage_id'])
            if answer['action']=='recommend':
                self.assertIn(selected,{(h['entry_id'],h['usage_id']) for h in trace[answer['id']]['retrieval']['results']})
            else:self.assertEqual(selected,(None,None))
            self.assertTrue(answer['text'].strip())

    def test_provisional_caution_and_target_boundaries(self):
        from build_usage_index import build_usage_index
        from usage_profiles import load_vocabulary
        from search_usage import search
        original=build_usage_index(ROOT);staged=copy.deepcopy(original)
        vocabulary=load_vocabulary(ROOT)
        identities={'king-reasonable-suspicion','naeronambul'}
        for entry in staged['entries']:
            if entry['id'] in identities:entry['review_status']='reviewed'
        def keys(result):return {(h['entry_id'],h['usage_id']) for h in result['results']}
        for entry in staged['entries']:
            if entry['id'] not in identities:continue
            for usage in entry['usages']:
                key=(entry['id'],usage['id'])
                filters={'intents':usage['intents'],'targets':usage['targets']}
                self.assertIn(key,keys(search(staged,vocabulary,mode='lookup',**filters)))
                self.assertNotIn(key,keys(search(staged,vocabulary,mode='recommend',**filters)))
                opposite=dict(filters,targets=['자기','상대','제삼자'])
                self.assertNotIn(key,keys(search(staged,vocabulary,mode='lookup',**opposite)))
                self.assertNotIn(key,keys(search(staged,vocabulary,mode='lookup',intents=['판단유보'])))
        self.assertTrue(strict_equal(original,build_usage_index(ROOT)))
