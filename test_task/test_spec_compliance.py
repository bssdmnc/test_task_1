"""
test_spec_compliance.py — 48 checks for the eval-task deliverables.

Run from test_task/:
    python -m pytest -q
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import pytest

from conftest import (
    BASE_DIR,
    CSV_COLUMNS,
    F2P_TEST_NAMES,
    METADATA_CSV,
    METADATA_JSON,
    P2P_TEST_NAMES,
    PR_DESCRIPTION_MD,
    PROBLEM_STATEMENT_MD,
    REPO_ROOT,
    REQUIRED_JSON_FIELDS,
    SHA_BASE,
    SHA_F2P,
    SHA_SOL,
    SOURCE_DECORATOR_NAMES,
    _git,
    file_exists_at_sha,
)


# ═══════════════════════════════════════════════════════════════════
# TestCommitStructure — base → [sol] → [f2p] → [meta]
# ═══════════════════════════════════════════════════════════════════

class TestCommitStructure:

    def test_base_commit_exists(self):
        assert SHA_BASE, "base SHA could not be resolved"

    def test_sol_commit_exists(self):
        assert SHA_SOL, "[sol] SHA could not be resolved"

    def test_f2p_commit_exists(self):
        assert SHA_F2P, "[f2p] SHA could not be resolved"

    def test_sol_follows_base(self):
        """[sol] must be a descendant of base."""
        mb = _merge_base(SHA_BASE, SHA_SOL)
        assert mb == SHA_BASE, (
            f"[sol] ({SHA_SOL[:8]}) is not a descendant of base ({SHA_BASE[:8]})"
        )

    def test_f2p_follows_base(self):
        """[f2p] must be a descendant of base."""
        mb = _merge_base(SHA_BASE, SHA_F2P)
        assert mb == SHA_BASE, (
            f"[f2p] ({SHA_F2P[:8]}) is not a descendant of base ({SHA_BASE[:8]})"
        )

    def test_sol_has_no_unit_test_files(self):
        """The [sol] commit must not introduce any files in packages/io/tests/unit/."""
        added = _git_diff_names(SHA_BASE, SHA_SOL)
        test_files = [f for f in added if "packages/io/tests/unit/" in f]
        assert test_files == [], (
            f"[sol] introduced unit test files: {test_files}"
        )

    def test_f2p_introduces_all_f2p_tests(self):
        """The [f2p] commit must introduce all F2P test files."""
        added = _git_diff_names(SHA_BASE, SHA_F2P)
        for name in F2P_TEST_NAMES:
            expected = f"base/packages/io/tests/unit/{name}.php"
            assert expected in added, (
                f"[f2p] is missing {name}.php"
            )

    def test_sol_introduces_all_decorators(self):
        """The [sol] commit must introduce all decorator source files."""
        added = _git_diff_names(SHA_BASE, SHA_SOL)
        for name in SOURCE_DECORATOR_NAMES:
            expected = f"base/packages/io/src/Psl/IO/{name}.php"
            assert expected in added, (
                f"[sol] is missing {name}.php"
            )


def _merge_base(a: str, b: str) -> str:
    import subprocess
    return subprocess.check_output(
        ["git", "merge-base", a, b], cwd=str(REPO_ROOT), text=True
    ).strip()


def _git_diff_names(a: str, b: str) -> list[str]:
    import subprocess
    out = subprocess.check_output(
        ["git", "diff", "--name-only", a, b], cwd=str(REPO_ROOT), text=True
    )
    return [l for l in out.splitlines() if l]


# ═══════════════════════════════════════════════════════════════════
# TestMetadataJson
# ═══════════════════════════════════════════════════════════════════

class TestMetadataJson:

    def test_file_exists(self):
        assert METADATA_JSON.exists(), f"{METADATA_JSON} not found"

    def test_valid_json(self):
        raw = json.loads(METADATA_JSON.read_text(encoding="utf-8"))
        assert isinstance(raw, (list, dict)), "metadata.json must be a JSON object or array"

    def test_no_agen_core_placeholders(self, json_meta: dict):
        text = json.dumps(json_meta)
        assert "agen-core" not in text, "metadata.json still contains agen-core placeholders"

    def test_required_fields_present(self, json_meta: dict):
        missing = [f for f in REQUIRED_JSON_FIELDS if f not in json_meta]
        assert missing == [], f"missing fields: {missing}"

    def test_fail_to_pass_is_list(self, json_meta: dict):
        val = json_meta["FAIL_TO_PASS"]
        if isinstance(val, str):
            items = [x.strip() for x in val.split(",") if x.strip()]
        else:
            items = val
        assert len(items) == len(F2P_TEST_NAMES), (
            f"expected {len(F2P_TEST_NAMES)} F2P tests, got {len(items)}"
        )

    def test_pass_to_pass_is_list(self, json_meta: dict):
        val = json_meta["PASS_TO_PASS"]
        if isinstance(val, str):
            items = [x.strip() for x in val.split(",") if x.strip()]
        else:
            items = val
        assert len(items) == len(P2P_TEST_NAMES), (
            f"expected {len(P2P_TEST_NAMES)} P2P tests, got {len(items)}"
        )

    def test_network_flag_false(self, json_meta: dict):
        assert json_meta["container_network_needed"].lower() == "false"

    def test_f2p_files_exist_at_f2p_commit(self, json_meta: dict):
        """Every F2P test file must exist at the [f2p] commit."""
        val = json_meta["FAIL_TO_PASS"]
        paths = [x.strip() for x in val.split(",") if x.strip()]
        for path in paths:
            # In the outer repo, paths are prefixed with base/
            outer = f"base/{path}"
            assert file_exists_at_sha(SHA_F2P, outer), (
                f"F2P file {path} missing at [f2p] commit"
            )

    def test_f2p_files_absent_at_base(self, json_meta: dict):
        """No F2P test file may exist at the base commit."""
        val = json_meta["FAIL_TO_PASS"]
        paths = [x.strip() for x in val.split(",") if x.strip()]
        for path in paths:
            outer = f"base/{path}"
            assert not file_exists_at_sha(SHA_BASE, outer), (
                f"F2P file {path} should NOT exist at base commit"
            )

    def test_source_files_exist_at_sol(self):
        """Every decorator source file must exist at the [sol] commit."""
        for name in SOURCE_DECORATOR_NAMES:
            path = f"base/packages/io/src/Psl/IO/{name}.php"
            assert file_exists_at_sha(SHA_SOL, path), (
                f"Source file {name}.php missing at [sol] commit"
            )

    def test_source_files_absent_at_base(self):
        """No decorator source file may exist at the base commit."""
        for name in SOURCE_DECORATOR_NAMES:
            path = f"base/packages/io/src/Psl/IO/{name}.php"
            assert not file_exists_at_sha(SHA_BASE, path), (
                f"Source file {name}.php should NOT exist at base commit"
            )


# ═══════════════════════════════════════════════════════════════════
# TestMetadataCsv
# ═══════════════════════════════════════════════════════════════════

class TestMetadataCsv:

    def test_file_exists(self):
        assert METADATA_CSV.exists(), f"{METADATA_CSV} not found"

    def test_exactly_35_columns(self, csv_row: dict):
        assert len(csv_row) == 35, f"expected 35 columns, got {len(csv_row)}"

    def test_columns_in_order(self, csv_row: dict):
        assert list(csv_row.keys()) == CSV_COLUMNS

    def test_golden_commit_non_empty(self, csv_row: dict):
        assert csv_row["golden_commit"], "golden_commit is empty"

    def test_test_commit_non_empty(self, csv_row: dict):
        assert csv_row["test_commit"], "test_commit is empty"

    def test_docker_file_non_empty(self, csv_row: dict):
        assert csv_row["docker_file"], "docker_file is empty"

    def test_run_script_non_empty(self, csv_row: dict):
        assert csv_row["run_script"], "run_script is empty"

    def test_eval_columns_empty(self, csv_row: dict):
        eval_cols = [c for c in csv_row if c.startswith("sonnet_") or c.startswith("gemini_")]
        empty = [c for c in eval_cols if csv_row[c].strip()]
        assert empty == [], f"eval columns should be empty: {empty}"

    def test_csv_round_trips(self):
        """Re-parse CSV and verify it produces exactly 1 row with 35 cols."""
        with open(METADATA_CSV, encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1, f"expected 1 data row, got {len(rows)}"
        assert len(rows[0]) == 35, f"expected 35 columns, got {len(rows[0])}"

    def test_problem_statement_matches_md(self, csv_row: dict):
        md = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        csv_ps = csv_row["problem_statement"].replace("\\n", "\n")
        assert md.strip() == csv_ps.strip(), (
            "PROBLEM_STATEMENT.md does not match CSV problem_statement"
        )

    def test_instance_id_value(self, csv_row: dict):
        assert csv_row["instance_id"] == "php-standard-library__php-standard-library__740"


# ═══════════════════════════════════════════════════════════════════
# TestProblemStatement
# ═══════════════════════════════════════════════════════════════════

class TestProblemStatement:

    def test_file_exists(self):
        assert PROBLEM_STATEMENT_MD.exists()

    def test_has_title(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert re.search(r"^# Task:", content, re.MULTILINE), "missing '# Task:' heading"

    def test_has_problem_statement_section(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert "## Problem Statement" in content

    def test_has_files_to_create(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert "Files to create" in content

    def test_has_constraints(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert "Constraints" in content

    def test_has_f2p_section(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert "Fail-to-Pass" in content

    def test_has_p2p_section(self):
        content = PROBLEM_STATEMENT_MD.read_text(encoding="utf-8")
        assert "Pass-to-Pass" in content


# ═══════════════════════════════════════════════════════════════════
# TestPrDescription
# ═══════════════════════════════════════════════════════════════════

class TestPrDescription:

    def test_file_exists(self):
        assert PR_DESCRIPTION_MD.exists()

    def test_has_golden_solution_heading(self):
        content = PR_DESCRIPTION_MD.read_text(encoding="utf-8")
        assert "GOLDEN SOLUTION" in content

    def test_has_problem_section(self):
        content = PR_DESCRIPTION_MD.read_text(encoding="utf-8")
        assert "## Problem" in content

    def test_has_approach_section(self):
        content = PR_DESCRIPTION_MD.read_text(encoding="utf-8")
        assert "## Approach" in content

    def test_has_testing_strategy(self):
        content = PR_DESCRIPTION_MD.read_text(encoding="utf-8")
        assert "## Testing Strategy" in content

    def test_has_commit_structure(self):
        content = PR_DESCRIPTION_MD.read_text(encoding="utf-8")
        assert "## Commit Structure" in content


# ═══════════════════════════════════════════════════════════════════
# TestF2pP2p
# ═══════════════════════════════════════════════════════════════════

class TestF2pP2p:

    def test_f2p_csv_equals_json(self, csv_row: dict, json_meta: dict):
        csv_f2p = set(_parse_test_list(csv_row["fail_to_pass"]))
        json_f2p = set(_parse_test_list(str(json_meta["FAIL_TO_PASS"])))
        assert csv_f2p == json_f2p, f"F2P mismatch: CSV={csv_f2p - json_f2p} JSON={json_f2p - csv_f2p}"

    def test_p2p_csv_equals_json(self, csv_row: dict, json_meta: dict):
        csv_p2p = set(_parse_test_list(csv_row["pass_to_pass"]))
        json_p2p = set(_parse_test_list(str(json_meta["PASS_TO_PASS"])))
        assert csv_p2p == json_p2p, f"P2P mismatch: CSV={csv_p2p - json_p2p} JSON={json_p2p - csv_p2p}"

    def test_f2p_count(self, csv_row: dict):
        assert len(_parse_test_list(csv_row["fail_to_pass"])) == 9

    def test_p2p_count(self, csv_row: dict):
        assert len(_parse_test_list(csv_row["pass_to_pass"])) == 8


def _parse_test_list(val: str) -> list[str]:
    """Parse comma-separated test paths into a sorted list."""
    return sorted(x.strip() for x in val.split(",") if x.strip())


# ═══════════════════════════════════════════════════════════════════
# TestNoDuplicates
# ═══════════════════════════════════════════════════════════════════

class TestNoDuplicates:

    def test_no_stray_problem_statement(self):
        stray = BASE_DIR / "PROBLEM_STATEMENT.md"
        assert not stray.exists(), "PROBLEM_STATEMENT.md should not exist in base/"

    def test_no_stray_pr_description(self):
        stray = BASE_DIR / "PR_DESCRIPTION.md"
        assert not stray.exists(), "PR_DESCRIPTION.md should not exist in base/"

    def test_exactly_one_metadata_csv(self):
        csvs = list(REPO_ROOT.rglob("metadata.csv"))
        assert len(csvs) == 1, f"expected 1 metadata.csv, found {len(csvs)}: {csvs}"


# ═══════════════════════════════════════════════════════════════════
# TestNoCredentials
# ═══════════════════════════════════════════════════════════════════

CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9]{36}"),
    re.compile(r"gho_[a-zA-Z0-9]{36}"),
    re.compile(r"xoxb-[a-zA-Z0-9-]+"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
]


class TestNoCredentials:

    def test_no_secrets_in_problem_statement(self):
        _assert_no_creds(PROBLEM_STATEMENT_MD)

    def test_no_secrets_in_pr_description(self):
        _assert_no_creds(PR_DESCRIPTION_MD)

    def test_no_secrets_in_metadata_json(self):
        _assert_no_creds(METADATA_JSON)


def _assert_no_creds(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    for pat in CREDENTIAL_PATTERNS:
        match = pat.search(content)
        assert not match, f"credential pattern found in {path.name}: {match.group()}"
