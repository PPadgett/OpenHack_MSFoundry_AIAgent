"""Validate structural and safety-critical requirements in agent-definition.yaml."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


AGENT_FILE = Path("agent-definition.yaml")
REQUIRED_TOOLS = {
    "menu_lookup",
    "allergen_lookup",
    "price_calc",
    "order_submit",
    "order_status",
    "human_handoff",
}


def fail(message: str) -> None:
    print(f"[FAIL] {message}")


def ok(message: str) -> None:
    print(f"[PASS] {message}")


def main() -> int:
    if not AGENT_FILE.exists():
        fail("agent-definition.yaml not found")
        return 1

    data = yaml.safe_load(AGENT_FILE.read_text(encoding="utf-8"))

    checks_failed = 0

    if data.get("kind") == "Agent":
        ok("kind is Agent")
    else:
        fail("kind must be Agent")
        checks_failed += 1

    spec = data.get("spec", {})
    model = spec.get("model", {})
    if model.get("catalog_id"):
        ok("model.catalog_id is configured")
    else:
        fail("model.catalog_id is missing")
        checks_failed += 1

    temp = spec.get("temperature")
    if isinstance(temp, (int, float)) and temp <= 0.3:
        ok("temperature is <= 0.3")
    else:
        fail("temperature should be <= 0.3 for accuracy")
        checks_failed += 1

    tools = spec.get("tools", [])
    configured_tool_names = {tool.get("name") for tool in tools if isinstance(tool, dict)}
    missing_tools = REQUIRED_TOOLS - configured_tool_names
    if not missing_tools:
        ok("all required tools are defined")
    else:
        fail(f"missing required tools: {sorted(missing_tools)}")
        checks_failed += 1

    instructions = str(spec.get("instructions", "")).lower()
    for required_phrase in (
        "can't guarantee",
        "cross-contact",
        "allergen_lookup",
        "price_calc",
        "human_handoff",
    ):
        if required_phrase in instructions:
            ok(f"instructions include: {required_phrase}")
        else:
            fail(f"instructions missing required phrase: {required_phrase}")
            checks_failed += 1

    safety = spec.get("safety", {})
    prompt_shields = safety.get("prompt_shields", {})
    if prompt_shields.get("enabled") and prompt_shields.get("jailbreak_detection") and prompt_shields.get("xpia_detection"):
        ok("prompt shields are enabled with jailbreak + XPIA detection")
    else:
        fail("prompt shields configuration is incomplete")
        checks_failed += 1

    deployment = spec.get("deployment", {})
    regions = set(deployment.get("regions", []))
    expected_regions = {"eastus2", "westus3"}
    if expected_regions.issubset(regions):
        ok("deployment regions aligned to Azure targets")
    else:
        fail(f"deployment.regions should include {sorted(expected_regions)}")
        checks_failed += 1

    if checks_failed:
        print(f"\nValidation failed with {checks_failed} issue(s).")
        return 1

    print("\nagent-definition.yaml validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
