"""Read one canonical entry or section, without downloading the whole dictionary."""
import argparse
import json
import re
from pathlib import Path
from build_index import ROOT
from frontmatter import read
from check_dictionary import title

SECTIONS = {'definition': '뜻풀이', 'origin': '유래와 확산', 'related': '함께 쓰이는 밈'}

def get_entry(root, entry_id, section=None):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', entry_id):
        raise ValueError('invalid entry id')
    if section is not None and section not in SECTIONS:
        raise ValueError('unknown section')
    root = Path(root).resolve()
    path = (root / 'memes' / (entry_id + '.md')).resolve()
    if path.parent != (root / 'memes').resolve():
        raise ValueError('entry outside dictionary')
    text = path.read_text()
    chunks = re.split(r'^## (.+)\n', text, flags=re.M)
    sections = {chunks[i]: chunks[i+1].strip() for i in range(1, len(chunks), 2)}
    # Navigation to collections is not part of the definition/related entry text.
    sections = {k: re.sub(r'\n\[(?:시험 수록 목록|월별 목록)[^\n]*', '', v).strip() for k,v in sections.items()}
    result = {'schema_version': 1, 'id': entry_id, 'title': title(text), **read(text),
              'sections': {k: sections.get(v, '') for k,v in SECTIONS.items() if section is None or section == k}}
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('id')
    parser.add_argument('--section', choices=SECTIONS)
    args = parser.parse_args()
    try:
        print(json.dumps(get_entry(ROOT, args.id, args.section), ensure_ascii=False, indent=2))
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f'{exc}\n')
