# Task: Add composable IO handle decorators to php-standard-library

**instance_id:** `php-standard-library__php-standard-library__740`
**language:** PHP
**task_type:** feature
**task_category:** io

---

## Problem Statement

Title: Add composable IO handle decorators to the `Psl\IO` package

### Current behavior

The `Psl\IO` package ships concrete handles (`MemoryHandle`, `IterableReadHandle`, the
stream handle family) and the interfaces they satisfy, but it has **no decorators** —
handles that wrap other handles to change their behavior.

As a result there is no supported way to:

- read two sources back to back as if they were one stream;
- require that a stream yields exactly *N* bytes and fail loudly if it does not;
- enforce a hard size ceiling on a stream and reject input that exceeds it;
- read a prefix of a stream and stop cleanly at a boundary;
- mirror a write stream to a second destination;
- pair an unrelated reader and writer into a single read/write handle;
- obtain `/dev/null`-style handles that discard writes and read as empty.

Consumers that need any of the above must hand-roll a private wrapper class, so the same
wrapper logic is duplicated ad hoc across packages instead of living once in `Psl\IO`.

### Reproduction steps

1. Open `packages/io/src/Psl/IO/`.
2. Observe that the directory contains interfaces, convenience traits, and concrete
   handles, but no decorator that accepts another handle and adapts it.
3. Try to build a size-capped reader over an existing `ReadHandleInterface`, or mirror one
   `WriteHandleInterface` onto two destinations, using only the public classes in the
   package. There is no way to do it without writing a custom local wrapper class.

### Expected behavior

Add nine new public decorator/utility handles under `packages/io/src/Psl/IO/`, in the
`Psl\IO` namespace. Each is described below by its public contract.

Conventions used by every one of the nine classes (unless a card says otherwise):

- The class is `final` and lives in namespace `Psl\IO`.
- Read handles use `ReadHandleConvenienceMethodsTrait`; write handles use
  `WriteHandleConvenienceMethodsTrait`. Do not reimplement the convenience methods
  (`readAll`, `readFixedSize`, `writeAll`, …) that these traits provide.
- Every interface method carries `#[Override]`.
- The class tracks its own closed flag, implements `CloseHandleInterface`, and `close()`
  is **idempotent** — a second call is a no-op and must not re-close anything underneath.
- `close()` also closes each underlying handle **only if** that handle implements
  `CloseHandleInterface` (check with `instanceof`; a non-closeable underlying handle is
  legal and must not cause an error).
- After `close()`, every read/write/EOF/flush operation throws
  `Psl\IO\Exception\AlreadyClosedException`. `isClosed()` is the one method that keeps
  working after close and never throws. Use the package's existing wording for this
  exception — `'Handle has already been closed.'` — as `MemoryHandle`,
  `IterableReadHandle`, and `Internal\ResourceHandle` already do.
- `read()` takes `(null|int $maxBytes = null, CancellationTokenInterface $cancellation = new NullCancellationToken())`;
  `tryRead()` takes `(null|int $maxBytes = null)`; `write()` takes
  `(string $bytes, CancellationTokenInterface $cancellation = new NullCancellationToken())`;
  `tryWrite()` takes `(string $bytes)`. Match the signatures already declared by the
  interfaces in the package.

Note on the distinction between "not ready" and "end of data": a read handle returning
`''` does **not** by itself mean end of stream — it can also mean no data is available
right now. Where that distinction matters, the card below says so explicitly; consult
`reachedEndOfDataSource()` on the underlying handle rather than inferring EOF from `''`.

---

#### 1. `ConcatReadHandle` — read two handles in sequence

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `CloseHandleInterface` |
| **Trait** | `ReadHandleConvenienceMethodsTrait` |
| **Constructor** | `(ReadHandleInterface $first, ReadHandleInterface $second)` |

- `read()` / `tryRead()` delegate to `$first` until it is exhausted, then to `$second`.
- The switch to `$second` happens only when `$first` returned `''` **and** `$first`
  reports end of data. If `$first` returned `''` but is *not* at end of data, return `''`
  and stay on `$first` — do not advance.
- Once the switch has happened it is permanent (latched); do not re-consult `$first`.
- `reachedEndOfDataSource()` is `true` only when `$first` has been exhausted **and**
  `$second` reports end of data.
- `close()` closes both underlying handles if they are closeable.

