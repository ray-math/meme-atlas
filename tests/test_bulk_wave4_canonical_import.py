import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from pilot_batch import digest
from build_index import build

class BulkWaveFourCanonicalImportTests(unittest.TestCase):
    def test_source_reviewed_entry_is_registered_with_digest_and_scope(self):
        manifest=json.loads((ROOT/'reports/bulk/canonical-wave4-approved.json').read_text())
        ledger=json.loads((ROOT/'data/pilot-state.json').read_text())
        ids={"sha-sha-sha","tte-kkeol-look","taebo-hae","national-handclap","dionysus-mood-broken","baby-shark-challenge","geu-japchae","baribarista","laughter-spoon","things-i-achieved","bamboo-cloth-song","positive-negative-markers","bam-yang-gang","chipi-chipi-chapa-chapa","gamdasal","gamdajuk","mukjjippa-major","jwi-lola","pedro-raccoon","oompa-loompa-challenge","we-chose-by-agreement","multiplication-dance","pokemon-dance-challenge","look-at-me-challenge","any-angle-challenge","ian-march","national-power-class","appearance-check","rubber-squeezing","dududu-bababa","honestly-i-was-envious","igeon-an-iji-ye"}
        self.assertEqual(len(manifest['entries']),32)
        self.assertEqual(len(ledger['batches'][manifest['batch_id']]['ids']),32)
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
        manifest=json.loads((ROOT/'reports/bulk/canonical-wave4-approved.json').read_text())
        snapshot=json.loads((ROOT/'tests/fixtures/bulk-wave4-approved-sources.json').read_text())
        self.assertIs(type(snapshot['schema_version']),int)
        self.assertEqual(snapshot['schema_version'],1)
        self.assertEqual(len(snapshot['entries']),32)
        self.assertEqual(len({r['slug'] for r in snapshot['entries']}),32)
        approved={r['slug']:r for r in snapshot['entries']}
        self.assertEqual(set(approved),{r['slug'] for r in manifest['entries']})
        for row in manifest['entries']:
            fixed=approved[row['slug']]
            for key in ['title','path','source_revision','source_blob_sha','evidence']:
                self.assertEqual(row[key],fixed[key])
            self.assertEqual(digest((ROOT/row['path']).read_text()),fixed['body_hash'])
            for evidence in row['evidence']:
                self.assertEqual(evidence['access'],'direct_body')
