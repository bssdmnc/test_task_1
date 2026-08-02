"""Cross-source compliance checks for the PR #740 eval-task bundle.

The deliverables are only useful if they agree with each other: the CSV row, the
runtime JSON, the git commit graph, and the two Markdown docs all describe the
same task. Each class below pins one of those agreements.
"""

from __future__ import annotations

import json
import re

from conftest import CSV_COLUMNS, DECORATORS, EVAL_SYSTEM_COLUMNS, as_list

F2P_COUNT = 9
P2P_COUNT = 8


def unescape(value: str) -> str:
    """Recover the source text of a metadata.csv field.

    The CSV stores every multi-line field on a single physical line, with real
    newlines written as the literal sequence ``\\n`` (see AGENTS.md, metadata.csv
    fill recipe). This mirrors ``csvcol.py --unescape``.
    """
    return value.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")


def files_in(git, sha: str) -> list[str]:
    out = git("show", "--stat", "--format=", "--name-only", sha)
    return [line.strip() for line in out.splitlines() if line.strip()]


def exists_at(git, sha: str, path: str) -> bool:
    result = git("cat-file", "-e", f"{sha}:{path}", check=False)
    return result == "" and git("cat-file", "-t", f"{sha}:{path}", check=False) == "blob"


class TestCommitStructure:
    """base_commit/golden_commit/test_commit are SHAs inside base/'s own
    repository (see conftest.git_base) — base/ has no `base/` prefix on its
    own paths, since its root *is* the php-standard-library tree."""

    def test_topology_is_base_sol_f2p_meta(self, git_base, shas):
        """base/ is its own repo now, so its base commit is a root commit
        (no parent) — walk all of golden-solution's history instead of a
        `{base}~1..` range."""
        meta_sha = git_base("rev-parse", "golden-solution")
        subjects = git_base("log", "--format=%s", meta_sha).splitlines()
        assert len(subjects) == 4, f"expected exactly 4 commits, got {subjects}"
        assert subjects[0].startswith("[meta]"), subjects[0]
        assert subjects[1].startswith("[f2p]"), subjects[1]
        assert subjects[2].startswith("[sol]"), subjects[2]
        assert not subjects[3].startswith("["), subjects[3]

    def test_shas_match_their_roles(self, git_base, shas):
        assert git_base("log", "-1", "--format=%s", shas["golden"]).startswith("[sol]")
        assert git_base("log", "-1", "--format=%s", shas["test"]).startswith("[f2p]")
        assert not git_base("log", "-1", "--format=%s", shas["base"]).startswith("[")

    def test_sol_is_the_parent_of_f2p(self, git_base, shas):
        assert git_base("rev-parse", f"{shas['test']}~1") == git_base("rev-parse", shas["golden"])

    def test_base_is_the_parent_of_sol(self, git_base, shas):
        assert git_base("rev-parse", f"{shas['golden']}~1") == git_base("rev-parse", shas["base"])

    def test_exactly_one_sol_commit(self, git_base, shas):
        subjects = git_base("log", "--format=%s", f"{shas['base']}..golden-solution").splitlines()
        assert sum(s.startswith("[sol]") for s in subjects) == 1

    def test_sol_carries_production_code_only(self, git_base, shas):
        for path in files_in(git_base, shas["golden"]):
            assert "/tests/" not in path, f"[sol] must not ship tests: {path}"
            assert path.startswith("packages/io/src/"), path

    def test_f2p_carries_tests_and_fixtures_only(self, git_base, shas):
        paths = files_in(git_base, shas["test"])
        for path in paths:
            assert path.startswith("packages/io/tests/"), path
        assert sum("/tests/unit/" in p for p in paths) == F2P_COUNT

    def test_f2p_ships_the_fixtures_its_tests_import(self, git_base, base_repo_root, shas):
        """A fixture that lived only in [sol] would be missing from a solver's
        tree at grading time, failing the test for the wrong reason."""
        shipped = {p.rsplit("/", 1)[-1] for p in files_in(git_base, shas["test"])}
        tests_dir = base_repo_root / "packages" / "io" / "tests" / "unit"
        imported = set()
        for test_file in tests_dir.glob("*Test.php"):
            for match in re.finditer(
                r"use\s+Psl\\IO\\Tests\\Fixture\\(\w+)\s*;", test_file.read_text(encoding="utf-8")
            ):
                imported.add(match.group(1) + ".php")
        missing = imported - shipped
        assert not missing, f"fixtures imported by F2P tests but not in [f2p]: {sorted(missing)}"

    def test_fixture_autoload_mapping_is_in_base(self, git_base, shas):
        """The mapping must predate [sol] so it survives into a solver's tree."""
        composer = git_base("show", f"{shas['base']}:composer.json")
        assert "Psl\\\\IO\\\\Tests\\\\Fixture\\\\" in composer

    def test_base_is_its_own_git_repository(self, base_repo_root):
        """The reviewer's core complaint: base/ must be a real, runnable git
        checkout on its own — not a subtree that only exists inside the
        wrapper's history under a base/ path prefix."""
        assert (base_repo_root / ".git").exists(), (
            "base/ has no .git — it cannot be cloned, reset, or built on its own"
        )

    def test_base_branches_exist_with_expected_tips(self, git_base, shas):
        """`main` (default branch) holds just the base snapshot; `golden-solution`
        carries base -> [sol] -> [f2p] -> [meta] on top of it."""
        assert git_base("rev-parse", "main") == shas["base"]
        assert git_base("rev-parse", "golden-solution") != shas["base"]
        assert git_base("merge-base", "main", "golden-solution") == shas["base"]


