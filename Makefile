# ==============================================================================
# FinSight — Visual Financial RAG Monorepo Makefile
# Governed by 529 Studio Engineering Standards & AGENTS.md
# ==============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Python Virtualenv & Binary Paths
VENV_PYTHON := packages/core-engine/.venv/bin/python
VENV_PYTEST := packages/core-engine/.venv/bin/pytest

# Colors for terminal styling
CYAN   := \033[36m
GREEN  := \033[32m
YELLOW := \033[33m
RED    := \033[31m
RESET  := \033[0m
BOLD   := \033[1m

##@ 📖 Help & Discovery

.PHONY: help
help: ## Show this help menu with descriptions
	@echo ""
	@echo -e "$(BOLD)$(CYAN)FinSight — Visual Financial RAG Developer CLI$(RESET)"
	@echo -e "Usage: $(GREEN)make [target]$(RESET)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf ""} \
		/^[a-zA-Z0-9_-]+:.*?##/ { printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2 } \
		/^##@/ { printf "\n$(BOLD)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ 🚀 Local Development

.PHONY: dev
dev: kill ## Run both backend Core Engine and Desktop Frontend concurrently
	@echo -e "$(GREEN)Starting FinSight Full-Stack Environment...$(RESET)"
	@echo -e "$(YELLOW)Engine: http://127.0.0.1:8765$(RESET) | $(YELLOW)Desktop UI: http://localhost:5173$(RESET)"
	@trap 'kill 0' SIGINT SIGTERM EXIT; \
		PYTHONPATH=packages/core-engine/src $(VENV_PYTHON) packages/core-engine/src/main.py & \
		npm run --prefix apps/desktop dev & \
		wait

.PHONY: engine
engine: ## Run Python Core Engine daemon on http://127.0.0.1:8765
	@echo -e "$(GREEN)Starting Core Engine daemon on :8765...$(RESET)"
	@PYTHONPATH=packages/core-engine/src $(VENV_PYTHON) packages/core-engine/src/main.py

.PHONY: desktop
desktop: ## Run Desktop Frontend Vite server on http://localhost:5173
	@echo -e "$(GREEN)Starting Desktop UI dev server on :5173...$(RESET)"
	@npm run --prefix apps/desktop dev

##@ 🧪 Testing & Quality Assurance

.PHONY: test
test: test-desktop test-engine ## Run all test suites (Frontend Vitest + Backend Pytest)
	@echo -e "$(GREEN)All test suites passed successfully!$(RESET)"

.PHONY: test-desktop
test-desktop: ## Run Frontend Vitest suite (usePaneResize, BoundingBoxOverlay, ResizableSplitView)
	@echo -e "$(CYAN)Running Desktop Vitest suite...$(RESET)"
	@npm run --prefix apps/desktop test

.PHONY: test-engine
test-engine: ## Run Core Engine Pytest suite (renderer, retriever, security defenses)
	@echo -e "$(CYAN)Running Backend Pytest suite...$(RESET)"
	@$(VENV_PYTEST)

.PHONY: bench
bench: ## Run 30-query retrieval benchmark (ColPali vs Text Chunking)
	@echo -e "$(CYAN)Running retrieval benchmark harness...$(RESET)"
	@$(VENV_PYTHON) benchmarks/eval_retrieval.py

##@ 📦 Build & Typecheck

.PHONY: build
build: ## Build Desktop production bundle (tsc && vite build)
	@echo -e "$(GREEN)Building Desktop production bundle...$(RESET)"
	@npm run --prefix apps/desktop build

.PHONY: typecheck
typecheck: ## Run TypeScript compiler check on Desktop codebase
	@echo -e "$(CYAN)Checking TypeScript types...$(RESET)"
	@(cd apps/desktop && npx tsc --noEmit)
	@echo -e "$(GREEN)TypeScript typecheck clean!$(RESET)"

##@ 🔍 Diagnostics & Process Management

.PHONY: status
status: ## Check git status and running port listeners (8765, 5173)
	@echo -e "$(BOLD)$(CYAN)=== Git Status ===$(RESET)"
	@git status -s
	@echo ""
	@echo -e "$(BOLD)$(CYAN)=== Process Listeners ===$(RESET)"
	@echo -n "Port 8765 (Core Engine): "
	@lsof -i :8765 -sTCP:LISTEN >/dev/null 2>&1 && echo -e "$(GREEN)RUNNING (PID: $$(lsof -ti :8765))$(RESET)" || echo -e "$(YELLOW)IDLE$(RESET)"
	@echo -n "Port 5173 (Desktop UI) : "
	@lsof -i :5173 -sTCP:LISTEN >/dev/null 2>&1 && echo -e "$(GREEN)RUNNING (PID: $$(lsof -ti :5173))$(RESET)" || echo -e "$(YELLOW)IDLE$(RESET)"
	@echo ""

.PHONY: kill
kill: ## Kill any hanging processes listening on ports 8765 and 5173
	@echo -e "$(YELLOW)Freeing ports 8765 and 5173...$(RESET)"
	@lsof -ti :8765 | xargs kill -9 2>/dev/null || true
	@lsof -ti :5173 | xargs kill -9 2>/dev/null || true
	@echo -e "$(GREEN)Ports cleared.$(RESET)"

.PHONY: clean
clean: ## Clean build artifacts, node_modules cache, and test caches
	@echo -e "$(YELLOW)Cleaning caches and artifacts...$(RESET)"
	@rm -rf apps/desktop/dist .pytest_cache **/node_modules/.vite .playwright-mcp
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo -e "$(GREEN)Clean complete.$(RESET)"
