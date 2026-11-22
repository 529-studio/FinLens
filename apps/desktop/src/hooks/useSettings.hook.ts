/**
 * File 3 of 4: Custom React Hook for FinSight Settings & Dual-Mode Configuration
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

import { useState, useEffect, useCallback } from 'react';
import {
  InferenceMode,
  CloudProvider,
  CloudStatusDTO,
  MlxModelStatusDTO,
  StoreStatsDTO,
} from '../types/settings.types';
import {
  fetchCloudStatus,
  updateCloudKey,
  fetchMlxStatus,
  downloadMlxModel,
  fetchStoreStats,
} from '../api/settings.fetch';

const MODE_STORAGE_KEY = 'finsight_inference_mode';

export function useSettings() {
  const [inferenceMode, setInferenceModeState] = useState<InferenceMode>(() => {
    try {
      const saved = localStorage.getItem(MODE_STORAGE_KEY);
      if (saved === 'local' || saved === 'cloud' || saved === 'auto') {
        return saved;
      }
    } catch {
      // In sandboxed webviews, localStorage might be unavailable
    }
    return 'auto';
  });

  const [cloudStatus, setCloudStatus] = useState<CloudStatusDTO | null>(null);
  const [mlxStatus, setMlxStatus] = useState<MlxModelStatusDTO | null>(null);
  const [storeStats, setStoreStats] = useState<StoreStatsDTO | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const loadSettings = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    const [cloudRes, mlxRes, storeRes] = await Promise.allSettled([
      fetchCloudStatus(),
      fetchMlxStatus(),
      fetchStoreStats(),
    ]);

    if (cloudRes.status === 'fulfilled') {
      setCloudStatus(cloudRes.value);
    }
    if (mlxRes.status === 'fulfilled') {
      setMlxStatus(mlxRes.value);
    }
    if (storeRes.status === 'fulfilled') {
      setStoreStats(storeRes.value);
    }

    if (
      cloudRes.status === 'rejected' &&
      mlxRes.status === 'rejected' &&
      storeRes.status === 'rejected'
    ) {
      setError('Không thể kết nối đến FinTrace Core Daemon. Hãy chắc chắn daemon đang chạy.');
    }

    setIsLoading(false);
  }, []);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  const setInferenceMode = useCallback((mode: InferenceMode) => {
    setInferenceModeState(mode);
    try {
      localStorage.setItem(MODE_STORAGE_KEY, mode);
    } catch {
      // Ignore storage errors in restricted contexts
    }
  }, []);

  const saveCloudKey = useCallback(
    async (provider: CloudProvider, apiKey: string, apiBase?: string) => {
      setSaveState('saving');
      setSaveMessage(null);
      try {
        const res = await updateCloudKey({
          provider,
          api_key: apiKey,
          api_base: apiBase,
        });
        setSaveState('saved');
        setSaveMessage(res.message);
        // Refresh cloud status without wiping other state
        const updated = await fetchCloudStatus();
        setCloudStatus(updated);
        return true;
      } catch (err: any) {
        setSaveState('error');
        setSaveMessage(err.message || 'Lỗi cập nhật API key');
        return false;
      }
    },
    []
  );

  const startMlxDownload = useCallback(async (modelId?: string) => {
    setIsLoading(true);
    try {
      await downloadMlxModel(modelId, true);
      const updated = await fetchMlxStatus();
      setMlxStatus(updated);
    } catch (err: any) {
      setError(err.message || 'Lỗi tải mô hình MLX');
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    inferenceMode,
    setInferenceMode,
    cloudStatus,
    mlxStatus,
    storeStats,
    isLoading,
    error,
    saveState,
    saveMessage,
    loadSettings,
    saveCloudKey,
    startMlxDownload,
  };
}
