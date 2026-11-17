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
