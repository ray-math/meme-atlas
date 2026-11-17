"""Replay frozen AI query plans using the real search implementation. No LLM call here."""
import argparse
import json
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from usage_profiles import ROOT, load_vocabulary
from build_usage_index import build_usage_index
from search_usage import search
from evaluation_records import ACTIONS, indexed_records

def replay(plans, root=ROOT):
    indexed_records({'schema_version':1, 'plans': plans}, 'plans')
    for plan in plans:
        if plan.get('action') not in ACTIONS:
            raise ValueError('unsupported plan action')
        if not isinstance(plan.get('prompt'), str) or not plan['prompt'].strip():
            raise ValueError('plan prompt must be non-empty text')
        if not isinstance(plan.get('filters'), dict):
            raise ValueError('plan filters must be an object')
    index=build_usage_index(root);vocabulary=load_vocabulary(root);results=[]
    seen=set()
    for plan in plans:
        identity=plan['id']
        if identity in seen:raise ValueError('duplicate plan id')
        seen.add(identity)
        if plan['action'] in ('clarify','abstain'):
            result={'status':'not_searched','results':[],'reason':plan['action']}
        else:
            try:result=search(index,vocabulary,**plan['filters'])
            except (ValueError,TypeError) as exc:
                result={'status':'invalid_plan','results':[],'reason':str(exc)}
        results.append({'id':identity,'prompt':plan['prompt'],'action':plan['action'],
                        'filters':plan.get('filters',{}),'retrieval':result})
    digest=lambda value: hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    return {'schema_version':1,'execution':'actual_search_replay_not_llm_inference',
            'recorded_at':datetime.now(timezone.utc).isoformat(),
            'source_revision':os.environ.get('GITHUB_SHA','unrecorded'),
            'plans_sha256':digest(plans),'index_sha256':digest(index),
            'vocabulary_sha256':digest(vocabulary),
            'coverage':index['coverage'],'results':results}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('plans',type=Path)
    p.add_argument('--root',type=Path,default=ROOT)
    p.add_argument('--jsonl',action='store_true',help='emit one case per log line for larger batches')
    a=p.parse_args()
    plans=json.loads(a.plans.read_text(encoding='utf-8'))
    trace=replay(plans['plans'],a.root)
    if a.jsonl:
        print('NLMETA='+json.dumps({k:v for k,v in trace.items() if k!='results'},ensure_ascii=False,separators=(',',':')))
        for row in trace['results']:
            print('NLCASE='+json.dumps(row,ensure_ascii=False,separators=(',',':')))
    else:
        print('NLTRACE='+json.dumps(trace,ensure_ascii=False,separators=(',',':')))
