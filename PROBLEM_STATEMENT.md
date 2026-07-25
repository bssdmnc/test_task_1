# Task: Add composable IO handle decorators to php-standard-library

**instance_id:** `php-standard-library__php-standard-library__740`
**language:** PHP
**task_type:** feature
**task_category:** io

---

## Problem Statement

Title: Add composable IO handle decorators for `ReadHandleInterface`, `WriteHandleInterface`, and `ReadWriteHandleInterface`

Current behavior:
- The `Psl\IO` package lacks reusable decorators for composing stream handles.
- Equivalent wrapper logic is duplicated ad hoc across internal packages.
- There is no standard way to concatenate readers, cap read length, mirror writes, or provide `/dev/null`-style sink handles.

Reproduction steps:
1. Open `base/packages/io/src/Psl/IO/`.
2. Note that classes such as `ConcatReadHandle`, `FixedLengthReadHandle`, `BoundedReadHandle`, `TruncatedReadHandle`, `TeeWriteHandle`, `JoinedReadWriteHandle`, `SinkReadHandle`, `SinkWriteHandle`, and `SinkReadWriteHandle` are missing.
3. Attempt to compose a bounded read pipeline or tee writes using only existing public classes; this is impossible without custom local wrappers.

Expected behavior:
Add composable decorator classes under `base/packages/io/src/Psl/IO/`:
- `ConcatReadHandle`: read from two handles sequentially.
- `FixedLengthReadHandle`: read exactly N bytes or fail on premature EOF.
- `BoundedReadHandle`: cap total bytes and detect overflow.
- `TruncatedReadHandle`: silently report EOF at a byte limit.
- `TeeWriteHandle`: mirror writes to two write handles.
- `JoinedReadWriteHandle`: join a read handle and write handle into one read-write handle.
- `SinkReadHandle`, `SinkWriteHandle`, `SinkReadWriteHandle`: no-op discard handles.

Files to create/modify:
- `packages/io/src/Psl/IO/ConcatReadHandle.php`
- `packages/io/src/Psl/IO/FixedLengthReadHandle.php`
- `packages/io/src/Psl/IO/BoundedReadHandle.php`
- `packages/io/src/Psl/IO/TruncatedReadHandle.php`
- `packages/io/src/Psl/IO/TeeWriteHandle.php`
- `packages/io/src/Psl/IO/JoinedReadWriteHandle.php`
- `packages/io/src/Psl/IO/SinkReadHandle.php`
- `packages/io/src/Psl/IO/SinkWriteHandle.php`
- `packages/io/src/Psl/IO/SinkReadWriteHandle.php`
- `packages/io/tests/fixture/NonCloseableWriteHandle.php`
- `packages/io/tests/fixture/SlowWriteHandle.php`
- `packages/io/tests/unit/ConcatReadHandleTest.php`
- `packages/io/tests/unit/FixedLengthReadHandleTest.php`
- `packages/io/tests/unit/BoundedReadHandleTest.php`
- `packages/io/tests/unit/TruncatedReadHandleTest.php`
- `packages/io/tests/unit/TeeWriteHandleTest.php`
- `packages/io/tests/unit/JoinedReadWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadHandleTest.php`
- `packages/io/tests/unit/SinkWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadWriteHandleTest.php`

Files NOT to touch:
- `packages/http-client`
- `packages/message`
- Existing public IO handle classes unrelated to this task

Constraints:
- PHP 8.4 syntax and types.
- Implement `Psl\IO` interfaces and convenience traits used by existing handles.
- Close underlying handles that implement `CloseHandleInterface`; throw `AlreadyClosedException` after close.
- Do not break existing public APIs or tests.

---

## Hints

Key files and code locations:
- `packages/io/src/Psl/IO/ReadHandleInterface.php`
- `packages/io/src/Psl/IO/WriteHandleInterface.php`
- `packages/io/src/Psl/IO/ReadHandleConvenienceMethodsTrait.php`
- `packages/io/src/Psl/IO/WriteHandleConvenienceMethodsTrait.php`
- `packages/io/src/Psl/IO/MemoryHandle.php`
- `packages/io/src/Psl/IO/IterableReadHandle.php`

---

## Test Files

**Fail-to-Pass** (fail on base, pass after the solution):
- `packages/io/tests/unit/ConcatReadHandleTest.php`
- `packages/io/tests/unit/FixedLengthReadHandleTest.php`
- `packages/io/tests/unit/BoundedReadHandleTest.php`
- `packages/io/tests/unit/TruncatedReadHandleTest.php`
- `packages/io/tests/unit/TeeWriteHandleTest.php`
- `packages/io/tests/unit/JoinedReadWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadHandleTest.php`
- `packages/io/tests/unit/SinkWriteHandleTest.php`
- `packages/io/tests/unit/SinkReadWriteHandleTest.php`

**Pass-to-Pass** (pass before and after):
- `packages/io/tests/unit/StreamTest.php`
- `packages/io/tests/unit/SpoolTest.php`
- `packages/io/tests/unit/ReaderTest.php`
- `packages/io/tests/unit/PipeTest.php`
- `packages/io/tests/unit/MemoryHandleTest.php`
- `packages/io/tests/unit/IterableReadHandleTest.php`
- `packages/io/tests/unit/CopyTest.php`
- `packages/io/tests/unit/CopyBidirectionalTest.php`

---

## Commits

| SHA | Type | Message |
|-----|------|---------|
| `8aa52a6a5598c809c6b79591d292e43c4931ecac` | base | php-standard-library snapshot before PR #740 |
| `e36f571b907a8cd50fbe1272140a547ebd5bf084` | [sol] | add io handle decorators, test fixtures, and autoload wiring |
| `1ff9853114f737bf8ddc0186b25b0ad179f7677a` | [f2p] | add fail-to-pass io handle tests |
| `ed4f54b5100ac15e0ec9c62349a5410fb0bcd64e` | [meta] | metadata.json + task docs |
