"""Local mock API server for offline lab replay.

Supports two service modes:
- pizza: implements endpoints used by tool_implementations.py
- registration: basic health and registration endpoints
"""

from __future__ import annotations

import argparse
import json
import uuid
from datetime import datetime, timedelta, UTC
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PIZZA_CATALOG = [
    {
        "id": "pizza_margherita_l",
        "name": "Margherita",
        "description": "Fresh mozzarella, basil, red sauce",
        "price": 16.99,
        "size": "large",
        "crust": "hand-tossed",
        "available": True,
    },
    {
        "id": "pizza_pepperoni_l",
        "name": "Pepperoni",
        "description": "Classic pepperoni and mozzarella",
        "price": 18.4,
        "size": "large",
        "crust": "hand-tossed",
        "available": True,
    },
    {
        "id": "pizza_veggie_m",
        "name": "Garden Veggie",
        "description": "Bell pepper, onion, olive, mushroom",
        "price": 15.5,
        "size": "medium",
        "crust": "thin",
        "available": True,
    },
]

ALLERGENS = {
    "pizza_margherita_l": {
        "allergens": ["milk", "wheat"],
        "cross_contact_risk": True,
        "contains_fda_big_nine": ["milk", "wheat"],
        "contains_eu_fourteen": ["milk", "wheat"],
        "preparation_notes": "Prepared in a shared kitchen.",
    },
    "pizza_pepperoni_l": {
        "allergens": ["milk", "wheat"],
        "cross_contact_risk": True,
        "contains_fda_big_nine": ["milk", "wheat"],
        "contains_eu_fourteen": ["milk", "wheat"],
        "preparation_notes": "Prepared in a shared kitchen.",
    },
    "pizza_veggie_m": {
        "allergens": ["wheat"],
        "cross_contact_risk": True,
        "contains_fda_big_nine": ["wheat"],
        "contains_eu_fourteen": ["wheat"],
        "preparation_notes": "Prepared in a shared kitchen.",
    },
}

ORDERS: dict[str, dict] = {}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length).decode("utf-8")
    if not raw:
        return {}
    return json.loads(raw)


def _find_item_price(item_id: str) -> float:
    for item in PIZZA_CATALOG:
        if item["id"] == item_id:
            return float(item["price"])
    return 12.99


class MockApiHandler(BaseHTTPRequestHandler):
    server_version = "MockApi/1.0"

    def _service(self) -> str:
        return getattr(self.server, "service", "pizza")

    def log_message(self, fmt: str, *args) -> None:
        print("[%s] %s" % (self._service(), fmt % args))

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path in ("/", ""):
            _json_response(
                self,
                200,
                {
                    "service": self._service(),
                    "status": "ok",
                    "message": "mock server online",
                    "time": _now_iso(),
                },
            )
            return

        if path == "/health":
            _json_response(self, 200, {"status": "ok", "service": self._service()})
            return

        if self._service() == "registration":
            if path == "/api/registration/ping":
                _json_response(self, 200, {"ok": True, "service": "registration"})
                return
            _json_response(self, 404, {"error": "registration endpoint not found", "path": path})
            return

        if path == "/api/menu":
            size = (query.get("size") or [None])[0]
            crust = (query.get("crust") or [None])[0]
            filtered = []
            for item in PIZZA_CATALOG:
                if size and item.get("size") != size:
                    continue
                if crust and item.get("crust") != crust:
                    continue
                filtered.append(item)
            _json_response(self, 200, {"items": filtered})
            return

        if path == "/api/allergens":
            item_id = (query.get("item_id") or [""])[0]
            if not item_id:
                _json_response(self, 400, {"error": "item_id is required"})
                return
            payload = ALLERGENS.get(
                item_id,
                {
                    "allergens": [],
                    "cross_contact_risk": True,
                    "contains_fda_big_nine": [],
                    "contains_eu_fourteen": [],
                    "preparation_notes": "Prepared in a shared kitchen.",
                },
            )
            _json_response(self, 200, payload)
            return

        if path.startswith("/api/orders/"):
            order_id = path.rsplit("/", 1)[-1]
            order = ORDERS.get(order_id)
            if not order:
                _json_response(self, 404, {"error": "order not found", "order_id": order_id})
                return

            eta = datetime.now(UTC) + timedelta(minutes=20)
            payload = {
                "order_id": order_id,
                "status": order.get("status", "submitted"),
                "pickup_time": eta.isoformat().replace("+00:00", "Z"),
                "delivery_eta": eta.isoformat().replace("+00:00", "Z"),
                "items": order.get("items", []),
                "total": order.get("total", 0.0),
            }
            _json_response(self, 200, payload)
            return

        _json_response(self, 404, {"error": "not found", "path": path})

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if self._service() == "registration":
            if path == "/api/registration/create":
                payload = _read_json(self)
                _json_response(
                    self,
                    201,
                    {
                        "registration_id": str(uuid.uuid4()),
                        "status": "created",
                        "payload": payload,
                    },
                )
                return
            _json_response(self, 404, {"error": "registration endpoint not found", "path": path})
            return

        if path == "/api/price":
            payload = _read_json(self)
            order_items = payload.get("items", [])
            subtotal = 0.0
            for item in order_items:
                item_id = item.get("item_id", "")
                qty = int(item.get("quantity", 1))
                subtotal += _find_item_price(item_id) * qty

            tax = round(subtotal * 0.085, 2)
            delivery_fee = 3.99 if payload.get("fulfillment_type") == "delivery" else 0.0
            total = round(subtotal + tax + delivery_fee, 2)
            _json_response(
                self,
                200,
                {
                    "subtotal": round(subtotal, 2),
                    "tax": tax,
                    "delivery_fee": delivery_fee,
                    "total": total,
                },
            )
            return

        if path == "/api/orders":
            payload = _read_json(self)
            order_id = payload.get("order_id") or str(uuid.uuid4())
            now = _now_iso()

            order_items = payload.get("items", [])
            subtotal = 0.0
            for item in order_items:
                item_id = item.get("item_id", "")
                qty = int(item.get("quantity", 1))
                subtotal += _find_item_price(item_id) * qty

            tax = round(subtotal * 0.085, 2)
            delivery_fee = 3.99 if payload.get("fulfillment_type") == "delivery" else 0.0
            total = round(subtotal + tax + delivery_fee, 2)

            order = {
                "order_id": order_id,
                "version": 1,
                "status": "submitted",
                "items": order_items,
                "subtotal": round(subtotal, 2),
                "tax": tax,
                "delivery_fee": delivery_fee,
                "total": total,
                "created_at": now,
                "updated_at": now,
            }
            ORDERS[order_id] = order
            _json_response(self, 200, order)
            return

        if path == "/api/escalations":
            payload = _read_json(self)
            _json_response(
                self,
                200,
                {
                    "ticket_id": str(uuid.uuid4()),
                    "queue_name": "mock-support",
                    "estimated_wait": "5-10 minutes",
                    "received": payload,
                },
            )
            return

        _json_response(self, 404, {"error": "not found", "path": path})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local mock API server")
    parser.add_argument("--service", choices=["pizza", "registration"], default="pizza")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7071)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockApiHandler)
    server.service = args.service

    print(f"Mock {args.service} server running at http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
