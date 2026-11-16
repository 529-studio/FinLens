# FinSight — Lessons Learned & Engineering Post-Mortems

> Sổ tay ghi chép các cạm bẫy kỹ thuật, bài học thực chiến và quyết định kiến trúc được kiểm chứng trong dự án **FinSight**.  
> Được đồng bộ hai chiều với kho tri thức trung tâm `529-engineering-skills` qua script:  
> `bash ~/repos/529-engineering-skills/scripts/harvest-lessons.sh`

---

## Lesson 1: Tử huyệt của OCR/Text-chunking trong BCTC & Giải pháp Visual RAG Native
- **Bối cảnh:** Khi cố gắng phân tích Báo cáo tài chính (BCTC) bằng pipeline RAG truyền thống (LangChain, LlamaIndex + pdfplumber / pypdf + text embeddings), tỷ lệ trả lời sai hoặc "không tìm thấy dữ liệu" trên các câu hỏi về biểu đồ cơ cấu doanh thu và bảng cân đối kế toán vượt quá 60%.
- **Nguyên nhân gốc rễ:** 
  1. Biểu đồ tài chính (cột, tròn, waterfall) bị OCR bỏ qua hoặc biến thành chuỗi text rời rạc mất hoàn toàn nhãn trục và chú giải màu sắc.
  2. Bảng cân đối đa tầng bị thuật toán chunking cắt đôi, phá hủy mối quan hệ dòng - cột và ngữ cảnh mã tài khoản.
  3. Thuyết minh chân trang (Footnotes) chứa thông tin rủi ro nợ tiềm tàng bị tách rời khỏi số liệu chính.
- **Giải pháp chuẩn hóa:** 
  - Chuyển hoàn toàn sang kiến trúc **Visual RAG (ColPali + VLM)**. Coi mỗi trang tài liệu là ảnh PNG 150-200 DPI nguyên bản.
  - Sử dụng cơ chế Late Interaction (MaxSim) của ColPali trên các visual patches để tìm kiếm trực tiếp trên ảnh.
  - Yêu cầu VLM trả về câu trả lời kèm Bounding Box `[ymin, xmin, ymax, xmax]` để tạo bằng chứng kiểm toán (Visual Grounding).

---

## Lesson 2: Chiến lược Dual-Engine suy luận VLM cho hệ thống B2B Tài chính
- **Bối cảnh:** Giới tài chính và kế toán doanh nghiệp sử dụng máy tính Windows văn phòng chiếm hơn 85%, đa phần là laptop mỏng nhẹ không có card đồ họa rời (chỉ có Intel Iris Xe hoặc Core Ultra iGPU), trong khi các nhà nghiên cứu / lead dev dùng MacBook Apple Silicon (M2/M3/M4).
- **Nguyên nhân gốc rễ:** Nếu ép buộc người dùng chạy VLM 7B local trên mọi máy, ứng dụng desktop sẽ bị crash bộ nhớ hoặc phản hồi mất hàng chục phút, phá hỏng trải nghiệm người dùng. Nếu chỉ hỗ trợ Cloud API thì vi phạm chính sách bảo mật dữ liệu nhạy cảm của các quỹ đầu tư / ngân hàng.
- **Giải pháp chuẩn hóa:**
  - Thiết kế kiến trúc **Dual-Engine Hybrid**:
    - **Mode Local:** Tự động kích hoạt khi phát hiện Apple Silicon (qua engine `mlx-vlm` với `Qwen2.5-VL-7B-Instruct` 4-bit) hoặc NVIDIA GPU (qua `llama.cpp` CUDA).
    - **Mode Cloud / BYOK (Bring Your Own Key):** Kích hoạt trên laptop văn phòng thông thường, định tuyến qua `LiteLLM` đến Claude 3.5 Sonnet hoặc Azure OpenAI enterprise endpoint của chính doanh nghiệp.

---

## Lesson 3: Đảm bảo tính toàn vẹn số liệu tài chính với Bounding Box Coordinate System
- **Bối cảnh:** Khi trích xuất số liệu từ BCTC để phục vụ quyết định đầu tư, dung sai cho ảo giác (hallucination) là 0%. Nếu AI trích xuất sai một chữ số trong báo cáo kiểm toán, hậu quả pháp lý và tài chính là khôn lường.
- **Giải pháp chuẩn hóa:**
  - Chuẩn hóa hệ quy chiếu tọa độ Bounding Box về thang đo chuẩn `[0, 1000]` cho `[ymin, xmin, ymax, xmax]`.
  - Trên giao diện Split-View Desktop, mỗi con số trích xuất đều được gắn liên kết hai chiều với canvas SVG overlay của PDF Viewer.
  - Người dùng nhấp vào số liệu -> PDF Viewer tự động scroll và flash highlight vùng dữ liệu gốc, người dùng tự mắt thấy tai nghe bằng chứng (Evidence Before Assertions).
