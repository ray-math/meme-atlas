import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_index import build
from search_dictionary import norm, search
from get_entry import get_entry

class ReviewBoundaryTests(unittest.TestCase):
    def test_held_candidate_is_not_a_dictionary_entry(self):
        rows=build(ROOT)
        candidates=json.loads((ROOT/'review/candidates.json').read_text())['candidates']
        for candidate in candidates:
            self.assertEqual(candidate['workflow'],'held')
            self.assertEqual(candidate['origin_review'],'unconfirmed')
            names=[norm(v) for row in rows for v in [row['title'],*row.get('aliases',[])]]
            self.assertNotIn(norm(candidate['title']),names)
            self.assertNotIn(candidate['candidate_id'],[r['id'] for r in rows])
    def test_search_then_get(self):
        rows=build(ROOT)
        for query,expected in [('럭키비키','wonyoung-thinking'),('모방','sonminsu'),('음료 이름','mojito-maldives')]:
            hits=search(rows,query,limit=3)
            self.assertIn(expected,[x['id'] for x in hits])
            value=get_entry(ROOT,expected,'definition')
            self.assertTrue(value['sections']['definition'])
            self.assertNotIn('origin',value['sections'])
