<!-- BEGIN:529studio-engineering-standards -->
# 529 Studio Engineering Standards & Agent Protocol

This repository is governed by the official **529 Studio Engineering Standards**.
Every developer and AI Coding Agent (Antigravity CLI, OpenCode, Claude Code, Cursor) MUST comply with the following mandatory rules.

## 1. Mandatory Pre-Flight Skill Review
Before planning (`/plan`) or implementing any task, feature, or bugfix, the agent MUST review the applicable Senior Skills from the 529 Studio Hub:
- `resilient-networking-and-waf`: For any HTTP client, WAF timeouts, or test mocks.
- `env-and-auth-ops-debugging`: For `.env` loading, CWD path safety, and fail-closed auth debugging.
- `module-boundary-and-concurrency`: For Go/backend module boundaries, `deps.go` interfaces, and `SELECT FOR UPDATE` locking.
- `frontend-4file-and-resilient-ui`: For Next.js/React APIs, 4-file pattern, 3 UI states (Skeleton/Error/Empty), and 48px touch targets.
- `docker-runtime-patching-and-secrets`: For Docker Compose, runtime asset patching, and zero-leak cryptographic secrets.
- `evidence-based-dod-and-llm-guardrails`: For Definition of Done verification, avoiding LLM outdated training hallucinations, and scope control.

## 2. Zero-Leak Security Policy
- NEVER hardcode or commit API keys, passwords, private keys, or tokens in git.
- All secrets MUST be loaded via `.env` (guarded by `.gitignore`).

## 3. Evidence Before Assertions (Hardened DoD)
- Passing unit tests alone is NEVER sufficient to close an issue or declare production readiness.
- You must produce empirical verification evidence (an actual cURL response, log trace, or UI screenshot from the running environment) before claiming completion.

## 4. Two-Way Knowledge Synchronization Hook (Mandatory AI Rule)
- When you fix a significant bug, solve an elusive operational failure, or make an architectural decision in this repository:
  1. Record the post-mortem in this repository's `lesson_learn.md` (or `docs/lesson_learn.md`).
  2. If the lesson has cross-repo organizational value, YOU MUST automatically sync it to the central hub by running:
     ```bash
     bash ~/repos/529-engineering-skills/scripts/harvest-lessons.sh
     ```
     or by directly updating the relevant skill in `~/repos/529-engineering-skills/skills/`.
<!-- END:529studio-engineering-standards -->

<!-- lore:memory-protocol:start -->
## 11. Persistent memory protocol (Lore)

This project uses Lore for shared memory across all AI agents and sessions.
- **Task start**: Before proposing or editing code, invoke MCP tool `memory_search` with relevant file paths, symbols, or feature keywords to retrieve active architectural decisions, conventions, and environment variables.
- **Definition of Done**: When introducing or modifying environment variables, API endpoints, module dependencies, or architectural rules, invoke `memory_write` with evidence.
- **Provenance & drift**: Use `memory_blame` to verify authority, author, and evidence before overwriting an established pattern.
<!-- lore:memory-protocol:end -->