class TestMetadataJson:
    REQUIRED = [
        "instance_id", "task_title", "problem_statement", "problem_statement_variant",
        "hints", "repo", "repo_path_or_url", "FAIL_TO_PASS", "PASS_TO_PASS",
        "language", "docker_file", "run_script", "task_type", "task_category",
        "repo_category", "version", "container_mem", "container_memswap",
        "container_network_needed",
    ]

    def test_required_fields_present_and_non_empty(self, meta):
        for field in self.REQUIRED:
            assert field in meta, f"missing field: {field}"
            assert meta[field] not in ("", None), f"empty field: {field}"

    def test_no_placeholders_survive(self, meta_raw):
        for placeholder in ("agen-core", "<meta-sha>", "<sha>", "TODO", "TBD"):
            assert placeholder not in meta_raw, f"placeholder left in metadata.json: {placeholder}"

    def test_test_lists_have_expected_shape(self, meta):
        assert len(as_list(meta["FAIL_TO_PASS"])) == F2P_COUNT
        assert len(as_list(meta["PASS_TO_PASS"])) == P2P_COUNT

    def test_network_is_disabled(self, meta):
        assert str(meta["container_network_needed"]).upper() == "FALSE"

    def test_variant_is_not_a_copy_of_the_statement(self, meta):
        assert meta["problem_statement_variant"].strip() != meta["problem_statement"].strip()

    def test_variant_avoids_naming_the_classes(self, meta):
        """The variant is meant to read like a non-technical stakeholder ask."""
        variant = meta["problem_statement_variant"]
        leaked = [name for name in DECORATORS if name in variant]
        assert not leaked, f"variant leaks class names: {leaked}"

    def test_runtime_paths_point_at_real_files(self, repo_root, meta):
        for field in ("docker_file", "run_script"):
            assert (repo_root / "base" / meta[field]).is_file(), meta[field]


