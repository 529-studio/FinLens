# ADR-002: Kiến Trúc Suy Luận Dual-Mode (Local MLX / CUDA vs Cloud BYOK Router)

- **Trạng thái:** Approved
- **Ngày quyết định:** 16/11/2026
- **Tác giả:** FinSight Architecture Team (rag-ml-engineer, lead-architect)
- **Tham chiếu:** Outline PRD §3, §5

## Bối Cảnh (Context)
Cơ cấu phần cứng của người dùng tài chính rất phân hóa:
1. Đa số nhân viên văn phòng, kế toán sử dụng laptop Windows mỏng nhẹ không có card đồ họa rời (VRAM = 0).
2. Các chuyên gia tài chính, quỹ đầu tư, kỹ sư dùng MacBook Apple Silicon (M2/M3/M4 với Unified Memory 16GB - 36GB+) hoặc máy trạm có card NVIDIA RTX.
3. Yêu cầu bảo mật: Một số doanh nghiệp cấm dữ liệu BCTC nội bộ bị đẩy lên cloud công cộng, nhưng một số khác sẵn sàng dùng endpoint Azure OpenAI doanh nghiệp riêng.

## Quyết Định (Decisions)

### Thiết kế Bộ Định Tuyến Dual-Mode Inference
- **Chế độ 1: Local Engine (Offline & Private 100%)**
  * **Trên macOS:** Sử dụng `mlx-vlm` chạy mô hình `Qwen2.5-VL-7B-Instruct` lượng tử hóa 4-bit. Tận dụng tối đa bộ nhớ hợp nhất (Unified Memory) của Apple Silicon M-series để suy luận với tốc độ cao (< 5 giây/câu hỏi).
  * **Trên Windows có GPU:** Sử dụng backend `llama.cpp` qua Vulkan hoặc CUDA.
  * Chi phí token = 0, hoạt động hoàn toàn không cần Internet.
- **Chế độ 2: Cloud BYOK Engine (Bring Your Own Key)**
  * Dành cho máy tính văn phòng cấu hình bình thường hoặc người dùng muốn độ chính xác phân tích tối đa từ các mô hình biên (frontier models).
  * Sử dụng thư viện định tuyến `LiteLLM` hỗ trợ cắm API Key của:
    1. Anthropic Claude 3.5 Sonnet (Đọc biểu đồ và bảng cực kỳ xuất sắc).
    2. Azure OpenAI GPT-4o (Endpoint riêng đạt chuẩn bảo mật doanh nghiệp).
  * Ứng dụng Desktop đóng vai trò là Client giao diện và bộ render hình ảnh, toàn bộ việc suy luận VLM được đẩy lên Cloud an toàn qua HTTPS.

## Hệ Quả (Consequences)
- Người dùng ở bất kỳ cấu hình máy nào cũng có trải nghiệm tối ưu.
- Đảm bảo tuân thủ tiêu chuẩn Zero-Leak: API Keys của người dùng được mã hóa qua Secure Storage (OS Keychain / Credential Manager), không bao giờ ghi ra file log hay commit vào git.
