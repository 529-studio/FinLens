# FinSight — Kế Hoạch 4 Sprints Chi Tiết (Sprint Backlog & Deliverables)

> **Mô hình triển khai:** 2-Phase Strategy chia thành 4 Sprints 2 tuần.  
> **Nguyên tắc nghiệm thu:** Evidence-Based DoD (Không chấp nhận khẳng định nếu thiếu terminal log / test report / UI capture).

---

## Sprint 1: Nghiên Cứu Lõi & Thử Nghiệm Visual RAG (PoC & Benchmarking)
- **Mục tiêu chính:** Chứng minh tính khả thi của Visual RAG (ColPali) trên Báo cáo tài chính thực tế và thiết lập chuẩn giao tiếp Dual-Engine.
- **Thời lượng dự kiến:** 2 tuần
- **Chủ trì kỹ thuật:** `rag-ml-engineer` & `qa-benchmark-engineer`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S1-01** | `lead-architect` | Khởi tạo cấu trúc Monorepo, thiết lập ADR-001 đến ADR-004, cấu hình Lore memory. | Cấu trúc monorepo, files ADR hoàn chỉnh, Lore ontology active. |
| **S1-02** | `qa-benchmark-engineer` | Thu thập 10 BCTC kiểm toán thực tế (Vinamilk, Hòa Phát, Vietcombank, Apple 10-K...) có biểu đồ phức tạp và đa dạng bảng số liệu. | Thư mục `benchmarks/data/` kèm manifest JSON định nghĩa Ground Truth. |
| **S1-03** | `rag-ml-engineer` | Viết module render PDF sang ảnh PNG (150-200 DPI) bằng PyMuPDF (`fitz`). | `packages/core-engine/src/renderer.py` có test case render trang sắc nét. |
| **S1-04** | `rag-ml-engineer` | Tích hợp thư viện ColPali (`byaldi`) và vector database cục bộ LanceDB. Xây dựng index cho 10 file BCTC. | `packages/core-engine/src/retriever.py` có khả năng sinh multi-vector embeddings. |
| **S1-05** | `qa-benchmark-engineer` | Viết script benchmark tự động: Đặt 30 câu hỏi về biểu đồ và đo tỷ lệ tìm đúng trang chứa biểu đồ (Top-1 / Top-3 Recall). | `benchmarks/eval_retrieval.py` xuất ra bảng so sánh giữa ColPali vs Text Chunking. |
| **S1-06** | `rag-ml-engineer` | Đánh giá trích xuất thị giác: Chạy `Qwen2.5-VL-7B-Instruct` qua `mlx-vlm` (Local) so sánh với `Claude 3.5 Sonnet` (Cloud). | `benchmarks/eval_vlm_extraction.py` đo độ lệch số liệu và trích xuất Bounding Box. |
| **S1-07** | `frontend-engineer` | Khởi tạo bộ khung Tauri v2 Desktop và cấu hình Vite + React 19 + Tailwind CSS. | Ứng dụng Desktop khởi động được, có cửa sổ trống chuẩn bị cho Sprint 2. |

### Definition of Done (DoD) Sprint 1:
- [ ] ColPali đạt Top-1 Recall >= 85% trên tập 30 câu hỏi biểu đồ BCTC (vượt trội hoàn toàn so với Text RAG < 40%).
- [ ] VLM trích xuất được Bounding Box định dạng chuẩn `[ymin, xmin, ymax, xmax]` (thang đo 0-1000).
- [ ] Báo cáo kết quả lưu tại `benchmarks/results/sprint1_report.md` và đồng bộ bài học vào `docs/lesson_learn.md`.

---

