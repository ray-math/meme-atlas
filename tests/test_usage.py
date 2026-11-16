import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from usage_profiles import validate, blob_sha, load_profiles, load_vocabulary, FACETS
from build_usage_index import render
from search_usage import search

def vocabulary():
    labels = {'emotions':['놀람','짜증','중립'], 'intents':['감탄','조롱','자조'],
              'situations':['뜻밖의사실','실패'], 'targets':['자기','상대','상황'],
              'registers':['친근한대화','온라인댓글'], 'risk_flags':['모욕']}
    return {'schema_version':1,'facets':{f:[{'label':s,'aliases':['놀라움'] if s=='놀람' else []}
                                           for s in values] for f,values in labels.items()}}

def usage(uid='reaction', **changes):
    value = {'id':uid,'emotions':['놀람'],'intents':['감탄'],'situations':['뜻밖의사실'],
             'targets':['상황'],'registers':['친근한대화'],'risk_flags':[],
             'safety':'standard','context':'뜻밖의 사실을 확인한 반응',
             'avoid_when':['진지한 위로가 필요한 경우'],'example':{'text':'이게 진짜라니!','kind':'editorial'},
             'review_note':'테스트 전용 편집 예시'}
    value.update(changes)
    return value

def index():
    return {'schema_version':1,'vocabulary_version':1,'coverage':{'dictionary_entries':2,'annotated_entries':1,
             'reviewed_entries':1,'unannotated_entries':1},
            'entries':[{'id':'test','title':'테스트','aliases':['Test'],'tags':['방송'],'path':'memes/test.md',
                        'review_status':'reviewed','source_sha':'a'*40,'usages':[usage(),
                        usage('mockery',emotions=['짜증'],intents=['조롱'],targets=['상대'],
                              safety='caution',risk_flags=['모욕'])]}]}

class UsageSearchTests(unittest.TestCase):
    def test_same_usage_not_cross_product(self):
        self.assertEqual(search(index(),vocabulary(),emotions=['놀람'],intents=['조롱'],mode='lookup')['status'],'no_match')
    def test_same_facet_or_different_facet_and(self):
        r=search(index(),vocabulary(),emotions=['놀람','짜증'],intents=['감탄'])
        self.assertEqual([h['usage_id'] for h in r['results']],['reaction'])
    def test_synonym_normalization(self):
        self.assertEqual(search(index(),vocabulary(),emotions=['놀라움'])['results'][0]['usage_id'],'reaction')
    def test_default_recommendation_excludes_caution(self):
        self.assertEqual(search(index(),vocabulary(),intents=['조롱'])['results'],[])
        self.assertEqual(search(index(),vocabulary(),intents=['조롱'],mode='lookup')['results'][0]['usage']['safety'],'caution')
    def test_avoid_is_lookup_only(self):
        data=index();data['entries'][0]['usages'][0]['safety']='avoid'
        self.assertEqual(search(data,vocabulary(),intents=['감탄'])['results'],[])
        self.assertTrue(search(data,vocabulary(),intents=['감탄'],mode='lookup')['results'])
    def test_risk_exclusion(self):
        self.assertEqual(search(index(),vocabulary(),intents=['조롱'],mode='lookup',exclude_risks=['모욕'])['results'],[])
    def test_negative_conditions_not_positive_matches(self):
        self.assertEqual(search(index(),vocabulary(),'위로')['results'],[])
    def test_unknown_filter_abstains(self):
        self.assertEqual(search(index(),vocabulary(),emotions=['미등록감정'])['status'],'unsupported_filter')
    def test_no_query_abstains(self):
        self.assertEqual(search(index(),vocabulary())['status'],'insufficient_query')
    def test_no_match_does_not_fabricate(self):
        self.assertEqual(search(index(),vocabulary(),'찾을수없는단어')['status'],'no_match')
    def test_draft_not_published(self):
        data=index();data['entries'][0]['review_status']='draft'
        self.assertEqual(search(data,vocabulary(),'테스트',mode='lookup')['results'],[])
    def test_missing_emotion_not_neutral(self):
        data=index();data['entries'][0]['usages'][0]['emotions']=[]
        self.assertEqual(search(data,vocabulary(),emotions=['중립'])['results'],[])
    def test_output_provenance_context_and_example(self):
        hit=search(index(),vocabulary(),'ＴＥＳＴ')['results'][0]
        self.assertEqual(hit['source_sha'],'a'*40)
        self.assertTrue(hit['requires_context_check'])
        self.assertEqual(hit['usage']['example']['kind'],'editorial')
        self.assertTrue(hit['usage']['avoid_when'])
    def test_read_only_and_stable(self):
        data=index();before=copy.deepcopy(data)
        first=search(data,vocabulary(),'테스트',mode='lookup')
        self.assertEqual(first,search(data,vocabulary(),'테스트',mode='lookup'))
        self.assertEqual(before,data)
    def test_invalid_arguments(self):
        for limit in [0,101,True]:
            with self.assertRaises(ValueError):search(index(),vocabulary(),limit=limit)
        with self.assertRaises(ValueError):search(index(),vocabulary(),mode='automatic')

