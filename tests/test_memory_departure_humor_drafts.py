import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search
from get_entry import get_entry

class MemoryDepartureHumorReviewedTests(unittest.TestCase):
    IDS={'blanket-kick','goodbye-everyone','laugh-bell'}
    def test_three_individually_reviewed_profiles_four_usages(self):
        data=load_profiles(ROOT)
        profiles=[p for p in data['profiles'] if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in profiles},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in profiles),4)
        for profile in profiles:
            self.assertEqual(profile['review_status'],'reviewed')
            self.assertEqual(profile['source_sha'],blob_sha(ROOT/'memes'/f"{profile['entry_id']}.md"))
            result=get_entry(ROOT,profile['entry_id'],include_usage=True)
            self.assertEqual(result['usage_annotation_status'],'reviewed')
            for usage in profile['usages']:
                self.assertEqual(usage['example']['kind'],'editorial')
                if profile['entry_id']=='blanket-kick':
                    self.assertEqual(usage['emotion_status'],'annotated')
                    self.assertEqual(usage['emotions'],['민망함'])
                else:
                    self.assertEqual(usage['emotion_status'],'unknown')
                    self.assertEqual(usage['emotions'],[])

    def test_unreviewed_copies_cannot_leak_through_exact_lookup_or_context(self):
        data=build_usage_index(ROOT);vocabulary=load_vocabulary(ROOT)
        profiles=[e for e in data['entries'] if e['id'] in self.IDS]
        self.assertEqual({p['id'] for p in profiles},self.IDS)
        for entry in profiles:entry['review_status']='draft'  # copies only
        for entry in profiles:
            for usage in entry['usages']:
                for mode in ['lookup','recommend']:
                    result=search(data,vocabulary,entry['title'],mode=mode,
                                  **usage['retrieval_requirements'])
                    self.assertFalse(any(h['entry_id'] in self.IDS for h in result['results']))
