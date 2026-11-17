"""Structural draft regressions, not a natural-language or context-safety evaluation."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class ExplanationVisitDraftTests(unittest.TestCase):
    SPEC = {
        'help-speedwagon': {
            'usage_id': 'request-online-context',
            'sha': 'c8bd6618ae8eebb8b974385133ac3a4cfea41e9d',
            'requirements': {'intents': ['해설요청'], 'targets': ['상대']},
        },
        'internet-pilgrimage': {
            'usage_id': 'mark-public-post-visit',
            'sha': '1b1371d5bd9c6f841f6e8990e82c190581ae96c4',
            'requirements': {'situations': ['화제글방문'], 'targets': ['상황']},
        },
    }

    def setUp(self):
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        response = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(response['status'], 'unsupported_filter')
        return [h for h in response['results'] if h['entry_id'] == identity]

    def test_source_bound_unknown_caution_reviews(self):
        profiles = [p for p in load_profiles(ROOT)['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in profiles}, set(self.SPEC))
        for p in profiles:
            spec = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], spec['sha'])
            self.assertEqual(p['source_sha'], blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'reviewed')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], spec['usage_id'])
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['safety'], 'caution')
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['retrieval_requirements'], spec['requirements'])
            if p['entry_id'] == 'help-speedwagon':
                self.assertEqual(u['situations'], [])
                self.assertEqual(u['intents'], ['해설요청'])
                self.assertEqual(u['targets'], ['상대'])
            else:
                self.assertEqual(u['intents'], ['방문표시'])
                self.assertEqual(u['situations'], ['화제글방문'])
                self.assertEqual(u['targets'], ['상황'])

    def test_single_defined_vocabulary_without_aliases(self):
        for facet, label in [('intents', '해설요청'), ('intents', '방문표시'),
                             ('situations', '화제글방문')]:
            rows = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['aliases'], [])
            self.assertTrue(rows[0]['definition'].strip())

    def test_hypothetical_caution_lookup_is_not_recommendation(self):
        for identity, spec in self.SPEC.items():
            index = copy.deepcopy(self.index)
            entry = next(e for e in index['entries'] if e['id'] == identity)
            entry['review_status'] = 'reviewed'
            req = spec['requirements']
            matches = self.hits(index, identity, mode='lookup', **req)
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]['usage_id'], spec['usage_id'])
            self.assertTrue(matches[0]['requires_context_check'])
            self.assertTrue(matches[0]['retrieval_scope']['explicit_filters_match'])
            self.assertFalse(matches[0]['retrieval_scope']['exact_lookup_only'])
            for filters in (req, dict(req, query=entry['title']),
                            {'query': entry['title']}):
                self.assertFalse(self.hits(index, identity, mode='recommend', **filters))
            for facet in req:
                incomplete = {k: v for k, v in req.items() if k != facet}
                self.assertFalse(self.hits(index, identity, mode='lookup', **incomplete))
            wrong_target = dict(req, targets=['자기'])
            broad_target = dict(req, targets=req['targets'] + ['자기'])
            broad_facet = copy.deepcopy(req)
            if identity == 'help-speedwagon':
                broad_facet['intents'].append('칭찬')
            else:
                broad_facet['situations'].append('성과')
            for filters in (wrong_target, broad_target, broad_facet):
                self.assertFalse(self.hits(index, identity, mode='lookup', **filters))
            explanation = self.hits(index, identity, mode='lookup', query=entry['title'])
            self.assertEqual(len(explanation), 1)
            self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_explanation_filters_do_not_certify_online_context(self):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == 'help-speedwagon')
        entry['review_status'] = 'reviewed'
        req = self.SPEC['help-speedwagon']['requirements']
        # Same semantic filters can be supplied for a formal explanation request.
        # No additional online-situation gate exists. Preserve this limitation.
        matches = self.hits(index, entry['id'], mode='lookup', **req)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['retrieval_scope']['required_filters'], req)
        self.assertTrue(matches[0]['requires_context_check'])
        self.assertFalse(self.hits(index, entry['id'], mode='recommend', **req))

if __name__ == '__main__':
    unittest.main()
