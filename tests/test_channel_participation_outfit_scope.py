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
