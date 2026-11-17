import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from compare_evaluation_expansion import compare,load_additions

class ReviewedExpansionTests(unittest.TestCase):
    def setUp(self):
        self.old=[{'id':'case','action':'recommend','filters':{},'prompt':'synthetic',
                   'retrieval':{'status':'matches','coverage':{'n':1},
                                'results':[{'entry_id':'old1','usage_id':'one'},
                                           {'entry_id':'old2','usage_id':'two'}]}}]
        self.hit={'entry_id':'new','usage_id':'one','source_sha':'a'*40,'score':20,'requires_context_check':True}
        self.allow={('test','case','new','one'):{'hit':self.hit,'position':1}}
        self.new=copy.deepcopy(self.old)
        self.new[0]['retrieval']['results'].insert(1,copy.deepcopy(self.hit))

    def test_exact_reviewed_addition_only(self):
        self.assertEqual(compare(self.old,self.new,'test',self.allow)['reviewed_additions'],1)
        new=copy.deepcopy(self.new);new[0]['retrieval']['coverage']={'n':2}
        compare(self.old,new,'test',self.allow)

    def test_unreviewed_changes_fail_closed(self):
        mutations=[
            lambda x:x[0]['retrieval']['results'].pop(0),
            lambda x:x[0]['retrieval']['results'].pop(1),
            lambda x:x[0]['retrieval']['results'].reverse(),
            lambda x:x[0]['retrieval']['results'].append({'entry_id':'extra','usage_id':'one'}),
            lambda x:x[0]['retrieval']['results'].append(copy.deepcopy(self.hit)),
            lambda x:x[0]['retrieval'].update(status='no_match'),
            lambda x:x[0]['retrieval']['results'][1].update(source_sha='b'*40),
            lambda x:x[0].update(prompt='changed'),
            lambda x:x[0]['retrieval']['results'][1].update(score=20.0),
            lambda x:x[0]['retrieval']['results'][1].update(requires_context_check=1),
            lambda x:x.append(copy.deepcopy(x[0])),
            lambda x:x.clear(),
        ]
        for mutate in mutations:
            new=copy.deepcopy(self.new);mutate(new)
            with self.assertRaises(ValueError):compare(self.old,new,'test',self.allow)
        with self.assertRaises(ValueError):compare(self.old,self.new,'unapproved-set',self.allow)

    def test_review_registry_is_specific(self):
        additions=load_additions(ROOT)
        self.assertEqual(set(additions),{
            ('challenge/audit','A08','carrot-of-course','playful-agreement'),
            ('challenge/editorial','E08','carrot-of-course','playful-agreement'),
            ('regression-v3/audit','A08','carrot-of-course','playful-agreement'),
            ('regression-v3/editorial','E08','carrot-of-course','playful-agreement')})
        for value in additions.values():
            self.assertEqual(value['position'],1)
            self.assertEqual(value['hit']['source_sha'],'1488b467718d86edacf37a1c29d2848869b1c62a')

    def test_duplicate_or_invalid_registry_rejected(self):
        original=Path.read_text
        for change in ['duplicate','position','reason','schema-bool','schema-float']:
            def edited(path,*args,**kwargs):
                content=original(path,*args,**kwargs)
                if str(path).endswith('eval/reviewed-expansions.json'):
                    data=json.loads(content)
                    if change=='duplicate':data['additions'].append(copy.deepcopy(data['additions'][0]))
                    elif change=='position':data['additions'][0]['expected_position']=True
                    elif change=='schema-bool':data['schema_version']=True
                    elif change=='schema-float':data['schema_version']=1.0
                    else:data['additions'][0]['reason']=''
                    return json.dumps(data)
                return content
            with patch.object(Path,'read_text',edited):
                with self.assertRaises(ValueError):load_additions(ROOT)
