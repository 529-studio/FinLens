# FinTrace Sprint 9 Implementation Plan: General Availability (GA) & Enterprise Expansion

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch FinTrace Production Release v1.0.0 GA under the clean, cleared brand, deliver on-premise Docker LAN deployment for enterprise banks, enable interactive Footnote deep-linking in the Desktop client, package the Excel Add-in for Microsoft AppSource Admin Center rollout, and configure Windows Authenticode packaging.

**Architecture:** Polyglot monorepo leveraging Tauri v2 (Rust + React 19) for Desktop, Office.js for Excel, Python 3.12 daemon for Visual RAG (ColPali + LanceDB), and Docker Compose for LAN deployment.

**Tech Stack:** Tauri v2, React 19, Lucide React, Vite, Office.js, FastAPI, LanceDB, PyMuPDF, Docker, GitHub Actions, Apple Notarytool, Windows SignTool.

---

## Global Constraints

- All development on protected branch `dev` via Pull Requests with merge commits (`gh pr merge --merge`).
- AGENTS.md Rule 2: Zero-Leak Security Policy (never hardcode or commit API keys or tokens).
- AGENTS.md Rule 13: Mandatory Independent Subagent Audit before merging any PR.
- AGENTS.md Rule 15: Zero-Emoji UI Policy (all iconography must use Lucide React vector SVGs).
- 100% test pass rate across all tiers (Vitest, Pytest, Cargo).

---

## Sprint 9 Task Breakdown

### Task S9-01: Production Release v1.0.0 Tagging, Changelog & GA Release Pipeline
- **Role:** `role:architect`
- **Target Files:**
  - `apps/desktop/src-tauri/tauri.conf.json`: Set version `1.0.0`.
  - `apps/desktop/package.json`: Set version `1.0.0`.
  - `apps/excel/package.json`: Set version `1.0.0`.
  - `apps/excel/manifest.xml` & `manifest.prod.xml`: Set version `1.0.0.0`.
  - `packages/core-engine/src/main.py`: Set version `1.0.0`.
  - `CHANGELOG.md`: Curated public release notes detailing Sprint 1 to 8 deliverables.
  - `.github/workflows/release-desktop.yml`: Release asset generation.
- **Verification:**
  - [ ] Package versions synchronized to `1.0.0` across monorepo.
  - [ ] `CHANGELOG.md` created with verified feature highlights.
  - [ ] Automated release workflow dry-run passes on clean workspace.
  - [ ] PR created and merged into `dev` via merge commit.

### Task S9-02: Multi-Tenant Team Box (Docker Compose LAN Deployment) for Enterprise Banking Clients
- **Role:** `role:architect`, `role:rag-ml`
- **Target Files:**
  - `deploy/Dockerfile.engine`: Multi-stage Python 3.12 Dockerfile with non-root security (`appuser:10001`) and healthcheck.
  - `deploy/docker-compose.yml`: Production orchestration with healthchecks, persistent volumes (`fintrace_lancedb`, `fintrace_uploads`, `fintrace_cache`), and network isolation.
  - `deploy/.env.lan.example`: Zero-leak cryptographic configuration template.
  - `deploy/nginx/fintrace-lan.conf`: LAN reverse proxy with CORS headers and WebSocket upgrade (`/ws/query/stream`).
  - `deploy/tests/test_lan_deploy.sh`: Smoke test script validating container health and path traversal defense.
- **Verification:**
  - [ ] `docker compose -f deploy/docker-compose.yml config` passes validation with 0 errors.
  - [ ] Non-root execution and zero secret leakage verified.
  - [ ] Container healthcheck passes within 15 seconds.
  - [ ] PR created and merged into `dev` via merge commit.

### Task S9-03: Interactive Footnote Deep-Linking in Desktop PDF Viewer
- **Role:** `role:frontend`
- **Target Files:**
  - `apps/desktop/src/types/visual_rag.types.ts`: Define `FootnoteReferenceDTO` interface.
  - `apps/desktop/src/hooks/usePdfViewer.ts`: Add `jumpToPage(page: number, boundingBox?: BoundingBox)` and smooth scroll handler.
  - `apps/desktop/src/components/chat/FootnoteChip.tsx`: Interactive chip component with tooltip, 48px touch target ergonomics, Lucide `FileText` icon, and click handler.
  - `apps/desktop/src/components/layout/SplitView.component.tsx`: Render Footnote chips under answer text, connecting click events to PDF viewer deep-linking.
  - `apps/desktop/src/components/chat/__tests__/FootnoteChip.test.tsx`: Vitest suite testing rendering, accessibility labels, and click delegation.
- **Verification:**
  - [ ] Clicking a footnote chip in Desktop UI smoothly scrolls the PDF viewer to the footnote's page.
  - [ ] Bounding box overlay displays active footnote highlight with high-contrast indicator.
  - [ ] 100% Vitest unit tests pass.
  - [ ] Zero raw emojis in component (Rule 15).
  - [ ] PR created and merged into `dev` via merge commit.

### Task S9-04: Microsoft AppSource Manifest Package & Centralized Deployment Infrastructure
- **Role:** `role:excel`
- **Target Files:**
  - `apps/excel/manifest.appsource.xml`: Schema-compliant manifest with AppDomains, high-res icons (16x16, 32x32, 64x64, 80x80), and permissions.
  - `apps/excel/scripts/validate-manifest.js`: Automated validation script using `office-addin-manifest` CLI.
  - `apps/excel/assets/`: Ensure all required AppSource icons (brand vector SVG export, PNG icons) exist.
  - `docs/deployment/MICROSOFT_365_ADMIN_DEPLOYMENT.md`: Step-by-step enterprise guide for IT admins to deploy FinTrace Add-in centralized across Excel desktop & web.
- **Verification:**
  - [ ] Manifest validation passes all Microsoft Office Add-in validator checks.
  - [ ] High-resolution brand assets correctly linked and accessible.
  - [ ] Complete enterprise deployment guide authored with verified steps.
  - [ ] PR created and merged into `dev` via merge commit.

### Task S9-05: Windows Authenticode Code Signing & Packaging Pipeline
- **Role:** `role:architect`, `role:frontend`
- **Target Files:**
  - `apps/desktop/src-tauri/tauri.conf.json`: Configure Windows NSIS bundle target (`targets: ["dmg", "app", "nsis"]`) with custom installer icons.
  - `scripts/sign-windows.ps1` (or `scripts/sign-windows.sh`): Windows signing script supporting Azure Trusted Signing / signtool with `--dry-run` validation.
  - `.github/workflows/release-desktop.yml`: Add `build-and-sign-windows` job targeting `windows-latest`.
  - `apps/desktop/src/utils/__tests__/signing-config.test.ts`: Extend test suite to verify Windows bundle configuration.
- **Verification:**
  - [ ] `tauri.conf.json` declares valid NSIS bundle settings.
  - [ ] Windows signing script passes `--dry-run` verification.
  - [ ] Signing configuration test suite passes with 100% rate.
  - [ ] PR created and merged into `dev` via merge commit.
