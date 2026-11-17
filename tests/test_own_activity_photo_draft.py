"""Structural photo-sharing draft tests; metadata checks are not fact verification."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class OwnActivityPhotoDraftTests(unittest.TestCase):
    ID = 'proof-photo'
    SHA = '54d487149fba2edaa1a166f6f73d61633b1e5c2f'
    REQ = {'situations': ['활동기록사진'], 'targets': ['자기']}

    def setUp(self):
        self.profiles = load_profiles(ROOT)['profiles']
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, **kwargs):
        r = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(r['status'], 'unsupported_filter')
        return [h for h in r['results'] if h['entry_id'] == self.ID]

    def provisional(self):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == self.ID)
        entry['review_status'] = 'reviewed'
        return index, entry

    def test_source_and_narrow_unknown_draft_shape(self):
        rows = [p for p in self.profiles if p['entry_id'] == self.ID]
        self.assertEqual(len(rows), 1)
        p = rows[0]
        self.assertEqual(p['source_sha'], self.SHA)
        self.assertEqual(self.SHA, blob_sha(ROOT / 'memes' / 'proof-photo.md'))
        self.assertEqual(p['review_status'], 'reviewed')
        self.assertEqual(len(p['usages']), 1)
        u = p['usages'][0]
        self.assertEqual(u['id'], 'share-own-completed-activity')
        self.assertEqual(u['emotion_status'], 'unknown')
        self.assertEqual(u['emotions'], [])
        self.assertEqual(u['intents'], ['활동기록공유'])
        self.assertEqual(u['situations'], ['활동기록사진'])
        self.assertEqual(u['targets'], ['자기'])
        self.assertEqual(u['safety'], 'standard')
        self.assertEqual(u['risk_flags'], ['사실오인'])
        self.assertEqual(u['example']['kind'], 'editorial')
        self.assertEqual(u['retrieval_requirements'], self.REQ)

    def test_new_concepts_defined_once(self):
        for facet, label in [('intents', '활동기록공유'), ('situations', '활동기록사진')]:
            rows = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['aliases'], [])
            self.assertTrue(rows[0]['definition'].strip())

    def test_provisional_exact_requirements_return_context_checked_candidate(self):
        index, entry = self.provisional()
        for mode in ('lookup', 'recommend'):
            hits = self.hits(index, mode=mode, **self.REQ)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]['usage_id'], 'share-own-completed-activity')
            self.assertTrue(hits[0]['requires_context_check'])
            self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
        self.assertFalse(self.hits(index, mode='recommend', query=entry['title']))
        explanation = self.hits(index, mode='lookup', query=entry['title'])
        self.assertEqual(len(explanation), 1)
        self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_provisional_missing_or_and_wrong_target_filters_blocked(self):
        index, _ = self.provisional()
        blocked = [
            {'intents': ['활동기록공유']},
            {'situations': ['활동기록사진']},
            {'targets': ['자기']},
            {'situations': ['활동기록사진', '결과물공유'], 'targets': ['자기']},
            {'situations': ['활동기록사진'], 'targets': ['자기', '상대']},
        ]
        blocked += [{'situations': ['활동기록사진'], 'targets': [target]}
                    for target in ('상대', '제삼자', '상황')]
        for mode in ('lookup', 'recommend'):
            for filters in blocked:
                self.assertFalse(self.hits(index, mode=mode, **filters))

    def test_neighboring_situations_alone_do_not_match(self):
        index, _ = self.provisional()
        for situation in ('결과물공유', '작업솜씨평가', '일완료'):
            for mode in ('lookup', 'recommend'):
                for filters in ({'situations': [situation]},
                                {'situations': [situation], 'targets': ['자기']}):
                    self.assertFalse(self.hits(index, mode=mode, **filters))
        # This reflects this usage's required facets, not semantic impossibility
        # of overlapping activities in a real person's experience.

    def test_context_omits_title_and_boundary_metadata_remains(self):
        index, entry = self.provisional()
        u = entry['usages'][0]
        self.assertNotIn(entry['title'], u['context'])
        boundary = ' '.join(u['avoid_when']) + u['review_note']
        for term in ('진위', '실제로 보지', '동의', '독립 검증', '메달'):
            self.assertIn(term, boundary)
        hit = self.hits(index, mode='recommend', **self.REQ)[0]
        self.assertTrue(hit['requires_context_check'])
        self.assertEqual(hit['usage']['risk_flags'], ['사실오인'])
        # Metadata preservation does not inspect an image or establish truth,
        # completed activity, consent, identity, location or depicted objects.

if __name__ == '__main__':
    unittest.main()
