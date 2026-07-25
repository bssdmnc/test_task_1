# [GOLDEN SOLUTION] Add composable IO handle decorators

## Problem

The `Psl\IO` package did not expose reusable decorators for composing read/write handles. As a result, equivalent wrapping logic was duplicated as bespoke internal adapters in other packages. This made stream composition inconsistent and harder to maintain.

## Approach

Introduce a focused set of composable decorator classes in `packages/io`:
- reader decorators for concatenation, fixed-length reads, bounded reads, and truncated reads
- writer decorators for mirroring writes
- a joined read-write handle
- sink read/write/read-write handles as `/dev/null` primitives

The implementation follows existing `Psl\IO` interface contracts, closes underlying `CloseHandleInterface` instances, and keeps edge cases explicit: empty handles, premature EOF, double close, zero-length operations, and deterministic backpressure for `TeeWriteHandle`.

Key decisions vs. the original PR:
- Scope is limited to `packages/io` to keep the evaluation task self-contained and deterministic.
- Test fixtures are added under `packages/io/tests/fixture` to validate decorator behavior without external services or network.
- F2P suite is structured as strict `base → pass after [sol]` tests, while existing io tests are preserved as P2P.

**Files changed:**

| Status | File |
|--------|------|
| NEW | `packages/io/src/Psl/IO/ConcatReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/FixedLengthReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/BoundedReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/TruncatedReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/TeeWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/JoinedReadWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkReadWriteHandle.php` |
| MOVED | `packages/io/tests/fixture/NonCloseableWriteHandle.php` (was `src/Psl/IO/`) |
| MOVED | `packages/io/tests/fixture/SlowWriteHandle.php` (was `src/Psl/IO/`) |
| NEW | `packages/io/tests/unit/ConcatReadHandleTest.php` |
| MOD | `packages/io/src/Psl/IO/BoundedReadHandle.php` (generic error message) |
| MOD | `packages/io/composer.json` (autoload-dev for fixtures) |
| MOD | `base/.agen-runtime/metadata.json` |

## Differences from the original PR / existing-solution

This golden solution intentionally diverges from the raw PR merge and from `existing-solution` in three concrete, intentional ways:

1. **Fixtures relocated to `tests/fixture/`** — `NonCloseableWriteHandle` and `SlowWriteHandle` were originally committed under `src/Psl/IO/` (production namespace). They are test doubles, so they now live in `tests/fixture/` under the `Psl\IO\Tests\Fixture` namespace and are registered via `composer.json` `autoload-dev`. This keeps the shipped `src/` tree free of test-only classes.
2. **Generic error message in `BoundedReadHandle`** — the original threw `"Response body exceeded the configured limit..."`, which leaks an HTTP-specific concept into a generic IO decorator. It now throws `"Read exceeded the configured limit..."`, which is correct for any bounded read source (file, pipe, socket, memory).
3. **`ConcatReadHandleTest` is part of `[sol]`**, not `[f2p]` — because its class is implemented in `[sol]`; only the *remaining* handle tests are added in `[f2p]` to keep the fail→pass partition honest.

## Testing Strategy

**Fail-to-Pass:** tests in `packages/io/tests/unit/*HandleTest.php` error on base due to missing classes, then pass after `[sol]`.

**Pass-to-Pass:** existing io tests remain green before and after:
- `StreamTest.php`
- `SpoolTest.php`
- `ReaderTest.php`
- `PipeTest.php`
- `MemoryHandleTest.php`
- `IterableReadHandleTest.php`
- `CopyTest.php`
- `CopyBidirectionalTest.php`

Coverage includes: sequential reads, limit enforcement, silent truncation, write mirroring with backpressure, joined read-write behavior, sink semantics, and close/double-close tolerance.

## Commit Structure

```
9dcb6be base: php-standard-library snapshot before PR #740
7e8958d [sol] add io handle decorators, test fixtures, and autoload wiring
3cb1dcf [f2p] add fail-to-pass io handle tests
<meta-sha> [meta] metadata.json + task docs
```
