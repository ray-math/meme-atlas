import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pilot_batch import digest
from build_index import build

class BulkWaveOneCanonicalImportTests(unittest.TestCase):
    def test_source_reviewed_entry_is_registered_with_digest_and_scope(self):
        manifest=json.loads((ROOT/'reports/bulk/canonical-wave1-approved.json').read_text())
        ledger=json.loads((ROOT/'data/pilot-state.json').read_text())
        ids={"chill-guy","naniga-suki","italian-brainrot","hambugi","do-you-think-i-dont-know","good-night-ojousama","heogeodeonggeodeongseu","galteyateya","azasu","tiramisu-cake","kaelbak","banmo","bakbak","jjajja","cherry-peace","but-it-was-fast","home-protector","dodoreok-chaewon","keke-rupingpong","josammosa-parody","jjalbang","troll-play","heomu-song","number-song-internet","brain-map-meme","jjijjippong","dotne","eba","haek-intensifier"}
        self.assertEqual(len(manifest['entries']),29)
        self.assertEqual(len(ledger['batches'][manifest['batch_id']]['ids']),29)
        self.assertEqual({r['slug'] for r in manifest['entries']},ids)
        self.assertEqual(set(ledger['batches'][manifest['batch_id']]['ids']),ids)
        known={r['id']:r for r in build(ROOT)}
        for identity in ids:
            self.assertIn(identity,known)
            self.assertEqual(ledger['entries'][identity]['scope_type'],'korean_usage')
            self.assertEqual(ledger['entries'][identity]['body_hash'],digest((ROOT/'memes'/f'{identity}.md').read_text()))
        for row in manifest['entries']:
            self.assertGreaterEqual(len({r['url'] for r in row['evidence']}),2)
            self.assertGreaterEqual(len({r['publisher'] for r in row['evidence']}),2)
            self.assertEqual(len(row['source_revision']),40)
            self.assertEqual(len(row['source_blob_sha']),40)


    def test_approved_source_pins_evidence_and_final_body_remain_bound(self):
        manifest=json.loads((ROOT/'reports/bulk/canonical-wave1-approved.json').read_text())
        snapshot=json.loads((ROOT/'tests/fixtures/bulk-wave1-approved-sources.json').read_text())
        self.assertIs(type(snapshot['schema_version']),int)
        self.assertEqual(snapshot['schema_version'],1)
        self.assertEqual(len(snapshot['entries']),29)
        self.assertEqual(len({r['slug'] for r in snapshot['entries']}),29)
        approved={r['slug']:r for r in snapshot['entries']}
        self.assertEqual(set(approved),{r['slug'] for r in manifest['entries']})
        for row in manifest['entries']:
            fixed=approved[row['slug']]
            for key in ['title','path','source_revision','source_blob_sha','evidence']:
                self.assertEqual(row[key],fixed[key])
            self.assertEqual(digest((ROOT/row['path']).read_text()),fixed['body_hash'])
            for evidence in row['evidence']:
                self.assertEqual(evidence['access'],'direct_body')
