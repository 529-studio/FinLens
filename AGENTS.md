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

## 12. Git Flow, Protected Branches, and Sprint Boundary Protocol

### A. Git Flow & Protected Branch Policy
1. **Default Branch is `dev`:**
   - All active development merges into `dev`.
   - `main` represents production releases tagged per milestone.
2. **Branch Protection:**
   - Both `dev` and `main` are protected. Direct pushes are strictly forbidden.
   - All modifications MUST go through a Pull Request targeting `dev`.
   - **Merge Commit Required:** PR merges MUST create a merge commit (`gh pr merge --merge`). Squash and rebase merges are disabled to preserve granular Git history and verifiable attribution.
3. **Branch Naming Standard:**
   - Features: `feat/s<N>-<task-slug>` (e.g. `feat/s1-pdf-renderer`)
   - Fixes: `fix/<issue-number>-<slug>`
   - Handoff & Sprint Close: `docs/s<N>-handoff`

### B. Sprint Boundary Protocol (1 Conversation = 1 Sprint)
1. **Context Window Hygiene:**
   - A single agent conversation covers exactly **one sprint** (or roughly ~1,200 conversation steps).
   - Bloated conversations (>1,200 steps) suffer from context degradation, forgotten constraints, and hallucinated diffs.
2. **Sprint Close Ritual:**
   - When all tasks of a sprint are implemented and verified via PRs into `dev`:
     1. Author `docs/reports/sprint<N>_report.md` documenting verified quantitative scorecards and reality checks.
     2. Run `tools/sprint/close.sh --init` to scaffold `docs/HANDOFF-s<N>.md` (must be between 700 B and 12 KB, with all 7 numbered sections completed).
     3. Ensure all lessons learned are recorded in `docs/lesson_learn.md` and synced via `npm run harvest:lessons`.
     4. Open a PR for `docs/s<N>-handoff` and merge it into `dev` with a merge commit.
     5. Run `tools/sprint/close.sh` to validate the handoff and output the bootstrap prompt for the next conversation.
     6. Launch the new sprint in a FRESH conversation: `tools/sprint/close.sh --launch` (or `agy -i "<prompt>"`).
   - **Never start a new sprint's tasks in the closing conversation.**
