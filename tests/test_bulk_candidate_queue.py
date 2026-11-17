"""Synthetic structural tests, not factual candidate review."""
import copy
import json
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from bulk_candidate_queue import queue, validate, adapt, main, dump

def row(i, title=None, **kw):
    return dict(id=str(i), title=title or 'candidate-' + str(i), status='unreviewed',
                dictionary_paths=[], evidence=[], notes=[], **kw)

class BulkCandidateQueueTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'repo'
        (self.root / 'data').mkdir(parents=True)
        self.path = self.root / 'data/korea-candidates.json'
        self.canonical = [{'id': 'existing', 'title': 'Existing', 'aliases': ['별칭'],
                           'path': 'memes/existing.md'}]
    def write(self, rows, path=None):
        path = path or self.path
        path.write_text(json.dumps({'schema_version': 1, 'source': {'url': 'https://example.org/list'},
                                    'candidates': rows}, ensure_ascii=False))
        return path
    def run_queue(self, inputs=None):
        with patch('bulk_candidate_queue.build', return_value=self.canonical):
            return queue(self.root, inputs)
    def test_600_rows_determinism_and_original_unchanged(self):
        self.write([row(i) for i in range(600)])
        before = self.path.read_bytes()
        start = time.monotonic()
        a = self.run_queue()
        self.assertLess(time.monotonic() - start, 10)
        self.assertEqual(a, self.run_queue())
        self.assertEqual(a['counts']['total'], 600)
        self.assertEqual(a['counts']['needs_research'], 600)
        self.assertEqual(a['by_source_kind']['new_source_rows']['total'], 0)
        self.assertEqual(self.path.read_bytes(), before)
    def test_alias_unicode_candidate_duplicate_and_held(self):
        rows = [row('a', 'ＥＸＩＳＴＩＮＧ!'), row('b', '다른말', aliases=['별칭']),
                row('c', '새 표현'), row('d', '새표현!'), row('e', '●▅')]
        rows.append(row('f')); rows[-1]['status'] = 'held'
        self.write(rows)
        a = self.run_queue()
        self.assertEqual([r['classification'] for r in a['rows']],
                         ['duplicate_existing', 'duplicate_existing', 'needs_research',
                          'duplicate_candidate', 'held', 'held'])
        self.assertEqual(sum(a['counts'][k] for k in
                         ('duplicate_existing','duplicate_candidate','held','needs_research')), 6)
    def test_retired_alias_and_included_path_consistency(self):
        (self.root/'data/pilot-state.json').write_text(json.dumps({
            'version':1, 'entries':{'old':{'title':'Old name','aliases':['Old alias'],
                                         'superseded_by':'existing'}}}))
        rows = [row('a','Old alias'), row('b','unrelated')]
        rows[1].update(status='included', dictionary_paths=['memes/existing.md'])
        self.write(rows)
        a = self.run_queue()
        self.assertEqual(a['rows'][0]['classification'], 'duplicate_existing')
        self.assertEqual(a['rows'][1]['classification'], 'held')
        self.assertIn('stale_included_status', [d['kind'] for d in a['diagnostics']])
        rows[1]['title'] = 'Existing'
        self.write(rows)
        self.assertTrue(self.run_queue()['rows'][1]['included_link_verified'])
    def test_same_count_replacement_changes_fingerprint(self):
        self.write([row('a')])
        a = self.run_queue()
        self.write([row('b')])
        b = self.run_queue()
        self.assertEqual(a['counts'], b['counts'])
        self.assertNotEqual(a['sources'][0]['sha256'], b['sources'][0]['sha256'])
        self.canonical[0]['title'] = 'Changed'
        self.assertNotEqual(b['canonical_fingerprint'], self.run_queue()['canonical_fingerprint'])
    def test_export_provenance_and_global_duplicate_id(self):
        self.write([row('a')])
        extra = Path(self.tmp.name)/'export.json'
        self.write([row('b')], extra)
        a = self.run_queue([self.path, extra])
        self.assertEqual(a['by_source_kind']['legacy_existing']['total'], 1)
        self.assertEqual(a['by_source_kind']['new_source_rows']['total'], 1)
        self.assertEqual(a['rows'][1]['candidate']['id'], 'b')
        self.assertEqual(a['sources'][1]['metadata']['source']['url'], 'https://example.org/list')
        self.write([row('a')], extra)
        with self.assertRaises(ValueError): self.run_queue([self.path, extra])
    def test_strict_types_and_reference_shapes(self):
        good = {'schema_version':1, 'candidates':[row('a')]}
        for field, value in [('aliases','abc'),('aliases',[1]),('title',' '),
                             ('status',[]),('status','ready'),('parent_id',True),
                             ('parent_id','a'),('dictionary_paths', ['../x.md'])]:
            bad = copy.deepcopy(good); bad['candidates'][0][field] = value
            with self.subTest(field=field,value=value):
                with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(good); bad['schema_version'] = True
        with self.assertRaises(ValueError): validate(bad)
        bad = copy.deepcopy(good); bad['candidates'] *= 2
        with self.assertRaises(ValueError): validate(bad)
    def test_check_output_exclusive_and_outside_repo(self):
        self.write([row('a')])
        output = Path(self.tmp.name)/'queue.json'
        with patch('bulk_candidate_queue.build', return_value=self.canonical):
            main(['--root',str(self.root),'--check','--output',str(output)])
            with self.assertRaises(FileExistsError):
                main(['--root',str(self.root),'--output',str(output)])
            with self.assertRaises(ValueError):
                main(['--root',str(self.root),'--output',str(self.root/'queue.json')])
        self.assertEqual(json.loads(output.read_text())['counts']['total'], 1)

    def test_research_adapter_rich_urls_and_explicit_ids(self):
        env = {'schema_version':1, 'candidates':[{
            'research_id':'r1', 'title':'새 제목', 'aliases':[],
            'review_status':'unreviewed', 'source_urls':[{'url':'https://example.org/a',
            'access':'search_index','independent_group':'publisher'}],
            'evidence_tier':'independent_reporting'}]}
        before = copy.deepcopy(env)
        normalized, originals = adapt(env, '/tmp/research.json')
        self.assertEqual(normalized['candidates'][0]['id'], 'r1')
        self.assertEqual(originals['r1'], env['candidates'][0])
        self.assertEqual(env, before)
        for update in ({'id':'different'}, {'status':'held'}, {'review_status':'reviewed'},
                       {'aliases':'bad'}, {'source_urls':[{'url':False}]}):
            bad = copy.deepcopy(env); bad['candidates'][0].update(update)
            with self.assertRaises(ValueError): adapt(bad, '/tmp/research.json')
    def test_legacy_reexport_not_new_source_rows(self):
        self.write([row('legacy1','원제목')])
        export = Path(self.tmp.name)/'reexport.json'
        export.write_text(json.dumps({'schema_version':1,'candidates':[
            {'ledger_id':'legacy1','title':'원제목','status':'unreviewed'}]}))
        result = self.run_queue([self.path, export])
        self.assertEqual(result['by_source_kind']['legacy_existing']['total'], 1)
        self.assertEqual(result['by_source_kind']['legacy_reexport']['total'], 1)
        self.assertEqual(result['by_source_kind']['new_source_rows']['total'], 0)
        self.assertEqual(result['rows'][1]['original_source_id'], 'legacy1')
        self.assertEqual(result['rows'][1]['classification'], 'duplicate_candidate')
        self.assertEqual(result['rows'][1]['source_file'], str(export.resolve()))
        bad = json.loads(export.read_text()); bad['candidates'][0]['title']='changed'
        export.write_text(json.dumps(bad))
        with self.assertRaises(ValueError): self.run_queue([export])
    def test_repeated_source_fingerprint_retains_both_provenances(self):
        self.write([row('legacy1','원제목')])
        env = {'schema_version':1,'candidates':[{'ledger_id':'legacy1','title':'원제목','status':'unreviewed'}]}
        a = Path(self.tmp.name)/'a.json'; b = Path(self.tmp.name)/'b.json'
        a.write_text(json.dumps(env)); b.write_text(json.dumps(env))
        result = self.run_queue([a,b])
        self.assertEqual(result['counts']['total'], 2)
        self.assertEqual(result['by_source_kind']['new_source_rows']['total'], 0)
        self.assertIn('repeated_source_fingerprint', [d['kind'] for d in result['diagnostics']])


