import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_work_interest_fan_meeting_scope import evaluate

class WorkInterestFanMeetingScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'K-work','K-fan','K-workwish','K-exploit','K-intrude','K-consent','A07','A21','E06','A26'})
        # Candidate behavior is observed first, not assumed accurate.
