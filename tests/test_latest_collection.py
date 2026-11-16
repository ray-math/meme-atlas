import sys, unittest, json, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from latest_collection import validate, select, write, window, ROOT

class LatestTests(unittest.TestCase):
    def sample(self):
        return {'id':'wonyoung-thinking','observed_date':'2026-01-01',
                'trend_type':'resurgence','scope_type':'korean_origin',
                'review_note':'시험용 데이터이며 최신 유행 인증 아님'}
    def validate(self, rows):
        return validate(rows, as_of='2026-11-13')
    def test_boundaries(self):
        for day in ['2025-11-13','2026-11-13']:
            row=self.sample();row['observed_date']=day;self.validate([row])
    def test_outside_window(self):
        for day in ['2025-11-12','2026-11-14']:
            row=self.sample();row['observed_date']=day
            with self.assertRaises(ValueError):self.validate([row])
    def test_duplicates(self):
        row=self.sample()
        with self.assertRaises(ValueError):self.validate([row,row])
    def test_unknown_entry(self):
        row=self.sample();row['id']='imaginary-new-entry'
        with self.assertRaises(ValueError):self.validate([row])
    def test_limit(self):
        with self.assertRaises(ValueError):self.validate([self.sample()]*201)
    def test_current_selection_snapshot(self):
        data=json.loads((ROOT/'data/latest-selection.json').read_text())
        validate(data['entries'], as_of=data['end'])
        self.assertEqual(window(data['end'])[0].isoformat(), data['start'])
    def test_scope_required(self):
        row=self.sample();row['scope_type']='global_popular'
        with self.assertRaises(ValueError):self.validate([row])
    def test_leap_year(self):
        start,end=window('2028-02-29')
        self.assertEqual(str(start),'2027-02-28')
        self.assertEqual(str(end),'2028-02-29')
    def test_expired_observations_are_filtered_not_mutated(self):
        row=self.sample();row['observed_date']='2024-01-01'
        rows=[row];original=json.dumps(rows)
        self.assertEqual(select(rows,as_of='2026-11-16'),[])
        self.assertEqual(json.dumps(rows),original)
    def test_reobserved_entry_uses_latest(self):
        first=self.sample();second=dict(first,observed_date='2026-11-01',trend_type='observed')
        self.assertEqual(select([first,second],as_of='2026-11-16'),[second])
    def test_future_archive_rejected(self):
        row=self.sample();row['observed_date']='2030-01-01'
        with self.assertRaises(ValueError):select([row],as_of='2026-11-16')
    def test_archive_is_not_modified_by_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'memes').mkdir();(root/'data').mkdir()
            (root/'memes/wonyoung-thinking.md').write_text('# 원영적 사고\n\n## 뜻풀이\n뜻\n\n## 유래와 확산\n맥락\n')
            archive=root/'data/observations.json';archive.write_text('preserve me')
            write(root,[self.sample()],as_of='2026-11-16')
            self.assertEqual(archive.read_text(),'preserve me')
            self.assertEqual(json.loads((root/'data/latest-selection.json').read_text())['end'],'2026-11-16')
    def test_archive_current(self):
        rows=json.loads((ROOT/'data/observations.json').read_text())['entries']
        validate(rows,archive=True)

    def test_generated_snapshot_is_reproducible(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'repo'
            shutil.copytree(ROOT, root)
            saved=json.loads((root/'data/latest-selection.json').read_text())
            archive=json.loads((root/'data/observations.json').read_text())
            before={p:(root/p).read_text() for p in ['data/latest-selection.json','collections/latest-year.md']}
            write(root,archive['entries'],as_of=saved['end'])
            for p,expected in before.items():
                self.assertEqual((root/p).read_text(),expected)
