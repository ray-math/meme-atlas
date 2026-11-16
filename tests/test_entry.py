import sys
import unittest
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from get_entry import get_entry, ROOT
from check_generated import check

class EntryTests(unittest.TestCase):
    def test_all_entries(self):
        paths = list((ROOT/'memes').glob('*.md'))
        for p in paths:
            if p.stem != 'README':
                value = get_entry(ROOT,p.stem)
                self.assertTrue(value['sections']['definition'])
                self.assertTrue(value['sections']['origin'])
    def test_section(self):
        v=get_entry(ROOT,'wonyoung-thinking','definition')
        self.assertEqual(list(v['sections']),['definition'])
        self.assertIn('럭키비키',v['aliases'])
    def test_related_not_alias(self):
        v=get_entry(ROOT,'wonyoung-thinking','related')
        self.assertIn('오히려 좋아',v['sections']['related'])
        self.assertNotIn('오히려 좋아',v['aliases'])
    def test_traversal(self):
        for x in ['../README','/etc/passwd','README','a/b','a.md']:
            with self.assertRaises(ValueError):get_entry(ROOT,x)
    def test_missing(self):
        with self.assertRaises(FileNotFoundError):get_entry(ROOT,'does-not-exist')
    def test_invalid_section(self):
        with self.assertRaises(ValueError):get_entry(ROOT,'wonyoung-thinking','all')
    def test_generated_stale(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for name in ['memes','data','collections']:
                shutil.copytree(ROOT/name,root/name)
            (root/'data/search-index.json').write_text('[]')
            self.assertIn('data/search-index.json',check(root))
    def test_generated_current(self):
        self.assertEqual(check(ROOT),[])

if __name__=='__main__':unittest.main()
