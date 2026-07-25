#!/usr/bin/env python3
"""csvcol.py — extract a single column from the eval-task metadata.csv.

Usage:
    python csvcol.py <file.csv> <column> [options]

`<column>` may be a header name (`problem_statement`, `golden_commit`, …) or
a 1-based index (`15`). Prefix with `@` to force name mode when a name collides
with a number (e.g. `@15`).

The CSV uses standard RFC-4180 quoting; fields may contain commas, newlines,
and embedded escaped sequences such as `\\n` (a literal backslash + n).
Do **not** use `cut -d,` — it breaks on the embedded commas.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from pathlib import Path
from typing import Iterable, Sequence


def _parse_column(arg: str, headers: Sequence[str]) -> tuple[str, bool]:
    """Return (column key, is_int_flag)."""
    if arg.startswith("@"):
        return arg[1:], False
    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(headers):
            return headers[idx], True
        raise SystemExit(f"column index {arg!r} out of range (1..{len(headers)})")
    if arg in headers:
        return arg, False
    raise SystemExit(f"unknown column {arg!r}; pass --list-cols to see names")


def _load_rows(path: Path) -> tuple[Sequence[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8", newline="")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        raise SystemExit(f"{path} is empty")
    headers = rows[0]
    data = [dict(zip(headers, r)) for r in rows[1:]]
    return headers, data


def _filter(rows: list[dict[str, str]], filters: list[tuple[str, str]]) -> list[dict[str, str]]:
    out = rows
    for col, val in filters:
        out = [r for r in out if r.get(col, "") == val]
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract a column from metadata.csv")
    parser.add_argument("csv_path", type=Path)
    parser.add_argument("column", nargs="?", help="column name or 1-based index")
    parser.add_argument("--full", action="store_true", help="print full field (default: 200-char preview + length)")
    parser.add_argument("--len", action="store_true", help="print only the byte/char length")
    parser.add_argument("--json", action="store_true", help="emit value(s) as a JSON array")
    parser.add_argument("--index", action="store_true", help="prefix each value with its row number (header=row 0)")
    parser.add_argument("--unescape", action="store_true", help="replace literal \\\\n with real newlines in the output")
    parser.add_argument("--list-cols", action="store_true", help="list header names + index, then exit")
    parser.add_argument("--row", action="append", default=[], metavar="COL=VAL",
                        help="filter to rows where COL equals VAL (repeatable)")
    args = parser.parse_args(argv)

    if not args.csv_path.exists():
        raise SystemExit(f"{args.csv_path}: not found")

    headers, rows = _load_rows(args.csv_path)

    if args.list_cols:
        for i, h in enumerate(headers, 1):
            print(f"{i:>3}  {h}")
        print(f"\n{len(headers)} columns, {len(rows)} data rows")
        return 0

    if not args.column:
        parser.error("column is required (or pass --list-cols)")

    filters: list[tuple[str, str]] = []
    for spec in args.row:
        if "=" not in spec:
            raise SystemExit(f"--row expects COL=VAL, got {spec!r}")
        k, v = spec.split("=", 1)
        filters.append((k, v))

    selected = _filter(rows, filters)
    key, _ = _parse_column(args.column, headers)

    values = [r.get(key, "") for r in selected]

    if args.unescape:
        values = [v.replace("\\n", "\n") for v in values]

    if args.json:
        json.dump(values, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0

    if args.len:
        for v in values:
            print(len(v))
        return 0

    for i, v in enumerate(values):
        if args.index:
            row_no = (i + 1) + (1 if not filters else 0)  # data rows start at 1
            # recompute actual row number from the original file when filtered
            print(f"row {row_no}:", end=" ")
        if args.full:
            print(v)
        else:
            preview = v if len(v) <= 200 else v[:200] + f"…[{len(v)} chars]"
            print(preview)
    return 0


if __name__ == "__main__":
    sys.exit(main())