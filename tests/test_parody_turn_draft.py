"""Caution draft gates only; lookup never certifies final suitability."""
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

class ParodyTurnDraftTests(unittest.TestCase):
    ID = 'but-the-question'
    SHA = '4d8b1bc5ef1b56d38ecb827d51db3a09bd34475d'
    REQ = {'intents': ['반전도입'], 'targets': ['상황']}
    def setUp(self):
        self.data = load_profiles(ROOT)
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)
    def hits(self, index, **kwargs):
        result = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(result['status'], 'unsupported_filter')
        return [h for h in result['results'] if h['entry_id'] == self.ID]
    def provisional(self):
        before = copy.deepcopy(self.data)
        cloned = copy.deepcopy(self.data)
        next(p for p in cloned['profiles'] if p['entry_id'] == self.ID)['review_status'] = 'reviewed'
        with patch('build_usage_index.load_profiles', return_value=cloned):
            index = build_usage_index(ROOT)
        self.assertEqual(self.data, before)
        self.assertEqual(load_profiles(ROOT), before)
        return index
    def test_source_bound_single_unknown_caution(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] == self.ID]
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p['source_sha'], self.SHA)
        self.assertEqual(self.SHA, blob_sha(ROOT / 'memes' / (self.ID + '.md')))
        self.assertEqual(p['review_status'], 'draft')
        self.assertEqual(len(p['usages']), 1)
        u = p['usages'][0]
        self.assertEqual(u['id'], 'introduce-provided-minor-twist')
        self.assertEqual(u['emotion_status'], 'unknown')
        self.assertEqual(u['emotions'], [])
        self.assertEqual(u['intents'], ['반전도입'])
        self.assertEqual(u['targets'], ['상황'])
        self.assertEqual(u['situations'], [])
        self.assertEqual(u['risk_flags'], ['사실오인'])
        self.assertEqual(u['safety'], 'caution')
        self.assertEqual(u['retrieval_requirements'], self.REQ)
        self.assertEqual(u['example']['kind'], 'editorial')
    def test_actual_draft_hidden_even_exact_name(self):
        e = next(e for e in self.index['entries'] if e['id'] == self.ID)
        for mode in ('lookup', 'recommend'):
            for filters in (self.REQ, {'query': e['title']}, dict(self.REQ, query=e['title'])):
                self.assertFalse(self.hits(self.index, mode=mode, **filters))
    def test_provisional_lookup_positive_but_recommend_never(self):
        index = self.provisional()
        e = next(e for e in index['entries'] if e['id'] == self.ID)
        hits = self.hits(index, mode='lookup', **self.REQ)
        self.assertEqual(len(hits), 1)
        self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
        self.assertFalse(hits[0]['retrieval_scope']['exact_lookup_only'])
        for filters in (self.REQ, {'query': e['title']}, dict(self.REQ, query=e['title']),
                        {'query': e['title'], 'intents': ['반전도입', '상태설명'], 'targets': ['상황']}):
            self.assertFalse(self.hits(index, mode='recommend', **filters))
    def test_missing_broad_or_opposite_generic_lookup_rejected(self):
        index = self.provisional()
        cases = [
            {'intents': ['반전도입']}, {'targets': ['상황']},
            {'intents': ['반전도입', '상태설명'], 'targets': ['상황']},
            {'intents': ['반전도입'], 'targets': ['상황', '상대']},
            {'intents': ['상태설명'], 'targets': ['상황']},
            {'intents': ['반전도입'], 'targets': ['상대']},
        ]
        for filters in cases:
            self.assertFalse(self.hits(index, mode='lookup', **filters))
            self.assertFalse(self.hits(index, mode='recommend', **filters))
    def test_exact_lookup_exception_is_explanation_not_recommendation(self):
        index = self.provisional()
        e = next(e for e in index['entries'] if e['id'] == self.ID)
        for filters in ({'query': e['title']},
                        {'query': e['title'], 'intents': ['반전도입', '상태설명'], 'targets': ['상황']}):
            hits = self.hits(index, mode='lookup', **filters)
            self.assertEqual(len(hits), 1)
            self.assertTrue(hits[0]['retrieval_scope']['exact_lookup_only'])
            self.assertTrue(hits[0]['requires_context_check'])
            self.assertFalse(self.hits(index, mode='recommend', **filters))
    def test_definition_context_and_avoid_boundaries(self):
        rows = [c for c in self.vocab['facets']['intents'] if c['label'] == '반전도입']
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['definition'].strip())
        e = next(e for e in self.index['entries'] if e['id'] == self.ID)
        u = e['usages'][0]
        self.assertNotIn(e['title'], u['context'])
        self.assertIn('이미 제공된', u['context'])
        notes = ' '.join(u['avoid_when'])
        for term in ('입력에 없', '공식 감사', '범죄', '공개 망신', '음성'):
            self.assertIn(term, notes)
        # Metadata retention is not factual, speech or final-use validation.

if __name__ == '__main__':
    unittest.main()
