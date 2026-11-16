import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from check_context_decisions import validate_decisions
class ContextDecisionTests(unittest.TestCase):
 def sample(self):
  return ({'plans':[{'id':'x','prompt':'서로 장난을 즐긴다'}]},
          {'results':[{'id':'x','retrieval':{'results':[{'entry_id':'a','usage_id':'u',
                       'usage':{'safety':'caution','risk_flags':['관계의존']}}]}}]},
          {'answers':[{'id':'x','action':'recommend','selected_entry_id':'a','selected_usage_id':'u',
                       'context_check':{'assessment':'compatible','evidence_spans':['서로 장난을 즐긴다'],
                                        'checked_risk_flags':['관계의존'],'unresolved_conditions':[]}}]})
 def test_auditable_decision(self):
  self.assertEqual(validate_decisions(*self.sample()),[])
 def test_invented_context_rejected(self):
  values=self.sample();values[2]['answers'][0]['context_check']['evidence_spans']=['없는 조건']
  self.assertTrue(validate_decisions(*values))
 def test_unresolved_context_rejected(self):
  values=self.sample();values[2]['answers'][0]['context_check']['unresolved_conditions']=['관계']
  self.assertTrue(validate_decisions(*values))
 def test_risk_not_checked(self):
  values=self.sample();values[2]['answers'][0]['context_check']['checked_risk_flags']=[]
  self.assertTrue(validate_decisions(*values))
 def test_avoid_cannot_be_promoted(self):
  values=self.sample();values[1]['results'][0]['retrieval']['results'][0]['usage']['safety']='avoid'
  self.assertTrue(validate_decisions(*values))
 def test_unknown_selected_usage(self):
  values=self.sample();values[2]['answers'][0]['selected_usage_id']='other'
  self.assertTrue(validate_decisions(*values))
