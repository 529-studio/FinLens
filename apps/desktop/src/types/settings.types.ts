/**
 * File 1 of 4: DTOs & Interfaces for FinSight Settings & Dual-Mode Inference
 * Governed by 529 Engineering Standards (frontend-4file-and-resilient-ui)
 */

export type InferenceMode = 'auto' | 'local' | 'cloud';

export type CloudProvider = 'anthropic' | 'azure' | 'openai';

export interface CloudProviderDetailDTO {
  configured: boolean;
  model: string;
  api_base_configured?: boolean | null;
}

export interface CloudStatusDTO {
  available_providers: string[];
  providers: Record<string, CloudProviderDetailDTO>;
  default_model: string;
}

export interface CloudKeyUpdateRequestDTO {
  provider: CloudProvider;
  api_key: string;
  api_base?: string;
}

export interface CloudKeyUpdateResponseDTO {
  provider: string;
  status: string;
  message: string;
}

export interface MlxModelStatusDTO {
  model_id: string;
  quantization: string;
  estimated_size_gb: number;
  memory_ceiling_gb: number;
  is_cached: boolean;
  is_loaded: boolean;
  cache_dir: string;
  hardware_capability: string;
  memory_usage: {
    active_mb: number;
    peak_mb: number;
    rss_mb: number;
  };
}

export interface StoreStatsDTO {
  db_path: string;
  total_documents: number;
  total_pages: number;
  disk_size_bytes: number;
  vector_dimension: number;
}
