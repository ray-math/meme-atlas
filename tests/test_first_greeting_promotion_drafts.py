"""Source-bound rollout regressions; metadata is not general semantic accuracy."""
import copy
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from usage_profiles import load_profiles, load_vocabulary, blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class FirstGreetingPromotionDraftTests(unittest.TestCase):
    SPEC = {
        'manbanjalbu': ('friendly-first-introduction', '첫만남', '상대', '인사',
                       'b633d35e82a8130613431cb1f56dce75cbd9191e'),
        'mangwanbu': ('request-attention-to-project', '작품활동소개', '상황', '관심요청',
                     '19fa456c64e6d16353c8735199951436121e2702'),
    }

    def setUp(self):
        self.profiles = load_profiles(ROOT)['profiles']
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        response = search(index, self.vocab, limit=100, **kwargs)
        self.assertNotEqual(response['status'], 'unsupported_filter')
        return [r for r in response['results'] if r['entry_id'] == identity]

    def provisional(self, identity):
        index = copy.deepcopy(self.index)
        entry = next(e for e in index['entries'] if e['id'] == identity)
        entry['review_status'] = 'reviewed'
        return index, entry

    def test_01_source_bound_draft_profiles(self):
        profiles = [p for p in self.profiles if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in profiles}, set(self.SPEC))
        for p in profiles:
            uid, situation, target, intent, sha = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'reviewed')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['id'], uid)
            self.assertEqual(u['safety'], 'standard')
            self.assertEqual(u['intents'], [intent])
            self.assertEqual(u['situations'], [situation])
            self.assertEqual(u['targets'], [target])
            self.assertEqual(u['example']['kind'], 'editorial')
            self.assertEqual(u['retrieval_requirements'],
                             {'situations': [situation], 'targets': [target]})

    def test_02_expressed_welcome_vs_unknown_emotion(self):
        for p in self.profiles:
            if p['entry_id'] not in self.SPEC:
                continue
            u = p['usages'][0]
            if p['entry_id'] == 'manbanjalbu':
                self.assertEqual(u['emotion_status'], 'annotated')
                self.assertEqual(u['emotions'], ['반가움'])
            else:
                self.assertEqual(u['emotion_status'], 'unknown')
                self.assertEqual(u['emotions'], [])

    def test_03_new_situations_and_existing_meeting_definition(self):
        for label in ('첫만남', '작품활동소개'):
            rows = [c for c in self.vocab['facets']['situations'] if c['label'] == label]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['aliases'], [])
            self.assertTrue(rows[0]['definition'].strip())
        existing = next(c for c in self.vocab['facets']['situations'] if c['label'] == '만남시작')
        self.assertEqual(existing, {"label":"만남시작","aliases":[],"definition":"만나거나 대화 공간에 등장한 사람을 맞이하는 상황. 처음 만나는 사람에게만 한정하지 않는다."})

    def test_04_attention_definition_update_preserves_existing_comfort_usage(self):
        rows = [c for c in self.vocab['facets']['intents'] if c['label'] == '관심요청']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['aliases'], [])
        self.assertEqual(rows[0]['definition'], "자신이나 소개하는 대상에 관심을 기울여 달라고 요청함. 관심의 대상과 요청의 목적은 개별 용법에서 구별하며, 그 자체로 위로·구매·구독 같은 특정 반응을 뜻하지 않는다.")
        hug = next(p for p in self.profiles if p['entry_id'] == 'hug-me-animal')
        usage = next(u for u in hug['usages'] if u['id'] == 'request-comfort')
        self.assertEqual(usage['intents'], ['위로요청', '관심요청'])

    def test_06_hypothetical_exact_filters_return_standard_candidates(self):
        for identity, (uid, situation, target, _, _) in self.SPEC.items():
            index, entry = self.provisional(identity)
            req = {'situations': [situation], 'targets': [target]}
            for mode in ('lookup', 'recommend'):
                matches = self.hits(index, identity, mode=mode, **req)
                self.assertEqual(len(matches), 1)
                self.assertEqual(matches[0]['usage_id'], uid)
                self.assertTrue(matches[0]['retrieval_scope']['explicit_filters_match'])
                self.assertTrue(matches[0]['requires_context_check'])
            self.assertFalse(self.hits(index, identity, mode='recommend', query=entry['title']))
            explanation = self.hits(index, identity, mode='lookup', query=entry['title'])
            self.assertEqual(len(explanation), 1)
            self.assertTrue(explanation[0]['retrieval_scope']['exact_lookup_only'])

    def test_07_broad_intent_or_and_missing_filters_blocked(self):
        for identity, (_, situation, target, intent, _) in self.SPEC.items():
            index, _ = self.provisional(identity)
            filters_list = [
                {'intents': [intent]},
                {'intents': [intent], 'targets': [target]},
                {'situations': [situation]},
                {'targets': [target]},
                {'situations': [situation, '성과'], 'targets': [target]},
                {'situations': [situation], 'targets': [target, '자기']},
            ]
            for mode in ('lookup', 'recommend'):
                for filters in filters_list:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))

    def test_08_narrow_first_meeting_and_project_focus(self):
        greeting, _ = self.provisional('manbanjalbu')
        project, _ = self.provisional('mangwanbu')
        for mode in ('lookup', 'recommend'):
            self.assertFalse(self.hits(greeting, 'manbanjalbu', mode=mode,
                                      situations=['만남시작'], targets=['상대']))
            self.assertFalse(self.hits(greeting, 'manbanjalbu', mode=mode,
                                      situations=['첫만남'], targets=['상황']))
            # Reader is the addressee, but this profile focuses on the project.
            self.assertFalse(self.hits(project, 'mangwanbu', mode=mode,
                                      situations=['작품활동소개'], targets=['상대']))

if __name__ == '__main__':
    unittest.main()
