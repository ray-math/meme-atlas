"""Small-batch importer. Evidence inputs stay outside the public repository.
Structural/replay checks do not certify factual truth.
"""
import argparse, hashlib, json, re, unicodedata, shutil, tempfile, os
from pathlib import Path
from check_dictionary import check, title
from frontmatter import render, validate, read as read_metadata

def key(value):
    return re.sub(r'[^\w]+', '', unicodedata.normalize('NFKC', value).casefold())

def digest(s): return hashlib.sha256(s.encode()).hexdigest()

def _apply(root, input_path, batch):
    root = Path(root)
    rows = json.loads(Path(input_path).read_text())
    if len(rows) != 10: raise ValueError('pilot batch must contain exactly 10 entries')
    ledger_path = root/'data/pilot-state.json'
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {'version':1,'batches':{},'entries':{}}
    payload = digest(json.dumps(rows,ensure_ascii=False,sort_keys=True))
    if batch in ledger['batches']:
        if ledger['batches'][batch]['input_hash'] != payload: raise ValueError('batch replay differs; review required')
        for slug in ledger['batches'][batch]['ids']:
            if digest((root/'memes'/f'{slug}.md').read_text()) != ledger['entries'][slug]['body_hash']:
                raise ValueError('published entry changed; refuse overwrite')
        return {'status':'unchanged','batch':batch,'added':0}
    known = {}
    for p in (root/'memes').glob('*.md'):
        if p.name!='README.md':
            text=p.read_text();known[key(title(text))]=p.stem
            for alias in read_metadata(text).get('aliases',[]):known[key(alias)]=p.stem
    for slug, item in ledger['entries'].items():
        for alias in item.get('aliases',[]): known[key(alias)]=slug
    planned=[]
    for row in rows:
        slug=row['slug']; name=row['title']; body=row['markdown'].strip()
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',slug): raise ValueError('unsafe slug')
        if (root/'memes'/f'{slug}.md').exists(): raise ValueError('existing ID')
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
        body+='\n\n[시험 수록 목록](../collections/pilot-30.md)\n'
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
    collection='# 확장 시험 수록\n\n최근 유행 순위나 관찰 월이 아니라, 사전 확장 절차를 검증하기 위해 고른 한국에서 생성되었거나 독자적인 한국식 변형이 확인된 표본입니다. 해외 밈의 단순 국내 유행은 포함하지 않습니다.\n\n'
    collection+='\n'.join(f'- [{v["title"]}](../memes/{k}.md)' for k,v in ledger['entries'].items())+'\n'
    (root/'collections/pilot-30.md').write_text(collection)
    errors=check(root)
    if errors: raise ValueError('\n'.join(errors))
    return {'status':'applied','batch':batch,'added':len(rows),'total_pilot':len(ledger['entries'])}

def apply(root, input_path, batch):
    root=Path(root).resolve()
    with tempfile.TemporaryDirectory() as directory:
        stage=Path(directory)/'stage'
        shutil.copytree(root,stage,ignore=shutil.ignore_patterns('.git','__pycache__'))
        result=_apply(stage,input_path,batch)
        if result['status']=='unchanged': return result
        # Validate a whole batch before touching the working copy; ledger written last.
        files=[p for p in stage.rglob('*') if p.is_file()]
        files.sort(key=lambda p: p.relative_to(stage).as_posix()=='data/pilot-state.json')
        for p in files:
            dest=root/p.relative_to(stage)
            if dest.exists() and dest.read_bytes()==p.read_bytes():continue
            dest.parent.mkdir(parents=True,exist_ok=True)
            tmp=dest.with_name(dest.name+'.pilot-tmp')
            shutil.copy2(p,tmp);os.replace(tmp,dest)
        return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('input');p.add_argument('--batch',required=True);p.add_argument('--root',default=str(Path(__file__).resolve().parents[1]));a=p.parse_args()
    print(json.dumps(apply(a.root,a.input,a.batch),ensure_ascii=False))
