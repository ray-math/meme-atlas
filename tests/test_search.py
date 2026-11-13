import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from search_dictionary import search
DATA=[{'id':'a','title':'크리스 크로스','aliases':['Criss Cross'],'tags':['게임'],'summary':'게임 춤'},{'id':'b','title':'다른 표현','tags':['방송'],'summary':'크리스 크로스를 언급한다'}]
class SearchTests(unittest.TestCase):
 def test_alias_case(self):self.assertEqual(search(DATA,'ＣＲＩＳＳ cross')[0]['id'],'a')
 def test_exact_title_first(self):self.assertEqual(search(DATA,'크리스크로스')[0]['id'],'a')
 def test_tag_filter(self):self.assertEqual([x['id'] for x in search(DATA,tags=['방송'])],['b'])
 def test_unknown_no_fabrication(self):self.assertEqual(search(DATA,'없는표현'),[])
 def test_required_all_terms(self):self.assertEqual(search(DATA,'게임 없는표현'),[])
 def test_limit(self):self.assertEqual(len(search(DATA,limit=1)),1)
 def test_invalid_limit(self):
  with self.assertRaises(ValueError):search(DATA,limit=0)
 def test_read_only(self):
  original=repr(DATA);search(DATA,'게임');self.assertEqual(repr(DATA),original)
