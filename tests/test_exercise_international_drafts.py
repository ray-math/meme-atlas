import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class ExerciseInternationalDraftTests(unittest.TestCase):
    IDS={'hellchang','jumo-cheer'}
    def test_two_source_bound_reviewed_profiles_keep_unknown_and_caution(self):
        data=load_profiles(ROOT)['profiles']
        selected=[p for p in data if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in selected},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in selected),2)
        for p in selected:
            self.assertEqual(p['review_status'],'reviewed')
            self.assertEqual(p['source_sha'],blob_sha(ROOT/'memes'/f"{p['entry_id']}.md"))
            u=p['usages'][0]
            self.assertEqual(u['emotion_status'],'unknown')
            self.assertEqual(u['emotions'],[])
            self.assertEqual(u['safety'],'caution')
            expected={'situations':['운동중심생활'],'targets':['자기']} if p['entry_id']=='hellchang' else {'situations':['한국관련국제성과'],'targets':['상황']}
            self.assertEqual(u['retrieval_requirements'],expected)
    def test_drafts_excluded_in_title_and_explicit_filter_search(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        for e in index['entries']:
            if e['id'] in self.IDS:e['review_status']='draft'  # hypothetical copies
        for e in index['entries']:
            if e['id'] not in self.IDS:continue
            for mode in ('lookup','recommend'):
                for filters in ({'query':e['title']},e['usages'][0]['retrieval_requirements']):
                    self.assertFalse(any(h['entry_id'] in self.IDS for h in search(index,vocab,mode=mode,**filters)['results']))
