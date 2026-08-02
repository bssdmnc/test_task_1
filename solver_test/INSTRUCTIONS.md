# How to test AGENTS.md / PROBLEM_STATEMENT.md as a solver would see them

This is a dry run of the "Operator runbook" section at the bottom of `AGENTS.md`:
build the exact fixture a grading solver receives, hand it to a fresh agent with
no memory of this authoring conversation, then grade the result with the hidden
F2P tests. It answers one question: **is `PROBLEM_STATEMENT.md` self-sufficient?**

Everything here is authoring-side tooling. Nothing in `solver_test/` is part of
the deliverable matrix and none of it may be copied into the fixture itself.

## Prerequisites

- Docker Desktop running (`docker version` should succeed). PHP/Composer are
  **not** required on the host — the Dockerfile in `.agen-runtime/` provides
  them inside the image.
- A clean git working tree (`git status --porcelain` empty). The build script
  refuses to run otherwise, per AGENTS.md's git-safety rule.

## Step 1 — Build the isolated fixture

```bash
bash solver_test/build_fixture.sh [output_dir]
# default output_dir: ../psl740-solver-fixture (a sibling of this repo, never committed)
```

This reproduces the fixture construction rules from AGENTS.md's operator
runbook:

- Copies `AGENTS.md` with the `===== AUTHORING BLOCK START/END =====` section
  removed (only the global rules, mode-identification text, the Solver Mode
  block, and the human-facing operator runbook survive).
- Copies `PROBLEM_STATEMENT.md` verbatim.
- Copies the monorepo tree **at the base commit** (the commit whose subject
  starts `base:`).

One non-obvious pitfall the script works around: `base/.gitattributes` marks
`config/`, `docs/`, `examples/`, `splitter/`, `var/`, and **every**
`packages/*/tests` directory as `export-ignore`. A plain `git archive` on the
base commit silently drops all of that — including every P2P test file. The
script uses `git checkout` into an alternate `--work-tree` instead, which
ignores `export-ignore`, then resets the index of *this* repo so the checkout
leaves no trace on your working tree.

The script also runs a leakage self-check: none of the nine solution classes,
none of the nine F2P test files, and none of the authoring-only docs
(`README*.md`, `IDEA.md`, `ORIGINAL_TASK*.md`, `PR_DESCRIPTION.md`,
`metadata.csv`, `test_task/`) should be reachable from the fixture root.

## Step 2 — (optional) sanity-check the fixture builds and P2P is green on base

```bash
cd ../psl740-solver-fixture
docker build -t psl740-base -f .agen-runtime/Dockerfile.agen-runtime .
docker run --rm psl740-base bash .agen-runtime/run-tests-eval.sh \
  "packages/io/tests/unit/StreamTest.php,packages/io/tests/unit/SpoolTest.php,packages/io/tests/unit/ReaderTest.php,packages/io/tests/unit/PipeTest.php,packages/io/tests/unit/MemoryHandleTest.php,packages/io/tests/unit/IterableReadHandleTest.php,packages/io/tests/unit/CopyTest.php,packages/io/tests/unit/CopyBidirectionalTest.php"
```

Expect all 8 P2P suites green and no trace of the 9 new classes. If this step
fails, the fixture itself is broken — fix that before wasting a solver run.

## Step 3 — Hand the fixture to a fresh solver agent

Start a **new** agent session (no memory of this conversation) whose only
input is the fixture directory — ideally with network access disabled, per
AGENTS.md's Solver Mode. Point it at the directory and tell it:

> Read `AGENTS.md` in this directory. You are in Solver Mode — follow the
> `===== SOLVER BLOCK START/END =====` section exactly. Your only authoritative
> input is `PROBLEM_STATEMENT.md`.

Do not give it anything else — no hints beyond what's in `PROBLEM_STATEMENT.md`,
no access to this repo, no access to the original PR.

## Step 4 — Freeze and diff

Once the solver agent exits, snapshot its tree (e.g. `git init && git add -A &&
git commit` inside a copy of the fixture, or just `diff -r` against the
pristine fixture) so you have a record of exactly what it changed before
injecting anything else.

## Step 5 — Inject F2P tests and grade

```bash
bash solver_test/grade.sh <path_to_solver's_finished_tree>
```

This copies the nine hidden F2P test files (and any fixture files they import)
from the `[f2p]` commit onto the solver's tree, builds a grading image, and
runs the F2P set and the P2P set separately inside containers.

## Step 6 — Interpret the result

- **F2P all pass, P2P all pass** → the problem statement is self-sufficient;
  the task bundle is sound.
- **F2P fails for the right reason** (assertion mismatch — wrong exception
  class, wrong EOF semantics, etc.) → likely a genuine spec gap. Find which
  contract card under-specified the behavior and tighten
  `PROBLEM_STATEMENT.md`, then rerun from Step 1 with a fresh solver.
- **F2P fails for the wrong reason** (class not found, fixture not found,
  autoload error) → tooling/fixture bug, not a solver failure. Check the
  fixture build, not the prompt.
- **P2P breaks** → the solver's implementation (or an ambiguity in the
  statement) caused a regression outside the nine new classes; investigate
  what in `PROBLEM_STATEMENT.md` implied it was safe to touch shared code.
- **Solver reports a leakage incident** → note the leak vector and close it
  in `build_fixture.sh` or in the AUTHORING BLOCK strip before rerunning.
