"""Replay frozen, synthetic final-evaluation plans without calling an LLM."""
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from replay_nl_queries import replay
from compare_evaluation_expansion import compare,load_additions

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
                self.assertEqual(frozen['plans_sha256'], actual['plans_sha256'])
                # Corpus coverage may grow without changing these case outcomes.
                # Historical hashes stay in snapshots; gate reviewed case-specific additions and other behavioral drift,
                # not unrelated inventory growth.
                compare(frozen['results'],actual['results'],
                        'holdout' if prefix=='holdout' else 'challenge/'+plan_name.removesuffix('-plans'),
                        load_additions(ROOT))

    def test_v3_public_regression_behavior_is_preserved(self):
        # Existing public cases, not a new held-out accuracy estimate.
        for group in ['audit','editorial']:
            with self.subTest(group=group):
                folder=ROOT/'eval/regression-v3'
                plans=json.loads((folder/f'{group}-plans.json').read_text())['plans']
                frozen=json.loads((folder/f'{group}-retrieval.json').read_text())
                actual=replay(plans,ROOT)
                self.assertEqual(frozen['plans_sha256'],actual['plans_sha256'])
                compare(frozen['results'],actual['results'],'regression-v3/'+group,load_additions(ROOT))
