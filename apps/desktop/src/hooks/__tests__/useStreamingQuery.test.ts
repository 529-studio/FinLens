import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useStreamingQuery } from '../useStreamingQuery';

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;
  sentData: string[] = [];
  readyState = 1;

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 0);
  }

  send(data: string) {
    this.sentData.push(data);
  }

  close() {
    if (this.onclose) this.onclose();
  }

  simulateMessage(payload: any) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(payload) });
    }
  }

  simulateError() {
    if (this.onerror) {
      this.onerror();
    }
  }
}

describe('useStreamingQuery hook', () => {
  beforeEach(() => {
    MockWebSocket.instances = [];
    vi.stubGlobal('WebSocket', MockWebSocket);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('initializes with idle state and empty streaming text', () => {
    const { result } = renderHook(() => useStreamingQuery());

    expect(result.current.state).toBe('idle');
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.streamingText).toBe('');
    expect(result.current.streamEvidences).toEqual([]);
    expect(result.current.error).toBeNull();
  });

  it('accumulates progressive tokens, parses evidence, and completes on done', async () => {
    const { result } = renderHook(() => useStreamingQuery());

    act(() => {
      result.current.sendStreamQuery('VNM_2023', 'Doanh thu nội địa?');
    });

    expect(result.current.state).toBe('loading');
    expect(result.current.isStreaming).toBe(true);

    const ws = MockWebSocket.instances[0];
    expect(ws).toBeDefined();

    // Simulate token 1
    act(() => {
      ws.simulateMessage({ event: 'token', token: 'Doanh thu ' });
    });
    expect(result.current.streamingText).toBe('Doanh thu ');

    // Simulate token 2
    act(() => {
      ws.simulateMessage({ event: 'token', token: 'nội địa đạt 50.617 tỷ.' });
    });
    expect(result.current.streamingText).toBe('Doanh thu nội địa đạt 50.617 tỷ.');

    // Simulate evidence
    const mockEvidence = [
      {
        page_number: 1,
        bounding_box: { ymin: 300, xmin: 100, ymax: 500, xmax: 300 },
        label: 'Doanh thu nội địa',
        confidence: 0.99,
      },
    ];
    act(() => {
      ws.simulateMessage({ event: 'evidence', evidences: mockEvidence });
    });
    expect(result.current.streamEvidences).toEqual(mockEvidence);

    // Simulate done
    act(() => {
      ws.simulateMessage({ event: 'done', answer: 'Doanh thu nội địa đạt 50.617 tỷ.' });
    });
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.state).toBe('success');
  });

  it('handles streaming error event properly', () => {
    const { result } = renderHook(() => useStreamingQuery());

    act(() => {
      result.current.sendStreamQuery('../../etc', 'attack');
    });

    const ws = MockWebSocket.instances[0];
    act(() => {
      ws.simulateMessage({ event: 'error', error: 'Access denied: Invalid document_id' });
    });

    expect(result.current.state).toBe('error');
    expect(result.current.isStreaming).toBe(false);
    expect(result.current.error).toBe('Access denied: Invalid document_id');
  });
});
