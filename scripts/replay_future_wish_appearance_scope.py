"""Replay public-text AI plans against a provisional copy, never promote stored profiles."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search
from evaluation_records import indexed_records, ACTIONS

def evaluate(root=ROOT, enforce_requirements=True):
    if type(enforce_requirements) is not bool:raise ValueError('requirements control must be boolean')
    envelope=json.loads((Path(root)/'eval/future-wish-appearance-scope/plans.json').read_text())
    plans=indexed_records(envelope,'plans')
    expected_ids={'F-wish','F-appearance','F-pressure','F-danger','A01','A20','A23','A26'}
    if set(plans)!=expected_ids:
        raise ValueError('public rehearsal must contain exactly the fixed eight cases')
    original_inputs=json.loads((Path(root)/'eval/challenge/audit-inputs.json').read_text())['inputs']
    expected={row['id']:row['prompt'] for row in original_inputs if row['id'] in expected_ids}
    index=copy.deepcopy(build_usage_index(root));vocabulary=load_vocabulary(root)
    named={entry['id']:entry for entry in index['entries']}
    for identity,entry_id,uid in [('F-wish','flower-road','wish-good-future'),
                                   ('F-appearance','gaptuk-twi','describe-unexpected-person-on-screen')]:
        usage=next(u for u in named[entry_id]['usages'] if u['id']==uid)
        expected[identity]=usage['context']
    expected['F-pressure']=named['flower-road']['usages'][0]['avoid_when'][1]
    expected['F-danger']=named['gaptuk-twi']['usages'][0]['avoid_when'][1]
    if any(plan['prompt']!=expected[identity] for identity,plan in plans.items()):
        raise ValueError('public rehearsal prompt differs from its published source')
    provisional={'flower-road','gaptuk-twi'}
    found={e['id'] for e in index['entries'] if e['id'] in provisional}
    if found!=provisional:
        raise ValueError('missing provisional profiles')
    for entry in index['entries']:
        if entry['id'] in provisional:
            entry['review_status']='reviewed'
            if not enforce_requirements:
                for usage in entry['usages']:usage.pop('retrieval_requirements',None)
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
    original=build_usage_index(root)
    # Fixed pre-promotion comparison even after an explicitly reviewed rollout.
    for entry in original['entries']:
        if entry['id'] in provisional:entry['review_status']='draft'
    drift=[]
    for source in ['challenge','regression-v3']:
        for group in ['audit','editorial']:
            historical=json.loads((Path(root)/f'eval/{source}/{group}-plans.json').read_text())['plans']
            for plan in historical:
                if plan['action'] in ('clarify','abstain'):continue
                before=search(original,vocabulary,**plan['filters'])
                after=search(index,vocabulary,**plan['filters'])
                def keys(value):return [h['entry_id']+':'+h['usage_id'] for h in value['results']]
                if keys(before)!=keys(after):
                    drift.append({'set':source+'/'+group,'id':plan['id'],'before':keys(before),'after':keys(after)})
    return {'schema_version':1,'execution':'actual Python search over provisional in-memory profiles',
            'provisional_profiles':sorted(provisional),
            'requirements_enabled':enforce_requirements,
            'current_baseline_candidate_drift':drift,
            'baseline_coverage':index['coverage'],
            'provisional_reviewed_entries':sum(e['review_status']=='reviewed' for e in index['entries']),
            'coverage_interpretation':'per-result coverage is the source baseline, not provisional review counts',
            'results':rows,
            'limitations':['No new live LLM call in replay. Not independent natural-language accuracy.',
                           'Source profile review statuses are never modified.']}

if __name__=='__main__':
    result=evaluate()
    print('FUTURE_META='+json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    for row in result['results']:
        print('FUTURE_CASE='+json.dumps(row,ensure_ascii=False))
    if any(r['retrieval']['status'] not in ('matches','no_match','not_searched') for r in result['results']):
        raise SystemExit(1)
