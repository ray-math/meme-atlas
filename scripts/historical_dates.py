"""Opt-in date evidence prototype; never rewrites observation or latest indexes."""
import argparse
import calendar
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KINDS = {
    'source_edition_publication': '원작 관련 판본 공개일',
    'meme_emergence': '밈 발생 시점',
    'korean_attestation': '검토 자료 내 한국 사용 확인일',
}
PRECISIONS = {'year': '연', 'month': '월', 'day': '일', 'unknown': '미상'}

def interval(record):
    value, precision = record['value'], record['precision']
    if precision == 'unknown':
        if value is not None:
            raise ValueError('unknown precision requires null')
        return None
    patterns = {'year': r'\d{4}', 'month': r'\d{4}-\d{2}', 'day': r'\d{4}-\d{2}-\d{2}'}
    if precision not in patterns or not isinstance(value, str) or not re.fullmatch(patterns[precision], value):
        raise ValueError('date and precision mismatch')
    if precision == 'year':
        year = int(value)
        return dt.date(year, 1, 1), dt.date(year, 12, 31)
    if precision == 'month':
        year, month = map(int, value.split('-'))
        return dt.date(year, month, 1), dt.date(year, month, calendar.monthrange(year, month)[1])
    day = dt.date.fromisoformat(value)
    return day, day

def validate(data, known):
    if data.get('schema_version') != 1 or not data.get('scope'):
        raise ValueError('schema and scope required')
    seen = set()
    for row in data['entries']:
        if row['id'] not in known or row['id'] in seen:
            raise ValueError('unknown or duplicate entry')
        seen.add(row['id'])
        if set(row['dates']) != set(KINDS):
            raise ValueError('all date kinds required')
        for record in row['dates'].values():
            span = interval(record)
            if not record.get('note', '').strip():
                raise ValueError('date context required')
            source = record.get('source_url')
            if span is not None and (not isinstance(source, str) or not source.startswith('https://')):
                raise ValueError('known date requires source')

def ordered(rows, kind, descending=False):
    if kind not in KINDS:
        raise ValueError('unknown date kind')
    def key(row):
        span = interval(row['dates'][kind])
        if span is None:
            return (1, 0, row['id'])
        lower = span[0].toordinal()
        return (0, -lower if descending else lower, row['id'])
    return sorted(rows, key=key)

def render(data, known, kind, descending=False):
    validate(data, known)
    lines = ['# 날짜 구분 정렬 시제품', '', data['scope'], '',
             '정렬 기준: ' + KINDS[kind] + (' · 내림차순' if descending else ' · 오름차순'), '',
             '연·월·일 정밀도를 그대로 표시합니다. 부분 날짜는 해당 기간의 시작을 계산용 키로만 사용하며 1월 1일이나 월초에 실제 발생했다고 해석하지 않습니다. 겹치는 기간 사이의 실제 선후는 확정하지 않습니다. 미상은 방향과 무관하게 맨 뒤, 같은 계산 키는 항목 ID순입니다.', '',
             '원작 관련 판본의 공개일은 대사 최초 공개일과 다를 수 있습니다. 한국 사용 확인일은 검토 자료 내 사례일 뿐 한국 최초 사용일이 아닙니다. 기존 관측일·최근 1년 목록은 변경하지 않습니다.', '']
    for row in ordered(data['entries'], kind, descending):
        record = row['dates'][kind]
        item = known[row['id']]
        date = record['value'] or '미상'
        lines.append('- [' + item['title'] + '](../' + item['path'] + ') · ' + date + ' · 정밀도: ' + PRECISIONS[record['precision']])
        lines.append('  - ' + record['note'])
        if record.get('source_url'):
            lines.append('  - [날짜 근거](' + record['source_url'] + ')')
    return '\n'.join(lines) + '\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kind', choices=KINDS, default='source_edition_publication')
    parser.add_argument('--descending', action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT/'data/historical-dates.json').read_text())
    known = {r['id']: r for r in json.loads((ROOT/'data/search-index.json').read_text())}
    print(render(data, known, args.kind, args.descending), end='')

if __name__ == '__main__':
    main()
