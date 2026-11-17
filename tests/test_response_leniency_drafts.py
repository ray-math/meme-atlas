import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from usage_profiles import load_profiles,load_vocabulary,blob_sha
from build_usage_index import build_usage_index
from search_usage import search

class ResponseLeniencyDraftTests(unittest.TestCase):
    IDS={'are-you-t','criticism-shield'}
    def test_two_source_bound_reviewed_profiles_do_not_diagnose_or_grant_immunity(self):
        profiles=load_profiles(ROOT)['profiles']
        selected=[p for p in profiles if p['entry_id'] in self.IDS]
        self.assertEqual({p['entry_id'] for p in selected},self.IDS)
        self.assertEqual(sum(len(p['usages']) for p in selected),2)
        self.assertEqual(sum(p['review_status']=='reviewed' for p in profiles),54)
        for profile in selected:
            self.assertEqual(profile['review_status'],'reviewed')
            self.assertEqual(profile['source_sha'],blob_sha(ROOT/'memes'/f"{profile['entry_id']}.md"))
            usage=profile['usages'][0]
            self.assertEqual(usage['emotions'],[])
            self.assertEqual(usage['emotion_status'],'unknown')
            self.assertEqual(usage['safety'],'caution')
            if profile['entry_id']=='are-you-t':
                self.assertEqual(usage['intents'],['장난스러운항의'])
                self.assertEqual(usage['situations'],['반응기대불일치'])
                self.assertEqual(usage['targets'],['상대'])
            else:
                self.assertEqual(usage['intents'],['칭찬','관대한평가'])
                self.assertEqual(usage['targets'],['제삼자'])
                self.assertIn('법적면책오인',usage['risk_flags'])

    def test_drafts_do_not_enter_either_mode(self):
        index=build_usage_index(ROOT);vocab=load_vocabulary(ROOT)
        for entry in index['entries']:
            if entry['id'] in self.IDS:entry['review_status']='draft'  # hypothetical unreviewed copies
        for entry in index['entries']:
            if entry['id'] not in self.IDS:continue
            for mode in ['lookup','recommend']:
                for filters in [{'query':entry['title']},{'intents':entry['usages'][0]['intents']}]:
                    result=search(index,vocab,mode=mode,**filters)
                    self.assertFalse(any(h['entry_id'] in self.IDS for h in result['results']))
