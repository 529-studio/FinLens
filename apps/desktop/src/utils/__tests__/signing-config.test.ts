import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Tauri v2 Production Code Signing & Hardened Runtime Configuration', () => {
  const tauriDir = path.resolve(__dirname, '../../../src-tauri');
  const tauriConfPath = path.join(tauriDir, 'tauri.conf.json');
  const entitlementsPath = path.join(tauriDir, 'entitlements.plist');
  const scriptsDir = path.resolve(__dirname, '../../../../../scripts');
  const notarizeScriptPath = path.join(scriptsDir, 'notarize-macos.sh');

  it('tauri.conf.json has hardenedRuntime and entitlements configured for macOS bundle', () => {
    expect(fs.existsSync(tauriConfPath)).toBe(true);
    const content = JSON.parse(fs.readFileSync(tauriConfPath, 'utf-8'));
    
    expect(content.bundle).toBeDefined();
    expect(content.bundle.macOS).toBeDefined();
    expect(content.bundle.macOS.hardenedRuntime).toBe(true);
    expect(content.bundle.macOS.entitlements).toBe('entitlements.plist');
    expect(content.bundle.macOS.minimumSystemVersion).toBe('12.0');
  });

  it('entitlements.plist exists and declares required hardened runtime security flags', () => {
    expect(fs.existsSync(entitlementsPath)).toBe(true);
    const plist = fs.readFileSync(entitlementsPath, 'utf-8');

    // Required entitlements for Python daemon, JIT, and local network IPC
    expect(plist).toContain('com.apple.security.cs.allow-jit');
    expect(plist).toContain('com.apple.security.cs.allow-unsigned-executable-memory');
    expect(plist).toContain('com.apple.security.network.client');
    expect(plist).toContain('com.apple.security.network.server');
    expect(plist).toContain('com.apple.security.files.user-selected.read-write');
  });

  it('scripts/notarize-macos.sh exists, is executable, and supports --dry-run', () => {
    expect(fs.existsSync(notarizeScriptPath)).toBe(true);
    const stats = fs.statSync(notarizeScriptPath);
    // Check executable bit
    expect((stats.mode & 0o111) !== 0).toBe(true);

    const scriptContent = fs.readFileSync(notarizeScriptPath, 'utf-8');
    expect(scriptContent).toContain('notarytool');
    expect(scriptContent).toContain('stapler');
    expect(scriptContent).toContain('--dry-run');
  });
});
