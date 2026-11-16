import sys
import tempfile
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from build_navigation import write, check, START

class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root/'memes').mkdir()
        (self.root/'months').mkdir()
        self.a = '# 가\n\n## 뜻풀이\n설명\n\n## 유래와 확산\n역사\n\n- [나](b.md) · 비슷한 표현\n\n[1월](../months/2026-01.md)\n'
        self.b = '# 나\n\n## 뜻풀이\n설명\n\n## 유래와 확산\n역사\n'
        (self.root/'memes/a.md').write_text(self.a)
        (self.root/'memes/b.md').write_text(self.b)

    def test_repository_navigation_current(self):
        self.assertEqual(check(ROOT), [])

    def test_reverse_link_and_idempotence(self):
        write(self.root)
        self.assertIn('- [가](a.md)', (self.root/'memes/b.md').read_text())
        self.assertEqual((self.root/'memes/a.md').read_text(), self.a)
        self.assertEqual(check(self.root), [])
        self.assertEqual(write(self.root), [])

    def test_remove_relation_removes_generated_reverse(self):
        write(self.root)
        (self.root/'memes/a.md').write_text(self.a.replace('- [나](b.md) · 비슷한 표현\n', ''))
        write(self.root)
        self.assertNotIn(START, (self.root/'memes/b.md').read_text())
        self.assertEqual((self.root/'memes/b.md').read_text(), self.b)

    def test_manual_reverse_not_duplicated(self):
        (self.root/'memes/b.md').write_text(self.b + '\n- [가](a.md)\n')
        write(self.root)
        self.assertNotIn(START, (self.root/'memes/b.md').read_text())

    def test_month_derived_from_article(self):
        write(self.root)
        self.assertIn('- [가](../memes/a.md)', (self.root/'months/2026-01.md').read_text())
        self.assertIn('[1월](2026-01.md)', (self.root/'months/README.md').read_text())
        self.assertIn('[나](b.md)', (self.root/'memes/README.md').read_text())

    def test_missing_marker_refused(self):
        (self.root/'memes/b.md').write_text(self.b + START)
        with self.assertRaises(ValueError):
            write(self.root)

if __name__ == '__main__':
    unittest.main()
