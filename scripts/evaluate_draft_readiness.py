"""Structural retrieval probes over published drafts, not natural-language accuracy."""
import copy
import json
from pathlib import Path
from build_usage_index import build_usage_index
from usage_profiles import ROOT, load_vocabulary
from search_usage import search

IDS = {'ubd','pro-offended','goat','pon-eunjeong','three-lifts-500','ohiryeo-joa','gabojago'}

def evaluate(root=ROOT):
    original=build_usage_index(root)
    vocab=load_vocabulary(root)
    staged=copy.deepcopy(original)
    for entry in staged['entries']:
        if entry['id'] in IDS:
            entry['review_status']='reviewed'
    rows=[]
    for entry in staged['entries']:
        if entry['id'] not in IDS:
            continue
        for usage in entry['usages']:
            key=(entry['id'],usage['id'])
            filters={'query':entry['title'],'intents':usage['intents'],
                     'situations':usage['situations'],'targets':usage['targets']}
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
                    'actual_draft_is_unpublished':key not in keys(actual) if entry['id'] in {
                        e['id'] for e in original['entries'] if e['review_status']=='draft'} else True}
            rows.append({'entry_id':entry['id'],'usage_id':usage['id'],'filters':filters,
                         'safety':usage['safety'],'checks':checks,
                         'lookup_candidates':sorted(':'.join(k) for k in keys(lookup)),
                         'recommend_candidates':sorted(':'.join(k) for k in keys(recommend)),
                         'passed':all(checks.values())})
    assert original==build_usage_index(root), 'readiness probes mutated production data'
    return {'schema_version':1,'kind':'published-data structural retrieval probes',
            'limitations':['Uses annotation-derived filters, not independent natural-language questions.',
                           'Temporarily marks copies reviewed in memory; never promotes source profiles.',
                           'A pass does not validate source truth, context appropriateness, or generation safety.'],
            'total':len(rows),'passed':sum(r['passed'] for r in rows),'results':rows}

if __name__=='__main__':
    result=evaluate()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    raise SystemExit(0 if result['total']==10 and result['passed']==10 else 1)
