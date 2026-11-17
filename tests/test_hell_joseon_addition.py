import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pilot_batch import digest
from build_index import build

class HellJoseonCanonicalAdditionTests(unittest.TestCase):
    def test_source_reviewed_entry_are_registered_without_latest_claims(self):
        manifest=json.loads((ROOT/'reports/canonical-hell-joseon-2026-11-17.json').read_text())
        ledger=json.loads((ROOT/'data/pilot-state.json').read_text())
        ids={'hell-joseon'}
        self.assertEqual({r['slug'] for r in manifest['entries']},ids)
        self.assertEqual(set(ledger['batches'][manifest['batch_id']]['ids']),ids)
        known={r['id']:r for r in build(ROOT)}
        observations=json.loads((ROOT/'data/observations.json').read_text())['entries']
        for identity in ids:
            self.assertIn(identity,known)
            self.assertEqual(ledger['entries'][identity]['scope_type'],'korean_usage')
            self.assertEqual(ledger['entries'][identity]['body_hash'],digest((ROOT/'memes'/f'{identity}.md').read_text()))
            self.assertFalse(any(r['id']==identity for r in observations))
        for row in manifest['entries']:
            self.assertEqual(len({r['url'] for r in row['evidence']}),2)
            self.assertEqual(len(row['source_blob_sha']),40)
