# Crust Documentation Hub

This folder contains architecture, pipeline, and contract documentation for the Crust Foundry agent.

## Contents

- [Agent and App Architecture](architecture-agent-app.md)
- [Build Pipeline](build-pipeline.md)
- [Data Schemas and Tool Contracts](data-schemas-and-contracts.md)
- [Docs Governance and GitHub Best Practices](DOCS_GOVERNANCE.md)

## Documentation Principles

- Keep docs close to code and update docs in the same pull request as behavior changes.
- Prefer source-of-truth links to repository files over duplicated definitions.
- Use Mermaid diagrams for architecture and workflow views so diagrams are diffable.
- Keep operational facts current: endpoints, environments, and CI/CD behavior.
- Use clear ownership and review expectations for docs changes.

## Quick Update Rules

1. If you change agent behavior in agent-definition.yaml, update architecture and contracts docs.
2. If you change .github/workflows/ci.yaml, update the build pipeline diagram.
3. If you add or modify schemas in schemas/ or tools/, update the schemas and contracts index.
4. Keep links relative so they render correctly in GitHub and local editors.
