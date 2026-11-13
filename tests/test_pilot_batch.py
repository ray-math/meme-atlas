import importlib.util,json,shutil,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import pilot_batch as p
class PilotTests(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(); self.addCleanup(self.t.cleanup); self.r=Path(self.t.name)/'repo';shutil.copytree(ROOT,self.r)
  self.input=Path(self.t.name)/'batch.json'
 def data(self):
  return [{'slug':f'fixture-{i}','title':f'테스트{i}','aliases':[f'Alias{i}'],'reviewed':True,'evidence':[{'url':'https://example.org/a'},{'url':'https://example.org/b'}],'markdown':f'# 테스트{i}\n\n## 뜻풀이\n시험 자료\n\n## 유래와 확산\n실제 밈이 아닌 테스트 자료'} for i in range(10)]
 def put(self,rows): self.input.write_text(json.dumps(rows))
 def test_replay(self):
  self.put(self.data());a=p.apply(self.r,self.input,'fixture');b=p.apply(self.r,self.input,'fixture');self.assertEqual(a['added'],10);self.assertEqual(b['added'],0)
 def test_duplicate_alias(self):
  rows=self.data();rows[1]['aliases']=['ＡＬＩＡＳ０'];self.put(rows)
  with self.assertRaisesRegex(ValueError,'alias collision'):p.apply(self.r,self.input,'fixture')
  self.assertFalse((self.r/'memes/fixture-0.md').exists())
 def test_unreviewed(self):
  rows=self.data();rows[0]['reviewed']=False;self.put(rows)
  with self.assertRaisesRegex(ValueError,'review gate'):p.apply(self.r,self.input,'fixture')
 def test_missing_evidence(self):
  rows=self.data();rows[0]['evidence']=[];self.put(rows)
  with self.assertRaisesRegex(ValueError,'evidence'):p.apply(self.r,self.input,'fixture')
 def test_replay_changed_input(self):
  rows=self.data();self.put(rows);p.apply(self.r,self.input,'fixture');rows[0]['title']='변경';self.put(rows)
  with self.assertRaisesRegex(ValueError,'replay differs'):p.apply(self.r,self.input,'fixture')
 def test_user_edit_preserved(self):
  self.put(self.data());p.apply(self.r,self.input,'fixture');f=self.r/'memes/fixture-0.md';f.write_text(f.read_text()+'\n사용자 수정')
  with self.assertRaisesRegex(ValueError,'refuse overwrite'):p.apply(self.r,self.input,'fixture')
  self.assertIn('사용자 수정',f.read_text())
