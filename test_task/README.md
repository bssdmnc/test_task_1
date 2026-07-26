# php-standard-library PR #740 — eval-task deliverables & verification

This folder (`test_task/`) is a **compliance harness** for the eval-task bundle
rooted at `code/task/`. It proves the deliverables are internally consistent:
the CSV, the JSON, the git commit graph, and the two Markdown docs must all agree.

## Deliverables (outside this folder)

| File | What it is |
|------|------------|
| `code/task/PROBLEM_STATEMENT.md` | canonical problem spec |
| `code/task/PR_DESCRIPTION.md` | golden-solution description |
| `code/task/base/` | git repo, golden-solution branch (`9dcb6be` → `[sol]` → `[f2p]` → `[meta]`) |
| `code/task/base/metadata.csv` | 35-column eval spec (the SWE-bench row) |
| `code/task/base/.agen-runtime/metadata.json` | JSON variant of the same spec |
| `code/task/csvcol.py` | helper to extract a single CSV column robustly |

## How to print a column VALUE from metadata.csv

`metadata.csv` has 35 columns and the `problem_statement` field contains an
embedded multi-line string (newlines + commas inside quotes). **Do NOT use
`cut -d,`** — it breaks on the embedded commas and shifts every column. Use the
dedicated helper instead.

### Option A — `csvcol.py` (recommended)

Usage: `python code/task/csvcol.py <file.csv> <column> [options]`

- `<column>` is a **header name** (`problem_statement`, `golden_commit`, …) or a
  **1-based index** (`15`).
- Prefix with `@` to force name mode when a name collides with a number: `@15`.

Common flags:

  --full        print the whole field (default previews 200 chars + length)
  --len         print only the byte/char length of the value
  --json        emit values as a JSON array
  --index       prefix each value with its row number (header = row 0)
  --row COL=VAL filter to rows where header COL equals VAL (repeatable)
  --list-cols   print header names + index, then exit

Examples:

  # list all 35 columns and their positions
  python code/task/csvcol.py code/task/base/metadata.csv --list-cols

  # print a single value by header name
  python code/task/csvcol.py code/task/base/metadata.csv golden_commit

  # same, by 1-based index (golden_commit is column 15)
  python code/task/csvcol.py code/task/base/metadata.csv 15

  # full problem_statement, scoped to this instance_id
  python code/task/csvcol.py code/task/base/metadata.csv problem_statement \
        --row instance_id=php-standard-library__php-standard-library__740 --full

  # length only (handy for big text fields)
  python code/task/csvcol.py code/task/base/metadata.csv problem_statement --len

  # the F2P / P2P test lists as a JSON array
  python code/task/csvcol.py code/task/base/metadata.csv fail_to_pass --json

### Option B — naive fallback when csvcol.py is missing

Read the whole row with Python's csv module and index by name:

  python - <<'PY'
  import csv
  with open('code/task/base/metadata.csv', encoding='utf-8') as f:
      row = next(csv.DictReader(f))
  print(row['golden_commit'])
  print('cols:', len(row))
  PY

This is exactly what the compliance fixtures use (see `conftest.csv_row`).

## How to COMPARE the values

The point of the harness is cross-source agreement. Three things must match:

1. **CSV ↔ JSON** — `metadata.csv` and `.agen-runtime/metadata.json` carry the
   same SHAs and the same F2P/P2P test lists.
2. **Spec ↔ git** — every SHA in the CSV/JSON must be a real commit, and the
   F2P/P2P files must exist (or not) at the right commit.
3. **Spec ↔ docs** — `PROBLEM_STATEMENT.md` text must equal the CSV
   `problem_statement` field (with `\n` escaped sequences unescaped).

### 1. CSV ↔ JSON (SHAs + test lists)

  python - <<'PY'
  import csv, json, io
  csv_raw = open('code/task/base/metadata.csv', encoding='utf-8').read()
  csv_row = next(csv.DictReader(io.StringIO(csv_raw)))
  meta = json.loads(open('code/task/base/.agen-runtime/metadata.json',
                          encoding='utf-8').read())
  # metadata.json may be a list wrapping one object
  meta = meta[0] if isinstance(meta, list) else meta

  print('base_commit :', csv_row['base_commit'], '==', meta['base_commit'],
        csv_row['base_commit'] == meta['base_commit'])
  print('golden_commit:', csv_row['golden_commit'], '==', meta['golden_commit'],
        csv_row['golden_commit'] == meta['golden_commit'])
  print('test_commit :', csv_row['test_commit'], '==', meta['test_commit'],
        csv_row['test_commit'] == meta['test_commit'])

  csv_f2p, csv_p2p = json.loads(csv_row['fail_to_pass']), json.loads(csv_row['pass_to_pass'])
  json_f2p, json_p2p = json.loads(meta['FAIL_TO_PASS']), json.loads(meta['PASS_TO_PASS'])
  print('F2P sets equal:', set(csv_f2p) == set(json_f2p), '(', len(csv_f2p), 'tests )')
  print('P2P sets equal:', set(csv_p2p) == set(json_p2p), '(', len(csv_p2p), 'tests )')
  PY

