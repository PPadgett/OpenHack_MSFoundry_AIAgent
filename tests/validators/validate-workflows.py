"""Validate workflow structure and transition references."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


WORKFLOW_FILE = Path("workflows/ordering-workflow.yaml")


def main() -> int:
    if not WORKFLOW_FILE.exists():
        print("[FAIL] workflows/ordering-workflow.yaml not found")
        return 1

    workflow = yaml.safe_load(WORKFLOW_FILE.read_text(encoding="utf-8"))
    spec = workflow.get("spec", {})
    states = spec.get("states", [])

    if not states:
        print("[FAIL] No states found in workflow")
        return 1

    state_names = {s.get("name") for s in states if isinstance(s, dict) and s.get("name")}
    initial_state = spec.get("initial_state")
    failures = 0

    if initial_state in state_names:
        print(f"[PASS] Initial state exists: {initial_state}")
    else:
        print(f"[FAIL] initial_state '{initial_state}' missing from states")
        failures += 1

    terminal_states = {
        s.get("name")
        for s in states
        if isinstance(s, dict) and s.get("type") == "end" and s.get("name")
    }
    if terminal_states:
        print(f"[PASS] Terminal states found: {sorted(terminal_states)}")
    else:
        print("[FAIL] No terminal states (type: end) defined")
        failures += 1

    for state in states:
        name = state.get("name", "<unnamed>")
        transitions = state.get("transitions", [])
        for transition in transitions:
            next_state = transition.get("next_state")
            if next_state and next_state not in state_names:
                print(f"[FAIL] State '{name}' references missing next_state '{next_state}'")
                failures += 1

    # Safety-critical states expected in this workflow.
    for required_state in ("collect_allergies", "allergen_disclosure", "submit"):
        if required_state in state_names:
            print(f"[PASS] Required state present: {required_state}")
        else:
            print(f"[FAIL] Missing required state: {required_state}")
            failures += 1

    if failures:
        print(f"\nWorkflow validation failed: {failures} issue(s).")
        return 1

    print("\nWorkflow validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
