# IDEA — golden-solution bundle for php-standard-library PR #740

## What this bundle is

An evaluation task for a coding agent, built from a real upstream PR
(`azjezz/php-standard-library#740`, `packages/io`). The agent receives only the
problem statement plus the pre-PR monorepo and must implement the feature in
isolation.

The goal is **not** to fix the upstream PR. The goal is to design a high-quality
assessment that measures whether an agent can implement the missing feature,
pass the hidden F2P tests, and keep all visible P2P tests green.

## Feature being assessed

`Psl\IO` currently lacks reusable decorators for composing stream handles; the
same wrapper logic is duplicated ad hoc across internal packages. The task
asks the agent to add a small family of composable decorator classes under
`packages/io/src/Psl/IO/`:

- `ConcatReadHandle` — sequential read from two handles.
- `FixedLengthReadHandle` — read exactly N bytes or fail on premature EOF.
- `BoundedReadHandle` — cap total bytes, detect overflow.
- `TruncatedReadHandle` — silently report EOF at a byte limit.
- `TeeWriteHandle` — mirror writes to two write handles.
- `JoinedReadWriteHandle` — join a read handle and a write handle.
- `SinkReadHandle`, `SinkWriteHandle`, `SinkReadWriteHandle` — `/dev/null`-style
  discard handles.

Scope is limited to the `io` package. `http-client` and `message` are out of
scope. Existing public APIs and convenience traits stay intact.

## Bundle structure

```
base/                                 tracked subtree — the upstream monorepo
  packages/io/src/Psl/IO/             ← agent edits here
  packages/io/tests/unit/             ← visible P2P tests (regression guard)
PROBLEM_STATEMENT.md                  ← spec the solver sees
PR_DESCRIPTION.md                     ← writeup of the golden solution
base/.agen-runtime/metadata.json      ← task metadata
base/.agen-runtime/Dockerfile.*       ← deterministic runtime
base/.agen-runtime/run-tests-eval.sh  ← build + test harness
metadata.csv                          ← dataset row
test_task/                            ← authoring-only compliance harness
golden-solution branch                ← [sol] / [f2p] / [meta] commits
```

## Commit topology (golden-solution branch)

| SHA      | Tag   | Contents                                                    |
| -------- | ----- | ----------------------------------------------------------- |
| base     | [base]| php-standard-library snapshot immediately before PR #740    |
| base     | [base]| src, `config/phpunit.xml.dist`, the P2P tests, and the inert `Psl\IO\Tests\Fixture\` autoload-dev mapping |
| sol      | [sol] | decorator sources only                                       |
| f2p      | [f2p] | the nine hidden F2P test files **and the fixtures they import** |
| meta     | [meta]| `metadata.json`, `metadata.csv`, `PROBLEM_STATEMENT.md`, …  |

The `[sol]` commit must contain **no tests, no fixtures, and no metadata**, so a
clean-room agent run can be graded purely on the F2P delta vs. P2P stability.

Fixtures ship in `[f2p]`, not `[sol]`, because grading runs against the
*solver's* tree — which has the solver's production code and nothing else. A
fixture that lived only in `[sol]` would be missing at grading time and would
fail `TeeWriteHandleTest` in every solver run regardless of implementation
quality. The `autoload-dev` mapping goes in the **base** commit so the injected
fixtures can actually resolve in the solver's tree.

Rule: anything an F2P test needs at grading time, and that the solver is not
asked to write, must be reachable from base + `[f2p]` alone.

## How an agent is evaluated

1. The authoring block above is stripped. The agent only sees
   `PROBLEM_STATEMENT.md`, the visible P2P tests under
   `packages/io/tests/unit/`, and the unmodified monorepo.
2. The agent edits `packages/io/src/Psl/IO/` to implement the decorators.
3. We then drop in the hidden F2P tests from the `[f2p]` commit and run the
   PHPUnit suite inside the Docker runtime.
4. Pass criterion: every F2P test transitions from red → green, every P2P
   test stays green.

## Authoring safeguards

- No weakening, skipping, or rewriting existing tests to make them pass.
- No golden-solution code, exact test assertions, expected message strings, or
  commit SHAs leaked into `PROBLEM_STATEMENT.md`. Class names and their
  behavioral contracts (constructor, `read`/`write`/`close` semantics, exception
  classes, edge cases) are **required** there — README §10.1 mandates the public
  contract of each class, and a solver cannot hit the F2P targets without them.
- All edits to the `base/` subtree stay localized to `packages/io/`.
- Docker build + full test suite must run end-to-end (`run-tests-eval.sh`).
- Never run `git reset --hard`, `git clean`, or any destructive operation
  on dirty state without explicit approval — the workspace has uncommitted
  changes the operator values.

## Key files for an authoring agent

- `AGENTS.md` — single source of truth; contains the Authoring vs. Solver
  block split.
- `README.md` / `README_EN.md` — methodology, schema for `metadata.csv`.
- `ORIGINAL_TASK.md` / `ORIGINAL_TASK_EN.md` — condensed upstream brief.
- `test_task/README.md` — requirements for the authoring-side compliance
  harness.
