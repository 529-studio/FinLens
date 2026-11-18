# Sprint 3 Report: Cloud Router & Interactive Canvas

**Sprint**: 3  
**Status**: Completed  
**Deliverables**: S3-02 (Cloud Router), S3-03 (Settings), S3-Canvas (PDF.js Integration), S3-05 (CI/CD)

---

## 1. Quantitative Scorecard
| Metric | Result |
| :--- | :--- |
| Core-Engine Tests | 54/54 Passed |
| Desktop UI Tests | 26/26 Passed |
| CI/CD Pipeline | Operational |
| Independent Audits | 3/3 Passed |

## 2. Reality Checks
- **Cloud Router**: Verified secure credential handling (Zero-Leak) with Anthropic/Azure.
- **Settings**: Implemented dual-mode switcher, verified ergonomic touch targets.
- **Canvas**: Successfully integrated `pdfjs-dist` in `apps/desktop` with stable worker path loading.
- **CI/CD**: Established basic CI pipeline in GitHub Actions.

## 3. Lessons Learned
- **PDF.js Worker Path**: Bundled dependencies must be carefully managed. Moving the worker to `public/js/` was critical for correct production path resolution.
- **Touch Target Ergonomics**: Header close buttons in modals are prone to falling below the 48px ergonomic threshold. Explicit sizing is required.
