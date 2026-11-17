import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search
class DiscretionDraftTests(unittest.TestCase):
    def test_source_bound_request_is_not_praise(self):
        p=next(p for p in load_profiles(ROOT)['profiles'] if p['entry_id']=='aljaltakkalsen')
        self.assertEqual(p['review_status'],'draft')
        self.assertEqual(p['source_sha'],blob_sha(ROOT/'memes/aljaltakkalsen.md'))
        self.assertEqual(len(p['usages']),1)
        u=p['usages'][0]
        self.assertEqual(u['intents'],['재량요청'])
        self.assertEqual(u['emotion_status'],'unknown');self.assertEqual(u['emotions'],[])
        self.assertEqual(u['safety'],'caution')
        self.assertEqual(u['retrieval_requirements'],{'situations':['공유기준내재량'],'targets':['상대']})
    def test_draft_is_not_exposed_by_exact_name_or_filters(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        e=next(e for e in index['entries'] if e['id']=='aljaltakkalsen')
        for mode in ('lookup','recommend'):
            for filters in [{'query':e['title']},e['usages'][0]['retrieval_requirements']]:
                self.assertFalse(any(h['entry_id']==e['id'] for h in search(index,vocab,mode=mode,**filters)['results']))
