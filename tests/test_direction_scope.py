import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from build_usage_index import build_usage_index
from usage_profiles import load_vocabulary
from search_usage import search

class DirectionScopeTests(unittest.TestCase):
    def setUp(self):
        self.data=build_usage_index(ROOT);self.vocab=load_vocabulary(ROOT)
        for entry in self.data['entries']:
            if entry['id'] in {'goat','gabojago'}:
                entry['review_status']='reviewed'

    def selected(self,**kwargs):
        return {(h['entry_id'],h['usage_id']) for h in search(self.data,self.vocab,limit=100,**kwargs)['results']}

    def test_goat_sports_context_does_not_require_recipient_question(self):
        key=('goat','praise-greatest')
        self.assertIn(key,self.selected(situations=['스포츠선수평가']))
        for target in ['상대','제삼자']:
            self.assertIn(key,self.selected(situations=['스포츠선수평가'],targets=[target]))
        for target in ['자기','상황']:
            self.assertNotIn(key,self.selected(situations=['스포츠선수평가'],targets=[target]))
        self.assertNotIn(key,self.selected(intents=['칭찬']))

    def test_gabojago_directions_are_not_cross_combined(self):
        own=('gabojago','encourage-self');other=('gabojago','encourage-challenge')
        self.assertIn(own,self.selected(intents=['격려'],situations=['도전시작'],targets=['자기']))
        self.assertNotIn(other,self.selected(intents=['격려'],situations=['도전시작'],targets=['자기']))
        self.assertIn(other,self.selected(intents=['격려'],situations=['도전시작'],targets=['상대']))
        self.assertNotIn(own,self.selected(intents=['격려'],situations=['도전시작'],targets=['상대']))
        self.assertNotIn(own,self.selected(intents=['다짐'],situations=['도전시작'],targets=['자기']))
        self.assertFalse({own,other}&self.selected(intents=['격려']))
        self.assertFalse({own,other}&self.selected(intents=['격려'],situations=['도전시작']))
