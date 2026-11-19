import copy
import datetime as dt
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import historical_dates as h

class HistoricalDatesTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT/'data/historical-dates.json').read_text())
        self.known = {r['id']: r for r in json.loads((ROOT/'data/search-index.json').read_text())}

    def test_live_evidence_shape_and_known_entries(self):
        h.validate(self.data, self.known)

    def test_partial_date_intervals(self):
        self.assertEqual(h.interval({'value': '2020', 'precision': 'year'}), (dt.date(2020,1,1),dt.date(2020,12,31)))
        self.assertEqual(h.interval({'value': '2020-02', 'precision': 'month'}), (dt.date(2020,2,1),dt.date(2020,2,29)))

    def test_invalid_date_and_precision(self):
        for value, precision in [('2020','day'),('2020-13','month'),('2021-02-29','day'),('2020','unknown'),(None,'year'),('0000','year')]:
            with self.subTest(value=value, precision=precision), self.assertRaises((ValueError, TypeError)):
                h.interval({'value':value,'precision':precision})

    def test_unknown_last_both_directions(self):
        kind = 'korean_attestation'
        rows = [{'id':'unknown','dates':{kind:{'value':None,'precision':'unknown'}}},
                {'id':'old','dates':{kind:{'value':'2020','precision':'year'}}},
                {'id':'new','dates':{kind:{'value':'2021-05','precision':'month'}}}]
        self.assertEqual([r['id'] for r in h.ordered(rows,kind)],['old','new','unknown'])
        self.assertEqual([r['id'] for r in h.ordered(rows,kind,True)],['new','old','unknown'])

    def test_partial_tie_uses_id_not_precision(self):
        kind = 'meme_emergence'
        rows = [{'id':'z','dates':{kind:{'value':'2020','precision':'year'}}},
                {'id':'a','dates':{kind:{'value':'2020-01','precision':'month'}}}]
        for descending in [False,True]:
            self.assertEqual([r['id'] for r in h.ordered(rows,kind,descending)],['a','z'])

    def test_requires_evidence_and_context(self):
        for field, value in [('source_url',None),('note','')]:
            data = copy.deepcopy(self.data)
            data['entries'][0]['dates']['korean_attestation'][field] = value
            with self.assertRaises(ValueError):
                h.validate(data,self.known)

    def test_all_date_kinds_required(self):
        data = copy.deepcopy(self.data)
        del data['entries'][0]['dates']['meme_emergence']
        with self.assertRaises(ValueError):
            h.validate(data,self.known)

    def test_no_observation_or_canonical_mutation(self):
        paths = ['data/observations.json','data/latest-selection.json','collections/latest-year.md',
                 'data/search-index.json','scripts/latest_collection.py']
        before = {p:(ROOT/p).read_bytes() for p in paths}
        snapshot = copy.deepcopy(self.data)
        for kind in h.KINDS:
            for descending in [False,True]:
                text = h.render(self.data,self.known,kind,descending)
                self.assertIn('최초 사용일이 아닙니다',text)
        self.assertEqual(snapshot,self.data)
        self.assertEqual(before,{p:(ROOT/p).read_bytes() for p in paths})

    def test_checked_in_example_matches_renderer(self):
        self.assertEqual((ROOT/'collections/date-prototype.md').read_text(),
                         h.render(self.data,self.known,'source_edition_publication'))

if __name__ == '__main__':
    unittest.main()
