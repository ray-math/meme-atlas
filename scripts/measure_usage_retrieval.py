"""Measure strict usage-level retrieval separately from entry recall and final answers."""
import argparse
import json
from pathlib import Path
from evaluation_records import indexed_records

def measure(gold, retrieval):
    cases=indexed_records(gold, 'cases'); traces=indexed_records(retrieval, 'results')
    if set(cases)!=set(traces): raise ValueError('case IDs differ')
    def empty():
        return {'queries':0,'recall_hits':0,'top1_hits':0,'candidates':0,'relevant_candidates':0}
    groups={'all_usage_labeled':empty(), 'recommendation_requests':empty()}
    details=[]
    for identity,case in cases.items():
        labels=case.get('acceptable_usage_ids', [])
        if not labels or case.get('expected_action') not in ('recommend','lookup'):
            continue
        allowed=set()
        for label in labels:
            if not isinstance(label,str): raise ValueError('usage gold must be text')
            parts=label.replace('/',':',1).split(':')
            if len(parts)!=2 or not all(parts): raise ValueError('expected entry:usage label')
            allowed.add(tuple(parts))
        hits=traces[identity]['retrieval']['results']
        relevant=[(h['entry_id'],h['usage_id']) in allowed for h in hits]
        values={'queries':1,'recall_hits':int(any(relevant)), 'top1_hits':int(bool(relevant) and relevant[0]),
                'candidates':len(hits), 'relevant_candidates':sum(relevant)}
        for name in ('all_usage_labeled','recommendation_requests'):
            if name=='recommendation_requests' and case['expected_action']!='recommend': continue
            for key,value in values.items(): groups[name][key]+=value
        details.append({'id':identity,**values})
    for values in groups.values():
        values['recall']=values['recall_hits']/values['queries'] if values['queries'] else None
        values['top1']=values['top1_hits']/values['queries'] if values['queries'] else None
        values['candidate_precision']=values['relevant_candidates']/values['candidates'] if values['candidates'] else None
    return {'schema_version':1,'interpretation':'Strict prewritten AI gold usage matching; not human precision or safety grading.',
            'groups':groups,'cases':details}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('gold',type=Path);p.add_argument('retrieval',type=Path)
    args=p.parse_args()
    print('USAGE_METRICS='+json.dumps(measure(json.loads(args.gold.read_text()),json.loads(args.retrieval.read_text())),ensure_ascii=False))
