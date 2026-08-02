# [GOLDEN SOLUTION] Add composable IO handle decorators

## Problem

On the base commit, `Psl\IO` ships concrete handles (`MemoryHandle`,
`IterableReadHandle`, the stream handle family) and the interfaces they satisfy — but no
**decorators**: handles that wrap other handles to adapt their behavior.

Anything that needs to cap a stream's size, read a stream's prefix, require an exact byte
count, concatenate two sources, mirror a write, or discard output has to hand-roll a
private wrapper class. The same wrapper logic is therefore duplicated ad hoc across
packages instead of living once in `Psl\IO`, and each copy re-decides the awkward
questions — what happens at the limit, what happens on premature EOF, whether `close()`
propagates — differently.

## Approach

Nine `final` classes under `packages/io/src/Psl/IO/`, each implementing the existing
interfaces and reusing `ReadHandleConvenienceMethodsTrait` /
`WriteHandleConvenienceMethodsTrait` rather than reimplementing `readAll`, `writeAll`, and
friends.

| Class | Behavior |
| --- | --- |
| `ConcatReadHandle` | Reads `$first` to exhaustion, then `$second`. Advances only when `$first` returns empty **and** reports EOF, so a not-ready read does not skip data. The switch latches. |
| `FixedLengthReadHandle` | Caps each request to the outstanding count. Underlying EOF with bytes still outstanding raises `RuntimeException`; empty-but-not-EOF is a not-ready read and returns `''` untouched. |
| `BoundedReadHandle` | Caps total bytes, then **probes one byte past the limit** to tell "fit exactly" from "overflowed", raising `RuntimeException` on the latter. |
| `TruncatedReadHandle` | Same capping, but never probes and never throws — at the limit it simply reports EOF and leaves the rest of the stream unread. |
| `TeeWriteHandle` | Mirrors writes to two destinations, buffering bytes `$first` accepted but `$second` has not, and returning `0` from `tryWrite` as backpressure until the buffer drains. |
| `JoinedReadWriteHandle` | Delegates reads to a reader and writes to a writer; `flush()` forwards only when the writer is buffered. |
| `SinkReadHandle` / `SinkWriteHandle` / `SinkReadWriteHandle` | `/dev/null`-style handles: reads are always empty and at EOF, writes always accept the full length and discard. |

Cross-cutting: `close()` is idempotent, propagates to underlying handles **only** when they
implement `CloseHandleInterface`, and every subsequent operation raises
`AlreadyClosedException` using the package's existing wording. `isClosed()` is the one
method that keeps working after close.

### Key decisions vs. the original PR

- **Scope held to `packages/io`.** The upstream PR also reworked bespoke wrappers in
  `http-client` and `message`. Those refactors are deliberately excluded: they widen the
  diff without exercising anything new, and they would force a solver to touch packages the
  task never describes.
- **`RuntimeException`, not `OverflowException`, for a bounded overflow.** The package ships
  an `OverflowException`, which reads like the natural choice and is the trap a solver falls
  into. Exceeding a configured read ceiling is an I/O condition, not an arithmetic one, and
  it is raised on the same code path as every other read failure — so it stays
  `RuntimeException` and the problem statement says so explicitly.
- **`BoundedReadHandle` distinguishes "fit exactly" from "overflowed".** Reaching the byte
  limit is not itself an error; only *more data existing past it* is. Hence the one-byte
  probe and the latched clean-limit flag, so `reachedEndOfDataSource()` cannot claim a clean
  end before the question has actually been answered.
- **`TeeWriteHandle` propagates backpressure instead of buffering without bound.** A naive
  tee either drops the slower destination's bytes or accumulates them forever. Returning `0`
  from `tryWrite` while the pending buffer is non-empty keeps the two destinations in sync
  and makes the memory cost bounded by one write.
- **Bounded and truncated are separate classes, not one class with a flag.** They differ in
  a single question — is excess data an error? — and callers pick by construction rather
  than by remembering a boolean.

**Files changed:**

| Status | File |
| ------ | ---------------------------------- |
| NEW | `packages/io/src/Psl/IO/ConcatReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/FixedLengthReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/BoundedReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/TruncatedReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/TeeWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/JoinedReadWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkReadHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkWriteHandle.php` |
| NEW | `packages/io/src/Psl/IO/SinkReadWriteHandle.php` |

