#!/usr/bin/env bash
# Rebuilds the isolated Solver Mode fixture: AGENTS.md (authoring block stripped),
# PROBLEM_STATEMENT.md, and the monorepo tree at the base commit. Mirrors the
# "Operator runbook" section of AGENTS.md.
#
# Usage: solver_test/build_fixture.sh [output_dir]
#   output_dir defaults to ../psl740-solver-fixture (outside the repo, so it's
#   never accidentally committed).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

OUT="${1:-$REPO_ROOT/../psl740-solver-fixture}"
OUT="$(cd "$(dirname "$OUT")" 2>/dev/null && pwd)/$(basename "$OUT")" || OUT="$1"

die() { echo "Error: $*" >&2; exit 1; }

[[ -z "$(git status --porcelain)" ]] || die "working tree is dirty — commit or stash before building the fixture (see AGENTS.md: 'Git safety')"

BASE_SHA="$(git log --format='%H %s' | grep -E ' base: ' | head -1 | cut -d' ' -f1)"
[[ -n "$BASE_SHA" ]] || die "could not find a commit with subject 'base: ...' in git history"
echo "Base commit: $BASE_SHA"

rm -rf "$OUT"
mkdir -p "$OUT/_raw"

# git archive would honor base/.gitattributes export-ignore (which strips
# config/, docs/, examples/, splitter/, var/, and ALL packages/*/tests — i.e.
# the P2P tests). Use an alternate work-tree checkout instead, which ignores
# export-ignore entirely.
git --work-tree="$OUT/_raw" checkout "$BASE_SHA" -- base
git reset -- base >/dev/null   # undo the index changes the above checkout staged; working tree of THIS repo is untouched

cp -r "$OUT/_raw/base/." "$OUT/"
rm -rf "$OUT/_raw"
rm -f "$OUT/.agen-runtime/metadata.json"   # authoring-only; never shipped to the solver

cp "$REPO_ROOT/PROBLEM_STATEMENT.md" "$OUT/PROBLEM_STATEMENT.md"

# Strip the AUTHORING BLOCK out of AGENTS.md.
START_LINE="$(grep -n '^## ===== AUTHORING BLOCK START =====' "$REPO_ROOT/AGENTS.md" | head -1 | cut -d: -f1)"
END_LINE="$(grep -n '^## ===== AUTHORING BLOCK END =====' "$REPO_ROOT/AGENTS.md" | head -1 | cut -d: -f1)"
[[ -n "$START_LINE" && -n "$END_LINE" ]] || die "could not locate AUTHORING BLOCK markers in AGENTS.md"
awk -v s="$START_LINE" -v e="$END_LINE" '
    NR==s { print "## (authoring-only block removed for Solver Mode — see operator instructions)"; f=1; next }
    NR==e { f=0; next }
    f     { next }
    { print }
' "$REPO_ROOT/AGENTS.md" > "$OUT/AGENTS.md"

# Leakage sanity checks — the nine solution classes and nine F2P test files must be absent.
LEAK=0
for cls in ConcatReadHandle FixedLengthReadHandle BoundedReadHandle TruncatedReadHandle \
           TeeWriteHandle JoinedReadWriteHandle SinkReadHandle SinkWriteHandle SinkReadWriteHandle; do
    [[ -f "$OUT/packages/io/src/Psl/IO/$cls.php" ]] && { echo "LEAK: $cls.php present in base"; LEAK=1; }
    [[ -f "$OUT/packages/io/tests/unit/${cls}Test.php" ]] && { echo "LEAK: ${cls}Test.php present in base"; LEAK=1; }
done
# Note: README.md is intentionally NOT checked here — base/README.md is the
# monorepo's own (legitimate) README, not the task-bundle's authoring doc.
# The latter is never copied into $OUT by construction, so checking for it
# would either miss the real leak vector or false-positive on the former.
for forbidden in README_EN.md IDEA.md ORIGINAL_TASK.md ORIGINAL_TASK_EN.md PR_DESCRIPTION.md metadata.csv test_task; do
    [[ -e "$OUT/$forbidden" ]] && { echo "LEAK: authoring-only $forbidden present at fixture root"; LEAK=1; }
done
(( LEAK == 0 )) || die "leakage check failed — see above"

echo "Fixture built at: $OUT"
echo "Contents:"
ls "$OUT"
echo
echo "Next: point a fresh agent at this directory, telling it to follow the Solver Mode block of AGENTS.md."
