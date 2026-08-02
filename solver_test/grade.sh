#!/usr/bin/env bash
# Injects the hidden [f2p] test files onto a frozen solver tree and grades the
# F2P (must go fail->pass) / P2P (must stay pass) transition, per the
# "Operator runbook" section of AGENTS.md (steps 4-5).
#
# Usage: solver_test/grade.sh <solver_tree_dir>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

die() { echo "Error: $*" >&2; exit 1; }

TREE="${1:?usage: grade.sh <solver_tree_dir>}"
TREE="$(cd "$TREE" && pwd)"
[[ -d "$TREE/packages/io/src/Psl/IO" ]] || die "$TREE doesn't look like a solver tree (no packages/io/src/Psl/IO)"

cd "$REPO_ROOT"
F2P_SHA="$(git log --format='%H %s' | grep -E ' \[f2p\]:' | head -1 | cut -d' ' -f1)"
[[ -n "$F2P_SHA" ]] || die "could not find a commit with subject '[f2p]: ...' in git history"
echo "F2P commit: $F2P_SHA"

# Ship every file the [f2p] commit touched under packages/io/tests/ (the nine
# test files plus any fixture they import) onto the solver's tree.
F2P_FILES=()
while IFS= read -r f; do
    rel="${f#base/}"
    mkdir -p "$TREE/$(dirname "$rel")"
    git show "$F2P_SHA:$f" > "$TREE/$rel"
    [[ "$rel" == *Test.php ]] && F2P_FILES+=("$rel")
done < <(git show --stat --name-only "$F2P_SHA" | grep '^base/packages/io/tests/')

echo "Injected ${#F2P_FILES[@]} F2P test files:"
printf '  %s\n' "${F2P_FILES[@]}"

P2P_FILES=(
    packages/io/tests/unit/StreamTest.php
    packages/io/tests/unit/SpoolTest.php
    packages/io/tests/unit/ReaderTest.php
    packages/io/tests/unit/PipeTest.php
    packages/io/tests/unit/MemoryHandleTest.php
    packages/io/tests/unit/IterableReadHandleTest.php
    packages/io/tests/unit/CopyTest.php
    packages/io/tests/unit/CopyBidirectionalTest.php
)

IMAGE="psl740-grade-$(basename "$TREE")"
echo "Building grading image ($IMAGE) from $TREE ..."
docker build --quiet -t "$IMAGE" -f "$TREE/.agen-runtime/Dockerfile.agen-runtime" "$TREE" >/dev/null

run_set() {
    local label="$1"; shift
    local files
    files="$(IFS=,; echo "$*")"
    echo
    echo "=== $label ==="
    docker run --rm "$IMAGE" bash .agen-runtime/run-tests-eval.sh "$files" || echo "[$label] FAILED (see above)"
}

run_set "F2P (expect: all pass)" "${F2P_FILES[@]}"
run_set "P2P (expect: all pass)" "${P2P_FILES[@]}"
