import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from check_editorial import check

class EditorialTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'review').mkdir()
        (self.root/'memes').mkdir()
        (self.root/'memes/a.md').write_text('# 가\n')

    def decisions(self, rows):
        (self.root/'review/tag-decisions.json').write_text(json.dumps({'decisions': rows}))

    def test_current(self):
        self.assertEqual(check(ROOT), [])

    def test_default_empty_not_false_classification(self):
        self.decisions({})
        self.assertEqual(check(self.root), [])

    def test_independent_needs_reason(self):
        self.decisions({'a': {'status': 'domain_independent'}})
        self.assertTrue(check(self.root))
        self.decisions({'a': {'status': 'domain_independent', 'reason': '검토 결과 분야를 특정하지 않음'}})
        self.assertEqual(check(self.root), [])

    def test_unknown_entry(self):
        self.decisions({'missing': {'status': 'pending'}})
        self.assertTrue(check(self.root))

    def test_invalid_candidate_state(self):
        (self.root/'review/candidates.json').write_text(json.dumps({'candidates': [
            {'candidate_id': 'a', 'workflow': 'magically_verified'}]}))
        self.assertTrue(check(self.root))
