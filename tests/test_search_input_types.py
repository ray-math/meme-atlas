"""API type boundaries must not interpret object keys as affirmative filters."""
import copy
import unittest
from test_usage import index, vocabulary
from search_usage import search

class SearchInputTypeTests(unittest.TestCase):
    def test_filter_containers_reject_false_mapping_and_scalar_shapes(self):
        labels={'emotions':'놀람','intents':'감탄','situations':'뜻밖의사실',
                'targets':'상황','registers':'친근한대화','exclude_risks':'모욕'}
        for facet,label in labels.items():
            for value in ({label:False},{label:True},label,None,False,1,{label},[None],[False],[1],[{}]):
                with self.subTest(facet=facet,value=value),self.assertRaises(ValueError):
                    search(index(),vocabulary(),query='테스트',**{facet:value})
    def test_query_must_be_text(self):
        for query in (None,False,1,[],{}):
            with self.subTest(query=query),self.assertRaises(ValueError):
                search(index(),vocabulary(),query=query,intents=['감탄'])
    def test_all_version_numbers_are_exact_integers(self):
        for field in ('schema_version','vocabulary_version'):
            for value in (True,1.0,'1',None,2):
                data=index();data[field]=value
                with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                    search(data,vocabulary(),'테스트')
        for value in (True,1.0,'1',None,2):
            vocab=vocabulary();vocab['schema_version']=value
            with self.subTest(vocabulary_version=value),self.assertRaises(ValueError):
                search(index(),vocab,'테스트')
    def test_supported_lists_tuples_and_defaults_preserve_results(self):
        default=search(index(),vocabulary(),'테스트')
        self.assertTrue(default['results'])
        lists=search(index(),vocabulary(),intents=['감탄'],targets=['상황'])
        tuples=search(index(),vocabulary(),intents=('감탄',),targets=('상황',))
        self.assertEqual(lists,tuples)
        self.assertEqual(search(index(),vocabulary(),intents=['없는라벨'])['status'],'unsupported_filter')
    def test_explanation_switch_is_not_truthy_coercion(self):
        for value in (1,0,1.0,None,[],{}):
            with self.subTest(value=value),self.assertRaises(ValueError):
                search(index(),vocabulary(),'테스트',explain_requirements=value)
