# Implementation Plan: Sprint 7 Task S7-03 - Tauri v2 Native Desktop Bundle Verification & Daemon Lifecycle

## 1. Executive Summary & Goals
- **Issue Reference:** [#44 - [frontend] S7-03: Tauri v2 Native Desktop Bundle Verification & Daemon Lifecycle](https://github.com/529-studio/Finsight/issues/44)
- **Target Branch:** `feat/s7-tauri-daemon-lifecycle` targeting `dev`
- **Objective:**
  Set up and verify the native desktop packaging and execution harness for FinSight Desktop using **Tauri v2** (`apps/desktop/src-tauri`).
  Ensure the backend Python daemon lifecycle (spawning, health polling against `http://127.0.0.1:8765/health`, and graceful shutdown on application exit) is bulletproof, leaving **0 zombie processes** upon window close or quit.

---

## 2. Architectural Blueprint & File Map

```
apps/desktop/
├── src-tauri/
│   ├── Cargo.toml                          # Tauri v2 dependencies (tauri, tauri-plugin-shell, reqwest/ureq)
│   ├── tauri.conf.json                     # Bundle config: targets (dmg, app), window 1280x800, permissions
│   ├── capabilities/
│   │   └── default.json                    # Tauri v2 security capabilities (core + scoped shell)
│   └── src/
│       ├── main.rs                         # Standard Tauri v2 main binary entrypoint
│       ├── lib.rs                          # App builder, lifecycle event listener (ExitRequested / WindowDestroyed)
│       └── daemon.rs                       # DaemonManager: spawn child, poll health, kill on exit (zero zombies)
└── src/
    ├── hooks/
    │   ├── useDaemonLifecycle.ts           # React hook for daemon status & health state
    │   └── __tests__/
    │       └── useDaemonLifecycle.test.ts  # Unit tests for daemon lifecycle hook
    └── components/layout/
        └── SplitView.component.tsx         # Displays subtle daemon connectivity indicator
```

---

## 3. Detailed Technical Tasks

### Task 1: Tauri v2 Scaffolding & Configuration
- Run non-interactive `tauri init --ci` in `apps/desktop`:
  - App Name: `FinSight`
  - Window Title: `FinSight — Trợ lý Phân Tích BCTC bằng Visual RAG`
  - Frontend Dist: `../dist`
  - Dev URL: `http://localhost:5173`
  - Before Dev: `npm run dev`
  - Before Build: `npm run build`
- Configure `tauri.conf.json`:
  - `bundle.targets`: `["dmg", "app"]`
  - Identifier: `com.finsight.desktop`
  - Set default window dimensions to `1280x800` (min width 960, min height 600) with dark background `#020617`.
  - Configure capabilities in `capabilities/default.json` for Tauri v2 security model.

### Task 2: Rust Daemon Process Manager (`daemon.rs`, `lib.rs`)
- Implement `DaemonManager`:
  - Maintains `Option<Child>` guarded by `Mutex`.
  - Function `start_daemon_if_needed()`:
    - First, attempts HTTP GET to `http://127.0.0.1:8765/health`.
    - If healthy, does not spawn redundant process.
    - If unreachable, locates `.venv/bin/python` in `packages/core-engine` (or virtualenv path) and spawns `packages/core-engine/src/main.py`.
    - Polls health check endpoint with backoff up to 10 seconds.
  - Function `terminate_daemon()`:
    - If a child was spawned, sends SIGTERM (`child.kill()`).
    - Verifies process termination to prevent zombie/orphaned processes.
- Bind Tauri v2 application lifecycle events:
  - `RunEvent::ExitRequested` or `RunEvent::Exit`: invoke `DaemonManager::terminate_daemon()`.
  - Expose Tauri command `get_daemon_status` for frontend status querying.

### Task 3: React Frontend Hook & UI Integration
- Create `apps/desktop/src/hooks/useDaemonLifecycle.ts`:
  - Polls daemon health on mount.
  - Exposes `daemonStatus: 'connecting' | 'online' | 'offline'`, `latencyMs`, and `retryConnection`.
- Update header in `apps/desktop/src/components/layout/SplitView.component.tsx`:
  - Displays daemon connectivity dot (`bg-emerald-400` when online, `bg-amber-400` connecting, `bg-rose-400` offline with retry button).
  - 100% Lucide React SVGs, 0 raw emojis, Kiosk $\ge 48\text{px}$ touch target on retry button.

### Task 4: Automated Testing & Verification
- Test `useDaemonLifecycle.test.ts` via Vitest.
- Run `cargo check` and `cargo test` in `apps/desktop/src-tauri`.
- Verify `npm --prefix apps/desktop run build` (`tsc && vite build`) passes with 0 errors.
- Empirical test:
  - Start daemon via manager, check health response.
  - Terminate manager, check that `lsof -ti :8765` returns empty (0 zombie processes).
- Playwright screenshot proof in `docs/proofs/sprint7/s7-03-tauri-lifecycle.png`.

### Task 5: Subagent Audit, CI & Merge
- Dispatch independent subagent `research` with role `Independent Codebase & UI/UX Quality Auditor`.
- Obtain `VERDICT: APPROVED 🟢`.
- Commit, push, create PR for Issue #44, monitor GitHub Actions CI, and merge into `dev`.

---

## 4. Definition of Done (DoD)
- [ ] Tauri v2 `src-tauri` fully configured with `tauri.conf.json` (bundle targets `dmg`, `app`).
- [ ] `DaemonManager` in Rust successfully spawns daemon if absent and guarantees clean termination on quit (0 zombies).
- [ ] React frontend `useDaemonLifecycle` integrated with 3 UI states and zero emojis.
- [ ] `npm --prefix apps/desktop test` (all 30+ tests) pass 100%.
- [ ] `npm --prefix apps/desktop run build` exits 0.
- [ ] Empirical Playwright screenshot saved to `docs/proofs/sprint7/s7-03-tauri-lifecycle.png`.
- [ ] Independent Subagent Audit gives `VERDICT: APPROVED 🟢`.
- [ ] PR merged to `dev` with `--merge` commit and passing GitHub Actions CI.
