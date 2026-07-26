# AGENTS.md

## Project

PHP Standard Library (PSL) — composable IO handle decorators for `ReadHandleInterface`, `WriteHandleInterface`, and `ReadWriteHandleInterface`.

## Branch Structure

```
baac32f feat: add README_EN.md for task evaluation and deliverables (master)
  └── 8aa52a6 feat(io): add composable handle decorators ...
        └── dda0845 [sol]: add io handle decorators, test fixtures, and autoload wiring
              └── 42a6b54 [f2p]: add fail-to-pass io handle tests
                    └── 0b18061 [meta]: metadata.json + task docs
```

## Commit Convention

| Prefix | Content |
|--------|---------|
| `feat(io):` | Base snapshot of the library |
| `[sol]` | Solution code: source files, fixtures, config, autoload |
| `[f2p]` | Tests: F2P (fail on base, pass after [sol]) + P2P (pass always) |
| `[meta]` | Metadata: metadata.json, metadata.csv, Dockerfile, test_task |

## Running Tests

```bash
cd base
docker build -t golden-solution-test -f .agen-runtime/Dockerfile.agen-runtime .
docker run --rm golden-solution-test
```

## Key Files

- `base/packages/io/src/Psl/IO/` — 9 decorator classes
- `base/packages/io/tests/unit/` — F2P and P2P tests
- `base/packages/io/tests/fixture/` — test fixtures (NonCloseableWriteHandle, SlowWriteHandle)
- `base/.agen-runtime/metadata.json` — task metadata
- `base/metadata.csv` — dataset row
- `PROBLEM_STATEMENT.md` — problem statement for evaluation
- `PR_DESCRIPTION.md` — PR description

## F2P Tests (9)

- BoundedReadHandleTest.php
- ConcatReadHandleTest.php
- FixedLengthReadHandleTest.php
- JoinedReadWriteHandleTest.php
- SinkReadHandleTest.php
- SinkReadWriteHandleTest.php
- SinkWriteHandleTest.php
- TeeWriteHandleTest.php
- TruncatedReadHandleTest.php

## P2P Tests (8)

- StreamTest.php, SpoolTest.php, ReaderTest.php, PipeTest.php
- MemoryHandleTest.php, IterableReadHandleTest.php
- CopyTest.php, CopyBidirectionalTest.php
