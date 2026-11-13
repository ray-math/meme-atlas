"""Structural checks only; does not certify the truth of a meme's history."""
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from frontmatter import read as read_metadata
from urllib.parse import unquote

LINK = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
MONTH = re.compile(r'\d{4}-(0[1-9]|1[0-2])\.md$')

def title(text):
    return next((line[2:].strip() for line in text.splitlines() if line.startswith('# ')), '')

def links(root, path, text):
    for label, href in LINK.findall(text):
        if re.match(r'[a-zA-Z][a-zA-Z0-9+.-]*:', href) or href.startswith('#'):
            continue
        target = (path.parent / unquote(href.split('#')[0])).resolve()
        yield label, target

def check(root):
    root = Path(root).resolve()
    errors = []
    files = {p.resolve(): p.read_text(encoding='utf-8') for p in root.rglob('*.md') if '.git' not in p.parts and 'templates' not in p.relative_to(root).parts}
    entries = {p: t for p, t in files.items() if p.parent == root/'memes' and p.name != 'README.md'}
    months = {p: t for p, t in files.items() if p.parent == root/'months' and MONTH.fullmatch(p.name)}
    collections = {p: t for p,t in files.items() if p.parent == root/'collections'}
    graph = {p: list(links(root, p, t)) for p, t in files.items()}
    def err(p, message): errors.append(f'{p.relative_to(root)}: {message}')
    for p, targets in graph.items():
        for label, target in targets:
            if not target.is_relative_to(root) or not target.exists(): err(p, f'broken link: {label}')
            if target in entries and label != title(entries[target]): err(p, f'title mismatch: {label} != {title(entries[target])}')
    seen = {}
    for p, text in entries.items():
        try: read_metadata(text)
        except (ValueError,TypeError) as e: err(p, str(e))
        name = title(text)
        if not name: err(p, 'missing title')
        if name in seen: err(p, f'duplicate title: {name}')
        seen[name] = p
        for section in ['## 뜻풀이', '## 유래와 확산']:
            if section not in text: err(p, f'missing section: {section}')
            elif not text.split(section,1)[1].split('\n## ',1)[0].strip(): err(p, f'empty section: {section}')
        if any(s in text for s in ['쓰이는 장면 — 상황 요약', '위 장면 설명은 용법을', '## 기록과 근거']): err(p, 'unwanted editorial boilerplate')
        if not any(target in months or target in collections for _,target in graph[p]): err(p, 'no observation month or curated collection')
        for _, target in graph[p]:
            if target in entries and p != target and not any(back == p for _,back in graph[target]): err(p, f'missing related backlink: {target.name}')
            if (target in months or target in collections) and not any(back == p for _,back in graph[target]): err(p, f'missing month backlink: {target.name}')
    for p, text in months.items():
        targets = [t for _,t in graph[p] if t in entries]
        if len(targets) != len(set(targets)): err(p, 'duplicate month entry')
        for target in targets:
            if not any(back == p for _,back in graph[target]): err(p, f'entry lacks month link: {target.name}')
        for line in text.splitlines():
            if line.strip() and not line.startswith('# ') and LINK.sub('', line).strip(' -·'): err(p, 'month must contain only heading and links')
    for index, expected in [(root/'memes/README.md',set(entries)), (root/'months/README.md',set(months))]:
        targets = [t for _,t in graph.get(index,[]) if t in expected]
        if len(targets) != len(set(targets)): err(index, 'duplicate index entry')
        if set(targets) != expected: err(index, 'index does not cover all entries')
    for _,target in graph.get(root/'README.md',[]):
        if target in entries: err(root/'README.md', 'home should link to indexes, not individual memes')
    return errors

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
    errors = check(root)
    if errors:
        print('\n'.join(errors)); sys.exit(1)
    print('Dictionary structure checks passed (not a factual-accuracy certification).')

