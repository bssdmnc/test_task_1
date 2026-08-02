#!/usr/bin/env python3
"""Extract a single column from a CSV whose fields contain embedded commas,
quotes, and newlines.

`metadata.csv` stores whole Markdown documents and whole shell scripts inside
quoted fields. Splitting it with `cut -d,` or `awk -F,` shifts every column and
silently produces wrong answers, so this helper parses the file with the stdlib
csv module instead.

Usage:
    python csvcol.py <file.csv> <column> [options]
    python csvcol.py <file.csv> --list-cols

<column> is a header name (problem_statement, golden_commit, ...) or a 1-based
index (15). Prefix with @ to force name mode when a name looks like a number.

Options:
    --full          print the whole field (default previews 200 chars + length)
    --len           print only the length of the value
    --json          emit values as a JSON array
    --index         prefix each value with its row number (header = row 0)
    --row COL=VAL   only rows where header COL equals VAL (repeatable)
    --list-cols     print header names with their 1-based index, then exit
    --unescape      turn literal \\n / \\t / \\r sequences into real characters

Note on --unescape: this bundle's metadata.csv keeps one record on one physical
line, storing newlines inside fields as the literal sequence \n (see AGENTS.md,
metadata.csv fill recipe). So --unescape is the normal way to read a multi-line
field back as text; without it you get the escaped form as stored on disk.
Quoting still follows RFC 4180 — fields with commas or quotes are quoted and
inner quotes doubled.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

PREVIEW = 200


def unescape(value: str) -> str:
    return value.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")


def resolve_column(header: list[str], column: str) -> int:
    """Return the 0-based index of `column` within `header`."""
    if column.startswith("@"):
        name = column[1:]
        if name not in header:
            raise SystemExit(f"csvcol: no such column: {name!r}")
        return header.index(name)

    if column in header:
        return header.index(column)

    try:
        index = int(column)
    except ValueError:
        raise SystemExit(
            f"csvcol: no such column: {column!r}\n"
            f"csvcol: available: {', '.join(header)}"
        ) from None

    if not 1 <= index <= len(header):
        raise SystemExit(
            f"csvcol: index {index} out of range (1..{len(header)})"
        )
    return index - 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(add_help=True, description=__doc__)
    parser.add_argument("file")
    parser.add_argument("column", nargs="?")
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--len", dest="length", action="store_true")
    parser.add_argument("--json", dest="as_json", action="store_true")
    parser.add_argument("--index", action="store_true")
    parser.add_argument("--row", action="append", default=[], metavar="COL=VAL")
    parser.add_argument("--list-cols", action="store_true")
    parser.add_argument("--unescape", action="store_true")
    args = parser.parse_args(argv)

    # newline="" is required: without it, Python's universal newline handling
    # mangles the newlines embedded inside quoted fields.
    with open(args.file, newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))

    if not rows:
        raise SystemExit(f"csvcol: {args.file} is empty")

    header, data = rows[0], rows[1:]

    if args.list_cols:
        for position, name in enumerate(header, start=1):
            print(f"{position:>3}  {name}")
        return 0

    if args.column is None:
        parser.error("a column is required unless --list-cols is given")

    index = resolve_column(header, args.column)

    filters = []
    for spec in args.row:
        if "=" not in spec:
            raise SystemExit(f"csvcol: --row expects COL=VAL, got {spec!r}")
        name, _, wanted = spec.partition("=")
        if name not in header:
            raise SystemExit(f"csvcol: --row references unknown column {name!r}")
        filters.append((header.index(name), wanted))

    selected = []
    for row_number, row in enumerate(data, start=1):
        if any(position >= len(row) or row[position] != wanted
               for position, wanted in filters):
            continue
        value = row[index] if index < len(row) else ""
        selected.append((row_number, unescape(value) if args.unescape else value))

    if args.as_json:
        json.dump([value for _, value in selected], sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    for row_number, value in selected:
        prefix = f"[{row_number}] " if args.index else ""
        if args.length:
            print(f"{prefix}{len(value)}")
        elif args.full:
            print(f"{prefix}{value}")
        elif len(value) > PREVIEW:
            print(f"{prefix}{value[:PREVIEW]}... ({len(value)} chars)")
        else:
            print(f"{prefix}{value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
