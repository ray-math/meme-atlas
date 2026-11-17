import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_check_in_lookup import evaluate
from compare_evaluation_expansion import strict_equal

class CheckInMeaningTests(unittest.TestCase):
    def test_lookup_direction_and_default_safety(self):
        result=evaluate(ROOT);rows={r['id']:r for r in result['results']}
        self.assertEqual(len(rows),7)
        key=('shake-a-carrot','playful-check-in')
        def keys(identity):return {(h['entry_id'],h['usage_id']) for h in rows[identity]['retrieval']['results']}
        self.assertEqual(keys('title-lookup'),{key})
        self.assertEqual(keys('other-check-in'),{key})
        for identity in ['title-recommend','self-check-in','self-comfort','exclude-downplaying','exclude-factual-risk']:
            self.assertNotIn(key,keys(identity))
        self.assertIn(('hug-me-animal','request-comfort'),keys('self-comfort'))
        self.assertGreaterEqual(rows['title-recommend']['retrieval']['safety_filtered_count'],1)
        self.assertGreaterEqual(rows['exclude-downplaying']['retrieval']['risk_filtered_count'],1)
        hit=rows['title-lookup']['retrieval']['results'][0]
        self.assertEqual(hit['usage']['safety'],'caution')
        self.assertTrue(hit['requires_context_check'])
        self.assertTrue(hit['usage']['avoid_when'])

    def test_existing_public_decisions_are_not_fabricated_answers(self):
        rows=evaluate(ROOT)['preserved_public_decisions']
        self.assertEqual([(r['source'],r['id'],r['action']) for r in rows],[
            ('carrot-scope','C-check-in','clarify'),('carrot-scope','A18','abstain'),
            ('carrot-scope','A23','clarify'),('direction-scope','A20','abstain')])
        for row in rows:self.assertEqual(row['retrieval']['status'],'not_searched')

    def test_frozen_lookup_and_explanation_selection(self):
        actual=evaluate(ROOT)
        frozen=json.loads((ROOT/'eval/check-in-lookup/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(actual['results']),behavior(frozen['results'])))
        self.assertTrue(strict_equal(actual['preserved_public_decisions'],frozen['preserved_public_decisions']))
        answer=json.loads((ROOT/'eval/check-in-lookup/answer.json').read_text())
        self.assertEqual(answer['action'],'lookup')
        self.assertEqual((answer['selected_entry_id'],answer['selected_usage_id']),('shake-a-carrot','playful-check-in'))
        self.assertTrue(answer['text'].strip())
