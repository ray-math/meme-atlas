"""Reviewed batch importer with explicit, hash-guarded updates. Evidence inputs stay outside the public repository.
Structural/replay checks do not certify factual truth.
"""
import argparse, hashlib, json, re, unicodedata, shutil, tempfile, os
from pathlib import Path
from check_dictionary import check, title
from frontmatter import render, validate, read as read_metadata
from build_index import build, write_topics
from build_navigation import write as write_navigation

def key(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def digest(s): return hashlib.sha256(s.encode()).hexdigest()

DEFAULT_MAX_ENTRIES = 100

def _apply(root, input_path, batch, max_entries=DEFAULT_MAX_ENTRIES):
    root = Path(root)
    rows = json.loads(Path(input_path).read_text())
    if not isinstance(rows, list) or not rows:
        raise ValueError('batch must contain at least 1 entry')
    if max_entries < 1 or len(rows) > max_entries:
        raise ValueError(f'batch exceeds maximum of {max_entries} entries')
    ledger_path = root/'data/pilot-state.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'version':1,'batches':{},'entries':{}}
    payload = digest(json.dumps(rows,ensure_ascii=False,sort_keys=True))
    if batch in ledger['batches']:
        if ledger['batches'][batch]['input_hash'] != payload: raise ValueError('batch replay differs; review required')
        for slug in ledger['batches'][batch]['ids']:
            entry = ledger['entries'][slug]
            canonical = entry.get('superseded_by', slug)
            expected = entry.get('canonical_body_hash', entry['body_hash'])
            if digest((root/'memes'/f'{canonical}.md').read_text()) != expected:
                raise ValueError('published entry changed; refuse overwrite')
        return {'status':'unchanged','batch':batch,'added':0}
    known = {}
    for p in (root/'memes').glob('*.md'):
        if p.name!='README.md':
            text=p.read_text();known[key(title(text))]=p.stem
            for alias in read_metadata(text).get('aliases',[]):known[key(alias)]=p.stem
    for slug, item in ledger['entries'].items():
        # Reserve retired names; active metadata comes only from the entry.
        if not item.get('superseded_by'): continue
        known[key(item['title'])]=item['superseded_by']
        for alias in item.get('aliases',[]): known[key(alias)]=item['superseded_by']
    planned=[]
    seen_ids=set()
    added=updated=0
    for row in rows:
        slug=row['slug']; name=row['title']; body=row['markdown'].strip()
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',slug): raise ValueError('unsafe slug')
        if slug in seen_ids: raise ValueError('duplicate ID in batch')
        seen_ids.add(slug)
        operation=row.get('operation','create')
        if operation not in {'create','update'}: raise ValueError('unknown operation')
        entry_path=root/'memes'/f'{slug}.md'
        if ledger['entries'].get(slug,{}).get('superseded_by'):
            raise ValueError('existing ID is retired')
        if operation=='create':
            if slug in ledger['entries'] or entry_path.exists(): raise ValueError('existing ID')
            added+=1
        else:
            if not entry_path.exists(): raise ValueError('update target does not exist')
            current=entry_path.read_text()
            if not row.get('expected_body_hash') or row['expected_body_hash']!=digest(current):
                raise ValueError('published entry changed; refuse overwrite')
            if name!=title(current): raise ValueError('rename requires linked-entry review')
            updated+=1
        if title(body)!=name: raise ValueError('title mismatch')
        if len({x['url'] for x in row['evidence']}) < 2: raise ValueError('two reviewed evidence URLs required')
        if not row.get('reviewed'): raise ValueError('human/editorial review gate missing')
        if row.get('scope_type') not in {'korean_origin','korean_adaptation'} or not row.get('scope_basis','').strip():
            raise ValueError('Korean origin/adaptation scope review required')
        for alias in [name]+row.get('aliases',[]):
            normalized=key(alias)
            if not normalized: raise ValueError('empty alias')
            if normalized in known and known[normalized]!=slug: raise ValueError('alias collision: '+alias)
            known[normalized]=slug
        if re.search(r'https?://',body): raise ValueError('public entry contains evidence URL')
        body=render(row.get('tags',[]),row.get('aliases',[]))+body
        if '../collections/pilot-30.md' not in body:
            body+='\n\n[기본 수록 목록](../collections/pilot-30.md)\n'
        planned.append((row,body))
    # Staging validation happens before caller's atomic Git tree/commit publication.
    for row,body in planned:
        (root/'memes'/f"{row['slug']}.md").write_text(body)
        ledger['entries'][row['slug']]={'title':row['title'],'aliases':row.get('aliases',[]),'batch':batch,'body_hash':digest(body),'scope_type':row['scope_type'],'scope_basis':row['scope_basis'],'tags':row.get('tags',[])}
        if not row.get('aliases'):ledger['entries'][row['slug']].pop('aliases')
    ledger['batches'][batch]={'input_hash':payload,'ids':[r['slug'] for r in rows]}
    (root/'data').mkdir(exist_ok=True); (root/'collections').mkdir(exist_ok=True)
    ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
    index='# 전체 밈 목록\n\n'
    all_entries=sorted((title(p.read_text()),p.name) for p in (root/'memes').glob('*.md') if p.name!='README.md')
    index+='\n'.join(f'- [{n}]({f})' for n,f in all_entries)+'\n\n[사전 소개](../README.md) · [월별 목록](../months/README.md)\n'
    (root/'memes/README.md').write_text(index)
    collection='# 기본 수록 목록\n\n관찰 월이나 최신 유행 순위를 뜻하지 않는 기본 수록 항목입니다. 한국에서 생성되었거나 독자적인 한국식 변형이 확인된 밈을 다룹니다.\n\n'
    collection+='\n'.join(f'- [{v["title"]}](../memes/{k}.md)' for k,v in ledger['entries'].items() if not v.get('superseded_by'))+'\n'
    (root/'collections/pilot-30.md').write_text(collection)
    write_navigation(root)
    # Hash the final rendered entries, including managed navigation blocks.
    for row, _ in planned:
        slug=row['slug']
        ledger['entries'][slug]['body_hash']=digest((root/'memes'/f'{slug}.md').read_text())
    ledger_path.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
    search_rows=build(root)
    (root/'data/search-index.json').write_text(json.dumps(search_rows,ensure_ascii=False,indent=2)+'\n')
    write_topics(root,search_rows)
    errors=check(root)
    if errors: raise ValueError('\n'.join(errors))
    return {'status':'applied','batch':batch,'added':added,'updated':updated,'total_pilot':len(ledger['entries'])}

def apply(root, input_path, batch, max_entries=DEFAULT_MAX_ENTRIES):
    root=Path(root).resolve()
    with tempfile.TemporaryDirectory() as directory:
        stage=Path(directory)/'stage'
        shutil.copytree(root,stage,ignore=shutil.ignore_patterns('.git','__pycache__','.venv','node_modules','.pytest_cache'))
        before={p.relative_to(stage):hashlib.sha256(p.read_bytes()).hexdigest() for p in stage.rglob('*') if p.is_file()}
        result=_apply(stage,input_path,batch,max_entries=max_entries)
        if result['status']=='unchanged': return result
        # Validate a whole batch before touching the working copy; ledger written last.
        files=[p for p in stage.rglob('*') if p.is_file()]
        # Refuse concurrent edits before publishing any file, including entries
        # not in this batch: index generation depends on the full snapshot.
        for relative, expected in before.items():
            target=root/relative
            if not target.is_file() or hashlib.sha256(target.read_bytes()).hexdigest()!=expected:
                raise ValueError('working copy changed during validation; retry from latest')
        for p in files:
            relative=p.relative_to(stage)
            if relative not in before and (root/relative).exists():
                raise ValueError('working copy changed during validation; new file collision')
        files.sort(key=lambda p: p.relative_to(stage).as_posix()=='data/pilot-state.json')
        for p in files:
            dest=root/p.relative_to(stage)
            if dest.exists() and dest.read_bytes()==p.read_bytes():continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_name(dest.name+'.pilot-tmp')
            shutil.copy2(p,tmp);os.replace(tmp,dest)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--batch',required=True);p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));p.add_argument('--max-entries',type=int,default=DEFAULT_MAX_ENTRIES);a=p.parse_args()
    print(json.dumps(apply(a.root,a.input,a.batch,max_entries=a.max_entries),ensure_ascii=False))
