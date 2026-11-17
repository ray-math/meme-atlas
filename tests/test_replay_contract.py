import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from replay_nl_queries import replay, validate_plan_envelope

class ReplayInputContractTests(unittest.TestCase):
 def sample(self):
  return {'schema_version':1,'prompt_version':'contextual-v3','plans':[{'id':'x','prompt':'서로 장난을 즐긴다','action':'clarify','filters':{}}]}
 def test_valid_envelope(self):
  self.assertEqual(validate_plan_envelope(self.sample())[0]['id'],'x')
 def test_missing_or_invalid_envelope_versions(self):
  for key,value in (('schema_version',None),('schema_version',2),('prompt_version',None),('prompt_version','other')):
   envelope=self.sample()
   if value is None:envelope.pop(key)
   else:envelope[key]=value
   with self.assertRaises(ValueError):validate_plan_envelope(envelope)
 def test_empty_plans_rejected_before_loading_dictionary(self):
  with self.assertRaises(ValueError):replay([],Path('/missing'))
 def test_invalid_plan_action_rejected_before_loading_dictionary(self):
  for action in ('other',[],{}):
   rows=self.sample()['plans'];rows[0]['action']=action
   with self.assertRaises(ValueError):replay(rows,Path('/missing'))
