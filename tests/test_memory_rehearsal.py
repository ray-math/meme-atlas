import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_memory_scope import evaluate

class PublicMemoryRehearsalTests(unittest.TestCase):
    def test_actual_python_supported_directions_and_counterexamples(self):
        rows={r['id']:r for r in evaluate(ROOT)['results']}
        self.assertEqual(len(rows),10)
        def keys(identity):
            return {(h['entry_id'],h['usage_id']) for h in rows[identity]['retrieval']['results']}
        expected={'P-blanket-kick':('blanket-kick','remember-embarrassment'),
                  'P-goodbye-everyone':('goodbye-everyone','relieved-departure'),
                  'P-laugh-bell-scene':('laugh-bell','fond-scene'),
                  'P-laugh-bell-person':('laugh-bell','praise-humor')}
        for identity,key in expected.items():self.assertEqual(keys(identity),{key})
        self.assertIn(('goguma-frustration','frustrating-plot'),keys('A10'))
        for identity in ['A17','A18','A22','A23','A27']:
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')

    def test_missing_case_or_changed_prompt_rejected(self):
        original=Path.read_text
        for change in ['missing','changed']:
            def edited(path,*args,**kwargs):
                value=original(path,*args,**kwargs)
                if str(path).endswith('eval/memory-scope/plans.json'):
                    data=json.loads(value)
                    if change=='missing':data['plans'].pop()
                    else:data['plans'][0]['prompt']='not the published text'
                    return json.dumps(data)
                return value
            with patch.object(Path,'read_text',edited):
                with self.assertRaises(ValueError):evaluate(ROOT)

    def test_frozen_trace_and_selection_are_preserved(self):
        actual=evaluate(ROOT)
        frozen=json.loads((ROOT/'eval/memory-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertEqual(behavior(actual['results']),behavior(frozen['results']))
        trace={r['id']:r for r in frozen['results']}
        answers=json.loads((ROOT/'eval/memory-scope/answers.json').read_text())['answers']
        self.assertEqual(len(answers),len(trace))
        self.assertEqual({a['id'] for a in answers},set(trace))
        for answer in answers:
            self.assertEqual(answer['action'],trace[answer['id']]['action'])
            selected=(answer['selected_entry_id'],answer['selected_usage_id'])
            if answer['action']=='recommend':
                self.assertIn(selected,{(h['entry_id'],h['usage_id']) for h in trace[answer['id']]['retrieval']['results']})
            else:self.assertEqual(selected,(None,None))
            self.assertTrue(answer['text'].strip())

    def test_provisional_safety_scope_and_historical_candidates(self):
        from build_usage_index import build_usage_index
        from usage_profiles import load_vocabulary
        from search_usage import search
        original=build_usage_index(ROOT); staged=copy.deepcopy(original)
        vocabulary=load_vocabulary(ROOT)
        identities={'blanket-kick','goodbye-everyone','laugh-bell'}
        for entry in staged['entries']:
            if entry['id'] in identities:entry['review_status']='reviewed'
        def keys(result):
            return {(h['entry_id'],h['usage_id']) for h in result['results']}
        for entry in staged['entries']:
            if entry['id'] not in identities:continue
            for usage in entry['usages']:
                key=(entry['id'],usage['id'])
                filters=dict(usage['retrieval_requirements'],targets=usage['targets'])
                self.assertIn(key,keys(search(staged,vocabulary,mode='lookup',**filters)))
                self.assertEqual(key in keys(search(staged,vocabulary,mode='recommend',**filters)),
                                 usage['safety']=='standard')
                broad={'intents':usage['intents']}
                self.assertNotIn(key,keys(search(staged,vocabulary,mode='lookup',**broad)))
                opposite=dict(filters,targets=[t for t in ['자기','상대','제삼자','상황'] if t not in usage['targets']])
                self.assertNotIn(key,keys(search(staged,vocabulary,mode='lookup',**opposite)))
        for source in ['challenge','regression-v3']:
            for group in ['audit','editorial']:
                plans=json.loads((ROOT/f'eval/{source}/{group}-plans.json').read_text())['plans']
                for plan in plans:
                    if plan['action'] in ('clarify','abstain'):continue
                    before=search(original,vocabulary,**plan['filters'])
                    after=search(staged,vocabulary,**plan['filters'])
                    before.pop('coverage',None);after.pop('coverage',None)
                    self.assertEqual(before,after,(source,group,plan['id']))
        self.assertEqual(original,build_usage_index(ROOT))
