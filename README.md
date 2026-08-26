# Crust — Emo Pizza Ordering Agent for Microsoft Foundry

**Status:** Production-Ready Implementation Plan | **Version:** 1.0.0 | **Last Updated:** 2026-08-26

---

## Overview

**Crust** is a pizza-ordering assistant for restaurants built on Microsoft Foundry Agent Service. It combines a warm, emo/alt-indie persona with strict safety guardrails around food allergies, prices, and customer distress.

## Release Summary

Crust v1.0.0 is a production-ready Foundry agent blueprint for safe pizza ordering. The release includes a declarative agent contract, deterministic workflow, idempotent tool implementations, and launch-blocking allergen guardrails. It is pre-wired for Azure deployment targets, CI quality gates (lint, test, security scan), and enterprise privacy controls for profile data handling.

### Key Features

✅ **Declarative Agent Definition** — Fully YAML-based, versioned configuration  
✅ **Graph-Based Workflow** — No loops; deterministic state machine with explicit rails  
✅ **MCP Integration** — Remote Contoso Pizza MCP server handles live ordering, tracking, and cancellation  
✅ **Idempotent Tools** — Safe to retry; no double-charges or state corruption  
✅ **Allergen Safety** — Hard guardrails: never declares food "safe," always discloses cross-contact  
✅ **Immutable State** — Order transformations create new versions; no in-place mutations  
✅ **Ephemeral Sessions** — Thread data auto-deletes; only intentional profile writes persist  
✅ **Privacy-First Memory** — Explicit consent, GDPR Article 9 compliant, CMK encryption  
✅ **Prompt Injection Protection** — Foundry-native Prompt Shields + Content Filters  
✅ **CI/CD Ready** — Build pipeline with linting, unit tests, security scanning (free enterprise tools)

### MCP Ordering Setup

The agent is connected to the live Contoso Pizza MCP endpoint:

- Server URL: `https://ca-pizza-mcp-ceki46omdafoe.gentlehill-7ae690c8.westus3.azurecontainerapps.io/sse`
- Required user ID: `<CONTOSO_PIZZA_USER_ID>`
- Tooling: order placement, order status lookup, and cancellation via the MCP capability layer

The system prompt explicitly includes the Contoso Pizza user ID so the agent can act on the correct account while guiding customers through ordering.

## Documentation Hub

Project documentation now lives in `docs/`:

- [Documentation Index](docs/README.md)
- [Agent and App Architecture Diagram](docs/architecture-agent-app.md)
- [Build Pipeline Diagram](docs/build-pipeline.md)
- [Data Schemas and Tool Contracts](docs/data-schemas-and-contracts.md)
- [Docs Governance and GitHub Best Practices](docs/DOCS_GOVERNANCE.md)

## API Endpoints Used by This Agent

This section is the canonical endpoint inventory for Crust and reflects the current implementation in agent-definition, tool implementations, deployment config, and test config.

### 1) MCP Endpoint (Live Ordering Capability Layer)

- Base SSE endpoint: `https://ca-pizza-mcp-ceki46omdafoe.gentlehill-7ae690c8.westus3.azurecontainerapps.io/sse`
- Configured MCP tools:
  - `list_menu`
  - `create_order`
  - `get_order_status`
  - `cancel_order`
  - `get_customer_orders`

### 2) Pizza API (REST)

- Base URL: `https://func-pizza-api-ceki46omdafoe.azurewebsites.net/`
- Runtime env var: `PIZZA_API_URL`

| Tool            | Method | Endpoint               | Purpose                                          |
| --------------- | ------ | ---------------------- | ------------------------------------------------ |
| menu_lookup     | GET    | /api/menu              | Retrieve menu items and availability             |
| allergen_lookup | GET    | /api/allergens         | Retrieve allergen and cross-contact data         |
| price_calc      | POST   | /api/price             | Calculate subtotal, tax, fees, total             |
| order_submit    | POST   | /api/orders            | Submit confirmed order (idempotent via order_id) |
| order_status    | GET    | /api/orders/{order_id} | Retrieve order status and ETA                    |
| human_handoff   | POST   | /api/escalations       | Escalate to human support                        |

### 3) Registration API (Configured Supporting Service)

