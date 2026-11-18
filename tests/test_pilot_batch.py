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
  with self.assertRaisesRegex(ValueError,'at least 1'):p.apply(self.r,self.input,'fixture')
 def test_oversized_batch_rejected(self):
  self.put(self.data())
  with self.assertRaisesRegex(ValueError,'maximum of 5'):p.apply(self.r,self.input,'fixture',max_entries=5)

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

 def test_large_batch(self):
  rows=self.data()
  for i in range(10,25):
   row=dict(rows[0]);row.update(slug=f'fixture-{i}',title=f'테스트{i}',aliases=[f'Alias{i}'],markdown=rows[0]['markdown'].replace('테스트0',f'테스트{i}'));rows.append(row)
  self.put(rows)
  self.assertEqual(p.apply(self.r,self.input,'large')['added'],25)

 def test_duplicate_slug_rejected(self):
  rows=self.data()[:2];rows[1]['slug']=rows[0]['slug'];self.put(rows)
  with self.assertRaisesRegex(ValueError,'duplicate ID'):p.apply(self.r,self.input,'fixture')
  self.assertFalse((self.r/'memes/fixture-0.md').exists())

 def update_data(self):
  row=self.data()[0];self.put([row]);p.apply(self.r,self.input,'fixture')
  row.update(operation='update',expected_body_hash=p.digest((self.r/'memes/fixture-0.md').read_text()))
  row['markdown']=row['markdown'].replace('시험 자료','보완된 시험 자료')
  return row

 def test_update_and_replay(self):
  row=self.update_data();self.put([row])
  result=p.apply(self.r,self.input,'revision')
  self.assertEqual((result['added'],result['updated']),(0,1))
  self.assertIn('보완된 시험 자료',(self.r/'memes/fixture-0.md').read_text())
  self.assertEqual(p.apply(self.r,self.input,'revision')['status'],'unchanged')

 def test_stale_update_preserves_user_edit(self):
  row=self.update_data();f=self.r/'memes/fixture-0.md';f.write_text(f.read_text()+'\n사용자 수정')
  self.put([row])
  with self.assertRaisesRegex(ValueError,'refuse overwrite'):p.apply(self.r,self.input,'revision')
  self.assertIn('사용자 수정',f.read_text())

 def test_update_requires_hash(self):
  row=self.update_data();del row['expected_body_hash'];self.put([row])
  with self.assertRaisesRegex(ValueError,'refuse overwrite'):p.apply(self.r,self.input,'revision')

 def test_update_unknown_id(self):
  row=self.data()[0];row['operation']='update';self.put([row])
  with self.assertRaisesRegex(ValueError,'target does not exist'):p.apply(self.r,self.input,'revision')

 def test_update_rename_rejected(self):
  row=self.update_data();row['title']='다른 표제어';self.put([row])
  with self.assertRaisesRegex(ValueError,'rename requires'):p.apply(self.r,self.input,'revision')

 def test_update_validation_leaves_original(self):
  row=self.update_data();f=self.r/'memes/fixture-0.md';original=f.read_text()
  row['markdown']+='\n[없는글](missing.md)';self.put([row])
  with self.assertRaises(ValueError):p.apply(self.r,self.input,'revision')
  self.assertEqual(f.read_text(),original)

 def test_existing_id_requires_explicit_update(self):
  row=self.update_data();row.pop('operation');self.put([row])
  with self.assertRaisesRegex(ValueError,'existing ID'):p.apply(self.r,self.input,'revision')

 def test_batch_generates_backlinks_and_replays(self):
  rows=self.data()[:2]
  rows[0]['markdown']+='\n\n- [테스트1](fixture-1.md) · 관련 표현\n'
  self.put(rows)
  p.apply(self.r,self.input,'linked')
  self.assertIn('[테스트0](fixture-0.md)',(self.r/'memes/fixture-1.md').read_text())
  self.assertEqual(p.apply(self.r,self.input,'linked')['status'],'unchanged')

 def test_reviewed_korean_usage_accepted_and_recorded(self):
  rows=self.data()[:1];rows[0]['scope_type']='korean_usage';rows[0]['scope_basis']='독립 출처 두 건에서 한국어 사용 사례 확인';self.put(rows)
  self.assertEqual(p.apply(self.r,self.input,'local-use')['added'],1)
  state=json.loads((self.r/'data/pilot-state.json').read_text())
  self.assertEqual(state['entries']['fixture-0']['scope_type'],'korean_usage')
  self.assertEqual(p.apply(self.r,self.input,'local-use')['status'],'unchanged')

 def test_korean_usage_keeps_review_evidence_and_basis_gates(self):
  for field,value,error in [('reviewed',False,'review gate'),('evidence',[],'evidence'),('scope_basis',' ','scope review')]:
   with self.subTest(field=field):
    rows=self.data()[:1];rows[0]['scope_type']='korean_usage';rows[0][field]=value;self.put(rows)
    with self.assertRaisesRegex(ValueError,error):p.apply(self.r,self.input,'unverified-local-use')
    self.assertFalse((self.r/'memes/fixture-0.md').exists())

 def test_related_guide_survives_regeneration_and_replay(self):
  guide=self.r/'docs/family-comparison-related.md'
  self.assertTrue(guide.is_file())
  paths=['memes/eomchina.md','memes/buchinnam-spouse-comparison-shortening.md','docs/family-comparison-related.md']
  before={name:(self.r/name).read_bytes() for name in paths}
  old_entries=json.loads((self.r/'data/pilot-state.json').read_text())['entries']
  link='[가족 비교 호칭 연결](../docs/family-comparison-related.md)'
  for i in range(2):
   self.put([self.data()[i]])
   self.assertEqual(p.apply(self.r,self.input,f'guide-{i}')['added'],1)
   self.assertEqual((self.r/'collections/pilot-30.md').read_text().count(link),1)
   for name,body in before.items(): self.assertEqual((self.r/name).read_bytes(),body)
   current=json.loads((self.r/'data/pilot-state.json').read_text())['entries']
   for slug,entry in old_entries.items(): self.assertEqual(current[slug],entry)
  snapshot={f.relative_to(self.r):f.read_bytes() for f in self.r.rglob('*') if f.is_file()}
  self.assertEqual(p.apply(self.r,self.input,'guide-1')['status'],'unchanged')
  self.assertEqual({f.relative_to(self.r):f.read_bytes() for f in self.r.rglob('*') if f.is_file()},snapshot)

 def test_missing_related_guide_does_not_emit_link(self):
  (self.r/'docs/family-comparison-related.md').unlink()
  entry=self.r/'memes/buchinnam-spouse-comparison-shortening.md'
  entry.write_text(entry.read_text().split('## 관련 밈',1)[0])
  self.put(self.data()[:1])
  self.assertEqual(p.apply(self.r,self.input,'without-guide')['added'],1)
  self.assertNotIn('family-comparison-related.md',(self.r/'collections/pilot-30.md').read_text())