## Sprint 2: Phát Triển Giao Diện Desktop (Tauri v2 MVP)
- **Mục tiêu chính:** Hoàn thiện giao diện Split-View Desktop với khả năng tương tác tài liệu trực quan và tính năng Click-to-Source.
- **Thời lượng dự kiến:** 2 tuần
- **Chủ trì kỹ thuật:** `frontend-engineer` & `lead-architect`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S2-01** | `frontend-engineer` | Triển khai layout Split-View (Chia đôi màn hình linh hoạt với thanh kéo resize). | `apps/desktop/src/components/layout/SplitView.tsx` |
| **S2-02** | `frontend-engineer` | Tích hợp PDF Viewer chất lượng cao (PDF.js) ở panel trái, hỗ trợ phóng to/thu nhỏ, chuyển trang mượt mà. | `apps/desktop/src/components/pdf/PdfViewer.tsx` |
| **S2-03** | `frontend-engineer` | Xây dựng Canvas/SVG Overlay vẽ Bounding Box màu đỏ trên trang PDF dựa vào tọa độ `[ymin, xmin, ymax, xmax]`. | `apps/desktop/src/components/pdf/BoundingBoxOverlay.tsx` |
| **S2-04** | `frontend-engineer` | Xây dựng khung Chat tài chính ở panel phải: Input câu hỏi, streaming response, bảng số liệu markdown. | `apps/desktop/src/components/chat/ChatPanel.tsx` |
| **S2-05** | `frontend-engineer` | Triển khai tính năng "Click-to-Source": Nhấp vào số liệu ở câu trả lời, PDF viewer tự cuộn đến đúng trang và chớp sáng khung viền đỏ. | Hook `useAuditTrail` và hiệu ứng CSS flash animation. |
| **S2-06** | `lead-architect` | Xây dựng Rust Tauri Command IPC để gọi tới Local AI Engine và truyền dữ liệu streaming an toàn. | `apps/desktop/src-tauri/src/commands.rs` |
| **S2-07** | `qa-benchmark-engineer` | Kiểm thử giao diện và độ mượt (>= 60 FPS khi cuộn PDF), kiểm thử tương thích hiển thị trên màn hình Retina / High-DPI. | Báo cáo kiểm thử UI và snapshot kiểm chứng. |

### Definition of Done (DoD) Sprint 2:
- [ ] Giao diện Split-View hoạt động mượt mà, kéo thả PDF vào ứng dụng là hiển thị ngay lập tức.
- [ ] Nhấp vào câu trả lời bất kỳ, ứng dụng nhảy đúng trang PDF và highlight chính xác vùng biểu đồ/bảng số liệu.
- [ ] Tuân thủ nghiêm ngặt 3 UI States (Skeleton, Error with retry, Empty state) theo chuẩn `frontend-4file-and-resilient-ui`.

---

## Sprint 3: Hoàn Thiện Dual-Engine & Đóng Gói Ứng Dụng
- **Mục tiêu chính:** Tối ưu hóa chuyển đổi linh hoạt giữa Local MLX và Cloud BYOK, đóng gói bộ cài đặt độc lập.
- **Thời lượng dự kiến:** 2 tuần
- **Chủ trì kỹ thuật:** `rag-ml-engineer` & `lead-architect`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S3-01** | `rag-ml-engineer` | Hoàn thiện Local Engine trên macOS Apple Silicon sử dụng `mlx-vlm` với mô hình 4-bit `Qwen2.5-VL-7B-Instruct`. | Engine chạy offline hoàn toàn, thời gian sinh câu trả lời < 5s trên M-series. |
| **S3-02** | `rag-ml-engineer` | Tích hợp Cloud BYOK Router qua `LiteLLM`: hỗ trợ cắm API Key của Claude 3.5 Sonnet và endpoint Azure OpenAI bảo mật. | `packages/core-engine/src/cloud_router.py` |
| **S3-03** | `frontend-engineer` | Xây dựng Settings Modal cho phép người dùng: Chuyển đổi Mode (Local/Cloud), nhập API Key, chỉnh DPI render, chọn Vector Store path. | `apps/desktop/src/components/settings/SettingsDialog.tsx` |
| **S3-04** | `lead-architect` | Bảo mật Zero-Leak: Mã hóa API Key trong hệ điều hành (Keychain trên macOS, Credential Manager trên Windows) thay vì lưu plain text. | Module lưu trữ an toàn trong Rust core. |
| **S3-05** | `lead-architect` | Thiết lập GitHub Actions CI/CD workflow tự động đóng gói ứng dụng: `.dmg` cho macOS (Universal) và `.msi/.exe` cho Windows. | `.github/workflows/release-desktop.yml` |
| **S3-06** | `qa-benchmark-engineer` | Đo đạc tài nguyên: Kiểm tra mức tiêu thụ RAM (< 500MB cho Desktop App, < 6GB cho MLX Engine) và kiểm tra tính ổn định dài hạn. | Báo cáo hiệu năng hệ thống Sprint 3. |

### Definition of Done (DoD) Sprint 3:
- [ ] Người dùng không có GPU vẫn sử dụng trơn tru chế độ Cloud BYOK; người dùng Mac Apple Silicon có thể tắt hẳn Wi-Fi và chạy 100% offline.
- [ ] File cài đặt `.dmg` và `.exe` được build thành công từ pipeline tự động.
- [ ] Không có bất kỳ API key nào bị rò rỉ vào mã nguồn hay git history (Zero-Leak verified).

---