- Base URL: `https://func-registration-api-ceki46omdafoe.azurewebsites.net/`
- Runtime env var: `REGISTRATION_API_URL`
- Note: This URL is configured and available to the agent runtime, but current tool implementations in `tools/tool_implementations.py` do not directly call registration routes.

### 4) Frontend Web App Endpoints

- Pizza web app (agent-facing UI/test target): `https://green-bush-0d277aa0f.7.azurestaticapps.net/`
  - Runtime env var: `PIZZA_WEBAPP_URL`
  - Playwright baseURL default: same URL if env var is not set
- Registration web app: `https://victorious-glacier-0bd2fb00f.7.azurestaticapps.net/`

### 5) Operational / Health Endpoints

- `/health` used by deployment health checks
- `/api/menu` used by deployment health checks as an API availability probe

### 6) Environment-Specific Base URLs

The deployment config defines overrides for these environments:

- Dev:
  - `http://localhost:7071/` (pizza API)
  - `http://localhost:7072/` (registration API)
- Staging:
  - `https://func-pizza-api-staging.azurewebsites.net/`
  - `https://func-registration-api-staging.azurewebsites.net/`
- Production:
  - `https://func-pizza-api-ceki46omdafoe.azurewebsites.net/`
  - `https://func-registration-api-ceki46omdafoe.azurewebsites.net/`

### 7) Timeout / Retry Controls Used for API Calls

- `API_TIMEOUT_SECONDS` (default: 30)
- `API_MAX_RETRIES` (default: 3)
- `API_RETRY_BACKOFF_SECONDS` (default: 2)

---

## Repository Structure

```
crust-agent/
├── README.md                          # This file
├── Makefile                           # Build, test, lint, security commands
├── agent-definition.yaml              # Foundry agent config (declarative core)
├── .prettierrc.yaml                   # YAML formatter config
├── .eslintrc.json                     # Linting rules (if using Node.js tools)
├── .gitignore                         # Git exclusions
│
├── tools/                             # Tool definitions (imperative routing)
│   ├── menu_lookup.json
│   ├── allergen_lookup.json
│   ├── price_calc.json
│   ├── order_submit.json
│   ├── order_status.json
│   └── human_handoff.json
│
├── workflows/                         # Workflow graphs (no loops, declarative state machine)
│   ├── ordering-workflow.yaml
│   ├── slot-collection.yaml
│   ├── confirmation.yaml
│   ├── terminal-states.yaml
│   └── state-transitions.yaml
│
├── safety/                            # Safety & injection protection
│   ├── content-filter-config.yaml
│   ├── prompt-shields-config.yaml
│   ├── tool-guardrails.yaml
│   ├── allergen-safety-rules.yaml
│   └── audit-logging-config.yaml
│
├── schemas/                           # Immutable data schemas
│   ├── order-state.schema.json
│   ├── customer-profile.schema.json
│   ├── allergen-data.schema.json
│   ├── tool-response.schema.json
│   └── thread-message.schema.json
│
├── memory/                            # Memory configuration
│   ├── memory-store-config.yaml
│   ├── thread-storage-config.yaml
│   └── profile-db-schema.sql
│
├── knowledge/                         # Knowledge sources for Azure AI Search
│   ├── menu.json
│   ├── allergens.json
│   └── locations.json
│
├── tests/
│   ├── playwright/                    # Playwright test scripts
│   │   ├── playwright.config.ts
│   │   ├── ordering-flow.spec.ts
│   │   ├── allergen-safety.spec.ts
│   │   ├── injection-tests.spec.ts
│   │   └── memory-tests.spec.ts
│   │
│   ├── unit/                          # Unit tests (Python/Node.js)
│   │   ├── test_tool_schemas.py
│   │   ├── test_idempotence.py
│   │   ├── test_workflow_graph.py
│   │   └── test_immutability.py
│   │
│   └── validators/                    # YAML/JSON validators
│       ├── validate-agent-definition.py
│       ├── validate-schemas.py
│       └── validate-workflows.py
│
├── build/                             # Build pipeline
│   ├── .github/
│   │   └── workflows/
│   │       ├── ci.yaml
│   │       ├── security.yaml
│   │       └── deploy.yaml
│   │
│   ├── security/
│   │   ├── trivy-config.yaml          # Container scanning
│   │   ├── semgrep-rules.yaml         # Static code analysis
│   │   ├── bandit.yaml                # Python security
│   │   └── dependency-check.yaml      # Dependency vulnerabilities
│   │
│   └── scripts/
│       ├── lint.sh
│       ├── test.sh
│       ├── validate.sh
│       └── security-scan.sh
│
├── config/                            # Configuration files
│   ├── prettier.config.yaml
│   ├── yamllint.yaml
│   └── sonarqube-properties.ini
│
├── docs/                              # Documentation
│   ├── DEPLOYMENT.md
│   ├── SAFETY.md
│   ├── PRIVACY.md
│   ├── API.md
│   └── TROUBLESHOOTING.md
│
└── examples/
    ├── happy-path-order.json
    ├── allergen-probe.json
    ├── distress-response.json
    └── error-handling.json
```

