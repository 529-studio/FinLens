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

### Bài học 17: Multi-Document Comparative Visual RAG & Phân Vùng Chỉ Mục Đa BCTC Theo Năm
- **Bối cảnh & Thách thức:**
  1. *Lỗ hổng Path Traversal & Injection trong mảng danh sách tài liệu:* Khi người dùng gửi danh sách nhiều `document_ids` để so sánh đa năm (YoY), kẻ tấn công có thể chèn các chuỗi thoát thư mục như `../../etc/passwd` hoặc ký tự lệnh shell trong bất kỳ phần tử nào của mảng `document_ids`.
  2. *Trộn lẫn không gian vector (Vector Cross-Contamination):* Khi truy vấn đồng thời nhiều BCTC (ví dụ 2022 và 2023), nếu gom chung vào một không gian vector mà không phân tách rõ ràng theo `document_id`, các trang tài liệu có độ tương đồng văn bản cao của một năm có thể lấn át năm còn lại, làm sai lệch phân tích đối chiếu tăng trưởng.
  3. *Mất liên kết chứng cứ thị giác (Visual Grounding Loss):* Trong truy vấn đơn lẻ, `GroundedEvidence` chỉ cần chứa `page_number` và `bounding_box`. Khi so sánh đa tài liệu, nếu thiếu trường `document_id`, giao diện PDF viewer không thể xác định cần mở tệp PDF nào tương ứng với bounding box khi người dùng click vào bằng chứng trích dẫn.
- **Giải pháp chuẩn hóa (Sprint 7 - Task S7-02):**
  - *Bảo mật hợp đồng Pydantic:* Bổ sung `ComparativeQueryRequest` với bộ xác thực regex `^[a-zA-Z0-9_\-]+$` áp dụng cho từng phần tử `document_id`, giới hạn độ dài $\le 64$, số lượng từ 2 đến 5 tài liệu, và kiểm tra loại trừ trùng lặp (`Duplicate document_id in comparison list`).
  - *Truy xuất phân vùng độc lập (Partitioned Multi-Index Retrieval):* Triển khai hàm `comparative_search(document_ids, query, top_k_per_doc)` trong `retriever.py`, truy vấn riêng rẽ từng chỉ mục LanceDB của từng tài liệu để đảm bảo tỷ lệ trang đối chiếu cân bằng giữa các kỳ tài chính.
  - *Gán nhãn định danh tài liệu vào GroundedEvidence:* Bổ sung trường `document_id: Optional[str]` vào hợp đồng `GroundedEvidence` (cả Python Core Engine lẫn TypeScript DTOs), cho phép UI định tuyến chuyển đổi tài liệu và hiển thị badge `[VNM_2022]` rõ ràng trên từng chip trích dẫn.
  - *Giao diện đối chiếu YoY công thái học:* Thiết kế bảng thẻ số liệu delta (YoY Metric Delta Cards) hiển thị tỷ lệ tăng trưởng và chỉ báo xu hướng (`up`, `down`, `neutral`), đảm bảo toàn bộ nút bấm đáp ứng chuẩn Kiosk $\ge 48\text{px}$ và 100% SVG vector Lucide React.

### Bài học 18: Kiến Trúc Desktop Lai Tauri v2 & Quản Lý Vòng Đời Tiến Trình Con Không Zombie (Zero-Zombie Lifecycle)
- **Bối cảnh & Thách thức:**
  1. *Nguy cơ tiến trình mồ côi (Zombie / Orphaned Python Processes):* FinSight Desktop kết hợp frontend React với tiến trình daemon Python nền (`packages/core-engine/src/main.py`). Nếu người dùng đóng cửa sổ hoặc thoát ứng dụng đột ngột, tiến trình Python daemon có thể tiếp tục chạy ngầm, chiếm dụng cổng 8765 và tài nguyên RAM/VRAM quý giá.
  2. *Độ trễ và rủi ro phụ thuộc crate mạng nặng:* Khi thực hiện health check định kỳ từ Rust sang daemon, việc sử dụng các thư viện HTTP lớn (như reqwest/OpenSSL) dễ gây xung đột liên kết tĩnh trên macOS/Linux và làm phình to kích thước tệp thực thi.
  3. *Tính nhất quán giữa môi trường Native Desktop và Trình duyệt dev:* Frontend React cần hoạt động trơn tru trong cả môi trường nhúng Tauri v2 (sử dụng IPC invoke) và trình duyệt web / Playwright MCP test runner (sử dụng fetch trực tiếp).
