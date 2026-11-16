"""Report hand-authored pilot retrieval regression cases, not semantic accuracy."""
import json
from pathlib import Path
from usage_profiles import ROOT, load_vocabulary
from build_usage_index import build_usage_index
from search_usage import search

def evaluate(root=ROOT):
    root=Path(root)
    cases=json.loads((root/'tests/fixtures/usage-evaluation.json').read_text())['cases']
    index=build_usage_index(root);vocab=load_vocabulary(root);results=[]
    for case in cases:
        result=search(index,vocab,**case['filters'])
        found={h['entry_id']+':'+h['usage_id'] for h in result['results']}
        passed=(result['status']==case['expected_status'] if 'expected_status' in case
                else bool(found.intersection(case['expected_any'])))
        if 'expected_exact' in case:
            passed = passed and found == set(case['expected_exact'])
        passed = passed and not found.intersection(case.get('expected_absent', []))
        results.append({'id':case['id'],'passed':passed,'status':result['status'],
                        'found':sorted(found)})
    return {'schema_version':1,'evaluation_kind':'editorial_regression_not_independent_accuracy',
            'coverage':index['coverage'],'total':len(results),
            'passed':sum(r['passed'] for r in results),'results':results}

if __name__=='__main__':
    report=evaluate()
    print(json.dumps(report,ensure_ascii=False,indent=2))
    raise SystemExit(0 if report['passed']==report['total'] else 1)
