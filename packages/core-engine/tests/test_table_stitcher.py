"""
FinTrace Multi-Page Table Stitcher Test Suite
Tests 2-page and 3-page spanned tables, repeated header filtering, column shifts,
split-row concatenation, row classification, and API security.
Governed by Sprint 10 Task S10-02, ADR-004, and AGENTS.md Rule 3 & Rule 13.
"""

import pytest
from fastapi.testclient import TestClient
from contracts import (
    BoundingBox,
    FragmentRowDTO,
    TableFragmentDTO,
    TableColumnDTO,
    TableRowDTO,
    MultiPageTableDTO,
    TableStitchRequest,
)
from table_stitcher import TableStitcher, strip_accents, is_continuation_title
from main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def stitcher():
    return TableStitcher()


def test_strip_accents_and_continuation_title():
    assert strip_accents("Bảng Cân đối kế toán") == "bang can doi ke toan"
    assert strip_accents("Thuyết minh BCTC") == "thuyet minh bctc"
    assert strip_accents("Số cuối năm") == "so cuoi nam"

    assert is_continuation_title("(Tiếp theo)")
    assert is_continuation_title("Bảng cân đối kế toán (tiếp theo)")
    assert is_continuation_title("Trang 15/45")
    assert not is_continuation_title("A. TÀI SẢN NGẮN HẠN")


def test_single_page_table_stitching(stitcher):
    fragment = TableFragmentDTO(
        page_number=1,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["A. TÀI SẢN NGẮN HẠN", "100", "", "15.000.000.000", "12.000.000.000"],
                bounding_box=BoundingBox(ymin=150, xmin=50, ymax=180, xmax=950),
            ),
            FragmentRowDTO(
                cells=["I. Tiền và các khoản tương đương tiền", "110", "V.01", "5.000.000.000", "4.000.000.000"],
                bounding_box=BoundingBox(ymin=190, xmin=50, ymax=220, xmax=950),
            ),
            FragmentRowDTO(
                cells=["Tiền mặt", "111", "", "2.000.000.000", "1.500.000.000"],
                bounding_box=BoundingBox(ymin=230, xmin=50, ymax=260, xmax=950),
            ),
        ],
    )

    result = stitcher.stitch_fragments([fragment], document_id="DOC_TEST_01", table_name="Bảng Cân đối kế toán")

    assert isinstance(result, MultiPageTableDTO)
    assert result.document_id == "DOC_TEST_01"
    assert result.spanned_pages == [1]
    assert len(result.columns) == 5
    assert [c.key for c in result.columns] == ["line_item", "code", "footnote", "ending_balance", "beginning_balance"]
    assert result.total_rows == 3

    # Check classifications
    assert result.rows[0].is_section is True
    assert result.rows[0].code == "100"
    assert result.rows[1].code == "110"
    assert result.rows[1].footnote == "V.01"
    assert result.rows[2].cells["ending_balance"] == "2.000.000.000"


