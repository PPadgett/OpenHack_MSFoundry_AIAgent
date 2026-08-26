"""Local mock MCP SSE endpoint for offline lab replay."""

from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from datetime import datetime, UTC

TOOLS = [
    "list_menu",
    "create_order",
    "get_order_status",
    "cancel_order",
    "get_customer_orders",
]


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class MockMcpHandler(BaseHTTPRequestHandler):
    server_version = "MockMCP/1.0"

    def log_message(self, fmt: str, *args) -> None:
        print("[mcp] %s" % (fmt % args))

    def _send_json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        if not raw:
            return {}
        return json.loads(raw)

    def do_GET(self) -> None:
        if self.path in ("/", ""):
            self._send_json(
                200,
                {
                    "service": "mock-mcp",
                    "status": "ok",
                    "sse": "/sse",
                    "tools": TOOLS,
                },
            )
            return

        if self.path == "/health":
            self._send_json(200, {"status": "ok", "service": "mock-mcp"})
            return

        if self.path == "/tools":
            self._send_json(200, {"tools": TOOLS})
            return

        if self.path.startswith("/sse"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            capabilities = {
                "protocol": "mock-mcp-sse",
                "tools": TOOLS,
                "timestamp": _iso_now(),
            }
            self.wfile.write(b"event: capabilities\n")
            self.wfile.write(f"data: {json.dumps(capabilities)}\n\n".encode("utf-8"))
            self.wfile.flush()

            try:
                for i in range(1, 120):
                    heartbeat = {"heartbeat": i, "timestamp": _iso_now()}
                    self.wfile.write(b"event: heartbeat\n")
                    self.wfile.write(f"data: {json.dumps(heartbeat)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                    time.sleep(5)
            except BrokenPipeError:
                return
            return

        self._send_json(404, {"error": "not found", "path": self.path})

    def do_POST(self) -> None:
        if self.path != "/invoke":
            self._send_json(404, {"error": "not found", "path": self.path})
            return

        payload = self._read_json()
        tool_name = payload.get("tool")
        if tool_name not in TOOLS:
            self._send_json(400, {"error": "unknown_tool", "tool": tool_name})
            return

        self._send_json(
            200,
            {
                "ok": True,
                "tool": tool_name,
                "arguments": payload.get("arguments", {}),
                "result": {
                    "mock": True,
                    "tool": tool_name,
                    "timestamp": _iso_now(),
                },
            },
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local mock MCP SSE server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockMcpHandler)
    print(f"Mock MCP SSE server running at http://{args.host}:{args.port}/sse")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
