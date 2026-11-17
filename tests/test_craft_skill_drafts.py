"""Draft registration regression; hypothetical review flags never persist."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class CraftSkillDraftTests(unittest.TestCase):
    SPEC = {
        'geumson': ('praise-third-party-craft', '제삼자', '칭찬', 'standard',
                    '26c1ac81bd49d557ca92e987887e0d91e03c7f0f'),
        'ttongson': ('self-deprecate-craft', '자기', '자조', 'caution',
                     'b600701774891b564521e77e0a0db306223a3b99'),
    }

    def setUp(self):
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        result = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(result['status'], 'unsupported_filter')
        return [h for h in result['results'] if h['entry_id'] == identity]

    def test_source_bound_unknown_drafts(self):
        profiles = [p for p in load_profiles(ROOT)['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in profiles}, set(self.SPEC))
        for p in profiles:
            usage_id, target, intent, safety, expected_sha = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], expected_sha)
            self.assertEqual(p['source_sha'], blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'draft')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], usage_id)
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['intents'], [intent])
            self.assertEqual(u['targets'], [target])
            self.assertEqual(u['situations'], ['작업솜씨평가'])
            self.assertEqual(u['safety'], safety)
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['retrieval_requirements'],
                             {'situations': ['작업솜씨평가'], 'targets': [target]})

    def test_vocabulary_is_single_defined_concept_without_aliases(self):
        concepts = [c for c in self.vocab['facets']['situations'] if c['label'] == '작업솜씨평가']
        self.assertEqual(len(concepts), 1)
        self.assertEqual(concepts[0]['aliases'], [])
        self.assertTrue(concepts[0]['definition'].strip())

    def test_actual_drafts_hidden_in_both_modes(self):
        for entry in self.index['entries']:
            if entry['id'] not in self.SPEC:
                continue
            requirements = entry['usages'][0]['retrieval_requirements']
            for mode in ('lookup', 'recommend'):
                for filters in ({'query': entry['title']}, requirements,
                                dict(requirements, query=entry['title'])):
                    with self.subTest(identity=entry['id'], mode=mode, filters=filters):
                        self.assertFalse(self.hits(self.index, entry['id'], mode=mode, **filters))

    def test_hypothetical_reviewed_exact_gates_and_safety(self):
        for identity, (usage_id, target, intent, safety, _) in self.SPEC.items():
            index = copy.deepcopy(self.index)
            entry = next(e for e in index['entries'] if e['id'] == identity)
            entry['review_status'] = 'reviewed'
            requirements = {'situations': ['작업솜씨평가'], 'targets': [target]}
            blocked = [
                {'intents': [intent]},
                {'intents': [intent], 'targets': [target]},
                {'situations': ['작업솜씨평가']},
                {'targets': [target]},
                {'situations': ['작업솜씨평가'], 'targets': ['상대']},
                {'situations': ['작업솜씨평가', '성과'], 'targets': [target]},
                {'situations': ['작업솜씨평가'], 'targets': [target, '상대']},
            ]
            for mode in ('lookup', 'recommend'):
                for filters in blocked:
                    with self.subTest(identity=identity, mode=mode, filters=filters):
                        self.assertFalse(self.hits(index, identity, mode=mode, **filters))
            matches = self.hits(index, identity, mode='lookup', **requirements)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]['usage_id'], usage_id)
            self.assertTrue(matches[0]['retrieval_scope']['explicit_filters_match'])
            self.assertFalse(matches[0]['retrieval_scope']['exact_lookup_only'])
            recommended = self.hits(index, identity, mode='recommend', **requirements)
            self.assertEqual(len(recommended), 1 if safety == 'standard' else 0)
            if recommended:
                self.assertEqual(recommended[0]['usage_id'], usage_id)
            self.assertFalse(self.hits(index, identity, mode='recommend', query=entry['title']))
            if safety == 'caution':
                self.assertFalse(self.hits(index, identity, mode='recommend',
                                          query=entry['title'], **requirements))
            explanation = self.hits(index, identity, mode='lookup', query=entry['title'])
            self.assertEqual(len(explanation), 1)
            self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

if __name__ == '__main__':
    unittest.main()
