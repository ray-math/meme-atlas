"""Structural draft gates only; responsibility and causal truth are not certified."""
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

class SeubuljaeChoiceDraftTests(unittest.TestCase):
    ID = 'seubuljae'
    SHA = '5425c472be370d7a694ef922ab6c75d773a92bb3'
    REQ = {'intents': ['자조'], 'situations': ['자초한곤란'], 'targets': ['자기']}

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

    def test_source_bound_unknown_draft(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] == self.ID]
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p['source_sha'], self.SHA)
        self.assertEqual(self.SHA, blob_sha(ROOT / 'memes' / 'seubuljae.md'))
        self.assertEqual(p['review_status'], 'draft')
        self.assertEqual(len(p['usages']), 1)
        u = p['usages'][0]
        self.assertEqual(u['id'], 'own-minor-choice-backfire')
        self.assertEqual(u['emotion_status'], 'unknown')
        self.assertEqual(u['emotions'], [])
        self.assertEqual(u['safety'], 'standard')
        self.assertEqual(u['risk_flags'], ['고통축소'])
        self.assertEqual(u['retrieval_requirements'], self.REQ)
        for facet, labels in self.REQ.items():
            self.assertEqual(u[facet], labels)
        self.assertEqual(u['example']['kind'], 'editorial')

    def test_draft_hidden_in_both_modes_even_exact_name(self):
        entry = next(e for e in self.index['entries'] if e['id'] == self.ID)
        for mode in ('lookup', 'recommend'):
            for filters in (self.REQ, {'query': entry['title']},
                            dict(self.REQ, query=entry['title'])):
                self.assertFalse(self.hits(self.index, mode=mode, **filters))

    def test_provisional_exact_positive_does_not_mutate_original(self):
        index = self.provisional()
        for mode in ('lookup', 'recommend'):
            hits = self.hits(index, mode=mode, **self.REQ)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['usage_id'], 'own-minor-choice-backfire')
            self.assertTrue(hits[0]['requires_context_check'])
            self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])

    def test_each_missing_broad_or_and_opposite_filter_blocked(self):
        index = self.provisional()
        alternatives = {'intents': '상태설명', 'situations': '기대와현실차이', 'targets': '상대'}
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
        for situation in ('과거언행회상', '구체적이점발견', '기대와현실차이'):
            filters = dict(self.REQ, situations=[situation])
            for mode in ('lookup', 'recommend'):
                self.assertFalse(self.hits(index, mode=mode, **filters))
        # Narrow facets can coexist in a real situation; no exclusivity claim.

    def test_definition_and_boundaries_preserved(self):
        concepts = [c for c in self.vocab['facets']['situations'] if c['label'] == '자초한곤란']
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['aliases'], [])
        self.assertTrue(concepts[0]['definition'].strip())
        entry = next(e for e in self.index['entries'] if e['id'] == self.ID)
        u = entry['usages'][0]
        self.assertNotIn(entry['title'], u['context'])
        notes = ' '.join(u['avoid_when']) + u['review_note']
        for term in ('자발적', '강요', '피해', '심각', '인과관계'):
            self.assertIn(term, notes)
        # Metadata tests are not causal verification, victim blame detection
        # or an independently measured natural-language safety evaluation.

if __name__ == '__main__':
    unittest.main()
