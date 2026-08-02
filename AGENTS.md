# AGENTS.md — PR #740 evaluation task

This file is the single source of truth for any agent working on this repository. It is designed to be safely readable in two very different contexts:

- **Authoring Mode** — when the agent is at the task-bundle root and is helping the human operator finish the evaluation bundle (problem statement, golden solution, hidden F2P tests, metadata, compliance harness).
- **Solver Mode** — when the agent is inside the isolated fixture handed to it for clean-room evaluation. The only authoritative inputs are `PROBLEM_STATEMENT.md`, the visible repository contracts/tests, and the rules below.

Each mode block is delimited with `===== AUTHORING BLOCK START/END =====` and `===== SOLVER BLOCK START/END =====`. The solver block contains no golden source code, no test assertions, and no solution SHAs.

## Global rules (apply in both modes)

- **Scope.** This task is about `packages/io` in the `php-standard-library` PHP 8.4 monorepo. Keep changes inside `packages/io/src/Psl/IO/` and the visible test tree under `packages/io/tests/`. Do not pull in unrelated refactors from the upstream PR. Never touch `packages/http-client`, `packages/message`, or any other package out of scope.
- **Style.** Match the surrounding PHP 8.4 code (`declare(strict_types=1)`, `final` classes, `#[Override]`, constructor property promotion, `Psl\IO` interface contracts, `CloseHandleInterface` propagation, `AlreadyClosedException` after `close()`). Use the existing PHPUnit configuration and `composer.json` autoload mappings; only add a new autoload mapping if the absence provably blocks the work.
- **Class-name policy.** Expected class names and their behavioral contracts (constructor signature, method semantics, exception classes, edge-case rules) **belong** in `PROBLEM_STATEMENT.md` — README §10.1 requires the public contract of each class. What must never appear there: golden source code, exact assertion strings or expected messages copied from tests, test method bodies, and commit SHAs.
- **Tests.** Never delete, skip, or rewrite an existing test merely to make it pass. You may add your own files under the visible test tree, but must not alter assertions to accommodate broken behavior.
- **Git safety.** This workspace has uncommitted changes the operator values. Never run `git reset --hard`, `git clean`, destructive checkout/rebase, force-push, or branch deletion without explicit approval. Use `git stash push -u` to preserve dirty state before any destructive operation.
- **Determinism.** No flaky tests. No timing-dependent assertions. No reliance on external network or filesystem state outside the repo.
- **Do not stop early.** A run is finished only when every checklist item for the active mode is green, or when you are genuinely blocked. A partially completed deliverable set is a failed run — say so explicitly rather than reporting success.
- **Final report.** Every agent run must end with a short report describing what changed, why, what was verified, and any blockers or leakage incidents.

## Identifying the active mode

If you are at the task-bundle root and can see `README.md`, `README_EN.md`, `ORIGINAL_TASK*.md`, `PR_DESCRIPTION.md`, `IDEA.md`, `base/.agen-runtime/metadata.json`, `metadata.csv`, `test_task/`, `reports/`, or `.hermes/plans/`, you are in **Authoring Mode**.

If you are in a directory that contains only `AGENTS.md`, `PROBLEM_STATEMENT.md`, the upstream monorepo, and the visible P2P tests — and nothing under `reports/`, `metadata/`, `authoring/`, `golden/`, `test_task/`, or the original PR — you are in **Solver Mode**. Treat everything above the `===== SOLVER BLOCK START =====` line as if it does not exist.

If you are not sure which mode you are in, stop and ask the operator. Do not guess.

---

## ===== AUTHORING BLOCK START =====

Read-only authoring context is allowed here. If you are a solver, ignore this entire block.

### Authoring goal

Complete the evaluation task bundle described in `README.md` / `README_EN.md` / `ORIGINAL_TASK_EN.md`. Success is measured by one thing: **a fresh solver agent, given only `PROBLEM_STATEMENT.md` plus the base monorepo, implements the feature and the hidden F2P tests go red → green while P2P stays green.** Everything below serves that outcome.