class UsageValidationTests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name);(self.root/'memes').mkdir()
        self.path=self.root/'memes/test.md';self.path.write_text('# 테스트\n')
        self.data={'schema_version':1,'profiles':[{'entry_id':'test','source_sha':blob_sha(self.path),
                   'review_status':'reviewed','review_note':'테스트 편집 검토','usages':[usage()]}]}
    def check(self,data):
        return validate(data,vocabulary(),self.root)
    def test_valid_no_mutation(self):
        before=copy.deepcopy(self.data);self.check(self.data);self.assertEqual(self.data,before)
    def test_stale_annotation_requires_review(self):
        self.path.write_text('# 변경\n')
        with self.assertRaisesRegex(ValueError,'source changed'):self.check(self.data)
    def test_unknown_entry_rejected(self):
        self.data['profiles'][0]['entry_id']='missing'
        with self.assertRaises(ValueError):self.check(self.data)
    def test_duplicate_usage_rejected(self):
        self.data['profiles'][0]['usages'].append(usage())
        with self.assertRaises(ValueError):self.check(self.data)
    def test_duplicate_profile_rejected(self):
        self.data['profiles'].append(copy.deepcopy(self.data['profiles'][0]))
        with self.assertRaises(ValueError):self.check(self.data)
    def test_unknown_fields_rejected(self):
        self.data['profiles'][0]['usages'][0]['confidence']=0.99
        with self.assertRaises(ValueError):self.check(self.data)
    def test_unknown_tags_rejected(self):
        self.data['profiles'][0]['usages'][0]['emotions']=['추측한감정']
        with self.assertRaises(ValueError):self.check(self.data)
    def test_editorial_example_must_be_labeled(self):
        self.data['profiles'][0]['usages'][0]['example']['kind']='observed'
        with self.assertRaises(ValueError):self.check(self.data)
    def test_empty_emotion_allowed_without_inference(self):
        self.data['profiles'][0]['usages'][0]['emotions']=[]
        self.check(self.data)
        self.assertEqual(self.data['profiles'][0]['usages'][0]['emotions'],[])
    def test_reviewed_needs_usage(self):
        self.data['profiles'][0]['usages']=[]
        with self.assertRaises(ValueError):self.check(self.data)
        self.data['profiles'][0]['review_status']='draft';self.check(self.data)
    def test_current_profiles(self):
        load_profiles(ROOT)
    def test_generated_usage_index_current(self):
        self.assertEqual((ROOT/'data/usage-index.json').read_text(),render(ROOT))

    def test_schema_and_runtime_fields_agree(self):
        from usage_profiles import PROFILE_KEYS, USAGE_KEYS
        schema=json.loads((ROOT/'schemas/usage-profiles.schema.json').read_text())
        self.assertEqual(set(schema['$defs']['profile']['required']),PROFILE_KEYS)
        self.assertEqual(set(schema['$defs']['usage']['required']),USAGE_KEYS)

    def test_pilot_retrieval_regressions(self):
        from evaluate_usage import evaluate
        report=evaluate(ROOT)
        self.assertEqual(report['passed'],report['total'],
                         [r for r in report['results'] if not r['passed']])
