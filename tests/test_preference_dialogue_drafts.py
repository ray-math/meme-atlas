import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search
class PreferenceDialogueDraftTests(unittest.TestCase):
    IDS={'chwijon','dapjeongneo'}
    def test_two_source_bound_profiles_do_not_infer_private_motives(self):
        profiles=[p for p in load_profiles(ROOT)['profiles'] if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in profiles},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in profiles),2)
        for p in profiles:
            self.assertEqual(p['review_status'],'reviewed')
            self.assertEqual(p['source_sha'],blob_sha(ROOT/'memes'/f"{p['entry_id']}.md"))
            u=p['usages'][0]
            self.assertEqual(u['emotion_status'],'unknown');self.assertEqual(u['emotions'],[])
            self.assertEqual(u['safety'],'caution');self.assertEqual(u['targets'],['상황'])
            if p['entry_id']=='chwijon':
                self.assertEqual(u['intents'],['취향존중요청']);self.assertEqual(u['situations'],[])
            else:
                self.assertEqual(u['intents'],['비판']);self.assertEqual(u['situations'],['특정답변만수용'])
    def test_lookup_available_but_default_recommend_excludes_caution(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        for e in index['entries']:
            if e['id'] not in self.IDS:continue
            filters=e['usages'][0]['retrieval_requirements']
            self.assertTrue(any(h['entry_id']==e['id'] for h in search(index,vocab,mode='lookup',**filters)['results']))
            self.assertFalse(any(h['entry_id']==e['id'] for h in search(index,vocab,mode='recommend',**filters)['results']))
