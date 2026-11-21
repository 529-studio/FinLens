/**
 * FinSight Excel Add-in Table Exporter
 * Inserts extracted financial table data and formulas into active Excel sheet
 * with interactive Audit Trail Links back to PDF source.
 * Governed by ADR-001 and Sprint 7 Task S7-04.
 */

/* global Excel */

import { FinancialTableData, TableExportResult } from '../../types/api';

/**
 * Converts a 0-indexed column number to Excel column letters (0 -> A, 1 -> B, 26 -> AA).
 */
export function getColumnLetter(colIndex: number): string {
  let temp = colIndex;
  let letter = '';
  while (temp >= 0) {
    letter = String.fromCharCode((temp % 26) + 65) + letter;
    temp = Math.floor(temp / 26) - 1;
  }
  return letter;
}

/**
 * Prepares the 2D values matrix and formula row for export.
 */
export function prepareExportMatrix(data: FinancialTableData): {
  valuesMatrix: (string | number)[][];
  totalRowIndex: number | null;
  formulas: (string | null)[];
} {
  const numRows = data.rows.length;
  const numCols = data.headers.length;

  const valuesMatrix: (string | number)[][] = [
    [...data.headers],
    ...data.rows.map((r) => [...r]),
  ];

  const shouldAddTotal = data.includeTotalRow ?? true;
  let totalRowIndex: number | null = null;
  const formulas: (string | null)[] = new Array(numCols).fill(null);

  if (shouldAddTotal && numRows > 0) {
    totalRowIndex = valuesMatrix.length;
    const totalRow: (string | number)[] = new Array(numCols).fill('');
    totalRow[0] = 'Tổng cộng';

    for (let c = 1; c < numCols; c++) {
      const isNumericCol = data.rows.some((r) => typeof r[c] === 'number');
      if (isNumericCol) {
        // Will be populated with =SUM(...) in sheet context
        formulas[c] = `SUM`;
        // Sum calculation for mock/preview
        const sum = data.rows.reduce<number>((acc, r) => {
          const val = r[c];
          return acc + (typeof val === 'number' ? val : 0);
        }, 0);
        totalRow[c] = sum;
      }
    }

    valuesMatrix.push(totalRow);
  }

  return { valuesMatrix, totalRowIndex, formulas };
}

/**
 * Inserts financial table data directly into active Excel sheet.
 */
export async function insertFinancialTableToSheet(
  data: FinancialTableData
): Promise<TableExportResult> {
  const { valuesMatrix, totalRowIndex } = prepareExportMatrix(data);
  let auditComment = `[FinSight Audit Trail] Trích xuất từ tài liệu ${data.sourceDocId}, trang ${data.sourcePage}. Nhấp vào sidebar để xem ảnh gốc.`;
  if (data.footnotes && data.footnotes.length > 0) {
    const fnSummary = data.footnotes
      .map((f) => `TM ${f.footnoteNumber} (${f.lineItem}): ${f.summary}`)
      .join(' | ');
    auditComment += ` | Thuyết minh BCTC: ${fnSummary}`;
  }

  // 1. Office.js Runtime
  if (typeof Excel !== 'undefined' && typeof Excel.run === 'function') {
    return Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      const selectedRange = context.workbook.getSelectedRange();
      selectedRange.load(['rowIndex', 'columnIndex', 'address']);

      await context.sync();

      const startRow = selectedRange.rowIndex;
      const startCol = selectedRange.columnIndex;
      const rowCount = valuesMatrix.length;
      const colCount = data.headers.length;

      // Target range for entire table
      const targetRange = sheet.getRangeByIndexes(startRow, startCol, rowCount, colCount);
      targetRange.values = valuesMatrix;

      // Header row styling
      const headerRange = sheet.getRangeByIndexes(startRow, startCol, 1, colCount);
      headerRange.format.font.bold = true;
      headerRange.format.fill.color = '#1E293B'; // slate-800
      headerRange.format.font.color = '#FFFFFF';

      // Insert native Excel formulas on Total row if present
      if (totalRowIndex !== null) {
        const totalSheetRow = startRow + totalRowIndex;
        const totalRange = sheet.getRangeByIndexes(totalSheetRow, startCol, 1, colCount);
        totalRange.format.font.bold = true;

        for (let c = 1; c < colCount; c++) {
          const isNumericCol = data.rows.some((r) => typeof r[c] === 'number');
          if (isNumericCol) {
            const colLetter = getColumnLetter(startCol + c);
            const firstDataRow = startRow + 2; // 1-based Excel row after header
            const lastDataRow = startRow + totalRowIndex;
            const formulaCell = sheet.getRangeByIndexes(totalSheetRow, startCol + c, 1, 1);
            formulaCell.formulas = [[`=SUM(${colLetter}${firstDataRow}:${colLetter}${lastDataRow})`]];
          }
        }
      }

      // Auto-fit column widths
      targetRange.format.autofitColumns();

      // Attach Audit Trail comment on top-left origin cell
      const originCell = sheet.getRangeByIndexes(startRow, startCol, 1, 1);
      context.workbook.comments.add(originCell, auditComment, 'Plain');

      await context.sync();

      return {
        success: true,
        insertedCellsCount: rowCount * colCount,
        originAddress: selectedRange.address,
        auditComment,
        footnotesCount: data.footnotes ? data.footnotes.length : 0,
      };
    });
  }

  // 2. Fallback for non-Office.js browser test / dev environment
  console.debug('Excel runtime not detected. Executing fallback preview.', valuesMatrix);
  return {
    success: true,
    insertedCellsCount: valuesMatrix.length * data.headers.length,
    originAddress: 'A1:C5 (Mock)',
    auditComment,
    footnotesCount: data.footnotes ? data.footnotes.length : 0,
  };
}
