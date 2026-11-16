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

    def ledger(self, rows):
        (self.root/'data').mkdir(exist_ok=True)
        p=self.root/'data/korea-candidates.json'
        p.write_text(json.dumps({'candidates':rows}))
        return p

    def candidate(self, **changes):
        row={'id':'one','status':'unreviewed','parent_id':None,'dictionary_paths':[]}
        row.update(changes)
        return row

    def test_candidate_ledger_valid_states_and_forward_references(self):
        rows=[self.candidate(id='child',parent_id='one'),
              self.candidate(id='copy',status='duplicate',duplicate_of='one'),
              self.candidate(status='included',dictionary_paths=['memes/a.md']),
              self.candidate(id='hold',status='held')]
        self.ledger(rows)
        self.assertEqual(check(self.root), [])

    def test_candidate_ledger_unique_nonempty_ids(self):
        for rows in [[self.candidate(),self.candidate()],
                     [self.candidate(id='')],[self.candidate(id=[])]]:
            with self.subTest(rows=rows):
                self.ledger(rows)
                self.assertTrue(check(self.root))

    def test_candidate_ledger_only_declared_states(self):
        for state in ['verified','reviewing','ready','rejected',None,[]]:
            with self.subTest(state=state):
                self.ledger([self.candidate(status=state)])
                self.assertTrue(check(self.root))

    def test_candidate_ledger_reference_targets(self):
        for field in ['parent_id','duplicate_of']:
            for target in ['missing','one',[], '']:
                with self.subTest(field=field,target=target):
                    self.ledger([self.candidate(**{field:target})])
                    self.assertTrue(check(self.root))
        self.ledger([self.candidate(status='duplicate')])
        self.assertTrue(check(self.root))

    def test_candidate_ledger_included_paths_required(self):
        for paths in [None,[], 'memes/a.md',['memes/missing.md'],
                      ['../memes/a.md'],['memes/../memes/a.md'],
                      ['/memes/a.md'],['memes'],['memes/README.md'],[123]]:
            with self.subTest(paths=paths):
                self.ledger([self.candidate(status='included',dictionary_paths=paths)])
                self.assertTrue(check(self.root))

    def test_candidate_ledger_requires_file_not_directory(self):
        (self.root/'memes/directory.md').mkdir()
        self.ledger([self.candidate(status='included',dictionary_paths=['memes/directory.md'])])
        self.assertTrue(check(self.root))

    def test_candidate_ledger_no_truth_check_or_state_changes(self):
        rows=[self.candidate(evidence=[],notes=['未検証'],dictionary_paths=['not-reviewed']),
              self.candidate(id='two',status='included',dictionary_paths=['memes/a.md'],evidence=[])]
        path=self.ledger(rows);before=path.read_bytes()
        self.assertEqual(check(self.root), [])
        self.assertEqual(path.read_bytes(),before)

    def test_candidate_ledger_malformed_container(self):
        path=self.ledger([])
        for data in [[],{}, {'candidates':{}}, {'candidates':[None]}]:
            path.write_text(json.dumps(data))
            self.assertTrue(check(self.root))
        path.write_text('{')
        self.assertTrue(check(self.root))
