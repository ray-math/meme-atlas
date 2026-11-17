import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_own_activity_photo_scope import evaluate

class OwnActivityPhotoScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'P-record','P-other','P-details','P-private','P-consent','A07','A26','E18'})
        # Candidate behavior is observed before semantic review.
