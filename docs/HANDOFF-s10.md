# S10 Handoff & Sprint 11 Horizon

**Document**: `docs/HANDOFF-s10.md`  
**Date**: 2026-11-22  
**Repository**: `529-studio/FinTrace`  
**Charter**: Transition ledger documenting Sprint 10 completion state, delivered capabilities, settled architecture decisions, pitfalls, and next tasks for a fresh conversation.

---

## 1. Branch & Commit Status

- **Active branch**: `dev` (transitioning via `docs/s10-handoff`)
- **Head commit**: `b7d3bc9` (`Merge pull request #84 from 529-studio/docs/s10-lesson-29`)
- **Worktree**: clean (all 5 feature branches merged via PR merge commits into `dev`)
- **Merged in this sprint**:
  - PR #76 (`feat/s10-01-regression-benchmark`): Automated E2E Regression Benchmarking Pipeline with CI Reporting (Issue #71).
  - PR #77 (`feat/s10-02-multipage-table-stitching`): Multi-Page Table Stitching for Spanned Financial Statements (Issue #72).
  - PR #78 (`docs/s10-lesson-learned-table-stitching`): Lesson 26 on Multi-Page Table Stitching & Vietnamese BCTC Normalization.
  - PR #79 (`feat/s10-03-enterprise-rbac-audit-log`): Enterprise Role-Based Access Control (RBAC) & Tamper-Evident Audit Logging (Issue #73).
  - PR #80 (`docs/s10-lesson-learned-rbac-audit`): Lesson 27 on Enterprise RBAC & Tamper-Evident SHA-256 Audit Chaining.
  - PR #81 (`feat/s10-04-vlm-quantization-tuning`): Offline VLM Quantization Tuning (4-bit vs 8-bit Accuracy Evaluation) (Issue #74).
  - PR #82 (`docs/s10-lesson-28`): Lesson 28 on VLM Quantization Trade-offs & Memory Ceiling Tuning.
  - PR #83 (`feat/s10-05-excel-formula-auditor-sensitivity`): Excel Add-in Formula Auditor & Dynamic Model Sensitivity Slider (Issue #75).
  - PR #84 (`docs/s10-lesson-29`): Lesson 29 on AST Formula Auditor & Kiosk Ergonomic Sensitivity Slider.

---

## 2. Merged Deliverables

| PR | Task | Subsystem | Delivered capability |
| :--- | :--- | :-------- | :------------------- |
| **#76** | **S10-01** (#71) | `benchmarks/`, `ci/` | Automated E2E regression benchmarking pipeline with baseline diffs, zero-emoji Markdown CI reports, and GitHub Actions workflow. |
| **#77** | **S10-02** (#72) | `core-engine` | Multi-page financial table stitcher resolving repeated headers, Vietnamese continuation titles, column shifts, and split-row concatenation. |
| **#79** | **S10-03** (#73) | `core-engine`, `deploy/` | Pure-Python RFC 7519 HS256 JWT RBAC (4 roles), fail-closed Nginx gateway, and SHA-256 chained tamper-evident audit logger with zero-leak scrubbing. |
| **#81** | **S10-04** (#74) | `core-engine`, `benchmarks/` | Dynamic 4-bit vs 8-bit VLM quantization switching, Apple Silicon Metal memory ceiling enforcement (6GB vs 10GB), and empirical trade-off report. |
| **#83** | **S10-05** (#75) | `apps/excel` | Deterministic zero-eval AST formula evaluator, 3-color DFS cycle detection, and Kiosk-standard ($\ge 48\text{px}$) interactive sensitivity slider. |

---

## 3. Open Issues & Backlog

- **All active milestone issues for Sprint 10 are CLOSED**:
  - Issue #71 (S10-01): Closed via PR #76.
  - Issue #72 (S10-02): Closed via PR #77.
  - Issue #73 (S10-03): Closed via PR #79.
  - Issue #74 (S10-04): Closed via PR #81.
  - Issue #75 (S10-05): Closed via PR #83.
- Repository issue backlog count: 0 open issues.

---

## 4. Settled Architectural Decisions

- **ADR-001 (Hybrid Desktop & Visual RAG Native)**: Visual RAG ColPali late-interaction indexing in LanceDB; multi-document cross-referencing maintains normalized coordinates `[0, 1000]`.
- **ADR-002 (Dual-Mode Inference Architecture & Streaming)**: Apple Silicon MLX local inference prioritized; Cloud Router fallback; real-time WebSocket token streaming with bounding box emission.
- **ADR-003 (Bounding Box Visual Grounding Protocol)**: Audited SVG overlay remains 100% immutable over source PDF; multi-page stitched tables preserve origin page and coordinates.
- **ADR-004 (Monorepo Blackbox Boundaries & IPC)**: Desktop Client (`apps/desktop`) and Excel Add-in (`apps/excel`) communicate with `packages/core-engine` daemon over REST and WebSocket broadcast.
- **ADR-005 (Production Packaging, Notarization & Authenticode Signing)**: Dual-platform distribution pipeline supporting macOS Hardened Runtime (`notarytool` stapling) and Windows Authenticode.
- **ADR-006 (Enterprise On-Premises Docker LAN Box Architecture)**: Air-gapped multi-tenant deployment for enterprise banking accounting departments running on internal isolated networks.
- **ADR-007 (Enterprise RBAC, Cryptographic Audit Chaining & AST Formula Engine)**: Tamper-evident SHA-256 event chaining for audit trails, pure Python JWT authentication, and zero-eval recursive descent AST formula evaluation.

---

## 5. Pitfalls Encountered

- **Base64url Padding Bit Invariance**: Mutating the 43rd base64url character of a 32-byte JWT signature may not alter the decoded bytes due to 2 unused padding bits. Test suites must mutate `sig[0]` to deterministically invalidate cryptographic signatures.
- **Vietnamese BCTC Continuation Header Variations**: Continuation markers in Vietnamese filings vary widely (`(Tiếp theo Bảng cân đối kế toán)`, `(tiếp theo)`). Applying symmetric ASCII de-accenting (`strip_accents`) to both raw text and keyword registries eliminates false negatives.
- **JavaScript IEEE-754 Floating-Point Drift**: Direct financial multiplication in formula evaluation (e.g. `50000 * 1.1 = 55000.00000000001`) causes subtle comparison mismatches; normalizing via `Math.round((val + Number.EPSILON) * 1e9) / 1e9` guarantees exact precision.

---

## 6. Sprint 11 Horizon: next tasks

1. `S11-01: Multi-Document Portfolio Synthesis & Cross-Filing Comparative Analytics` — `packages/core-engine/src/comparative_query.py`
2. `S11-02: Automated Financial Ratio Calculation Engine & Cash Flow Health Screener` — `packages/core-engine/src/ratio_engine.py`
3. `S11-03: Real-Time Collaborative Audit Session Sync via Secure WebSockets` — `packages/core-engine/src/session_sync.py`, `apps/desktop/`
4. `S11-04: Offline Air-Gapped License Key Cryptographic Activation & Hardware Fingerprinting` — `packages/core-engine/src/licensing.py`
5. `S11-05: Excel Add-in Scenario Comparison Waterfall Chart & PDF Grounding Export` — `apps/excel/src/components/WaterfallChart.tsx`

---

## 7. Open Questions For The Human

- **Air-Gapped Enterprise License Activation Architecture**: For on-premises banking deployments in Sprint 11, should offline air-gapped license key activation rely on machine hardware GUID + Ed25519 digital signature files, or enterprise PKI X.509 client certificate verification?
