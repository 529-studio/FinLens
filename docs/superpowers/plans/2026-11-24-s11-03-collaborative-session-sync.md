# Implementation Plan — S11-03: Real-Time Collaborative Audit Session Sync via Secure WebSockets

## Phase 1: Contracts & Domain Engine (Backend)
- [ ] Step 1.1: Add collaborative session contracts to `packages/core-engine/src/contracts.py`:
  - `SessionEventType`, `UserPresence`, `AuditAnnotation`, `SessionState`, `CollaborativeMessage`, `CreateSessionRequest`.
- [ ] Step 1.2: Implement `AuditSessionManager` in `packages/core-engine/src/session_sync.py`:
  - In-memory thread-safe room registry protected by `asyncio.Lock`.
  - Session ID sanitization (`^[a-zA-Z0-9_-]{3,64}$`).
  - Client connection lifecycle (`connect`, `disconnect`, `prune_stale`).
  - Broadcast routing (all peers or excluding sender).
  - Presence updates & spatial annotation addition/resolution.
- [ ] Step 1.3: Wire endpoints in `packages/core-engine/src/main.py`:
  - `@app.websocket("/ws/v1/sessions/{session_id}")` with optional/required JWT authentication.
  - `POST /api/v1/sessions` and `GET /api/v1/sessions/{session_id}` for session inspection.
- [ ] Step 1.4: Author unit tests in `packages/core-engine/tests/test_session_sync.py`:
  - Validate multi-client broadcast, presence sync, annotation handling, input sanitization, and heartbeat.

## Phase 2: Frontend Desktop Types, Hook & UI (apps/desktop)
- [ ] Step 2.1: Define TypeScript contracts in `apps/desktop/src/types/session_sync.types.ts`.
- [ ] Step 2.2: Implement `useSessionSync` hook in `apps/desktop/src/hooks/useSessionSync.ts` with exponential backoff and heartbeat.
- [ ] Step 2.3: Implement `CollaborativeSessionBar` in `apps/desktop/src/components/pdf/CollaborativeSessionBar.tsx`:
  - Enforce 3 UI states: Skeleton loading, Error banner with Retry (`min-h-[48px]`), Empty state.
  - Render active peer chips with role badges and active page indicators.
  - Strictly free-licensed Lucide React icons, 0 raw Unicode emojis.
- [ ] Step 2.4: Author Vitest component tests in `apps/desktop/src/components/pdf/__tests__/CollaborativeSessionBar.test.tsx`:
  - Validate 3 UI states, `>=48px` touch target ergonomics, and zero raw emojis.

## Phase 3: Integration, Verification & Subagent Audit
- [ ] Step 3.1: Run full backend and frontend test suites (`pytest` and `npm --prefix apps/desktop test`).
- [ ] Step 3.2: Execute empirical live verification over local daemon (multi-client WebSocket test).
- [ ] Step 3.3: Record post-mortem and lessons learned in `docs/lesson_learn.md` and sync via `npm run harvest:lessons`.
- [ ] Step 3.4: Dispatch independent subagent auditor for code & UI/UX review.
- [ ] Step 3.5: Open PR against `dev`, verify GitHub Actions CI passes green, and merge with merge commit.
