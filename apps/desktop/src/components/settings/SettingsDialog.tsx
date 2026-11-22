/**
 * File 4 of 4: SettingsDialog Component with Dual-Mode Switcher & BYOK Configuration
 * Governed by 529 Engineering Standards:
 * - Rule 2: Zero-Leak Security Policy (masked keys, never exposed).
 * - Rule 15: Zero-Emoji UI Policy (100% Lucide React vector SVGs).
 * - 3 Mandatory UI States (Skeleton, Error with Retry, Empty/Loaded).
 * - Kiosk Ergonomics (>= 48px touch targets).
 */

import { useState, type FC, type FormEvent } from 'react';
import { useSettings } from '../../hooks/useSettings.hook';
import { CloudProvider } from '../../types/settings.types';
import {
  X,
  Settings,
  Cpu,
  Cloud,
  Database,
  Key,
  ShieldCheck,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Eye,
  EyeOff,
  Sliders,
  HardDrive,
} from 'lucide-react';

interface SettingsDialogProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsDialog: FC<SettingsDialogProps> = ({ isOpen, onClose }) => {
  const {
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
  } = useSettings();

  const [activeTab, setActiveTab] = useState<'inference' | 'cloud' | 'local' | 'storage'>('inference');
  const [selectedProvider, setSelectedProvider] = useState<CloudProvider>('anthropic');
  const [apiKeyInput, setApiKeyInput] = useState('');
  const [apiBaseInput, setApiBaseInput] = useState('');
  const [showApiKey, setShowApiKey] = useState(false);

  if (!isOpen) return null;

