"""Compare current retrieval with immutable traces and narrowly reviewed additions."""
import copy
import json
from pathlib import Path
from evaluation_records import indexed_records

def load_additions(root):
    data=json.loads((Path(root)/'eval/reviewed-expansions.json').read_text())
    if data.get('schema_version')!=1 or not isinstance(data.get('additions'),list):
        raise ValueError('invalid reviewed expansion registry')
    result={}
    for row in data['additions']:
        if not isinstance(row,dict) or not all(isinstance(row.get(k),str) and row[k].strip()
                                               for k in ['evaluation_set','case_id','reason']):
            raise ValueError('invalid reviewed expansion identity or reason')
        hit=row.get('expected_hit')
        if not isinstance(hit,dict) or not all(isinstance(hit.get(k),str) and hit[k]
                                             for k in ['entry_id','usage_id','source_sha']):
            raise ValueError('invalid reviewed addition hit')
        identity=(row['evaluation_set'],row['case_id'],hit['entry_id'],hit['usage_id'])
        if identity in result:raise ValueError('duplicate reviewed addition')
        position=row.get('expected_position')
        if type(position) is not int or position<0:raise ValueError('invalid addition position')
        result[identity]={'hit':hit,'position':position}
    return result

def compare(frozen,current,evaluation_set,additions):
    old=indexed_records({'schema_version':1,'results':frozen},'results')
    new=indexed_records({'schema_version':1,'results':current},'results')
    if list(old)!=list(new):raise ValueError('case IDs/order changed')
    expected={(case,entry,usage):hit for (group,case,entry,usage),hit in additions.items()
              if group==evaluation_set}
    if any(case not in old for case,entry,usage in expected):
        raise ValueError('reviewed addition refers to a missing case')
    seen=set()
    for identity in old:
        before=copy.deepcopy(old[identity]);after=copy.deepcopy(new[identity])
        for row in [before,after]:
            retrieval=row.get('retrieval')
            if not isinstance(retrieval,dict) or not isinstance(retrieval.get('results'),list):
                raise ValueError('invalid retrieval')
            retrieval.pop('coverage',None)
            hits=retrieval['results']
            keys=[(h.get('entry_id'),h.get('usage_id')) for h in hits]
            if len(keys)!=len(set(keys)):raise ValueError('duplicate retrieval candidate')
        old_keys={(h['entry_id'],h['usage_id']) for h in before['retrieval']['results']}
        retained=[]
        for position,hit in enumerate(after['retrieval']['results']):
            key=(identity,hit['entry_id'],hit['usage_id'])
            if key in expected:
                if (hit['entry_id'],hit['usage_id']) in old_keys:
                    raise ValueError('addition already exists in frozen trace')
                if hit!=expected[key]['hit'] or position!=expected[key]['position']:
                    raise ValueError('reviewed addition content or position changed')
                seen.add(key)
            else:retained.append(hit)
        after['retrieval']['results']=retained
        if before!=after:
            raise ValueError('unreviewed behavioral drift: '+evaluation_set+'/'+identity)
    if seen!=set(expected):raise ValueError('reviewed addition missing from current candidates')
    return {'cases':len(old),'reviewed_additions':len(seen)}
