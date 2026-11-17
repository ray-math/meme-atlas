import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_seubuljae_choice_scope import evaluate

class SeubuljaeChoiceScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound_and_profiles_unchanged(self):
        before=(ROOT/'data/usage-profiles.json').read_bytes()
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'S-choice','S-missing','S-forced','S-victim','S-serious','S-luck',
                          'O-disappointment','B-memory','R-gap','U-upside','A26'})
        self.assertTrue(trace['requirements_enabled'])
        self.assertEqual((ROOT/'data/usage-profiles.json').read_bytes(),before)
        # Candidate behavior is observed from actual Python output before freezing it.

    def test_requirements_control_is_strict_boolean(self):
        for value in (None,0,1,'false',[],{}):
            with self.assertRaises(ValueError):
                evaluate(ROOT,enforce_requirements=value)
