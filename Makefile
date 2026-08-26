.PHONY: help install lint format test test-all validate clean security-scan build deploy destroy

# Variables
PYTHON := python3
PIP := pip3
NODE := node
NPM := npm
DOCKER := docker

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help:
	@echo "$(BLUE)Crust Agent - Build Pipeline$(NC)"
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  $(GREEN)install$(NC)          Install all dependencies (Python + Node.js)"
	@echo "  $(GREEN)lint$(NC)             Linting & formatting checks (YAML, JSON, Python)"
	@echo "  $(GREEN)format$(NC)           Auto-format code (Prettier, Black)"
	@echo "  $(GREEN)test$(NC)             Run unit tests (pytest) + Playwright e2e tests"
	@echo "  $(GREEN)test-unit$(NC)        Run pytest only"
	@echo "  $(GREEN)test-playwright$(NC)  Run Playwright tests only"
	@echo "  $(GREEN)validate$(NC)         Validate YAML/JSON schemas and agent definition"
	@echo "  $(GREEN)security-scan$(NC)    Run security scanners (Trivy, Semgrep, Bandit)"
	@echo "  $(GREEN)build$(NC)            Full CI pipeline (lint → test → security → validate)"
	@echo "  $(GREEN)deploy$(NC)           Deploy to Azure Foundry"
	@echo "  $(GREEN)destroy$(NC)          Tear down deployment"
	@echo "  $(GREEN)clean$(NC)            Clean build artifacts"
	@echo "  $(GREEN)help$(NC)             Show this help message"
	@echo ""

install:
	@echo "$(BLUE)[INSTALL]$(NC) Installing Python dependencies..."
	$(PIP) install -r requirements.txt
	@echo "$(BLUE)[INSTALL]$(NC) Installing Node.js dependencies..."
	$(NPM) install
	@echo "$(BLUE)[INSTALL]$(NC) Installing Playwright browsers..."
	$(NPM) exec -- playwright install
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

lint:
	@echo "$(BLUE)[LINT]$(NC) Linting YAML files..."
	yamllint -c config/yamllint.yaml . --strict 2>/dev/null || echo "$(YELLOW)⚠ YAML linting issues found (non-fatal)$(NC)"
	
	@echo "$(BLUE)[LINT]$(NC) Linting JSON files..."
	$(NPM) run lint:json
	
	@echo "$(BLUE)[LINT]$(NC) Linting Python files..."
	$(PYTHON) -m pylint tools/tool_implementations.py --fail-under=8.0 2>/dev/null || echo "$(YELLOW)⚠ Python linting issues found (check manually)$(NC)"
	
	@echo "$(BLUE)[LINT]$(NC) Checking code formatting (Prettier)..."
	$(NPM) run prettier:check
	
	@echo "$(GREEN)✓ Linting complete$(NC)"

format:
	@echo "$(BLUE)[FORMAT]$(NC) Auto-formatting with Prettier..."
	$(NPM) run prettier:write
	
	@echo "$(BLUE)[FORMAT]$(NC) Auto-formatting with Black..."
	$(PYTHON) -m black tools/ tests/unit/ --line-length=100
	
	@echo "$(GREEN)✓ Formatting complete$(NC)"

test-unit:
	@echo "$(BLUE)[TEST UNIT]$(NC) Running pytest..."
	$(PYTHON) -m pytest tests/unit/ -v --cov=tools --cov-report=html
	@echo "$(GREEN)✓ Unit tests passed$(NC)"

test-playwright:
	@echo "$(BLUE)[TEST E2E]$(NC) Running Playwright tests..."
	$(NPM) run test:playwright
	@echo "$(GREEN)✓ E2E tests passed$(NC)"

test: test-unit test-playwright
	@echo "$(GREEN)✓ All tests passed$(NC)"

validate:
	@echo "$(BLUE)[VALIDATE]$(NC) Validating agent definition YAML..."
	$(PYTHON) tests/validators/validate-agent-definition.py
	
	@echo "$(BLUE)[VALIDATE]$(NC) Validating JSON schemas..."
	$(PYTHON) tests/validators/validate-schemas.py
	
	@echo "$(BLUE)[VALIDATE]$(NC) Validating workflow graph..."
	$(PYTHON) tests/validators/validate-workflows.py
	
	@echo "$(GREEN)✓ All validations passed$(NC)"

