"""Shared structural source-record loader; caller owns scope and version policy."""
import json
from pathlib import Path
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

