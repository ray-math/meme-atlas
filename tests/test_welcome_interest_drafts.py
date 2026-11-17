"""Registration regression only; hypothetical review flags are in-memory, not promotions."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class WelcomeInterestDraftTests(unittest.TestCase):
    IDS = {'bangga-bangga', 'anmul-angung'}

    def setUp(self):
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        result = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(result['status'], 'unsupported_filter')
        return [h for h in result['results'] if h['entry_id'] == identity]

    def provisional(self, identity):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == identity)
        entry['review_status'] = 'reviewed'
        return index, entry

    def test_registered_profiles_remain_source_bound_drafts(self):
        profiles = [p for p in load_profiles(ROOT)['profiles'] if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in profiles}, self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in profiles), 2)
        for p in profiles:
            self.assertEqual(p['review_status'], 'draft')
            self.assertEqual(p['source_sha'], blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            u = p['usages'][0]
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertTrue(u['review_note'])
            if p['entry_id'] == 'bangga-bangga':
                self.assertEqual(u['emotion_status'], 'annotated')
                self.assertEqual(u['emotions'], ['반가움'])
                self.assertEqual(u['intents'], ['인사'])
                self.assertEqual(u['safety'], 'standard')
                self.assertEqual(u['retrieval_requirements'],
                                 {'situations': ['만남시작'], 'targets': ['상대']})
            else:
                self.assertEqual(u['emotion_status'], 'unknown')
                self.assertEqual(u['emotions'], [])
                self.assertEqual(u['intents'], ['관심없음표시'])
                self.assertEqual(u['situations'], [])
                self.assertEqual(u['safety'], 'caution')
                self.assertEqual(set(u['risk_flags']), {'관계의존', '무시로들림', '고통축소'})
                self.assertEqual(u['retrieval_requirements'],
                                 {'intents': ['관심없음표시'], 'targets': ['상황']})

    def test_new_vocabulary_has_single_explicit_definitions(self):
        for facet, label in [('emotions', '반가움'), ('situations', '만남시작'),
                             ('intents', '관심없음표시')]:
            concepts = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(concepts), 1)
            self.assertTrue(concepts[0]['definition'].strip())

    def test_drafts_hidden_even_with_exact_names_and_full_filters(self):
        for entry in self.index['entries']:
            if entry['id'] not in self.IDS:
                continue
            requirements = entry['usages'][0]['retrieval_requirements']
            for mode in ('lookup', 'recommend'):
                for filters in ({'query': entry['title']}, requirements,
                                dict(requirements, query=entry['title'])):
                    with self.subTest(identity=entry['id'], mode=mode, filters=filters):
                        self.assertFalse(self.hits(self.index, entry['id'], mode=mode, **filters))

    def test_hypothetical_standard_welcome_requires_both_exact_filters(self):
        index, entry = self.provisional('bangga-bangga')
        requirements = entry['usages'][0]['retrieval_requirements']
        for filters in [
            {'intents': ['인사']},
            {'emotions': ['반가움']},
            {'query': entry['title']},
            {'situations': ['만남시작']},
            {'targets': ['상대']},
            {'situations': ['만남시작', '헤어짐'], 'targets': ['상대']},
            {'situations': ['만남시작'], 'targets': ['상대', '자기']},
        ]:
            with self.subTest(filters=filters):
                self.assertFalse(self.hits(index, entry['id'], mode='recommend', **filters))
        matches = self.hits(index, entry['id'], mode='recommend', **requirements)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['usage_id'], 'friendly-welcome')
        self.assertTrue(matches[0]['retrieval_scope']['explicit_filters_match'])
        self.assertFalse(matches[0]['retrieval_scope']['exact_lookup_only'])
        explanation = self.hits(index, entry['id'], query=entry['title'], mode='lookup')
        self.assertEqual(len(explanation), 1)
        self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_hypothetical_caution_never_enters_default_recommendations(self):
        index, entry = self.provisional('anmul-angung')
        requirements = entry['usages'][0]['retrieval_requirements']
        for filters in (requirements, dict(requirements, query=entry['title']),
                        {'query': entry['title']}):
            self.assertFalse(self.hits(index, entry['id'], mode='recommend', **filters))
        matches = self.hits(index, entry['id'], mode='lookup', **requirements)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['usage_id'], 'dismiss-optional-topic')
        self.assertTrue(matches[0]['requires_context_check'])
        self.assertFalse(self.hits(index, entry['id'], mode='lookup',
                                  intents=['관심없음표시'], targets=['상황', '상대']))
        self.assertFalse(self.hits(index, entry['id'], mode='lookup',
                                  intents=['관심없음표시', '제지'], targets=['상황']))
        explanation = self.hits(index, entry['id'], mode='lookup', query=entry['title'])
        self.assertEqual(len(explanation), 1)
        self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

if __name__ == '__main__':
    unittest.main()
