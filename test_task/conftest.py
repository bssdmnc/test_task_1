"""Shared fixtures for the eval-task compliance suite.

Everything here is read-only: the harness inspects the committed bundle and the
git graph, it never mutates the repository.
"""

from __future__ import annotations

import csv
import io
import json
import pathlib
import subprocess

import pytest

# The 35 columns of metadata.csv, in the order fixed by README_EN section 7.
CSV_COLUMNS = [
    "instance_id", "problem_statement", "problem_statement_variant", "hints",
    "repo", "repo_access", "license", "repo_path_or_url", "fail_to_pass",
    "pass_to_pass", "language", "docker_image_url", "docker_file", "base_commit",
    "golden_commit", "test_commit", "run_script", "task_category", "repo_category",
    "before_repo_set_cmd", "version", "container_mem", "container_memswap",
    "container_network_needed", "scenario", "sonnet_successes",
    "sonnet_avg_toolcalls", "sonnet_avg_loc_changed", "sonnet_avg_files_changed",
    "sonnet_avg_num_turns", "gemini_successes", "gemini_avg_toolcalls",
    "gemini_avg_loc_changed", "gemini_avg_files_changed", "gemini_avg_num_turns",
]

# Columns the evaluation system fills in, which must be empty on delivery.
EVAL_SYSTEM_COLUMNS = [
    "docker_image_url", "sonnet_successes", "sonnet_avg_toolcalls",
    "sonnet_avg_loc_changed", "sonnet_avg_files_changed", "sonnet_avg_num_turns",
    "gemini_successes", "gemini_avg_toolcalls", "gemini_avg_loc_changed",
    "gemini_avg_files_changed", "gemini_avg_num_turns",
]

DECORATORS = [
    "ConcatReadHandle", "FixedLengthReadHandle", "BoundedReadHandle",
    "TruncatedReadHandle", "TeeWriteHandle", "JoinedReadWriteHandle",
    "SinkReadHandle", "SinkWriteHandle", "SinkReadWriteHandle",
]


@pytest.fixture(scope="session")
def repo_root() -> pathlib.Path:
    """The task-bundle root (the directory containing test_task/)."""
    return pathlib.Path(__file__).resolve().parent.parent


def _git_runner(cwd: pathlib.Path):
    def run(*args: str, check: bool = True) -> str:
        result = subprocess.run(
            ["git", "-C", str(cwd), *args],
            capture_output=True, text=True,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed ({result.returncode}): {result.stderr.strip()}"
            )
        return result.stdout.strip()
    return run


@pytest.fixture(scope="session")
def git(repo_root):
    """Run a git command in the bundle (wrapper) repo and return stripped stdout.

    Only the wrapper's own tracked files (metadata.csv, the docs) live in this
    repo's history. base/ is a separate repository with its own commits — use
    `git_base` for anything keyed by base_commit/golden_commit/test_commit.
    """
    return _git_runner(repo_root)


@pytest.fixture(scope="session")
def base_repo_root(repo_root) -> pathlib.Path:
    """base/ is not a subdirectory of the wrapper's history — it is its own git
    repository (its own .git, its own `main` and `golden-solution` branches),
    handed to the solver as the thing it clones and resets."""
    return repo_root / "base"


@pytest.fixture(scope="session")
def git_base(base_repo_root):
    """Run a git command inside base/'s own repository.

    base_commit/golden_commit/test_commit and every path in FAIL_TO_PASS /
    PASS_TO_PASS are relative to *this* repo's root (no `base/` prefix) — that
    root is what a solver's `git reset --hard <base_commit>` actually resets.
    """
    return _git_runner(base_repo_root)


@pytest.fixture(scope="session")
def csv_path(repo_root) -> pathlib.Path:
    """Canonical dataset row location: the bundle root (README_EN section 3)."""
    return repo_root / "metadata.csv"


@pytest.fixture(scope="session")
def csv_raw(csv_path) -> str:
    return csv_path.read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def csv_rows(csv_path) -> list[list[str]]:
    # newline="" keeps the newlines embedded in quoted fields intact.
    with csv_path.open("r", newline="", encoding="utf-8") as handle:
        return list(csv.reader(handle))


@pytest.fixture(scope="session")
def csv_row(csv_raw) -> dict[str, str]:
    return next(csv.DictReader(io.StringIO(csv_raw)))


@pytest.fixture(scope="session")
def meta(repo_root) -> dict:
    raw = (repo_root / "base" / ".agen-runtime" / "metadata.json").read_text(encoding="utf-8")
    parsed = json.loads(raw)
    return parsed[0] if isinstance(parsed, list) else parsed


@pytest.fixture(scope="session")
def meta_raw(repo_root) -> str:
    return (repo_root / "base" / ".agen-runtime" / "metadata.json").read_text(encoding="utf-8")


def as_list(value) -> list[str]:
    """metadata.json may store the test lists as arrays or as JSON strings."""
    if isinstance(value, list):
        return value
    return json.loads(value)


@pytest.fixture(scope="session")
def shas(meta) -> dict[str, str]:
    return {
        "base": meta["base_commit"],
        "golden": meta["golden_commit"],
        "test": meta["test_commit"],
    }
