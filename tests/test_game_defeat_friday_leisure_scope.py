import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from replay_game_defeat_friday_leisure_scope import evaluate

class GameDefeatFridayLeisureScopeTests(unittest.TestCase):
    def test_public_inputs_are_exactly_source_bound(self):
        trace=evaluate(ROOT)
        self.assertEqual({r['id'] for r in trace['results']},
                         {'G-defeat','G-friday','G-force','G-system','G-offday','G-overwork','A04','E06','A20','A26'})
        # Candidate behavior is observed first, not assumed accurate.

    def test_observed_candidates_and_boundaries(self):
        rows={r['id']:r for r in evaluate(ROOT)['results']}
        for identity, expected in {'G-defeat':['gg'],'G-friday':['fiery-friday'],
                                   'A04':['jung-kkeok-ma'],'E06':['flower-road','haengshow']}.items():
            self.assertEqual([h['entry_id'] for h in rows[identity]['retrieval']['results']],expected)
            self.assertEqual(rows[identity]['retrieval']['mode'],'recommend')
        for identity in ('G-force','G-system','G-offday','G-overwork','A20','A26'):
            self.assertEqual(rows[identity]['retrieval']['status'],'not_searched')
        self.assertEqual(evaluate(ROOT)['current_baseline_candidate_drift'],[])

    def test_frozen_trace_reexecutes_without_type_drift(self):
        import copy
        from compare_evaluation_expansion import strict_equal
        frozen=json.loads((ROOT/'eval/game-defeat-friday-leisure-scope/retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(frozen['results']),behavior(evaluate(ROOT)['results'])))
