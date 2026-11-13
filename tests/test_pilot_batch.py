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
  return [{'slug':f'fixture-{i}','title':f'테스트{i}','aliases':[f'Alias{i}'],'reviewed':True,'scope_type':'korean_origin','scope_basis':'시험용 국내 분류','evidence':[{'url':'https://example.org/a'},{'url':'https://example.org/b'}],'markdown':f'# 테스트{i}\n\n## 뜻풀이\n시험 자료\n\n## 유래와 확산\n실제 밈이 아닌 테스트 자료'} for i in range(10)]
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

 def test_structure_failure_leaves_worktree(self):
  rows=self.data();rows[0]['markdown']+='\n[없는글](missing.md)';self.put(rows)
  with self.assertRaises(ValueError):p.apply(self.r,self.input,'fixture')
  self.assertFalse((self.r/'memes/fixture-0.md').exists())

 def test_foreign_popularity_rejected(self):
  rows=self.data();rows[0]['scope_type']='foreign_popular';self.put(rows)
  with self.assertRaisesRegex(ValueError,'scope review'):p.apply(self.r,self.input,'fixture')
  self.assertFalse((self.r/'memes/fixture-0.md').exists())

 def test_missing_scope_basis_rejected(self):
  rows=self.data();rows[0]['scope_basis']='';self.put(rows)
  with self.assertRaisesRegex(ValueError,'scope review'):p.apply(self.r,self.input,'fixture')

 def test_legacy_yaml_alias_collision(self):
  rows=self.data();rows[0]['aliases']=['Criss Cross'];self.put(rows)
  with self.assertRaisesRegex(ValueError,'alias collision'):p.apply(self.r,self.input,'fixture')
  self.assertFalse((self.r/'memes/fixture-0.md').exists())

 def test_small_final_batch(self):
  self.put(self.data()[:4]);self.assertEqual(p.apply(self.r,self.input,'fixture')['added'],4)
  self.assertEqual(p.apply(self.r,self.input,'fixture')['added'],0)
 def test_empty_batch_rejected(self):
  self.put([])
  with self.assertRaisesRegex(ValueError,'1 to 10'):p.apply(self.r,self.input,'fixture')
 def test_oversized_batch_rejected(self):
  self.put(self.data()+self.data()[:1])
  with self.assertRaisesRegex(ValueError,'1 to 10'):p.apply(self.r,self.input,'fixture')

 def test_derived_index_updated_in_staging(self):
  rows=self.data()[:1];rows[0]['tags']=['게임'];self.put(rows);p.apply(self.r,self.input,'fixture')
  index=json.loads((self.r/'data/search-index.json').read_text())
  self.assertTrue(any(x['id']=='fixture-0' and x['tags']==['게임'] for x in index))
  self.assertIn('[테스트0]',(self.r/'collections/topics.md').read_text())

 def test_retired_slug_cannot_return(self):
  rows=self.data()[:1];rows[0]['slug']='ppibappi';self.put(rows)
  with self.assertRaisesRegex(ValueError,'existing ID'):p.apply(self.r,self.input,'fixture')
 def test_retired_title_cannot_return(self):
  rows=self.data()[:1];rows[0]['title']='삐바삐';rows[0]['markdown']=rows[0]['markdown'].replace('테스트0','삐바삐');self.put(rows)
  with self.assertRaisesRegex(ValueError,'alias collision'):p.apply(self.r,self.input,'fixture')
 def test_superseded_replay_checks_original(self):
  self.put(self.data()[:1]);p.apply(self.r,self.input,'fixture')
  lp=self.r/'data/pilot-state.json';ledger=json.loads(lp.read_text());entry=ledger['entries']['fixture-0'];entry['superseded_by']='ppi';entry['canonical_body_hash']=p.digest((self.r/'memes/ppi.md').read_text());lp.write_text(json.dumps(ledger));(self.r/'memes/fixture-0.md').unlink()
  self.assertEqual(p.apply(self.r,self.input,'fixture')['added'],0)
  q=self.r/'memes/ppi.md';q.write_text(q.read_text()+'수정')
  with self.assertRaisesRegex(ValueError,'refuse overwrite'):p.apply(self.r,self.input,'fixture')
