"""Fail when committed derived navigation/search data no longer matches Markdown."""
import json
import tempfile
from pathlib import Path
from build_index import ROOT, build, write_topics

def check(root):
    root = Path(root)
    rows = build(root)
    expected = {'data/search-index.json': json.dumps(rows, ensure_ascii=False, indent=2) + '\n'}
    with tempfile.TemporaryDirectory() as directory:
        write_topics(directory, rows)
        expected['collections/topics.md'] = (Path(directory)/'collections/topics.md').read_text()
    return [name for name,text in expected.items() if not (root/name).exists() or (root/name).read_text() != text]

if __name__ == '__main__':
    stale = check(ROOT)
    if stale:
        raise SystemExit('Stale generated files: ' + ', '.join(stale) + '; run python scripts/build_index.py')
    print('Generated index and topics match canonical Markdown.')
