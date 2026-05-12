"""Validate data/data.json against data/schema.json.

Run from the repository root:
    python data/validate.py

Exits with code 0 if data.json conforms to the schema, 1 otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

REPO = Path(__file__).resolve().parent.parent
SCHEMA_PATH = REPO / "data" / "schema.json"
DATA_PATH = REPO / "data" / "data.json"


def main() -> int:
    with SCHEMA_PATH.open() as f:
        schema = json.load(f)
    with DATA_PATH.open() as f:
        data = json.load(f)

    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    if errors:
        for err in errors:
            path = "/".join(str(p) for p in err.absolute_path) or "<root>"
            print(f"[{path}] {err.message}", file=sys.stderr)
        print(f"\nFAIL: {len(errors)} schema violation(s)", file=sys.stderr)
        return 1

    sections = data.get("Data Sets", [])
    subsections = sum(len(s.get("subsections", [])) for s in sections)
    items = sum(
        len(sub.get("items", []))
        for s in sections
        for sub in s.get("subsections", [])
    )
    print(
        f"OK: data.json conforms to schema "
        f"({len(sections)} sections, {subsections} subsections, {items} items)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
