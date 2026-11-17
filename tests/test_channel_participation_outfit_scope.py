import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_channel_participation_outfit_scope import evaluate

class ChannelParticipationOutfitScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'C-channel','C-outfit','C-one-action','C-pressure','C-click',
                          'C-unseen','C-details','C-effort','A07','A26','I-interest'})
        self.assertTrue(trace['requirements_enabled'])
        # Candidate behavior is observed before semantic review or promotion.

    def test_observed_candidates_and_boundaries(self):
        trace=evaluate(ROOT)
        rows={r['id']:r for r in trace['results']}
        for identity, expected in {'C-channel':['jotdaet-gual'],'C-outfit':['kkuan-kku'],
                                   'A07':['look-at-this-hand'],'I-interest':['mangwanbu']}.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']],expected)
            self.assertEqual(rows[identity]['retrieval']['mode'],'recommend')
        for identity in ('C-one-action','C-pressure','C-click','C-unseen','C-details','C-effort','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(trace['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/channel-participation-outfit-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))

    def test_final_answers_have_auditable_context_and_facts(self):
        from check_context_decisions import validate_decisions
        def read(name):return json.loads((ROOT/'eval/channel-participation-outfit-scope'/name).read_text())
        self.assertEqual(validate_decisions(read('plans.json'),read('retrieval.json'),read('answers.json'),expected_prompt_version='contextual-v3'),[])

    def test_original_provenance_error_and_bounded_correction_are_preserved(self):
        import copy
        from usage_profiles import blob_sha
        from compare_evaluation_expansion import strict_equal
        folder=ROOT/'eval/channel-participation-outfit-scope'
        original_path=folder/'answers-v1-provenance.json'
        self.assertEqual(blob_sha(original_path),'0e701be5b5edf6331a2e2f1ca48d91533fca6078')
        original=json.loads(original_path.read_text())
        corrected=json.loads((folder/'answers.json').read_text())
        trace=json.loads((folder/'retrieval.json').read_text())
        row=next(r for r in trace['results'] if r['id']=='C-effort')
        self.assertEqual(row['retrieval']['status'],'not_searched')
        old=next(r for r in original['answers'] if r['id']=='C-effort')
        new=next(r for r in corrected['answers'] if r['id']=='C-effort')
        self.assertIn('반환 용례',old['reason'])
        self.assertIn('이 행에서는 검색하지 않았다.',new['reason'])
        allowed=copy.deepcopy(original)
        next(r for r in allowed['answers'] if r['id']=='C-effort')['reason']=new['reason']
        self.assertTrue(strict_equal(allowed,corrected))
        # This bounded migration does not implement a general semantic-provenance checker.
