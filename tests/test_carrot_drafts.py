import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search
from get_entry import get_entry

class CarrotDraftTests(unittest.TestCase):
    IDS={'carrot-of-course','shake-a-carrot'}
    def test_source_bound_profiles_have_individual_review_status(self):
        profiles=load_profiles(ROOT)['profiles']
        selected=[p for p in profiles if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in selected},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in selected),2)
        self.assertEqual(sum(p['review_status']=='reviewed' for p in profiles),60)
        for profile in selected:
            expected='reviewed'
            self.assertEqual(profile['review_status'],expected)
            self.assertEqual(profile['source_sha'],blob_sha(ROOT/'memes'/f"{profile['entry_id']}.md"))
            self.assertEqual(get_entry(ROOT,profile['entry_id'],include_usage=True)['usage_annotation_status'],expected)
            for usage in profile['usages']:
                self.assertEqual(usage['emotion_status'],'unknown')
                self.assertEqual(usage['emotions'],[])
        agreement=next(p for p in selected if p['entry_id']=='carrot-of-course')['usages'][0]
        request=next(p for p in selected if p['entry_id']=='shake-a-carrot')['usages'][0]
        self.assertEqual(agreement['intents'],['동조']);self.assertEqual(agreement['targets'],['상황'])
        self.assertEqual(request['intents'],['안부확인']);self.assertEqual(request['targets'],['상대'])
        self.assertEqual(request['situations'],[])

    def test_drafts_never_enter_search_modes(self):
        data=build_usage_index(ROOT);vocabulary=load_vocabulary(ROOT)
        for entry in data['entries']:
            if entry['id'] in self.IDS:entry['review_status']='draft'  # hypothetical copies
        for entry in data['entries']:
            if entry['id'] not in self.IDS:continue
            usage=entry['usages'][0]
            for mode in ['lookup','recommend']:
                for filters in [{'query':entry['title']},{'intents':usage['intents'],'targets':usage['targets']}]:
                    result=search(data,vocabulary,mode=mode,**filters)
                    self.assertFalse(any(h['entry_id'] in self.IDS for h in result['results']))

    def test_reviewed_agreement_is_not_check_in_or_self_comfort(self):
        data=build_usage_index(ROOT);vocabulary=load_vocabulary(ROOT)
        key=('carrot-of-course','playful-agreement')
        def keys(result):return {(h['entry_id'],h['usage_id']) for h in result['results']}
        for mode in ['lookup','recommend']:
            self.assertIn(key,keys(search(data,vocabulary,mode=mode,intents=['동조'],targets=['상황'])))
        for filters in [{'intents':['안부확인']},{'intents':['위로요청']},{'intents':['동조'],'targets':['자기']}]:
            self.assertNotIn(key,keys(search(data,vocabulary,mode='lookup',**filters)))
