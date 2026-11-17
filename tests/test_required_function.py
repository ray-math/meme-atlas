import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,validate,REQUIREMENT_FACETS
from build_usage_index import build_usage_index
from search_usage import search
from replay_response_scope import evaluate
from compare_evaluation_expansion import strict_equal

class ResponseRequiredFunctionTests(unittest.TestCase):
    def setUp(self):
        self.index=build_usage_index(ROOT);self.vocab=load_vocabulary(ROOT)
        self.entries={e['id']:e for e in self.index['entries'] if e['id'] in {'are-you-t','criticism-shield'}}
        for entry in self.entries.values():entry['review_status']='reviewed'
    def keys(self,result):return {(h['entry_id'],h['usage_id']) for h in result['results']}

    def test_specific_event_or_function_not_broad_protest_or_praise(self):
        for identity,facet,label,broad in [
            ('are-you-t','situations','반응기대불일치',{'intents':['장난스러운항의']}),
            ('criticism-shield','intents','관대한평가',{'intents':['칭찬']})]:
            entry=self.entries[identity];usage=entry['usages'][0];key=(identity,usage['id'])
            self.assertEqual(usage['retrieval_requirements'],{facet:[label]})
            self.assertNotIn(key,self.keys(search(self.index,self.vocab,mode='lookup',**broad)))
            self.assertIn(key,self.keys(search(self.index,self.vocab,mode='lookup',**{facet:[label]})))
            self.assertNotIn(key,self.keys(search(self.index,self.vocab,mode='recommend',**{facet:[label]})))
            self.assertNotIn(key,self.keys(search(self.index,self.vocab,mode='lookup',**{facet:[label,'칭찬' if facet=='intents' else '가벼운놀림']})))
            result=search(self.index,self.vocab,entry['title'],mode='lookup')
            hit=next(h for h in result['results'] if (h['entry_id'],h['usage_id'])==key)
            self.assertTrue(hit['retrieval_scope']['exact_lookup_only'])
            self.assertNotIn(key,self.keys(search(self.index,self.vocab,entry['title']+' 추천',mode='lookup')))

    def test_requirement_schema_and_invalid_intent_values(self):
        schema=json.loads((ROOT/'schemas/usage-profiles.schema.json').read_text())
        self.assertEqual(set(schema['$defs']['usage']['properties']['retrieval_requirements']['properties']),REQUIREMENT_FACETS)
        profiles=load_profiles(ROOT)
        for invalid in [{'intents':[]},{'intents':['관대한평가','칭찬']},
                        {'intents':['다짐']},{'registers':['친근한대화']},{'intents':[True]}]:
            data=copy.deepcopy(profiles)
            next(p for p in data['profiles'] if p['entry_id']=='criticism-shield')['usages'][0]['retrieval_requirements']=invalid
            with self.assertRaises(ValueError):validate(data,self.vocab,ROOT)

    def test_measured_baseline_is_preserved_and_controlled_gate_removes_drift(self):
        before=evaluate(ROOT,enforce_requirements=False)
        frozen=json.loads((ROOT/'eval/response-scope/baseline-retrieval.json').read_text())
        def behavior(rows):
            rows=copy.deepcopy(rows)
            for row in rows:row['retrieval'].pop('coverage',None)
            return rows
        self.assertTrue(strict_equal(behavior(before['results']),behavior(frozen['results'])))
        self.assertEqual(len(before['current_baseline_candidate_drift']),8)
        after=evaluate(ROOT)
        self.assertEqual(after['current_baseline_candidate_drift'],[])
        rows={r['id']:r for r in after['results']}
        self.assertEqual(self.keys(rows['T-protest']['retrieval']),{('are-you-t','playful-response-protest')})
        self.assertEqual(self.keys(rows['S-leniency']['retrieval']),{('criticism-shield','credit-with-leniency')})
        self.assertNotIn(('are-you-t','playful-response-protest'),self.keys(rows['A14']['retrieval']))
        with self.assertRaises(ValueError):evaluate(ROOT,enforce_requirements='false')

    def test_profile_schema_version_is_strict_integer(self):
        for invalid in (True,False,1.0,'1',None):
            data=copy.deepcopy(load_profiles(ROOT));data['schema_version']=invalid
            with self.assertRaises(ValueError):validate(data,self.vocab,ROOT)
