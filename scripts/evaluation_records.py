"""Structural checks for evaluation artifacts; never semantic grading."""
ACTIONS = frozenset(('recommend', 'lookup', 'clarify', 'abstain'))

def indexed_records(envelope, key):
    if isinstance(envelope, dict) and 'schema_version' in envelope:
        if type(envelope['schema_version']) is not int or envelope['schema_version'] != 1:
            raise ValueError('unsupported evaluation schema version')
    rows = envelope.get(key) if isinstance(envelope, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError(key + ' must be a non-empty list')
    result = {}
    for row in rows:
        identity = row.get('id') if isinstance(row, dict) else None
        if not isinstance(identity, str) or not identity.strip() or identity in result:
            raise ValueError(key + ': missing/duplicate evaluation case IDs')
        result[identity] = row
    return result

def validate_selection(answer, hits):
    action = answer.get('action')
    if action not in ACTIONS:
        raise ValueError('unsupported answer action')
    entry = answer.get('selected_entry_id')
    usage = answer.get('selected_usage_id')
    if entry is not None and (not isinstance(entry, str) or not entry.strip()):
        raise ValueError('invalid selected entry')
    if usage is not None and (not isinstance(usage, str) or not usage.strip()):
        raise ValueError('invalid selected usage')
    if action == 'recommend' and (not entry or not usage):
        raise ValueError('recommendation requires an entry and usage')
    if usage and not entry:
        raise ValueError('usage requires an entry')
    if action in ('clarify', 'abstain') and (entry or usage):
        raise ValueError('no-selection action contains a selection')
    if entry:
        pairs = {(r['entry_id'], r['usage_id']) for r in hits}
        ambiguous_lookup = action == 'lookup' and usage is None and any(r['entry_id'] == entry for r in hits)
        if not ambiguous_lookup and (entry, usage) not in pairs:
            raise ValueError('selected usage was not retrieved')
