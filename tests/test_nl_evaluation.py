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
