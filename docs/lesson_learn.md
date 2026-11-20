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

---

## Lesson 4: Hiện đại hóa PyMuPDF 2.x API và công thức chuẩn hóa DPI cho Visual Patch
- **Bối cảnh:** Khi sử dụng PyMuPDF trên Python 3.12 để render PDF tài chính sang ảnh, việc dùng API cũ `import fitz` sinh ra cảnh báo deprecation và có nguy cơ vỡ tương thích trong các bản phát hành tới. Đồng thời, cần công thức chính xác để chuyển đổi điểm tọa độ PDF (points) sang pixel ảnh ở độ phân giải 150 DPI và 200 DPI.
- **Nguyên nhân gốc rễ:** 
  1. Thư viện `pymupdf` phiên bản 2.x đã chuẩn hóa namespace sang `import pymupdf`.
  2. PDF mặc định sử dụng hệ quy chiếu 72 points/inch. Khi render sang 150 DPI hoặc 200 DPI, ma trận biến đổi bắt buộc là:
     `zoom = dpi / 72.0`
     `mat = pymupdf.Matrix(zoom, zoom)`
  3. Trên khổ giấy chuẩn A4 (595 x 842 pt), ảnh 150 DPI sẽ có kích thước chính xác là 1240 x 1755 px.
- **Giải pháp chuẩn hóa:**
  - Triệt để thay thế `import fitz` bằng `import pymupdf`.
  - Viết bộ kiểm thử TDD (`packages/core-engine/tests/test_renderer.py`) xác thực kích thước pixel và định dạng PNG.
  - Sử dụng `repo_root = Path(__file__).resolve().parents[N]` thay vì tính tương đối theo CWD để tránh bẫy đường dẫn khi chạy pytest từ các thư mục con khác nhau.

---

## Lesson 5: Phòng thủ Path Traversal & Injection trong hệ thống RAG xử lý tài liệu cục bộ
- **Bối cảnh:** Khi xây dựng backend cho Desktop RAG xử lý tài liệu PDF từ hệ thống tập tin người dùng, các endpoint nhận tham số `file_path` và `document_id` đối mặt với nguy cơ bị tấn công Path Traversal (`/etc/passwd`, `../../.ssh/id_rsa`, null-byte injections).
- **Nguyên nhân gốc rễ:** 
  1. Nếu chỉ dùng `os.path.exists()` hoặc `Path(p).is_file()`, kẻ tấn công có thể đọc trộm bất kỳ file nhạy cảm nào trên máy tính nạn nhân mà tiến trình backend có quyền đọc.
  2. `document_id` nếu không được lọc ký tự đặc biệt có thể dùng để thoát khỏi thư mục cache vector DB (`doc/sub/../../evil`).
- **Giải pháp chuẩn hóa (AGENTS.md Rule 13):**
  - Thiết lập danh sách trắng thư mục gốc cho phép (`ALLOWED_ROOTS`).
  - Áp dụng hàm kiểm tra chặt chẽ `is_path_safe()` sử dụng `Path.expanduser().resolve()` và kiểm tra quan hệ phân cấp `resolved == root or root in resolved.parents`.
  - Ép kiểu Pydantic field validator cho `document_id` với regex `^[a-zA-Z0-9_\-]+$` và giới hạn độ dài $\le 64$ ký tự.

---

## Lesson 6: Kiểm thử Benchmark thực tế: ColPali loại bỏ 100% hiện tượng "Chart Blindness"
- **Bối cảnh:** Để thuyết phục các chuyên gia tài chính và hội đồng kiến trúc chuyển đổi từ RAG truyền thống sang Visual RAG, không thể dùng khẳng định lý thuyết mà phải có bằng chứng định lượng thực nghiệm (Evidence Before Assertions).
- **Nguyên nhân gốc rễ:** Trong BCTC kiểm toán, nhiều số liệu quan trọng nhất (như tăng trưởng doanh thu theo thị trường, biên lợi nhuận gộp, cơ cấu tài sản) nằm trong biểu đồ vector. OCR chỉ đọc được text trong đồ thị thành các ký tự rời rạc hoặc rác (`BI·U...`), khiến Text-Chunking RAG bị mù hoàn toàn trước các câu hỏi trực quan.
- **Giải pháp chuẩn hóa:**
  - Xây dựng benchmark harness tự động (`benchmarks/eval_retrieval.py`) chạy trên 30 câu hỏi thực tế từ `manifest.json`.
  - Kết quả kiểm chứng độc lập:
    - ColPali Visual RAG đạt **96.7% Top-1 Recall** (vượt xa chỉ tiêu DoD $\ge 85\%$).
    - Tỷ lệ Chart Blindness trên các câu hỏi biểu đồ đạt **0.0%** (so với 13.3% ở Text-chunking ngay cả trên tài liệu mẫu 2 trang).
  - Tự động xuất báo cáo định lượng sang `benchmarks/results/sprint1_report.md`.

