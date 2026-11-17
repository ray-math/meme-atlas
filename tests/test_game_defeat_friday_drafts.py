"""Source-bound rollout tests; provisional copies do not certify external facts."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class GameDefeatFridayDraftTests(unittest.TestCase):
    SPEC = {
        'gg': ('own-game-defeat', '패배인정', '게임패배', '자기',
               '52ecef09841e9832ec832c290db7a51649c514d9'),
        'fiery-friday': ('friday-leisure-anticipation', '상태설명', '금요일여가', '상황',
                        'eb4d5ec8532b249d8130fd9fb643e74865257167'),
    }
    def setUp(self):
        self.profiles = load_profiles(ROOT)['profiles']
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        r = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(r['status'], 'unsupported_filter')
        return [h for h in r['results'] if h['entry_id'] == identity]

    def provisional(self, identity):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == identity)
        entry['review_status'] = 'reviewed'
        return index, entry

    def test_source_bound_draft_shape_and_emotions(self):
        selected = [p for p in self.profiles if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in selected}, set(self.SPEC))
        for p in selected:
            uid, intent, situation, target, sha = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'reviewed')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], uid)
            self.assertEqual(u['intents'], [intent])
            self.assertEqual(u['situations'], [situation])
            self.assertEqual(u['targets'], [target])
            self.assertEqual(u['safety'], 'standard')
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['retrieval_requirements'],
                             {'situations': [situation], 'targets': [target]})
            self.assertEqual(u['emotion_status'], 'unknown' if p['entry_id'] == 'gg' else 'annotated')
            self.assertEqual(u['emotions'], [] if p['entry_id'] == 'gg' else ['기대'])

    def test_new_concepts_defined_once(self):
        for facet, label in [('intents', '패배인정'), ('situations', '게임패배'),
                             ('situations', '금요일여가')]:
            rows = [c for c in self.vocab['facets'][facet] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['aliases'], [])
            self.assertTrue(rows[0]['definition'].strip())

    def test_provisional_exact_filters_allow_standard_candidates(self):
        for identity, (uid, _, situation, target, _) in self.SPEC.items():
            index, entry = self.provisional(identity)
            req = {'situations': [situation], 'targets': [target]}
            for mode in ('lookup', 'recommend'):
                hits = self.hits(index, identity, mode=mode, **req)
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0]['usage_id'], uid)
                self.assertTrue(hits[0]['requires_context_check'])
                self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
            self.assertFalse(self.hits(index, identity, mode='recommend', query=entry['title']))
            explanation = self.hits(index, identity, mode='lookup', query=entry['title'])
            self.assertEqual(len(explanation), 1)
            self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_provisional_missing_broad_or_and_wrong_targets_blocked(self):
        for identity, (_, intent, situation, target, _) in self.SPEC.items():
            index, _ = self.provisional(identity)
            blocked = [
                {'intents': [intent]},
                {'intents': [intent], 'targets': [target]},
                {'situations': [situation]},
                {'targets': [target]},
                {'situations': [situation, '성과'], 'targets': [target]},
                {'situations': [situation], 'targets': [target, '상대']},
            ]
            blocked += [{'situations': [situation], 'targets': [wrong]}
                        for wrong in ('자기', '상대', '제삼자', '상황') if wrong != target]
            for mode in ('lookup', 'recommend'):
                for filters in blocked:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))

    def test_contexts_omit_titles_without_changing_examples(self):
        contexts = {p['entry_id']: p['usages'][0]['context']
                    for p in self.profiles if p['entry_id'] in self.SPEC}
        self.assertNotIn('gg', contexts['gg'].casefold())
        self.assertNotIn('불금', contexts['fiery-friday'])
        self.assertIn('패배', contexts['gg'])
        self.assertIn('기대', contexts['fiery-friday'])

    def test_boundaries_retained_not_external_state_guarantees(self):
        for identity in self.SPEC:
            index, _ = self.provisional(identity)
            _, _, situation, target, _ = self.SPEC[identity]
            hit = self.hits(index, identity, mode='recommend',
                            situations=[situation], targets=[target])[0]
            self.assertTrue(hit['requires_context_check'])
            notes = ' '.join(hit['usage']['avoid_when']) + hit['usage']['review_note']
            if identity == 'gg':
                for boundary in ('공식 결과', '상대의 수락', '게임 시스템'):
                    self.assertIn(boundary, notes)
            else:
                for boundary in ('금요일이 아닌', '퇴근', '음주', '날짜'):
                    self.assertIn(boundary, notes)
        # These are metadata-preservation assertions, not live game/calendar
        # validation or proof that a natural-language safety checker worked.

if __name__ == '__main__':
    unittest.main()
