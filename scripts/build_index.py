"""Generate a deterministic, small read-only index from Markdown, not another source of truth."""
import json,re
from pathlib import Path
from check_dictionary import title
from frontmatter import read as read_metadata
ROOT=Path(__file__).resolve().parents[1]
def build(root):
 root=Path(root);state=root/'data/pilot-state.json';meta=json.loads(state.read_text())['entries'] if state.exists() else {}
 rows=[]
 for p in sorted((root/'memes').glob('*.md')):
  if p.name=='README.md':continue
  text=p.read_text();definition=text.split('## 뜻풀이',1)[1].split('\n## ',1)[0]
  lines=[x.strip() for x in definition.splitlines() if x.strip() and not x.startswith(('#','>','-'))]
  if not lines:
   lines=[re.sub(r'^#+\s*(?:\d+\.\s*)?','',x.strip()) for x in definition.splitlines() if x.strip().startswith('### ')]
  metadata=read_metadata(text)
  search_text=text[text.index('# '):].split('## 유래와 확산',1)[0]
  search_text=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',search_text)
  # Retired derivative names remain searchable, but are not asserted to be aliases.
  retired=[v['title'] for v in meta.values() if v.get('superseded_by')==p.stem]
  search_text+=' '+' '.join(retired)
  search_text=re.sub(r'\s+',' ',search_text).strip()
  rows.append({'id':p.stem,'title':title(text),'aliases':metadata.get('aliases',meta.get(p.stem,{}).get('aliases',[])),'tags':metadata.get('tags',[]),'summary':lines[0] if lines else '', 'search_text':search_text, 'path':f'memes/{p.name}'})
  if not rows[-1]['aliases']:rows[-1].pop('aliases')
 return rows
def write_topics(root,rows):
 root=Path(root);groups={}
 for row in rows:
  for tag in row.get('tags') or ['미분류']:groups.setdefault(tag,[]).append(row)
 lines=['# 분야·소재별 목록','','태그는 사용 상황이나 정서가 아닌 분야·소재입니다. 미분류는 억지로 분야를 지정하지 않은 항목입니다.','']
 for tag,items in sorted(groups.items()):
  lines.extend(['## '+tag,''])
  for row in sorted(items,key=lambda x:x['title']):lines.append(f"- [{row['title']}](../{row['path']})")
  lines.append('')
 (root/'collections').mkdir(exist_ok=True)
 (root/'collections/topics.md').write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
 (ROOT/'data').mkdir(exist_ok=True)
 (ROOT/'data/search-index.json').write_text(json.dumps(build(ROOT),ensure_ascii=False,indent=2)+'\n')
 write_topics(ROOT,build(ROOT))
 print(f'Indexed {len(build(ROOT))} entries; lexical metadata only, not semantic ranking.')