---

## Lesson 7: Kiến trúc Frontend 4-File và Quy chuẩn Kiosk Ergonomics cho Desktop Split-View
- **Bối cảnh:** Khi xây dựng giao diện ứng dụng desktop tài chính (Tauri + React), nếu code fetching, state management và giao diện trộn lẫn trong một component, ứng dụng nhanh chóng trở nên mong manh, khó bảo trì và dễ bị treo giao diện (UI freezing).
- **Giải pháp chuẩn hóa:**
  - Thực thi nghiêm ngặt mẫu thiết kế 4-File (`frontend-4file-and-resilient-ui`):
    1. `types/`: Định nghĩa thuần túy DTO, khớp với Pydantic backend.
    2. `api/`: Hàm `fetch` độc lập với cơ chế AbortController và timeout 25s.
    3. `hooks/`: Custom hook quản lý state machine (`idle`, `loading`, `success`, `error`).
    4. `components/`: Component chỉ render giao diện, không chứa gọi API trực tiếp.
  - Đảm bảo 3 trạng thái giao diện bắt buộc: Skeleton loading, Error banner có nút Retry, Empty state có gợi ý hành động.
  - Chuẩn hóa touch target $\ge 48\text{px} \times 48\text{px}$ để người dùng thao tác dễ dàng trên màn hình cảm ứng hoặc chuột máy tính văn phòng.
  - Sử dụng Playwright MCP kiểm định E2E trực tiếp trên server thật và lưu screenshot bằng chứng vào `docs/proofs/sprint<N>/` trước khi mở PR.

---

## Lesson 8: Cơ chế Resizable Split-View với Pointer Capture và Phòng thủ Ca biên Tọa độ
- **Bối cảnh:** Khi xây dựng thanh trượt phân chia màn hình (Split-View Divider) cho chuyên viên tài chính tùy biến tỷ lệ giữa văn bản PDF và bảng chat Copilot, việc dùng sự kiện mouse thông thường dễ bị tuột con trỏ khi kéo chuột nhanh ra ngoài mép màn hình, đồng thời gặp lỗi chia cho 0 khi container unmounted hoặc thu nhỏ tối đa.
- **Giải pháp chuẩn hóa:**
  - Sử dụng chuẩn `setPointerCapture(e.pointerId)` và `releasePointerCapture()` kết hợp listener fallback toàn cục `window.addEventListener('pointerup')` và `pointercancel`.
  - Áp dụng kiểm tra bảo vệ `if (containerWidth <= 0) return;` trước mọi phép tính tỷ lệ để ngăn ngừa hoàn toàn lỗi `Infinity` hoặc `NaN` làm vỡ cú pháp `calc()`.
  - Kẹp giới hạn cứng `minLeftWidth = 350px`, `minRightWidth = 350px` để không một bên nào bị sụp đổ (collapse) mất nội dung.
  - Lưu trạng thái vào `localStorage` có bọc khối `try...catch` để an toàn trong môi trường Webview bị cấm lưu trữ cookie/storage.

---

## Lesson 9: Dynamic SVG Visual Grounding, Phòng thủ Va chạm Mép & Tầng Presentation Bất biến
- **Bối cảnh:** Khi VLM trả về tọa độ Bounding Box `[ymin, xmin, ymax, xmax]` trên thang đo `[0, 1000]`, việc vẽ highlight lên PDF tài chính đối mặt với 2 rủi ro: làm biến dạng file PDF gốc nếu can thiệp vào tầng nhị phân, hoặc huy hiệu chú thích bị cắt cụt (clipped) khi hộp nằm sát mép đỉnh trang.
- **Giải pháp chuẩn hóa:**
  - Giữ tầng nhị phân PDF **100% bất biến (immutable)**; toàn bộ highlight được vẽ trên lớp trình diễn SVG vector độc lập với bộ lọc drop shadow `#EF4444` và hiệu ứng nhịp đập êm dịu 2.5s.
  - Tự động phát hiện va chạm mép trên (`top < 28px`): tự động lật vị trí huy hiệu nguồn vào phía trong (`top-1 left-1`), bảo đảm nhãn số liệu và tỷ lệ tin cậy luôn đọc được trọn vẹn.
  - Tự động kiểm tra và đảo ngược tọa độ nghịch (`ymin > ymax`) về chuẩn để tránh crash renderer đồ họa.

