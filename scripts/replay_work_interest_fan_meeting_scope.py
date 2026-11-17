"""Replay public-text AI plans against a provisional copy, never promote stored profiles."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search
from evaluation_records import indexed_records, ACTIONS

from scope_records import read_records

def evaluate(root=ROOT, enforce_requirements=True):
    if type(enforce_requirements) is not bool:raise ValueError('requirements control must be boolean')
    expected_ids={'K-work','K-fan','K-workwish','K-exploit','K-intrude','K-consent','A07','A21','E06','A26'}
    envelope,plans=read_records(root,'eval/work-interest-fan-meeting-scope/plans.json',
                                'plans',exact_ids=expected_ids)
    if envelope.get('prompt_version')!='contextual-v3':
        raise ValueError('work/fan rehearsal requires contextual-v3')
    source_ids={'A07','A21','A26'}
    _,original_inputs=read_records(root,'eval/challenge/audit-inputs.json',
                                  'inputs',required_ids=source_ids)
    expected={identity:original_inputs[identity]['prompt'] for identity in source_ids}
    index=copy.deepcopy(build_usage_index(root));vocabulary=load_vocabulary(root)
    named={entry['id']:entry for entry in index['entries']}
    for identity,entry_id,uid in [('K-work','deogeop-ilchi','own-interest-became-work'),
                                   ('K-fan','seongdeok','own-hoped-for-fan-meeting')]:
        usage=next(u for u in named[entry_id]['usages'] if u['id']==uid)
        expected[identity]=usage['context']
    expected['K-workwish']=named['deogeop-ilchi']['usages'][0]['avoid_when'][0]
    expected['K-exploit']=named['deogeop-ilchi']['usages'][0]['avoid_when'][2]
    expected['K-intrude']=named['seongdeok']['usages'][0]['avoid_when'][2]
    expected['K-consent']=named['seongdeok']['usages'][0]['avoid_when'][4]
    _,editorial=read_records(root,'eval/challenge/editorial-inputs.json',
                            'inputs',required_ids={'E06'})
    expected['E06']=editorial['E06']['prompt']
    if any(plan['prompt']!=expected[identity] for identity,plan in plans.items()):
        raise ValueError('public rehearsal prompt differs from its published source')
    provisional={'deogeop-ilchi','seongdeok'}
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
            prefix='A' if group=='audit' else 'E'
            historical_ids={prefix+str(number).zfill(2) for number in range(1,29)}
            _,historical=read_records(root,f'eval/{source}/{group}-plans.json',
                                      'plans',exact_ids=historical_ids)
            for plan in historical.values():
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
    print('WORK_META='+json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    for row in result['results']:
        print('WORK_CASE='+json.dumps(row,ensure_ascii=False))
    if any(r['retrieval']['status'] not in ('matches','no_match','not_searched') for r in result['results']):
        raise SystemExit(1)
