import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from build_index import build
class IndexTests(unittest.TestCase):
 def test_deterministic(self):self.assertEqual(build(ROOT),build(ROOT))
 def test_complete(self):self.assertEqual(len(build(ROOT)),len(list((ROOT/'memes').glob('*.md')))-1)
 def test_summary_path(self):
  for r in build(ROOT):self.assertTrue(r['summary']);self.assertTrue((ROOT/r['path']).exists())