### 2. Spec ↔ git (commit existence + file presence)

  # do the three SHAs resolve to real commits?
  for h in 9dcb6be \
           7e8958d59bfe23a6778f00efa672dbc64b92e1bc \
           3cb1dcf0cf113e1f935156f010e0e372dacec336; do
    git -C code/task/base cat-file -t "$h"
  done

  # F2P test files must EXIST at test_commit (3cb1dcf) and be ABSENT at base
  for t in BoundedReadHandleTest ConcatReadHandleTest FixedLengthReadHandleTest \
           JoinedReadWriteHandleTest SinkReadHandleTest SinkReadWriteHandleTest \
           SinkWriteHandleTest TeeWriteHandleTest TruncatedReadHandleTest; do
    f="packages/io/tests/unit/$t.php"
    printf '%-32s at test: ' "$t"
    git -C code/task/base cat-file -e 3cb1dcf0cf113e1f935156f010e0e372dacec336:"$f" 2>/dev/null && echo -n OK || echo -n MISSING
    printf '  at base: '
    git -C code/task/base cat-file -e 9dcb6be:"$f" 2>/dev/null && echo PRESENT || echo absent
  done

  # source decorators must EXIST at golden_commit (7e8958d)
  for s in ConcatReadHandle FixedLengthReadHandle BoundedReadHandle TruncatedReadHandle \
           TeeWriteHandle JoinedReadWriteHandle SinkReadHandle SinkWriteHandle SinkReadWriteHandle; do
    f="packages/io/src/Psl/IO/$s.php"
    git -C code/task/base cat-file -e 7e8958d59bfe23a6778f00efa672dbc64b92e1bc:"$f" 2>/dev/null \
      && echo "OK  $s" || echo "MISSING $s"
  done

### 3. Spec ↔ docs (PROBLEM_STATEMENT.md equals CSV field)

The `problem_statement` field stores newlines as a **single-escaped** sequence —
one literal backslash followed by `n` (`\n`). Straight `csvcol --full` prints the
field **verbatim as stored** (with literal `\n`), so it will NOT byte-match the
`.md` (which has real newlines). Add `--unescape` to restore real newlines; the
output then equals the file content exactly:

  # direct, byte-equal to PROBLEM_STATEMENT.md (run from code/task):
  python code/task/csvcol.py code/task/base/metadata.csv problem_statement --full --unescape

  # or compare programmatically (default text mode, single-escape unescape):
  python - <<'PY'
  import csv, io
  csv_raw = open('code/task/base/metadata.csv', encoding='utf-8').read()
  csv_row = next(csv.DictReader(io.StringIO(csv_raw)))
  md = open('code/task/PROBLEM_STATEMENT.md', encoding='utf-8').read()
  csv_ps = csv_row['problem_statement'].replace('\\n', '\n')
  print('PROBLEM_STATEMENT.md == CSV problem_statement :', md.strip() == csv_ps.strip())
  PY

  # recommended equivalent, no heredoc quoting pitfalls (run from code/task):
  python -c "import csv,io,pathlib as p; r=next(csv.DictReader(io.StringIO(p.Path('base/metadata.csv').read_text(encoding='utf-8')))); m=p.Path('PROBLEM_STATEMENT.md').read_text(encoding='utf-8'); print('match:', r['problem_statement'].replace(chr(92)+'n', chr(10)).strip()==m.strip())"

This check is encoded as `TestMetadataCsv::test_problem_statement_matches_md`
and currently passes. If it ever fails, the cause is almost always a mismatched
escape level or a `newline=''` open — not a content divergence.

## Run the full compliance suite

All cross-source checks above are encoded as pytest tests in this folder.

  cd code/task/test_task
  python -m pytest -q        # 48 tests; 100% should pass

What it covers (see `test_spec_compliance.py`):

- `TestCommitStructure` — order `base → [sol] → [f2p] → [meta]`, single `[sol]`,
  `[sol]` carries no unit tests (fixtures allowed).
- `TestMetadataJson` — all required fields, no `agen-core` placeholders,
  F2P/P2P are arrays, network flag FALSE, files exist at HEAD / absent on base.
- `TestMetadataCsv` — exactly 35 columns in order, SHAs match JSON,
  `docker_file`/`run_script` non-empty, eval columns empty, CSV re-parses to 35.
- `TestProblemStatement` / `TestPrDescription` — required Markdown sections.
- `TestF2pP2p` — CSV lists == JSON lists, counts 9 F2P / 8 P2P.
- `TestNoDuplicates` — no stray `PROBLEM_STATEMENT.md`/`PR_DESCRIPTION.md` in
  `base/`, exactly one `metadata.csv`.
- `TestNoCredentials` — no tokens/secrets in the docs.

## File map

  code/task/
  ├── PROBLEM_STATEMENT.md          canonical spec
  ├── PR_DESCRIPTION.md             golden-solution writeup
  ├── csvcol.py                     CSV column extractor (this doc's Option A)
  ├── base/
  │   ├── metadata.csv              35-col eval spec
  │   ├── .agen-runtime/metadata.json   JSON spec
  │   └── ... (php-standard-library git repo, golden-solution branch)
  └── test_task/
      ├── README.md                 this file
      ├── conftest.py               fixtures + constants (paths, CSV_COLUMNS, REQUIRED_JSON_FIELDS)
      ├── test_spec_compliance.py   the 48 checks
      ├── pyproject.toml            pytest config
      └── .venv/                    pinned test env (pytest>=8)
