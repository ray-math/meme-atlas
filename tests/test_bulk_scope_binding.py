"""Exercise the real wave guards against manifest/ledger scope drift."""
import copy,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'))
import importlib

class BulkScopeBindingMutationTests(unittest.TestCase):
    def test_each_wave_rejects_manifest_and_ledger_scope_mutations(self):
        original=Path.read_text
        for number in range(1,7):
            module=importlib.import_module(f'test_bulk_wave{number}_canonical_import')
            cls=next(v for v in vars(module).values() if isinstance(v,type) and issubclass(v,unittest.TestCase) and v is not unittest.TestCase)
            guard=cls('test_approved_source_pins_evidence_and_final_body_remain_bound')
            manifest_path=ROOT/f'reports/bulk/canonical-wave{number}-approved.json'
            identity=json.loads(original(manifest_path))['entries'][0]['slug']
            for target in ['manifest','ledger']:
                for key,value in [('scope_type','korean_origin'),('scope_basis',''),('scope_basis','unreviewed replacement')]:
                    path=manifest_path if target=='manifest' else ROOT/'data/pilot-state.json'
                    doc=json.loads(original(path))
                    row=doc['entries'][0] if target=='manifest' else doc['entries'][identity]
                    row[key]=value
                    def altered(p,*args,**kwargs):
                        return json.dumps(doc,ensure_ascii=False) if p==path else original(p,*args,**kwargs)
                    with self.subTest(wave=number,target=target,key=key,value=value),patch.object(Path,'read_text',altered):
                        with self.assertRaises(AssertionError):
                            guard.test_approved_source_pins_evidence_and_final_body_remain_bound()