## Sprint 4: Khởi Động Module Excel Add-in & Báo Cáo Doanh Nghiệp
- **Mục tiêu chính:** Khởi tạo Office.js Add-in, kết nối nhúng trong Excel và chuẩn bị tài liệu triển khai On-Premise cho doanh nghiệp.
- **Thời lượng dự kiến:** 2 tuần
- **Chủ trì kỹ thuật:** `excel-addin-engineer` & `lead-architect`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S4-01** | `excel-addin-engineer` | Khởi tạo dự án Office.js Web Add-in (`manifest.xml`, Fluent UI, React). | `packages/office-addin/` hoạt động được trong môi trường Excel Dev. |
| **S4-02** | `excel-addin-engineer` | Xây dựng giao diện Sidebar Excel: Cho phép kéo thả BCTC PDF trực tiếp vào khung thanh bên. | Sidebar Component có trạng thái đồng bộ với FinSight Core Daemon. |
| **S4-03** | `excel-addin-engineer` | Tính năng "1-Click Export to Table": Bóc tách cấu trúc bảng từ PDF và điền thẳng số liệu vào vùng cell đang chọn trong bảng tính. | Hàm `exportTableToRange(cellsData)` sử dụng `Excel.run`. |
| **S4-04** | `excel-addin-engineer` | Sinh công thức tự động: Khi trích xuất bảng doanh thu/chi phí, AI tự động thêm dòng tổng cộng với công thức `=SUM(...)` chuẩn của Excel. | Thuật toán sinh công thức tài chính. |
| **S4-05** | `excel-addin-engineer` | Thiết lập Audit Trail Link trên Cell: Nhấp vào ô số liệu, mở ngay ảnh chụp gốc chứng minh xuất xứ con số. | Tích hợp hyperlink / comment audit trail vào ô tính. |
| **S4-06** | `lead-architect` | Đóng gói Backend thành Docker Compose On-Premise ("Team Box") cho khách hàng doanh nghiệp / ngân hàng muốn đặt server trong mạng LAN. | `docker-compose.enterprise.yml` và tài liệu triển khai bảo mật. |
| **S4-07** | `qa-benchmark-engineer` | Kiểm thử tích hợp E2E: Quy trình trích xuất PDF từ Excel -> Bơm số liệu vào Sheet -> Kiểm toán ngược lại nguồn gốc. | Biên bản nghiệm thu toàn diện sản phẩm FinSight. |

### Definition of Done (DoD) Sprint 4:
- [ ] Thao tác 1-Click đưa số liệu từ biểu đồ/bảng BCTC vào bảng tính Excel chính xác 100% dòng/cột.
- [ ] Kiểm toán viên click vào ô tính có thể xem ngay hình ảnh chứng minh gốc.
- [ ] Toàn bộ bài học kinh nghiệm và kiến trúc được thu hoạch đồng bộ vào Lore và `529-engineering-skills`.

---

## Sprint 6: Triển Khai Trung Tâm, Visual RAG Nâng Cao & Tối Ưu Hiệu Năng
- **Mục tiêu chính:** Hoàn thiện hạ tầng triển khai sản phẩm, cải thiện khả năng RAG trên tài liệu lớn và tối ưu hóa xử lý.
- **Thời lượng dự kiến:** 2 tuần
- **Chủ trì kỹ thuật:** `lead-architect` & `rag-ml-engineer`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S6-01** | `lead-architect` | Triển khai Centralized Deployment: Publish `manifest.xml` và cấu hình server production. | Manifest sản phẩm hợp lệ, CI/CD pipeline cho production. |
| **S6-02** | `rag-ml-engineer` | Advanced Visual RAG: Tích hợp multi-page evidence linkage. | Module RAG kết nối dữ liệu chéo giữa các trang. |
| **S6-03** | `rag-ml-engineer` | Tối ưu hóa hiệu năng: Tăng tốc xử lý parsing các báo cáo tài chính quy mô lớn. | Benchmark hiệu năng mới, xử lý nhanh hơn 30%. |

### Definition of Done (DoD) Sprint 6:
- [ ] Manifest được publish thành công và hoạt động trên môi trường production.
- [ ] Visual RAG hỗ trợ trích dẫn liên trang (multi-page) chính xác.
- [ ] Hiệu năng xử lý báo cáo tài chính lớn được cải thiện rõ rệt theo benchmark.
- [ ] Toàn bộ kết quả kiểm thử được lưu trữ và bài học được ghi lại vào Lore.

---

