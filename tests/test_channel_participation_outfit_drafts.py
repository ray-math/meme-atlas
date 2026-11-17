"""Draft gates only; no implicit review promotion or natural-language safety claim."""
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

class ChannelParticipationOutfitDraftTests(unittest.TestCase):
    SPEC = {
        'jotdaet-gual': ('8b8824cbe4782f692244f58c32059583acf18754',
                         {'intents': ['채널참여요청'], 'targets': ['상대']}),
        'kkuan-kku': ('036c15bb60a6e154e67e33bff8cbc45b5fc7b691',
                     {'situations': ['자연스러운차림'], 'targets': ['상황']}),
    }
    def setUp(self):
        self.data = load_profiles(ROOT)
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        result = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(result['status'], 'unsupported_filter')
        return [h for h in result['results'] if h['entry_id'] == identity]

    def provisional(self):
        before = copy.deepcopy(self.data)
        cloned = copy.deepcopy(self.data)
        for profile in cloned['profiles']:
            if profile['entry_id'] in self.SPEC:
                profile['review_status'] = 'reviewed'
        with patch('build_usage_index.load_profiles', return_value=cloned):
            index = build_usage_index(ROOT)
        self.assertEqual(self.data, before)
        self.assertEqual(load_profiles(ROOT), before)
        return index

    def test_source_status_requirements(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in rows}, set(self.SPEC))
        for p in rows:
            sha, req = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'reviewed')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['safety'], 'standard')
            self.assertEqual(u['retrieval_requirements'], req)
            self.assertEqual(u['example']['kind'], 'editorial')

    def test_provisional_two_explicit_positives_preserve_original_data(self):
        index = self.provisional()
        for identity, (_, req) in self.SPEC.items():
            for mode in ('lookup', 'recommend'):
                hits = self.hits(index, identity, mode=mode, **req)
                self.assertEqual(len(hits), 1)
                self.assertTrue(hits[0]['requires_context_check'])
                self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])

    def test_provisional_missing_and_broad_or_blocked(self):
        index = self.provisional()
        for identity, (_, req) in self.SPEC.items():
            cases = [{k: v for k, v in req.items() if k != missing} for missing in req]
            cases.append(dict(req, targets=req['targets'] + ['자기']))
            cases.append(dict(req, targets=['자기']))
            broad = copy.deepcopy(req)
            if identity == 'jotdaet-gual':
                broad['intents'].append('관심요청')
            else:
                broad['situations'].append('작업솜씨평가')
            cases.append(broad)
            for mode in ('lookup', 'recommend'):
                for filters in cases:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))

    def test_new_definitions_and_boundary_metadata(self):
        for facet, label in [('intents', '채널참여요청'), ('situations', '자연스러운차림')]:
            rows = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertTrue(rows[0]['definition'].strip())
        for e in self.index['entries']:
            if e['id'] not in self.SPEC:
                continue
            u = e['usages'][0]
            self.assertNotIn(e['title'], u['context'])
            notes = ' '.join(u['avoid_when'])
            expected = ('한 행동', '실제 클릭') if e['id'] == 'jotdaet-gual' else ('제공되지 않은', '사진을 보지')
            for term in expected:
                self.assertIn(term, notes)
        # Metadata checks do not test action-count inference or image grounding.

if __name__ == '__main__':
    unittest.main()
