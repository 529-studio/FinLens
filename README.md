# FinTrace — Visual Financial RAG & Hybrid Desktop Platform

> **Nền tảng Trợ Lý Phân Tích Báo Cáo Tài Chính bằng Visual RAG (Hybrid Desktop & Excel Add-in)**  
> *Sản phẩm của 529 Studio Architecture Team*

---

## 1. Giới Thiệu & Bài Toán Giải Quyết

FinTrace giải quyết triệt để 3 **"tử huyệt"** của RAG truyền thống khi phân tích Báo cáo tài chính (BCTC) và Báo cáo thường niên:
1. **Mù biểu đồ (Charts Blindness):** Biểu đồ cơ cấu doanh thu, biên lợi nhuận, biểu đồ thác nước (waterfall) bị OCR và text parser bỏ qua 100%.
2. **Vỡ cấu trúc bảng (Complex Tables Fragmentation):** Cắt đôi bảng biểu nhiều tầng làm mất ngữ cảnh dòng - cột.
3. **Mất liên kết chú thích (Footnotes Severance):** Các thuyết minh chân trang về nợ tiềm tàng và rủi ro bị tách rời khỏi số liệu chính.

**Giải pháp của FinTrace:**
- **Visual RAG Native:** Mỗi trang PDF được render thành ảnh độ phân giải cao (150-200 DPI PNG).
- **ColPali Visual Retrieval:** Tìm kiếm trực tiếp trên các mảnh ảnh (visual patches) qua cơ chế Late Interaction (MaxSim), không cần qua OCR.
- **Visual Grounding:** Mô hình VLM (`Qwen2.5-VL` / `Claude 3.5 Sonnet`) suy luận trực tiếp trên ảnh và trả về tọa độ Bounding Box `[ymin, xmin, ymax, xmax]` (thang đo 0-1000).
- **Audit Trail 1-Click:** Nhấp vào số liệu để nhảy ngay đến trang PDF gốc với khung viền đỏ highlight vùng bằng chứng kiểm toán.

---

## 2. Chiến Lược 2 Giai Đoạn (2-Phase Roadmap)

- **Giai đoạn 1: Hybrid Desktop App (Tauri v2 + React 19 + TypeScript)**
  - Chạy mượt mà trên macOS và Windows với bộ cài < 20MB.
  - **Dual-Engine:**
    - *Local Engine:* Chạy 100% offline trên Apple Silicon (`mlx-vlm` với `Qwen2.5-VL-7B-Instruct` 4-bit) hoặc Windows NVIDIA GPU (`llama.cpp`).
    - *Cloud BYOK:* Hỗ trợ Claude 3.5 Sonnet / Azure OpenAI cho máy tính văn phòng mỏng nhẹ.
- **Giai đoạn 2: Deep Excel Integration (Office.js Add-in)**
  - Nhúng trực tiếp trong Microsoft Excel. Kéo thả PDF bóc tách bảng số liệu, sinh công thức `=SUM(...)`, và gắn link Audit Trail vào ô tính.
  - Phiên bản On-Premise LAN Container ("Team Box") cho khách hàng ngân hàng / kiểm toán.

---

## 3. Cấu Trúc Monorepo

```
FinTrace/
├── apps/
│   └── desktop/                  # Tauri v2 Desktop App (React 19 + Tailwind CSS)
├── packages/
│   ├── core-engine/              # Python Visual RAG Engine (PyMuPDF, ColPali, LanceDB, VLM)
│   └── office-addin/             # Office.js Web Add-in cho Microsoft Excel
├── benchmarks/                   # Bộ dữ liệu 10 BCTC thực tế & kịch bản benchmark
├── docs/
│   ├── PRD_ARCH_FINSIGHT.md      # Bản đặc tả kỹ thuật & PRD đầy đủ
│   ├── TEAM_STRUCTURE_AND_ROSTER.md # Cơ cấu tổ chức 5 vai trò Subagents
│   ├── SPRINT_PLAN.md            # Kế hoạch 4 Sprints chi tiết kèm DoD
│   ├── lesson_learn.md           # Sổ tay bài học kinh nghiệm đồng bộ 2 chiều
│   └── adr/                      # Architectural Decision Records (ADR-001 đến 004)
├── .agents/mcp_config.json       # Cấu hình Lore MCP cho Antigravity CLI
├── lore.ontology.yml             # Bộ quy chuẩn ontology ký ức của Lore
└── AGENTS.md                     # Quy chế làm việc chuẩn 529 Studio
```

---

## 4. Cơ Cấu Đội Ngũ Subagents (Software Engineering Squad)

Dự án được phân chia theo 5 vai trò chuyên môn hóa:
1. **`lead-architect` (Tech Lead & Architect):** Kiến trúc tổng thể, IPC Rust/Tauri, Lore governance, ADR reviews.
2. **`rag-ml-engineer` (Visual RAG & AI Engineer):** PyMuPDF, ColPali, LanceDB, MLX local Qwen2.5-VL, LiteLLM router.
3. **`frontend-engineer` (Frontend Desktop Engineer):** Tauri v2, React 19, 4-File Architecture, Split-View layout, Bounding Box SVG overlay.
4. **`excel-addin-engineer` (Office Excel Specialist):** Office.js Web Add-in, Excel cell injection, formula generation, audit links.
5. **`qa-benchmark-engineer` (QA & Benchmark Specialist):** Bộ dữ liệu BCTC, harness đo Top-1/Top-3 Recall, Evidence-based DoD.

---

## 5. Ký Ức Dùng Chung Lore & Tiêu Chuẩn Kỹ Thuật 529 Studio

- **Lore Persistent Memory:** Mọi subagent đều dùng chung bộ nhớ Lore (`lore search`, `lore write`, `lore verify`).
- **529 Studio Standards:** Tuân thủ 6 kỹ năng cốt lõi:
  - `resilient-networking-and-waf`
  - `env-and-auth-ops-debugging`
  - `module-boundary-and-concurrency`
  - `frontend-4file-and-resilient-ui`
  - `docker-runtime-patching-and-secrets`
  - `evidence-based-dod-and-llm-guardrails`
- **Đồng bộ 2 chiều:** Các bài học thực chiến mới trong `docs/lesson_learn.md` được tự động thu hoạch về kho tri thức trung tâm `529-engineering-skills` qua lệnh:
  ```bash
  npm run harvest:lessons
  ```

---

## 6. Khởi Động Nhanh (Quick Start)

### Yêu cầu tiên quyết:
- Node.js >= 22
- Python >= 3.10
- Rust & Cargo (dành cho Tauri build)

### Chạy Core AI Daemon:
```bash
pip install -r packages/core-engine/requirements.txt
npm run dev:engine
# Daemon lắng nghe tại: http://127.0.0.1:8765
```

### Chạy Desktop App:
```bash
cd apps/desktop
npm install
npm run dev
```

### Chạy Benchmark Recall:
```bash
npm run bench:recall
```
