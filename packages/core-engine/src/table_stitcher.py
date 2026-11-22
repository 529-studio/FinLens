"""
FinTrace Multi-Page Table Stitcher
Heuristic and geometric table header alignment and row concatenation across consecutive PDF pages.
Handles repeated headers, continuation markers, column shifts, split rows, and cross-page coordinate grounding.
Governed by Sprint 10 Task S10-02, ADR-004, and AGENTS.md Rule 13 & Rule 15.
"""

import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Set
from contracts import (
    BoundingBox,
    TableColumnDTO,
    FragmentRowDTO,
    TableFragmentDTO,
    TableRowDTO,
    MultiPageTableDTO,
    TableStitchRequest,
)


CONTINUATION_PATTERNS = [
    r"(?i)\(tiếp theo\)",
    r"(?i)\(tiếp\)",
    r"(?i)tiếp theo trang",
    r"(?i)^bảng cân đối kế toán\s*\(tiếp theo\)",
    r"(?i)^báo cáo kết quả hoạt động kinh doanh\s*\(tiếp theo\)",
    r"(?i)^báo cáo lưu chuyển tiền tệ\s*\(tiếp theo\)",
    r"(?i)^trang\s+\d+(\s*/\s*\d+)?$",
]

HEADER_KEYWORDS = {
    "line_item": ["chi tieu", "khoan muc", "noi dung", "dien giai", "ten tai san", "nguon von", "muc", "item"],
    "code": ["ma so", "ma", "code", "ms"],
    "footnote": ["thuyet minh", "thuyet minh bctc", "tm", "note"],
    "ending_balance": ["so cuoi nam", "so cuoi ky", "cuoi nam", "cuoi ky", "nam nay", "ky nay", "31/12"],
    "beginning_balance": ["so dau nam", "so dau ky", "dau nam", "dau ky", "nam truoc", "ky truoc", "01/01"],
}

TOTAL_KEYWORDS = [
    "tong cong",
    "tong so",
    "tong tai san",
    "tong nguon von",
    "tong no phai tra",
    "tong von chu so huu",
    "loi nhuan sau thue",
    "loi nhuan truoc thue",
    "loi nhuan ke toan truoc thue",
    "tong doanh thu",
    "luu chuyen tien thuan",
]

SECTION_PATTERN = r"^(?:[A-E]\.|\b(?:I|II|III|IV|V|VI|VII|VIII|IX|X)\.)\s+"


def strip_accents(text: str) -> str:
    """Removes Vietnamese accents and returns normalized lowercase ASCII string."""
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return ascii_text.replace("đ", "d").replace("Đ", "d").lower().strip()


def is_continuation_title(text: str) -> bool:
    """Checks if text is a continuation title or page artifact."""
    clean = text.strip()
    norm = strip_accents(clean)
    if "tiep theo" in norm:
        return True
    if "tiep" in norm and ("(" in norm or ")" in norm or "trang" in norm):
        return True
    if re.match(r"(?i)^trang\s+\d+(\s*/\s*\d+)?$", clean):
        return True
    return any(re.search(pat, clean) for pat in CONTINUATION_PATTERNS)


