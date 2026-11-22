# S9 Handoff & Sprint 10 Horizon

**Document**: `docs/HANDOFF-s9.md`  
**Date**: 2026-11-22  
**Repository**: `529-studio/FinTrace`  
**Charter**: Transition ledger documenting Sprint 9 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s9-handoff`)
- **Head commit**: `a8b99a8` (`Merge pull request #69 from 529-studio/feat/s9-05-windows-signing-packaging`)
- **Worktree**: clean (all 5 feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #59 (`feat/s9-rebrand-fintrace`): Complete brand clearance and rebranding from FinSight to FinTrace.
  - PR #65 (`feat/s9-01-release-v100-ga`): S9-01 Production Release v1.0.0 Tagging, Changelog & GA Release Pipeline (Issue #60).
  - PR #66 (`feat/s9-02-docker-lan-box`): S9-02 Multi-Tenant Docker Compose LAN Deployment for Enterprise Banking (Issue #61).
  - PR #67 (`feat/s9-03-interactive-footnotes`): S9-03 Interactive Footnote Deep-Linking in Desktop PDF Viewer (Issue #62).
  - PR #68 (`feat/s9-04-appsource-manifest`): S9-04 Microsoft AppSource Production Manifest Package & Admin Deployment (Issue #63).
  - PR #69 (`feat/s9-05-windows-signing-packaging`): S9-05 Windows Authenticode Code Signing & Packaging Pipeline (Issue #64).

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#59** | Rebrand | `all` | Full brand clearance and clean trademark migration to FinTrace across GitHub, monorepo packages, and assets. |
| **#65** | **S9-01** (#60) | `release/`, `packages/` | Monorepo version synchronization to 1.0.0, CHANGELOG.md, Apple notarization verification, and official git tag `v1.0.0`. |
| **#66** | **S9-02** (#61) | `deploy/` | Production Docker Compose LAN Box running unprivileged user (UID 10001), Nginx gateway with WebSocket upgrade, and automated secret generation. |
| **#67** | **S9-03** (#62) | `apps/desktop`, `core-engine` | Interactive FootnoteChip component (48px kiosk target, zero raw emojis) with bidirectional deep-linking to PDF Thuyết minh BCTC. |
| **#68** | **S9-04** (#63) | `apps/excel`, `docs/` | Validated Microsoft AppSource manifest (`manifest.appsource.xml`), complete icon set (16-128px PNG + SVG), and enterprise IT admin deployment guide. |
| **#69** | **S9-05** (#64) | `apps/desktop`, `scripts/`, `ci/` | Windows NSIS installer bundling in Tauri v2, Authenticode signing scripts (`sign-windows.sh`, `sign-windows.ps1`) with dry-run mode, and GitHub Actions CI runner. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 9 are CLOSED**:
  - Issue #60 (S9-01): Closed via PR #65.
  - Issue #61 (S9-02): Closed via PR #66.
  - Issue #62 (S9-03): Closed via PR #67.
  - Issue #63 (S9-04): Closed via PR #68.
  - Issue #64 (S9-05): Closed via PR #69.
- Repository issue backlog count: 0 open issues.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing in LanceDB; multi-document cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture & Streaming)**: Apple Silicon MLX local inference prioritized; Cloud Router fallback; real-time WebSocket token streaming with bounding box emission.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; interactive footnote deep-linking ties directly to `activeEvidence`.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Desktop Client (`apps/desktop`) and Excel Add-in (`apps/excel`) communicate with `packages/core-engine` daemon over REST and WebSocket broadcast.
- **ADR-005 (Production Packaging, Notarization & Authenticode Signing)**: Dual-platform distribution pipeline supporting macOS Hardened Runtime (`notarytool` stapling) and Windows Authenticode (NSIS installer with RFC 3161 timestamps).
- **ADR-006 (Enterprise On-Premises Docker LAN Box Architecture)**: Air-gapped multi-tenant deployment for enterprise banking accounting departments running on internal isolated networks.

---

## 5. Pitfalls Encountered

- **Pre-Release Brand Collision Risk**: Initial renaming consideration `FinLens` collided directly with an active Vietnamese business ("CÔNG TY TNHH DỮ LIỆU FINLENS", MST 3703442871) and YC S24 Finlens. Performing exhaustive trademark clearance before code modification prevented irreversible trademark liability.
- **Cross-Platform Dependency Compilation in Docker**: macOS-exclusive ML packages (`mlx` and `mlx-vlm`) fail compilation on Linux Docker containers. PEP 508 environment markers `; sys_platform == 'darwin'` in `requirements.txt` ensure deterministic cross-platform builds.
- **IDE Agent Working Directory Divergence**: Renaming the physical workspace directory during an active IDE agent session broke the CLI subprocess runner due to a stale CWD. Creating a symlink (`/Users/thanhdatvu/repos/Finsight -> /Users/thanhdatvu/repos/FinTrace`) solved the issue permanently.

---

## 6. Sprint 10 Horizon: next tasks

1. `S10-01: Automated E2E Regression Benchmarking Pipeline with CI Reporting` — `benchmarks/eval_golden_suite.py`, `.github/workflows/benchmark-regression.yml`
2. `S10-02: Multi-Page Table Stitching for Spanned Financial Statements` — `packages/core-engine/src/table_stitcher.py`, `packages/core-engine/src/contracts.py`
3. `S10-03: Enterprise Role-Based Access Control (RBAC) & Audit Log Export` — `packages/core-engine/src/auth.py`, `deploy/nginx/`
4. `S10-04: Offline VLM Quantization Tuning (4-bit vs 8-bit Accuracy Evaluation)` — `packages/core-engine/src/mlx_engine.py`, `benchmarks/`
5. `S10-05: Excel Add-in Formula Auditor & Dynamic Model Sensitivity Slider` — `apps/excel/src/components/SensitivitySlider.tsx`, `apps/excel/src/lib/`

---

## 7. Open Questions For The Human

- **Enterprise Pilot Target Selection**: For the initial banking pilot deployment in Sprint 10, should we prioritize deploying the Docker Compose LAN Box into an on-premises Linux server environment (e.g., Ubuntu LTS / RHEL), or packaging a single-binary Windows Server service installer?
