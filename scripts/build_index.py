"""Generate a deterministic, small read-only index from Markdown, not another source of truth."""
import json,re
from pathlib import Path
from check_dictionary import title
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
  rows.append({'id':p.stem,'title':title(text),'aliases':meta.get(p.stem,{}).get('aliases',[]),'summary':lines[0] if lines else '', 'path':f'memes/{p.name}'})
 return rows
if __name__=='__main__':
 (ROOT/'data').mkdir(exist_ok=True)
 (ROOT/'data/search-index.json').write_text(json.dumps(build(ROOT),ensure_ascii=False,indent=2)+'\n')
 print(f'Indexed {len(build(ROOT))} entries; lexical metadata only, not semantic ranking.')
