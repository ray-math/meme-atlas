import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from measure_usage_retrieval import measure

class UsageRetrievalMetricTests(unittest.TestCase):
 def sample(self,usage='wrong',separator=':'):
  return ({'schema_version':1,'cases':[{'id':'x','expected_action':'recommend','acceptable_usage_ids':['entry'+separator+'right']}]},
          {'schema_version':1,'results':[{'id':'x','retrieval':{'schema_version':1,'results':[{'entry_id':'entry','usage_id':usage}]}}]})
 def test_same_entry_wrong_usage_is_miss(self):
  result=measure(*self.sample())['groups']['recommendation_requests']
  self.assertEqual(result['recall_hits'],0);self.assertEqual(result['relevant_candidates'],0)
 def test_correct_usage_and_separators(self):
  for sep in (':','/'):
   result=measure(*self.sample('right',sep))['groups']['recommendation_requests']
   self.assertEqual(result['recall'],1);self.assertEqual(result['candidate_precision'],1)
 def test_lookup_not_in_recommendation_denominator(self):
  values=self.sample('right');values[0]['cases'][0]['expected_action']='lookup'
  result=measure(*values)['groups']
  self.assertEqual(result['all_usage_labeled']['queries'],1)
  self.assertEqual(result['recommendation_requests']['queries'],0)
 def test_no_candidates_not_perfect_precision(self):
  values=self.sample();values[1]['results'][0]['retrieval']['results']=[]
  result=measure(*values)['groups']['recommendation_requests']
  self.assertEqual(result['recall'],0);self.assertIsNone(result['candidate_precision'])
 def test_invalid_label_rejected(self):
  values=self.sample();values[0]['cases'][0]['acceptable_usage_ids']=['entry-only']
  with self.assertRaises(ValueError):measure(*values)
