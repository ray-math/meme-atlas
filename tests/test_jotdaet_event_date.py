import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pilot_batch import digest

class JotdaetEventDateTests(unittest.TestCase):
    def test_report_and_event_dates_are_distinct(self):
        text=(ROOT/'memes/jotdaet-gual.md').read_text()
        self.assertIn('2026년 1월 보도에서는',text)
        self.assertIn('2025년 12월 공연에서',text)
        self.assertNotIn('2026년에는 나얼이 공연에서',text)
        self.assertIn('2024년 팬덤 분석 기사에서 반응 지표를 가리키는 말로 쓰였고',text)
        state=json.loads((ROOT/'data/pilot-state.json').read_text())
        manifest=json.loads((ROOT/'reports/canonical-jotdaet-event-date-2026-11-17.json').read_text())
        self.assertEqual(state['entries']['jotdaet-gual']['body_hash'],digest(text))
        self.assertEqual(state['batches'][manifest['batch_id']]['ids'],['jotdaet-gual'])
        self.assertEqual(manifest['entries'][0]['evidence'][0]['event_month'],'2025-12')
