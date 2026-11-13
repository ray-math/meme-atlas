import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from frontmatter import read,render
class MetadataTests(unittest.TestCase):
 def test_roundtrip(self):self.assertEqual(read(render(['게임','방송'],['별칭'])+'# 제목'),{'tags':['게임','방송'],'aliases':['별칭']})
 def test_no_alias_field_without_verified_alias(self):self.assertNotIn('aliases:',render([],[]))
 def test_block_yaml(self):self.assertEqual(read('---\ntags:\n  - 방송\n  - 음악\n---\n')['tags'],['방송','음악'])
 def test_situation_rejected(self):
  with self.assertRaises(ValueError):render(['당황'],[])
 def test_duplicates_rejected(self):
  with self.assertRaises(ValueError):render(['영화','영화'],[])
 def test_invalid_type_rejected(self):
  with self.assertRaises(ValueError):render('게임',[])
 def test_legacy_no_frontmatter(self):self.assertEqual(read('# 제목'),{})