class TestMetadataCsv:
    def test_header_is_the_35_columns_in_order(self, csv_rows):
        assert csv_rows[0] == CSV_COLUMNS

    def test_exactly_one_data_row(self, csv_rows):
        assert len(csv_rows) == 2, f"expected header + 1 data row, got {len(csv_rows)}"

    def test_data_row_parses_to_35_fields(self, csv_rows):
        assert len(csv_rows[1]) == 35

    def test_shas_match_metadata_json(self, csv_row, shas):
        assert csv_row["base_commit"] == shas["base"]
        assert csv_row["golden_commit"] == shas["golden"]
        assert csv_row["test_commit"] == shas["test"]

    def test_shas_are_real_commits(self, git_base, csv_row):
        for field in ("base_commit", "golden_commit", "test_commit"):
            assert git_base("cat-file", "-t", csv_row[field]) == "commit", field

    def test_docker_file_holds_contents_not_a_path(self, repo_root, csv_row):
        """The CSV embeds the whole file; metadata.json stores the path."""
        actual = (repo_root / "base" / ".agen-runtime" / "Dockerfile.agen-runtime").read_text(encoding="utf-8")
        assert unescape(csv_row["docker_file"]) == actual
        assert "\n" not in csv_row["docker_file"], "newlines must be escaped, not literal"

    def test_run_script_holds_contents_not_a_path(self, repo_root, csv_row):
        actual = (repo_root / "base" / ".agen-runtime" / "run-tests-eval.sh").read_text(encoding="utf-8")
        assert unescape(csv_row["run_script"]) == actual
        assert "\n" not in csv_row["run_script"], "newlines must be escaped, not literal"

    def test_evaluation_system_columns_are_empty(self, csv_row):
        for column in EVAL_SYSTEM_COLUMNS:
            assert csv_row[column] == "", f"{column} should be left for the eval system"

    def test_before_repo_set_cmd_resets_to_base(self, csv_row):
        assert csv_row["before_repo_set_cmd"] == f"git reset --hard {csv_row['base_commit']}"

    def test_multiline_fields_are_escaped_and_inner_quotes_doubled(self, csv_raw, csv_row):
        """Round-trip is the real check; this pins the on-disk encoding."""
        statement = csv_row["problem_statement"]
        assert "\n" not in statement, "newlines must be escaped, not literal"
        assert "\\n" in statement, "problem_statement should carry escaped newlines"
        if '"' in statement:
            assert '""' in csv_raw, "internal quotes must be doubled on disk"

    def test_one_record_is_one_physical_line(self, csv_raw):
        """The whole point of escaping: line-based readers must see 2 lines."""
        assert csv_raw.count("\n") == 2, "header + one data row, one line each"

    def test_no_field_carries_a_raw_newline(self, csv_row):
        offenders = [name for name, value in csv_row.items() if "\n" in value or "\r" in value]
        assert not offenders, f"fields with unescaped newlines: {offenders}"

    def test_every_field_round_trips(self, csv_path, csv_rows):
        import csv as _csv
        with csv_path.open("r", newline="", encoding="utf-8") as handle:
            reparsed = list(_csv.reader(handle))
        assert reparsed == csv_rows


class TestF2pP2p:
    def test_csv_and_json_lists_agree(self, csv_row, meta):
        assert json.loads(csv_row["fail_to_pass"]) == as_list(meta["FAIL_TO_PASS"])
        assert json.loads(csv_row["pass_to_pass"]) == as_list(meta["PASS_TO_PASS"])

    def test_counts(self, csv_row):
        assert len(json.loads(csv_row["fail_to_pass"])) == F2P_COUNT
        assert len(json.loads(csv_row["pass_to_pass"])) == P2P_COUNT

    def test_f2p_files_absent_at_base_present_at_test_commit(self, git_base, csv_row, shas):
        for path in json.loads(csv_row["fail_to_pass"]):
            assert exists_at(git_base, shas["test"], path), f"F2P missing at test_commit: {path}"
            assert not exists_at(git_base, shas["base"], path), f"F2P leaked into base: {path}"

    def test_p2p_files_present_at_base(self, git_base, csv_row, shas):
        for path in json.loads(csv_row["pass_to_pass"]):
            assert exists_at(git_base, shas["base"], path), (
                f"P2P must exist at base or it cannot be a regression guard: {path}"
            )

    def test_decorators_absent_at_base_present_at_golden(self, git_base, shas):
        for name in DECORATORS:
            path = f"packages/io/src/Psl/IO/{name}.php"
            assert exists_at(git_base, shas["golden"], path), f"missing at [sol]: {name}"
            assert not exists_at(git_base, shas["base"], path), f"leaked into base: {name}"


