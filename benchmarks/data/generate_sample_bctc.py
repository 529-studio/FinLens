#!/usr/bin/env python3
"""
Generates synthetic yet structurally authentic Vietnamese Audited Financial Statements (BCTC)
for FinSight Visual RAG testing and benchmarking.
Includes complex multi-column balance sheets, segment revenue charts, and footnotes.
"""

from pathlib import Path
import pymupdf


def create_sample_bctc(output_path: str) -> str:
    resolved_path = Path(output_path).resolve()
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    doc = pymupdf.open()

    # ---------------- PAGE 1: COVER & EXECUTIVE SUMMARY ----------------
    page1 = doc.new_page(width=595, height=842)  # A4: 595 x 842 pt
    page1.insert_text((50, 80), "CÔNG TY CỔ PHẦN SỮA VIỆT NAM (VINAMILK)", fontsize=16, fontname="helv", color=(0.1, 0.2, 0.5))
    page1.insert_text((50, 110), "BÁO CÁO TÀI CHÍNH HỢP NHẤT ĐÃ ĐƯỢC KIỂM TOÁN NĂM 2023", fontsize=13, fontname="helv")
    page1.insert_text((50, 130), "Mã chứng khoán: VNM | Chuẩn mực Kế toán Việt Nam (VAS)", fontsize=10, fontname="helv", color=(0.4, 0.4, 0.4))

    # Draw summary banner
    rect_banner = pymupdf.Rect(50, 150, 545, 230)
    page1.draw_rect(rect_banner, color=(0.2, 0.4, 0.8), fill=(0.95, 0.97, 1.0))
    page1.insert_text((65, 175), "TỔNG QUAN KẾT QUẢ KINH DOANH NĂM 2023", fontsize=11, fontname="helv", color=(0.1, 0.2, 0.5))
    page1.insert_text((65, 195), "• Tổng doanh thu hợp nhất: 60.479 tỷ VNĐ (+0,7% YoY)", fontsize=10, fontname="helv")
    page1.insert_text((65, 215), "• Lợi nhuận sau thuế hợp nhất: 9.019 tỷ VNĐ (+5,2% YoY)", fontsize=10, fontname="helv")

    # Draw simulated bar chart
    chart_rect = pymupdf.Rect(50, 260, 545, 520)
    page1.draw_rect(chart_rect, color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98))
    page1.insert_text((70, 290), "BIỂU ĐỒ 1: CƠ CẤU DOANH THU THEO THỊ TRƯỜNG (2021 - 2023)", fontsize=11, fontname="helv")

    # Bar 1: Thị trường nội địa
    page1.draw_rect(pymupdf.Rect(100, 340, 200, 480), color=(0.1, 0.4, 0.7), fill=(0.2, 0.5, 0.8))
    page1.insert_text((115, 330), "Nội địa: 50.617 tỷ", fontsize=9, fontname="helv")

    # Bar 2: Xuất khẩu & Chi nhánh nước ngoài
    page1.draw_rect(pymupdf.Rect(250, 410, 350, 480), color=(0.8, 0.3, 0.1), fill=(0.9, 0.4, 0.2))
    page1.insert_text((255, 400), "Xuất khẩu: 9.862 tỷ", fontsize=9, fontname="helv")

    # Bar 3: Biên lợi nhuận gộp
    page1.draw_rect(pymupdf.Rect(400, 430, 500, 480), color=(0.1, 0.6, 0.3), fill=(0.2, 0.7, 0.4))
    page1.insert_text((410, 420), "Biên LNG: 40,7%", fontsize=9, fontname="helv")

    # Footnote note
    page1.insert_text((50, 780), "(*) Số liệu trích từ Báo cáo của Ban Điều hành và BCTC kiểm toán bởi PwC Việt Nam.", fontsize=8, fontname="helv", color=(0.5, 0.5, 0.5))

    # ---------------- PAGE 2: BALANCE SHEET ----------------
    page2 = doc.new_page(width=595, height=842)
    page2.insert_text((50, 60), "BẢNG CÂN ĐỐI KẾ TOÁN HỢP NHẤT (Tại ngày 31 tháng 12 năm 2023)", fontsize=13, fontname="helv", color=(0.1, 0.2, 0.5))
    page2.insert_text((50, 80), "Đơn vị tính: Triệu đồng Việt Nam", fontsize=9, fontname="helv", color=(0.4, 0.4, 0.4))

    # Table Header
    page2.draw_rect(pymupdf.Rect(50, 100, 545, 125), color=(0.2, 0.3, 0.4), fill=(0.15, 0.2, 0.3))
    page2.insert_text((60, 117), "TÀI SẢN", fontsize=9, fontname="helv", color=(1, 1, 1))
    page2.insert_text((280, 117), "Mã số", fontsize=9, fontname="helv", color=(1, 1, 1))
    page2.insert_text((330, 117), "Thuyết minh", fontsize=9, fontname="helv", color=(1, 1, 1))
    page2.insert_text((420, 117), "Số cuối năm", fontsize=9, fontname="helv", color=(1, 1, 1))
    page2.insert_text((485, 117), "Số đầu năm", fontsize=9, fontname="helv", color=(1, 1, 1))

    # Rows
    rows = [
        ("A. TÀI SẢN NGẮN HẠN", "100", "", "35.617.200", "31.974.150"),
        ("I. Tiền và các khoản tương đương tiền", "110", "4", "2.671.120", "2.299.850"),
        ("1. Tiền", "111", "", "1.120.400", "890.300"),
        ("2. Các khoản tương đương tiền", "112", "", "1.550.720", "1.409.550"),
        ("II. Đầu tư tài chính ngắn hạn (Tiền gửi)", "120", "5", "23.115.000", "19.700.000"),
        ("III. Các khoản phải thu ngắn hạn", "130", "6", "6.120.400", "5.890.200"),
        ("IV. Hàng tồn kho", "140", "7", "3.610.680", "4.084.100"),
        ("B. TÀI SẢN DÀI HẠN", "200", "", "17.056.800", "16.508.300"),
        ("I. Tài sản cố định hữu hình", "220", "8", "12.450.200", "12.110.000"),
        ("TỔNG CỘNG TÀI SẢN (100 + 200)", "270", "", "52.674.000", "48.482.450"),
    ]

    y = 145
    for item in rows:
        page2.insert_text((60, y), item[0], fontsize=8, fontname="helv")
        page2.insert_text((290, y), item[1], fontsize=8, fontname="helv")
        page2.insert_text((350, y), item[2], fontsize=8, fontname="helv")
        page2.insert_text((410, y), item[3], fontsize=8, fontname="helv")
        page2.insert_text((480, y), item[4], fontsize=8, fontname="helv")
        page2.draw_line((50, y + 5), (545, y + 5), color=(0.85, 0.85, 0.85))
        y += 24

    # Footnote Box
    footnote_rect = pymupdf.Rect(50, 480, 545, 620)
    page2.draw_rect(footnote_rect, color=(0.9, 0.6, 0.2), fill=(1.0, 0.98, 0.92))
    page2.insert_text((65, 505), "THUYẾT MINH SỐ 4: TIỀN VÀ CÁC KHOẢN TƯƠNG ĐƯƠNG TIỀN", fontsize=10, fontname="helv", color=(0.6, 0.3, 0.0))
    page2.insert_text((65, 530), "• Tiền gửi ngân hàng không kỳ hạn: 1.120.400 triệu đồng.", fontsize=8.5, fontname="helv")
    page2.insert_text((65, 550), "• Các khoản tương đương tiền đại diện cho các khoản tiền gửi kỳ hạn gốc không quá 3 tháng", fontsize=8.5, fontname="helv")
    page2.insert_text((65, 570), "  tại các ngân hàng thương mại uy tín với lãi suất dao động từ 3,5% đến 5,2%/năm.", fontsize=8.5, fontname="helv")
    page2.insert_text((65, 595), "• Toàn bộ số dư tiền gửi không bị phong tỏa hay thế chấp cho bất kỳ khoản vay nào.", fontsize=8.5, fontname="helv")

    doc.save(str(resolved_path))
    doc.close()
    return str(resolved_path)


if __name__ == "__main__":
    out = "benchmarks/data/VNM_BCTC_2023_AUDITED.pdf"
    res = create_sample_bctc(out)
    print(f"Sample audited BCTC generated at: {res}")
