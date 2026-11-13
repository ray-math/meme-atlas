"""Build a dated editorial selection, not an automatic factual verification system."""
import datetime as dt
import json
from pathlib import Path
from build_index import ROOT, build

START=dt.date(2025,11,13)
END=dt.date(2026,11,13)

def validate(rows, root=ROOT):
    known={x['id']:x for x in build(root)}
    seen=set()
    if len(rows)>200: raise ValueError('latest selection exceeds 200')
    for row in rows:
        if row['id'] not in known: raise ValueError('unknown canonical entry')
        if row['id'] in seen: raise ValueError('duplicate latest entry')
        seen.add(row['id'])
        observed=dt.date.fromisoformat(row['observed_date'])
        if not START<=observed<=END: raise ValueError('observation outside requested window')
        if row['trend_type'] not in {'new','resurgence','observed'}: raise ValueError('unknown trend type')
        if row.get('scope_type') not in {'korean_origin','korean_adaptation'}: raise ValueError('scope review missing')
        if not row.get('review_note','').strip(): raise ValueError('editorial date context missing')
    return known

def write(root,rows):
    root=Path(root);known=validate(rows,root)
    labels={'new':'기간 내 새 확산','resurgence':'재유행','observed':'기간 내 사용 확인'}
    lines=['# 최근 1년 한국 밈 선별','','대상 기간: 2025-11-13~2026-11-13. 최대 200개 중 독립 검토를 마친 항목만 담습니다. 관찰일은 최초 탄생일이 아닙니다. 최근에도 보인다는 이유만으로 새 유행이라고 분류하지 않습니다.','']
    for row in sorted(rows,key=lambda r:(r['observed_date'],r['id']),reverse=True):
        item=known[row['id']]
        lines.append(f"- [{item['title']}](../{item['path']}) · {labels[row['trend_type']]} · {row['observed_date']} 관찰")
    lines+=['','본문과 출처 검토는 별개입니다. 공개 목차에는 근거 URL을 노출하지 않습니다.','']
    (root/'collections/latest-year.md').write_text('\n'.join(lines))
    (root/'data/latest-selection.json').write_text(json.dumps({'schema_version':1,'start':START.isoformat(),'end':END.isoformat(),'entries':rows},ensure_ascii=False,indent=2)+'\n')
