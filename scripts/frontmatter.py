"""Small, explicit YAML subset for list metadata (inline JSON or dash lists)."""
import json
ALLOWED_TAGS={'애니','게임','방송','음악','인터넷방송','영화','광고','스포츠','연예','소비','AI','음식'}
def validate(meta):
 for name in ('tags','aliases'):
  values=meta.get(name,[])
  if not isinstance(values,list) or any(not isinstance(v,str) or not v.strip() for v in values):raise ValueError(name+' must be a string list')
  if len(values)!=len(set(values)):raise ValueError('duplicate '+name)
 if set(meta.get('tags',[]))-ALLOWED_TAGS:raise ValueError('tags must describe a reviewed domain, not a situation')
 return meta

def read(text):
 if not text.startswith('---\n'):return {}
 if '\n---\n' not in text[4:]:raise ValueError('unclosed frontmatter')
 raw=text[4:].split('\n---\n',1)[0];meta={};key=None
 for line in raw.splitlines():
  if not line.strip():continue
  if line.lstrip().startswith('- ') and key:
   value=line.strip()[2:].strip();meta[key].append(value.strip('\"\''));continue
  if ':' not in line:raise ValueError('invalid frontmatter line')
  key,value=line.split(':',1);key=key.strip();value=value.strip()
  if key not in ('tags','aliases'):key=None;continue
  if key in meta:raise ValueError('duplicate metadata field')
  meta[key]=json.loads(value) if value else []
 return validate(meta)

def render(tags,aliases):
 meta=validate({'tags':tags,'aliases':aliases});lines=['---','tags: '+json.dumps(tags,ensure_ascii=False)]
 if aliases:lines.append('aliases: '+json.dumps(aliases,ensure_ascii=False))
 return '\n'.join(lines)+'\n---\n\n'
