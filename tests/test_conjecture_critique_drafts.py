import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class ConjectureCritiqueDraftTests(unittest.TestCase):
    IDS={'king-reasonable-suspicion','naeronambul'}
    def test_two_narrow_drafts_keep_function_separate_from_truth(self):
        data=load_profiles(ROOT)['profiles']
        selected=[p for p in data if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in selected},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in selected),2)
        self.assertEqual(sum(p['review_status']=='reviewed' for p in data),39)
        for profile in selected:
            self.assertEqual(profile['review_status'],'draft')
            self.assertEqual(profile['source_sha'],blob_sha(ROOT/'memes'/f"{profile['entry_id']}.md"))
            usage=profile['usages'][0]
            self.assertEqual(usage['emotions'],[])
            self.assertEqual(usage['emotion_status'],'unknown')
            self.assertEqual(usage['safety'],'caution')
            self.assertEqual(usage['targets'],['상황'])
            self.assertNotIn('비꼼',usage['intents'])
            self.assertNotIn('판단유보',usage['intents'])
            if profile['entry_id']=='king-reasonable-suspicion':
                self.assertEqual(usage['intents'],['추측표현'])
            else:
                self.assertEqual(usage['intents'],['비판'])
                self.assertEqual(usage['situations'],['기준적용차이'])

    def test_drafts_do_not_enter_either_mode(self):
        data=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        for entry in data['entries']:
            if entry['id'] not in self.IDS:continue
            for mode in ['lookup','recommend']:
                for filters in [{'query':entry['title']},{'intents':entry['usages'][0]['intents']}]:
                    result=search(data,vocab,mode=mode,**filters)
                    self.assertFalse(any(h['entry_id'] in self.IDS for h in result['results']))