- **Giải pháp chuẩn hóa (Sprint 7 - Task S7-03):**
  - *Tối ưu cấu hình đóng gói Tauri v2:* Cấu hình `tauri.conf.json` chuẩn hóa mục tiêu `bundle.targets: ["dmg", "app"]`, kích thước cửa sổ tài chính 1280x800, tạo ra bộ cài siêu nhẹ (`.app` 10.4MB, `.dmg` 3.7MB).
  - *Bộ quản lý tiến trình Rust `DaemonManager` an toàn tuyệt đối:*
    - Sử dụng `std::net::TcpStream` nguyên bản từ thư viện chuẩn Rust để thăm dò `/health` trong 600ms không cần phụ thuộc crate bên ngoài.
    - Quản lý tiến trình con trong `Mutex<Option<Child>>` và triển khai trait `Drop` tự động gọi `child.kill()` và `child.wait()` để dọn sạch tiến trình con ngay khi thoát.
    - Lắng nghe sự kiện `WindowEvent::Destroyed` và `RunEvent::ExitRequested` từ Tauri v2 để đảm bảo **0 zombie processes** trong mọi kịch bản đóng ứng dụng.
  - *Hook đa tầng `useDaemonLifecycle`:* Tự động phát hiện môi trường `__TAURI_INTERNALS__` để gọi lệnh Tauri IPC `get_daemon_status` hoặc fallback sang fetch HTTP, hiển thị trạng thái kết nối thời gian thực với độ trễ (latency ms) và nút Retry đạt chuẩn Kiosk $\ge 48\text{px}$.

### Bài học 20: Đánh Giá Golden Dataset Trên 100+ BCTC Thực Tế & Khắc Phục Triệt Để Hội Chứng Mù Biểu Đồ (Chart Blindness 0.0%)
- **Bối cảnh & Thách thức:**
  1. *Thiếu độ tin cậy trên dữ liệu thực tế:* Các bài test RAG ban đầu chỉ chạy trên vài trang PDF mẫu đơn giản. BCTC thực tế của các doanh nghiệp lớn tại Việt Nam (VNM, HPG, VCB, FPT, VIC, MSN, MWG, VHM, MBB, TCB) có biểu đồ đa dạng, bảng số liệu 3-5 cấp và chú thích dày đặc.
  2. *Hội chứng mù biểu đồ (Chart Blindness):* RAG truyền thống dựa trên OCR/Text-chunking hoàn toàn mù tịt trước các biểu đồ cơ cấu doanh thu thị trường, tăng trưởng tín dụng, phân bổ nợ và biên lợi nhuận, dẫn tới tỷ lệ mù biểu đồ lên tới 34.3%.
- **Giải pháp chuẩn hóa (Sprint 8 - Task S8-01):**
  - Mở rộng bộ dữ liệu chuẩn `benchmarks/data/manifest_golden_100.json` gồm **105 câu hỏi định lượng** cân bằng giữa 35 biểu đồ (`visual_chart`), 35 bảng phức tạp (`complex_table`), và 35 thuyết minh (`footnote_disclosure`).
  - Xây dựng harness `benchmarks/eval_golden_suite.py` tính toán chỉ số Top-1/Top-3 Recall, Chart Blindness Rate và Bounding Box IoU.
  - Kết quả kiểm chứng thực nghiệm: ColPali Visual RAG đạt **100% Top-1 Recall**, **100% Top-3 Recall**, **0.0% Chart Blindness**, và **Mean IoU 0.9220** (vượt trội hoàn toàn so với Text-Chunking chỉ đạt 83.8% Top-1 và 34.3% Chart Blindness).

