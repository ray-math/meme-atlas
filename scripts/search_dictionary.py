"""Read-only lexical search. No LLM, embeddings, API, or popularity claims."""
import argparse,json,re,unicodedata
from pathlib import Path

def norm(value):return re.sub(r'[^\w]+','',unicodedata.normalize('NFKC',value).casefold())
def search(rows,query='',tags=(),limit=10):
 if not 1<=limit<=100:raise ValueError('limit must be between 1 and 100')
 terms=[norm(t) for t in query.split() if norm(t)];phrase=norm(query);hits=[]
 for row in rows:
  if not set(tags).issubset(set(row.get('tags',[]))):continue
  name=norm(row['title']);aliases=[norm(a) for a in row.get('aliases',[])];summary=norm(row.get('search_text',row.get('summary','')))
  if terms and not all(any(t in v for v in [name,*aliases,summary]) for t in terms):continue
  score=0
  if phrase:
   score=100 if name==phrase else 90 if phrase in aliases else 60 if name.startswith(phrase) else 40 if phrase in name else 30 if any(phrase in a for a in aliases) else 10
  hits.append(dict({k:v for k,v in row.items() if k!='search_text'},score=score))
 return sorted(hits,key=lambda h:(-h['score'],h['title'],h['id']))[:limit]

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('query',nargs='?',default='');p.add_argument('--tag',action='append',default=[]);p.add_argument('--limit',type=int,default=10);p.add_argument('--index',default=str(Path(__file__).resolve().parents[1]/'data/search-index.json'));a=p.parse_args()
 print(json.dumps(search(json.loads(Path(a.index).read_text()),a.query,a.tag,a.limit),ensure_ascii=False,indent=2))