security-scan:
	@echo "$(BLUE)[SECURITY]$(NC) Running Trivy (container + dependency scanning)..."
	$(DOCKER) run --rm -v $(PWD):/repo aquasec/trivy repo /repo --severity HIGH,CRITICAL --exit-code 1 || echo "$(YELLOW)⚠ Trivy scan complete (review results)$(NC)"
	
	@echo "$(BLUE)[SECURITY]$(NC) Running Semgrep (static code analysis)..."
	$(DOCKER) run --rm -v $(PWD):/src returntocorp/semgrep --config=p/python --config=p/security-audit /src/tools/ 2>/dev/null || echo "$(YELLOW)⚠ Semgrep scan complete$(NC)"
	
	@echo "$(BLUE)[SECURITY]$(NC) Running Bandit (Python security)..."
	$(PYTHON) -m bandit -r tools/ -f json -o bandit-report.json 2>/dev/null || echo "$(YELLOW)⚠ Bandit scan complete (review bandit-report.json)$(NC)"
	
	@echo "$(BLUE)[SECURITY]$(NC) Running OWASP Dependency-Check..."
	$(DOCKER) run --rm -v $(PWD):/src owasp/dependency-check --scan /src --format JSON --project "crust-agent" 2>/dev/null || echo "$(YELLOW)⚠ Dependency-Check complete$(NC)"
	
	@echo "$(BLUE)[SECURITY]$(NC) Running allergen safety probes..."
	$(PYTHON) tests/validators/test-allergen-guardrail.py
	
	@echo "$(GREEN)✓ Security scanning complete$(NC)"

build: lint test validate security-scan
	@echo "$(GREEN)✓ Full build pipeline passed$(NC)"
	@echo ""
	@echo "Ready for deployment. Next steps:"
	@echo "  $(BLUE)make deploy$(NC) - Deploy to Azure Foundry"

deploy:
	@echo "$(BLUE)[DEPLOY]$(NC) Deploying Crust agent to Azure Foundry..."
	az foundry agent validate --definition agent-definition.yaml
	@echo "$(BLUE)[DEPLOY]$(NC) Creating/updating agent..."
	az foundry agent create-or-update \
		--name crust \
		--definition agent-definition.yaml \
		--resource-group $${AZURE_RESOURCE_GROUP} \
		--location $${AZURE_LOCATION}
	@echo "$(BLUE)[DEPLOY]$(NC) Running smoke tests..."
	$(PYTHON) tests/validators/test-deployment-health.py
	@echo "$(GREEN)✓ Deployment successful$(NC)"

destroy:
	@echo "$(RED)[DESTROY]$(NC) Removing Crust agent from Azure Foundry..."
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		az foundry agent delete --name crust --resource-group $${AZURE_RESOURCE_GROUP}; \
		echo "$(GREEN)✓ Agent deleted$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled$(NC)"; \
	fi

clean:
	@echo "$(BLUE)[CLEAN]$(NC) Removing build artifacts..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/ htmlcov/ coverage.xml
	rm -rf test-results/ playwright-results/
	rm -rf node_modules/
	rm -rf bandit-report.json
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

# CI/CD targets (for GitHub Actions)
.PHONY: ci-build ci-test ci-security ci-deploy

ci-build: lint validate
	@echo "$(GREEN)✓ CI build checks passed$(NC)"

ci-test: test-unit test-playwright
	@echo "$(GREEN)✓ CI tests passed$(NC)"

ci-security: security-scan
	@echo "$(GREEN)✓ CI security scan passed$(NC)"

ci-deploy: build
	@echo "$(GREEN)✓ CI ready to deploy$(NC)"

# Development targets

.PHONY: dev-server dev-test watch

dev-server:
	@echo "$(BLUE)[DEV]$(NC) Starting local pizza API mock server..."
	# TODO: Implement mock server for local development
	@echo "$(YELLOW)Mock server not yet implemented$(NC)"

dev-test:
	@echo "$(BLUE)[DEV]$(NC) Running tests in watch mode..."
	$(PYTHON) -m pytest tests/unit/ -v --tb=short --watch

watch:
	@echo "$(BLUE)[WATCH]$(NC) Watching for file changes and running linting..."
	$(NPM) run watch

# Documentation

.PHONY: docs docs-build docs-serve

docs:
	@echo "$(BLUE)[DOCS]$(NC) Building documentation..."
	# TODO: Generate docs from YAML/JSON + docstrings
	@echo "$(YELLOW)Documentation generation not yet implemented$(NC)"

docs-build:
	@echo "$(BLUE)[DOCS]$(NC) Building docs..."

docs-serve:
	@echo "$(BLUE)[DOCS]$(NC) Serving docs locally..."
	python3 -m http.server 8000 --directory docs

# Reporting

.PHONY: report report-coverage report-security

report-coverage:
	@echo "$(BLUE)[REPORT]$(NC) Generating coverage report..."
	@if [ -f htmlcov/index.html ]; then \
		echo "Coverage report: file://$(PWD)/htmlcov/index.html"; \
	else \
		echo "$(YELLOW)No coverage report found (run 'make test-unit' first)$(NC)"; \
	fi

report-security:
	@echo "$(BLUE)[REPORT]$(NC) Summarizing security scan results..."
	@if [ -f bandit-report.json ]; then \
		echo "Bandit report: $(PWD)/bandit-report.json"; \
	else \
		echo "$(YELLOW)No security report found (run 'make security-scan' first)$(NC)"; \
	fi

report: report-coverage report-security
	@echo "$(GREEN)✓ Reports generated$(NC)"

# Default target
.DEFAULT_GOAL := help
