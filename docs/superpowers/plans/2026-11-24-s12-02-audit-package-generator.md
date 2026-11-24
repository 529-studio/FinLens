# S12-02: Automated Audit Trail Exporter & Regulatory Package Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated audit trail exporter and regulatory compliance package generator capable of producing Inline XBRL (iXBRL), PDF/A-3 archival containers with embedded machine-readable JSON-LD/XML metadata, and cryptographic SHA-256 tamper-evident event chains.

**Architecture:**
1. `packages/core-engine/src/contracts.py`: Extends contracts with `RegulatoryPackageFormat`, `PackageManifestItem`, `AuditPackageRequest`, `AuditPackageResponse`.
2. `packages/core-engine/src/audit_packager.py`: Core package generator assembling structured XBRL XML, PDF/A-3 archival streams with embedded `/AFRelationship /Data` dictionaries, zip bundles, and SHA-256 hash chaining.
3. `packages/core-engine/src/main.py`: Mounts `POST /api/v1/audit/export-package` with RBAC (`Permission.DOC_READ`), strict path traversal validation (`^[a-zA-Z0-9_\-]+$`), and audit event logging.

**Tech Stack:**
- Python 3.13, FastAPI, Pydantic v2, Pytest, PyMuPDF (fitz) or standard binary streams, hashlib, zipfile.
- Standards: AGENTS.md Rules 1, 2, 3, 11, 12, 13, 14, 15 and ADR-003, ADR-007.

**Spec:** Issue #99 (`[rag-ml] S12-02: Automated Audit Trail Exporter & Regulatory Package Generator (XBRL & PDF/A-3)`).

---

## Global Constraints

- **Git Flow (Rule 12):** Active branch is `feat/s12-02-audit-package-generator` targeting `dev`. PR merge commit required.
- **Security & Path Traversal (Rule 13B):** Every `document_id` strictly validated against regex `^[a-zA-Z0-9_\-]+$` and rejects any `..` path traversal attempt.
- **Zero-Leak Policy (Rule 2):** Zero credentials or private keys exposed in package files or response payloads.
- **Zero Raw Emojis in UI / Output (Rule 15):** 0 raw emojis in narrative summaries, metadata schemas, and generated report files.
- **Tamper-Evident Chaining (ADR-007):** SHA-256 event chaining ensures verifiable immutability of the audit package.

---

## Review Focus

1. **Path Traversal Defense:** Supplying `["../../etc/passwd"]` in document targets returns HTTP 400/422.
2. **Missing Document Target:** If a document is missing in the store index, returns HTTP 404.
3. **Format Integrity:** XBRL documents validate as well-formed XML; PDF/A-3 streams contain proper header `%PDF-1.7` and embedded `/Filespec` attachments.
4. **Bundle Zip Structure:** Dual-format `BUNDLE` export contains valid ZIP archive with readable internal XBRL, PDF/A-3, and manifest files.
5. **SHA-256 Hash Chaining:** Tamper-evident root hash uniquely and deterministically matches the sequence of audited findings.

---

### Task 1: Regulatory Packager Contracts (`contracts.py`)
- Modify: `packages/core-engine/src/contracts.py`
- Test: `packages/core-engine/tests/test_audit_packager.py`

### Task 2: Pure Package Generator Engine (`audit_packager.py`)
- Create: `packages/core-engine/src/audit_packager.py`
- Test: `packages/core-engine/tests/test_audit_packager.py`

### Task 3: REST API Endpoint (`main.py`)
- Modify: `packages/core-engine/src/main.py`
- Test: `packages/core-engine/tests/test_audit_packager.py`

### Task 4: Full Verification, Independent Subagent Audit & Merge
- Run full core-engine test suite.
- Push branch, create PR targeting `dev`, dispatch independent subagent audit.
- Merge PR with `--merge`.
