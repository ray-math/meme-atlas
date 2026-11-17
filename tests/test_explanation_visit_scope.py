import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_explanation_visit_scope import evaluate

class ExplanationVisitScopeTests(unittest.TestCase):
    def test_semantic_filters_do_not_authorize_formal_or_urgent_use(self):
        trace=evaluate(ROOT)
        self.assertEqual(trace['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in trace['results']}
        for case,entry in [('X-explain','help-speedwagon'),('X-visit','internet-pilgrimage')]:
            self.assertEqual([h['entry_id'] for h in rows[case]['retrieval']['results']],[entry])
            self.assertEqual(rows[case]['retrieval']['mode'],'lookup')
        for case in ('X-formal','X-urgent','X-harass','X-generic','A26'):
            self.assertEqual(rows[case]['retrieval']['status'],'not_searched')
        self.assertEqual(rows['X-generic']['action'],'clarify')
        self.assertEqual(rows['A26']['action'],'clarify')
        self.assertTrue(any(h['entry_id']=='you-insulted-me' for h in rows['A14']['retrieval']['results']))
        self.assertFalse(any(h['entry_id'] in {'help-speedwagon','internet-pilgrimage'} for h in rows['A14']['retrieval']['results']))
