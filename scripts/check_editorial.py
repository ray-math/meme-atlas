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

if __name__ == '__main__':
    errors = check(ROOT)
    if errors:
        raise SystemExit('\n'.join(errors))
    print('Editorial workflow labels valid (not factual verification).')
