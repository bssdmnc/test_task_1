# Original task (digest)

A general description of the methodology: how to turn a real pull request into an evaluation task for a coding AI agent. For specifics on our PR, see [README_EN.md](README_EN.md).

## Objective

Turn a real pull request into an evaluation task for a coding agent. Each task must:

- include the repository state **immediately before** the change was merged;
- define a deterministic execution environment (Docker);
- include a high-quality problem statement;
- include tests that validate the fix.

During evaluation the agent receives **only** the problem statement + the base repository, and implements the solution **independently**.

## What a task consists of

1. **Base repository state** — the repository frozen at the commit immediately before the original PR was merged. The change intended by the original PR is available separately as the "existing solution".
2. **Golden solution** — a clean, independent reimplementation of the fix; does not copy the original PR verbatim; quality no lower than the original.
3. **Execution environment** — Docker-based (the `.agen-runtime/` directory); ensures reproducible builds and test runs.
4. **Test partitioning:**
   - **Fail-to-Pass (F2P)** — validate the bug/missing feature; fail on the base commit; pass after the golden solution.
   - **Pass-to-Pass (P2P)** — existing tests unaffected by the change; pass both before and after (regression safeguards).
5. **Problem statement (LLM prompt)** — a structured, self-contained description of the problem; the agent's only input during evaluation.
6. **Metadata file** — `.agen-runtime/metadata.json`: problem statement, hints, and test mappings.

## Process

### Environment
The `.agen-runtime/` directory contains three core files:
- `Dockerfile.agen-runtime` — base image matching the repo's language, with dependency management;
- `run-tests-eval.sh` — script that builds the image and runs the tests;
- `metadata.json` — task metadata.

> If a Docker-setup seeding PR is provided — first review, approve, and merge it, and only then start the work.

### Solution development

Create the solution branch off the default branch:

```bash
git checkout <default-branch>   # main / master / dev
git pull
git checkout -b golden-solution
```

Bring in the existing solution so you have the original's full diff:

```bash
git checkout existing-solution -- .
```

Improve the solution using the original as your baseline:
- preserve correct logic and working parts;
- improve readability and structure;
- refactor where appropriate;
- handle edge cases more robustly.

The first commit must contain **only the implementation**, no tests (remove test changes from the patch):

```bash
git commit -am "[sol]: feature code"
```

### Docker fix policy
If Docker is broken: fix it on a separate `docker-golden-solution` branch, merge that into `main` first, then rebase the `golden-solution` branch onto the updated `main`.

### Validation
- Docker builds successfully and the tests run inside the container.
- **F2P:** fail before `[sol]` → pass after `[sol]`.
- **P2P:** pass both before and after.

## Commit structure

All work goes on the `golden-solution` branch, strictly in this order, with a mandatory prefix on every commit:

```
[sol]:  feature code         # isolated solution code (no tests or extraneous changes)
[f2p]:  fail to pass tests    # tests that fail on the base commit
[meta]: metadata.json         # problem statement, variants, test paths, hints
```

## Pull Request requirements

**Title:** `[GOLDEN SOLUTION] <original PR title>`

**The description must include:**
1. **Problem** — what was broken/missing.
2. **Approach** — how your solution works and why it is better than the original PR.
3. **Testing Strategy** — what behavior is validated and which edge cases are covered.

## Acceptance criteria

The task will be rejected if **any** of the following holds:
- Docker does not build or run the tests;
- F2P tests do not produce a strict "fail → pass" transition;
- P2P tests fail at any point;
- the problem statement is vague or incomplete;
- the golden solution is not a correct/complete solution to the statement;
- the commit structure/prefixes are incorrect;
- tests are flaky or non-deterministic.

## Evaluation model

The agent receives: the base repository (broken state) and **only** the `problem_statement`.
The agent does **not** see: your solution, your tests, the original PR.

Task quality is judged by whether the agent can: implement the fix, pass all F2P tests, and keep all P2P tests passing.

## Key principle

> You are not fixing a bug. You are designing a high-quality evaluation task that tests whether an AI can fix that bug.

## Delivery schema (CSV)

The data is delivered as a CSV. Minimal set of columns:

| Column | Explanation |
| --- | --- |
| `repo_url` | Full URL of the provided repository |
| `repo` | Full repository name |
| `instance_id` | Task identifier (usually the same as `repo`) |
| `base_commit` | Full 32-character SHA of the latest commit on the default branch |
| `test_commit` | Full 32-character SHA of the `[f2p]` commit (the fail-to-pass tests) |
| `pass_to_pass` | Comma-separated paths to P2P test files (from the repo root) |
| `fail_to_pass` | Comma-separated paths to F2P test files (from the repo root) |
| `problem_statement` | The contents of the LLM prompt |
| `problem_statement_variant` | A harder version of the prompt (as a non-technical person would phrase it) |
| `golden_commit` | Full 32-character SHA of the `[sol]` commit (the solution code) |

**Example** (placeholder values):

```csv
repo_url,repo,instance_id,base_commit,test_commit,pass_to_pass,fail_to_pass,problem_statement,golden_commit
<repo_url>,<repo>,<instance_id>,<base_commit_sha>,<test_commit_sha>,"<p2p_path_1>,<p2p_path_2>","<f2p_path_1>,<f2p_path_2>","<prompt text>",<golden_commit_sha>
```

> The extended format of the dataset's final row (the full set of columns, the Dockerfile/script contents, etc.) is described in [README_EN.md](README_EN.md), the "metadata.csv" section.
