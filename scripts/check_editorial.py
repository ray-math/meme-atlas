"""Validate workflow labels, not factual correctness."""
import json
from pathlib import Path
from frontmatter import read
ROOT = Path(__file__).resolve().parents[1]
STATES = {'discovered', 'reviewing', 'ready', 'published', 'held', 'rejected'}

def check(root):
    root = Path(root)
    errors = []
    candidates = root/'review/candidates.json'
    if candidates.exists():
        seen = set()
        for row in json.loads(candidates.read_text())['candidates']:
            identity = row.get('candidate_id')
            if not identity or identity in seen:
                errors.append('missing or duplicate candidate_id')
            seen.add(identity)
            if row.get('workflow') not in STATES:
                errors.append('invalid candidate workflow: ' + str(identity))
            if row.get('workflow') in {'held', 'rejected'} and not row.get('reason', '').strip():
                errors.append('held/rejected candidate needs reason')
    errors.extend(check_korea_candidates(root))
    decisions = root/'review/tag-decisions.json'
    if decisions.exists():
        for identity, row in json.loads(decisions.read_text())['decisions'].items():
            if not identity or '/' in identity or '\\' in identity or identity in {'.', '..'}:
                errors.append('invalid decision ID')
                continue
            p = root/'memes'/f'{identity}.md'
            if not p.exists():
                errors.append('unknown decision entry: ' + identity)
                continue
            if read(p.read_text()).get('tags'):
                errors.append('tagged entry must not duplicate classification in decisions: ' + identity)
            if row.get('status') not in {'pending', 'domain_independent'}:
                errors.append('invalid tag decision status: ' + identity)
            if row.get('status') == 'domain_independent' and not row.get('reason', '').strip():
                errors.append('domain_independent needs reason: ' + identity)
    return errors


def check_korea_candidates(root):
    """Read-only shape/reference checks; never infer truth or promote status."""
    root = Path(root).resolve()
    path = root/'data/korea-candidates.json'
    if not path.exists():
        return []
    errors = []
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, OSError) as exc:
        return ['candidate ledger cannot be read: ' + str(exc)]
    rows = data.get('candidates') if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return ['candidate ledger candidates must be a list']
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            errors.append('candidate ledger row must be an object')
            continue
        identity = row.get('id')
        if not isinstance(identity, str) or not identity.strip():
            errors.append('candidate ledger missing or invalid id')
        elif identity in seen:
            errors.append('candidate ledger duplicate id: ' + identity)
        else:
            seen.add(identity)
    for row in rows:
        if not isinstance(row, dict):
            continue
        identity = row.get('id')
        status = row.get('status')
        if not isinstance(status, str) or status not in {'unreviewed', 'held', 'duplicate', 'included'}:
            errors.append('candidate ledger invalid status: ' + str(identity))
        for field in ('parent_id', 'duplicate_of'):
            target = row.get(field)
            if target is None:
                if field == 'duplicate_of' and status == 'duplicate':
                    errors.append('candidate ledger duplicate_of required: ' + str(identity))
                continue
            if not isinstance(target, str) or target not in seen or target == identity:
                errors.append('candidate ledger invalid ' + field + ': ' + str(identity))
        if status == 'included':
            paths = row.get('dictionary_paths')
            if not isinstance(paths, list) or not paths:
                errors.append('candidate ledger included needs dictionary_paths: ' + str(identity))
                continue
            for value in paths:
                if not isinstance(value, str):
                    errors.append('candidate ledger invalid dictionary path: ' + str(identity))
                    continue
                relative = Path(value)
                target = (root/relative).resolve()
                if (relative.is_absolute() or len(relative.parts) != 2
                        or relative.parts[0] != 'memes' or relative.suffix != '.md'
                        or relative.name == 'README.md' or target.parent != root/'memes'
                        or not target.is_file()):
                    errors.append('candidate ledger missing/invalid dictionary file: ' + str(identity))
    return errors

if __name__ == '__main__':
    errors = check(ROOT)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Editorial workflow labels valid (not factual verification).')
