import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('checker',ROOT/'scripts/check_dictionary.py')
checker=importlib.util.module_from_spec(spec); spec.loader.exec_module(checker)

class DictionaryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for name in ['README.md','CONTRIBUTING.md','memes','months','templates','collections']:
            src=ROOT/name; dst=self.root/name
            if not src.exists(): continue
            shutil.copytree(src,dst) if src.is_dir() else shutil.copy2(src,dst)
    def edit(self,path,old,new):
        p=self.root/path; p.write_text(p.read_text().replace(old,new))
    def test_current(self): self.assertEqual(checker.check(self.root),[])
    def test_broken_link(self):
        self.edit('memes/README.md','click.md','missing.md')
        self.assertTrue(any('broken link' in e for e in checker.check(self.root)))
    def test_wrong_title(self):
        self.edit('memes/README.md','[딸깍]','[Wrong]')
        self.assertTrue(any('title mismatch' in e for e in checker.check(self.root)))
    def test_missing_section(self):
        self.edit('memes/click.md','## 유래와 확산','## Other')
        self.assertTrue(any('missing section' in e for e in checker.check(self.root)))
    def test_orphan(self):
        self.edit('memes/README.md','- [딸깍](click.md)','')
        self.assertTrue(any('index does not cover' in e for e in checker.check(self.root)))
    def test_asymmetric_related(self):
        self.edit('memes/54000.md','[딸깍](click.md)','딸깍')
        self.assertTrue(any('missing related backlink' in e for e in checker.check(self.root)))
    def test_month_prose(self):
        p=self.root/'months/2026-09.md'; p.write_text(p.read_text()+'\nSome duplicate definition.\n')
        self.assertTrue(any('month must contain' in e for e in checker.check(self.root)))
    def test_home_meme(self):
        p=self.root/'README.md'; p.write_text(p.read_text()+'\n[딸깍](memes/click.md)\n')
        self.assertTrue(any('home should link' in e for e in checker.check(self.root)))
    def test_new_month_and_entry(self):
        (self.root/'memes/new.md').write_text('# 새말\n\n## 뜻풀이\n뜻\n\n## 유래와 확산\n맥락\n\n[12월](../months/2026-12.md)\n')
        (self.root/'months/2026-12.md').write_text('# 2026년 12월\n\n- [새말](../memes/new.md)\n')
        for p,line in [('memes/README.md','- [새말](new.md)'),('months/README.md','- [12월](2026-12.md)')]:
            f=self.root/p; f.write_text(f.read_text()+'\n'+line+'\n')
        self.assertEqual(checker.check(self.root),[])

if __name__=='__main__': unittest.main()