#### 2. `FixedLengthReadHandle` — read exactly N bytes

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `CloseHandleInterface` |
| **Trait** | `ReadHandleConvenienceMethodsTrait` |
| **Constructor** | `(ReadHandleInterface $handle, int $length)` — `$length` is non-negative |

- Tracks how many bytes remain of the declared `$length`.
- `reachedEndOfDataSource()` is `true` exactly when the remaining count is `0`. A
  `$length` of `0` therefore reports end of data immediately and never reads.
- `read()` / `tryRead()`: when nothing remains, return `''`. Otherwise cap the request to
  the remaining count — read at most `min($maxBytes, $remaining)` bytes, or `$remaining`
  when `$maxBytes` is `null` — delegate to the underlying handle, and subtract the length
  of what came back from the remaining count.
- **Premature EOF:** if the underlying handle returns `''` **and** reports end of data
  while bytes are still outstanding, throw `Psl\IO\Exception\RuntimeException`. The
  message should state how many bytes were expected versus how many were available.
- If the underlying handle returns `''` but is *not* at end of data, that is merely "not
  ready": return `''` without throwing and without changing the remaining count.
- `close()` closes the underlying handle if it is closeable.

#### 3. `BoundedReadHandle` — hard size ceiling, reject overflow

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `CloseHandleInterface` |
| **Trait** | `ReadHandleConvenienceMethodsTrait` |
| **Constructor** | `(ReadHandleInterface $handle, int $limit)` |

- Counts bytes read and never lets the total exceed `$limit`: each request is capped to
  the remaining allowance (`min($maxBytes, $remaining)`, or the whole remaining allowance
  when `$maxBytes` is `null`).
- **Overflow probe — the defining behavior of this class.** Once the byte count has
  reached `$limit`, the handle must determine whether the underlying stream held *more*
  data than the limit allowed:
  - If the underlying handle already reports end of data, the input fit exactly. Latch a
    "limit reached cleanly" flag and return `''`.
  - Otherwise attempt to read **one** more byte from the underlying handle. If that comes
    back empty, the input fit exactly: latch the clean flag and return `''`. If a byte
    *is* returned, the input exceeded the limit — throw
    `Psl\IO\Exception\RuntimeException` naming the configured limit.
  - Once the clean flag is latched, subsequent calls return `''` without probing again.
- **Use `RuntimeException`, not `OverflowException`.** `Psl\IO\Exception\OverflowException`
  exists in the package but is not the exception for this condition.
- `reachedEndOfDataSource()` is `true` when the clean-limit flag has been latched **or**
  the underlying handle reports end of data. Reaching the byte limit alone is *not*
  sufficient — until the probe has run, the handle cannot yet claim a clean end.
- `close()` closes the underlying handle if it is closeable.

#### 4. `TruncatedReadHandle` — read a prefix, stop silently

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `CloseHandleInterface` |
| **Trait** | `ReadHandleConvenienceMethodsTrait` |
| **Constructor** | `(ReadHandleInterface $handle, int $limit)` |

- Same byte-counting and per-request capping as `BoundedReadHandle`.
- **Contrast with `BoundedReadHandle`:** this class never probes and **never throws** on
  excess data. Once the byte count reaches `$limit`, every further read returns `''`,
  regardless of how much data the underlying handle still holds. The remainder of the
  underlying stream is left untouched and unread.
- `reachedEndOfDataSource()` is `true` when the byte count has reached `$limit` **or** the
  underlying handle reports end of data.
- `close()` closes the underlying handle if it is closeable.

#### 5. `TeeWriteHandle` — mirror writes to two destinations

| | |
|---|---|
| **Implements** | `BufferedWriteHandleInterface`, `CloseHandleInterface` |
| **Trait** | `WriteHandleConvenienceMethodsTrait` |
| **Constructor** | `(WriteHandleInterface $first, WriteHandleInterface $second)` |

Every byte written must reach both handles. The two destinations may accept data at
different rates, so the handle keeps an internal **pending buffer** holding bytes that
`$first` accepted but `$second` has not taken yet.

