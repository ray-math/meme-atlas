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
        self.assertEqual(result['plan_errors'],[])

    def test_selected_reviewed_subset_has_no_candidate_drift(self):
        result=evaluate(ROOT,['ubd','pro-offended','three-lifts-500'])
        self.assertEqual(result['total'],5)
        self.assertEqual(result['passed'],5)
        self.assertEqual(result['plan_errors'],[])
        self.assertEqual(result['staged_public_candidate_drift'],[])

    def test_held_profiles_reproduce_known_contamination(self):
        for profile,case,source in [('goat','A01','regression-v3/audit'),('pon-eunjeong','A12','regression-v3/audit'),('ohiryeo-joa','A16','challenge/audit')]:
            result=evaluate(ROOT,[profile])
            self.assertTrue(any(row['id']==case and row['evaluation_set']==source and any(hit.startswith(profile+':') for hit in row['after']) for row in result['staged_public_candidate_drift']),
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
            if expected in (0,1):
                import json
                payload=json.loads(result.stdout)
                self.assertEqual(payload['plan_errors'],[])
                self.assertEqual(bool(payload['staged_public_candidate_drift']),expected==1)

    def test_missing_or_empty_selected_profile_is_not_partial_success(self):
        import copy
        from unittest.mock import patch
        from build_usage_index import build_usage_index
        original=build_usage_index(ROOT)
        for empty in [False,True]:
            data=copy.deepcopy(original)
            if empty:
                next(e for e in data['entries'] if e['id']=='goat')['usages']=[]
            else:
                data['entries']=[e for e in data['entries'] if e['id']!='goat']
            with patch('evaluate_draft_readiness.build_usage_index',return_value=data):
                with self.assertRaisesRegex(ValueError,'missing or without usages'):
                    evaluate(ROOT,['goat','ubd'])

    def test_unknown_contract_rejects_other_emotion_even_without_joy(self):
        import copy
        from unittest.mock import patch
        from build_usage_index import build_usage_index
        data=copy.deepcopy(build_usage_index(ROOT))
        usage=next(e for e in data['entries'] if e['id']=='goat')['usages'][0]
        usage['emotion_status']='annotated';usage['emotions']=['놀람']
        with patch('evaluate_draft_readiness.build_usage_index',return_value=data):
            result=evaluate(ROOT,['goat'])
            self.assertFalse(result['results'][0]['checks']['unknown_emotion_contract'])
            self.assertEqual(result['passed'],0)

    def test_plan_error_is_reported_even_when_before_and_after_are_empty(self):
        from unittest.mock import patch
        from search_usage import search as actual_search
        def search_with_bad_plan(index,vocabulary,query='',**kwargs):
            if not query:
                return {'status':'unsupported_filter','reason':'test invalid plan','results':[]}
            return actual_search(index,vocabulary,query,**kwargs)
        with patch('evaluate_draft_readiness.search',side_effect=search_with_bad_plan):
            result=evaluate(ROOT,['ubd'])
            self.assertTrue(result['plan_errors'])
            self.assertTrue(all(e['status']=='unsupported_filter' for e in result['plan_errors']))
