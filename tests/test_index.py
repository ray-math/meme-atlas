import sys,unittest,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_index import build,write_topics
class IndexTests(unittest.TestCase):
 def test_deterministic(self):self.assertEqual(build(ROOT),build(ROOT))
 def test_complete(self):self.assertEqual(len(build(ROOT)),len(list((ROOT/'memes').glob('*.md')))-1)
 def test_summary_path(self):
  for r in build(ROOT):self.assertTrue(r['summary']);self.assertTrue((ROOT/r['path']).exists())

 def test_definition_in_numbered_heading(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);(r/'memes').mkdir();(r/'memes/test.md').write_text('# 표제어\n\n## 뜻풀이\n### 1. 정의가 소제목인 문서\n- 사용 장면\n\n## 유래와 확산\n기원')
   self.assertEqual(build(r)[0]['summary'],'정의가 소제목인 문서')

 def test_topic_index_groups_and_unclassified(self):
  with tempfile.TemporaryDirectory() as d:
   rows=[{'title':'A','path':'memes/a.md','tags':['게임','방송']},{'title':'B','path':'memes/b.md','tags':[]}]
   write_topics(d,rows);text=(Path(d)/'collections/topics.md').read_text()
   self.assertIn('## 게임',text);self.assertIn('## 방송',text);self.assertIn('## 미분류',text)
   self.assertEqual(text.count('[A]'),2);self.assertEqual(text.count('[B]'),1)

 def test_retired_derivative_search_without_false_alias(self):
  from search_dictionary import search
  rows=build(ROOT);hit=search(rows,'삐바삐',limit=1)[0]
  self.assertEqual(hit['id'],'ppi')
  self.assertNotIn('삐바삐',hit.get('aliases',[]))
  self.assertFalse(any(r['id']=='ppibappi' for r in rows))