- **`tryWrite(string $bytes): int` — non-blocking, with backpressure:**
  1. If the pending buffer is non-empty, first try to drain it into `$second` and drop the
     accepted prefix from the buffer.
  2. If the pending buffer is *still* non-empty after that attempt, return `0` — this is
     the backpressure signal. Do not touch `$bytes` at all; the caller is expected to
     retry later.
  3. With the buffer empty, offer `$bytes` to `$first`. If `$first` accepts `0` bytes,
     return `0`.
  4. Offer exactly the prefix `$first` accepted to `$second`. If `$second` accepts all of
     it, the handles are in sync.
  5. If `$second` accepted less, store the un-accepted remainder of that prefix in the
     pending buffer.
  6. Return the number of bytes `$first` accepted (steps 4–5 do not change the return
     value — the return value always reflects `$first`).
- **`write(string $bytes, ...): int` — blocking:** drain any pending buffer into `$second`
  in full first (a blocking write-all, then clear the buffer), then write `$bytes` to
  `$first`, then write exactly the prefix `$first` accepted to `$second` in full. Return
  the number of bytes `$first` accepted.
- **`flush(...)`:** write any pending buffer to `$second` in full and clear it. (This is
  why the class implements the buffered-write interface.)
- **`close()`:** discard the pending buffer and close both underlying handles if they are
  closeable.

#### 6. `JoinedReadWriteHandle` — pair a reader with a writer

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `BufferedWriteHandleInterface`, `CloseHandleInterface` |
| **Traits** | `ReadHandleConvenienceMethodsTrait` **and** `WriteHandleConvenienceMethodsTrait` |
| **Constructor** | `(ReadHandleInterface $reader, WriteHandleInterface $writer)` |

- All read operations (`read`, `tryRead`, `reachedEndOfDataSource`) delegate straight to
  `$reader`; all write operations (`write`, `tryWrite`) delegate straight to `$writer`.
  No buffering, no transformation.
- `flush()` forwards to `$writer` **only if** `$writer` implements
  `BufferedWriteHandleInterface`; otherwise it is a no-op (but still throws if the joined
  handle is closed).
- `close()` closes both `$reader` and `$writer` if they are closeable.

#### 7. `SinkReadHandle` — always empty, always at EOF

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `CloseHandleInterface` |
| **Trait** | `ReadHandleConvenienceMethodsTrait` |
| **Constructor** | none (no arguments) |

- `reachedEndOfDataSource()` returns `true` from the very first call — unlike
  `new MemoryHandle('')`, which only reports end of data after a read has been attempted.
- `read()` and `tryRead()` always return `''`, ignoring `$maxBytes`.
- `close()` is idempotent; there is nothing underneath to close.

#### 8. `SinkWriteHandle` — discard everything written

| | |
|---|---|
| **Implements** | `BufferedWriteHandleInterface`, `CloseHandleInterface` |
| **Trait** | `WriteHandleConvenienceMethodsTrait` |
| **Constructor** | none (no arguments) |

- `tryWrite()` and `write()` accept every byte, discard it, and return the **full length**
  of the input string — never a short write.
- `flush()` is a no-op (it still throws if the handle is closed).
- `close()` is idempotent; there is nothing underneath to close.

#### 9. `SinkReadWriteHandle` — both sink behaviors in one handle

| | |
|---|---|
| **Implements** | `ReadHandleInterface`, `BufferedWriteHandleInterface`, `CloseHandleInterface` |
| **Traits** | `ReadHandleConvenienceMethodsTrait` **and** `WriteHandleConvenienceMethodsTrait` |
| **Constructor** | none (no arguments) |

- Read side behaves exactly like `SinkReadHandle`; write side exactly like
  `SinkWriteHandle`.
- `close()` is idempotent; there is nothing underneath to close.

---

### Files to create/modify

Create these nine files — this is the entire required production change:

- `packages/io/src/Psl/IO/ConcatReadHandle.php`
- `packages/io/src/Psl/IO/FixedLengthReadHandle.php`
- `packages/io/src/Psl/IO/BoundedReadHandle.php`
- `packages/io/src/Psl/IO/TruncatedReadHandle.php`
- `packages/io/src/Psl/IO/TeeWriteHandle.php`
- `packages/io/src/Psl/IO/JoinedReadWriteHandle.php`
- `packages/io/src/Psl/IO/SinkReadHandle.php`
- `packages/io/src/Psl/IO/SinkWriteHandle.php`
- `packages/io/src/Psl/IO/SinkReadWriteHandle.php`

