import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_otl_finger_heart_scope import evaluate

class OtlFingerHeartScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'G-otl','G-heart','G-crisis','G-mock','G-body','G-done',
                          'G-consent','G-romance','G-force','A16','A26','E06'})
        self.assertTrue(trace['requirements_enabled'])
        # Observe broad OTL collisions before deciding review readiness.
