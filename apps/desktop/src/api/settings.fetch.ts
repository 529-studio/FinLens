/**
 * File 2 of 4: Resilient Fetcher for FinSight Settings & BYOK
 * Governed by 529 Engineering Standards (resilient-networking-and-waf & frontend-4file)
 */

import {
  CloudStatusDTO,
  CloudKeyUpdateRequestDTO,
  CloudKeyUpdateResponseDTO,
  MlxModelStatusDTO,
  StoreStatsDTO,
} from '../types/settings.types';
import { ApiError } from './visual_rag.fetch';

const BASE_URL = 'http://127.0.0.1:8765';
const DEFAULT_TIMEOUT_MS = 10000;

async function requestWithTimeout<T>(
  url: string,
  options: RequestInit = {},
  timeoutMs = DEFAULT_TIMEOUT_MS
): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'User-Agent': 'FinTrace-Desktop-Client/1.0',
        ...(options.headers || {}),
      },
      signal: controller.signal,
    });

    if (!res.ok) {
      const errBody = await res.text().catch(() => '');
      throw new ApiError(res.status, `Request failed (${res.status}): ${errBody || res.statusText}`);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err.name === 'AbortError') {
      throw new ApiError(408, 'Request timed out. Ensure core daemon is running.');
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function fetchCloudStatus(): Promise<CloudStatusDTO> {
  return requestWithTimeout<CloudStatusDTO>(`${BASE_URL}/api/v1/models/cloud/status`);
}

export async function updateCloudKey(payload: CloudKeyUpdateRequestDTO): Promise<CloudKeyUpdateResponseDTO> {
  return requestWithTimeout<CloudKeyUpdateResponseDTO>(`${BASE_URL}/api/v1/models/cloud/keys`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function fetchMlxStatus(): Promise<MlxModelStatusDTO> {
  return requestWithTimeout<MlxModelStatusDTO>(`${BASE_URL}/api/v1/models/mlx/status`);
}

export async function downloadMlxModel(modelId?: string, confirm = true): Promise<any> {
  return requestWithTimeout<any>(`${BASE_URL}/api/v1/models/mlx/download`, {
    method: 'POST',
    body: JSON.stringify({
      model_id: modelId,
      confirm,
    }),
  }, 60000); // 60s timeout for download initialization
}

export async function fetchStoreStats(): Promise<StoreStatsDTO> {
  return requestWithTimeout<StoreStatsDTO>(`${BASE_URL}/api/v1/store/stats`);
}
