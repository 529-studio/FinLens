import { useState, useEffect, useCallback } from 'react';

export type DaemonConnectionStatus = 'connecting' | 'online' | 'offline';

export interface DaemonState {
  status: DaemonConnectionStatus;
  port: number;
  latencyMs: number | null;
  error: string | null;
  isManaged: boolean;
  pid: number | null;
  checkHealth: () => Promise<void>;
  retry: () => Promise<void>;
}

const DEFAULT_DAEMON_PORT = 8765;
const HEALTH_URL = `http://127.0.0.1:${DEFAULT_DAEMON_PORT}/health`;

export function useDaemonLifecycle(autoPoll = true): DaemonState {
  const [status, setStatus] = useState<DaemonConnectionStatus>('connecting');
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isManaged, setIsManaged] = useState<boolean>(false);
  const [pid, setPid] = useState<number | null>(null);

  const checkHealth = useCallback(async () => {
    const startTime = performance.now();

    // 1. Try Tauri IPC if in native Tauri environment
    if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const res = (await invoke('get_daemon_status')) as {
          is_running: boolean;
          port: number;
          managed_child: boolean;
          pid: number | null;
          message: string;
        };

        const duration = Math.round(performance.now() - startTime);
        if (res.is_running) {
          setStatus('online');
          setLatencyMs(duration);
          setIsManaged(res.managed_child);
          setPid(res.pid);
          setError(null);
          return;
        }
      } catch (e: any) {
        console.debug('Tauri IPC get_daemon_status not available, falling back to fetch', e);
      }
    }

    // 2. Direct HTTP health check fallback
    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 2000);

      const res = await fetch(HEALTH_URL, {
        method: 'GET',
        headers: {
          'User-Agent': 'FinTrace-Desktop-Client/1.0',
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);
      const duration = Math.round(performance.now() - startTime);

      if (res.ok) {
        setStatus('online');
        setLatencyMs(duration);
        setError(null);
      } else {
        setStatus('offline');
        setError(`Daemon trả về mã lỗi HTTP ${res.status}`);
      }
    } catch (err: any) {
      setStatus('offline');
      setError('Không thể kết nối daemon tại http://127.0.0.1:8765');
    }
  }, []);

  const retry = useCallback(async () => {
    setStatus('connecting');
    setError(null);

    // Try starting via Tauri if available
    if (typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window) {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        await invoke('start_daemon');
      } catch (e) {
        console.debug('Failed to start daemon via Tauri command', e);
      }
    }

    await checkHealth();
  }, [checkHealth]);

  useEffect(() => {
    checkHealth();

    if (!autoPoll) return;

    // Background keep-alive polling every 10 seconds
    const interval = setInterval(() => {
      checkHealth();
    }, 10000);

    return () => clearInterval(interval);
  }, [checkHealth, autoPoll]);

  return {
    status,
    port: DEFAULT_DAEMON_PORT,
    latencyMs,
    error,
    isManaged,
    pid,
    checkHealth,
    retry,
  };
}
