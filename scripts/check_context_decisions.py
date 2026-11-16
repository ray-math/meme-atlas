"""Check the auditability of AI context decisions, not their semantic truth."""
def validate_decisions(plans, retrieval, answers):
    requests={p['id']:p for p in plans['plans']}
    traces={r['id']:r for r in retrieval['results']}
    errors=[]
    for answer in answers['answers']:
        identity=answer['id']
        if identity not in requests or identity not in traces:
            errors.append(identity+': missing request or retrieval')
            continue
        if plans.get('prompt_version')=='contextual-v3':
            facts=answer.get('factual_check',{})
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
    args=p.parse_args()
    errors=validate_decisions(*(json.loads(getattr(args,k).read_text()) for k in ('plans','retrieval','answers')))
    if errors:p.exit(1,'\n'.join(errors)+'\n')
    print('Context decision records are auditable; this is not semantic or safety certification.')
