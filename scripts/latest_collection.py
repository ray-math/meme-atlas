"""Generate a rolling editorial selection from a preserved observation archive."""
import argparse
import datetime as dt
import json
from pathlib import Path
from build_index import ROOT, build

def window(as_of=None):
    end = dt.date.fromisoformat(as_of) if isinstance(as_of, str) else (as_of or dt.date.today())
    try:
        start = end.replace(year=end.year - 1)
    except ValueError:
        start = end.replace(year=end.year - 1, day=28)
    return start, end

def validate(rows, root=ROOT, as_of=None, archive=False):
    start, end = window(as_of)
    known = {x['id']: x for x in build(root)}
    seen = set()
    if not archive and len(rows) > 200:
        raise ValueError('latest selection exceeds 200')
    for row in rows:
        if row['id'] not in known:
            raise ValueError('unknown canonical entry')
        observed = dt.date.fromisoformat(row['observed_date'])
        identity = (row['id'], row['observed_date']) if archive else row['id']
        if identity in seen:
            raise ValueError('duplicate observation or latest entry')
        seen.add(identity)
        if observed > end or (not archive and observed < start):
            raise ValueError('observation outside requested window')
        if row['trend_type'] not in {'new', 'resurgence', 'observed'}:
            raise ValueError('unknown trend type')
        if row.get('scope_type') not in {'korean_origin', 'korean_adaptation'}:
            raise ValueError('scope review missing')
        if not row.get('review_note', '').strip():
            raise ValueError('editorial date context missing')
    return known

def select(rows, root=ROOT, as_of=None, limit=200):
    if not 1 <= limit <= 200:
        raise ValueError('limit must be between 1 and 200')
    validate(rows, root, as_of, archive=True)
    start, end = window(as_of)
    latest = {}
    for row in sorted(rows, key=lambda r: (r['observed_date'], r['id']), reverse=True):
        if start <= dt.date.fromisoformat(row['observed_date']) <= end:
            latest.setdefault(row['id'], row)
    return list(latest.values())[:limit]

def write(root, rows, as_of=None):
    root = Path(root)
    start, end = window(as_of)
    selected = select(rows, root, end)
    known = validate(selected, root, end)
    labels = {'new':'기간 내 새 확산', 'resurgence':'재유행', 'observed':'기간 내 사용 확인'}
    lines = ['# 최근 1년 한국 밈 선별', '',
             f'대상 기간: {start.isoformat()}~{end.isoformat()}. 최대 200개 중 독립 검토를 마친 항목만 담습니다. 관찰일은 최초 탄생일이 아닙니다. 최근에도 보인다는 이유만으로 새 유행이라고 분류하지 않습니다.', '']
    for row in selected:
        item = known[row['id']]
        lines.append(f"- [{item['title']}](../{item['path']}) · {labels[row['trend_type']]} · {row['observed_date']} 관찰")
    lines += ['', '본문과 출처 검토는 별개입니다. 공개 목차에는 근거 URL을 노출하지 않습니다.', '']
    (root/'collections').mkdir(exist_ok=True)
    (root/'data').mkdir(exist_ok=True)
    (root/'collections/latest-year.md').write_text('\n'.join(lines), encoding='utf-8')
    (root/'data/latest-selection.json').write_text(json.dumps({
        'schema_version': 1, 'start': start.isoformat(), 'end': end.isoformat(),
        'entries': selected}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    # The archive is deliberately not rewritten: expired observations remain available.
    return selected

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', help='ISO date; defaults to the current date')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        archive = json.loads((args.root/'data/observations.json').read_text(encoding='utf-8'))
        selected = write(args.root, archive['entries'], args.as_of)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, f'{exc}\n')
    print(f'Selected {len(selected)} entries; observation archive preserved.')
