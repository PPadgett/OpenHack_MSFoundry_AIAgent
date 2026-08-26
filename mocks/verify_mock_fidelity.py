"""Verify local mock fidelity against project expectations.

Run after starting mocks:
  python mocks/verify_mock_fidelity.py
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, UTC, timedelta

import requests

PIZZA_API_URL = os.getenv("PIZZA_API_URL", "http://127.0.0.1:7071").rstrip("/")
REG_API_URL = os.getenv("REGISTRATION_API_URL", "http://127.0.0.1:7072").rstrip("/")
MCP_URL = os.getenv("PIZZA_MCP_URL", "http://127.0.0.1:8081/sse")


def assert_keys(payload: dict, required: list[str], label: str) -> None:
    missing = [k for k in required if k not in payload]
    if missing:
        raise AssertionError(f"{label} missing keys: {missing}")


def main() -> int:
    print("Checking base health endpoints...")
    assert requests.get(f"{PIZZA_API_URL}/health", timeout=5).status_code == 200
    assert requests.get(f"{REG_API_URL}/health", timeout=5).status_code == 200
    assert requests.get(MCP_URL.replace("/sse", "/health"), timeout=5).status_code == 200

    print("Checking menu response shape...")
    menu = requests.get(f"{PIZZA_API_URL}/api/menu", timeout=5).json()
    assert_keys(menu, ["items"], "menu")
    assert isinstance(menu["items"], list) and menu["items"], "menu items should be non-empty"
    assert_keys(
        menu["items"][0],
        ["id", "name", "description", "price", "size", "crust", "available"],
        "menu item",
    )

    print("Checking allergen response shape...")
    item_id = menu["items"][0]["id"]
    allergen = requests.get(
        f"{PIZZA_API_URL}/api/allergens", params={"item_id": item_id}, timeout=5
    ).json()
    assert_keys(
        allergen,
        [
            "allergens",
            "cross_contact_risk",
            "contains_fda_big_nine",
            "contains_eu_fourteen",
            "preparation_notes",
        ],
        "allergen",
    )

    print("Checking price response shape...")
    price = requests.post(
        f"{PIZZA_API_URL}/api/price",
        json={
            "items": [{"item_id": item_id, "quantity": 1}],
            "tax_jurisdiction": "CA",
            "fulfillment_type": "pickup",
        },
        timeout=5,
    ).json()
    assert_keys(price, ["subtotal", "tax", "delivery_fee", "total"], "price")

    print("Checking order submit idempotence and shape...")
    order_id = str(uuid.uuid4())
    now_plus = (datetime.now(UTC) + timedelta(minutes=20)).isoformat().replace("+00:00", "Z")
    order_payload = {
        "order_id": order_id,
        "customer_id": str(uuid.uuid4()),
        "items": [{"item_id": item_id, "quantity": 1}],
        "fulfillment_type": "pickup",
        "fulfillment_address": None,
        "fulfillment_time": now_plus,
        "allergen_flags": ["wheat"],
    }
    first = requests.post(f"{PIZZA_API_URL}/api/orders", json=order_payload, timeout=5).json()
    second = requests.post(f"{PIZZA_API_URL}/api/orders", json=order_payload, timeout=5).json()
    assert first == second, "order_submit should be idempotent for same order_id"
    assert_keys(
        first,
        [
            "order_id",
            "version",
            "status",
            "order_number",
            "confirmation_token",
            "subtotal",
            "tax",
            "delivery_fee",
            "total",
            "created_at",
            "updated_at",
        ],
        "order submit",
    )

    print("Checking order status shape...")
    status = requests.get(f"{PIZZA_API_URL}/api/orders/{order_id}", timeout=5).json()
    assert_keys(
        status,
        [
            "order_id",
            "status",
            "pickup_time",
            "delivery_eta",
            "items",
            "order_items",
            "total",
            "tracking_url",
            "order_number",
        ],
        "order status",
    )

    print("Checking human handoff shape...")
    escalation = requests.post(
        f"{PIZZA_API_URL}/api/escalations",
        json={"reason": "tool_failure", "priority": "normal", "context": {}},
        timeout=5,
    ).json()
    assert_keys(escalation, ["ticket_id", "queue_name", "estimated_wait"], "escalation")

    print("Checking MCP metadata endpoints...")
    tools = requests.get(MCP_URL.replace("/sse", "/tools"), timeout=5).json()
    assert_keys(tools, ["tools"], "mcp tools")

    invoke = requests.post(
        MCP_URL.replace("/sse", "/invoke"),
        json={"tool": "list_menu", "arguments": {}},
        timeout=5,
    ).json()
    assert_keys(invoke, ["ok", "tool", "arguments", "result"], "mcp invoke")

    print("All mock fidelity checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
