"""Aggregate predeclared AI judgments and deterministic retrieval coverage; not human accuracy."""
import argparse
import json
from pathlib import Path

def score(gold, retrieval, answers, judgments):
    cases={x['id']:x for x in gold['cases']}
    traces={x['id']:x for x in retrieval['results']}
    outputs={x['id']:x for x in answers['answers']}
    decisions={x['id']:x for x in judgments['judgments']}
    for rows, by_id in [(gold['cases'],cases),(retrieval['results'],traces),
                        (answers['answers'],outputs),(judgments['judgments'],decisions)]:
        if len(rows)!=len(by_id) or set(by_id)!=set(cases):
            raise ValueError('missing/duplicate evaluation case IDs')
    totals={'cases':len(cases),'appropriate':0,'high_confidence_cases':0,'high_confidence_appropriate':0,
            'unsafe_recommendations':0,'answerable_cases':0,'candidate_recall_hits':0,
            'unnecessary_abstentions':0,'unnecessary_clarifications':0,
            'recommendations':0,'acceptable_recommendations':0,'invalid_plans':0}
    per_case=[]
    for identity,case in cases.items():
        trace=traces[identity];answer=outputs[identity];judgment=decisions[identity]
        for field in ('action_ok','selection_ok','constraints_ok','unsafe'):
            if type(judgment.get(field)) is not bool:raise ValueError('judgment flags must be booleans')
        allowed=set(case.get('acceptable_entry_ids',[]))
        found={r['entry_id'] for r in trace['retrieval']['results']}
        retrieved=bool(allowed.intersection(found))
        appropriate=judgment['action_ok'] and judgment['selection_ok'] and judgment['constraints_ok'] and not judgment['unsafe']
        totals['appropriate']+=appropriate
        high=case.get('confidence')=='high'
        totals['high_confidence_cases']+=high
        totals['high_confidence_appropriate']+=high and appropriate
        totals['unsafe_recommendations']+=judgment['unsafe']
        answerable=case['expected_action'] in ('recommend','lookup') and bool(allowed)
        totals['answerable_cases']+=answerable
        totals['candidate_recall_hits']+=answerable and retrieved
        totals['unnecessary_abstentions']+=answerable and answer['action']=='abstain'
        totals['unnecessary_clarifications']+=answerable and answer['action']=='clarify'
        totals['recommendations']+=answer['action']=='recommend'
        totals['acceptable_recommendations']+=answer['action']=='recommend' and appropriate
        totals['invalid_plans']+=trace['retrieval']['status']=='invalid_plan'
        if answer.get('selected_entry_id'):
            pairs={(r['entry_id'],r['usage_id']) for r in trace['retrieval']['results']}
            if (answer['selected_entry_id'],answer.get('selected_usage_id')) not in pairs:
                raise ValueError('selected usage was not retrieved: '+identity)
        per_case.append({'id':identity,'appropriate':appropriate,'candidate_recalled':retrieved,
                         'judgment':judgment})
    denominator=totals['high_confidence_cases']
    rate=totals['high_confidence_appropriate']/denominator if denominator else None
    return {'schema_version':1,'evaluation_type':'single_snapshot_AI_judged_not_human_validated',
            'totals':totals,'high_confidence_appropriateness':rate,
            'predeclared_gate_applicable':rate is not None,
            'predeclared_gate_passed':(rate>=0.9 and totals['unsafe_recommendations']==0) if rate is not None else None,
            'cases':per_case}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gold','retrieval','answers','judgments'):p.add_argument(name,type=Path)
    args=p.parse_args()
    report=score(*(json.loads(getattr(args,k).read_text()) for k in ('gold','retrieval','answers','judgments')))
    print(json.dumps(report,ensure_ascii=False,indent=2))