You are **not** asked to write unit tests or test fixtures — grading supplies its own
(see *Test Files*). If you want scratch test handles for your own verification, either put
them under `packages/io/tests/unit/` — that namespace, `Psl\IO\Tests\Unit\`, is already
registered in the base commit's `composer.json` `autoload-dev` section — or register your
own `autoload-dev` mapping for wherever you put them; `packages/io/tests/fixture/` /
`Psl\IO\Tests\Fixture\` is not wired up on the base commit.

### Files NOT to touch

- `packages/http-client/` and `packages/message/` — out of scope entirely.
- Existing handle classes, interfaces, and convenience traits in `packages/io/src/Psl/IO/`
  — the nine new classes must fit the existing contracts, not change them.
- Existing tests anywhere in the repository.
- `composer.json`, `config/phpunit.xml.dist`, and the rest of the build configuration —
  the nine new classes need no build changes.

### Constraints

- PHP 8.4. Use the syntax and type style of the surrounding code: `declare(strict_types=1)`,
  constructor property promotion, `readonly` where appropriate, `final` classes,
  `#[Override]` on interface methods, and the psalm-flavored docblock types the package
  already uses (`non-negative-int`, `positive-int`, `int<0, max>`).
- Do not break any existing public API or any existing test.
- No network access, no filesystem access outside the repository, no timing-dependent
  behavior. All nine classes must be deterministic and testable with in-memory handles.
- Do not add third-party dependencies.

---

## Hints

Read these before starting — the new classes must satisfy the contracts they declare:

- `packages/io/src/Psl/IO/ReadHandleInterface.php` — `read`, `tryRead`,
  `reachedEndOfDataSource` signatures and semantics.
- `packages/io/src/Psl/IO/WriteHandleInterface.php` — `write`, `tryWrite` semantics,
  including that a write may legitimately be short.
- `packages/io/src/Psl/IO/BufferedWriteHandleInterface.php` — the `flush` contract.
- `packages/io/src/Psl/IO/CloseHandleInterface.php` — `close` / `isClosed`.
- `packages/io/src/Psl/IO/ReadHandleConvenienceMethodsTrait.php` and
  `packages/io/src/Psl/IO/WriteHandleConvenienceMethodsTrait.php` — what you get for free
  (`readAll`, `readFixedSize`, `writeAll`, …) and what they expect from you.
- `packages/io/src/Psl/IO/Exception/` — the available exception classes
  (`AlreadyClosedException`, `RuntimeException`, `OverflowException`).
- `packages/io/src/Psl/IO/MemoryHandle.php` and
  `packages/io/src/Psl/IO/IterableReadHandle.php` — reference implementations showing the
  house style for closed-state assertions, EOF handling, and `__destruct`.
- Note that this package has no `ReadWriteHandleInterface`; a read/write handle is one
  that implements the read interface and a write interface together.

---

## Test Files

These are the **grading sets**. You do not create these files — they are supplied by the
evaluation harness. They are listed so you know what is measured.

**Fail-to-Pass** (must fail on the base commit, pass after your change):

- `packages/io/tests/unit/ConcatReadHandleTest.php`
- `packages/io/tests/unit/FixedLengthReadHandleTest.php`
- `packages/io/tests/unit/BoundedReadHandleTest.php`
- `packages/io/tests/unit/TruncatedReadHandleTest.php`
- `packages/io/tests/unit/TeeWriteHandleTest.php`
- `packages/io/tests/unit/JoinedReadWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadHandleTest.php`
- `packages/io/tests/unit/SinkWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadWriteHandleTest.php`

**Pass-to-Pass** (visible in your tree; must stay green before and after):

- `packages/io/tests/unit/StreamTest.php`
- `packages/io/tests/unit/SpoolTest.php`
- `packages/io/tests/unit/ReaderTest.php`
- `packages/io/tests/unit/PipeTest.php`
- `packages/io/tests/unit/MemoryHandleTest.php`
- `packages/io/tests/unit/IterableReadHandleTest.php`
- `packages/io/tests/unit/CopyTest.php`
- `packages/io/tests/unit/CopyBidirectionalTest.php`

Run the visible suite with the repository's own configuration, for example:

```bash
composer install
./vendor/bin/phpunit -c config/phpunit.xml.dist packages/io/tests/unit/
```

---

## Commits

The bundle's `golden-solution` branch uses the following commit topology. Commit SHAs are
recorded in the task metadata, not here.

| Type | Purpose |
|------|---------|
| base | php-standard-library snapshot before the relevant PR (pre-solution state) |
| `[sol]` | solution code |
| `[f2p]` | fail-to-pass tests |
| `[meta]` | metadata + task docs |
