/**
 * Unit & Ergonomics Test Suite for SettingsDialog
 * Governed by 529 Engineering Standards:
 * - Rule 2: Zero-Leak Security Policy
 * - Rule 15: Zero-Emoji UI Standard
 * - Kiosk Ergonomics (>= 48px touch targets)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { SettingsDialog } from '../SettingsDialog';

// Mock the useSettings hook
const mockSetInferenceMode = vi.fn();
const mockSaveCloudKey = vi.fn().mockResolvedValue(true);
const mockLoadSettings = vi.fn();
const mockStartMlxDownload = vi.fn();

vi.mock('../../../hooks/useSettings.hook', () => ({
  useSettings: () => ({
    inferenceMode: 'auto',
    setInferenceMode: mockSetInferenceMode,
    cloudStatus: {
      available_providers: ['anthropic', 'azure', 'openai'],
      providers: {
        anthropic: { configured: false, model: 'claude-3-5-sonnet-20241022' },
        azure: { configured: false, model: 'azure/gpt-4o', api_base_configured: false },
        openai: { configured: false, model: 'gpt-4o' },
      },
      default_model: 'claude-3-5-sonnet-20241022',
    },
    mlxStatus: {
      model_id: 'mlx-community/Qwen2.5-VL-7B-Instruct-4bit',
      quantization: '4-bit',
      estimated_size_gb: 4.5,
      memory_ceiling_gb: 6.0,
      is_cached: false,
      is_loaded: false,
      cache_dir: '/tmp/mlx_cache',
      hardware_capability: 'mlx_apple_silicon',
      memory_usage: { active_mb: 512, peak_mb: 1024, rss_mb: 800 },
    },
    storeStats: {
      db_path: '~/.finsight/lancedb',
      total_documents: 3,
      total_pages: 15,
      disk_size_bytes: 1048576,
      vector_dimension: 128,
    },
    isLoading: false,
    error: null,
    saveState: 'idle',
    saveMessage: null,
    loadSettings: mockLoadSettings,
    saveCloudKey: mockSaveCloudKey,
    startMlxDownload: mockStartMlxDownload,
  }),
}));

describe('SettingsDialog Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render when isOpen is false', () => {
    const { container } = render(<SettingsDialog isOpen={false} onClose={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders modal dialog with tabs when isOpen is true', () => {
    render(<SettingsDialog isOpen={true} onClose={() => {}} />);
    expect(screen.getByRole('dialog', { name: /FinTrace Settings/i })).toBeDefined();
    expect(screen.getByText('Cài đặt & Cấu hình FinTrace')).toBeDefined();
    expect(screen.getByText('Chế độ suy luận')).toBeDefined();
    expect(screen.getByText('Cloud BYOK')).toBeDefined();
    expect(screen.getByText('Local Apple Silicon')).toBeDefined();
    expect(screen.getByText('Lưu trữ LanceDB')).toBeDefined();
  });

  it('allows switching inference mode', () => {
    render(<SettingsDialog isOpen={true} onClose={() => {}} />);
    const localRadio = screen.getByLabelText(/Local Engine/i);
    fireEvent.click(localRadio);
    expect(mockSetInferenceMode).toHaveBeenCalledWith('local');
  });

  it('navigates to Cloud BYOK tab and supports key entry with masking', async () => {
    render(<SettingsDialog isOpen={true} onClose={() => {}} />);
    const cloudTab = screen.getByText('Cloud BYOK');
    await act(async () => {
      fireEvent.click(cloudTab);
    });

    // Verify Zero-Leak notice
    expect(screen.getByText(/Chính sách Zero-Leak Security/i)).toBeDefined();

    const keyInput = screen.getByPlaceholderText(/Nhập API key bí mật.../i) as HTMLInputElement;
    expect(keyInput.type).toBe('password');

    // Toggle reveal
    const toggleBtn = screen.getByLabelText(/Hiển thị khóa API/i);
    await act(async () => {
      fireEvent.click(toggleBtn);
    });
    expect(keyInput.type).toBe('text');

    // Type key and save
    await act(async () => {
      fireEvent.change(keyInput, { target: { value: 'sk-ant-test-super-secret' } });
      const saveBtn = screen.getByText('Lưu khóa BYOK');
      fireEvent.click(saveBtn);
    });

    expect(mockSaveCloudKey).toHaveBeenCalledWith('anthropic', 'sk-ant-test-super-secret', undefined);
  });

  it('enforces AGENTS.md Rule 15: Zero raw emojis in rendered output', () => {
    const { container } = render(<SettingsDialog isOpen={true} onClose={() => {}} />);
    const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(container.innerHTML)).toBe(false);
  });
});
