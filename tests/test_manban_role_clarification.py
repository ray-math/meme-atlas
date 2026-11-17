import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pilot_batch import digest
from build_index import build

class ManbanRoleClarificationTests(unittest.TestCase):
    def test_source_reviewed_entry_are_registered_without_latest_claims(self):
        manifest=json.loads((ROOT/'reports/canonical-manban-role-clarification-2026-11-17.json').read_text())
        ledger=json.loads((ROOT/'data/pilot-state.json').read_text())
        ids={'manbanjalbu'}
        self.assertEqual({r['slug'] for r in manifest['entries']},ids)
        self.assertEqual(set(ledger['batches'][manifest['batch_id']]['ids']),ids)
        known={r['id']:r for r in build(ROOT)}
        observations=json.loads((ROOT/'data/observations.json').read_text())['entries']
        for identity in ids:
            self.assertIn(identity,known)
            self.assertEqual(ledger['entries'][identity]['scope_type'],'korean_origin')
            self.assertEqual(ledger['entries'][identity]['body_hash'],digest((ROOT/'memes'/f'{identity}.md').read_text()))
        for row in manifest['entries']:
            self.assertEqual(len({r['url'] for r in row['evidence']}),2)
            self.assertEqual(len(row['source_blob_sha']),40)

    def test_roles_are_examples_not_exclusive_speaker_rules(self):
        body=(ROOT/'memes/manbanjalbu.md').read_text()
        self.assertIn('처음 만나는 자리에서',body)
        self.assertIn('답하는 식으로 함께 쓸 수 있다',body)
        self.assertNotIn('처음 들어오는 쪽의 인사',body)
