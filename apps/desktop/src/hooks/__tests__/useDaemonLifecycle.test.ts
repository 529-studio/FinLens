import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDaemonLifecycle } from '../useDaemonLifecycle';

describe('useDaemonLifecycle', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('initializes in connecting state and transitions to online when fetch succeeds', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'healthy', service: 'FinTrace Core Daemon' }),
    }));

    const { result } = renderHook(() => useDaemonLifecycle(false));

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.status).toBe('online');
    expect(result.current.error).toBeNull();
    expect(result.current.port).toBe(8765);
  });

  it('transitions to offline state when health check fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('Network error')));

    const { result } = renderHook(() => useDaemonLifecycle(false));

    await act(async () => {
      await Promise.resolve();
    });

    expect(result.current.status).toBe('offline');
    expect(result.current.error).toContain('Không thể kết nối');
  });

  it('retries connection when retry is called', async () => {
    const mockFetch = vi.fn()
      .mockRejectedValueOnce(new Error('Connection refused'))
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ status: 'healthy' }),
      });

    vi.stubGlobal('fetch', mockFetch);

    const { result } = renderHook(() => useDaemonLifecycle(false));

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.status).toBe('offline');

    await act(async () => {
      await result.current.retry();
    });
    expect(result.current.status).toBe('online');
    expect(result.current.error).toBeNull();
  });
});