### Deliverable matrix

Every row must be green before the run is finished. "Done when" is the acceptance test, not a description.

| # | Artifact | Path | Done when |
|---|---|---|---|
| 1 | Problem statement | `PROBLEM_STATEMENT.md` | Contains the README §10.1 sections and one behavioral contract card per new class; no golden code, no assertion strings, no SHAs; paths written as `packages/io/...` |
| 2 | Golden solution | `base/packages/io/src/Psl/IO/*.php` | All nine decorators implemented; P2P green; no tests or metadata in the same commit |
| 3 | Test fixtures + autoload | `base/packages/io/tests/fixture/`, `base/composer.json` | `Psl\IO\Tests\Fixture\` is registered in `autoload-dev` **in the base commit**; the fixtures themselves ship in `[f2p]` (see Phase 3) |
| 4 | F2P tests | `base/packages/io/tests/unit/*Test.php` (nine files) | Calibration table below passes in all four cells |
| 5 | PR description | `PR_DESCRIPTION.md` | Sections: Problem, Approach (incl. differences vs. the original PR), file table, Testing Strategy, Commit Structure with real SHAs |
| 6 | Runtime metadata | `base/.agen-runtime/metadata.json` | No `agen-core` placeholders; `FAIL_TO_PASS` / `PASS_TO_PASS` arrays filled; `problem_statement` matches `PROBLEM_STATEMENT.md`; `problem_statement_variant` written |
| 7 | Dataset row | `metadata.csv` (repo root — canonical) | 35 columns in README §7 order; **one physical line per record** — newlines inside fields written as the literal sequence `\n`, internal quotes doubled; real SHAs; evaluation-system metric columns empty |
| 8 | Docker runtime | `base/.agen-runtime/Dockerfile.agen-runtime` | Builds clean |
| 9 | Run script | `base/.agen-runtime/run-tests-eval.sh` | Runs the suite inside the image |
| 10 | Compliance harness | `test_task/` (`conftest.py`, `test_spec_compliance.py`, `pyproject.toml`, `README.md`) plus `csvcol.py` at the bundle root | `python -m pytest -q` green; authoring-side only, never shipped to the solver fixture |
| 11 | Commit topology | `golden-solution` branch | `base` → `[sol]` → `[f2p]` → `[meta]`, content allowlists respected |

**Canonical `metadata.csv` location is the repository root.** If the compliance harness or any doc expects `base/metadata.csv`, keep exactly one file and document which — never let two copies drift.

### Phase 0 — Mode confirmation and inventory

1. Confirm Authoring Mode by the markers listed above. The repo root is `/mnt/c/Users/nikit/code/task` (`c:\Users\nikit\code\task` from Windows) and the working branch is `golden-solution`. `base/` is a tracked subtree, not a separate repo.
2. **Re-read every artifact from disk before acting.** Prior reports, plans, and transcripts go stale; the working tree is the only truth. Check `git status` and `git log --oneline` to see what is actually committed versus merely present in the dirty tree.
3. Note any divergence from the remote (`git status -sb`) and raise it with the operator before rewriting history.
4. Do not run destructive git operations to "clean up" — stash if you need a clean tree.

### Phase 1 — Problem statement quality

The statement is the highest-leverage artifact: if a solver fails because of a spec gap, the whole bundle is rejected (README §9).

For each class the statement must give: the interface set it implements, the convenience trait(s) it uses, the constructor signature and parameter meaning, the semantics of each core operation (`read`/`tryRead`/`reachedEndOfDataSource` or `write`/`tryWrite`/`flush`), close/idempotency rules, and which `Psl\IO\Exception\*` class is thrown under which condition.

Behaviors that solvers systematically get wrong unless stated explicitly — verify each is present:

- The exception class for premature EOF and for size overflow (and, where a plausible-looking alternative exists in the package, that it is *not* the right one).
- The difference between a bounded read that rejects excess data and a truncated read that silently stops.
- Any probe/lookahead step required to distinguish "fit exactly" from "overflowed".
- Backpressure semantics for a mirroring write handle: what the return value means and when it is zero.
- The distinction between "returned empty because not ready" and "returned empty because end of data".
- Whether close propagates to underlying handles, and what happens on a second close.

Self-check before moving on: *could a competent PHP engineer implement each class from its card alone, without seeing the golden code or the tests?* If not, the card is incomplete.

Forbidden in the statement: golden source, exact expected-message strings from tests, test method bodies, commit SHAs, `base/` path prefixes (the solver's working directory is the monorepo root), and instructions to create the F2P test files.

### Phase 2 — Golden implementation, `[sol]` commit

Content allowlist for `[sol]`:

- `packages/io/src/Psl/IO/*.php` — the decorator sources, plus any strictly required production support.

Not allowed in `[sol]`: unit tests, test fixtures, metadata, task docs.

**Why fixtures do *not* belong in `[sol]`.** Grading runs against the *solver's* tree, which contains the solver's production code and nothing else — the solver is never asked to author fixtures. If a fixture that an F2P test imports lived only in `[sol]`, that test would die on a missing fixture class in every solver run, no matter how correct the implementation. Fixtures therefore ship in `[f2p]`, alongside the tests that consume them.

**Where the autoload mapping goes.** The `autoload-dev` entry for `Psl\IO\Tests\Fixture\` belongs in the **base commit**, not in `[sol]` or `[f2p]`. It is inert on base (it maps a directory with no files), it survives into the solver's tree untouched, and it is what lets the injected fixtures resolve at grading time. Putting it in a later commit means the solver's tree cannot autoload the fixtures at all.

General rule: **anything an F2P test needs at grading time, and that the solver is not asked to write, must be reachable from base + `[f2p]` alone — never from `[sol]`.**

Verify before committing — P2P must be green on `[sol]` alone, with the F2P tests not yet present:

```bash
cd base
composer install
./vendor/bin/phpunit -c config/phpunit.xml.dist \
  packages/io/tests/unit/StreamTest.php \
  packages/io/tests/unit/SpoolTest.php \
  packages/io/tests/unit/ReaderTest.php \
  packages/io/tests/unit/PipeTest.php \
  packages/io/tests/unit/MemoryHandleTest.php \
  packages/io/tests/unit/IterableReadHandleTest.php \
  packages/io/tests/unit/CopyTest.php \
  packages/io/tests/unit/CopyBidirectionalTest.php
```

### Phase 3 — F2P tests, `[f2p]` commit

Content allowlist for `[f2p]`: the nine `packages/io/tests/unit/*Test.php` files named in the statement's grading section, plus any fixture under `packages/io/tests/fixture/` that those tests import. Nothing else.

**Calibration gate (mandatory).** Record the actual counts from each cell in the authoring report; a claim without numbers does not count.

| Cell | Tree under test | Expected result |
|---|---|---|
| F2P on base | base tree + the nine F2P files only | **Fail** — for the right reason (class not found / behavior missing), not a fixture or autoload error |
| F2P on golden | `[sol]` + `[f2p]` | **Pass**, all nine |
| P2P on base | base tree, P2P files only | **Pass** |
| P2P on golden | `[sol]`, P2P files only | **Pass** |

Inspect the *reason* for every failure in the first cell, not just the count. If an F2P test fails on base with "fixture class not found" rather than "decorator class not found", the fixture placement is wrong — move the fixture into `[f2p]` and the autoload mapping into base. Do not paper over it: that failure mode is invisible in the golden run and hits every solver.

Test-writing rules: no timing assertions, no `sleep`, no randomness, no network. Each test must exercise the contract as documented in the statement, so that a solver who implemented to the spec passes. If a test asserts something the statement does not say, either the statement is incomplete (fix Phase 1) or the test is overreaching (fix the test).

### Phase 4 — Docs and metadata, `[meta]` commit

Content allowlist for `[meta]`: `base/.agen-runtime/metadata.json`, `metadata.csv`, `PROBLEM_STATEMENT.md`, `PR_DESCRIPTION.md`, and the other task-level docs.

**`metadata.json`** — fill every field per README §6: `instance_id`, `task_title`, `problem_statement` (byte-identical to `PROBLEM_STATEMENT.md`'s statement text), `problem_statement_variant`, `hints`, `repo`, `repo_path_or_url`, `FAIL_TO_PASS`, `PASS_TO_PASS`, `language`, `docker_file`, `run_script`, `task_type`, `task_category`, `repo_category`, `version`, `container_mem`, `container_memswap`, `container_network_needed` (`FALSE` — the io tests are all in-memory). No `agen-core` values may survive.

**`problem_statement_variant`** is a required, easy-to-forget field: a deliberately harder prompt phrased the way a non-technical stakeholder would ask for the same feature — no class names, no interface names. Write it; do not leave it equal to `problem_statement`.

**`metadata.csv` fill recipe:**

1. Take the SHAs from the real commits: `base_commit` = the base snapshot, `golden_commit` = `[sol]`, `test_commit` = `[f2p]` (`git rev-parse <ref>`).
2. `docker_file` and `run_script` hold the **entire file contents**, not paths — unlike `metadata.json`, where they are paths. This is the single most common mistake.
3. Escape per README §7, which is plain RFC 4180: wrap any field containing a comma, newline, or quote in `"…"`, and double every internal quote (`""`). The JSON arrays and the two file-content fields are therefore always quoted.

   On top of that, this bundle writes **one physical line per record**. Five fields are multi-line — `problem_statement`, `problem_statement_variant`, `hints`, `docker_file`, `run_script` — and their newlines are stored as the literal two-character sequence `\n`, so the whole file is exactly 2 lines: header + data. The dataset consumer reads the row line-by-line and would otherwise see column 2 split across hundreds of lines.

   Escape newlines only; leave backslashes alone. That is reversible here because no field contains a `\n` / `\r` / `\t` sequence of its own (checked: 0 occurrences against 21/8/49 lone backslashes in `problem_statement`/`docker_file`/`run_script`), and it keeps the two script fields visually identical to the real files. The binding requirement is the **round-trip**: un-escaping a field must reproduce its source byte for byte (`PROBLEM_STATEMENT.md`, `metadata.json`, `Dockerfile.agen-runtime`, `run-tests-eval.sh`), which is what the compliance harness asserts. Recover the text with `python csvcol.py metadata.csv problem_statement --unescape --full`.
4. `before_repo_set_cmd` = `git reset --hard <base_commit>`.
5. Leave the evaluation-system columns empty: `docker_image_url`, `scenario` (unless specified), and all ten `sonnet_*` / `gemini_*` metric columns.
6. The header has **35 columns** in the fixed order given in README §7. Note the CSV has `task_category` but no `task_type` column, while `metadata.json` has both — do not "helpfully" add a column. The two specs also disagree on the *value*: README §6 gives `metadata.json` `task_type: feature` and `task_category: io`, while README §7's CSV example puts `feature` in `task_category`. Follow each spec literally (CSV `task_category` = `feature`, JSON `task_category` = `io`) and leave the discrepancy for the dataset owner rather than silently reconciling it.
7. Validate with a real CSV parser — `python csvcol.py metadata.csv --list-cols` / `python csvcol.py metadata.csv problem_statement --len` (the helper sits at the bundle root, next to `metadata.csv`), or the compliance harness. A healthy file parses to exactly **2 rows × 35 fields** and is exactly **2 physical lines** (`wc -l` = 2 is a fair smoke check once newlines are escaped). Still **never** verify field *contents* with `cut -d,` or `awk -F,`: the fields contain commas and quotes, so character-level splitting stays wrong.

### Phase 5 — Verification gates (hard stop)

The run is not finished until every one of these is true and reported with evidence:

1. `docker build --no-cache -f base/.agen-runtime/Dockerfile.agen-runtime base/` succeeds.
2. `bash base/.agen-runtime/run-tests-eval.sh` runs the suite on the golden tree and succeeds.
3. All four cells of the Phase 3 calibration table produce the expected result.
4. `test_task/` compliance harness is green.
5. `metadata.json` ↔ `metadata.csv` ↔ git SHAs ↔ `PROBLEM_STATEMENT.md` all agree — same statement text, same F2P/P2P lists, same commit SHAs.
6. No unresolved placeholders anywhere in a deliverable: grep for `agen-core`, `<meta-sha>`, `<sha>`, `TODO`, `TBD`, `…`.
7. Commit topology check: `git log --oneline` shows `base` → `[sol]` → `[f2p]` → `[meta]`, and `git show --stat` for each commit shows only its allowlisted paths.
8. Clean-room dry run is possible: the operator can build the solver fixture from monorepo@base + `PROBLEM_STATEMENT.md` + the authoring-stripped `AGENTS.md`, with no authoring artifact reachable.

If the operator gives a terse instruction that overrides one of these rules (e.g. "unite the commits under the `[meta]` tag"), execute it and record the deviation in the report rather than re-litigating it.

### Authoring prohibitions

- Do not weaken, delete, or skip any test to make the suite appear green.
- Do not embed golden-solution code or expected test assertions in `PROBLEM_STATEMENT.md`.
- Do not leave unresolved placeholders in any final deliverable.
- Do not commit secrets, tokens, or `ghp_*` credentials anywhere in the repo.
- Do not ship `test_task/`, `README*.md`, `IDEA.md`, `ORIGINAL_TASK*.md`, or `PR_DESCRIPTION.md` into the solver fixture.

### Phase 6 — Authoring report

End the run with a report containing: what changed (file list), which gates were run and their actual output counts, the three commit SHAs, any operator override and why it was taken, any leakage incident, and — explicitly — which deliverable-matrix rows are still red.

## ===== AUTHORING BLOCK END =====

---

## ===== SOLVER BLOCK START =====

If you are reading this, you are the solver. The only authoritative inputs are `PROBLEM_STATEMENT.md` (in this directory) and the visible repository contracts/tests. Nothing in the authoring block above is allowed to influence your work.

### Solver identity

You are an autonomous coding agent. Your job is to implement the feature described in `PROBLEM_STATEMENT.md` so that hidden grading tests pass and the visible tests continue to pass.

### Inputs you may read

- `PROBLEM_STATEMENT.md` (authoritative).
- `AGENTS.md` (this file).
- The repository tree under the current working directory, including:
  - `packages/io/src/Psl/IO/` — interface contracts and existing handles.
  - `packages/io/tests/unit/` — visible tests; these are your regression guard.
  - `composer.json`, `config/phpunit.xml.dist`, `Justfile`, and other build files.
- Standard PHP/Composer toolchain: `php`, `composer`, `phpunit`.

### Inputs you must NOT consult

- Any Git history, remotes, tags, branches, or commit messages beyond what is present in the working tree.
- The web, including the upstream repository, its pull requests, Stack Overflow, or any documentation site.
- The original PR title, description, author, or diff.
- Any sibling or parent directory outside the fixture.
- Any report, metadata file, plan, scratchpad, or transcript from the authoring side.
- Any test file not committed to the visible tree.

If you discover or are told any of the above, treat it as a leakage incident: stop, record the leak vector in your final report, and stop using the leaked information.

### Scope: production code only

Implement the classes named in `PROBLEM_STATEMENT.md` under `packages/io/src/Psl/IO/`. **Do not write the grading tests** — they are supplied externally and your own versions would not be used. You may add scratch tests or fixtures for your own verification, but they are not a deliverable and must not modify or weaken anything already in the tree.

### Workflow

1. Read `PROBLEM_STATEMENT.md` end to end. The per-class contract cards are the specification — treat each bullet as a requirement, including the ones that look like implementation detail (exception classes, probe/lookahead steps, backpressure return values, close propagation). Those are exactly the points graded.
2. Study the existing `Psl\IO` interfaces, the convenience traits, and a reference implementation such as `MemoryHandle` to absorb the house style (closed-state assertion helper, `#[Override]`, `final`, `__destruct` calling `close()`).
3. Establish a baseline before changing anything — run the visible tests by explicit path:

   ```bash
   composer install
   ./vendor/bin/phpunit -c config/phpunit.xml.dist \
     packages/io/tests/unit/StreamTest.php \
     packages/io/tests/unit/SpoolTest.php \
     packages/io/tests/unit/ReaderTest.php \
     packages/io/tests/unit/PipeTest.php \
     packages/io/tests/unit/MemoryHandleTest.php \
     packages/io/tests/unit/IterableReadHandleTest.php \
     packages/io/tests/unit/CopyTest.php \
     packages/io/tests/unit/CopyBidirectionalTest.php
   ```

   All must pass before you start.
4. Implement the minimum change that satisfies the statement. Keep every edit inside `packages/io/src/Psl/IO/` — the task needs no build-file or configuration changes.
5. Re-run the same command. All visible tests must still pass.
6. Re-read each contract card against your implementation, line by line, before declaring done. A class that "works" but throws the wrong exception type or reports end-of-data at the wrong moment will fail grading.
7. Write `SOLVER_REPORT.md` (template below).

### Solver rules

- Make the smallest change that satisfies the spec. Do not refactor unrelated code.
- Do not weaken, skip, delete, or rewrite any existing test.
- Do not import from authoring-only, reports, metadata, plan, or scratchpad directories.
- Do not run destructive git operations.
- Do not add code that depends on network, timing, or externally seeded state.
- Do not add third-party dependencies.
- If you cannot complete the work, say so explicitly in the report and note exactly what blocked you.

### Final solver report (mandatory)

End your run with `SOLVER_REPORT.md` at the repository root containing:

- **Design.** A short paragraph on the approach and why it satisfies the spec.
- **Files changed.** Path list with a one-line description each.
- **Visible test results.** Exact command, counts, pass/fail summary.
- **Contract checklist.** For each class you implemented, one line confirming you matched the card (or noting where you deviated and why).
- **Limitations.** What you would do with more time, and any ambiguity you found in `PROBLEM_STATEMENT.md`.
- **Leakage incidents.** Any prohibited source you encountered and how you neutralized it.

## ===== SOLVER BLOCK END =====

---

## Operator runbook (for the human evaluator)

This section is for the human, not for any agent. It records how to use the two modes together.

1. Confirm the working tree is committed or safely stashed before any fixture construction.
2. Build the isolated solver fixture in a separate directory tree that cannot reach authoring artifacts. Copy **only**:
   - `AGENTS.md` — with everything between `===== AUTHORING BLOCK START =====` and `===== AUTHORING BLOCK END =====` removed. This strip is mandatory; the authoring block names the deliverable set and the calibration procedure.
   - `PROBLEM_STATEMENT.md`.
   - The monorepo at the base commit, including the visible P2P tests.

   Do not copy `README*.md`, `IDEA.md`, `ORIGINAL_TASK*.md`, `PR_DESCRIPTION.md`, `metadata.csv`, `test_task/`, `.agen-runtime/metadata.json`, or any `reports/` or plan directory.
3. Run a fresh agent process with network disabled and only the fixture path as input, instructing it to follow Solver Mode.
4. After the solver exits, freeze the working tree and capture the diff.
5. Inject the hidden F2P tests out of band — apply the `[f2p]` commit's nine test files onto the frozen worktree — then run both the F2P and P2P sets and grade the transition.
6. If the solver fails for reasons that point at the spec rather than its implementation, revise `PROBLEM_STATEMENT.md`, rebuild the fixture from the same base, and rerun with a fresh agent. Record which spec gap caused the failure.

**Canonical paths:** `metadata.csv` lives at the repository root. `metadata.json` lives at `base/.agen-runtime/metadata.json`. Keep one copy of each.