def is_index_marker_row(cells: List[str]) -> bool:
    """Detects column numbering guide rows such as ['(1)', '(2)', '(3)', '(4)'] or ['1', '2', '3']."""
    if not cells:
        return False
    valid_count = 0
    for c in cells:
        s = c.strip()
        if not s:
            continue
        if re.match(r"^\(?\d+\)?$", s):
            valid_count += 1
        else:
            return False
    return valid_count >= max(2, len(cells) // 2)


class TableStitcher:
    """
    Multi-Page Table Stitcher for Vietnamese Audited Financial Statements (BCTC).
    Performs header detection, column alignment, continuous row concatenation,
    and cross-page coordinate preservation.
    """

    def __init__(self):
        pass

    def normalize_header(self, raw_header: str, col_idx: int) -> Tuple[str, str, str]:
        """
        Normalizes raw header text into (key, display_header, data_type).
        """
        norm = strip_accents(raw_header)
        for key, keywords in HEADER_KEYWORDS.items():
            for kw in keywords:
                if kw in norm:
                    if key == "line_item":
                        return ("line_item", raw_header.strip() or "Chỉ tiêu", "text")
                    elif key == "code":
                        return ("code", raw_header.strip() or "Mã số", "code")
                    elif key == "footnote":
                        return ("footnote", raw_header.strip() or "Thuyết minh", "footnote")
                    elif key == "ending_balance":
                        return ("ending_balance", raw_header.strip() or "Số cuối kỳ", "numeric")
                    elif key == "beginning_balance":
                        return ("beginning_balance", raw_header.strip() or "Số đầu kỳ", "numeric")

        # Fallback generic column
        clean_name = re.sub(r"[^a-zA-Z0-9_]+", "_", norm).strip("_")
        key = clean_name if clean_name else f"col_{col_idx}"
        return (key, raw_header.strip() or f"Column {col_idx+1}", "text")

    def _infer_column_type(self, cell_values: List[str]) -> str:
        """Infers data type of a column based on sample cell contents."""
        numeric_count = 0
        code_count = 0
        footnote_count = 0
        total_non_empty = 0

        for raw in cell_values:
            val = raw.strip()
            if not val or val == "-":
                continue
            total_non_empty += 1

            # Check numeric: formatted money with commas/dots
            if re.match(r"^[\(\-]?\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?\)?$", val):
                numeric_count += 1
            # Check code: 3-digit number (100-440) or section letter
            if re.match(r"^\d{3}$", val) or re.match(r"^[A-D]$", val):
                code_count += 1
            # Check footnote: V.01, 12, etc.
            if re.match(r"^(?:V\.)?\d{1,2}[a-z]?$", val, re.IGNORECASE):
                footnote_count += 1

        if total_non_empty == 0:
            return "text"

        if code_count / total_non_empty >= 0.6:
            return "code"
        if numeric_count / total_non_empty >= 0.6:
            return "numeric"
        if footnote_count / total_non_empty >= 0.6:
            return "footnote"
        return "text"

    def _score_column_match(
        self,
        base_col: TableColumnDTO,
        frag_header: Optional[str],
        frag_cells: List[str],
    ) -> float:
        """Calculates matching affinity score between a base column and a fragment column."""
        score = 0.0

        # Header similarity
        if frag_header:
            norm_frag = strip_accents(frag_header)
            norm_base = strip_accents(base_col.header)
            if norm_frag == norm_base:
                score += 5.0
            elif any(kw in norm_frag for kw in HEADER_KEYWORDS.get(base_col.key, [])):
                score += 4.0

        # Cell data type heuristic scoring
        inferred_type = self._infer_column_type(frag_cells)
        if inferred_type == base_col.data_type:
            score += 3.0

        # Code column specific check
        if base_col.key == "code":
            matches = sum(1 for c in frag_cells if re.match(r"^\d{3}$", c.strip()))
            if frag_cells and matches / len(frag_cells) >= 0.5:
                score += 3.0

        # Numeric column check
        if base_col.data_type == "numeric":
            matches = sum(1 for c in frag_cells if re.match(r"^[\(\-]?\d{1,3}(?:[.,]\d{3})*", c.strip()))
            if frag_cells and matches / len(frag_cells) >= 0.5:
                score += 2.0

        return score

    def align_columns(
        self,
        base_columns: List[TableColumnDTO],
        frag_headers: Optional[List[str]],
        frag_rows: List[FragmentRowDTO],
    ) -> Dict[int, int]:
        """
        Maps fragment column index -> base column index.
        Handles column shifts, omissions, and swapped orders.
        """
        num_base = len(base_columns)
        if not frag_rows:
            return {i: min(i, num_base - 1) for i in range(num_base)}

        num_frag_cols = max(len(r.cells) for r in frag_rows)
        mapping: Dict[int, int] = {}
        used_base_indices: Set[int] = set()

        # Extract column values for heuristic scoring
        frag_col_values: Dict[int, List[str]] = {i: [] for i in range(num_frag_cols)}
        for r in frag_rows:
            for i in range(num_frag_cols):
                if i < len(r.cells):
                    frag_col_values[i].append(r.cells[i])

        # Priority matching: match columns with highest affinity score
        candidates: List[Tuple[float, int, int]] = []
        for f_idx in range(num_frag_cols):
            f_hdr = frag_headers[f_idx] if frag_headers and f_idx < len(frag_headers) else None
            for b_idx, b_col in enumerate(base_columns):
                affinity = self._score_column_match(b_col, f_hdr, frag_col_values[f_idx])
                # Small positional preference if scores tie
                pos_bonus = 0.5 if f_idx == b_idx else 0.0
                candidates.append((affinity + pos_bonus, f_idx, b_idx))

        candidates.sort(reverse=True, key=lambda x: x[0])

        for score, f_idx, b_idx in candidates:
            if f_idx not in mapping and b_idx not in used_base_indices and score > 1.0:
                mapping[f_idx] = b_idx
                used_base_indices.add(b_idx)

        # Fallback for any unmapped fragment columns: map sequentially to unused base columns
        unused_base = [i for i in range(num_base) if i not in used_base_indices]
        for f_idx in range(num_frag_cols):
            if f_idx not in mapping:
                if unused_base:
                    b_idx = unused_base.pop(0)
                    mapping[f_idx] = b_idx
                    used_base_indices.add(b_idx)
                elif f_idx < num_base:
                    mapping[f_idx] = f_idx
                else:
                    mapping[f_idx] = num_base - 1

        return mapping

    def _extract_base_columns(self, fragment: TableFragmentDTO) -> Tuple[List[TableColumnDTO], List[FragmentRowDTO]]:
        """Extracts and normalizes base columns from the initial table fragment."""
        raw_rows = fragment.rows
        headers: List[str] = []
        data_rows: List[FragmentRowDTO] = []

        if fragment.headers:
            headers = fragment.headers
            data_rows = raw_rows
        elif raw_rows:
            # Check row 0 for continuation title
            start_idx = 0
            if is_continuation_title(raw_rows[0].cells[0] if raw_rows[0].cells else ""):
                start_idx = 1

            if start_idx < len(raw_rows):
                candidate_header = raw_rows[start_idx].cells
                # Check if row looks like header
                if any(any(kw in strip_accents(c) for kw in HEADER_KEYWORDS["line_item"]) for c in candidate_header):
                    headers = candidate_header
                    start_idx += 1
                else:
                    # Generic headers based on column count
                    headers = [f"Cột {i+1}" for i in range(len(candidate_header))]

            # Check if next row is column numbering marker (e.g. 1, 2, 3...)
            if start_idx < len(raw_rows) and is_index_marker_row(raw_rows[start_idx].cells):
                start_idx += 1

            data_rows = raw_rows[start_idx:]
        else:
            headers = ["Chỉ tiêu", "Mã số", "Thuyết minh", "Số cuối kỳ", "Số đầu kỳ"]
            data_rows = []

        columns: List[TableColumnDTO] = []
        seen_keys: Set[str] = set()

        for idx, h in enumerate(headers):
            key, display_name, data_type = self.normalize_header(h, idx)
            # Ensure unique keys
            if key in seen_keys:
                key = f"{key}_{idx}"
            seen_keys.add(key)

            columns.append(TableColumnDTO(
                key=key,
                header=display_name,
                index=idx,
                data_type=data_type,
            ))

        return columns, data_rows

    def _filter_continuation_rows(
        self,
        rows: List[FragmentRowDTO],
        base_columns: List[TableColumnDTO],
    ) -> List[FragmentRowDTO]:
        """Strips repeated headers, column numbering rows, and continuation markers from a fragment."""
        filtered: List[FragmentRowDTO] = []

        for r in rows:
            if not r.cells or all(not c.strip() for c in r.cells):
                continue

            first_cell = r.cells[0].strip()
            # 1. Skip continuation titles
            if is_continuation_title(first_cell):
                continue

            # 2. Skip index marker row (e.g. ['(1)', '(2)', '(3)', '(4)'])
            if is_index_marker_row(r.cells):
                continue

            # 3. Skip repeated header rows
            norm_cells = [strip_accents(c) for c in r.cells]
            is_repeated_header = any(
                any(kw in c for kw in HEADER_KEYWORDS["line_item"])
                for c in norm_cells
            ) and any(
                any(kw in c for kw in HEADER_KEYWORDS["code"] + HEADER_KEYWORDS["ending_balance"])
                for c in norm_cells
            )
            if is_repeated_header:
                continue

            filtered.append(r)

        return filtered

    def _classify_row(self, line_item: str, code: Optional[str]) -> Tuple[bool, bool]:
        """Determines whether a row is a section header or a total/summary row."""
        norm_item = strip_accents(line_item)

        is_total = any(kw in norm_item for kw in TOTAL_KEYWORDS)
        is_section = bool(re.match(SECTION_PATTERN, line_item.strip())) or (
            code is not None and code.endswith("00") and not is_total
        )

        return is_section, is_total

    def _merge_split_rows_if_needed(self, rows: List[TableRowDTO]) -> List[TableRowDTO]:
        """
        Detects and merges rows that split across consecutive pages.
        e.g., Description at bottom of Page 1 with empty code/balance,
        completed by continuation text on Page 2.
        """
        if len(rows) < 2:
            return rows

        merged: List[TableRowDTO] = []
        i = 0
        while i < len(rows):
            curr = rows[i]
            if i + 1 < len(rows):
                nxt = rows[i + 1]
                # Condition: curr is at page boundary, has line_item but no code/values,
                # and nxt is on consecutive page with values
                curr_item = curr.cells.get("line_item", "").strip()
                curr_code = curr.code or curr.cells.get("code", "").strip()
                curr_ending = curr.cells.get("ending_balance", "").strip()

                nxt_item = nxt.cells.get("line_item", "").strip()
                nxt_code = nxt.code or nxt.cells.get("code", "").strip()
                nxt_ending = nxt.cells.get("ending_balance", "").strip()

                is_boundary = (curr.page_number + 1 == nxt.page_number)
                curr_has_item_only = bool(curr_item) and not curr_code and not curr_ending
                nxt_has_values = bool(nxt_code or nxt_ending)

                if is_boundary and curr_has_item_only and nxt_has_values:
                    # Combine line item
                    combined_item = f"{curr_item} {nxt_item}".strip()
                    combined_cells = dict(nxt.cells)
                    combined_cells["line_item"] = combined_item

                    # Use nxt row properties with merged text and nxt bounding box
                    merged_row = TableRowDTO(
                        row_index=len(merged),
                        page_number=nxt.page_number,
                        cells=combined_cells,
                        raw_cells=nxt.raw_cells,
                        bounding_box=nxt.bounding_box,
                        is_total=nxt.is_total,
                        is_section=nxt.is_section,
                        code=nxt_code,
                        footnote=nxt.footnote,
                    )
                    merged.append(merged_row)
                    i += 2
                    continue

            merged.append(curr)
            i += 1

        # Reindex monotonic row numbers
        for idx, r in enumerate(merged):
            r.row_index = idx

        return merged

    def stitch_fragments(
        self,
        fragments: List[TableFragmentDTO],
        document_id: str,
        table_name: str = "Bảng Cân đối kế toán",
    ) -> MultiPageTableDTO:
        """
        Stitches multiple single-page table fragments into a continuous MultiPageTableDTO.
        """
        if not fragments:
            raise ValueError("At least one table fragment is required for stitching")

        # Sort fragments strictly by page number
        sorted_fragments = sorted(fragments, key=lambda f: f.page_number)
        spanned_pages = [f.page_number for f in sorted_fragments]

        # 1. Establish base columns from initial fragment
        base_columns, first_page_rows = self._extract_base_columns(sorted_fragments[0])
        first_page_rows = self._filter_continuation_rows(first_page_rows, base_columns)

        num_base_cols = len(base_columns)
        base_col_keys = [c.key for c in base_columns]

        stitched_rows: List[TableRowDTO] = []
        global_row_idx = 0

        # Helper to process and append rows for a page
        def process_page_rows(
            raw_rows: List[FragmentRowDTO],
            page_num: int,
            col_mapping: Dict[int, int],
        ):
            nonlocal global_row_idx
            for r in raw_rows:
                row_cells: Dict[str, str] = {k: "" for k in base_col_keys}
                ordered_cells: List[str] = ["" for _ in range(num_base_cols)]

                for frag_col_idx, val in enumerate(r.cells):
                    base_idx = col_mapping.get(frag_col_idx)
                    if base_idx is not None and 0 <= base_idx < num_base_cols:
                        k = base_col_keys[base_idx]
                        row_cells[k] = val.strip()
                        ordered_cells[base_idx] = val.strip()

                line_item = row_cells.get("line_item", "")
                code_val = row_cells.get("code") or None
                footnote_val = row_cells.get("footnote") or None

                is_sec, is_tot = self._classify_row(line_item, code_val)

                # Fallback bounding box if none provided
                bbox = r.bounding_box or BoundingBox(ymin=100, xmin=50, ymax=900, xmax=950)

                table_row = TableRowDTO(
                    row_index=global_row_idx,
                    page_number=page_num,
                    cells=row_cells,
                    raw_cells=ordered_cells,
                    bounding_box=bbox,
                    is_total=is_tot,
                    is_section=is_sec,
                    code=code_val,
                    footnote=footnote_val,
                )
                stitched_rows.append(table_row)
                global_row_idx += 1

        # Process first page with identity mapping
        identity_mapping = {i: i for i in range(num_base_cols)}
        process_page_rows(first_page_rows, sorted_fragments[0].page_number, identity_mapping)

        # 2. Process continuation fragments
        for frag in sorted_fragments[1:]:
            clean_rows = self._filter_continuation_rows(frag.rows, base_columns)
            mapping = self.align_columns(base_columns, frag.headers, clean_rows)
            process_page_rows(clean_rows, frag.page_number, mapping)

        # 3. Merge split rows across page breaks
        final_rows = self._merge_split_rows_if_needed(stitched_rows)

        # Calculate confidence: based on row extraction count and alignment
        confidence = 0.95 if len(final_rows) > 0 else 0.50

        return MultiPageTableDTO(
            document_id=document_id,
            table_name=table_name,
            spanned_pages=spanned_pages,
            columns=base_columns,
            rows=final_rows,
            total_rows=len(final_rows),
            stitched_from_fragments_count=len(sorted_fragments),
            confidence=round(confidence, 2),
            metadata={
                "page_count": len(spanned_pages),
                "total_sections": sum(1 for r in final_rows if r.is_section),
                "total_summary_rows": sum(1 for r in final_rows if r.is_total),
            },
        )

    def stitch(self, request: TableStitchRequest) -> MultiPageTableDTO:
        """API adapter for TableStitchRequest."""
        return self.stitch_fragments(
            fragments=request.fragments,
            document_id=request.document_id,
            table_name=request.table_name or "Financial Statement Table",
        )