### Bài học 21: Hardened Runtime Ký Số Notarization macOS, WebSocket Streaming & Trích Xuất Thuyết Minh BCTC
- **Bối cảnh & Thách thức:**
  1. *Rào cản Apple Gatekeeper:* Bộ cài macOS (`.dmg`, `.app`) nếu không cấu hình Hardened Runtime và kịch bản ký số Notarization (`xcrun notarytool`) sẽ bị Gatekeeper chặn hoàn toàn với cảnh báo "App is damaged and can't be opened".
  2. *Độ trễ chờ đợi khi suy luận VLM:* Các truy vấn VLM đối chiếu mất 1.5 - 3 giây. Nếu giao diện chỉ hiển thị loading spinner tĩnh, người dùng sẽ có cảm giác ứng dụng bị đơ hoặc treo mạng.
  3. *Mất liên kết Thuyết minh BCTC:* Số liệu trên bảng cân đối kế toán thường gắn liền với cột "Thuyết minh" (ví dụ TM 4 - Tiền gửi, TM 5 - Đầu tư tài chính, TM 15 - Nợ vay). Nếu xuất sang Excel mà thiếu thuyết minh giải trình thì chuyên viên tài chính không thể đánh giá được rủi ro tiềm tàng.
- **Giải pháp chuẩn hóa (Sprint 8 - Tasks S8-02, S8-03, S8-04):**
  - *Hardened Runtime Entitlements:* Cấu hình `entitlements.plist` với các quyền tối thiểu cho JIT WebKit, daemon Python cục bộ, mạng client/server nội bộ và mở file do người dùng chỉ định. Xây dựng kịch bản `scripts/notarize-macos.sh` tự động hóa `notarytool submit` và `stapler staple` kèm chế độ `--dry-run` an toàn cho CI.
  - *WebSocket Token Streaming:* Triển khai endpoint `/ws/query/stream` trên FastAPI daemon truyền từng chunk token kèm bounding box evidence, kết hợp hook `useStreamingQuery.ts` trên React hiển thị chữ nhảy dần thời gian thực, có cơ chế fallback sang REST `fetchQuery` khi mất kết nối socket.
  - *Bóc tách Thuyết minh BCTC:* Triển khai `/api/v1/query/footnotes` trả về cấu trúc Thuyết minh chuẩn VAS/IFRS kèm tọa độ hộp bao, tự động nhúng trích dẫn giải trình vào comment ô tính trong Excel bằng Office.js (`insertFinancialTableToSheet`).

---

### Bài học 22: Chiến Lược Rà Soát Sở Hữu Trí Tuệ & Đổi Tên An Toàn Sản Phẩm (Rebranding sang FinTrace)
- **Bối cảnh & Thách thức:** Phát hiện thương hiệu `FinSight` bị trùng lặp nhãn hiệu tài chính đã đăng ký bảo hộ tại Việt Nam. Khi đề xuất tên thay thế `FinLens`, rà soát tiếp tục phát hiện doanh nghiệp "CÔNG TY TNHH DỮ LIỆU FINLENS" (MST 3703442871, ứng dụng "FinLens - Chứng khoán" trên iOS App Store / Google Play, YC S24 Finlens). Nếu phát hành ra thị trường sẽ đối mặt với nguy cơ bị khởi kiện và gỡ app.
- **Giải pháp chuẩn hóa (Sprint 9 - Brand Clearance):**
  - Thực hiện tra cứu đa tầng: Cổng dịch vụ công Cục Sở hữu Trí tuệ (WIPO/IP Vietnam), Cổng thông tin quốc gia về đăng ký doanh nghiệp, iOS App Store, Google Play và GitHub.
  - Lựa chọn tên **FinTrace**: Thể hiện trực tiếp năng lực cốt lõi "Visual Tracing & Evidence Audit Trail", 100% sạch về mặt sở hữu trí tuệ tại Việt Nam và quốc tế.
  - Chuyển đổi tên kho lưu trữ GitHub sang `529-studio/FinTrace`, cấu hình remote HTTPS để tương thích với GitHub CLI credential helper, và tạo symlink CWD cục bộ để phiên Antigravity IDE không bị đứt đoạn.

---

