# Mock Endpoints Inventory

This page lists all project endpoints that should be mocked to run the lab offline.

## External Base Endpoints in Current Lab

| Surface | Environment Variable | Current URL |
| --- | --- | --- |
| Pizza API | PIZZA_API_URL | https://func-pizza-api-ceki46omdafoe.azurewebsites.net/ |
| Registration API | REGISTRATION_API_URL | https://func-registration-api-ceki46omdafoe.azurewebsites.net/ |
| Pizza Web App | PIZZA_WEBAPP_URL | https://green-bush-0d277aa0f.7.azurestaticapps.net/ |
| Registration Web App | REGISTRATION_WEBAPP_URL | https://victorious-glacier-0bd2fb00f.7.azurestaticapps.net/ |
| Contoso MCP SSE | PIZZA_MCP_URL | https://ca-pizza-mcp-ceki46omdafoe.gentlehill-7ae690c8.westus3.azurecontainerapps.io/sse |

## Tool API Routes to Mock

These are called by Python tool implementations.

| Tool | Method | Route |
| --- | --- | --- |
| menu_lookup | GET | /api/menu |
| allergen_lookup | GET | /api/allergens |
| price_calc | POST | /api/price |
| order_submit | POST | /api/orders |
| order_status | GET | /api/orders/{order_id} |
| human_handoff | POST | /api/escalations |

## Operational Routes to Mock

| Purpose | Route |
| --- | --- |
| Generic health | /health |
| API probe | /api/menu |

## MCP Surface to Mock

Configured MCP tools in agent definition:

- list_menu
- create_order
- get_order_status
- cancel_order
- get_customer_orders

## Recommended Local Mock Targets

| Surface | Local Target |
| --- | --- |
| Pizza API | http://localhost:7071 |
| Registration API | http://localhost:7072 |
| MCP SSE | http://localhost:8081/sse |
| Pizza Web App | http://localhost:4173 |

## Source of Truth in Repo

- Endpoint env and route vars: [.env](../.env)
- Deployment endpoint map: [config/deployment-config.yaml](../config/deployment-config.yaml)
- MCP endpoint and allowed tools: [agent-definition.yaml](../agent-definition.yaml)
- Runtime route usage: [tools/tool_implementations.py](../tools/tool_implementations.py)
- Playwright app endpoint usage: [tests/playwright/playwright.config.ts](../tests/playwright/playwright.config.ts)
- Integration endpoint usage: [tests/integration/test_live_endpoints.py](../tests/integration/test_live_endpoints.py)
