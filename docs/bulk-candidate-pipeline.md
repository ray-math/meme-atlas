# Bulk candidate queue

This read-only stage queues title-only candidates. It does not fetch article bodies,
change ledger statuses, promote entries, decide semantic duplicates, or certify
facts, independent evidence, safety or Korean usage.

Run from the repository:

```sh
python scripts/bulk_candidate_queue.py --check
python scripts/bulk_candidate_queue.py data/korea-candidates.json /tmp/new-export.json --check --output /tmp/new-queue.json
python -m unittest discover -s tests -p test_bulk_candidate_queue.py
```

Explicit inputs replace the default input list: include the legacy path when combining.
Output is stdout unless a **new** file under the system temporary directory,
outside the repository, is specified. Existing files are never overwritten.
No canonical, ledger, index or workflow files are generated.

## Input and identity
Each envelope requires integer schema_version=1 (boolean rejected) and candidates.
Legacy envelope source/comparison/scope and all other metadata are preserved.
Every row needs a globally unique nonempty id and title, one of unreviewed/held/
duplicate/included, dictionary_paths, evidence and notes arrays. aliases and
source_urls, if supplied, are arrays of nonempty strings. Parent/duplicate
references are null or nonempty non-self IDs; unresolved references are diagnostic,
not invented links. Unknown row fields are retained verbatim as provenance.

## Exact matching only
Canonical titles/aliases come from build_index.build(root); retired titles and
aliases come from pilot-state and must point to an active canonical path.
Normalization is imported directly from pilot_batch.key (NFKC, casefold,
non-word removal). Its underscore behavior is unchanged.

Classification precedence is duplicate_existing, duplicate_candidate, held,
needs_research. The first occurrence of a normalized candidate name wins according
to input file/row order. Every row remains in output, including duplicates.
Held rows remain held unless an exact match is available; original status is
always retained. Symbols that normalize to empty are held with a diagnostic.
Included status alone never establishes a duplicate: all linked paths must exist
in the actual canonical build and match a normalized title/alias (including
retired names). Stale/mismatched linkage is diagnostic, not silent promotion.

## Counts and reproducibility
The four exclusive classifications sum to total. indexed counts rows with a
nonempty normalized key; normalized_matches counts both duplicate classes.
Source groups distinguish legacy_existing (the repository's default ledger path)
from newly_collected (other exports). Export rows are **not** verified new memes.
A legacy queue of 1,091 rows with no export therefore has zero newly_collected rows.
canonical_count is the actual build size, never a fixed 357 assertion.
Full input-envelope and canonical/state fingerprints detect equal-count replacement.
--check repeats the read-only build and compares serialized outputs; it does not
establish semantic or factual accuracy. Determinism assumes the same ordered input
paths and unchanged files; absolute input paths are included in provenance.

## Review next
Inspect diagnostics, resolve semantic overlap manually, verify independent sources,
then use the existing reviewed importer separately. This tool grants no importer
approval. Synthetic tests cover 600 rows, duplicates, Unicode, retired aliases,
stale status, provenance, same-count changes, strict types and read-only behavior.
No actual Python/CI execution was performed while authoring this branch; CI must
run before integration. The 10-second synthetic test ceiling is a generous smoke
guard, not a production benchmark.
