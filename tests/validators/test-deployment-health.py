"""Validate deployment endpoints and basic health availability."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
import yaml


CONFIG_FILE = Path("config/deployment-config.yaml")


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _check_http(url: str, timeout: int = 10) -> tuple[bool, int | None, str]:
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code < 500, response.status_code, ""
    except requests.RequestException as exc:
        return False, None, str(exc)


def main() -> int:
    failures = 0

    if not CONFIG_FILE.exists():
        print("[FAIL] config/deployment-config.yaml not found")
        return 1

    docs = list(yaml.safe_load_all(CONFIG_FILE.read_text(encoding="utf-8")))
    config_map_data = {}
    for doc in docs:
        if isinstance(doc, dict) and doc.get("kind") == "ConfigMap":
            config_map_data = doc.get("data", {})
            break

    pizza_api_url = os.getenv("PIZZA_API_URL") or config_map_data.get("pizza_api_url")
    registration_api_url = os.getenv("REGISTRATION_API_URL") or config_map_data.get("registration_api_url")

    for label, base_url in (
        ("pizza_api", pizza_api_url),
        ("registration_api", registration_api_url),
    ):
        if not base_url:
            print(f"[FAIL] {label} URL missing")
            failures += 1
            continue

        normalized = _normalize_url(base_url)
        ok, status_code, error = _check_http(normalized)
        if not ok:
            # Fall back to /health if base path fails.
            health_ok, health_status, health_error = _check_http(f"{normalized}/health")
            if health_ok:
                print(f"[PASS] {label} reachable at /health ({health_status})")
            else:
                failures += 1
                detail = error or health_error
                print(f"[FAIL] {label} not reachable ({detail})")
        else:
            print(f"[PASS] {label} reachable ({status_code})")

    if failures:
        print(f"\nDeployment health check failed: {failures} issue(s).")
        return 1

    print("\nDeployment health check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
