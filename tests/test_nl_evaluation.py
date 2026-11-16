undefined
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
