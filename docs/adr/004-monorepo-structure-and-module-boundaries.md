# ADR-004: Cấu Trúc Monorepo & Ranh Giới Module Hộp Đen (Blackbox Boundaries)

- **Trạng thái:** Approved
- **Ngày quyết định:** 16/11/2026
- **Tác giả:** FinSight Architecture Team (lead-architect)
- **Tham chiếu:** 529 Engineering Standards (`module-boundary-and-concurrency`, `frontend-4file-and-resilient-ui`)

## Bối Cảnh (Context)
FinSight là một sản phẩm đa nền tảng kết hợp giữa Desktop Rust/Tauri, AI Engine Python, và Office Web Add-in TypeScript. Nếu để các phần phụ thuộc chéo vào nhau hoặc chia sẻ mã nguồn không có ranh giới, dự án sẽ nhanh chóng rơi vào "bẫy phụ thuộc", khó kiểm thử và không thể đóng gói độc lập.

## Quyết Định (Decisions)

### 1. Cấu Trúc Monorepo Độc Lập
Thiết lập cấu trúc thư mục phân tách tuyệt đối:
```
Finsight/
├── apps/
│   └── desktop/                  # Tauri v2 Desktop App (Rust + React 19)
├── packages/
│   ├── core-engine/              # Python Visual RAG Engine (PyMuPDF, ColPali, LanceDB, VLM)
│   └── office-addin/             # Office.js Web Add-in cho Microsoft Excel
├── benchmarks/                   # Dữ liệu kiểm thử BCTC & Harness đo Recall / Precision
├── docs/                         # PRD, Sprints, Team Roster, ADRs, Lessons Learned
├── .agents/                      # Cấu hình MCP (Lore, Antigravity CLI)
├── lore.ontology.yml             # Bộ quy tắc ký ức Lore
└── AGENTS.md                     # Quy chế làm việc của đội ngũ Subagents
```

### 2. Quy Tắc Ranh Giới Module (Blackbox Boundaries)
- **Core Engine (`packages/core-engine`):** Là một tiến trình độc lập, không import bất kỳ mã nào của frontend. Giao tiếp duy nhất qua HTTP REST / WebSocket JSON trên cổng `127.0.0.1:8765`.
- **Desktop Client (`apps/desktop`):** Đóng gói toàn bộ logic hiển thị. Không gọi trực tiếp vào internal functions của python; chỉ gửi request qua client fetcher an toàn.
- **Office Add-in (`packages/office-addin`):** Đóng gói theo chuẩn Office.js, chạy trong iframe sandbox của Microsoft Office. Kết nối tới Core Engine qua localhost HTTP endpoint.

### 3. Tuân Thủ Frontend 4-File Pattern
Mọi feature trên Frontend React bắt buộc chia thành 4 file chuẩn:
1. `[feature].types.ts`: Khai báo Type, DTO, không chứa code logic.
2. `[feature].fetch.ts`: Xử lý network call với timeout, abort controller, error status codes.
3. `[feature].hook.ts`: Chứa state machine, logic xử lý, expose clean API cho UI.
4. `[feature].component.tsx`: Render UI với 3 trạng thái bắt buộc: Skeleton, Error with Retry, Empty State.

## Hệ Quả (Consequences)
- Các subagent có thể làm việc song song trên từng thư mục mà không gây conflict merge code.
- Mỗi package có thể chạy test và build độc lập.
