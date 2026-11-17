"""Replay public-text AI plans against a provisional copy, never promote stored profiles."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search
from evaluation_records import indexed_records, ACTIONS

def evaluate(root=ROOT):
    envelope=json.loads((Path(root)/'eval/memory-scope/plans.json').read_text())
    plans=indexed_records(envelope,'plans')
    expected_ids={'P-blanket-kick','P-goodbye-everyone','P-laugh-bell-scene','P-laugh-bell-person','A10','A17','A18','A22','A23','A27'}
    if set(plans)!=expected_ids:
        raise ValueError('public rehearsal must contain exactly the fixed ten cases')
    original_inputs=json.loads((Path(root)/'eval/challenge/audit-inputs.json').read_text())['inputs']
    expected={row['id']:row['prompt'] for row in original_inputs if row['id'] in expected_ids}
    index=copy.deepcopy(build_usage_index(root));vocabulary=load_vocabulary(root)
    named={entry['id']:entry for entry in index['entries']}
    for identity,entry_id,uid in [('P-blanket-kick','blanket-kick','remember-embarrassment'),
                                   ('P-goodbye-everyone','goodbye-everyone','relieved-departure'),
                                   ('P-laugh-bell-scene','laugh-bell','fond-scene'),
                                   ('P-laugh-bell-person','laugh-bell','praise-humor')]:
        usage=next(u for u in named[entry_id]['usages'] if u['id']==uid)
        expected[identity]=usage['context']+'\n'+usage['example']['text']
    if any(plan['prompt']!=expected[identity] for identity,plan in plans.items()):
        raise ValueError('public rehearsal prompt differs from its published source')
    provisional={'blanket-kick','goodbye-everyone','laugh-bell'}
    found={e['id'] for e in index['entries'] if e['id'] in provisional}
    if found!=provisional:
        raise ValueError('missing provisional profiles')
    for entry in index['entries']:
        if entry['id'] in provisional:
            entry['review_status']='reviewed'
    rows=[]
    for plan in plans.values():
        if plan['action'] not in ACTIONS or not isinstance(plan['filters'],dict):
            raise ValueError('invalid public rehearsal plan')
        if plan['action'] in ('clarify','abstain'):
            result={'status':'not_searched','reason':plan['action'],'results':[]}
        else:
            result=search(index,vocabulary,**plan['filters'])
        rows.append({'id':plan['id'],'prompt':plan['prompt'],'action':plan['action'],
                     'filters':plan['filters'],'retrieval':result})
    return {'schema_version':1,'execution':'actual Python search over provisional in-memory profiles',
            'provisional_profiles':sorted(provisional),
            'baseline_coverage':index['coverage'],
            'provisional_reviewed_entries':sum(e['review_status']=='reviewed' for e in index['entries']),
            'coverage_interpretation':'per-result coverage is the source baseline, not provisional review counts',
            'results':rows,
            'limitations':['No new live LLM call in replay. Not independent natural-language accuracy.',
                           'Source profile review statuses are never modified.']}

if __name__=='__main__':
    result=evaluate()
    print('MEMORY_META='+json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    for row in result['results']:
        print('MEMORY_CASE='+json.dumps(row,ensure_ascii=False))
    if any(r['retrieval']['status'] not in ('matches','no_match','not_searched') for r in result['results']):
        raise SystemExit(1)
