# S3 Handoff & Sprint 4 Horizon

**Document**: `docs/HANDOFF-s3.md`  
**Date**: 2026-11-17  
**Repository**: `529-studio/Finsight`  
**Charter**: Transition ledger documenting Sprint 3 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (default development branch, protected, merge commit only)
- **Head commit**: `4f37664` (`feat(ci): add CI workflow for core-engine and desktop tests`)
- **Worktree**: Clean
- **Merged in this sprint**:
  - PR #30: `feat(core-engine): S3-02 Cloud BYOK inference router via LiteLLM`
  - PR #31: `feat(desktop): S3-03 Settings Modal, Dual-Mode Switcher, and Cloud BYOK configuration`
  - PR #32: `feat(desktop): S3-Canvas PDF.js integration scaffold`

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :--- | :------------------- |
| **#30** | **S3-02** | `core-engine` | Cloud BYOK inference router (LiteLLM) with secure key management |
| **#31** | **S3-03** | `apps/desktop` | Settings Modal with dual-mode switcher and Cloud BYOK configuration |
| **#32** | **S3-Canvas**| `apps/desktop` | Interactive PDF.js Canvas integration with worker loading |

---

## 3. Open Issues & Backlog

- #11 ([excel] S4-01: Office.js Webpack Build & Excel Custom Function =FINSIGHT.QUERY()): Open — Scheduled for Sprint 4.
- #12 ([excel] S4-03: 1-Click Financial Citation & Jump to Desktop Application): Open — Scheduled for Sprint 4.

---

## 4. Settled Architectural Decisions

- **Zero-Leak Credential Isolation**: API keys managed purely in memory, strictly forbidden in persistent state.
- **Worker Isolation**: Web workers (`pdf.worker.min.mjs`) must be served from `public/` and loaded via relative path.

---

## 5. Pitfalls Encountered

- **CI/CD Worker Pathing**: Bundled apps have different path expectations. Hardcoded paths to `node_modules` failed in production; explicit `public/` hosting is required.
- **Ergonomic Targets**: Modals often overlook the 48px touch target rule on interactive elements like close buttons.

---

## 6. Sprint 4 Horizon: next tasks

1. **Excel Custom Function Scaffold**: Implement `Excel.run` logic for `FINSIGHT.QUERY()` — `apps/excel`
2. **WebPack Build Setup**: Configure Excel Web Add-in Webpack build pipeline — `apps/excel`
3. **Citation Interop**: Connect Excel-to-Desktop interop bridge — `apps/excel`

---

## 7. Open Questions For The Human

- **Excel Deployment**: Will the add-in be deployed via centralized manifest (`manifest.xml`) or local sideloading for development in this phase?
