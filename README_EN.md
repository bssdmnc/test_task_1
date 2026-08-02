# Task: golden solution for php-standard-library/php-standard-library PR #740

> This is an evaluation task for a coding AI agent. You are **not just implementing a feature** —
> you are designing a high-quality task that tests whether an AI can reproduce this change,
> given only the problem statement and the base repository as input.

---

## 1. What we improve

**Original PR:** <https://github.com/php-standard-library/php-standard-library/pull/740>
**Title:** `feat(io): add composable handle decorators (Concat, Joined, Tee, Truncated, Bounded, FixedLength, Iterable, Sink) and replace internal duplicates`

- **Language:** PHP 8.4 (Composer, PHPUnit)
- **Where the change is:** the `packages/io` package (new composable handle decorators in the `Psl\IO` namespace); plus refactors in `packages/http-client` and `packages/message`, where bespoke internal handle classes are replaced with the new reusable decorators.
- **Gist:** `Psl\IO` gains a set of **composable decorators** over `ReadHandleInterface` / `WriteHandleInterface` / `ReadWriteHandleInterface`: `ConcatReadHandle` (read several handles sequentially as one), `FixedLengthReadHandle` (read exactly N bytes), `BoundedReadHandle` (cap the total number of bytes read), `TruncatedReadHandle` (truncate to a maximum length), `TeeWriteHandle` (write to two handles at once), `JoinedReadWriteHandle` (join a read handle and a write handle into one read-write handle), and `Sink{Read,ReadWrite,Write}Handle` (sink wrappers). These decorators replace duplicate ad-hoc implementations that previously lived in `http-client` (H1/H2 body handles, `LimitedReadHandle`) and `message` (`ConcatenatedReadHandle`), consolidating stream-composition logic in one place.

Files touched by the original PR (for orientation — what to study and where to draw test candidates from):

| Production code | Tests |
| --- | --- |
| `packages/io/src/Psl/IO/ConcatReadHandle.php`, `FixedLengthReadHandle.php`, `BoundedReadHandle.php`, `TruncatedReadHandle.php`, `TeeWriteHandle.php`, `JoinedReadWriteHandle.php`, `SinkReadHandle.php`, `SinkReadWriteHandle.php`, `SinkWriteHandle.php` (new) | `packages/io/tests/unit/ConcatReadHandleTest.php`, `FixedLengthReadHandleTest.php`, `BoundedReadHandleTest.php`, `TruncatedReadHandleTest.php`, `TeeWriteHandleTest.php`, `JoinedReadWriteHandleTest.php`, `SinkReadHandleTest.php`, `SinkReadWriteHandleTest.php`, `SinkWriteHandleTest.php` (new) |
| `packages/io/src/Psl/IO/IterableReadHandle.php`, `MemoryHandle.php` (modified) | `packages/io/tests/fixture/NonCloseableWriteHandle.php`, `SlowWriteHandle.php` (new fixtures) |
| `packages/http-client/src/Psl/HTTP/Client/Internal/{H1/FixedLengthBodyHandle,H1/ResponseReader,H2/ResponseBodyHandle,LimitedReadHandle}.php`, `Exception/ProtocolException.php` (refactored onto the new decorators) | `packages/http-client/tests/unit/Internal/{H1/FixedLengthBodyHandle,H1/MisbehavingServer,H1/ResponseReader,LimitedReadHandle}Test.php` |
| `packages/message/src/Psl/Message/Internal/ConcatenatedReadHandle.php`, `serialize.php` (refactored) | (covered by existing `packages/message/tests/unit/` tests) |