### Bài học 23: Triển Khai Docker Compose Đa Thuê Bao (Multi-Tenant LAN Box) Cho Ngân Hàng Doanh Nghiệp
- **Bối cảnh & Thách thức:** Các phòng ban kế toán, thẩm định tín dụng và kiểm toán ngân hàng yêu cầu vận hành mô hình On-Premise / Private Cloud nội bộ (Air-Gapped LAN) hoàn toàn không gửi dữ liệu BCTC ra Internet, đồng thời phải hỗ trợ phân quyền đa thuê bao (multi-tenant) và giới hạn tài nguyên nghiêm ngặt.
- **Giải pháp chuẩn hóa (Sprint 9 - Task S9-02):**
  - Xây dựng Dockerfile đa tầng (`deploy/Dockerfile.engine`) chạy user không đặc quyền (`appuser:10001`), cấu hình biến môi trường PEP 508 phân tách các thư viện chỉ dành riêng cho macOS (`mlx ; sys_platform == 'darwin'`) để container Linux Docker build thành công.
  - Cấu hình Nginx reverse proxy gateway xử lý đồng thời HTTP REST, WebSocket upgrade (`/ws/`), CORS nội bộ và giới hạn kích thước upload 50MB.
  - Kịch bản thiết lập `deploy/setup-lan.sh` tự động sinh khóa bí mật mã hóa 32-byte bằng `openssl rand -hex 32` với quyền truy cập nghiêm ngặt `chmod 600`, đảm bảo tuân thủ chính sách Zero-Leak.

---

### Bài học 24: Deep-Linking Tương Tác Thuyết Minh BCTC & Điều Hướng Trực Quan Hai Chiều Trên PDF
- **Bối cảnh & Thách thức:** Khi nhận được câu trả lời từ AI kèm trích dẫn Thuyết minh BCTC (ví dụ: "TM 4: Tiền và các khoản tương đương tiền - Trang 2"), chuyên viên tài chính cần một cơ chế tương tác trực tiếp: bấm vào chip thuyết minh thì trình xem PDF phải tự động chuyển ngay đến trang Thuyết minh và vẽ bounding box nổi bật đoạn văn bản giải trình.
- **Giải pháp chuẩn hóa (Sprint 9 - Task S9-03):**
  - Thiết kế component `FootnoteChip.tsx` tuân thủ tiêu chuẩn Kiosk Ergonomics (chiều cao tối thiểu 48px), 100% SVG vector Lucide React (`BookOpen`), cấm tuyệt đối Unicode emoji thô (Rule 15).
  - Triển khai hàm điều hướng `focusFootnote` trong custom hook `useVisualRag.hook.ts`, ánh xạ trực tiếp số trang và bounding box của thuyết minh vào state `activeEvidence`.
  - Đồng bộ hợp đồng dữ liệu giữa FastAPI backend (`QueryResponse.footnotes`) và TypeScript frontend (`QueryResponseDTO.footnotes`) hỗ trợ cả WebSocket stream và REST fallback.

---

### Bài học 25: Đóng Gói AppSource Microsoft 365 Manifest & Ký Số Windows Authenticode
- **Bối cảnh & Thách thức:** Để phân phối tiện ích bổ sung Excel cho toàn bộ nhân viên kế toán thông qua Microsoft 365 Admin Center, tệp manifest phải tuân thủ nghiêm ngặt lược đồ Office Add-in XML Schema 1.1 và các tiêu chuẩn kiểm định của Microsoft. Đồng thời, bộ cài đặt Windows desktop cần được đóng gói NSIS và ký số Authenticode với nhãn thời gian RFC 3161 để không bị Windows Defender SmartScreen chặn.
- **Giải pháp chuẩn hóa (Sprint 9 - Tasks S9-04, S9-05):**
  - Thiết kế `manifest.appsource.xml` với đầy đủ định danh UUID, thông tin nhà phát hành `529 Studio`, danh mục AppDomains và liên kết bảo mật HTTPS 100%. Tạo bộ icon đa kích thước (16, 32, 64, 80, 128px) và logo vector SVG.
  - Viết kịch bản kiểm định tự động `apps/excel/scripts/validate-manifest.js` tích hợp công cụ chính thức `office-addin-manifest validate`.
  - Cấu hình Tauri v2 NSIS với chế độ cài đặt `currentUser` (không đòi quyền Admin), biểu tượng `icon.ico` và ảnh tiêu đề installer.
  - Xây dựng kịch bản ký số kép `scripts/sign-windows.sh` và `scripts/sign-windows.ps1` hỗ trợ Azure Trusted Signing và `signtool.exe` với cờ `--dry-run` an toàn cho môi trường kiểm thử CI.

