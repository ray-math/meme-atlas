"""Versioned editorial usage annotations, not inferred psychological states."""
import hashlib
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FACETS = ('emotions', 'intents', 'situations', 'targets', 'registers', 'risk_flags')
PROFILE_KEYS = {'entry_id', 'source_sha', 'review_status', 'review_note', 'usages'}
USAGE_KEYS = {'id', *FACETS, 'safety', 'context', 'avoid_when', 'example', 'review_note'}
SAFETY = {'standard', 'caution', 'avoid'}
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')

def nonempty(value):
    return isinstance(value, str) and bool(value.strip())

def strings(value):
    return isinstance(value, list) and all(nonempty(v) for v in value) and len(value) == len(set(value))

def blob_sha(path):
    data = Path(path).read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()

def load_vocabulary(root=ROOT):
    value = json.loads((Path(root)/'data/usage-vocabulary.json').read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or set(value.get('facets', {})) != set(FACETS):
        raise ValueError('invalid usage vocabulary version/facets')
    for facet, concepts in value['facets'].items():
        if not isinstance(concepts, list):
            raise ValueError('vocabulary concepts must be a list')
        labels = set()
        for concept in concepts:
            if not isinstance(concept, dict) or set(concept) != {'label', 'aliases'} or not nonempty(concept.get('label')) or not strings(concept.get('aliases')):
                raise ValueError('invalid vocabulary concept: ' + facet)
            for label in [concept['label'], *concept['aliases']]:
                normalized = re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', label).casefold())
                if normalized in labels:
                    raise ValueError('ambiguous vocabulary label: ' + label)
                labels.add(normalized)
    return value

def validate(data, vocabulary, root=ROOT, check_sources=True):
    """Structural/provenance validation only. Never promotes review status."""
    root = Path(root).resolve()
    if not isinstance(data, dict) or set(data) != {'schema_version', 'profiles'} or data['schema_version'] != 1 or not isinstance(data['profiles'], list):
        raise ValueError('invalid usage profiles envelope')
    allowed = {f: {c['label'] for c in vocabulary['facets'][f]} for f in FACETS}
    seen = set()
    for profile in data['profiles']:
        if not isinstance(profile, dict) or set(profile) != PROFILE_KEYS:
            raise ValueError('invalid profile fields')
        identity = profile['entry_id']
        if not isinstance(identity, str) or not SLUG.fullmatch(identity) or identity in seen:
            raise ValueError('invalid/duplicate profile entry_id')
        seen.add(identity)
        if profile['review_status'] not in ('draft', 'reviewed') or not nonempty(profile['review_note']):
            raise ValueError('invalid profile review')
        sha = profile['source_sha']
        if not isinstance(sha, str) or not re.fullmatch('[a-f0-9]{40}', sha):
            raise ValueError('invalid reviewed source SHA')
        path = root/'memes'/f'{identity}.md'
        if check_sources:
            if not path.is_file() or path.resolve().parent != root/'memes':
                raise ValueError('unknown usage entry: ' + identity)
            if blob_sha(path) != sha:
                raise ValueError('usage source changed; editorial re-review required: ' + identity)
        usages = profile['usages']
        if not isinstance(usages, list) or (profile['review_status'] == 'reviewed' and not usages):
            raise ValueError('reviewed profile needs usages')
        usage_ids = set()
        for usage in usages:
            if not isinstance(usage, dict) or set(usage) != USAGE_KEYS:
                raise ValueError('invalid usage fields')
            uid = usage['id']
            if not isinstance(uid, str) or not SLUG.fullmatch(uid) or uid in usage_ids:
                raise ValueError('invalid/duplicate usage id')
            usage_ids.add(uid)
            for facet in FACETS:
                if not strings(usage[facet]) or set(usage[facet]) - allowed[facet]:
                    raise ValueError('unknown/invalid usage facet: ' + facet)
            if usage['safety'] not in ('standard', 'caution', 'avoid'):
                raise ValueError('invalid usage safety')
            if not nonempty(usage['context']) or not nonempty(usage['review_note']) or not strings(usage['avoid_when']):
                raise ValueError('usage context/review/avoid conditions required')
            example = usage['example']
            if not isinstance(example, dict) or set(example) != {'text', 'kind'} or example['kind'] != 'editorial' or not nonempty(example['text']):
                raise ValueError('example must be explicitly editorial')
    return data

def load_profiles(root=ROOT):
    root = Path(root)
    path = root/'data/usage-profiles.json'
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'schema_version': 1, 'profiles': []}
    return validate(value, load_vocabulary(root), root)

if __name__ == '__main__':
    result = load_profiles()
    print(f"Validated {len(result['profiles'])} usage profiles; structure is not factual certification.")
