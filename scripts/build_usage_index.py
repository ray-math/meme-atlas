"""Join canonical usage annotations with entry metadata; no automatic annotation."""
import argparse
import json
from pathlib import Path
from build_index import build
from usage_profiles import ROOT, load_profiles

def build_usage_index(root=ROOT):
    root = Path(root)
    known = {row['id']: row for row in build(root)}
    profiles = load_profiles(root)['profiles']
    entries = []
    for profile in sorted(profiles, key=lambda p: p['entry_id']):
        base = known[profile['entry_id']]
        entries.append({k: base[k] for k in ('id', 'title', 'tags', 'path')} |
                       {'aliases': base.get('aliases', []), 'source_sha': profile['source_sha'],
                        'review_status': profile['review_status'], 'review_note': profile['review_note'],
                        'usages': profile['usages']})
    return {'schema_version': 1, 'vocabulary_version': 1,
            'coverage': {'dictionary_entries': len(known), 'annotated_entries': len(entries),
                         'reviewed_entries': sum(p['review_status'] == 'reviewed' for p in entries),
                         'unannotated_entries': len(known) - len(entries)},
            'entries': entries}

def render(root=ROOT):
    return json.dumps(build_usage_index(root), ensure_ascii=False, indent=2) + '\n'

def write(root=ROOT):
    root = Path(root); path = root/'data/usage-index.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(root), encoding='utf-8')
    return path

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check', action='store_true')
    p.add_argument('--root', type=Path, default=ROOT)
    args = p.parse_args()
    expected = render(args.root)
    path = args.root/'data/usage-index.json'
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8') != expected:
            p.exit(1, 'Stale usage index; run python scripts/build_usage_index.py\n')
        print('Usage index matches reviewed annotations and canonical entries.')
    else:
        write(args.root)
