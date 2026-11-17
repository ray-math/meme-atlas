"""Replay public-text AI plans against a provisional copy, never promote stored profiles."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search
from evaluation_records import indexed_records, ACTIONS

def read_records(root, relative_path, key, *, required_ids=None, exact_ids=None):
    """Validate this rehearsal's source records without changing their order."""
    envelope=json.loads((Path(root)/relative_path).read_text())
    rows=indexed_records(envelope,key)
    if required_ids is not None and not required_ids.issubset(rows):
        raise ValueError(relative_path+': missing required IDs '+str(sorted(required_ids-set(rows))))
    if exact_ids is not None and set(rows)!=exact_ids:
        raise ValueError(relative_path+': unexpected or missing IDs')
    for row in rows.values():
        if not isinstance(row.get('prompt'),str) or not row['prompt'].strip():
            raise ValueError(relative_path+': prompt must be non-empty text')
        if key=='plans':
            if not isinstance(row.get('action'),str) or row['action'] not in ACTIONS:
                raise ValueError(relative_path+': invalid action')
            if not isinstance(row.get('filters'),dict):
                raise ValueError(relative_path+': filters must be an object')
    return envelope,rows

def evaluate(root=ROOT, enforce_requirements=True):
    if type(enforce_requirements) is not bool:raise ValueError('requirements control must be boolean')
    expected_ids={'G-defeat','G-friday','G-force','G-system','G-offday','G-overwork','A04','E06','A20','A26'}
    envelope,plans=read_records(root,'eval/game-defeat-friday-leisure-scope/plans.json',
                                'plans',exact_ids=expected_ids)
    if envelope.get('prompt_version')!='contextual-v3':
        raise ValueError('game/leisure rehearsal requires contextual-v3')
    source_ids={'A04','A20','A26'}
    _,original_inputs=read_records(root,'eval/challenge/audit-inputs.json',
                                  'inputs',required_ids=source_ids)
    expected={identity:original_inputs[identity]['prompt'] for identity in source_ids}
    index=copy.deepcopy(build_usage_index(root));vocabulary=load_vocabulary(root)
    named={entry['id']:entry for entry in index['entries']}
    for identity,entry_id,uid in [('G-defeat','gg','own-game-defeat'),
                                   ('G-friday','fiery-friday','friday-leisure-anticipation')]:
        usage=next(u for u in named[entry_id]['usages'] if u['id']==uid)
        expected[identity]=usage['context']
    expected['G-force']=named['gg']['usages'][0]['avoid_when'][1]
    expected['G-system']=named['gg']['usages'][0]['avoid_when'][2]
    expected['G-offday']=named['fiery-friday']['usages'][0]['avoid_when'][0]
    expected['G-overwork']=named['fiery-friday']['usages'][0]['avoid_when'][3]
    _,editorial=read_records(root,'eval/challenge/editorial-inputs.json',
                            'inputs',required_ids={'E06'})
    expected['E06']=editorial['E06']['prompt']
    if any(plan['prompt']!=expected[identity] for identity,plan in plans.items()):
        raise ValueError('public rehearsal prompt differs from its published source')
    provisional={'gg','fiery-friday'}
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
    print('GAME_META='+json.dumps({k:v for k,v in result.items() if k!='results'},ensure_ascii=False))
    for row in result['results']:
        print('GAME_CASE='+json.dumps(row,ensure_ascii=False))
    if any(r['retrieval']['status'] not in ('matches','no_match','not_searched') for r in result['results']):
        raise SystemExit(1)
