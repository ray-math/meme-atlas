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

    def test_cli_exit_codes_cover_drift_and_bad_candidate(self):
        import subprocess
        command=[sys.executable,str(ROOT/'scripts/evaluate_draft_readiness.py')]
        for args,expected in [
            (['--candidate','goat','--fail-on-drift'],1),
            (['--candidate','ubd','--fail-on-drift'],0),
            (['--candidate','missing-profile','--fail-on-drift'],2),
        ]:
            result=subprocess.run(command+args,capture_output=True,text=True)
            self.assertEqual(result.returncode,expected,result.stderr)
            self.assertNotIn('Traceback',result.stderr)
