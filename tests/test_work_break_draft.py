"""Structural draft gates only; work completion or leave approval is not certified."""
import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class WorkBreakDraftTests(unittest.TestCase):
    ID = 'work-hard-leave'
    SHA = 'd2173cd9a2226d826fe520919143e32f5aebe3df'
    REQ = {'intents': ['휴식권유'], 'situations': ['일마친뒤휴가'], 'targets': ['상대']}

    def setUp(self):
        self.data = load_profiles(ROOT)
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, **kwargs):
        r = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(r['status'], 'unsupported_filter')
        return [h for h in r['results'] if h['entry_id'] == self.ID]

    def provisional(self):
        before = copy.deepcopy(self.data)
        cloned = copy.deepcopy(self.data)
        next(p for p in cloned['profiles'] if p['entry_id'] == self.ID)['review_status'] = 'reviewed'
        with patch('build_usage_index.load_profiles', return_value=cloned):
            index = build_usage_index(ROOT)
        self.assertEqual(self.data, before)
        self.assertEqual(load_profiles(ROOT), before)
        return index

    def test_source_bound_unknown_reviewed(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] == self.ID]
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p['source_sha'], self.SHA)
        self.assertEqual(self.SHA, blob_sha(ROOT / 'memes' / 'work-hard-leave.md'))
        self.assertEqual(p['review_status'], 'reviewed')
        self.assertEqual(len(p['usages']), 1)
        u = p['usages'][0]
        self.assertEqual(u['id'], 'encourage-willing-post-work-break')
        self.assertEqual(u['emotion_status'], 'unknown')
        self.assertEqual(u['emotions'], [])
        self.assertEqual(u['safety'], 'standard')
        self.assertEqual(u['risk_flags'], ['의미불명확'])
        self.assertEqual(u['retrieval_requirements'], self.REQ)
        for facet, labels in self.REQ.items():
            self.assertEqual(u[facet], labels)
        self.assertEqual(u['example']['kind'], 'editorial')

    def test_provisional_exact_positive_does_not_mutate_original(self):
        index = self.provisional()
        for mode in ('lookup', 'recommend'):
            hits = self.hits(index, mode=mode, **self.REQ)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['usage_id'], 'encourage-willing-post-work-break')
            self.assertTrue(hits[0]['requires_context_check'])
            self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])

    def test_each_missing_broad_or_and_opposite_filter_blocked(self):
        index = self.provisional()
        alternatives = {'intents': '인사', 'situations': '헤어짐', 'targets': '자기'}
        cases = []
        for facet in self.REQ:
            cases.append({k: v for k, v in self.REQ.items() if k != facet})
            broad = copy.deepcopy(self.REQ)
            broad[facet].append(alternatives[facet])
            cases.append(broad)
            opposite = copy.deepcopy(self.REQ)
            opposite[facet] = [alternatives[facet]]
            cases.append(opposite)
        for mode in ('lookup', 'recommend'):
            for filters in cases:
                self.assertFalse(self.hits(index, mode=mode, **filters))

    def test_neighboring_situations_not_substituted(self):
        index = self.provisional()
        for situation in ('헤어짐', '업무에서벗어남', '좋은일기원', '일완료'):
            filters = dict(self.REQ, situations=[situation])
            for mode in ('lookup', 'recommend'):
                self.assertFalse(self.hits(index, mode=mode, **filters))
        # Narrow facets can coexist in a real situation; no exclusivity claim.

    def test_definition_and_boundaries_preserved(self):
        concepts = [c for c in self.vocab['facets']['situations'] if c['label'] == '일마친뒤휴가']
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['aliases'], [])
        self.assertTrue(concepts[0]['definition'].strip())
        intents = [c for c in self.vocab['facets']['intents'] if c['label'] == '휴식권유']
        self.assertEqual(len(intents), 1)
        self.assertTrue(intents[0]['definition'].strip())
        entry = next(e for e in self.index['entries'] if e['id'] == self.ID)
        u = entry['usages'][0]
        self.assertNotIn(entry['title'], u['context'])
        notes = ' '.join(u['avoid_when']) + u['review_note']
        for term in ('휴가 승인', '강요', '퇴사', '심각', '휴가 의사'):
            self.assertIn(term, notes)
        # Metadata tests do not verify work completion, willing leave or approval.

if __name__ == '__main__':
    unittest.main()
