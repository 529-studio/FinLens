# Changelog

All notable changes to **FinTrace** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-11-22 - General Availability (GA)

### Summary
FinTrace v1.0.0 marks the official commercial release of the **Visual Financial Intelligence Platform**. FinTrace solves the three fatal flaws of traditional text-based RAG on financial statements: chart blindness, complex table fragmentation, and severed footnote audit trails.

### Added
- **Visual RAG ColPali Late-Interaction Engine**:
  - High-resolution PDF page rendering (150-200 DPI PNG) with late-interaction patch retrieval.
  - Sub-second retrieval over LanceDB vector store maintaining immutable normalized coordinates `[0, 1000]`.
- **Dual-Engine Inference Architecture**:
  - Local Apple Silicon MLX inference (`mlx-community/Qwen2.5-VL-7B-Instruct-4bit`) for privacy-first, zero-leak processing.
  - Cloud BYOK frontier router supporting Claude 3.5 Sonnet, Azure OpenAI, and OpenAI GPT-4o.
- **WebSocket Streaming Inference (`/ws/query/stream`)**:
  - Asynchronous generator token streaming with progressive text rendering in Desktop Chat and Excel Taskpane.
  - Strict path traversal defense and connection lifecycle management.
- **Footnote Disambiguation & Formula Extraction**:
  - Automated mapping from consolidated financial statements line items to Thuyết minh BCTC (`/api/v1/query/footnotes`).
  - Rich audit trail export to Excel with embedded footnote comments and formulas.
- **Multi-Document Comparative Analysis**:
  - Cross-year BCTC comparison (e.g. 2022 vs 2023) with synchronized visual evidence switching.
- **Production Packaging & Apple Notarization**:
  - macOS hardened runtime entitlements (`entitlements.plist`) enabling JIT compilation and local IPC.
  - Automated notarization and stapling pipeline via Apple `notarytool` (`scripts/notarize-macos.sh`).
- **Golden Dataset Quantitative Verification**:
  - 105 real-world Vietnamese financial queries achieving **100% Top-1 recall**, **0% chart blindness** (vs 34.3% in text-based RAG), and **0.9220 mean bounding box IoU**.
- **Monorepo Brand Identity & Packaging**:
  - Rebranded from FinSight to **FinTrace** across Desktop, Excel Add-in, Core Engine, and CI workflows.
  - Standardized User-Agent headers (`FinTrace-Desktop-Client/1.0`, `FinTrace-Excel-Addin/1.0`).

### Changed
- Synchronized all monorepo packages to version `1.0.0` (`apps/desktop`, `apps/excel`, `packages/core-engine`).
- Hardened path traversal security checks to enforce authorized root boundaries (`~/.fintrace`, `~/.finsight`, workspace).
- Enforced 529 Engineering Standards: Zero-Emoji UI standard (Rule 15), Zero-Leak Security Policy (Rule 2), and Evidence-based Definition of Done (Rule 3).
