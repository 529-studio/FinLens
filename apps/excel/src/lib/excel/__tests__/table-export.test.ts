import { describe, it, expect } from 'vitest';
import {
  getColumnLetter,
  prepareExportMatrix,
  insertFinancialTableToSheet,
} from '../table-export';
import { FinancialTableData } from '../../../types/api';

describe('table-export utility', () => {
  it('correctly maps 0-based column indices to Excel column letters', () => {
    expect(getColumnLetter(0)).toBe('A');
    expect(getColumnLetter(1)).toBe('B');
    expect(getColumnLetter(25)).toBe('Z');
    expect(getColumnLetter(26)).toBe('AA');
    expect(getColumnLetter(27)).toBe('AB');
  });

  it('prepares 2D export matrix and appends Total row with sums for numeric columns', () => {
    const tableData: FinancialTableData = {
      headers: ['Khoản mục', 'Năm 2022', 'Năm 2023'],
      rows: [
        ['Doanh thu nội địa', 48200, 50617],
        ['Doanh thu xuất khẩu', 9120, 9862],
      ],
      includeTotalRow: true,
      sourceDocId: 'VNM_BCTC_2023_AUDITED',
      sourcePage: 1,
    };

    const { valuesMatrix, totalRowIndex, formulas } = prepareExportMatrix(tableData);

    expect(valuesMatrix.length).toBe(4); // Header + 2 data rows + 1 total row
    expect(valuesMatrix[0]).toEqual(['Khoản mục', 'Năm 2022', 'Năm 2023']);
    expect(totalRowIndex).toBe(3);

    // Total row check
    const totalRow = valuesMatrix[3];
    expect(totalRow[0]).toBe('Tổng cộng');
    expect(totalRow[1]).toBe(57320); // 48200 + 9120
    expect(totalRow[2]).toBe(60479); // 50617 + 9862

    expect(formulas[0]).toBeNull();
    expect(formulas[1]).toBe('SUM');
    expect(formulas[2]).toBe('SUM');
  });

  it('omits total row when includeTotalRow is false', () => {
    const tableData: FinancialTableData = {
      headers: ['Chỉ số', 'Tỷ lệ %'],
      rows: [
        ['Biên LNG', 40.7],
        ['Biên LN ròng', 18.2],
      ],
      includeTotalRow: false,
      sourceDocId: 'VNM_BCTC_2023_AUDITED',
      sourcePage: 1,
    };

    const { valuesMatrix, totalRowIndex } = prepareExportMatrix(tableData);
    expect(valuesMatrix.length).toBe(3); // Header + 2 data rows
    expect(totalRowIndex).toBeNull();
  });

  it('executes fallback cleanly when Office.js is not present in test environment', async () => {
    const tableData: FinancialTableData = {
      headers: ['Chỉ tiêu', 'Giá trị'],
      rows: [['Tiền mặt', 23115]],
      sourceDocId: 'VNM_2023',
      sourcePage: 2,
    };

    const res = await insertFinancialTableToSheet(tableData);
    expect(res.success).toBe(true);
    expect(res.insertedCellsCount).toBeGreaterThan(0);
    expect(res.auditComment).toContain('VNM_2023');
    expect(res.auditComment).toContain('trang 2');
  });
});