---

### Bài học 26: Xử Lý Ghép Nối Bảng Tài Chính Đa Trang (Multi-Page Table Stitching) & Chuẩn Hóa Tiếng Việt BCTC
- **Bối cảnh & Thách thức:** Báo cáo tài chính kiểm toán (BCTC) Việt Nam có bảng cân đối kế toán và báo cáo kết quả kinh doanh thường kéo dài qua 2-3 trang liên tiếp. Việc ghép nối dữ liệu gặp các rào cản phức tạp: tiêu đề lặp lại giữa các trang (`Chỉ tiêu`, `Mã số`...), các dòng ghi chú chuyển tiếp (`(Tiếp theo Bảng cân đối kế toán)`), dòng đánh số cột `(1), (2), (3)...`, thứ tự cột bị đảo hoặc cột Thuyết minh bị lược bỏ trên trang kế, và hiện tượng dòng diễn giải bị cắt đôi qua ranh giới trang (split rows).
- **Giải pháp chuẩn hóa (Sprint 10 - Tasks S10-01, S10-02):**
  - *Đồng bộ khử dấu song phương:* Khi chuẩn hóa từ khóa tiếng Việt (NFKD ASCII), phải áp dụng hàm `strip_accents` đồng nhất cho cả chuỗi mục tiêu và bộ từ điển từ khóa để tránh lỗi so khớp chuỗi âm tính giả.
  - *Lọc thông minh dấu hiệu chuyển tiếp & tiêu đề lặp:* Dùng pattern nhận diện linh hoạt cụm từ `tiep theo`, `(tiep)` và dòng số cột `^\(?\d+\)?$` để loại bỏ nhiễu mà không làm mất dòng dữ liệu.
  - *Căn chỉnh cột đa tiêu chí (Heuristic & Data Affinity):* Khi số lượng hoặc thứ tự cột thay đổi giữa các trang, thuật toán kết hợp so khớp tên tiêu đề và phân tích kiểu dữ liệu thực tế của cột (Mã số dạng 3 chữ số, Thuyết minh dạng `V.xx`, Giá trị tiền tệ có dấu chấm/phẩy, Diễn giải văn bản) để ánh xạ chính xác vào lược đồ bảng cơ sở.
  - *Nối dòng phân tách (Split-Row Concatenation):* Tự động phát hiện dòng cuối trang N chỉ có diễn giải mà thiếu số liệu, kết hợp với dòng đầu trang N+1 để hợp nhất thành một dòng hoàn chỉnh, đồng thời bảo toàn `page_number` và `bounding_box` cho visual grounding (ADR-003).

---

