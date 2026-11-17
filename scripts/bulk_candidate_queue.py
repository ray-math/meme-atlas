"""Read-only exact-normalized candidate queue. No semantic or factual decisions."""
import argparse
import copy
import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path
from build_index import build
from pilot_batch import key

ROOT = Path(__file__).resolve().parents[1]
STATUSES = {'unreviewed', 'held', 'duplicate', 'included'}
CLASSES = ('duplicate_existing', 'duplicate_candidate', 'held', 'needs_research')

def dump(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + '\n'

def digest(value):
    return hashlib.sha256(dump(value).encode()).hexdigest()

def strings(value, label):
    if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(label + ' must be a list of nonempty strings')
    return value

def validate(envelope):
    if not isinstance(envelope, dict) or type(envelope.get('schema_version')) is not int or envelope['schema_version'] != 1:
        raise ValueError('unsupported schema_version')
    rows = envelope.get('candidates')
    if not isinstance(rows, list):
        raise ValueError('candidates must be an array')
    seen = set()
    for r in rows:
        if not isinstance(r, dict):
            raise ValueError('candidate must be object')
        for field in ('id', 'title'):
            if not isinstance(r.get(field), str) or not r[field].strip():
                raise ValueError('invalid ' + field)
        if r['id'] in seen:
            raise ValueError('duplicate ID: ' + r['id'])
        seen.add(r['id'])
        if not isinstance(r.get('status'), str) or r['status'] not in STATUSES:
            raise ValueError('invalid status')
        for field in ('aliases', 'dictionary_paths', 'notes', 'source_urls'):
            strings(r.get(field, []) if field in ('aliases', 'source_urls') else r.get(field), field)
        if not isinstance(r.get('evidence'), list):
            raise ValueError('evidence must be array')
        for field in ('parent_id', 'duplicate_of'):
            value = r.get(field)
            if value is not None and (not isinstance(value, str) or not value.strip() or value == r['id']):
                raise ValueError('invalid ' + field)
        for path in r['dictionary_paths']:
            p = Path(path)
            if p.is_absolute() or '..' in p.parts or len(p.parts) != 2 or p.parts[0] != 'memes' or p.suffix != '.md':
                raise ValueError('unsafe dictionary path')
    return rows

def queue(root=ROOT, inputs=None):
    root = Path(root).resolve()
    legacy = (root / 'data/korea-candidates.json').resolve()
    paths = [legacy] if inputs is None else [Path(p).resolve() for p in inputs]
    if len(set(paths)) != len(paths):
        raise ValueError('repeated input file')
    canonical = build(root)
    by_path = {r['path']: r for r in canonical}
    names = {}
    for r in canonical:
        for name in [r['title'], *r.get('aliases', [])]:
            if key(name):
                names.setdefault(key(name), set()).add(r['path'])
    state_path = root / 'data/pilot-state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {'version': 1, 'entries': {}}
    if type(state.get('version')) is not int or state['version'] != 1 or not isinstance(state.get('entries'), dict):
        raise ValueError('invalid pilot state')
    diagnostics = []
    for slug, r in state['entries'].items():
        if r.get('superseded_by'):
            target = 'memes/' + r['superseded_by'] + '.md'
            if target not in by_path:
                diagnostics.append({'kind': 'retired_target_missing', 'id': slug})
                continue
            for name in [r['title'], *strings(r.get('aliases', []), 'retired aliases')]:
                if key(name):
                    names.setdefault(key(name), set()).add(target)
    sources, records, ids = [], [], set()
    for i, path in enumerate(paths):
        env = json.loads(path.read_text(encoding='utf-8'))
        rows = validate(env)
        kind = 'legacy_existing' if path == legacy else 'newly_collected'
        source_id = 'input-' + str(i)
        sources.append({'id': source_id, 'path': str(path), 'kind': kind,
                        'sha256': digest(env), 'metadata': {k: copy.deepcopy(v) for k, v in env.items() if k != 'candidates'}})
        for row in rows:
            if row['id'] in ids:
                raise ValueError('duplicate ID across inputs: ' + row['id'])
            ids.add(row['id'])
            records.append((source_id, kind, row))
    for _, _, row in records:
        for field in ('parent_id', 'duplicate_of'):
            if row.get(field) and row[field] not in ids:
                diagnostics.append({'id': row['id'], 'kind': 'unresolved_' + field, 'reference': row[field]})
    seen_names, output = {}, []
    for source_id, kind, row in records:
        normalized = sorted({key(n) for n in [row['title'], *row.get('aliases', [])] if key(n)})
        matched = sorted({p for n in normalized for p in names.get(n, ())})
        candidate_matches = sorted({seen_names[n] for n in normalized if n in seen_names})
        for path in row['dictionary_paths']:
            if path not in by_path:
                diagnostics.append({'id': row['id'], 'kind': 'dictionary_path_missing', 'path': path})
            elif path not in matched:
                diagnostics.append({'id': row['id'], 'kind': 'dictionary_name_mismatch', 'path': path})
        verified_included = bool(row['dictionary_paths']) and all(p in matched for p in row['dictionary_paths'])
        if row['status'] == 'included' and not verified_included:
            diagnostics.append({'id': row['id'], 'kind': 'stale_included_status'})
        if row['status'] == 'duplicate' and not matched and not candidate_matches:
            diagnostics.append({'id': row['id'], 'kind': 'unverified_duplicate_status'})
        category = ('duplicate_existing' if matched else 'duplicate_candidate' if candidate_matches
                    else 'held' if row['status'] == 'held' or not normalized else 'needs_research')
        if not normalized:
            diagnostics.append({'id': row['id'], 'kind': 'empty_normalized_name'})
        output.append({'id': row['id'], 'source_id': source_id, 'source_kind': kind,
                       'candidate': copy.deepcopy(row), 'classification': category,
                       'normalized_keys': normalized, 'existing_paths': matched,
                       'candidate_ids': candidate_matches, 'included_link_verified': verified_included})
        for n in normalized:
            seen_names.setdefault(n, row['id'])
    def counts(rows):
        c = Counter(r['classification'] for r in rows)
        result = {k: c[k] for k in CLASSES}
        result.update(total=len(rows), indexed=sum(bool(r['normalized_keys']) for r in rows),
                      normalized_matches=c['duplicate_existing'] + c['duplicate_candidate'])
        if sum(result[k] for k in CLASSES) != result['total']:
            raise ValueError('count mismatch')
        return result
    return {'schema_version': 1, 'method': 'pilot_batch.key exact normalized names only',
            'sources': sources, 'canonical_count': len(canonical),
            'canonical_fingerprint': digest(canonical), 'retired_fingerprint': digest(state),
            'counts': counts(output),
            'by_source_kind': {kind: counts([r for r in output if r['source_kind'] == kind])
                               for kind in ('legacy_existing', 'newly_collected')},
            'rows': output, 'diagnostics': diagnostics,
            'limitations': ['No semantic duplication, factual accuracy or evidence independence judgment.',
                            'Newly collected means rows in supplied exports, not verified new memes.',
                            'Original statuses, IDs and provenance are preserved; no promotion.']}

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('inputs', nargs='*')
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--output', type=Path)
    p.add_argument('--check', action='store_true')
    a = p.parse_args(argv)
    result = queue(a.root, a.inputs or None)
    text = dump(result)
    if a.check and text != dump(queue(a.root, a.inputs or None)):
        raise ValueError('nondeterministic input snapshot')
    if a.output:
        dest = a.output.resolve()
        root = a.root.resolve()
        temp = Path(tempfile.gettempdir()).resolve()
        if not dest.is_relative_to(temp) or dest.is_relative_to(root):
            raise ValueError('output must be a new temporary file outside repository')
        # Exclusive creation also prevents overwriting an input or existing artifact.
        with dest.open('x', encoding='utf-8') as f:
            f.write(text)
    else:
        print(text, end='')
    return result

if __name__ == '__main__':
    main()
