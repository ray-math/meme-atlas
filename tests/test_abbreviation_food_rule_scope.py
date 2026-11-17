import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_abbreviation_food_rule_scope import evaluate

class AbbreviationFoodRuleScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'B-abbrev','F-rule','B-meaning','B-person','B-public',
                          'F-missing','F-force','F-fact','F-health','A08','A26','E22'})
        self.assertTrue(trace['requirements_enabled'])
        # Observe actual caution lookup, abstention and candidate behavior before promotion.