class ExportReviewStatusAdapterTests(unittest.TestCase):
    def test_id_based_research_export_supplies_optional_empty_structural_fields(self):
        from bulk_candidate_queue import adapt
        original={'schema_version':1,'candidates':[{'id':'new-1','title':'별도 후보',
                  'review_status':'unreviewed','source_urls':[{'url':'https://example.org/one',
                  'access':'direct_body','independent_group':'one'}]}]}
        before=copy.deepcopy(original)
        result, raw=adapt(original,'research/export.json')
        self.assertEqual(result['candidates'][0]['dictionary_paths'],[])
        self.assertEqual(result['candidates'][0]['notes'],[])
        self.assertEqual(result['candidates'][0]['evidence'],[])
        self.assertEqual(original,before)
        self.assertEqual(raw['new-1'],before['candidates'][0])
        bad=copy.deepcopy(original)
        bad['candidates'][0]['notes']='not-list'
        with self.assertRaises(ValueError):adapt(bad,'research/export.json')


class UnverifiedPriorStateQueueTests(unittest.TestCase):
    setUp=BulkCandidateQueueTests.setUp
    write=BulkCandidateQueueTests.write
    run_queue=BulkCandidateQueueTests.run_queue
    def test_included_or_duplicate_without_exact_link_is_held_not_new_work(self):
        records=[row('a','unmatched included'),row('b','unmatched duplicate')]
        records[0].update(status='included',dictionary_paths=['memes/existing.md'])
        records[1].update(status='duplicate',duplicate_of='a')
        self.write(records)
        result=self.run_queue()
        self.assertEqual([r['classification'] for r in result['rows']],['held','held'])
        self.assertEqual([r['candidate']['status'] for r in result['rows']],['included','duplicate'])
        self.assertEqual(result['counts']['needs_research'],0)
        self.assertIn('stale_included_status',[d['kind'] for d in result['diagnostics']])

if __name__ == '__main__':
    unittest.main()
