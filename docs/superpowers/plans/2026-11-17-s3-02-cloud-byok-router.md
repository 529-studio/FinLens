# S3-02: Cloud BYOK Router via LiteLLM Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Cloud BYOK (Bring Your Own Key) inference router using LiteLLM to support Anthropic Claude 3.5 Sonnet and Azure OpenAI enterprise endpoints with strict Zero-Leak security and visual grounding coordinate normalization.

**Architecture:** `CloudRouter` in `packages/core-engine/src/cloud_router.py` encapsulates multi-provider LLM/VLM routing. It reads BYOK credentials from environment variables or secure session state, formats image payloads into multi-modal Vision inputs, and queries cloud frontier models via LiteLLM. Bounding box coordinates are extracted, normalized to 0-1000 scale, and clamped. Plugs directly into `VlmRouter` and daemon endpoints.

**Tech Stack:** Python 3.12, LiteLLM, FastAPI, Pydantic v2, Pillow.

**Spec:** PRD §3, ADR-002, Sprint 3 Plan Task S3-02, AGENTS.md (Rules 1, 2, 11, 12, 13, 15).

## Global Constraints

- Zero-Leak Security Policy (Rule 2): Never output or log API keys in plain text, response payloads, or error traces.
- Multi-provider support: Anthropic (`claude-3-5-sonnet-20241022`), Azure OpenAI (`azure/gpt-4o`), and OpenAI (`gpt-4o`).
- Bounding Box Normalization: Coordinates must be normalized strictly to [ymin, xmin, ymax, xmax] (0-1000 scale).
- Path Traversal Defense: Image inputs must be validated with `is_path_safe`.
- Offline/No-Key Resilience: If no API key is configured or network is unreachable, fallback gracefully without crashing.
- Zero raw emojis (Rule 15).

## Review Focus

1. **Zero-Leak Validation:** Status endpoints and error logs must report `configured: true/false` and never expose partial or full key strings.
2. **Path Traversal on Image Files:** Passing arbitrary host files (`/etc/passwd`) must be blocked before reading or encoding to base64.
3. **Provider Fallback Routing:** When Claude API key is absent, allow routing to Azure OpenAI or offline fallback.
4. **Coordinate Invariant Defense:** Ensure bounding boxes parsed from cloud VLM outputs obey `ymax > ymin` and `xmax > xmin` within [0, 1000].
5. **CWD Independent Environment Loading:** Strip trailing whitespace and quotes from keys per `env-and-auth-ops-debugging`.

---

### Task 1: Cloud BYOK Router Core (`cloud_router.py`)

**Files:**
- Create: `packages/core-engine/src/cloud_router.py`
- Test: `packages/core-engine/tests/test_cloud_router.py`

**Interfaces:**
- Produces:
  - `class CloudRouter`
    - `get_available_providers() -> List[str]`
    - `set_api_key(provider: str, key: str) -> None`
    - `analyze_page(image_path: str, page_number: int, query: str, provider: str = "auto") -> Dict[str, Any]`
    - `parse_vlm_output(raw_text: str, page_number: int) -> Tuple[str, List[Dict[str, Any]]]`

- [ ] **Step 1: Write failing tests for `CloudRouter`**
  Cover provider detection, Zero-Leak validation, path traversal defense, coordinate clamping, and mock LiteLLM completion.

- [ ] **Step 2: Run test to verify it fails**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_cloud_router.py -v`
  Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `CloudRouter` in `packages/core-engine/src/cloud_router.py`**
  Implement provider routing, base64 image encoding, prompt construction, and LiteLLM adapter with offline fallback.

- [ ] **Step 4: Run test to verify it passes**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_cloud_router.py -v`
  Expected: PASS

- [ ] **Step 5: Commit**
  ```bash
  git add packages/core-engine/src/cloud_router.py packages/core-engine/tests/test_cloud_router.py
  git commit -m "feat(core-engine): implement Cloud BYOK router via LiteLLM"
  ```

---

### Task 2: Wire `CloudRouter` into `VlmRouter` and Daemon API

**Files:**
- Modify: `packages/core-engine/src/vlm_router.py`
- Modify: `packages/core-engine/src/contracts.py`
- Modify: `packages/core-engine/src/main.py`
- Test: `packages/core-engine/tests/test_api_and_security.py`

**Interfaces:**
- Consumes: `CloudRouter` from `cloud_router.py`.
- Produces:
  - `GET /api/v1/models/cloud/status` -> Returns configured cloud providers (zero-leak).
  - `POST /api/v1/models/cloud/keys` -> Configures BYOK keys securely.
  - Updated `VlmRouter._infer_cloud_litellm` delegating to `CloudRouter`.

- [ ] **Step 1: Write integration tests in `test_api_and_security.py`**
  Test cloud status endpoint, BYOK key configuration, and query with `inference_mode="cloud"`.

- [ ] **Step 2: Run test to verify it fails**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests/test_api_and_security.py -k "cloud" -v`
  Expected: FAIL with 404 Not Found.

- [ ] **Step 3: Update `vlm_router.py`, `contracts.py`, and `main.py`**
  Wire `CloudRouter` into `VlmRouter`, expose status and key management endpoints.

- [ ] **Step 4: Run test to verify it passes**
  Run: `packages/core-engine/.venv/bin/pytest packages/core-engine/tests -v`
  Expected: All 50+ tests PASS.

- [ ] **Step 5: Commit**
  ```bash
  git add packages/core-engine/src/ packages/core-engine/tests/
  git commit -m "feat(core-engine): integrate Cloud BYOK router into daemon API"
  ```

---

### Task 3: Empirical Verification, Independent Subagent Audit & PR

**Files:**
- Documentation: `docs/lesson_learn.md`

- [ ] **Step 1: Live cURL verification of Cloud BYOK endpoints**
  Launch daemon, verify `GET /api/v1/models/cloud/status`, configure key, and run `POST /api/v1/query` with `inference_mode="cloud"`. Verify Zero-Leak.

- [ ] **Step 2: Record post-mortem and lessons learned in `docs/lesson_learn.md`**
  Document LiteLLM multi-provider routing and Zero-Leak key management.

- [ ] **Step 3: Push branch and open Pull Request against `dev`**
  Push `feat/s3-cloud-router` and open PR via `gh pr create`.

- [ ] **Step 4: Dispatch independent subagent audit (Rule 13 / 14)**
  Audit PR diff against security, Zero-Leak, and contract standards.

- [ ] **Step 5: Merge PR with merge commit (`gh pr merge --merge`)**
  Merge the PR cleanly into `dev`.