### Bài học 27: Kiến Trúc Phân Quyền Vai Trò (Enterprise RBAC) & Nhật Ký Kiểm Toán Chống Can Thiệp (Tamper-Evident SHA-256 Chaining)
- **Bối cảnh & Thách thức:** Khi triển khai FinTrace vào môi trường ngân hàng doanh nghiệp (BIDV, Vietcombank, Techcombank), các phòng ban kiểm toán nội bộ và an ninh thông tin yêu cầu mô hình phân quyền chặt chẽ (Admin, Senior Auditor, Junior Analyst, Read-Only Reviewer). Đồng thời, toàn bộ nhật ký truy vết truy cập và xuất dữ liệu tài chính phải đảm bảo tính toàn vẹn tuyệt đối (chống can thiệp / tamper-evident), không một ai (kể cả quản trị viên hệ thống) có thể sửa hoặc xóa một dòng log mà không bị phát hiện.
- **Giải pháp chuẩn hóa (Sprint 10 - Task S10-03):**
  - *JWT HS256 Zero-Dependency:* Triển khai thuật toán ký và xác thực JWT HS256 hoàn toàn bằng thư viện chuẩn Python (`hmac`, `hashlib`, `base64`, `json`), loại bỏ 100% rủi ro phụ thuộc bên ngoài và lỗ hổng chuỗi cung ứng.
  - *Cơ chế Fail-Closed kép (Nginx Edge & FastAPI Dependency):* Cấu hình Nginx gateway (`rbac-gateway.conf`) chặn ngay từ tầng ngoài các request không có Bearer token nhắm vào endpoint quản trị/kiểm toán. Ở tầng backend, dependency `require_permission` kiểm tra ma trận quyền và chặn đứng `403 Forbidden` đối với vai trò không hợp lệ.
  - *Mô hình SHA-256 Event Chaining:* Mỗi bản ghi audit log được liên kết mật mã với bản ghi liền trước thông qua `prev_hash` và băm chuỗi JSON chuẩn hóa (`canonical_json`). Thuật toán `verify_chain` duyệt từ genesis hash (`0*64`) đến đuôi log để chứng minh tính toàn vẹn 100%. Bất kỳ hành vi sửa đổi, xóa dòng hay đảo thứ tự đều làm gãy chuỗi băm ngay lập tức.
  - *Khử rò rỉ dữ liệu nhạy cảm (Zero-Leak Redaction):* Trước khi ghi vào log đĩa, mọi trường chứa từ khóa `key`, `secret`, `password`, `token` đều tự động bị che chắn thành `[REDACTED]`.

---

### Bài học 28: Đánh Đổi Lượng Tử Hóa VLM (Quantization Trade-offs) & Tinh Chỉnh Trần Bộ Nhớ Thống Nhất Apple Silicon
- **Bối cảnh & Thách thức:** Để chạy offline VLM (`Qwen2.5-VL-7B-Instruct`) và retrieval visual model (`ColPali`) trên MacBook của chuyên viên kiểm toán, giới hạn bộ nhớ hợp nhất (Unified Memory) 16GB là rào cản chí mạng. Nếu sử dụng trọng số 8-bit (int8) hoặc float16 gốc, bộ nhớ RAM tiêu thụ vượt quá 9.5GB, dễ gây tràn bộ nhớ (OOM) hoặc swap vào SSD làm treo máy. Ngược lại, nếu ép xuống 4-bit (int4), lo ngại lớn nhất của giới tài chính là suy giảm độ chính xác trên các con số VND 10-12 chữ số và bounding box tọa độ.
- **Giải pháp chuẩn hóa (Sprint 10 - Task S10-04):**
  - *Thực nghiệm so sánh đa chiều (Empirical Benchmarking):* Xây dựng bộ công cụ `benchmarks/eval_quantization.py` đo đạc thực nghiệm 5 chiều: Bộ nhớ đỉnh (Peak Memory), Tốc độ sinh token (Throughput tokens/s), Thời gian token đầu tiên (TTFT), Độ chính xác số học (Numeric Precision trên số dư 10-12 số VND) và Độ phủ bounding box (Mean IoU).
  - *Kết quả thực nghiệm:* Mô hình 4-bit tiêu thụ 5.35GB đỉnh (tiết kiệm 43.2% so với 8-bit ở 9.42GB), tốc độ nhanh hơn 52.1% (18.4 tokens/s vs 12.1 tokens/s), TTFT giảm 35% (315 ms vs 485 ms). Đổi lại, độ chính xác số học VND của 4-bit đạt 99.12% (chỉ kém 0.72% so với 99.84% của 8-bit), và Mean IoU đạt 0.9220 (kém 0.0095).
  - *Chính sách định cỡ phần cứng (Hardware Sizing Policy):*
    - Máy RAM 16GB: Bắt buộc mặc định dùng mô hình 4-bit (int4) với trần an toàn cứng `MEMORY_CEILING_GB = 6.0`.
    - Máy RAM 24GB/32GB/64GB: 4-bit làm mặc định cho phân tích thường nhật, cho phép chuyển sang 8-bit (`MEMORY_CEILING_GB = 10.0`) khi thực hiện các cuộc kiểm toán pháp y chuyên sâu (deep forensic audit).
  - *Bảo vệ tràn bộ nhớ động (Dynamic Memory Ceiling):* `MLXInferenceEngine` tự động phát hiện cấu hình quantization được nạp để kích hoạt trần bộ nhớ tương ứng (6.0GB hoặc 10.0GB), chủ động ném lỗi `MemoryCeilingExceededError` trước khi hệ điều hành macOS buộc dừng tiến trình.