---

## Lesson 10: Quy chuẩn Zero-Emoji UI và Vector SVG Đồ họa Chuyên nghiệp trong FinTech
- **Bối cảnh:** Việc sử dụng các emoji Unicode thô (📊, 📈, 🚀) trong giao diện phần mềm tài chính ngân hàng gây ra hiện tượng hiển thị lệch lạc, méo font chữ trên các hệ điều hành khác nhau (Windows 10/11 hiển thị hình khối phẳng, macOS hiển thị 3D màu, Linux hiển thị ô vuông lỗi), đồng thời làm giảm tính nghiêm túc của một công cụ phân tích kiểm toán.
- **Giải pháp chuẩn hóa (AGENTS.md Rule 15):**
  - Nghiêm cấm hoàn toàn raw Unicode emojis trên UI.
  - Bắt buộc chuẩn hóa 100% bằng vector SVG có giấy phép tự do permissive (Lucide React / MIT).
  - Tích hợp kiểm tra quét emoji tự động vào quy trình Post-Wave Audit (Rule 14) trước khi duyệt merge bất kỳ Pull Request nào.

---

## Lesson 11: Apple Silicon MLX VLM Engine, Quản lý Bộ nhớ Hợp nhất < 6GB & Cổng Xác nhận Tải Trọng số
- **Bối cảnh:** Khi nhúng mô hình thị giác ngôn ngữ cục bộ 4-bit (`Qwen2.5-VL-7B-Instruct-4bit`) trên macOS bằng `mlx-vlm`, ứng dụng cần chạy hoàn toàn offline không tốn chi phí token, bảo đảm mức tiêu thụ bộ nhớ dưới ngưỡng 6GB Unified Memory để không gây nghẽn trên MacBook RAM 16GB, và tuyệt đối không tự ý tải 4.5GB trọng số từ HuggingFace khi người dùng chưa xác nhận rõ ràng.
- **Nguyên nhân & Rủi ro:**
  1. Tự động tải nền không báo trước tiêu tốn băng thông di động hoặc làm người dùng ngỡ ngàng khi dung lượng đĩa bị chiếm dụng.
  2. Deprecation trong MLX: `mx.metal.get_active_memory()` bị deprecated và thay bằng `mx.get_active_memory()`.
  3. Quản lý bộ nhớ hợp nhất (Unified Memory) trên Apple Silicon đòi hỏi đo đạc kết hợp cả Metal active/peak allocations và Process RSS.
