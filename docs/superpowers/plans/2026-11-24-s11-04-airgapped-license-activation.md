# Implementation Plan — S11-04: Offline Air-Gapped License Key Cryptographic Activation & Hardware Fingerprinting

## Phase 1: Contracts & Cryptographic License Engine
- [ ] Step 1.1: Add licensing contracts to `packages/core-engine/src/contracts.py`:
  - `LicenseTier`, `LicenseState`, `LicensePayload`, `LicenseFileDTO`, `LicenseStatusResponse`, `LicenseActivationRequest`, `LicenseActivationResponse`.
- [ ] Step 1.2: Implement `packages/core-engine/src/licensing.py`:
  - One-way hardware fingerprint generator `get_machine_fingerprint()`.
  - Ed25519 canonical message serialization and signature verification.
  - License validator with state determination (`ACTIVE`, `EXPIRED`, `INVALID_SIGNATURE`, `FINGERPRINT_MISMATCH`, `COMMUNITY_EVALUATION`).
  - Atomic license file persistence to `~/.finsight/license.json` (`0o600` permissions).
  - Test helper `generate_test_license_key(private_key, payload)`.
- [ ] Step 1.3: Wire REST endpoints in `packages/core-engine/src/main.py`:
  - `POST /api/v1/license/activate` guarded by `Permission.ADMIN_CONFIG`.
  - `GET /api/v1/license/status` guarded by `Permission.DOC_READ`.
- [ ] Step 1.4: Author unit & integration test suite in `packages/core-engine/tests/test_licensing.py`:
  - Test hardware fingerprint reproducibility and zero-leak characteristics.
  - Test valid activation, signature verification, and atomic file saving.
  - Test rejection of tampered payloads and wrong signatures.
  - Test rejection of expired license keys.
  - Test rejection of machine fingerprint mismatches (and acceptance of floating `*`).
  - Test REST endpoints and RBAC enforcement.

## Phase 2: Verification, Knowledge Sync & Independent Subagent Audit
- [ ] Step 2.1: Run full pytest suite across core-engine (`pytest packages/core-engine/tests/test_licensing.py` and full suite).
- [ ] Step 2.2: Live empirical verification script testing license generation, activation, and status checks against running daemon.
- [ ] Step 2.3: Verify Zero-Emoji policy across all modified files.
- [ ] Step 2.4: Record Lesson 33 in `docs/lesson_learn.md` and sync via `npm run harvest:lessons`.
- [ ] Step 2.5: Update Lore shared memory (`memory_write` & `memory_approve`).
- [ ] Step 2.6: Dispatch independent subagent auditor for code & security review.
- [ ] Step 2.7: Open PR against `dev`, verify CI passes green, and merge via merge commit.
