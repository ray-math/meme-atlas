import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from latest_collection import validate

class LatestTests(unittest.TestCase):
    def sample(self):return {'id':'wonyoung-thinking','observed_date':'2026-01-01','trend_type':'resurgence','scope_type':'korean_origin','review_note':'시험용 데이터이며 최신 유행 인증 아님'}
    def test_boundaries(self):
        for day in ['2025-11-13','2026-11-13']:
            r=self.sample();r['observed_date']=day;validate([r])
    def test_old_observation(self):
        r=self.sample();r['observed_date']='2025-11-12'
        with self.assertRaises(ValueError):validate([r])
    def test_future_observation(self):
        r=self.sample();r['observed_date']='2026-11-14'
        with self.assertRaises(ValueError):validate([r])
    def test_duplicates(self):
        r=self.sample()
        with self.assertRaises(ValueError):validate([r,r])
    def test_no_canonical_entry(self):
        r=self.sample();r['id']='imaginary-new-entry'
        with self.assertRaises(ValueError):validate([r])
    def test_limit(self):
        with self.assertRaises(ValueError):validate([self.sample()]*201)