> Note: the original PR was merged not into `main` but into the development branch `next`. For your task the starting point is the snapshot in `base/` (= `base_commit`, the state immediately before PR #740), and the PR's changes are the "existing solution" (see section 4).
>
> ⚠️ The PR is large and multi-package. The core of the change is the **decorators in `packages/io`**. It is acceptable (and recommended) to scope the statement to a self-contained, testable subset — e.g. the io decorators and their unit tests — while keeping all P2P green. The key requirement is that the statement be complete for the scope you choose (see section 3).

---

## 2. What you are given

- **[`base/`](base/)** — a snapshot of the php-standard-library repository at the commit **immediately before** PR #740 was merged (the initial state, `base_commit`). Full tree: `packages/*/src` and `packages/*/tests`, `config/` (including `config/phpunit.xml.dist`), `docs/`, `examples/`, `composer.json`/`composer.lock`. Branch/commit history is not set up — you build it yourself (see section 4).
- **[`base/.agen-runtime/`](base/.agen-runtime/)** — the deterministic environment for building and running the tests:
  - [`Dockerfile.agen-runtime`](base/.agen-runtime/Dockerfile.agen-runtime) — image based on `php:8.4-cli` (extensions `bcmath`, `intl`, `zip`, `brotli`, `sodium`; Composer); installs dependencies (`composer install`) and runs `phpunit -c config/phpunit.xml.dist`;
  - [`run-tests-eval.sh`](base/.agen-runtime/run-tests-eval.sh) — script: parses the test command from the Dockerfile, can run the full suite or a targeted list of files (for PHPUnit it runs `./vendor/bin/phpunit <files>`);
  - [`metadata.json`](base/.agen-runtime/metadata.json) — the task metadata template (currently filled with `agen-core` placeholders; you must fill it in).

---

## 3. Deliverables

The task folder (`00_tasks/task_04_php-standard-library__php-standard-library__740/`) must eventually contain:

1. **Golden solution** — a clean, independent reimplementation of the same change on the `golden-solution` branch with the correct commit structure (see section 4). Do not copy the original PR verbatim; quality must be no lower than the original.
2. **F2P tests** (Fail-to-Pass) — fail on the base commit (the functionality is missing), pass after `[sol]`.
3. **P2P tests** (Pass-to-Pass) — existing tests unaffected by the change; pass both before and after.
4. **`PROBLEM_STATEMENT.md`** — the problem statement for the agent. For what it must contain, see section 10.
5. **`PR_DESCRIPTION.md`** — the description of the golden-solution PR. For what it must contain, see section 10.
6. **A filled-in** [`base/.agen-runtime/metadata.json`](base/.agen-runtime/metadata.json) (see section 6).
7. **`metadata.csv`** — the task's final row in the dataset table format (see section 7).

> ⚠️ **The main acceptance criterion — the task is solved by the agent, not by you.**
>
> During evaluation the agent receives **only** `problem_statement` + the base repository (`base/`). It does **not** see your solution, your tests, or the original PR. Task quality is judged by whether **the agent itself**, given that input, can:
> - implement the change;
> - pass **all** F2P tests;
> - keep **all** P2P tests passing.
>
> **If the agent cannot solve the task from `problem_statement` + `base` and run the tests — the solution is NOT accepted.** Therefore the problem statement must be self-contained, unambiguous, and complete: everything needed to solve it must follow from the statement, with no reliance on the original PR or your explanations.

---

## 4. Process

### 4.1. Study the context
Read the original PR #740 and the related discussion, and understand the `Psl\IO` namespace: the `ReadHandleInterface` / `WriteHandleInterface` / `ReadWriteHandleInterface` interfaces, the existing handle classes and traits (`ReadHandleConvenienceMethodsTrait`, `WriteHandleConvenienceMethodsTrait`), and the semantics of `read`/`write`/`close`/`tryRead`. Look at how the bespoke handle wrappers in `http-client` and `message` are currently built — those are what the PR consolidates.

### 4.2. Branches and base commit
In `base/`, commit the initial snapshot as the base commit and create the solution branch:

```bash
git checkout <default-branch>      # the default branch
git pull
git checkout -b golden-solution
```

Bring in the original PR's changes as a starting point (your "existing solution") — so you have the original's full diff available:

```bash
git checkout existing-solution -- .
```

### 4.3. Improve the solution
Use the original as your baseline, but:
- preserve correct logic and working parts;
- improve readability and structure;
- refactor where appropriate;
- handle edge cases more robustly (empty handles, reads past the end, partial writes, close/double-close, zero length).

### 4.4. Code-only commit
The first commit must contain **only the implementation**, no tests:

```bash
git commit -am "[sol]: <short description of the change>"
```

### 4.5. Add tests and metadata
In separate commits — the F2P/P2P tests and the metadata.

---

## 5. Commit and PR structure

All commits go on the `golden-solution` branch, strictly in this order and with these prefixes:

| Commit | Contents |
| --- | --- |
| `base` | php-standard-library snapshot at the commit before PR #740 |
| `[sol]` | isolated solution code (no tests or extraneous changes) |
| `[f2p]` | tests that fail on base and pass after `[sol]` |
| `[meta]` | `metadata.json` (problem_statement, hints, test mappings) |

**PR requirements:**
- **Title:** `[GOLDEN SOLUTION] Add composable IO handle decorators`
- **Description** is written in `PR_DESCRIPTION.md` and must include:
  1. **Problem** — what was missing / duplicated on base;
  2. **Approach** — how your solution works and why it is better than the original PR;
  3. **Testing Strategy** — what behavior is validated and which edge cases are covered.

---

## 6. metadata.json — fields to fill in

Fill in [`base/.agen-runtime/metadata.json`](base/.agen-runtime/metadata.json), replacing the `agen-core` placeholders with real values.

| Field | Value for this task |
| --- | --- |
| `instance_id` | task identifier (e.g. `php-standard-library__php-standard-library__740`) |
| `task_title` | short task title |
| `problem_statement` | the statement text (same as in `PROBLEM_STATEMENT.md`) |
| `problem_statement_variant` | a harder version of the prompt (as a non-technical person would phrase it) |
| `hints` | hints: key files/places in the code |
| `repo` | `php-standard-library` |
| `repo_path_or_url` | URL of the provided repository |
| `FAIL_TO_PASS` | JSON array of F2P test paths from the repo root |
| `PASS_TO_PASS` | JSON array of P2P test paths |
| `language` | `PHP` |
| `docker_file` | `.agen-runtime/Dockerfile.agen-runtime` |
| `run_script` | `.agen-runtime/run-tests-eval.sh` |
| `task_type` | e.g. `feature` |
| `task_category` | e.g. `io` / `refactor` |
| `repo_category` | e.g. `standard-library` |
| `version` | `1` |
| `container_mem` / `container_memswap` | e.g. `4g` / `4g` |
| `container_network_needed` | `FALSE` for the io decorators (tests use in-memory handles); verify if you include http-client |

---

## 7. metadata.csv — the dataset's final row

In addition to `metadata.json`, the task is delivered as **a single row** in the shared dataset table (`metadata.csv`): a header row of columns + one data row for this task.

Differences from `metadata.json`:
- the `docker_file` and `run_script` columns hold the **full contents** of the files (not paths): the entire text of `.agen-runtime/Dockerfile.agen-runtime` and `.agen-runtime/run-tests-eval.sh`;
- commit SHAs (`base_commit`, `golden_commit`, `test_commit`), access/license fields, and a repo-reset command are added.

**CSV escaping rules:** a field containing a comma, newline, or double quote is wrapped in double quotes `"…"`; internal double quotes are doubled (`""`). That is why the JSON arrays in `fail_to_pass`/`pass_to_pass` and the multi-line `docker_file`/`run_script` are always quoted.

| Column | What to write | Who fills it |
| --- | --- | --- |
| `instance_id` | unique task ID (UUID or `php-standard-library__php-standard-library__740`) | candidate |
| `problem_statement` | same text as in `PROBLEM_STATEMENT.md` | candidate |
| `problem_statement_variant` | a harder version of the prompt | candidate |
| `hints` | hints (key files/places in the code) | candidate |
| `repo` | `php-standard-library` | candidate |
| `repo_access` | `public` | candidate |
| `license` | `MIT` | candidate |
| `repo_path_or_url` | URL of the provided repository | candidate |
| `fail_to_pass` | JSON array of F2P test paths | candidate |
| `pass_to_pass` | JSON array of P2P test paths | candidate |
| `language` | `PHP` | candidate |
| `docker_image_url` | URL of the built docker image (if produced by the pipeline) | pipeline / leave empty |
| `docker_file` | **full contents** of `.agen-runtime/Dockerfile.agen-runtime` | candidate |
| `base_commit` | SHA of the base commit (state before the PR) | candidate |
| `golden_commit` | SHA of the `[sol]` commit | candidate |
| `test_commit` | SHA of the `[f2p]` commit | candidate |
| `run_script` | **full contents** of `.agen-runtime/run-tests-eval.sh` | candidate |
| `task_category` | e.g. `feature` | candidate |
| `repo_category` | e.g. `standard-library` | candidate |
| `before_repo_set_cmd` | `git reset --hard <base_commit>` | candidate |
| `version` | `1` | candidate |
| `container_mem` / `container_memswap` | `4g` / `4g` | candidate |
| `container_network_needed` | `FALSE` / `TRUE` | candidate |
| `scenario` | `standard` / `hints` | evaluation system |
| `sonnet_successes`, `sonnet_avg_toolcalls`, `sonnet_avg_loc_changed`, `sonnet_avg_files_changed`, `sonnet_avg_num_turns` | model run metrics | evaluation system (leave empty) |
| `gemini_successes`, `gemini_avg_toolcalls`, `gemini_avg_loc_changed`, `gemini_avg_files_changed`, `gemini_avg_num_turns` | model run metrics | evaluation system (leave empty) |

**Header row** (column order is fixed):

```csv
instance_id,problem_statement,problem_statement_variant,hints,repo,repo_access,license,repo_path_or_url,fail_to_pass,pass_to_pass,language,docker_image_url,docker_file,base_commit,golden_commit,test_commit,run_script,task_category,repo_category,before_repo_set_cmd,version,container_mem,container_memswap,container_network_needed,scenario,sonnet_successes,sonnet_avg_toolcalls,sonnet_avg_loc_changed,sonnet_avg_files_changed,sonnet_avg_num_turns,gemini_successes,gemini_avg_toolcalls,gemini_avg_loc_changed,gemini_avg_files_changed,gemini_avg_num_turns
```

**Data row schema** (placeholder values; fill the `<…>` fields yourself, large fields shown schematically):

```csv
php-standard-library__php-standard-library__740,"<problem_statement>","<problem_statement_variant>","<hints>",php-standard-library,public,MIT,<repo_url>,"[""packages/io/tests/unit/<...>Test.php""]","[""packages/io/tests/unit/<...>Test.php""]",PHP,,"<full contents of Dockerfile.agen-runtime>",<base_commit>,<golden_commit>,<test_commit>,"<full contents of run-tests-eval.sh>",feature,standard-library,git reset --hard <base_commit>,1,4g,4g,FALSE,standard,,,,,,,,,,
```

---

## 8. Runtime and validation

Build and run from the `base/` root:

```bash
# Full test suite
bash .agen-runtime/run-tests-eval.sh

# Targeted run over a list of files (comma-separated; for PHPUnit it runs ./vendor/bin/phpunit <files>)
bash .agen-runtime/run-tests-eval.sh "packages/io/tests/unit/ConcatReadHandleTest.php,packages/io/tests/unit/TeeWriteHandleTest.php"
```

Be sure to verify:
- **Docker builds** from `Dockerfile.agen-runtime` and the tests run inside the container.
- **F2P tests:** fail **before** `[sol]` → pass **after** `[sol]` (a strict fail → pass transition).
- **P2P tests:** pass **both before and after** the solution.

> **Self-containment check (mandatory).** Give `problem_statement` + `base` to an independent person or agent **without showing** your solution, tests, or the original PR. They must arrive at a solution that passes F2P/P2P. If the change cannot be reproduced from the statement alone — improve `problem_statement`, otherwise the task is not accepted.

---

## 9. Acceptance criteria

The task will be **rejected** if any of the following holds:

- ❌ **the agent cannot reproduce the change and pass F2P/P2P given only `problem_statement` + `base` (without your solution, tests, or the original PR) — the solution is NOT accepted;**
- ❌ Docker does not build or run the tests;
- ❌ F2P tests do not produce a strict fail → pass transition;
- ❌ P2P tests fail at any point;
- ❌ the problem statement is vague or incomplete;
- ❌ the golden solution is not a correct/complete solution to the stated problem;
- ❌ the commit structure/prefixes are incorrect;
- ❌ tests are flaky or non-deterministic.

---

## 10. What the files must contain (templates)

Below is the structure of the two mandatory documents. Copy the template into the corresponding file and fill it with your own data.

### 10.1. `PROBLEM_STATEMENT.md`

A self-contained problem statement: from it the agent (and the reviewer) must understand **what** is missing/suboptimal and **exactly** what needs to be done, without seeing your solution or the original PR. It must contain the sections:

- **Title and header** — `instance_id`, `language`, `task_type`, `task_category`.
- **Problem Statement** — `Title`; `Current behavior` (how the code behaves on base, what is missing); `Reproduction steps` (how to reproduce/demonstrate the missing functionality); `Expected behavior` (what it should become after the change — in detail: which classes/files are introduced and the public contract of each: constructor, `read`/`write`/`close` behavior, edge cases); `Files to create/modify`; `Files NOT to touch`; `Constraints`.
- **Hints** — key files and code locations worth studying.
- **Test Files** — the Fail-to-Pass and Pass-to-Pass test lists.
- **Commits** — a table of the final commits (`base` → `[sol]` → `[f2p]` → `[meta]`).

````markdown
# Task: <short task title>

**instance_id:** `php-standard-library__php-standard-library__740`
**language:** PHP
**task_type:** feature
**task_category:** <e.g. io / refactor>

---

## Problem Statement

Title: <title>

Current behavior:
<how the code behaves now, on the base commit, what is missing / duplicated>

Reproduction steps:
1. <step>
2. <step>

Expected behavior:
<what it should be after the change; in detail — which classes/files are introduced,
the public contract of each (constructor, read/write/close, behavior at the boundaries),
which bespoke wrappers are replaced>

Files to create/modify:
- `packages/io/src/Psl/IO/<Class>.php` — <what is introduced/changes>

Files NOT to touch:
- <files/areas that must not be changed>

Constraints:
- <constraints: determinism, no breaking the public API of existing handles,
  compatibility with the Psl\IO interfaces, etc.>

---

## Hints

<key files and code locations worth studying before solving>

---

## Test Files

**Fail-to-Pass** (fail on base, pass after the solution):
- `packages/io/tests/unit/<...>Test.php`

**Pass-to-Pass** (pass both before and after):
- `packages/io/tests/unit/<...>Test.php`

---

## Commits

| SHA | Type | Message |
|-----|------|---------|
| `<sha>` | base | php-standard-library at the commit before PR #740 |
| `<sha>` | [sol] | <solution code> |
| `<sha>` | [f2p] | <fail-to-pass tests> |
| `<sha>` | [meta] | metadata.json |
````

### 10.2. `PR_DESCRIPTION.md`

The description of the golden-solution PR. It must contain the sections:

- **Title** — `# [GOLDEN SOLUTION] <task title>`.
- **Problem** — what was missing / duplicated on base.
- **Approach** — how your solution works; as a separate block — the key differences/improvements relative to the original PR; a table of changed files (`NEW`/`MOD`/`DEL`).
- **Testing Strategy** — the F2P/P2P lists and exactly what is covered (scenarios, edge cases).
- **Commit Structure** — the final commits `[sol]` → `[f2p]` → `[meta]`.

````markdown
# [GOLDEN SOLUTION] Add composable IO handle decorators

## Problem

<what was missing / duplicated on the base commit>

## Approach

<how your solution works>

Key decisions vs. the original PR:
- <how your solution differs from / improves on the original PR #740>

**Files changed:**

| Status | File |
| ------ | ---------------------------------- |
| NEW    | `packages/io/src/Psl/IO/<Class>.php` |
| MOD    | `packages/io/src/Psl/IO/<Class>.php` |

## Testing Strategy

**Fail-to-Pass** (`packages/io/tests/unit/<...>Test.php`):
- fail on base → pass after `[sol]`

**Pass-to-Pass** (regression safeguards, pass before and after):
- `packages/io/tests/unit/<...>Test.php`

<exactly what is covered: key scenarios and edge cases>

## Commit Structure

```
<sha> [sol]: <solution code>
<sha> [f2p]: <fail-to-pass tests>
<sha> [meta]: metadata.json
```
````

---

### Key principle

> You are not implementing a feature. You are designing a high-quality evaluation task that tests
> whether an AI can reproduce this change.
