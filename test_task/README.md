# php-standard-library PR #740 — eval-task deliverables & verification

This folder is the **compliance harness** for the eval-task bundle rooted at
`code/task/`. It is an authoring-side tool only: it never ships to a solver, and
it never mutates the repository.

Its job is to prove the deliverables agree with one another. The CSV row, the
runtime JSON, the git commit graph, and the two Markdown docs all describe the
same task; if any of them drifts, the bundle is silently broken in a way that
only shows up during grading. These tests fail instead.

## Deliverables (outside this folder)

| File | What it is |
|------|------------|
| `code/task/PROBLEM_STATEMENT.md` | canonical problem spec — the only doc a solver sees |
| `code/task/PR_DESCRIPTION.md` | golden-solution writeup |
| `code/task/metadata.csv` | 35-column dataset row — **canonical location is the bundle root** |
| `code/task/base/.agen-runtime/metadata.json` | JSON variant of the same spec |
| `code/task/base/` | the monorepo subtree; `golden-solution` carries `base → [sol] → [f2p] → [meta]` |
| `code/task/csvcol.py` | helper to extract a single CSV column robustly |

The three commit SHAs are recorded in `metadata.json` (`base_commit`,
`golden_commit`, `test_commit`) and mirrored in the CSV. Read them from there
rather than hardcoding — the harness does exactly that, which is why it does not
go stale when history is rebuilt.

## Reading a column out of metadata.csv

The row embeds whole Markdown documents and whole shell scripts inside quoted
fields, so it contains commas, quotes, and newlines *inside* values. **Never use
`cut -d,`, `awk -F,`, or `head`** — they shift every column and produce
confidently wrong answers. Parse it with a real CSV reader.

### Option A — `csvcol.py` (recommended)

```
python csvcol.py <file.csv> <column> [options]
```

`<column>` is a header name (`problem_statement`, `golden_commit`, …) or a
1-based index (`15`). Prefix with `@` to force name mode.

```
  --full        print the whole field (default previews 200 chars + length)
  --len         print only the length of the value
  --json        emit values as a JSON array
  --index       prefix each value with its row number (header = row 0)
  --row COL=VAL filter to rows where header COL equals VAL (repeatable)
  --list-cols   print header names + index, then exit
  --unescape    turn literal \n sequences into real newlines
```

Examples, run from `code/task/`:

```bash
# list all 35 columns and their positions
python csvcol.py metadata.csv --list-cols

# a single value by header name, or by 1-based index
python csvcol.py metadata.csv golden_commit
python csvcol.py metadata.csv 15

# the full statement, scoped to this instance
python csvcol.py metadata.csv problem_statement \
      --row instance_id=php-standard-library__php-standard-library__740 --full

# length only, handy for the big text fields
python csvcol.py metadata.csv problem_statement --len

# the F2P / P2P lists as a JSON array
python csvcol.py metadata.csv fail_to_pass --json
```

> **On `--unescape`:** this bundle stores **real newlines inside quoted fields**,
> which is what RFC 4180 and README_EN section 7 describe, so `--full` already
> byte-matches `PROBLEM_STATEMENT.md` and `--unescape` is unnecessary. The flag
> exists only for CSVs produced by older tooling that stored newlines as literal
> `\n` escape sequences. If you ever need it here, something has re-encoded the
> file and the round-trip test will already be failing.

### Option B — fallback without the helper

```bash
python -c "import csv,io,pathlib as p; \
r=next(csv.DictReader(io.StringIO(p.Path('metadata.csv').read_text(encoding='utf-8')))); \
print(r['golden_commit']); print('cols:', len(r))"
```

## What the harness compares

1. **CSV ↔ JSON** — same SHAs, same F2P/P2P lists.
2. **Spec ↔ git** — every SHA is a real commit in the right topological position;
   F2P files exist at `test_commit` and are absent at `base_commit`; the nine
   decorators exist at `golden_commit` and are absent at base; P2P files exist at
   base (otherwise they cannot be regression guards).
3. **Spec ↔ docs** — `PROBLEM_STATEMENT.md` is byte-equal to both the CSV
   `problem_statement` field and the JSON one; `PR_DESCRIPTION.md` cites SHAs that
   actually resolve to commits.

## Run it

```bash
cd code/task/test_task
python -m pytest -q        # 47 tests, all should pass
```

Coverage, by class in `test_spec_compliance.py`:

- **`TestCommitStructure`** — order `base → [sol] → [f2p] → [meta]`, exactly one
  `[sol]`, parent links, `[sol]` carries production code only, `[f2p]` carries
  tests plus the fixtures its tests import, and the fixture `autoload-dev`
  mapping lives in the base commit.
- **`TestMetadataJson`** — required fields present and non-empty, no `agen-core`
  placeholders, list shapes, network flag `FALSE`, and a
  `problem_statement_variant` that is neither a copy of the statement nor a leak
  of the class names.
- **`TestMetadataCsv`** — 35 columns in the fixed order, one data row, SHAs match
  the JSON, `docker_file`/`run_script` hold **contents** rather than paths,
  evaluation-system columns left empty, `before_repo_set_cmd` resets to base, and
  every field round-trips through a CSV parser byte-exactly.
- **`TestF2pP2p`** — the two lists agree across sources, counts are 9 and 8, and
  each file is present or absent at the commit where it should be.
- **`TestProblemStatement`** — required sections, byte-equality with both metadata
  copies, every decorator named, monorepo-relative paths (no `base/` prefixes),
  and no placeholders or pinned SHAs.
- **`TestPrDescription`** — required sections, golden-solution title, and cited
  SHAs that resolve to real commits (catches a stale SHA after a history rebuild).
- **`TestNoDuplicates`** — exactly one tracked `metadata.csv`, and no author-side
  doc reachable from inside `base/`, which is the tree a solver receives.
- **`TestNoCredentials`** — no tokens, keys, or secrets in the docs or metadata.

## File map

```
code/task/
├── PROBLEM_STATEMENT.md              canonical spec
├── PR_DESCRIPTION.md                 golden-solution writeup
├── metadata.csv                      35-column dataset row
├── csvcol.py                         CSV column extractor
├── base/
│   ├── .agen-runtime/metadata.json   JSON spec
│   ├── .agen-runtime/Dockerfile.agen-runtime
│   ├── .agen-runtime/run-tests-eval.sh
│   └── ...                           php-standard-library subtree
└── test_task/
    ├── README.md                     this file
    ├── conftest.py                   fixtures: CSV row, JSON, git, SHAs
    ├── test_spec_compliance.py       the checks
    └── pyproject.toml                pytest config
```
