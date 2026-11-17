"""Structural draft gates only; OTL candidate drift remains to be measured."""
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

class OtlFingerHeartDraftTests(unittest.TestCase):
    SPEC = {
        'otl': ('43d0612e03a847a14fb6d5bee5d6625bbf2766a7', '기대와현실차이', '자기'),
        'finger-heart': ('fe03b4b0be86e47769ae675729c0217cbf360153', '공개행사인사', '상대'),
    }

    def setUp(self):
        self.data = load_profiles(ROOT)
        self.vocab = load_vocabulary(ROOT)
        self.index = build_usage_index(ROOT)

    def hits(self, index, identity, **kwargs):
        kwargs.setdefault('limit', 100)
        r = search(index, self.vocab, **kwargs)
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

    def test_source_bound_draft_shapes(self):
        rows = [p for p in self.data['profiles'] if p['entry_id'] in self.SPEC]
        self.assertEqual({p['entry_id'] for p in rows}, set(self.SPEC))
        for p in rows:
            sha, situation, target = self.SPEC[p['entry_id']]
            self.assertEqual(p['source_sha'], sha)
            self.assertEqual(sha, blob_sha(ROOT / 'memes' / (p['entry_id'] + '.md')))
            self.assertEqual(p['review_status'], 'draft')
            self.assertEqual(len(p['usages']), 1)
            u = p['usages'][0]
            self.assertEqual(u['safety'], 'standard')
            expected = {'situations': [situation], 'targets': [target]}
            if p['entry_id'] == 'otl': expected['intents'] = ['상태설명']
            self.assertEqual(u['retrieval_requirements'], expected)
            self.assertEqual(u['targets'], [target])
            self.assertEqual(u['situations'], [situation])
            self.assertEqual(u['example']['kind'], 'editorial')
            if p['entry_id'] == 'otl':
                self.assertEqual(u['intents'], ['상태설명'])
                self.assertEqual(u['emotion_status'], 'annotated')
                self.assertEqual(u['emotions'], ['실망'])
            else:
                self.assertEqual(u['intents'], ['인사'])
                self.assertEqual(u['emotion_status'], 'unknown')
                self.assertEqual(u['emotions'], [])
                self.assertEqual(u['risk_flags'], ['동의오인', '호감확정오인'])

    def test_actual_drafts_hidden_even_exact_lookup(self):
        for e in self.index['entries']:
            if e['id'] not in self.SPEC:
                continue
            req = e['usages'][0]['retrieval_requirements']
            for mode in ('lookup', 'recommend'):
                for filters in (req, {'query': e['title']}, dict(req, query=e['title'])):
                    self.assertFalse(self.hits(self.index, e['id'], mode=mode, **filters))

    def test_provisional_positive_contains_own_usage_not_exclusive_results(self):
        index = self.provisional()
        for identity, (_, situation, target) in self.SPEC.items():
            for mode in ('lookup', 'recommend'):
                extra = {'intents': ['상태설명']} if identity == 'otl' else {}
                hits = self.hits(index, identity, mode=mode, situations=[situation], targets=[target], **extra)
                self.assertEqual(len(hits), 1)
                self.assertTrue(hits[0]['requires_context_check'])
                self.assertTrue(hits[0]['retrieval_scope']['explicit_filters_match'])
        # OTL uses broad existing facets: other candidates may also be returned.
        # This is not a zero-drift, precision or review-readiness assertion.

    def test_provisional_missing_or_wrong_target_blocked(self):
        index = self.provisional()
        for identity, (_, situation, target) in self.SPEC.items():
            req = {'situations': [situation], 'targets': [target]}
            if identity == 'otl': req['intents'] = ['상태설명']
            blocked = [{k:v for k,v in req.items() if k != missing} for missing in req]
            blocked.extend([dict(req, situations=[situation, '성과']),
                            dict(req, targets=[target, '상황']), dict(req, targets=['상황'])])
            if identity == 'otl': blocked.append(dict(req, intents=['상태설명', '자조']))
            for mode in ('lookup', 'recommend'):
                for filters in blocked:
                    self.assertFalse(self.hits(index, identity, mode=mode, **filters))

    def test_public_greeting_definition_and_boundary_metadata(self):
        rows = [c for c in self.vocab['facets']['situations'] if c['label'] == '공개행사인사']
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]['definition'].strip())
        for e in self.index['entries']:
            if e['id'] not in self.SPEC:
                continue
            u = e['usages'][0]
            self.assertNotIn(e['title'], u['context'])
            notes = ' '.join(u['avoid_when']) + u['review_note']
            words = ('위기', '포기', '신체 동작') if e['id'] == 'otl' else ('동의', '실제 수행', '반응')
            for word in words:
                self.assertIn(word, notes)
        # Metadata checks do not infer mental state, actual gestures or consent.


    def test_otl_function_gate_prevents_observed_historical_a16_addition(self):
        import json
        index = self.provisional()
        plans = json.loads((ROOT/'eval/regression-v3/audit-plans.json').read_text())
        plan = next(p for p in plans['plans'] if p['id'] == 'A16')
        self.assertFalse(self.hits(index, 'otl', **plan['filters']))
        without_function = copy.deepcopy(index)
        entry = next(e for e in without_function['entries'] if e['id'] == 'otl')
        entry['usages'][0]['retrieval_requirements'].pop('intents')
        self.assertEqual(len(self.hits(without_function, 'otl', **plan['filters'])), 1)
        self.assertIn('intents', next(e for e in index['entries'] if e['id']=='otl')['usages'][0]['retrieval_requirements'])
        # This observed candidate addition was not a proven final-answer misrecommendation.

if __name__ == '__main__':
    unittest.main()
