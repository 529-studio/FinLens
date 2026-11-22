#!/usr/bin/env python3
"""
Creates comprehensive GitHub issues for FinTrace Sprint 9 following 529 Engineering Standards.
Governed by AGENTS.md, evidence-based Definition of Done, and technical details.
"""

import subprocess
import json

ISSUES = [
    {
        "title": "[architect] S9-01: Production Release v1.0.0 Tagging, Changelog & GA Release Pipeline",
        "labels": ["sprint-9", "role:architect"],
        "body": """## Context
FinTrace has completed brand clearance, rebranding, Apple Hardened Runtime notarization, and quantitative evaluation (100% Top-1 recall, 0% chart blindness).
Now we need to synchronize package versions to `1.0.0`, author the comprehensive `CHANGELOG.md`, and validate the production release pipeline.

## Depends on
Rebrand to FinTrace (PR #59 merged into `dev`).

## Technical Details
- File paths to modify:
  - `apps/desktop/src-tauri/tauri.conf.json`: Bump version to `"1.0.0"`.
  - `apps/desktop/package.json`: Bump version to `"1.0.0"`.
  - `apps/excel/package.json`: Bump version to `"1.0.0"`.
  - `apps/excel/manifest.xml` & `apps/excel/manifest.prod.xml`: Bump version to `"1.0.0.0"`.
  - `packages/core-engine/src/main.py`: Bump version to `"1.0.0"`.
  - `CHANGELOG.md`: Author structured release notes capturing Sprint 1 through Sprint 8 achievements.
  - `.github/workflows/release-desktop.yml`: Validate release build triggers on tag `v1.0.0`.

## Out of Scope
- Do not publish public announcements on social media before binary builds pass.
- Do not commit signing secrets into git repository.

## Definition of Done
- [ ] Monorepo package versions across desktop, excel, tauri, and core-engine are synchronized to `1.0.0`.
- [ ] `CHANGELOG.md` created with documented milestones, architectural decisions, and capabilities.
- [ ] `scripts/notarize-macos.sh --dry-run` succeeds with v1.0.0 target path.
- [ ] 100% test suites pass across all tiers.
- [ ] PR created and merged into `dev` via merge commit.
"""
    },
    {
        "title": "[devops] S9-02: Multi-Tenant Docker Compose LAN Deployment for Enterprise Banking",
        "labels": ["sprint-9", "role:architect", "role:rag-ml"],
        "body": """## Context
Enterprise banking institutions and audit firms require strictly isolated on-premise / private LAN deployment where financial reports never leave their internal infrastructure.
Governed by `docker-runtime-patching-and-secrets` standard.

## Depends on
S9-01 (Version 1.0.0 alignment).

## Technical Details
- File paths to create/verify:
  - `deploy/Dockerfile.engine`: Multi-stage Python 3.12 image, non-root user (`appuser:10001`), curl healthcheck (`http://localhost:8765/health`).
  - `deploy/docker-compose.yml`: Production LAN configuration with named volumes (`fintrace_lancedb`, `fintrace_uploads`, `fintrace_cache`), restart policy, resource limits, and healthcheck.
  - `deploy/.env.lan.example`: Zero-leak cryptographic secret configuration template (`FINTRACE_SECRET_KEY`, `LAN_BIND_HOST=0.0.0.0`).
  - `deploy/nginx/fintrace-lan.conf`: Nginx reverse proxy with CORS headers for Office.js and LAN desktop clients, WebSocket upgrade (`/ws/query/stream`).
  - `deploy/tests/test_lan_deploy.sh`: Automated smoke test checking startup, healthcheck endpoint, and path traversal rejection.

## Out of Scope
- Do not push pre-built Docker images to public Docker Hub until internal registry security review is complete.
- Do not disable path traversal protections in LAN mode.

## Definition of Done
- [ ] `docker compose -f deploy/docker-compose.yml config` passes validation with 0 errors.
- [ ] Non-root execution (`10001`) and zero-leak environment isolation verified.
- [ ] Healthcheck endpoint passes within 15 seconds of container launch.
- [ ] Smoke test script demonstrates successful document ingestion and query over LAN endpoint.
- [ ] PR created and merged into `dev` via merge commit.
"""
    },
    {
        "title": "[frontend] S9-03: Interactive Footnote Deep-Linking in Desktop PDF Viewer",
        "labels": ["sprint-9", "role:frontend"],
        "body": """## Context
In Sprint 8 (PR #57), footnote disambiguation was delivered on the backend (`/api/v1/query/footnotes`) and in Excel comments.
In Desktop Client, analysts reviewing financial statements need to click on a Footnote badge/chip (e.g. `TM 4 (Tiền và tương đương tiền)`) and have the PDF viewer automatically jump to the target Thuyết minh page with bounding box highlight.

## Depends on
S8-04 (`/api/v1/query/footnotes` endpoint) & S9-01.

## Technical Details
- File paths to modify/create:
  - `apps/desktop/src/types/visual_rag.types.ts`: Define `FootnoteReferenceDTO` (`footnoteNumber`, `lineItem`, `targetPage`, `boundingBox`).
  - `apps/desktop/src/hooks/usePdfViewer.ts`: Implement `jumpToPage(page: number, boundingBox?: BoundingBox)` and smooth scroll handler.
  - `apps/desktop/src/components/chat/FootnoteChip.tsx`: Interactive chip component with tooltip, 48px touch target ergonomics, Lucide `FileText` icon, and click handler.
  - `apps/desktop/src/components/layout/SplitView.component.tsx`: Render Footnote chips under answer text, connecting click events to PDF viewer deep-linking.
  - `apps/desktop/src/components/chat/__tests__/FootnoteChip.test.tsx`: Vitest suite testing rendering, accessibility labels, and click delegation.

## Out of Scope
- Do not alter OCR or core extraction models; utilize existing footnote disambiguation endpoints.
- Do not introduce raw emojis in UI (enforce AGENTS.md Rule 15).

## Definition of Done
- [ ] Clicking a footnote chip in Desktop UI smoothly scrolls the PDF viewer to the footnote's page.
- [ ] Bounding box overlay displays active footnote highlight with high-contrast indicator.
- [ ] 100% Vitest unit tests pass.
- [ ] Zero raw emojis in component (Rule 15).
- [ ] PR created and merged into `dev` via merge commit.
"""
    },
    {
        "title": "[excel] S9-04: Microsoft AppSource Production Manifest Package & Admin Deployment",
        "labels": ["sprint-9", "role:excel"],
        "body": """## Context
For corporate rollout across enterprise accounting departments, the Excel Add-in requires a strictly compliant AppSource package and documentation for Microsoft 365 Admin Center centralized deployment.

## Depends on
S9-01 (Version 1.0.0 alignment).

## Technical Details
- File paths to create/modify:
  - `apps/excel/manifest.appsource.xml`: Schema-compliant manifest with AppDomains, high-res icons (16x16, 32x32, 64x64, 80x80), and permissions.
  - `apps/excel/scripts/validate-manifest.js`: Automated validation script using `office-addin-manifest` CLI.
  - `apps/excel/assets/`: Ensure all required AppSource icons (brand vector SVG export, PNG icons) exist.
  - `docs/deployment/MICROSOFT_365_ADMIN_DEPLOYMENT.md`: Step-by-step enterprise guide for IT admins to deploy FinTrace Add-in centralized across Excel desktop & web.

## Out of Scope
- Do not submit to public AppSource marketplace without organization admin approval.
- Do not allow unencrypted HTTP endpoints in production manifest.

## Definition of Done
- [ ] Manifest validation passes all Microsoft Office Add-in validator checks (`office-addin-manifest validate`).
- [ ] High-resolution brand assets correctly linked and accessible.
- [ ] Complete enterprise deployment guide authored with verified steps.
- [ ] PR created and merged into `dev` via merge commit.
"""
    },
    {
        "title": "[devops] S9-05: Windows Authenticode Code Signing & Packaging Pipeline",
        "labels": ["sprint-9", "role:architect", "role:frontend"],
        "body": """## Context
To support enterprise finance teams running Windows 11/10 workstations without SmartScreen warnings, configure Tauri v2 NSIS / MSIX bundling and Windows Authenticode signing pipeline.

## Depends on
S9-01 (Version 1.0.0 alignment).

## Technical Details
- File paths to create/modify:
  - `apps/desktop/src-tauri/tauri.conf.json`: Configure Windows NSIS bundle target (`targets: ["dmg", "app", "nsis"]`) with custom installer icons and install directory.
  - `scripts/sign-windows.ps1` (or `scripts/sign-windows.sh`): Windows signing script supporting Azure Trusted Signing / signtool with `--dry-run` validation.
  - `.github/workflows/release-desktop.yml`: Add `build-and-sign-windows` job targeting `windows-latest`.
  - `apps/desktop/src/utils/__tests__/signing-config.test.ts`: Extend test suite to verify Windows bundle configuration.

## Out of Scope
- Do not hardcode private PFX certificates or passwords in repository or workflows.
- Do not disable SmartScreen or bypass Windows Defender checks.

## Definition of Done
- [ ] `tauri.conf.json` declares valid NSIS bundle settings.
- [ ] Windows signing script passes `--dry-run` verification.
- [ ] Signing configuration test suite passes with 100% rate.
- [ ] PR created and merged into `dev` via merge commit.
"""
    }
]

def main():
    print(f"Creating {len(ISSUES)} structured issues in 529-studio/FinTrace...")
    created_issues = []
    for issue in ISSUES:
        cmd = [
            "gh", "issue", "create",
            "--repo", "529-studio/FinTrace",
            "--title", issue["title"],
            "--body", issue["body"]
        ]
        for label in issue.get("labels", []):
            cmd.extend(["--label", label])

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            issue_url = res.stdout.strip()
            print(f"✓ Created: {issue['title']} -> {issue_url}")
            created_issues.append({"title": issue["title"], "url": issue_url})
        else:
            print(f"✗ Failed: {issue['title']}")
            print(res.stderr)

    print("\nSummary of created Sprint 9 issues:")
    for item in created_issues:
        print(f"- {item['title']}: {item['url']}")

if __name__ == "__main__":
    main()
