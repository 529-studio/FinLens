/**
 * FinSight Excel Add-in Taskpane Logic
 * Injects extracted financial table data and formulas into active Excel sheet
 * with interactive Audit Trail Links back to PDF source.
 */

/* global Excel, Office */

export interface ExtractedTableData {
  headers: string[];
  rows: (string | number)[][];
  totalRowFormula?: string;
  sourceDocId: string;
  sourcePage: number;
}

export async function insertFinancialTableToSheet(data: ExtractedTableData): Promise<void> {
  return Excel.run(async (context) => {
    const sheet = context.workbook.worksheets.getActiveWorksheet();
    const selectedRange = context.workbook.getSelectedRange();
    selectedRange.load(["rowIndex", "columnIndex"]);

    await context.sync();

    const startRow = selectedRange.rowIndex;
    const startCol = selectedRange.columnIndex;
    const numRows = data.rows.length + 1; // +1 for header
    const numCols = data.headers.length;

    // Target range for table
    const targetRange = sheet.getRangeByIndexes(startRow, startCol, numRows, numCols);

    // Prepare 2D matrix
    const valuesMatrix: (string | number)[][] = [
      data.headers,
      ...data.rows
    ];

    targetRange.values = valuesMatrix;

    // Format headers: bold, dark background, white text
    const headerRange = sheet.getRangeByIndexes(startRow, startCol, 1, numCols);
    headerRange.format.font.bold = true;
    headerRange.format.fill.color = "#1E293B"; // slate-800
    headerRange.format.font.color = "#FFFFFF";

    // Auto-fit columns
    targetRange.format.autofitColumns();

    // Attach Audit Trail Comment on the first header cell
    const originCell = sheet.getRangeByIndexes(startRow, startCol, 1, 1);
    originCell.comments.add(
      `[FinSight Audit Trail] Trích xuất từ tài liệu ${data.sourceDocId}, trang ${data.sourcePage}. Nhấp vào sidebar để xem ảnh gốc.`
    );

    await context.sync();
  });
}