---

## Quick Start

### Prerequisites

- **Microsoft Foundry** account with Standard setup (Azure storage, Cosmos DB, AI Search)
- **Azure CLI** (az login)
- **Docker** (for security scanning)
- **Python 3.9+** and **Node.js 16+** (for tests/linting)
- **Playwright** for end-to-end tests

### Installation

```bash
# Clone the repository
git clone <repo>
cd crust-agent

# Install dependencies
make install

# Validate configuration
make validate

# Run tests
make test

# Run security scan
make security-scan

# Deploy to Foundry
make deploy
```

### Run Local Tests

```bash
# Unit tests
pytest tests/unit/ -v

# Playwright end-to-end tests
npx playwright test tests/playwright/

# Validate all YAML/JSON
python tests/validators/validate-agent-definition.py
```

---

## Build Pipeline & CI/CD

### GitHub Actions Workflows

**CI/CD runs automatically on push/PR:**

1. **Lint & Validate** (.github/workflows/ci.yaml)
   - YAML linting (yamllint)
   - JSON schema validation
   - Prettier format check
   - Agent definition validation

2. **Security Scanning** (.github/workflows/security.yaml)
   - Trivy (container/dependency scanning)
   - Semgrep (static code analysis)
   - Bandit (Python security)
   - OWASP Dependency-Check
   - Prompt Shield test (custom)
   - Allergen safety probe (launch-blocking)

3. **Unit & E2E Tests** (ci.yaml)
   - pytest (Python unit tests)
   - Playwright (end-to-end tests)
   - Coverage reporting

4. **Deploy** (.github/workflows/deploy.yaml)
   - Push agent definition to Foundry
   - Verify deployment health
   - Run smoke tests
   - Rollback on failure

**To run locally:**

```bash
make lint           # YAML/JSON/formatting checks
make test           # Unit + Playwright tests
make security-scan  # Trivy, Semgrep, Bandit, dependency-check
make validate       # Schema validation
make build          # Full pipeline (lint → test → scan)
```

**Node Tooling Verification Note:**

- Local Node checks are: `npm install`, `npm run lint`, `npm run prettier:check`, `npm run test:playwright`.
- If Node/npm is unavailable on a contributor machine, these checks are still enforced in GitHub Actions on every push/PR via [ci.yaml](.github/workflows/ci.yaml).
- Playwright execution in CI is the release gate for JS/TS-side validation.

---

## Key Design Principles

### 1. Declarative Configuration

**All business logic is declarative (YAML/JSON), not hardcoded:**

- Agent definition: `agent-definition.yaml`
- Workflows: `workflows/ordering-workflow.yaml` (state machine, no loops)
- Safety rules: `safety/allergen-safety-rules.yaml`
- Tool schemas: `tools/*.json` (function signatures)
- Data schemas: `schemas/*.schema.json` (immutable shapes)

**Benefit:** Change behavior without redeploying code; version control enables audit trail.

### 2. Imperative Tool Routing

**Tool invocation is explicit and deterministic, not learned:**

- System message specifies when to call each tool
- Workflow graph defines state transitions (if/then/else branches)
- No ML-driven routing; predictable and auditable

**Example:** "ALWAYS get prices from price_calc. Never guess."

### 3. Idempotent Operations

**Every tool call is safe to retry:**

- **GET tools** (menu_lookup, allergen_lookup, order_status) have no side effects
- **POST tools** (order_submit) include idempotency key (order_id); calling twice with same key returns same result
- **Errors** distinguish between retryable (5xx) and terminal (4xx)

**Benefit:** Resilient to network failures; no double-charges or lost data.

### 4. Immutable State

**Order objects are never mutated; transformations create new versions:**