class TestProblemStatement:
    SECTIONS = [
        "## Problem Statement", "Current behavior", "Reproduction steps",
        "Expected behavior", "Files to create/modify", "Files NOT to touch",
        "Constraints", "## Hints", "## Test Files", "## Commits",
    ]

    def test_required_sections_present(self, repo_root):
        text = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        for section in self.SECTIONS:
            assert section in text, f"missing section: {section}"

    def test_matches_csv_problem_statement(self, repo_root, csv_row):
        md = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        assert unescape(csv_row["problem_statement"]) == md

    def test_matches_json_problem_statement(self, repo_root, meta):
        md = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        assert meta["problem_statement"].strip() == md.strip()

    def test_documents_every_class_the_solver_must_write(self, repo_root):
        text = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        for name in DECORATORS:
            assert name in text, f"statement never names {name}"

    def test_uses_monorepo_relative_paths(self, repo_root):
        """A solver's working directory is the monorepo, so base/ prefixes are wrong."""
        text = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        assert "base/packages/" not in text

    def test_no_placeholders_or_shas(self, repo_root):
        text = (repo_root / "PROBLEM_STATEMENT.md").read_text(encoding="utf-8")
        for placeholder in ("agen-core", "<meta-sha>", "<sha>", "TODO", "TBD"):
            assert placeholder not in text, f"placeholder in statement: {placeholder}"
        assert not re.search(r"\b[0-9a-f]{40}\b", text), "statement must not pin commit SHAs"


class TestPrDescription:
    SECTIONS = ["## Problem", "## Approach", "## Testing Strategy", "## Commit Structure"]

    def test_required_sections_present(self, repo_root):
        text = (repo_root / "PR_DESCRIPTION.md").read_text(encoding="utf-8")
        for section in self.SECTIONS:
            assert section in text, f"missing section: {section}"

    def test_title_marks_it_as_the_golden_solution(self, repo_root):
        text = (repo_root / "PR_DESCRIPTION.md").read_text(encoding="utf-8")
        assert text.lstrip().startswith("# [GOLDEN SOLUTION]")

    def test_commit_structure_cites_the_real_shas(self, repo_root, shas):
        text = (repo_root / "PR_DESCRIPTION.md").read_text(encoding="utf-8")
        for role, sha in shas.items():
            assert sha[:7] in text, f"PR description does not cite the {role} commit"

    def test_no_stale_shas(self, repo_root, git_base):
        text = (repo_root / "PR_DESCRIPTION.md").read_text(encoding="utf-8")
        for candidate in set(re.findall(r"\b[0-9a-f]{7,40}\b", text)):
            assert git_base("cat-file", "-t", candidate, check=False) == "commit", (
                f"PR description cites {candidate}, which is not a commit in base/'s repo"
            )


class TestNoDuplicates:
    def test_exactly_one_metadata_csv(self, repo_root):
        """This harness runs both inside the author's wrapper repo and against
        a plain (non-git) deliverable folder handed off for review, so this is
        a filesystem check rather than a `git ls-files` one: metadata.csv's
        canonical location is the bundle root, and nothing should shadow it
        (e.g. a stray copy under base/ — separately pinned by
        test_docs_do_not_leak_into_the_monorepo)."""
        found = sorted(
            p for p in repo_root.rglob("metadata.csv")
            if ".git" not in p.relative_to(repo_root).parts
        )
        assert found == [repo_root / "metadata.csv"], (
            f"expected exactly one metadata.csv, found {found}"
        )

    def test_docs_do_not_leak_into_the_monorepo(self, repo_root):
        """base/ is handed to the solver; author-side docs must not be reachable."""
        for name in ("PROBLEM_STATEMENT.md", "PR_DESCRIPTION.md", "IDEA.md", "metadata.csv"):
            assert not (repo_root / "base" / name).exists(), f"base/{name} must not exist"

    def test_test_task_is_not_inside_base(self, repo_root):
        assert not (repo_root / "base" / "test_task").exists()


class TestNoCredentials:
    PATTERNS = [
        r"ghp_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        r"AKIA[0-9A-Z]{16}",
        r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
    ]

    def test_docs_carry_no_secrets(self, repo_root):
        targets = ["PROBLEM_STATEMENT.md", "PR_DESCRIPTION.md", "AGENTS.md",
                   "IDEA.md", "metadata.csv"]
        for name in targets:
            path = repo_root / name
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in self.PATTERNS:
                assert not re.search(pattern, text), f"possible secret in {name}"

    def test_runtime_metadata_carries_no_secrets(self, meta_raw):
        for pattern in self.PATTERNS:
            assert not re.search(pattern, meta_raw), "possible secret in metadata.json"
