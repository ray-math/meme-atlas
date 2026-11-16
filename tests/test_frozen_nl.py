"""Replay frozen, synthetic final-evaluation plans without calling an LLM."""
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from replay_nl_queries import replay

class FrozenNaturalLanguageTests(unittest.TestCase):
    def test_inputs_plans_and_actual_retrieval_agree(self):
        for prefix, input_name, plan_name, trace_name in [
            ('holdout', 'inputs', 'plans', 'retrieval'),
            ('challenge', 'audit-inputs', 'audit-plans', 'audit-retrieval'),
            ('challenge', 'editorial-inputs', 'editorial-plans', 'editorial-retrieval'),
        ]:
            with self.subTest(group=plan_name):
                folder = ROOT / 'eval' / prefix
                inputs = json.loads((folder / (input_name + '.json')).read_text())['inputs']
                plans = json.loads((folder / (plan_name + '.json')).read_text())['plans']
                frozen = json.loads((folder / (trace_name + '.json')).read_text())
                self.assertEqual([(x['id'], x['prompt']) for x in inputs],
                                 [(x['id'], x['prompt']) for x in plans])
                actual = replay(plans, ROOT)
                for key in ('results', 'plans_sha256', 'index_sha256', 'vocabulary_sha256', 'coverage'):
                    self.assertEqual(frozen[key], actual[key], key)
