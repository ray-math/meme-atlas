"""Structural draft regressions; filter matches are not verified context."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class FutureWishAppearanceDraftTests(unittest.TestCase):
    SPEC = {
        'flower-road': ('wish-good-future', '응원', '좋은일기원', '상대',
                        'a9c2331068075d45d76e3ad2b0d2577a47a96ee5'),
        'gaptuk-twi': ('describe-unexpected-person-on-screen', '상태설명', '뜻밖등장', '상황',
                      'ac73b2b6de04f421b6eb41acb8f632084dee3e91'),
    }

    def setUp(self):
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        response = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(response['status'], 'unsupported_filter')
        return [h for h in response['results'] if h['entry_id'] == identity]

    def test_source_bound_unknown_standard_drafts(self):
        profiles = [p for p in load_profiles(ROOT)['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in profiles}, set(self.SPEC))
        for p in profiles:
            usage_id, intent, situation, target, sha = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'draft')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], usage_id)
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['safety'], 'standard')
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['intents'], [intent])
            self.assertEqual(u['situations'], [situation])
            self.assertEqual(u['targets'], [target])
            self.assertEqual(u['retrieval_requirements'],
                             {'situations': [situation], 'targets': [target]})

    def test_new_vocabulary_is_single_defined_concept(self):
        concepts = [c for c in self.vocab['facets']['situations'] if c['label'] == '뜻밖등장']
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['aliases'], [])
        self.assertTrue(concepts[0]['definition'].strip())

    def test_actual_drafts_hidden_in_both_modes(self):
        for entry in self.index['entries']:
            if entry['id'] not in self.SPEC:
                continue
            req = entry['usages'][0]['retrieval_requirements']
            for mode in ('lookup', 'recommend'):
                for filters in (req, {'query': entry['title']},
                                dict(req, query=entry['title'])):
                    with self.subTest(identity=entry['id'], mode=mode, filters=filters):
                        self.assertFalse(self.hits(self.index, entry['id'], mode=mode, **filters))

    def test_hypothetical_standard_requires_exact_situation_and_target(self):
        for identity, (usage_id, intent, situation, target, _) in self.SPEC.items():
            index = copy.deepcopy(self.index)
            entry = next(e for e in index['entries'] if e['id'] == identity)
            entry['review_status'] = 'reviewed'
            req = {'situations': [situation], 'targets': [target]}
            blocked = [
                {'intents': [intent]},
                {'intents': [intent], 'targets': [target]},
                {'situations': [situation]},
                {'targets': [target]},
                {'situations': [situation], 'targets': ['자기']},
                {'situations': [situation, '성과'], 'targets': [target]},
                {'situations': [situation], 'targets': [target, '자기']},
            ]
            for mode in ('lookup', 'recommend'):
                for filters in blocked:
                    with self.subTest(identity=identity, mode=mode, filters=filters):
                        self.assertFalse(self.hits(index, identity, mode=mode, **filters))
                matches = self.hits(index, identity, mode=mode, **req)
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]['usage_id'], usage_id)
                self.assertTrue(matches[0]['retrieval_scope']['explicit_filters_match'])
                self.assertFalse(matches[0]['retrieval_scope']['exact_lookup_only'])
                self.assertTrue(matches[0]['requires_context_check'])
            self.assertFalse(self.hits(index, identity, mode='recommend', query=entry['title']))
            explanation = self.hits(index, identity, mode='lookup', query=entry['title'])
            self.assertEqual(len(explanation), 1)
            self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_appearance_filters_do_not_certify_person_video_or_safety(self):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == 'gaptuk-twi')
        entry['review_status'] = 'reviewed'
        req = {'situations': ['뜻밖등장'], 'targets': ['상황']}
        # The situation concept also covers objects. These same filters can be
        # supplied outside this profile's person-on-screen scope; no hidden
        # person/video/intent/risk classifier is present.
        matches = self.hits(index, entry['id'], mode='recommend', **req)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['retrieval_scope']['required_filters'], req)
        self.assertTrue(matches[0]['requires_context_check'])
        self.assertTrue(matches[0]['usage']['context'])
        self.assertTrue(matches[0]['usage']['avoid_when'])

if __name__ == '__main__':
    unittest.main()
