import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_evaluation_expansion import strict_equal
from replay_context_scope import evaluate

class PublicScopeRehearsalTests(unittest.TestCase):
    def test_actual_python_positive_and_counterexample_rehearsal(self):
        rows={r['id']:r for r in evaluate(ROOT)['results']}
        self.assertEqual(len(rows),10)
        def keys(identity):
            return {(h['entry_id'],h['usage_id']) for h in rows[identity]['retrieval']['results']}
        self.assertEqual(keys('P-pon'),{('pon-eunjeong','expose-fabrication')})
        self.assertEqual(keys('P-upside'),{('ohiryeo-joa','find-upside')})
        for identity,excluded in [('A01','goat'),('A12','pon-eunjeong'),('A16','ohiryeo-joa')]:
            self.assertFalse(any(entry==excluded for entry,usage in keys(identity)))
        for identity in ['P-goat','P-goat-context','A17','A19','A20']:
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')

    def test_missing_case_or_changed_public_prompt_rejected(self):
        original=Path.read_text
        for change in ['missing','changed']:
            def edited(path,*args,**kwargs):
                value=original(path,*args,**kwargs)
                if str(path).endswith('eval/context-scope/plans.json'):
                    data=json.loads(value)
                    if change=='missing':
                        data['plans'].pop()
                    else:
                        data['plans'][0]['prompt']='not the published text'
                    return json.dumps(data)
                return value
            with patch.object(Path,'read_text',edited):
                with self.assertRaises(ValueError):
                    evaluate(ROOT)

    def test_frozen_scope_trace_keeps_actual_candidates(self):
        actual=evaluate(ROOT)
        frozen=json.loads((ROOT/'eval/context-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:
                row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(actual['results']),behavior(frozen['results'])))

    def test_final_ai_selection_is_within_actual_retrieval(self):
        trace={r['id']:r for r in json.loads((ROOT/'eval/context-scope/retrieval.json').read_text())['results']}
        answers=json.loads((ROOT/'eval/context-scope/answers.json').read_text())['answers']
        self.assertEqual(len(answers),len(trace))
        self.assertEqual({a['id'] for a in answers},set(trace))
        for answer in answers:
            self.assertEqual(answer['action'],trace[answer['id']]['action'])
            selected=(answer['selected_entry_id'],answer['selected_usage_id'])
            if answer['action']=='recommend':
                self.assertIn(selected,{(h['entry_id'],h['usage_id']) for h in trace[answer['id']]['retrieval']['results']})
            else:
                self.assertEqual(selected,(None,None))
            self.assertTrue(answer['text'].strip())
