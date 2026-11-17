"""Check the auditability of AI context decisions, not their semantic truth."""
from evaluation_records import ACTIONS, indexed_records, validate_selection

def validate_decisions(plans, retrieval, answers, expected_prompt_version=None):
    try:
        requests=indexed_records(plans, 'plans')
        traces=indexed_records(retrieval, 'results')
        outputs=indexed_records(answers, 'answers')
        if set(requests)!=set(traces) or set(requests)!=set(outputs):
            raise ValueError('missing/extra evaluation case IDs')
    except ValueError as exc:
        return [str(exc)]
    errors=[]
    version=plans.get('prompt_version')
    if version not in ('contextual-v2','contextual-v3'):
        errors.append('unsupported or missing prompt version')
    if expected_prompt_version is not None and version != expected_prompt_version:
        errors.append('prompt version differs from required evaluation contract')
    if answers.get('prompt_version') != version:
        errors.append('answer prompt version differs from plan')
    for identity, plan in requests.items():
        if not isinstance(plan.get('action'),str) or plan.get('action') not in ACTIONS or not isinstance(plan.get('prompt'), str) or not isinstance(plan.get('filters'), dict):
            errors.append(identity+': invalid plan structure')
        for field in ('prompt', 'action', 'filters'):
            if field not in traces[identity] or traces[identity][field] != plan.get(field):
                errors.append(identity+': plan/trace '+field+' mismatch')
    if errors:
        return errors
    for answer in answers['answers']:
        identity=answer['id']
        if identity not in requests or identity not in traces:
            errors.append(identity+': missing request or retrieval')
            continue
        try:
            validate_selection(answer, traces[identity]['retrieval']['results'])
        except ValueError as exc:
            errors.append(identity+': '+str(exc))
            continue
        if plans.get('prompt_version')=='contextual-v3':
            facts=answer.get('factual_check',{})
            if not isinstance(facts,dict):
                errors.append(identity+': invalid factual audit')
                continue
            if facts.get('unsupported_claims')!=[]:
                errors.append(identity+': unresolved factual claims')
            claims=facts.get('supported_claims')
            if not isinstance(claims,list):
                errors.append(identity+': missing factual audit')
            else:
                for claim in claims:
                    if (not isinstance(claim,dict) or not isinstance(claim.get('claim'),str)
                        or not claim['claim'].strip() or not isinstance(claim.get('evidence_span'),str)
                        or not claim['evidence_span'].strip()
                        or claim['evidence_span'] not in requests[identity]['prompt']):
                        errors.append(identity+': factual evidence not quoted from request')
        if answer['action']!='recommend':
            continue
        selected=next((r for r in traces[identity]['retrieval']['results']
                       if r['entry_id']==answer.get('selected_entry_id')
                       and r['usage_id']==answer.get('selected_usage_id')),None)
        if selected is None:
            errors.append(identity+': recommendation not retrieved')
            continue
        usage=selected['usage']
        if usage['safety']=='avoid':
            errors.append(identity+': avoid usage recommended')
        context=answer.get('context_check',{})
        if not isinstance(context,dict):
            errors.append(identity+': invalid context audit')
            continue
        if context.get('assessment')!='compatible' or context.get('unresolved_conditions')!=[]:
            errors.append(identity+': unresolved context')
        spans=context.get('evidence_spans')
        if not isinstance(spans,list) or not spans or any(not isinstance(s,str) or not s.strip()
                                                        or s not in requests[identity]['prompt'] for s in spans):
            errors.append(identity+': context evidence not quoted from request')
        checked=context.get('checked_risk_flags')
        if not isinstance(checked,list) or any(not isinstance(s,str) for s in checked):
            errors.append(identity+': invalid risk assessment')
        elif not set(usage['risk_flags']).issubset(checked):
            errors.append(identity+': risk flags not assessed')
    return errors

if __name__=='__main__':
    import argparse
    import json
    from pathlib import Path
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('plans','retrieval','answers'):p.add_argument(name,type=Path)
    p.add_argument('--expected-prompt-version',choices=('contextual-v2','contextual-v3'))
    args=p.parse_args()
    errors=validate_decisions(*(json.loads(getattr(args,k).read_text()) for k in ('plans','retrieval','answers')), expected_prompt_version=args.expected_prompt_version)
    if errors:p.exit(1,'\n'.join(errors)+'\n')
    print('Context decision records are auditable; this is not semantic or safety certification.')
