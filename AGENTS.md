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

## 13. Independent Subagent Audit, Security/Injection & E2E Playwright Protocol

Before any Pull Request is merged into `dev` or any bugfix is marked resolved, the following protocol MUST be executed:

### A. Mandatory Independent Subagent Audit
- The implementer agent MUST NOT audit its own PR.
- An independent subagent (`research` or `self`) MUST be dispatched to review the diff against specifications, contracts, and security standards.
- The PR description MUST include the Subagent Audit verdict and sign-off.

### B. Backend Security & Injection Testing (Mandatory Live Checks)
- **Path Traversal Defense:** All endpoints accepting file paths (e.g. `file_path`, `document_id`) must be actively probed for directory traversal (`../../etc/passwd`, arbitrary host reads). Only approved directories (`~/.finsight/`, `benchmarks/data/`, workspace) are permitted.
- **Injection Defense:** All prompt inputs and query strings must be validated and sanitized. Zero `eval()`, zero unvalidated raw SQL execution, zero shell injection through subprocesses.
- **Zero-Leak Leakage Defense:** Verify that no private keys, `.env` values, or API tokens leak into HTTP responses, debug logs, or vector metadata.

### C. Frontend E2E Verification via Playwright MCP
- For all frontend changes (`apps/desktop` or web views), the agent MUST launch the dev server and use **Playwright MCP tools** (`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_console_messages`, `browser_take_screenshot`) to:
  1. Inspect the live UI rendering.
  2. Test interactive flows (e.g. drag & drop, clicking evidence chips, split-view resize).
  3. Validate all 3 UI States (Skeleton loading, Error state with retry, Empty state).
  4. Ensure 0 unhandled console errors and 0 failed network requests.
  5. Save screenshot evidence to `docs/proofs/sprint<N>/` as empirical verification before merging PR.

## 14. Post-Wave Independent Subagent Audit & UI/UX Quality Gate (Mandatory)

Whenever a milestone wave (a batch or logical grouping of related tasks within a sprint) is completed, the agent MUST execute an independent verification cycle before proceeding to the next wave or closing the sprint:

### A. Independent External Subagent Dispatch
- The implementer agent MUST NOT perform its own wave audit.
- An independent external subagent (`research` or `self` with role `Independent Codebase & UI/UX Quality Auditor`) MUST be dispatched.
- The subagent must inspect the codebase, test suites, and live UI / proof artifacts.

### B. Dual-Axis Audit Scope: Correctness & User-Friendliness
The audit subagent MUST evaluate two mandatory dimensions:
1. **Functional Correctness & Integration Health**:
   - Inspect the codebase modified during the wave for contract consistency, type safety, regressions, and security defenses.
   - Verify that all unit, component, and backend test suites pass with 100% success rate.
   - Ensure zero orphaned code, zero `console.log` statements, and robust edge-case handling (e.g. division-by-zero, storage exceptions, invalid bounds).
2. **UI/UX & User-Friendliness Inspection**:
   - **Interactive Polish & Ergonomics**: Check that drag handles, split views, overlays, and animations operate smoothly without stutter or layout shifts.
   - **Financial Analyst Usability**: Evaluate whether visual grounding highlights, confidence badges, and evidence chips are clear, readable, and intuitive for financial analysts reviewing audited filings.
   - **3 UI States & Kiosk Standards**: Confirm that Skeleton loading, localized Error states with retry, and Actionable Empty states render gracefully, and interactive touch targets meet the $\ge 48\text{px}$ ergonomic rule.
   - **Clarity & Contrast**: Verify dark/light contrast ratios, readable typography, and zero clipped labels or overflowing components.

### C. Gate & Sign-Off Requirement
- The subagent MUST generate a formal **Wave Audit Report** concluding with an explicit verdict:
  - **VERDICT: APPROVED 🟢**: Wave meets all functional correctness standards and passes user-friendly UI/UX evaluation.
  - **VERDICT: REJECTED 🔴**: Specific actionable issues or UX friction points are documented for the implementer to fix before proceeding.
- The main agent MUST NOT advance to the next wave or initiate sprint close rituals until the independent audit report is signed off with `APPROVED`.
