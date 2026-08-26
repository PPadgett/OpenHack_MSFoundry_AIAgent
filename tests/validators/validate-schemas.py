"""Validate JSON schemas and tool contract schema files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft7Validator


SCHEMA_FILES = [
    Path("schemas/customer-profile.schema.json"),
    Path("tools/menu_lookup.json"),
    Path("tools/allergen_lookup.json"),
    Path("tools/price_calc.json"),
    Path("tools/order_submit.json"),
    Path("tools/order_status.json"),
    Path("tools/human_handoff.json"),
]


def main() -> int:
    failures = 0
    for path in SCHEMA_FILES:
        if not path.exists():
            print(f"[FAIL] Missing file: {path}")
            failures += 1
            continue

        try:
            schema_obj = json.loads(path.read_text(encoding="utf-8"))
            Draft7Validator.check_schema(schema_obj)
            print(f"[PASS] Valid schema syntax: {path}")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Invalid schema: {path} -> {exc}")
            failures += 1

    if failures:
        print(f"\nSchema validation failed: {failures} issue(s).")
        return 1

    print("\nAll schema files are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
