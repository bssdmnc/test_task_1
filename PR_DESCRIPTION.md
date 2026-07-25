# [GOLDEN SOLUTION] Add composable IO handle decorators

## Problem

- The `Psl\IO` package on base lacks reusable decorators for composing stream handles.
- Equivalent wrapper logic is duplicated ad hoc across internal packages.
- There is no standard way to concatenate readers, cap read length, mirror writes, or provide `/dev/null`-style sink handles.

## Approach

Add composable decorator classes in `packages/io/src/Psl/IO/`:
- `ConcatReadHandle`: sequential read from two handles.
- `FixedLengthReadHandle`: exact N-byte read contract.
- `BoundedReadHandle`: total read cap with overflow detection.
- `TruncatedReadHandle`: silent EOF at byte limit.
- `TeeWriteHandle`: mirrored writes.
- `JoinedReadWriteHandle`: read/write handle composition.
- `SinkReadHandle`, `SinkWriteHandle`, `SinkReadWriteHandle`: discard handles.

Key decisions vs. the original PR:
- Keep scope limited to IO package only; do not refactor `http-client` or `message`.
- Preserve existing public APIs and convenience traits; reuse interface contracts verbatim.
- Handle closed-state invariants immediately and throw `AlreadyClosedException` after close.

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
| MOD | `packages/io/tests/fixture/NonCloseableWriteHandle.php` |
| MOD | `packages/io/tests/fixture/SlowWriteHandle.php` |
| NEW | `packages/io/tests/unit/ConcatReadHandleTest.php` |
| NEW | `packages/io/tests/unit/FixedLengthReadHandleTest.php` |
| NEW | `packages/io/tests/unit/BoundedReadHandleTest.php` |
| NEW | `packages/io/tests/unit/TruncatedReadHandleTest.php` |
| NEW | `packages/io/tests/unit/TeeWriteHandleTest.php` |
| NEW | `packages/io/tests/unit/JoinedReadWriteHandleTest.php` |
| NEW | `packages/io/tests/unit/SinkReadHandleTest.php` |
| NEW | `packages/io/tests/unit/SinkWriteHandleTest.php` |
| NEW | `packages/io/tests/unit/SinkReadWriteHandleTest.php` |

## Testing Strategy

**Fail-to-Pass** (`packages/io/tests/unit/...`):
- `packages/io/tests/unit/ConcatReadHandleTest.php`
- `packages/io/tests/unit/FixedLengthReadHandleTest.php`
- `packages/io/tests/unit/BoundedReadHandleTest.php`
- `packages/io/tests/unit/TruncatedReadHandleTest.php`
- `packages/io/tests/unit/TeeWriteHandleTest.php`
- `packages/io/tests/unit/JoinedReadWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadHandleTest.php`
- `packages/io/tests/unit/SinkWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadWriteHandleTest.php`

Expected behavior: these tests fail on base because classes/helpers are missing; they pass after `[sol]`.

**Pass-to-Pass** (regression):
- `packages/io/tests/unit/StreamTest.php`
- `packages/io/tests/unit/SpoolTest.php`
- `packages/io/tests/unit/ReaderTest.php`
- `packages/io/tests/unit/PipeTest.php`
- `packages/io/tests/unit/MemoryHandleTest.php`
- `packages/io/tests/unit/IterableReadHandleTest.php`
- `packages/io/tests/unit/CopyTest.php`
- `packages/io/tests/unit/CopyBidirectionalTest.php`

Validated subsets:
- Base P2P run in Docker returned `OK (123 tests, 314 assertions)`.

Covered scenarios:
- Empty handle behavior and zero-length reads/writes.
- Partial reads and premature EOF for `FixedLengthReadHandle`.
- Overflow detection for `BoundedReadHandle`.
- Close semantics and `AlreadyClosedException`.
- Fixture autoload wiring in root `composer.json`.

## Commit Structure

```
9dcb6be [base]: php-standard-library snapshot before PR #740
7e8958d [sol]: add io handle decorators, test fixtures, and autoload wiring
3cb1dcf [f2p]: add fail-to-pass io handle tests
<next> [meta]: metadata.json + task docs
```