## Sprint 7: Ingestion Office.js, Comparative Visual RAG & Hardened Native Desktop (Completed)
- **Mục tiêu chính:** Hoàn thiện 1-click Ingestion trên Excel Taskpane, RAG đối chiếu đa niên độ BCTC, native packaging Tauri v2 và xuất bảng tự động.
- **Thời lượng:** Hoàn thành (2026-11-21)
- **Trạng thái:** 100% hoàn thành, 4 PRs (#42, #46, #47, #48) đã merge vào `dev`.

---

## Sprint 8: Production Readiness, Golden Dataset Benchmarks, Signing/Notarization & Streaming Inference
- **Mục tiêu chính:** Nâng cấp FinSight đạt chuẩn phát hành thương mại (GA) với bộ benchmark 100+ BCTC thực tế, pipeline ký số và notarization cho macOS/Windows, suy luận streaming qua WebSocket, và bóc tách thuyết minh BCTC liên kết bảng tính.
- **Thời lượng dự kiến:** 2 tuần (Sprint 8)
- **Chủ trì kỹ thuật:** `lead-architect`, `qa-benchmark-engineer`, `rag-ml-engineer`, `excel-addin-engineer`, `frontend-engineer`

### Task Breakdown & Phân Công:

| Mã Task | Phân công | Mô tả công việc | Deliverables / Đầu ra |
|:--------|:----------|:----------------|:----------------------|
| **S8-01** | `qa-benchmark-engineer`, `rag-ml-engineer` | Golden Dataset Comprehensive Evaluation: Mở rộng benchmark 100+ BCTC kiểm toán thực tế (VNM, HPG, VCB, FPT, VIC, MSN, MWG, VHM...), đo Top-1/Top-3 recall, chart blindness rate và bounding box IoU. | `benchmarks/data/manifest_golden_100.json`, `benchmarks/eval_golden_suite.py`, báo cáo định lượng `sprint8_golden_benchmark.json`. |
| **S8-02** | `lead-architect`, `frontend-engineer` | Production Installer Signing, Hardened Runtime & Notarization Pipeline: Thiết lập Apple Developer ID code signing, entitlements.plist hardened runtime, Apple `notarytool` stapling, và pipeline cho macOS `.dmg`/`.app`. | `apps/desktop/src-tauri/entitlements.plist`, `scripts/notarize-macos.sh`, cấu hình `tauri.conf.json` chuẩn sản xuất. |
| **S8-03** | `rag-ml-engineer`, `frontend-engineer`, `excel-addin-engineer` | Real-Time WebSocket Streaming Inference: Triển khai endpoint `/ws/query/stream`, stream từng token từ MLX Engine & Cloud Router đến Desktop Chat và Excel Taskpane theo thời gian thực. | Endpoint `/ws/query/stream`, hook `useStreamingQuery.ts`, cập nhật progressive rendering cho ChatPanel và Excel Sidebar. |
| **S8-04** | `rag-ml-engineer`, `excel-addin-engineer` | Consolidated BCTC Footnote Disambiguation & Formula Extraction: Tối ưu prompt VLM nhận diện và bóc tách Thuyết minh BCTC, tự động liên kết các khoản mục bảng cân đối kế toán với thuyết minh chi tiết và sinh link/comment trong Excel. | Endpoint `/api/v1/query/footnotes`, hàm `insertFinancialTableToSheet` nâng cao hỗ trợ cột Thuyết minh và comment trích dẫn. |
| **S8-05** | `lead-architect`, `qa-benchmark-engineer` | Independent Wave Audit, Security Traversal Probing & Sprint Close Ritual: Kiểm thử bảo mật path traversal trên tất cả endpoint mới, audit UI/UX độc lập, nghiệm thu 100% test matrix và lập biên bản bàn giao Sprint 8. | `docs/reports/sprint8_report.md`, `docs/HANDOFF-s8.md`, `npm run harvest:lessons`. |

### Definition of Done (DoD) Sprint 8:
- [ ] Golden dataset benchmark đạt Top-1 Recall $\ge 85\%$, Top-3 Recall $\ge 95\%$, Chart Blindness 0.0%, và Bounding Box IoU $\ge 0.80$ trên 100+ BCTC thực tế.
- [ ] macOS `.dmg` và `.app` được cấu hình hardened runtime và kịch bản notarization vượt qua kiểm tra của Apple Gatekeeper.
- [ ] WebSocket streaming trả về token mượt mà không làm đơ giao diện; hiển thị trọn vẹn 3 UI States.
- [ ] Thuyết minh BCTC được bóc tách chính xác và đính kèm vào bảng tính Excel mà không gây lỗi tham chiếu.
- [ ] 100% test suites (Python, Vitest, Rust Cargo) vượt qua và audit subagent xác nhận `APPROVED 🟢`.


