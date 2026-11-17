import copy
import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary, load_profiles, validate
from search_usage import search

class ExplicitContextTests(unittest.TestCase):
    IDS={'goat','pon-eunjeong','ohiryeo-joa'}

    def setUp(self):
        self.index=build_usage_index(ROOT)
        self.vocab=load_vocabulary(ROOT)
        self.entries=[e for e in self.index['entries'] if e['id'] in self.IDS]
        self.assertEqual({e['id'] for e in self.entries},self.IDS)
        for entry in self.entries:
            entry['review_status']='reviewed'  # isolated copy, never saves/promotes sources

    def ids(self,result):
        return {(h['entry_id'],h['usage_id']) for h in result['results']}

    def test_context_requirements_are_symmetric(self):
        for entry in self.entries:
            usage=entry['usages'][0];required=usage['retrieval_requirements']
            key=(entry['id'],usage['id'])
            for mode in ['lookup','recommend']:
                filters={'intents':usage['intents'],'mode':mode,'limit':100}
                for incomplete in [{},{'situations':required['situations']},{'targets':required['targets']}]:
                    result=search(self.index,self.vocab,**dict(filters,**incomplete))
                    self.assertNotIn(key,self.ids(result))
                complete=dict(filters,**required)
                result=search(self.index,self.vocab,**complete)
                self.assertEqual(key in self.ids(result),mode=='lookup' or usage['safety']=='standard')
                wrong=dict(complete,targets=['자기'])
                self.assertNotIn(key,self.ids(search(self.index,self.vocab,**wrong)))
                wrong_situation=dict(complete,situations=['불확실한결과'])
                self.assertNotIn(key,self.ids(search(self.index,self.vocab,**wrong_situation)))
                broad_target=dict(complete,targets=required['targets']+['자기'])
                self.assertNotIn(key,self.ids(search(self.index,self.vocab,**broad_target)))
                ambiguous=dict(complete,situations=required['situations']+['불확실한결과'])
                self.assertNotIn(key,self.ids(search(self.index,self.vocab,**ambiguous)))

    def test_exact_lookup_is_explanation_only_not_recommendation(self):
        for entry in self.entries:
            key=(entry['id'],entry['usages'][0]['id'])
            for query in [entry['title'],*entry['aliases']]:
                result=search(self.index,self.vocab,query,mode='lookup')
                self.assertIn(key,self.ids(result))
                hit=next(h for h in result['results'] if (h['entry_id'],h['usage_id'])==key)
                self.assertTrue(hit['retrieval_scope']['exact_lookup_only'])
                self.assertFalse(hit['retrieval_scope']['explicit_filters_match'])
                self.assertTrue(hit['requires_context_check'])
                self.assertNotIn(key,self.ids(search(self.index,self.vocab,query,mode='recommend')))
            self.assertNotIn(key,self.ids(search(self.index,self.vocab,entry['title']+' 추천',mode='lookup')))
            self.assertNotIn(key,self.ids(search(self.index,self.vocab,entry['title'][:2],mode='lookup')))

    def test_exact_lookup_cannot_override_other_gates(self):
        entry=self.entries[0];usage=entry['usages'][0];key=(entry['id'],usage['id'])
        usage['risk_flags']=['사실오인']
        self.assertNotIn(key,self.ids(search(self.index,self.vocab,entry['title'],mode='lookup',exclude_risks=['사실오인'])))
        usage['safety']='avoid'
        self.assertNotIn(key,self.ids(search(self.index,self.vocab,entry['title'],mode='recommend',**usage['retrieval_requirements'])))
        entry['review_status']='draft'
        self.assertNotIn(key,self.ids(search(self.index,self.vocab,entry['title'],mode='lookup')))

    def test_diagnostics_are_explicit_opt_in(self):
        result=search(self.index,self.vocab,'GOAT',explain_requirements=True)
        self.assertEqual(result['reason'],'explicit_context_filters_required')
        self.assertGreater(result['context_requirements_filtered_count'],0)
        self.assertNotIn('context_requirements_filtered_count',search(self.index,self.vocab,'GOAT'))

    def test_invalid_requirements_rejected(self):
        profiles=load_profiles(ROOT)
        for invalid in [{},{'emotions':['기쁨']},{'targets':[]},{'targets':['자기']},
                        {'situations':['성과','스포츠선수평가']},{'situations':['오타']}]:
            data=copy.deepcopy(profiles)
            usage=next(p for p in data['profiles'] if p['entry_id']=='goat')['usages'][0]
            usage['retrieval_requirements']=invalid
            with self.assertRaises(ValueError):
                validate(data,self.vocab,ROOT)

    def test_schema_optional_fields_match_runtime(self):
        from usage_profiles import USAGE_KEYS, OPTIONAL_USAGE_KEYS
        usage=json.loads((ROOT/'schemas/usage-profiles.schema.json').read_text())['$defs']['usage']
        self.assertEqual(set(usage['properties'])-set(usage['required']),OPTIONAL_USAGE_KEYS)
        self.assertEqual(set(usage['required']),USAGE_KEYS)