```json
{
  "order_id": "uuid",
  "version": 1,
  "items": [...],
  "status": "pending_confirmation"
}
// → new order created with version: 2
```

**Benefit:** Full audit trail; easy rollback; thread-safe concurrency.

### 5. Ephemeral Sessions

**Short-term state is disposable; long-term data requires explicit consent:**

- Thread messages auto-delete after 24h (TTL)
- Customer profile stored only with consent
- Allergies (health data) have separate consent + encryption

**Benefit:** GDPR compliant; minimal data exposure; privacy-by-design.

### 6. Convergence

**All workflows reach a terminal state:**

- Success (order submitted)
- Escalation (human handoff)
- Cancellation (user exits)
- Max turns exceeded (auto-escalate)

**No infinite loops; every conversation ends decisively.**

### 7. Allergen Safety Guardrail

**Hard-coded rule (overrides persona and everything else):**

- ❌ Never declare food "safe" or "allergen-free"
- ✅ Always disclose: "I can't guarantee against cross-contact — confirm with kitchen"
- ✅ Offer human_handoff on allergy questions
- ✅ Log all allergen interactions for compliance

**This is a launch-blocking requirement tested in every deployment.**

---

## Configuration & Deployment

### Agent Definition (agent-definition.yaml)

```yaml
apiVersion: foundry.agents/v1
kind: Agent
metadata:
  name: crust
  version: "1.0.0"
spec:
  model:
    catalog_id: "gpt-4o"
    version: "latest"
  instructions: |
    # [System message from Part C of design doc]
  temperature: 0.3
  tools:
    [
      menu_lookup,
      allergen_lookup,
      price_calc,
      order_submit,
      order_status,
      human_handoff,
    ]
  safety:
    content_filters:
      enabled: true
    prompt_shields:
      enabled: true
      jailbreak_detection: true
      xpia_detection: true
```

### Deploy to Foundry

```bash
# Validate
az foundry agent validate --definition agent-definition.yaml

# Deploy
az foundry agent create \
  --name crust \
  --definition agent-definition.yaml \
  --resource-group <your-rg> \
  --location us-east-1

# Test
az foundry agent test \
  --name crust \
  --message "i'd like to order a pizza"
```

### Chat With Production Agent

Use the script below to send messages directly to the deployed production Foundry agent:

```powershell
# Single message
./scripts/chat-production-agent.ps1 \
  -AgentName crust \
  -ResourceGroup <your-rg> \
  -Location us-east-1 \
  -Message "I want a pepperoni pizza"

# Interactive chat loop
./scripts/chat-production-agent.ps1 \
  -AgentName crust \
  -ResourceGroup <your-rg> \
  -Location us-east-1 \
  -Interactive
```

Prerequisites:

- Azure CLI logged in (`az login`)
- Foundry command group available (`az foundry -h`)
- Agent is already deployed and reachable
- Optional env defaults: `FOUNDRY_AGENT_NAME`, `AZURE_RESOURCE_GROUP`, `FOUNDRY_LOCATION` (or `AZURE_REGION`)

---

## Testing Strategy

### Phase 1: Unit Tests

- Tool schema validation
- Idempotence proofs
- Immutability checks
- Workflow graph structure

### Phase 2: Integration Tests

- Slot-filling happy path
- Modification workflow
- Error handling & escalation

### Phase 3: Safety Tests (Launch-Blocking)

- Allergen probe: "is veggie pizza safe for peanut allergy?" → must disclose cross-contact
- Distress detection: trigger 988 message
- Prompt injection: attempt jailbreak → blocked
- XPIA: inject hidden prompt → escalate

### Phase 4: E2E Tests (Playwright)

- Full ordering flow (greet → slots → confirm → submit)
- Memory (consent capture, re-confirmation)
- Escalation routing
- UI/UX validation (if web-based)

### Phase 5: Compliance Tests

- GDPR Article 9: allergies only with consent
- Data minimization: no credit cards stored
- Retention: TTL enforced
- Audit logs: 90-day retention

**Run all tests before each deployment:**

```bash
make test-all  # Runs all phases
```

---

## Security & Compliance

### Safety Stack (Foundry-Native Only)

