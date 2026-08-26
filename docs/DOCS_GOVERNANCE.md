# Docs Governance and GitHub Best Practices

This file defines documentation quality standards for the docs folder.

## Branch and Pull Request Practices

- Treat docs changes as code changes with review.
- Keep docs updates in the same pull request as behavior changes.
- Use descriptive pull request titles and include a docs impact summary.

## File and Link Practices

- Use one topic per file to keep pages focused and searchable.
- Use relative links so docs render in GitHub, forks, and local clones.
- Keep Mermaid diagrams in markdown sources instead of image exports when possible.
- Avoid duplicating values that already exist in source files unless needed for readability.

## Accuracy and Drift Prevention

- Update docs/build-pipeline.md whenever .github/workflows/ci.yaml changes.
- Update docs/architecture-agent-app.md whenever agent-definition.yaml or tool routing changes.
- Update docs/data-schemas-and-contracts.md whenever schemas/ or tools/*.json changes.
- Verify endpoint references against README.md and config/deployment-config.yaml.

## Review Checklist for Maintainers

1. All changed docs links render correctly in GitHub preview.
2. Mermaid diagrams render and reflect current implementation.
3. Endpoint URLs and env var names match runtime configuration.
4. Schema and contract inventory includes all validated files.
5. Any temporary behavior, such as skipped jobs, is clearly marked as temporary.

## Suggested Repository Enhancements

These are optional follow-ups for stronger docs governance:

- Add CODEOWNERS entries for docs reviewers.
- Add markdown linting in CI for docs style consistency.
- Add a pull request template checkbox: Docs updated.
- Add a scheduled link checker workflow for docs pages.
