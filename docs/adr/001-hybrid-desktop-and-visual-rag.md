# ADR-001: Lựa Chọn Kiến Trúc Hybrid Desktop (Tauri v2) & Visual RAG Native (ColPali)

- **Trạng thái:** Approved
- **Ngày quyết định:** 16/11/2026
- **Tác giả:** FinSight Architecture Team (lead-architect, rag-ml-engineer)
- **Tham chiếu:** Outline PRD §2, §4

## Bối Cảnh (Context)
Dự án FinSight yêu cầu xây dựng trợ lý phân tích Báo cáo tài chính (BCTC) chuyên nghiệp cho các nhà phân tích, kiểm toán viên và kế toán. BCTC có đặc thù chứa nhiều biểu đồ phức tạp (cơ cấu doanh thu, waterfall chart, margin trends) và các bảng cân đối kế toán nhiều cột với chú thích chân trang.
Đồng thời, đối tượng người dùng tài chính làm việc chủ yếu trên máy tính desktop (Windows và macOS), đòi hỏi ứng dụng nhẹ, khởi động nhanh, bảo mật cao và tiêu tốn ít bộ nhớ.

## Quyết Định (Decisions)

### 1. Chọn Visual RAG (ColPali) thay vì RAG Văn Bản Truyền Thống
- **Quyết định:** Không sử dụng text parsing (pypdf, pdfplumber) và text embedding truyền thống. Thay vào đó, coi mỗi trang tài liệu là ảnh độ phân giải cao 150-200 DPI và lập chỉ mục bằng **ColPali** (`byaldi` / multi-vector patch embeddings).
- **Lý do:**
  1. Tránh được 3 tử huyệt: Mù biểu đồ, vỡ cấu trúc bảng và mất liên kết chú thích chân trang.
  2. Cơ chế Late Interaction (MaxSim) cho phép tìm kiếm chính xác vùng ảnh có biểu đồ/bảng mà không cần qua bước OCR trung gian dễ sinh lỗi.
  3. Cho phép trích xuất tọa độ Bounding Box trực tiếp từ Vision-Language Model để làm bằng chứng kiểm toán.

### 2. Chọn Tauri v2 (Rust + React 19) thay vì Electron
- **Quyết định:** Xây dựng ứng dụng Desktop bằng **Tauri v2**.
- **Lý do:**
  1. Dung lượng bộ cài siêu nhẹ (< 20MB so với > 120MB của Electron).
  2. Mức độ ngốn RAM thấp hơn 5-10 lần so với Electron nhờ sử dụng Webview native của hệ điều hành (WebView2 trên Windows, WebKit trên macOS).
  3. Lớp lõi Rust cung cấp độ an toàn bộ nhớ tuyệt đối và hiệu năng cao khi giao tiếp với các engine native và sidecars.

## Hệ Quả (Consequences)
- **Tích cực:** Ứng dụng phản hồi cực nhanh, chiếm ít tài nguyên máy, phân tích biểu đồ chính xác, hiển thị bằng chứng thị giác trực quan.
- **Thách thức:** Cần quản lý tiến trình backend AI (Python sidecar hoặc local daemon) một cách mượt mà và an toàn trên cả macOS và Windows.
