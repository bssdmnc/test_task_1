"""
conftest.py — fixtures + constants for the eval-task compliance harness.

Paths are relative to the repo root (one level up from test_task/).
The outer git repo is used for commit/file checks since ``base/`` is a
plain directory snapshot, not its own git clone.
"""

from __future__ import annotations

import csv
import io
import json
import subprocess
from pathlib import Path

import pytest

# ── Paths ──────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
BASE_DIR = REPO_ROOT / "base"
METADATA_JSON = BASE_DIR / ".agen-runtime" / "metadata.json"
METADATA_CSV = BASE_DIR / "metadata.csv"
PROBLEM_STATEMENT_MD = REPO_ROOT / "PROBLEM_STATEMENT.md"
PR_DESCRIPTION_MD = REPO_ROOT / "PR_DESCRIPTION.md"

# ── Git helpers ────────────────────────────────────────────────────

def _git(args: list[str], cwd: str | None = None) -> str:
    kw = dict(cwd=cwd or str(REPO_ROOT), text=True)
    return subprocess.check_output(["git", *args], **kw).strip()


def _rev(short: str) -> str:
    return _git(["rev-parse", short])


# Key SHAs (from the outer repo's git history):
#   407202b = base snapshot (before PR #740)
#   62de728 = [sol] commit (decorators only, no tests) on golden-solution branch
#   d048d18 = combined [sol]+[f2p] on origin/golden-solution (has both decorators AND tests)
#             [f2p] in the outer repo = the origin/golden-solution side that adds tests
# The actual [f2p] commit (where F2P tests were first introduced) is d048d18.
SHA_BASE = _rev("407202b")
SHA_SOL  = _rev("62de728")   # clean [sol]: decorators only
SHA_F2P  = _rev("d048d18")   # [f2p] = tests added (combined [sol]+[f2p] on origin)


def file_exists_at_sha(sha: str, rel_path: str) -> bool:
    try:
        _git(["cat-file", "-e", f"{sha}:{rel_path}"])
        return True
    except subprocess.CalledProcessError:
        return False


# ── CSV helpers ────────────────────────────────────────────────────

CSV_COLUMNS: list[str] = [
    "instance_id", "problem_statement", "problem_statement_variant", "hints",
    "repo", "repo_access", "license", "repo_path_or_url",
    "fail_to_pass", "pass_to_pass", "language", "docker_image_url",
    "docker_file", "base_commit", "golden_commit", "test_commit",
    "run_script", "task_category", "repo_category", "before_repo_set_cmd",
    "version", "container_mem", "container_memswap", "container_network_needed",
    "scenario", "sonnet_successes", "sonnet_avg_toolcalls",
    "sonnet_avg_loc_changed", "sonnet_avg_files_changed", "sonnet_avg_num_turns",
    "gemini_successes", "gemini_avg_toolcalls", "gemini_avg_loc_changed",
    "gemini_avg_files_changed", "gemini_avg_num_turns",
]

REQUIRED_JSON_FIELDS: list[str] = [
    "instance_id", "task_title", "problem_statement",
    "repo", "repo_path_or_url",
    "FAIL_TO_PASS", "PASS_TO_PASS",
    "language", "docker_file", "run_script",
    "task_type", "task_category", "repo_category",
    "version", "container_mem", "container_memswap",
    "container_network_needed",
]

F2P_TEST_NAMES: list[str] = [
    "BoundedReadHandleTest", "ConcatReadHandleTest", "FixedLengthReadHandleTest",
    "JoinedReadWriteHandleTest", "SinkReadHandleTest", "SinkReadWriteHandleTest",
    "SinkWriteHandleTest", "TeeWriteHandleTest", "TruncatedReadHandleTest",
]

P2P_TEST_NAMES: list[str] = [
    "StreamTest", "SpoolTest", "ReaderTest", "PipeTest",
    "MemoryHandleTest", "IterableReadHandleTest", "CopyTest", "CopyBidirectionalTest",
]

SOURCE_DECORATOR_NAMES: list[str] = [
    "BoundedReadHandle", "ConcatReadHandle", "FixedLengthReadHandle",
    "JoinedReadWriteHandle", "SinkReadHandle", "SinkReadWriteHandle",
    "SinkWriteHandle", "TeeWriteHandle", "TruncatedReadHandle",
]


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def csv_row() -> dict[str, str]:
    with open(METADATA_CSV, encoding="utf-8", newline="") as f:
        return next(csv.DictReader(f))


@pytest.fixture(scope="session")
def json_meta() -> dict[str, object]:
    with open(METADATA_JSON, encoding="utf-8") as f:
        raw = json.load(f)
    return raw[0] if isinstance(raw, list) else raw
