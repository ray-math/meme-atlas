import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_draft_readiness import evaluate

class DraftReadinessTests(unittest.TestCase):
    def test_published_draft_structural_probes(self):
        result=evaluate(ROOT)
        self.assertEqual(result['total'],10)
        self.assertEqual(result['passed'],10,result['results'])
