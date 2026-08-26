"""Launch-blocking allergen safety verification checks."""

from __future__ import annotations

import sys
from pathlib import Path


REQUIRED_FILES = {
    Path("agent-definition.yaml"): [
        "never",
        "cross-contact",
        "allergen_lookup",
        "human_handoff",
    ],
    Path("workflows/ordering-workflow.yaml"): [
        "collect_allergies",
        "allergen_disclosure",
        "ALWAYS disclose cross-contact risk",
    ],
    Path("safety/allergen-safety-rules.yaml"): [
        "allergen_never_safe",
        "allergen_always_disclose_cross_contact",
        "allergen_use_tool_never_guess",
    ],
}


def main() -> int:
    failures = 0
    for file_path, expected_terms in REQUIRED_FILES.items():
        if not file_path.exists():
            print(f"[FAIL] Missing required file: {file_path}")
            failures += 1
            continue

        content = file_path.read_text(encoding="utf-8")
        lowered = content.lower()

        for term in expected_terms:
            if term.lower() in lowered:
                print(f"[PASS] {file_path}: found '{term}'")
            else:
                print(f"[FAIL] {file_path}: missing '{term}'")
                failures += 1

    if failures:
        print(f"\nAllergen safety verification failed: {failures} issue(s).")
        return 1

    print("\nAllergen safety verification passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
