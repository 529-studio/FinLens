import { describe, it, expect, vi, afterEach } from 'vitest';
import { fetchQueryResult, ApiError } from '../finsight';

describe('Excel finsight API client (S13-02)', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('rejects empty documentId with ApiError instead of returning mock-guide', async () => {
    await expect(fetchQueryResult('Doanh thu?', undefined)).rejects.toThrow(ApiError);
  });

  it('throws ApiError on daemon HTTP/network errors instead of silent 0.85 fallback', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValueOnce(new Error('Network down'));
    await expect(fetchQueryResult('Doanh thu?', 'VNM_BCTC_2023_AUDITED')).rejects.toThrow(ApiError);
  });

  it('returns grounded QueryResult when daemon responds 200 OK', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        document_id: 'VNM_BCTC_2023_AUDITED',
        answer: 'Doanh thu đạt 60.478 tỷ VNĐ.',
        evidences: [{ page_number: 1, confidence: 0.98 }],
      }),
    } as Response);

    const res = await fetchQueryResult('Doanh thu?', 'VNM_BCTC_2023_AUDITED');
    expect(res.id).toBe('VNM_BCTC_2023_AUDITED_P1');
    expect(res.confidence).toBe(0.98);
    expect(res.data).toContain('60.478');
  });
});
