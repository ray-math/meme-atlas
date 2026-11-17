import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_first_greeting_promotion_scope import evaluate

class FirstGreetingInterestScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'I-first','I-interest','I-formal','I-pressure','W-welcome','A13','A23','A26'})
        # Candidate behavior is observed first, then explicitly frozen.
        # No selected candidate or general accuracy is assumed here.
