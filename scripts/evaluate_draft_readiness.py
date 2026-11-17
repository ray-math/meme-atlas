"""Structural retrieval probes over published drafts, not natural-language accuracy."""
import argparse
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search

IDS = {'ubd','pro-offended','goat','pon-eunjeong','three-lifts-500','ohiryeo-joa','gabojago'}

def evaluate(root=ROOT, candidates=None):
    selected=set(IDS if candidates is None else candidates)
    if not selected or selected-IDS:
        raise ValueError('candidate IDs must be a nonempty subset of the reviewed expansion set')
    original=build_usage_index(root)
    present={entry['id']:entry for entry in original['entries']}
    missing=selected-set(present)
    empty={identity for identity in selected if identity in present and not present[identity]['usages']}
    if missing or empty:
        raise ValueError('selected profiles missing or without usages: '+','.join(sorted(missing|empty)))
    vocab=load_vocabulary(root)
    staged=copy.deepcopy(original)
    for entry in staged['entries']:
        if entry['id'] in selected:
            entry['review_status']='reviewed'
    rows=[]
    for entry in staged['entries']:
        if entry['id'] not in selected:
            continue
        for usage in entry['usages']:
            key=(entry['id'],usage['id'])
            filters={'query':entry['title'],'intents':usage['intents'],
                     'situations':usage['situations'],'targets':usage['targets']}
            filters.update(usage.get('retrieval_requirements',{}))
            def keys(result):
                return {(hit['entry_id'],hit['usage_id']) for hit in result['results']}
            lookup=search(staged,vocab,mode='lookup',limit=100,**filters)
            recommend=search(staged,vocab,mode='recommend',limit=100,**filters)
            actual=search(original,vocab,mode='lookup',limit=100,**filters)
            opposite=dict(filters)
            opposite['targets']=[x for x in ['자기','상대','상황','제삼자'] if x not in usage['targets']]
            opposite_result=search(staged,vocab,mode='lookup',limit=100,**opposite)
            checks={'lookup_retrieves_own_usage':key in keys(lookup),
                    'recommend_respects_safety':(key in keys(recommend))==(usage['safety']=='standard'),
                    'opposite_target_does_not_retrieve_same_usage':key not in keys(opposite_result),
                    'unknown_emotion_contract': usage['emotion_status']=='unknown' and usage['emotions']==[],
                    'joy_resolve_filters_do_not_match': all(key not in keys(search(staged,vocab,mode='lookup',limit=100,emotions=[emotion],**filters)) for emotion in ['기쁨','결의']),
                    'context_contract_visible':all(h.get('requires_context_check') is True and h['usage']['avoid_when'] and h['usage']['example']['kind']=='editorial' for h in lookup['results']),
                    'actual_draft_is_unpublished':key not in keys(actual) if entry['id'] in {
                        e['id'] for e in original['entries'] if e['review_status']=='draft'} else True}
            rows.append({'entry_id':entry['id'],'usage_id':usage['id'],'filters':filters,
                         'safety':usage['safety'],'checks':checks,
                         'lookup_candidates':sorted(':'.join(k) for k in keys(lookup)),
                         'recommend_candidates':sorted(':'.join(k) for k in keys(recommend)),
                         'passed':all(checks.values())})
    drift=[];plan_errors=[]
    for group in ['audit','editorial']:
        plans=[]
        for source in ['regression-v3','challenge']:
            for plan in json.loads((Path(root)/f'eval/{source}/{group}-plans.json').read_text())['plans']:
                plans.append(dict(plan,evaluation_set=source+'/'+group))
        for plan in plans:
            if plan['action'] in ('clarify','abstain'):
                continue
            before=search(original,vocab,**plan['filters'])
            after=search(staged,vocab,**plan['filters'])
            for phase,result in [('before',before),('after',after)]:
                if result.get('status') not in ('matches','no_match'):
                    plan_errors.append({'evaluation_set':plan['evaluation_set'],'id':plan['id'],
                                        'phase':phase,'status':result.get('status'),'reason':result.get('reason')})
            def hits(result):
                return [h['entry_id']+':'+h['usage_id'] for h in result['results']]
            if hits(before)!=hits(after):
                drift.append({'evaluation_set':plan['evaluation_set'],'id':plan['id'],'filters':plan['filters'],
                              'before':hits(before),'after':hits(after)})
    assert original==build_usage_index(root), 'readiness probes mutated production data'
    return {'schema_version':1,'kind':'published-data structural retrieval probes',
            'limitations':['Uses annotation-derived filters, not independent natural-language questions.',
                           'Temporarily marks copies reviewed in memory; never promotes source profiles.',
                           'A pass does not validate source truth, context appropriateness, or generation safety.'],
            'staged_public_candidate_drift':drift,
            'candidate_profiles':sorted(selected),
            'evaluated_profile_counts':{identity:sum(r['entry_id']==identity for r in rows) for identity in sorted(selected)},
            'plan_errors':plan_errors,
            'total':len(rows),'passed':sum(r['passed'] for r in rows),'results':rows}

def exit_code(result,fail_on_drift=False):
    passed=result['total']>0 and result['passed']==result['total'] and not result['plan_errors']
    if fail_on_drift and result['staged_public_candidate_drift']:
        passed=False
    return 0 if passed else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate',action='append',help='published profile ID to provisionally review; repeatable')
    parser.add_argument('--fail-on-drift',action='store_true',
                        help='also fail if existing public v2/v3 candidate lists change')
    args=parser.parse_args()
    try:
        result=evaluate(candidates=args.candidate)
    except ValueError as exc:
        parser.exit(2,str(exc)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(exit_code(result,args.fail_on_drift))
