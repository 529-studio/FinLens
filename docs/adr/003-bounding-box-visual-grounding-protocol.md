# ADR-003: Giao Thức Chuẩn Hóa Bounding Box & Bằng Chứng Thị Giác (Audit Trail Protocol)

- **Trạng thái:** Approved
- **Ngày quyết định:** 16/11/2026
- **Tác giả:** FinSight Architecture Team (rag-ml-engineer, frontend-engineer)
- **Tham chiếu:** Outline PRD §2.2, §4.1

## Bối Cảnh (Context)
Trong phân tích tài chính, mọi phát biểu và số liệu trích xuất từ BCTC đều phải có bằng chứng chứng minh xuất xứ (Provenance / Auditability). Nếu không có bằng chứng rõ ràng, người dùng tài chính sẽ không dám tin tưởng vào kết quả của AI.

## Quyết Định (Decisions)

### 1. Chuẩn Hóa Hệ Tọa Độ Bounding Box
- Toàn bộ các mô hình VLM (Local Qwen2.5-VL hoặc Cloud Claude/GPT-4o) đều được prompt để trả về tọa độ hộp giới hạn theo quy chuẩn 4 điểm chuẩn hóa trên thang đo `0 - 1000`:
  ```json
  {
    "ymin": 120,
    "xmin": 450,
    "ymax": 380,
    "xmax": 920
  }
  ```
- **Lý do chọn thang đo 0-1000:**
  * Độc lập hoàn toàn với DPI render (150 DPI hay 200 DPI) và độ phân giải màn hình hiển thị của người dùng.
  * Phía Frontend (React + PDF Viewer) chỉ cần tính tỷ lệ:
    `top = (ymin / 1000) * renderedHeight`
    `left = (xmin / 1000) * renderedWidth`
    `height = ((ymax - ymin) / 1000) * renderedHeight`
    `width = ((xmax - xmin) / 1000) * renderedWidth`

### 2. Giao Thức Click-to-Source (Audit Trail Protocol)
- Mỗi câu trả lời hoặc số liệu trích xuất trả về từ Engine bao gồm payload:
  ```typescript
  export interface GroundedEvidence {
    pageNumber: number;
    boundingBox: [number, number, number, number]; // [ymin, xmin, ymax, xmax]
    label: string;
    extractedValue?: string | number;
    confidence: number;
  }
  ```
- Khi người dùng nhấp chuột vào số liệu trên Chat Panel hoặc ô tính Excel:
  1. Frontend phát tín hiệu `ACTIVATE_EVIDENCE({ pageNumber, boundingBox })`.
  2. PDF Viewer tự động cuộn (smooth scroll) đến trang tương ứng.
  3. Canvas / SVG Overlay kích hoạt animation nhấp nháy (flash pulse viền đỏ `#EF4444`, độ dày 2.5px) trong 2.5 giây để thu hút ánh mắt người dùng vào đúng vị trí nguồn.

## Hệ Quả (Consequences)
- Triệt tiêu hoàn toàn nỗi sợ ảo giác (hallucination) của giới tài chính.
- Tạo nền tảng đồng nhất cho cả Desktop App (Phase 1) và Excel Add-in (Phase 2).
