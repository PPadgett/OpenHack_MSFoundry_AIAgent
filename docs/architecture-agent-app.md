# Agent and App Architecture

This diagram reflects the current agent runtime shape defined by agent-definition.yaml, tools/tool_implementations.py, and config/deployment-config.yaml.

## System Diagram

```mermaid
flowchart LR
    U[Customer]
    W[Pizza Web App\nAzure Static Web App]
    A[Crust Agent\nMicrosoft Foundry]
    M[MCP Server\nContoso Pizza SSE]
    T[Tool Runtime\ntools/tool_implementations.py]
    P[Pizza API\nAzure Functions]
    R[Registration API\nAzure Functions]
    H[Human Support Queue]
    S[Safety Controls\nPrompt Shields + Content Filters]
    C[Contracts\nagent-definition.yaml + tools/*.json]
    D[Data Schema\nschemas/customer-profile.schema.json]

    U --> W
    W --> A
    A --> S
    A --> M
    A --> T
    T --> P
    T --> R
    T --> H
    A -. validated by .-> C
    A -. profile shape .-> D
```

## Runtime Notes

- MCP endpoint is the live ordering capability layer for menu, create order, status, and cancellation.
- Python tools call REST endpoints for menu/allergen/price/order/escalation operations.
- Safety controls are configured in the agent definition and applied before/around generation.
- Schema and tool contracts are enforced by validator scripts in tests/validators.

## Interaction Flow (High Level)

```mermaid
sequenceDiagram
    participant User
    participant WebApp as Pizza Web App
    participant Agent as Crust Agent
    participant MCP as Contoso MCP
    participant Tools as Tool Runtime
    participant API as Pizza API

    User->>WebApp: Submit order request
    WebApp->>Agent: User message
    Agent->>MCP: Live menu or order action (as needed)
    Agent->>Tools: price_calc / allergen_lookup / order_submit
    Tools->>API: REST call
    API-->>Tools: JSON response
    Tools-->>Agent: Structured result
    Agent-->>WebApp: Response with guardrails and confirmation
    WebApp-->>User: Final response
```