  const handleKeySubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!apiKeyInput.trim()) return;
    const ok = await saveCloudKey(selectedProvider, apiKeyInput.trim(), apiBaseInput.trim() || undefined);
    if (ok) {
      setApiKeyInput('');
      setApiBaseInput('');
      setShowApiKey(false);
    }
  };

  const isProviderConfigured = cloudStatus?.providers?.[selectedProvider]?.configured ?? false;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="FinTrace Settings"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4 animate-in fade-in duration-200"
    >
      <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <header className="h-16 px-6 border-b border-slate-800 flex items-center justify-between flex-shrink-0 bg-slate-900/90">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 rounded-xl bg-indigo-950/60 border border-indigo-700/50 text-indigo-400">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-slate-100">Cài đặt & Cấu hình FinTrace</h2>
              <p className="text-[11px] text-slate-400">Quản lý Dual-Engine, Cloud BYOK và Lưu trữ Vector</p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng cửa sổ cài đặt"
            className="w-12 h-12 rounded-xl hover:bg-slate-800 text-slate-400 hover:text-slate-200 flex items-center justify-center transition"
          >
            <X className="w-6 h-6" />
          </button>
        </header>

        {/* Tab Navigation */}
        <nav className="flex border-b border-slate-800 bg-slate-950/40 px-6 space-x-2 overflow-x-auto">
          <button
            type="button"
            onClick={() => setActiveTab('inference')}
            className={`min-h-[48px] px-3 py-2 text-xs font-medium border-b-2 transition flex items-center space-x-2 ${
              activeTab === 'inference'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="w-4 h-4 flex-shrink-0" />
            <span>Chế độ suy luận</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('cloud')}
            className={`min-h-[48px] px-3 py-2 text-xs font-medium border-b-2 transition flex items-center space-x-2 ${
              activeTab === 'cloud'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cloud className="w-4 h-4 flex-shrink-0" />
            <span>Cloud BYOK</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('local')}
            className={`min-h-[48px] px-3 py-2 text-xs font-medium border-b-2 transition flex items-center space-x-2 ${
              activeTab === 'local'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Cpu className="w-4 h-4 flex-shrink-0" />
            <span>Local Apple Silicon</span>
          </button>

          <button
            type="button"
            onClick={() => setActiveTab('storage')}
            className={`min-h-[48px] px-3 py-2 text-xs font-medium border-b-2 transition flex items-center space-x-2 ${
              activeTab === 'storage'
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-4 h-4 flex-shrink-0" />
            <span>Lưu trữ LanceDB</span>
          </button>
        </nav>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* SKELETON LOADING STATE */}
          {isLoading && !cloudStatus && !mlxStatus && !storeStats && (
            <div className="space-y-4 animate-pulse">
              <div className="h-6 bg-slate-800 rounded w-1/3"></div>
              <div className="h-20 bg-slate-800/60 rounded-xl"></div>
              <div className="h-20 bg-slate-800/60 rounded-xl"></div>
            </div>
          )}

          {/* ERROR STATE WITH RETRY */}
          {error && (
            <div className="p-4 bg-red-950/50 border border-red-800/60 rounded-xl text-red-200 space-y-3">
              <div className="flex items-center space-x-2">
                <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                <span className="text-sm font-semibold">Lỗi tải thông tin cài đặt</span>
              </div>
              <p className="text-xs text-red-300">{error}</p>
              <button
                type="button"
                onClick={loadSettings}
                className="min-h-[48px] px-4 py-2 bg-red-800 hover:bg-red-700 text-white text-xs font-semibold rounded-lg flex items-center justify-center space-x-2 transition"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Thử lại tải cài đặt (Retry)</span>
              </button>
            </div>
          )}

          {/* TAB 1: INFERENCE MODE */}
          {activeTab === 'inference' && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Chọn chiến lược suy luận VLM
                </h3>
                <p className="text-xs text-slate-400">
                  FinTrace hỗ trợ kiến trúc Dual-Engine linh hoạt giữa xử lý cục bộ và đám mây.
                </p>
              </div>

              <div className="grid grid-cols-1 gap-3">
                {/* Mode Auto */}
                <label
                  className={`min-h-[48px] p-4 rounded-xl border flex items-start space-x-3 cursor-pointer transition ${
                    inferenceMode === 'auto'
                      ? 'bg-indigo-950/40 border-indigo-500/80 ring-1 ring-indigo-500/50'
                      : 'bg-slate-800/40 border-slate-700 hover:bg-slate-800/70'
                  }`}
                >
                  <input
                    type="radio"
                    name="inference_mode"
                    value="auto"
                    checked={inferenceMode === 'auto'}
                    onChange={() => setInferenceMode('auto')}
                    className="mt-1 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-semibold text-slate-200">Tự động (Auto Detect)</span>
                      <span className="text-[10px] bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full">
                        Khuyến nghị
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Tự động dùng Apple Silicon MLX nếu có; tự động chuyển sang Cloud BYOK khi chạy trên máy văn phòng khác.
                    </p>
                  </div>
                </label>

                {/* Mode Local */}
                <label
                  className={`min-h-[48px] p-4 rounded-xl border flex items-start space-x-3 cursor-pointer transition ${
                    inferenceMode === 'local'
                      ? 'bg-indigo-950/40 border-indigo-500/80 ring-1 ring-indigo-500/50'
                      : 'bg-slate-800/40 border-slate-700 hover:bg-slate-800/70'
                  }`}
                >
                  <input
                    type="radio"
                    name="inference_mode"
                    value="local"
                    checked={inferenceMode === 'local'}
                    onChange={() => setInferenceMode('local')}
                    className="mt-1 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center space-x-2">
                      <Cpu className="w-4 h-4 text-emerald-400" />
                      <span className="text-sm font-semibold text-slate-200">Local Engine (Apple Silicon MLX)</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Chạy offline 100% trên chip M-Series với Qwen2.5-VL-7B 4-bit. Chi phí 0 VNĐ, bảo mật tuyệt đối.
                    </p>
                  </div>
                </label>

                {/* Mode Cloud */}
                <label
                  className={`min-h-[48px] p-4 rounded-xl border flex items-start space-x-3 cursor-pointer transition ${
                    inferenceMode === 'cloud'
                      ? 'bg-indigo-950/40 border-indigo-500/80 ring-1 ring-indigo-500/50'
                      : 'bg-slate-800/40 border-slate-700 hover:bg-slate-800/70'
                  }`}
                >
                  <input
                    type="radio"
                    name="inference_mode"
                    value="cloud"
                    checked={inferenceMode === 'cloud'}
                    onChange={() => setInferenceMode('cloud')}
                    className="mt-1 text-indigo-600 focus:ring-indigo-500"
                  />
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center space-x-2">
                      <Cloud className="w-4 h-4 text-indigo-400" />
                      <span className="text-sm font-semibold text-slate-200">Cloud BYOK Router (LiteLLM)</span>
                    </div>
                    <p className="text-xs text-slate-400">
                      Sử dụng khóa API riêng của doanh nghiệp với Claude 3.5 Sonnet hoặc Azure OpenAI GPT-4o.
                    </p>
                  </div>
                </label>
              </div>
            </div>
          )}

          {/* TAB 2: CLOUD BYOK */}
          {activeTab === 'cloud' && (
            <div className="space-y-5">
              <div className="space-y-1">
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300">
                    Chính sách Zero-Leak Security (Rule 2)
                  </h3>
                </div>
                <p className="text-xs text-slate-400">
                  Khóa API chỉ được lưu trong phiên bộ nhớ bảo mật và không bao giờ phản hồi qua API hoặc log.
                </p>
              </div>

              {/* Provider Selector */}
              <div className="flex space-x-2">
                {(['anthropic', 'azure', 'openai'] as CloudProvider[]).map((p) => {
                  const isConf = cloudStatus?.providers?.[p]?.configured ?? false;
                  return (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setSelectedProvider(p)}
                      className={`flex-1 min-h-[48px] p-3 rounded-xl border text-xs font-medium transition flex flex-col items-center justify-center space-y-1 ${
                        selectedProvider === p
                          ? 'bg-indigo-950/60 border-indigo-500 text-indigo-200'
                          : 'bg-slate-800/40 border-slate-700 text-slate-400 hover:bg-slate-800'
                      }`}
                    >
                      <span className="capitalize font-semibold">{p}</span>
                      <span className="flex items-center space-x-1 text-[10px]">
                        {isConf ? (
                          <>
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-400">Đã cấu hình</span>
                          </>
                        ) : (
                          <span className="text-slate-400">Chưa có khóa</span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>

              {/* Form Input for Provider */}
              <form onSubmit={handleKeySubmit} className="space-y-4 bg-slate-950/40 p-4 rounded-xl border border-slate-800">
                <div className="space-y-1.5">
                  <label htmlFor="cloud-api-key" className="text-xs font-medium text-slate-300 flex items-center justify-between">
                    <span>Khóa API ({selectedProvider.toUpperCase()})</span>
                    {isProviderConfigured && (
                      <span className="text-[11px] text-emerald-400">Khóa đã kích hoạt sẵn sàng</span>
                    )}
                  </label>
                  <div className="relative flex items-center">
                    <input
                      id="cloud-api-key"
                      type={showApiKey ? 'text' : 'password'}
                      value={apiKeyInput}
                      onChange={(e) => setApiKeyInput(e.target.value)}
                      placeholder={isProviderConfigured ? 'Nhập khóa mới để ghi đè...' : 'Nhập API key bí mật...'}
                      className="w-full bg-slate-800/80 border border-slate-700 text-sm px-4 py-3 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-100 placeholder-slate-400 min-h-[48px] pr-12"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      aria-label={showApiKey ? 'Ẩn khóa API' : 'Hiển thị khóa API'}
                      className="absolute right-3 p-1.5 text-slate-400 hover:text-slate-200 transition"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {selectedProvider === 'azure' && (
                  <div className="space-y-1.5">
                    <label htmlFor="azure-endpoint" className="text-xs font-medium text-slate-300">
                      Azure API Base URL (Endpoint)
                    </label>
                    <input
                      id="azure-endpoint"
                      type="text"
                      value={apiBaseInput}
                      onChange={(e) => setApiBaseInput(e.target.value)}
                      placeholder="https://your-resource.openai.azure.com/"
                      className="w-full bg-slate-800/80 border border-slate-700 text-sm px-4 py-3 rounded-xl focus:outline-none focus:border-indigo-500 text-slate-100 placeholder-slate-400 min-h-[48px]"
                    />
                  </div>
                )}

                <div className="flex items-center justify-between pt-2">
                  <div className="text-xs">
                    {saveState === 'saved' && (
                      <span className="text-emerald-400 flex items-center space-x-1">
                        <CheckCircle2 className="w-4 h-4" />
                        <span>Đã lưu thành công (Zero-Leak)</span>
                      </span>
                    )}
                    {saveState === 'error' && (
                      <span className="text-red-400 flex items-center space-x-1">
                        <AlertCircle className="w-4 h-4" />
                        <span>{saveMessage || 'Lỗi lưu khóa'}</span>
                      </span>
                    )}
                  </div>

                  <button
                    type="submit"
                    disabled={saveState === 'saving' || !apiKeyInput.trim()}
                    className="min-h-[48px] px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white font-medium text-xs rounded-xl flex items-center space-x-2 transition shadow"
                  >
                    <Key className="w-4 h-4" />
                    <span>{saveState === 'saving' ? 'Đang lưu...' : 'Lưu khóa BYOK'}</span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* TAB 3: LOCAL MLX */}
          {activeTab === 'local' && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Apple Silicon Unified Memory Engine
                </h3>
                <p className="text-xs text-slate-400">
                  Tải và vận hành mô hình Qwen2.5-VL-7B 4-bit cục bộ dưới trần bộ nhớ 6.0 GB.
                </p>
              </div>

              {mlxStatus ? (
                <div className="space-y-3 bg-slate-950/40 p-4 rounded-xl border border-slate-800 text-xs">
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Mô hình:</span>
                    <span className="font-mono text-slate-200">{mlxStatus.model_id}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Lượng tử hóa:</span>
                    <span className="text-emerald-400 font-semibold">{mlxStatus.quantization}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Trạng thái bộ đệm cache:</span>
                    <span className={mlxStatus.is_cached ? 'text-emerald-400' : 'text-amber-400'}>
                      {mlxStatus.is_cached ? 'Đã tải sẵn sàng' : 'Chưa tải trọng số (~4.5 GB)'}
                    </span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Trần bộ nhớ tối đa:</span>
                    <span className="text-indigo-400">{mlxStatus.memory_ceiling_gb} GB Unified Memory</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-slate-400">Bộ nhớ Metal sử dụng:</span>
                    <span className="font-mono text-slate-200">
                      {Math.round(mlxStatus.memory_usage.active_mb)} MB (Active) /{' '}
                      {Math.round(mlxStatus.memory_usage.peak_mb)} MB (Peak)
                    </span>
                  </div>

                  {!mlxStatus.is_cached && (
                    <div className="pt-3">
                      <button
                        type="button"
                        onClick={() => startMlxDownload()}
                        className="w-full min-h-[48px] px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded-xl text-xs font-semibold flex items-center justify-center space-x-2 transition"
                      >
                        <HardDrive className="w-4 h-4" />
                        <span>Xác nhận tải trọng số mô hình (4.5 GB)</span>
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <p className="text-xs text-slate-400">Không có thông tin MLX Engine khả dụng.</p>
              )}
            </div>
          )}

          {/* TAB 4: LANCEDB STORAGE */}
          {activeTab === 'storage' && (
            <div className="space-y-4">
              <div className="space-y-1">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                  Kho lưu trữ Multi-Vector LanceDB
                </h3>
                <p className="text-xs text-slate-400">
                  Tập trung quản lý các vector 128 chiều và siêu dữ liệu trang tài liệu trên đĩa.
                </p>
              </div>

              {storeStats ? (
                <div className="space-y-3 bg-slate-950/40 p-4 rounded-xl border border-slate-800 text-xs">
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Đường dẫn đĩa:</span>
                    <span className="font-mono text-slate-200 truncate max-w-xs">{storeStats.db_path}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Tổng tài liệu đã lưu:</span>
                    <span className="font-semibold text-indigo-400">{storeStats.total_documents}</span>
                  </div>
                  <div className="flex justify-between border-b border-slate-800 pb-2">
                    <span className="text-slate-400">Tổng số trang vector:</span>
                    <span className="font-semibold text-emerald-400">{storeStats.total_pages}</span>
                  </div>
                  <div className="flex justify-between pt-1">
                    <span className="text-slate-400">Kích thước vector:</span>
                    <span className="font-mono text-slate-200">{storeStats.vector_dimension} chiều</span>
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-400">Không có dữ liệu thống kê lưu trữ.</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="h-16 px-6 border-t border-slate-800 flex items-center justify-between flex-shrink-0 bg-slate-900/90">
          <span className="text-[11px] text-slate-400">FinTrace Visual Financial Intelligence v0.1.0</span>
          <button
            type="button"
            onClick={onClose}
            className="min-h-[48px] px-6 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl transition"
          >
            Đóng
          </button>
        </footer>
      </div>
    </div>
  );
};
