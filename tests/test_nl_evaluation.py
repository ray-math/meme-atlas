import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_vocabulary

class VocabularyContractTests(unittest.TestCase):
    def test_current_definitions(self):
        data=load_vocabulary(ROOT)
        self.assertEqual(len(data['facet_definitions']),6)
        self.assertTrue(any('definition' in c for c in data['facets']['intents']))
    def test_describe_cli_does_not_search(self):
        result=subprocess.run([sys.executable,str(ROOT/'scripts/search_usage.py'),'--describe-facets'],
                              capture_output=True,text=True,check=True)
        self.assertIn('facet_definitions',json.loads(result.stdout))
        self.assertNotIn('results',json.loads(result.stdout))
    def test_invalid_vocabulary_definitions(self):
        base=load_vocabulary(ROOT)
        cases=[]
        bad=copy.deepcopy(base);bad['facet_definitions']['intents']='';cases.append(bad)
        bad=copy.deepcopy(base);bad['facets']['emotions'][0]['definition']=[];cases.append(bad)
        bad=copy.deepcopy(base);bad['facets']['emotions'][0]['aliases']=['!!!'];cases.append(bad)
        bad=copy.deepcopy(base);bad['schema_version']=True;cases.append(bad)
        cases.extend([[], {'schema_version':1,'facets':list(base['facets'])}])
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'data').mkdir()
            for value in cases:
                (root/'data/usage-vocabulary.json').write_text(json.dumps(value))
                with self.subTest(value=type(value).__name__):
                    with self.assertRaises(ValueError):load_vocabulary(root)

class ScoreContractTests(unittest.TestCase):
    def sample(self):
        return ({'cases':[{'id':'x','expected_action':'recommend','confidence':'high',
                           'acceptable_entry_ids':['a']}]},
                {'results':[{'id':'x','retrieval':{'status':'matches','results':[{'entry_id':'a','usage_id':'u'}]}}]},
                {'answers':[{'id':'x','action':'recommend','selected_entry_id':'a','selected_usage_id':'u'}]},
                {'judgments':[{'id':'x','action_ok':True,'selection_ok':True,'constraints_ok':True,'unsafe':False}]})
    def test_known_score(self):
        from score_nl_evaluation import score
        report=score(*self.sample())
        self.assertTrue(report['predeclared_gate_passed'])
        self.assertEqual(report['totals']['candidate_recall_hits'],1)
    def test_unsafe_never_passes(self):
        from score_nl_evaluation import score
        values=self.sample();values[3]['judgments'][0]['unsafe']=True
        self.assertFalse(score(*values)['predeclared_gate_passed'])
    def test_fabricated_usage_rejected(self):
        from score_nl_evaluation import score
        values=self.sample();values[2]['answers'][0]['selected_usage_id']='invented'
        with self.assertRaises(ValueError):score(*values)
    def test_missing_case_rejected(self):
        from score_nl_evaluation import score
        values=self.sample();values[3]['judgments']=[]
        with self.assertRaises(ValueError):score(*values)

    def test_missing_prior_confidence_is_not_failed_gate(self):
        from score_nl_evaluation import score
        values=self.sample();values[0]['cases'][0].pop('confidence')
        report=score(*values)
        self.assertFalse(report['predeclared_gate_applicable'])
        self.assertIsNone(report['predeclared_gate_passed'])

    def test_ambiguous_lookup_can_explain_retrieved_entry_without_single_sense(self):
        from score_nl_evaluation import score
        values=self.sample();values[2]['answers'][0].update(action='lookup',selected_usage_id=None)
        score(*values)
        values[2]['answers'][0]['action']='recommend'
        with self.assertRaises(ValueError):score(*values)
