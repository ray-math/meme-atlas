import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_work_break_scope import evaluate

class WorkBreakScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound_and_profiles_unchanged(self):
        before=(ROOT/'data/usage-profiles.json').read_bytes()
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'W-break','W-missing','W-expel','W-force','W-distress','W-right','W-invent',
                          'H-wish','G-leave','F-future','A26'})
        self.assertTrue(trace['requirements_enabled'])
        self.assertEqual((ROOT/'data/usage-profiles.json').read_bytes(),before)
        # Observe actual candidates before freezing a behavior assertion.

    def test_requirements_control_is_strict_boolean(self):
        for value in (None,0,1,'false',[],{}):
            with self.assertRaises(ValueError):
                evaluate(ROOT,enforce_requirements=value)
