"""Draft retrieval contracts only; no semantic or safety certification."""
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

class AbbreviationFoodRuleDraftTests(unittest.TestCase):
    SPEC = {
        'byeoldajul': ('c94c9df3584960ea615999812b02468575f824e3', 'caution',
                      {'situations': ['축약방식평가'], 'targets': ['상황']}),
        'guk-rule': ('f4809202023fdddc789bbc538ca717942776cbe5', 'standard',
                     {'intents': ['취향규칙화'], 'situations': ['음식조합취향']}),
    }
    def setUp(self):
        self.data = load_profiles(ROOT)
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        r = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(r['status'], 'unsupported_filter')
        return [h for h in r['results'] if h['entry_id'] == identity]

    def provisional(self):
        original = copy.deepcopy(self.data)
        cloned = copy.deepcopy(self.data)
        for p in cloned['profiles']:
            if p['entry_id'] in self.SPEC:
                p['review_status'] = 'reviewed'
        with patch('build_usage_index.load_profiles', return_value=cloned):
            index = build_usage_index(ROOT)
        self.assertEqual(self.data, original)
        self.assertEqual(load_profiles(ROOT), original)
        return index

    def test_source_bound_draft_shape(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in rows}, set(self.SPEC))
        for p in rows:
            sha, safety, req = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'draft')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['targets'], ['상황'])
            self.assertEqual(u['safety'], safety)
            self.assertEqual(u['retrieval_requirements'], req)
            self.assertEqual(u['example']['kind'], 'editorial')

    def test_drafts_hidden_with_exact_names(self):
        for e in self.index['entries']:
            if e['id'] not in self.SPEC:
                continue
            req = self.SPEC[e['id']][2]
            for mode in ('lookup', 'recommend'):
                for filters in (req, {'query': e['title']}, dict(req, query=e['title'])):
                    self.assertFalse(self.hits(self.index, e['id'], mode=mode, **filters))

    def test_provisional_lookup_positive_and_caution_default_exclusion(self):
        index = self.provisional()
        for identity, (_, safety, req) in self.SPEC.items():
            hits = self.hits(index, identity, mode='lookup', **req)
            self.assertEqual(len(hits), 1)
            self.assertTrue(hits[0]['requires_context_check'])
            self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
            recommended = self.hits(index, identity, mode='recommend', **req)
            self.assertEqual(len(recommended), 1 if safety == 'standard' else 0)
            e = next(e for e in index['entries'] if e['id'] == identity)
            self.assertFalse(self.hits(index, identity, mode='recommend', query=e['title']))
            if safety == 'caution':
                self.assertFalse(self.hits(index, identity, mode='recommend',
                                          query=e['title'], **req))

    def test_provisional_missing_and_or_requirements_blocked(self):
        index = self.provisional()
        extras = {'situations': '성과', 'targets': '자기', 'intents': '상태설명'}
        for identity, (_, _, req) in self.SPEC.items():
            cases = [{k: v for k, v in req.items() if k != facet} for facet in req]
            for facet in req:
                broad = copy.deepcopy(req)
                broad[facet].append(extras[facet])
                cases.append(broad)
            for mode in ('lookup', 'recommend'):
                for filters in cases:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))

    def test_three_new_concepts_and_boundary_metadata(self):
        for facet, label in [('intents', '취향규칙화'), ('situations', '축약방식평가'),
                             ('situations', '음식조합취향')]:
            rows = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['definition'].strip())
        for e in self.index['entries']:
            if e['id'] not in self.SPEC:
                continue
            u = e['usages'][0]
            self.assertNotIn(e['title'], u['context'])
            notes = ' '.join(u['avoid_when']) + u['review_note']
            words = ('설명 요청', '능력', '기본 recommend') if e['id'] == 'byeoldajul' else ('입력에 없는', '식이 제한', '건강')
            for word in words:
                self.assertIn(word, notes)
        # These assertions preserve editorial boundaries, not dietary advice,
        # real consent or an LLM's ability to avoid invented food combinations.

if __name__ == '__main__':
    unittest.main()