- **Giải pháp chuẩn hóa (DoD Issue #10):**
  - Xây dựng `ModelManager` với cổng kiểm soát xác nhận người dùng bắt buộc (`confirm=True`), ngăn chặn mọi hành vi tự ý tải trọng số khi thiếu sự đồng thuận (`UnconfirmedDownloadError`).
  - Kiểm tra đường dẫn an toàn (`is_path_safe`), phòng thủ tuyệt đối tấn công Directory Traversal (`../../etc/passwd`).
  - Kiểm tra trần bộ nhớ định kỳ bằng `mx.get_active_memory()` và `psutil`, chủ động ngắt hoặc cảnh báo khi vượt trần 6.0GB (`MemoryCeilingExceededError`).
  - Cung cấp cơ chế hồi quy ngoại tuyến (Offline Resilient Fallback) để toàn bộ pipeline API kiểm toán và CI/CD có thể kiểm thử xác thực ngay cả khi chưa tải trọng số 4.5GB.

---

## Lesson 13: Cloud BYOK Router qua LiteLLM, Quản lý Khóa Zero-Leak & Định tuyến Multi-Modal
- **Bối cảnh:** Đối với người dùng máy tính văn phòng thông thường không sở hữu GPU/NPU mạnh mẽ, FinSight cần cung cấp khả năng suy luận đám mây với cơ chế BYOK (Bring Your Own Key) cho Anthropic Claude 3.5 Sonnet, Azure OpenAI và OpenAI GPT-4o mà không vi phạm chính sách bảo mật Zero-Leak (AGENTS.md Rule 2).
- **Nguyên nhân & Cạm bẫy:**
  1. Xung đột phụ thuộc: Cài đặt gói `litellm` trần có xu hướng tự động hạ cấp `huggingface-hub` xuống `<2.0`, làm vỡ thư viện `mlx-vlm`. Khắc phục bằng cách ghim phiên bản phụ thuộc `pip install "huggingface-hub>=2.0" litellm`.
  2. Rò rỉ thông tin đăng nhập: Nếu các endpoint trả lời trạng thái cấu hình phản hồi một phần tiền tố khóa (e.g. `sk-ant-api03...`) hoặc trả lại khóa trong JSON response / stack trace, kẻ tấn công hoặc mã độc cục bộ có thể đánh cắp API key của doanh nghiệp.
  3. Mã hóa hình ảnh và Path Traversal: Việc đọc file ảnh để mã hóa base64 đưa vào prompt thị giác (Vision API) nếu không kiểm tra đường dẫn sẽ trở thành công cụ đọc trộm file nhạy cảm trên máy nạn nhân.
- **Giải pháp chuẩn hóa:**
  - Thiết kế `CloudRouter` bọc qua LiteLLM hỗ trợ định tuyến linh hoạt: Anthropic, OpenAI và Azure OpenAI.
  - Tuân thủ nghiêm ngặt Chính sách Zero-Leak: API keys chỉ lưu trong session bộ nhớ hoặc nạp từ `.env`, các endpoint API (`GET /api/v1/models/cloud/status`, `POST /api/v1/models/cloud/keys`) chỉ trả về cờ boolean `configured: true/false` và tuyệt đối không bao giờ phản hồi giá trị khóa.
  - Bảo vệ đa tầng: Kiểm tra an toàn đường dẫn (`is_path_safe`) trước khi đọc và mã hóa base64; chuẩn hóa và gọt phẳng tọa độ bounding box VLM về thang đo `[0, 1000]`.
  - Hồi quy ngoại tuyến (Offline Resilient Fallback): Nếu chưa cấu hình API key hoặc mạng ngoại tuyến, hệ thống tự động fallback về câu trả lời giả định có cấu trúc chuẩn để không làm gián đoạn trải nghiệm người dùng hoặc test suite.





---

## Lesson 14: Tối ưu hóa xử lý BCTC quy mô lớn: Render đa luồng PyMuPDF, Bộ nhớ đệm Manifest và Phòng thủ Traversal trong Cache Invalidation
- **Bối cảnh:** Khi xử lý các báo cáo tài chính kiểm toán dày từ 50 đến 100 trang, việc rasterize từng trang một tuần tự bằng PyMuPDF tốn rất nhiều thời gian. Đồng thời, việc tính toán lại visual patches và suy luận VLM cho các câu hỏi lặp lại trên cùng một tài liệu làm tăng độ trễ và tiêu tốn token không cần thiết.
- **Nguyên nhân & Cạm bẫy:**
  1. *Khóa luồng C / GIL:* Mặc dù PyMuPDF giải phóng GIL trong các thao tác nặng của C, nếu nhiều luồng dùng chung một đối tượng `doc = pymupdf.open()`, tài nguyên có thể bị nghẽn hoặc crash. Cần mở độc lập một document handle cho mỗi luồng xử lý (`_render_single_page_worker`) để bảo đảm an toàn đa luồng 100%.
  2. *Lỗ hổng Traversal trong Subdirectory Cache Clear:* Hàm kiểm tra an toàn đường dẫn chung `is_path_safe()` chỉ đối chiếu với danh sách gốc `ALLOWED_ROOTS` (ví dụ `~/.finsight`). Nếu thư mục xóa cache là thư mục con `~/.finsight/cache/rendered_pages`, tham số `document_id="../../lancedb"` vẫn nằm trong `ALLOWED_ROOTS` và vượt qua kiểm tra, cho phép xóa trắng cơ sở dữ liệu vector! Cần bắt buộc bổ sung ràng buộc quan hệ cha-con trực tiếp: `target_dir.parent == self.render_cache_dir` và lọc ký tự `document_id` qua regex `^[a-zA-Z0-9_\-]+$`.
- **Giải pháp chuẩn hóa:**
  - Áp dụng `concurrent.futures.ThreadPoolExecutor` với số luồng tối ưu `min(cpu_count, 8)`, mở document độc lập trên mỗi worker.
  - Sử dụng bộ nhớ đệm `manifest.json` ghi atomic qua file tạm `.tmp` để kiểm tra `file_size`, `file_mtime`, `dpi`. Khi cache hợp lệ, trả về kết quả trong `< 15ms` mà không cần rasterize lại.
  - Thêm `QueryLRUCache` bộ nhớ đệm trong RAM với khóa `(doc_id, query, top_k, mode)` bọc bởi `threading.RLock()`, đưa độ trễ của các truy vấn lặp lại xuống mức tức thì `< 1ms` (thực nghiệm `0.05ms - 0.58ms`).
  - Đóng dấu cờ `cached: bool` trên API và hiển thị huy hiệu `Cache` màu ngọc lục bảo (emerald) tinh tế trên giao diện máy tính.

---

## Lesson 15: Office.js Taskpane Web Sandbox Multipart Upload & Phòng thủ Traversal trong Tải Lên Tệp PDF
- **Bối cảnh:** Khi tài chính gia thao tác trên Microsoft Excel qua Office.js Web Add-in (chạy trong iframe hoặc webview sandbox của trình duyệt), ứng dụng JavaScript không thể truy cập trực tiếp đường dẫn tập tin tuyệt đối trên hệ điều hành cục bộ (`req.file_path`). Do đó, luồng nạp báo cáo tài chính bắt buộc phải hỗ trợ tải trực tiếp dữ liệu nhị phân hoặc đa phần (multipart stream upload) từ file picker.
- **Cạm bẫy & Lỗ hổng bảo mật:**
  1. *Lỗ hổng Path Traversal trong tiêu đề Content-Disposition:* Tham số `filename` do trình duyệt gửi lên trong multipart form-data có thể bị kẻ tấn công thao túng chứa chuỗi thoát thư mục như `../../evil.pdf` hoặc null bytes (`\0`). Nếu backend ghép chuỗi trực tiếp để lưu trữ, tệp tin độc hại có thể bị ghi đè ra ngoài thư mục an toàn.
  2. *Tệp tin giả mạo định dạng (MIME Spoofing):* Kẻ tấn công có thể đổi tên tệp thực thi độc hại hoặc mã script shell thành `.pdf`. Kiểm tra phần mở rộng tệp là không đủ.
  3. *Trải nghiệm người dùng trong Taskpane hẹp:* Trong không gian bề ngang hẹp (300px - 400px) của taskpane Excel, nếu không tuân thủ quy chuẩn 3 trạng thái giao diện (Skeleton, Error có retry, Actionable Empty) và quy chuẩn kích thước bấm tối thiểu $\ge 48\text{px}$, người dùng sẽ gặp khó khăn khi thao tác kéo thả hoặc chọn tệp.
- **Giải pháp chuẩn hóa (Sprint 7 - Task S7-01):**
  - Xây dựng endpoint `POST /api/v1/documents/upload` tiếp nhận `file: UploadFile = File(...)` với thư mục lưu trữ cô lập `~/.finsight/uploads/`.
  - Xác thực đa tầng: Chặn triệt để ký tự `..`, `/`, `\`, `\0`; lọc tên tệp qua regex nghiêm ngặt `^[a-zA-Z0-9_\-\.]+$` và ràng buộc `target_path.parent == UPLOAD_DIR`.
  - Xác thực magic bytes: Đọc trước 1024 bytes đầu tiên để xác nhận chữ ký nhị phân `%PDF-` trước khi tiến hành lưu luồng tệp đầy đủ.
  - Áp dụng triệt để mô hình **Frontend 4-file pattern** trên `apps/excel`:
    - `src/types/api.ts` (DTOs)
    - `src/lib/api/finsight.ts` (Pure fetch có timeout và User-Agent)
    - `src/lib/hooks/use-ingest.ts` (TanStack Query mutation)
    - `src/components/DocumentUploader.tsx` & `Sidebar.tsx` (Xử lý trọn vẹn 3 trạng thái UI, Kiosk touch target $\ge 48\text{px}$, 100% SVG Lucide React, 0 raw emoji).


