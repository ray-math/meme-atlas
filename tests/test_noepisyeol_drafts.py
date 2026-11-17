import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class NoepisyeolDraftTests(unittest.TestCase):
    def test_source_bound_two_distinct_functions_are_reviewed(self):
        profiles=load_profiles(ROOT)['profiles']
        p=next(p for p in profiles if p['entry_id']=='noepisyeol')
        self.assertEqual(p['review_status'],'reviewed')
        self.assertEqual(p['source_sha'],blob_sha(ROOT/'memes/noepisyeol.md'))
        uses={u['id']:u for u in p['usages']}
        self.assertEqual(set(uses),{'disclose-personal-guess','criticize-unsupported-claim'})
        for u in uses.values():
            self.assertEqual(u['emotion_status'],'unknown');self.assertEqual(u['emotions'],[])
            self.assertEqual(u['targets'],['상황']);self.assertEqual(u['safety'],'caution')
        self.assertEqual(uses['disclose-personal-guess']['intents'],['추측고지'])
        self.assertEqual(uses['criticize-unsupported-claim']['intents'],['비판'])
    def test_draft_is_excluded_even_in_explicit_queries(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        e=next(e for e in index['entries'] if e['id']=='noepisyeol')
        e['review_status']='draft'  # hypothetical unreviewed copy
        for mode in ('lookup','recommend'):
            for filters in [{'query':e['title']}]+[u['retrieval_requirements'] for u in e['usages']]:
                self.assertFalse(any(h['entry_id']==e['id'] for h in search(index,vocab,mode=mode,**filters)['results']))