def test_two_page_spanned_table_with_repeated_header(stitcher):
    # Page 1: Assets short-term
    frag_page_1 = TableFragmentDTO(
        page_number=12,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["A. TÀI SẢN NGẮN HẠN", "100", "", "15.000.000.000", "12.000.000.000"],
                bounding_box=BoundingBox(ymin=150, xmin=50, ymax=180, xmax=950),
            ),
            FragmentRowDTO(
                cells=["1. Tiền mặt", "111", "", "5.000.000.000", "4.000.000.000"],
                bounding_box=BoundingBox(ymin=190, xmin=50, ymax=220, xmax=950),
            ),
        ],
    )

    # Page 2: Continuation with repeated header and continuation marker
    frag_page_2 = TableFragmentDTO(
        page_number=13,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(cells=["(Tiếp theo Bảng cân đối kế toán)"]),  # Continuation marker
            FragmentRowDTO(cells=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"]),  # Repeated header
            FragmentRowDTO(cells=["(1)", "(2)", "(3)", "(4)", "(5)"]),  # Column numbering row
            FragmentRowDTO(
                cells=["B. TÀI SẢN DÀI HẠN", "200", "", "25.000.000.000", "20.000.000.000"],
                bounding_box=BoundingBox(ymin=250, xmin=50, ymax=280, xmax=950),
            ),
            FragmentRowDTO(
                cells=["TỔNG CỘNG TÀI SẢN", "270", "", "40.000.000.000", "32.000.000.000"],
                bounding_box=BoundingBox(ymin=290, xmin=50, ymax=320, xmax=950),
            ),
        ],
    )

    result = stitcher.stitch_fragments([frag_page_1, frag_page_2], document_id="VNM_BCTC_2023", table_name="Balance Sheet")

    assert result.spanned_pages == [12, 13]
    assert result.stitched_from_fragments_count == 2
    # Should contain 4 data rows (repeated header, marker, index row filtered out)
    assert result.total_rows == 4
    assert result.rows[0].page_number == 12
    assert result.rows[1].page_number == 12
    assert result.rows[2].page_number == 13
    assert result.rows[3].page_number == 13

    # Check total row classification
    assert result.rows[3].is_total is True
    assert result.rows[3].code == "270"
    assert result.rows[3].cells["ending_balance"] == "40.000.000.000"


def test_three_page_spanned_table_with_column_shifts(stitcher):
    """
    Test 3-page spanned table with column shifts:
    - Page 1: [Chỉ tiêu, Mã số, Thuyết minh, Số cuối năm, Số đầu năm]
    - Page 2: Column shift -> [Mã số, Chỉ tiêu, Thuyết minh, Số cuối năm, Số đầu năm] (Col 0 and 1 swapped)
    - Page 3: Column shift & omitted -> [Chỉ tiêu, Mã số, Số cuối năm, Số đầu năm] (Thuyết minh omitted, 4 cols)
    """
    frag_1 = TableFragmentDTO(
        page_number=10,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["A. TÀI SẢN NGẮN HẠN", "100", "", "10.000.000.000", "8.000.000.000"],
                bounding_box=BoundingBox(ymin=100, xmin=50, ymax=130, xmax=950),
            ),
        ],
    )

    # Page 2 has Mã số first, then Chỉ tiêu
    frag_2 = TableFragmentDTO(
        page_number=11,
        headers=["Mã số", "Chỉ tiêu", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["200", "B. TÀI SẢN DÀI HẠN", "V.05", "20.000.000.000", "15.000.000.000"],
                bounding_box=BoundingBox(ymin=120, xmin=50, ymax=150, xmax=950),
            ),
        ],
    )

    # Page 3 omitted footnote column
    frag_3 = TableFragmentDTO(
        page_number=12,
        headers=["Chỉ tiêu", "Mã số", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["C. NỢ PHẢI TRẢ", "300", "12.000.000.000", "10.000.000.000"],
                bounding_box=BoundingBox(ymin=140, xmin=50, ymax=170, xmax=950),
            ),
            FragmentRowDTO(
                cells=["TỔNG CỘNG NGUỒN VỐN", "440", "30.000.000.000", "23.000.000.000"],
                bounding_box=BoundingBox(ymin=180, xmin=50, ymax=210, xmax=950),
            ),
        ],
    )

    result = stitcher.stitch_fragments([frag_1, frag_2, frag_3], document_id="HPG_BCTC_2023")

    assert result.spanned_pages == [10, 11, 12]
    assert result.total_rows == 4

    # Verify Page 2 column alignment: code and line_item correctly mapped despite column swap
    row_p2 = result.rows[1]
    assert row_p2.page_number == 11
    assert row_p2.code == "200"
    assert "TÀI SẢN DÀI HẠN" in row_p2.cells["line_item"]
    assert row_p2.cells["ending_balance"] == "20.000.000.000"
    assert row_p2.footnote == "V.05"

    # Verify Page 3 column alignment: ending_balance and beginning_balance aligned despite omitted footnote
    row_p3_1 = result.rows[2]
    assert row_p3_1.page_number == 12
    assert row_p3_1.code == "300"
    assert "NỢ PHẢI TRẢ" in row_p3_1.cells["line_item"]
    assert row_p3_1.cells["ending_balance"] == "12.000.000.000"
    assert row_p3_1.cells["beginning_balance"] == "10.000.000.000"

    # Verify Page 3 summary row
    row_p3_2 = result.rows[3]
    assert row_p3_2.is_total is True
    assert row_p3_2.code == "440"


