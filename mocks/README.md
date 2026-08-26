# Offline Mock Stack

Use these mocks to run the lab after hosted endpoints are unavailable.

## Start Services

One command from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File mocks/start-mocks.ps1 -Action start
```

Other actions:

```powershell
powershell -ExecutionPolicy Bypass -File mocks/start-mocks.ps1 -Action status
powershell -ExecutionPolicy Bypass -File mocks/start-mocks.ps1 -Action health
powershell -ExecutionPolicy Bypass -File mocks/start-mocks.ps1 -Action stop
```

Manual mode (three terminals) is still available:

1. Pizza API mock (localhost:7071)

```powershell
c:/Users/demouser/OpenHack_MSFoundry_AIAgent/.venv/Scripts/python.exe mocks/mock_api_server.py --service pizza --port 7071
```

2. Registration API mock (localhost:7072)

```powershell
c:/Users/demouser/OpenHack_MSFoundry_AIAgent/.venv/Scripts/python.exe mocks/mock_api_server.py --service registration --port 7072
```

3. MCP SSE mock (localhost:8081/sse)

```powershell
c:/Users/demouser/OpenHack_MSFoundry_AIAgent/.venv/Scripts/python.exe mocks/mock_mcp_sse_server.py --port 8081
```

## Switch Environment to Mock Mode

Use values from [.env.mock](../.env.mock) in your active environment.

Minimum required variables:

- PIZZA_API_URL=http://localhost:7071/
- REGISTRATION_API_URL=http://localhost:7072/
- PIZZA_MCP_URL=http://localhost:8081/sse
- PIZZA_WEBAPP_URL=http://localhost:4173/

## Quick Health Checks

```powershell
curl http://localhost:7071/health
curl http://localhost:7072/health
curl http://localhost:8081/health
curl http://localhost:7071/api/menu
```

## Implemented Mock Routes

### Pizza API

- GET /health
- GET /api/menu
- GET /api/allergens
- POST /api/price
- POST /api/orders
- GET /api/orders/{order_id}
- POST /api/escalations

### Registration API

- GET /health
- GET /api/registration/ping
- POST /api/registration/create

### MCP

- GET /health
- GET /tools
- GET /sse (Server-Sent Events stream)

## Notes

- Mock responses are deterministic and sufficient for local tool-flow testing.
- Order state is in-memory and resets when the process restarts.
- This stack does not emulate cloud auth; it is for local functional replay.
- Runtime PID files are written to mocks/.run and logs to mocks/logs.
