import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from evaluate_draft_readiness import evaluate

class DraftReadinessTests(unittest.TestCase):
    def test_published_draft_structural_probes(self):
        result=evaluate(ROOT)
        self.assertEqual(result['total'],10)
        self.assertEqual(result['passed'],10,result['results'])

    def test_selected_reviewed_subset_has_no_candidate_drift(self):
        result=evaluate(ROOT,['ubd','pro-offended','three-lifts-500'])
        self.assertEqual(result['total'],5)
        self.assertEqual(result['passed'],5)
        self.assertEqual(result['staged_public_candidate_drift'],[])

    def test_held_profiles_reproduce_known_contamination(self):
        for profile,case in [('goat','A01'),('pon-eunjeong','A12'),('ohiryeo-joa','A16')]:
            result=evaluate(ROOT,[profile])
            self.assertTrue(any(row['id']==case for row in result['staged_public_candidate_drift']),
                            (profile,result))

    def test_unknown_or_empty_candidates_fail_closed(self):
        for candidates in [[],['missing-profile']]:
            with self.assertRaises(ValueError):
                evaluate(ROOT,candidates)
