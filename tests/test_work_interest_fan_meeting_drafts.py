"""Structural draft tests, not proof of semantic exclusivity or verified context."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class WorkInterestFanMeetingDraftTests(unittest.TestCase):
    SPEC = {
        'deogeop-ilchi': ('own-interest-became-work', '관심사직업연결',
                         '48c9ae497d772bc923b4ff6501f34f04c8f43eb2'),
        'seongdeok': ('own-hoped-for-fan-meeting', '팬교류성취',
                     '339edafb707f77c5bbab18efd48529165cca93a8'),
    }

    def setUp(self):
        self.profiles = load_profiles(ROOT)['profiles']
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        result = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(result['status'], 'unsupported_filter')
        return [h for h in result['results'] if h['entry_id'] == identity]

    def provisional(self):
        index = copy.deepcopy(self.index)
        for entry in index['entries']:
            if entry['id'] in self.SPEC:
                entry['review_status'] = 'reviewed'
        return index

    def test_source_bound_unknown_self_state_drafts(self):
        selected = [p for p in self.profiles if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in selected}, set(self.SPEC))
        for p in selected:
            uid, situation, sha = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'reviewed')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], uid)
            self.assertEqual(u['emotion_status'], 'unknown')
            self.assertEqual(u['emotions'], [])
            self.assertEqual(u['intents'], ['상태설명'])
            self.assertEqual(u['targets'], ['자기'])
            self.assertEqual(u['situations'], [situation])
            self.assertEqual(u['safety'], 'standard')
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['retrieval_requirements'],
                             {'situations': [situation], 'targets': ['자기']})

    def test_two_defined_situations_without_aliases(self):
        for _, situation, _ in self.SPEC.values():
            rows = [c for c in self.vocab['facets']['situations'] if c['label'] == situation]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['aliases'], [])
            self.assertTrue(rows[0]['definition'].strip())

    def test_provisional_exact_conditions_return_standard_candidates(self):
        index = self.provisional()
        for identity, (uid, situation, _) in self.SPEC.items():
            for mode in ('lookup', 'recommend'):
                hits = self.hits(index, identity, mode=mode,
                                 situations=[situation], targets=['자기'])
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0]['usage_id'], uid)
                self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
                self.assertTrue(hits[0]['requires_context_check'])

    def test_broad_or_and_wrong_targets_blocked_by_current_contract(self):
        index = self.provisional()
        both = [v[1] for v in self.SPEC.values()]
        for identity, (_, situation, _) in self.SPEC.items():
            blocked = [
                {'intents': ['상태설명']},
                {'intents': ['상태설명'], 'targets': ['자기']},
                {'situations': [situation]},
                {'targets': ['자기']},
                {'situations': both, 'targets': ['자기']},
                {'situations': [situation], 'targets': ['자기', '상대']},
            ]
            blocked += [{'situations': [situation], 'targets': [target]}
                        for target in ('상대', '제삼자', '상황')]
            for mode in ('lookup', 'recommend'):
                for filters in blocked:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))
        # Broad OR fails singleton exact requirements. Real situations can overlap.

    def test_cross_situation_filters_are_profile_scoped_not_mutual_exclusivity(self):
        index = self.provisional()
        for identity, (_, situation, _) in self.SPEC.items():
            other = next(v[1] for key, v in self.SPEC.items() if key != identity)
            self.assertFalse(self.hits(index, identity, mode='recommend',
                                      situations=[other], targets=['자기']))
            self.assertEqual(len(self.hits(index, identity, mode='recommend',
                                           situations=[situation], targets=['자기'])), 1)
        # Separate calls may both be appropriate for one real person's experience.
        # This test checks stored facets only; it asserts no semantic contradiction.

    def test_contexts_do_not_contain_titles(self):
        for entry in self.index['entries']:
            if entry['id'] not in self.SPEC:
                continue
            context = entry['usages'][0]['context']
            self.assertNotIn(entry['title'], context)
            self.assertTrue(context.strip())

    def test_boundary_metadata_preserved_without_certifying_facts(self):
        index = self.provisional()
        for identity, (_, situation, _) in self.SPEC.items():
            hit = self.hits(index, identity, mode='recommend',
                            situations=[situation], targets=['자기'])[0]
            text = ' '.join(hit['usage']['avoid_when']) + hit['usage']['review_note']
            if identity == 'deogeop-ilchi':
                for word in ('전문성', '저임금', '고소득', '미래 취업'):
                    self.assertIn(word, text)
            else:
                for word in ('동의', '친밀', '사생활', '공식'):
                    self.assertIn(word, text)
            self.assertTrue(hit['requires_context_check'])
        # Metadata preservation is not a job, consent, intimacy or safety check.

if __name__ == '__main__':
    unittest.main()