def test_split_row_concatenation_across_page_boundary(stitcher):
    """
    Test split row across page boundary:
    Bottom of Page 1: 'Phải thu ngắn hạn của khách hàng' (description only, no values)
    Top of Page 2: 'chi tiết theo từng đối tượng lớn', Mã số 131, ending 8.000.000.000
    """
    frag_1 = TableFragmentDTO(
        page_number=5,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["1. Phải thu ngắn hạn của khách hàng", "", "", "", ""],
                bounding_box=BoundingBox(ymin=920, xmin=50, ymax=960, xmax=950),
            ),
        ],
    )

    frag_2 = TableFragmentDTO(
        page_number=6,
        headers=["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối năm", "Số đầu năm"],
        rows=[
            FragmentRowDTO(
                cells=["chi tiết đối tượng lớn", "131", "V.03", "8.000.000.000", "6.500.000.000"],
                bounding_box=BoundingBox(ymin=120, xmin=50, ymax=150, xmax=950),
            ),
        ],
    )

    result = stitcher.stitch_fragments([frag_1, frag_2], document_id="SPLIT_TEST")

    # The 2 rows should be seamlessly concatenated into 1 merged row
    assert result.total_rows == 1
    merged = result.rows[0]
    assert "Phải thu ngắn hạn của khách hàng chi tiết đối tượng lớn" in merged.cells["line_item"]
    assert merged.code == "131"
    assert merged.footnote == "V.03"
    assert merged.cells["ending_balance"] == "8.000.000.000"


def test_empty_fragments_error(stitcher):
    with pytest.raises(ValueError, match="At least one table fragment is required"):
        stitcher.stitch_fragments([], document_id="EMPTY_TEST")


def test_api_table_stitch_endpoint(client):
    payload = {
        "document_id": "VNM_2023",
        "table_name": "Báo cáo Kết quả Kinh doanh",
        "fragments": [
            {
                "page_number": 1,
                "headers": ["Chỉ tiêu", "Mã số", "Thuyết minh", "Năm nay", "Năm trước"],
                "rows": [
                    {
                        "cells": ["1. Doanh thu bán hàng", "01", "VI.25", "100.000.000", "90.000.000"],
                        "bounding_box": {"ymin": 100, "xmin": 50, "ymax": 150, "xmax": 950},
                    }
                ],
            },
            {
                "page_number": 2,
                "headers": ["Chỉ tiêu", "Mã số", "Thuyết minh", "Năm nay", "Năm trước"],
                "rows": [
                    {
                        "cells": ["2. Lợi nhuận sau thuế", "60", "VI.30", "20.000.000", "18.000.000"],
                        "bounding_box": {"ymin": 120, "xmin": 50, "ymax": 160, "xmax": 950},
                    }
                ],
            },
        ],
    }

    response = client.post("/api/v1/table/stitch", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["document_id"] == "VNM_2023"
    assert "table" in data
    table = data["table"]
    assert table["spanned_pages"] == [1, 2]
    assert table["total_rows"] == 2
    assert table["rows"][1]["is_total"] is True
    assert table["rows"][1]["code"] == "60"
    assert "elapsed_ms" in data


def test_api_table_stitch_security_path_traversal(client):
    # Test path traversal injection attempt in document_id
    payload = {
        "document_id": "../../etc/passwd",
        "fragments": [
            {
                "page_number": 1,
                "rows": [{"cells": ["Item", "100", "1000"]}],
            }
        ],
    }
    response = client.post("/api/v1/table/stitch", json=payload)
    assert response.status_code == 422  # Rejected by pydantic field validator
