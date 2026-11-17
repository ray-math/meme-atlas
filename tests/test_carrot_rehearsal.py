import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_carrot_scope import evaluate

class PublicCarrotRehearsalTests(unittest.TestCase):
    def test_actual_python_candidates_and_missing_relationship(self):
        result=evaluate(ROOT)
        rows={r['id']:r for r in result['results']}
        self.assertEqual(len(rows),6)
        expected=[('real-lol','agree-laugh'),('carrot-of-course','playful-agreement'),('injeong','agreement')]
        for identity in ['C-agree','A08']:
            self.assertEqual([(h['entry_id'],h['usage_id']) for h in rows[identity]['retrieval']['results']],expected)
        for identity in ['C-check-in','A18','A23','A27']:
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        expected_drift={(source,identity) for source,identity in [
            ('challenge/audit','A08'),('challenge/editorial','E08'),
            ('regression-v3/audit','A08'),('regression-v3/editorial','E08')]}
        self.assertEqual({(r['set'],r['id']) for r in result['historical_candidate_drift']},expected_drift)
        for row in result['historical_candidate_drift']:
            self.assertEqual(row['after'],['real-lol:agree-laugh','carrot-of-course:playful-agreement','injeong:agreement'])
            self.assertEqual(row['before'],['real-lol:agree-laugh','injeong:agreement'])

    def test_missing_case_or_changed_prompt_rejected(self):
        original=Path.read_text
        for change in ['missing','changed']:
            def edited(path,*args,**kwargs):
                value=original(path,*args,**kwargs)
                if str(path).endswith('eval/carrot-scope/plans.json'):
                    data=json.loads(value)
                    if change=='missing':data['plans'].pop()
                    else:data['plans'][0]['prompt']='not the published text'
                    return json.dumps(data)
                return value
            with patch.object(Path,'read_text',edited):
                with self.assertRaises(ValueError):evaluate(ROOT)

    def test_frozen_trace_and_selection_are_preserved(self):
        actual=evaluate(ROOT)
        frozen=json.loads((ROOT/'eval/carrot-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertEqual(behavior(actual['results']),behavior(frozen['results']))
        trace={r['id']:r for r in frozen['results']}
        answers=json.loads((ROOT/'eval/carrot-scope/answers.json').read_text())['answers']
        self.assertEqual(len(answers),len(trace))
        self.assertEqual({a['id'] for a in answers},set(trace))
        for answer in answers:
            self.assertEqual(answer['action'],trace[answer['id']]['action'])
            selected=(answer['selected_entry_id'],answer['selected_usage_id'])
            if answer['action']=='recommend':
                self.assertIn(selected,{(h['entry_id'],h['usage_id']) for h in trace[answer['id']]['retrieval']['results']})
            else:self.assertEqual(selected,(None,None))
            self.assertTrue(answer['text'].strip())