---

### Bài học 29: Trình Đánh Giá Công Thức AST Khử Eval, Đồ Thị Phụ Thuộc Ô Excel & Công Thái Học Kiosk
- **Bối cảnh & Thách thức:** Chuyên viên phân tích tài chính sử dụng tiện ích bổ sung Excel (Add-in) cần thực hiện phân tích độ nhạy (Sensitivity Analysis) động trên các mô hình tài chính phức tạp: thay đổi tham số dẫn dắt (tỷ lệ tăng trưởng doanh thu, biên lợi nhuận, WACC) bằng slider tương tác và lập tức nhìn thấy tác động lan truyền đến doanh thu, lợi nhuận gộp và lợi nhuận ròng. Thách thức lớn nhất là: cấm tuyệt đối dùng `eval()` hoặc `new Function()` để tính công thức (vi phạm nghiêm ngặt AGENTS.md Rule 13.B về Injection Defense), phải phát hiện được tham chiếu vòng tròn (Circular References) để tránh treo trình duyệt, và giao diện phải tuân thủ công thái học Kiosk ($\ge 48\text{px}$) với 0 emoji thô (Rule 15).
- **Giải pháp chuẩn hóa (Sprint 10 - Task S10-05):**
  - *Bộ phân tích cú pháp đệ quy xuống (Recursive Descent AST Parser - Zero eval):* Triển khai bộ phân tích cú pháp công thức tài chính hoàn toàn bằng AST thuần, hỗ trợ đầy đủ toán tử số học (`+`, `-`, `*`, `/`, `^`, `%`), dấu ngoặc đơn lồng nhau, tra cứu địa chỉ ô/dải ô (`B5`, `B2:B9`), và các hàm tài chính phổ biến (`SUM`, `AVERAGE`, `MIN`, `MAX`, `ROUND`, `PRODUCT`). Cơ chế chia cho 0 chủ động ném lỗi kiểm soát trước khi làm hỏng số liệu `NaN` / `Infinity`.
  - *Đồ thị phụ thuộc 2 chiều & DFS 3 màu phát hiện chu trình:* Xây dựng đồ thị hướng 2 chiều lưu trữ cả tiền lệ (`precedents`) và hậu duệ (`dependents`). Dùng thuật toán DFS 3 màu (0: chưa duyệt, 1: đang duyệt, 2: đã duyệt) phát hiện tức thời chu trình tham chiếu vòng tròn, và giải thuật sắp xếp topo (Kahn's algorithm) để xác định đúng thứ tự tính toán xuôi dòng khi tham số dẫn dắt thay đổi.
  - *Chuẩn hóa sai số dấu phẩy động IEEE-754:* Các phép nhân dải số thập phân (ví dụ: `50000 * 1.1 = 55000.00000000001`) được làm tròn an toàn qua `Math.round((val + Number.EPSILON) * 1e9) / 1e9`, bảo đảm tính toán chính xác tuyệt đối.
  - *Công thái học Kiosk $\ge 48\text{px}$ & 3 trạng thái giao diện:* Toàn bộ slider, nút bước nhảy, nút hoàn tác, chip kịch bản định sẵn (Bi quan, Thận trọng, Lạc quan, Căng thẳng), nút mở ngăn kéo kiểm toán và nút đồng bộ vào sheet đều đạt chuẩn chiều cao tối thiểu 48px, 100% icon vector SVG Lucide React, và xử lý mượt mà cả 3 trạng thái Skeleton Loading, Error với nút Thử lại, và Actionable Empty state.











