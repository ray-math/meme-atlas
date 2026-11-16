"""Usage-level faceted retrieval. Keywords are lexical, not natural-language inference."""
import argparse
import json
import re
import unicodedata
from pathlib import Path
from usage_profiles import ROOT, FACETS, load_vocabulary

def norm(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def canonical(values, facet, vocabulary):
    mapping = {}
    for concept in vocabulary['facets'][facet]:
        for label in [concept['label'], *concept['aliases']]:
            mapping[norm(label)] = concept['label']
    result = set()
    for value in values:
        label = mapping.get(norm(value))
        if label is None:
            raise ValueError('unsupported ' + facet + ' filter: ' + value)
        result.add(label)
    return result

def search(index, vocabulary, query='', *, emotions=(), intents=(), situations=(),
           targets=(), registers=(), exclude_risks=(), mode='recommend', limit=10):
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    if mode not in ('recommend', 'lookup'):
        raise ValueError('mode must be recommend or lookup')
    if index.get('schema_version') != 1 or index.get('vocabulary_version') != 1:
        raise ValueError('unsupported usage index version')
    envelope = {'schema_version': 1, 'mode': mode, 'coverage': index['coverage'],
                'interpretation': 'editorial usage candidates; inspect context and avoid_when before speaking',
                'status': 'no_match', 'results': []}
    raw = {'emotions': emotions, 'intents': intents, 'situations': situations,
           'targets': targets, 'registers': registers}
    try:
        filters = {f: canonical(v, f, vocabulary) for f, v in raw.items()}
        excluded = canonical(exclude_risks, 'risk_flags', vocabulary)
    except ValueError as exc:
        return dict(envelope, status='unsupported_filter', reason=str(exc))
    if not query.strip() and not any(filters.values()):
        return dict(envelope, status='insufficient_query')
    terms = set(norm(t) for t in query.split() if norm(t))
    phrase = norm(query)
    hits = []
    for entry in index['entries']:
        if entry['review_status'] != 'reviewed':
            continue
        for usage in entry['usages']:
            # Never combine facets from different usages of the same meme.
            if any(values and not values.intersection(usage[f]) for f, values in filters.items()):
                continue
            if mode == 'recommend' and usage['safety'] != 'standard':
                continue
            if excluded.intersection(usage['risk_flags']):
                continue
            # Negative contexts/risk notes are deliberately NOT positive search text.
            text = ' '.join([entry['title'], *entry['aliases'], usage['context'],
                             *usage['emotions'], *usage['intents'], *usage['situations']])
            haystack = norm(text)
            matches = [t for t in terms if t in haystack]
            if terms and not matches:
                continue
            exact = phrase and phrase in [norm(entry['title']), *map(norm, entry['aliases'])]
            score = (100 if exact else 0) + 10 * len(matches) + 20 * sum(bool(v) for v in filters.values())
            hits.append({'entry_id': entry['id'], 'title': entry['title'], 'path': entry['path'],
                         'domain_tags': entry['tags'], 'usage_id': usage['id'], 'score': score,
                         'matched_facets': {f: sorted(v.intersection(usage[f])) for f,v in filters.items() if v},
                         'usage': usage, 'review_status': entry['review_status'],
                         'source_sha': entry['source_sha'], 'requires_context_check': True})
    hits.sort(key=lambda h: (-h['score'], h['title'], h['entry_id'], h['usage_id']))
    envelope['results'] = hits[:limit]
    envelope['status'] = 'matches' if hits else 'no_match'
    return envelope

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('query', nargs='?', default='', help='optional positive lexical keywords, not a free-form instruction')
    for option in ('emotion', 'intent', 'situation', 'target', 'register', 'exclude-risk'):
        p.add_argument('--'+option, action='append', default=[])
    p.add_argument('--mode', choices=('recommend', 'lookup'), default='recommend')
    p.add_argument('--limit', type=int, default=10)
    p.add_argument('--root', type=Path, default=ROOT)
    args = p.parse_args()
    try:
        index = json.loads((args.root/'data/usage-index.json').read_text(encoding='utf-8'))
        from build_usage_index import build_usage_index
        if index != build_usage_index(args.root):
            raise ValueError('stale usage index; rebuild and review changed source entries')
        result = search(index, load_vocabulary(args.root), args.query, emotions=args.emotion,
                        intents=args.intent, situations=args.situation, targets=args.target,
                        registers=args.register, exclude_risks=args.exclude_risk,
                        mode=args.mode, limit=args.limit)
    except (ValueError, OSError) as exc:
        p.exit(2, str(exc)+'\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))
