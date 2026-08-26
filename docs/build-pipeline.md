# Build Pipeline

This diagram mirrors the active pipeline in .github/workflows/ci.yaml.

## CI/CD Pipeline Diagram

```mermaid
flowchart TD
    TR[Trigger\npush, pull_request, schedule]

    L[Lint and Validate]
    U[Unit Tests]
    S[Security Scanning]
    E[E2E Tests Playwright\ncurrently skipped]
    A[Allergen Safety Tests]
    I[Integration Tests\npush or schedule only]

    B[Build Approval Gate]
    DS[Deploy Staging\ndevelop only]
    DP[Deploy Production\nmain only]
    N[Notify on Failure\nPR comments only]

    TR --> L
    L --> U
    L --> S
    L -. optional .-> E

    U --> A
    U --> I

    L --> B
    U --> B
    S --> B
    A --> B

    B --> DS
    B --> DP

    L -. on any failure .-> N
    U -. on any failure .-> N
    S -. on any failure .-> N
    A -. on any failure .-> N
```

## Job Summary

1. Lint and Validate

- Python and Node setup
- Dependency install
- make lint
- make validate
- formatting checks

2. Unit Tests

- pytest unit tests with coverage
- coverage upload and junit artifacts

3. Security Scanning

- Trivy scan and SARIF upload
- Semgrep static analysis
- Bandit scan
- dependency-check scan

4. Allergen Safety Tests

- guardrail test execution
- post-run verification script

5. Integration Tests

- runs only on push and schedule
- uses live API endpoint configuration

6. Deployments

- Staging deployment from develop branch
- Production deployment from main branch

## Current Pipeline Notes

- Playwright E2E job is intentionally disabled during stabilization.
- Notify on Failure posting is gated to pull_request events to avoid push-event issue comment failures.