1. **Content Filters** — Blocks hateful, sexual, violent, self-harm content
2. **Prompt Shields** — Detects jailbreaks and XPIA (indirect prompt injection)
3. **Tool Guardrails** — Validates tool responses; malformed → escalate
4. **Audit Logging** — All requests/responses logged for 90 days

### Code-Level Protections

1. **Linting** — Catches syntax errors, unused code, security antipatterns
2. **Static Analysis** — Semgrep + Bandit for Python vulnerabilities
3. **Dependency Scanning** — Trivy + Dependency-Check for known CVEs
4. **YAML Validation** — Ensures no injection vectors in config

### Allergen Liability Protection

- System message explicitly forbids safety claims
- Prompt Shields detect attempts to bypass
- Human_handoff always offered for allergy queries
- Audit log proves kitchen was notified
- No blame-shift: agent never says "safe" or assumes kitchen cleared it

---

## Privacy & Compliance

### GDPR Article 9 (Allergies = Health Data)

✅ Explicit consent: "Can I save your name, favorite orders, and allergy info…?"  
✅ Lawful basis: Consent (captured + versioned)  
✅ Data minimization: No SSN, precise location, or financial data  
✅ Encryption: CMK at rest, TLS in transit  
✅ Access/Delete: Customer self-service portal, honored within 30 days  
✅ Audit trail: All writes logged with timestamp and justification

### CPRA (California Privacy Rights)

✅ "Sensitive Personal Information" flagged (allergies)  
✅ Opt-in required (not opt-out)  
✅ Limit the Use control: allergies used only to flag orders

### Retention Policy

- Profiles: 12 months of inactivity → auto-delete
- Thread messages: 24 hours (ephemeral)
- Audit logs: 90 days
- Order history: 3 years (tax/legal requirement)

---

## Troubleshooting

### Agent not responding to orders

1. Check Foundry service status: `az foundry agent health --name crust`
2. Validate workflow: `python tests/validators/validate-workflows.py`
3. Check tool connectivity: `make test-tools`
4. Review audit logs: `az foundry agent logs --name crust --last-24h`

### Allergy guardrail failing

1. ⚠️ **This is launch-blocking.** Do not proceed to production.
2. Run allergen safety test: `pytest tests/unit/test_allergen_guardrail.py -v`
3. Verify Prompt Shields enabled: `make validate`
4. Review system message: See Part C of design doc

### Memory not persisting

1. Check consent capture: "Did user say yes to save profile?"
2. Verify profile DB connection: `make test-memory`
3. Check TTL settings: `memory/memory-store-config.yaml`
4. Review GDPR lawful basis: Consent required before any storage

### CI/CD failing

1. Lint errors: `make lint`
2. Test failures: `make test`
3. Security scan: `make security-scan`
4. Review workflow logs: `.github/workflows/ci.yaml`

---

## References

### Microsoft Foundry Docs

- [Foundry Agent Service Overview](https://learn.microsoft.com/en-us/azure/ai-services/agents/)
- [System Message Best Practices](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/system-message)
- [Safety System Messages](https://learn.microsoft.com/en-us/azure/ai-services/openai/concepts/safety-system-messages)
- [Prompt Shields Documentation](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/prompt-shields)
- [Memory Store (Preview)](https://learn.microsoft.com/en-us/azure/ai-services/agents/memory-store)

### Compliance & Standards

- [GDPR Article 9 (Special Categories)](https://gdpr-info.eu/art-9-gdpr/)
- [CPRA "Sensitive Personal Information"](https://cpra.ca.gov/)
- [FDA Food Allergens](https://www.fda.gov/food/food-allergenslab-testing/food-allergen-labeling-and-protection-act-falcpa)
- [EU Allergen Regulation (EU) No 1169/2011](https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32011R1169)

### Testing & Security

- [Playwright Documentation](https://playwright.dev)
- [OWASP Dependency-Check](https://owasp.org/www-project-dependency-check/)
- [Trivy Scanner](https://github.com/aquasecurity/trivy)
- [Semgrep Rules](https://semgrep.dev/r)
- [Bandit (Python)](https://bandit.readthedocs.io/)

---

## Support & Contributing

For issues, questions, or improvements:

1. Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
2. Review [SAFETY.md](docs/SAFETY.md) for allergen/distress handling
3. Open an issue on GitHub
4. Contact security@[restaurant].com for vulnerabilities

**Last Updated:** 2026-08-26 | **Maintainer:** OpenHack MSFoundry Team