No existing file is modified by `[sol]`: the decorators satisfy the current interfaces
as-is, so the public API and every convenience trait are untouched.

## Testing Strategy

**Fail-to-Pass** — 168 tests across nine files, all failing on base with
`Class "Psl\IO\<Decorator>" not found` and passing on `[sol]`:

- `packages/io/tests/unit/ConcatReadHandleTest.php`
- `packages/io/tests/unit/FixedLengthReadHandleTest.php`
- `packages/io/tests/unit/BoundedReadHandleTest.php`
- `packages/io/tests/unit/TruncatedReadHandleTest.php`
- `packages/io/tests/unit/TeeWriteHandleTest.php`
- `packages/io/tests/unit/JoinedReadWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadHandleTest.php`
- `packages/io/tests/unit/SinkWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadWriteHandleTest.php`

**Pass-to-Pass** — 123 tests guarding the untouched surface, green before and after:

- `packages/io/tests/unit/StreamTest.php`
- `packages/io/tests/unit/SpoolTest.php`
- `packages/io/tests/unit/ReaderTest.php`
- `packages/io/tests/unit/PipeTest.php`
- `packages/io/tests/unit/MemoryHandleTest.php`
- `packages/io/tests/unit/IterableReadHandleTest.php`
- `packages/io/tests/unit/CopyTest.php`
- `packages/io/tests/unit/CopyBidirectionalTest.php`

Calibration, run on PHP 8.4.23:

| Cell | Result |
| --- | --- |
| F2P on base | 168 errors, each naming the missing decorator |
| F2P on `[sol]` + `[f2p]` | `OK (168 tests, 345 assertions)` |
| P2P on base | `OK (123 tests, 314 assertions)` |
| P2P on `[sol]` | `OK (123 tests, 314 assertions)` |
| Full `packages/io` suite on golden | `OK (291 tests, 659 assertions)` |

Covered scenarios and edge cases:

- Empty sources, zero-length limits, and reads issued past the end.
- Not-ready reads (`''` without EOF) kept distinct from genuine end-of-data — the case that
  separates a correct `ConcatReadHandle` and `FixedLengthReadHandle` from a plausible one.
- Premature EOF for `FixedLengthReadHandle` on both `read()` and `tryRead()`.
- Overflow detection for `BoundedReadHandle` on both paths, plus the clean-fit case where
  the payload lands exactly on the limit and no exception is due.
- `TruncatedReadHandle` stopping silently with data still pending underneath.
- `TeeWriteHandle` under a deliberately slow second destination: partial acceptance,
  incremental draining, `tryWrite` returning `0` while backpressured, and both destinations
  holding identical bytes once drained.
- Close semantics for every handle: idempotent double-close, propagation to closeable
  underlying handles, graceful handling of non-closeable ones, and
  `AlreadyClosedException` from every operation afterwards.

Determinism: no timing assertions, no sleeps, no randomness, no network. The slow-writer
fixture accepts a fixed byte count per call rather than depending on a clock.

## Commit Structure

```
0f45cdd base   php-standard-library snapshot before PR #740
               (full upstream tree at the commit immediately preceding PR #740,
                plus .agen-runtime/)
cd9c131 [sol]  add composable IO handle decorators — production code only
6abec9b [f2p]  add fail-to-pass tests, the fixtures those tests import, and the
               Psl\IO\Tests\Fixture\ autoload-dev wiring (root composer.json and
               packages/io/composer.json) those fixtures need to resolve
903aab8 [meta] metadata.json, metadata.csv, and the agent-facing docs
```

The fixtures ship in `[f2p]` rather than `[sol]` on purpose. Grading runs against the
*solver's* tree, which contains the solver's production code and nothing else — the solver
is never asked to author fixtures. A fixture reachable only from `[sol]` would be missing at
grading time, and `TeeWriteHandleTest` would fail on a missing fixture class rather than on
the implementation under test. The corresponding `autoload-dev` mapping ships in the same
`[f2p]` commit as the fixtures it resolves, rather than in `base` — a solver working only
from `base` never needs that namespace, since it is never asked to author fixtures either.
