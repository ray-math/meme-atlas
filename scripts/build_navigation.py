"""Derived navigation from authored Markdown links; never invent a relationship.

Write a related link once in either article. Only the missing reverse link is
generated, in a removable managed block. Existing prose and hand-written links
remain authoritative. Observation-month links in articles own month membership.
"""
import argparse
import re
from pathlib import Path
from urllib.parse import unquote
from check_dictionary import title, LINK

ROOT = Path(__file__).resolve().parents[1]
START = '<!-- generated-backlinks:start -->'
END = '<!-- generated-backlinks:end -->'
BLOCK = re.compile(r'\n*' + re.escape(START) + r'.*?' + re.escape(END) + r'\n*', re.S)

def authored(text):
    if text.count(START) != text.count(END) or text.count(START) > 1:
        raise ValueError('invalid generated backlink markers')
    return BLOCK.sub('\n', text).rstrip() + '\n'

def targets(root, path, text):
    for label, href in LINK.findall(text):
        if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', href) or href.startswith('#'):
            continue
        target = (path.parent / unquote(href.split('#')[0])).resolve()
        if not target.is_relative_to(root):
            raise ValueError('navigation link escapes repository')
        yield target

def expected(root):
    root = Path(root).resolve()
    entries = {p.resolve(): authored(p.read_text(encoding='utf-8'))
               for p in (root / 'memes').glob('*.md') if p.name != 'README.md'}
    names = {p: title(text) for p, text in entries.items()}
    edges = {p: set(targets(root, p, text)) for p, text in entries.items()}
    outputs = {}
    for p, text in entries.items():
        missing = sorted((source for source in entries
                          if source != p and p in edges[source] and source not in edges[p]),
                         key=lambda source: (names[source], source.name))
        if missing:
            lines = [START, '## 이 항목을 언급한 밈', '']
            lines += [f'- [{names[source]}]({source.name})' for source in missing]
            lines += [END]
            text = text.rstrip() + '\n\n' + '\n'.join(lines) + '\n'
        # Do not churn authored files merely to normalize their trailing newline.
        original = p.read_text(encoding='utf-8')
        if missing or START in original:
            outputs[p.relative_to(root).as_posix()] = text
    lines = ['# 전체 밈 목록', '']
    lines += [f'- [{names[p]}]({p.name})' for p in sorted(entries, key=lambda p: (names[p], p.name))]
    lines += ['', '[사전 소개](../README.md) · [월별 목록](../months/README.md)']
    outputs['memes/README.md'] = '\n'.join(lines) + '\n'
    months = {}
    for p, linked in edges.items():
        for target in linked:
            if target.parent == root/'months' and re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])\.md', target.name):
                months.setdefault(target.stem, set()).add(p)
    # Keep existing empty months; never silently remove editorial history.
    for p in (root/'months').glob('????-??.md'):
        if re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', p.stem):
            months.setdefault(p.stem, set())
    for month, members in sorted(months.items()):
        year, number = month.split('-')
        lines = [f'# {year}년 {int(number)}월', '']
        lines += [f'- [{names[p]}](../memes/{p.name})' for p in sorted(members, key=lambda p: (names[p], p.name))]
        outputs[f'months/{month}.md'] = '\n'.join(lines) + '\n'
    lines = ['# 월별 목록', '',
             '밈을 관찰한 월별 목차입니다. 월은 탄생월이나 최초 유행월을 뜻하지 않습니다.',
             '같은 밈이 여러 달에 실려도 뜻과 예시는 하나의 항목에서 관리합니다.', '']
    year = None
    for month in sorted(months, reverse=True):
        y, m = month.split('-')
        if y != year:
            if year is not None:
                lines.append('')
            lines.append(f'## {y}년')
            year = y
        lines.append(f'- [{int(m)}월]({month}.md)')
    lines += ['', '[사전 소개](../README.md) · [전체 밈 목록](../memes/README.md)']
    outputs['months/README.md'] = '\n'.join(lines) + '\n'
    return outputs

def check(root):
    root = Path(root)
    return [name for name, text in expected(root).items()
            if not (root/name).exists() or (root/name).read_text(encoding='utf-8') != text]

def write(root):
    root = Path(root)
    changed = []
    for name, text in expected(root).items():
        path = root/name
        if path.exists() and path.read_text(encoding='utf-8') == text:
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        changed.append(name)
    return changed

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        stale = check(args.root)
        if stale:
            raise SystemExit('Stale navigation: ' + ', '.join(stale))
        print('Navigation matches authored links.')
    else:
        print('Updated navigation: ' + ', '.join(write(args.root)))
