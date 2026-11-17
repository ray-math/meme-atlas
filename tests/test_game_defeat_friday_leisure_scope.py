import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_game_defeat_friday_leisure_scope import evaluate

class GameDefeatFridayLeisureScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'G-defeat','G-friday','G-force','G-system','G-offday','G-overwork','A04','E06','A20','A26'})
        # Candidate behavior is observed first, not assumed accurate.
