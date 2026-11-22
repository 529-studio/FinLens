import { describe, it, expect } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';

describe('Tauri v2 Production Code Signing & Hardened Runtime Configuration', () => {
  const tauriDir = path.resolve(__dirname, '../../../src-tauri');
  const tauriConfPath = path.join(tauriDir, 'tauri.conf.json');
  const entitlementsPath = path.join(tauriDir, 'entitlements.plist');
  const scriptsDir = path.resolve(__dirname, '../../../../../scripts');
  const notarizeScriptPath = path.join(scriptsDir, 'notarize-macos.sh');
  const winSignShPath = path.join(scriptsDir, 'sign-windows.sh');
  const winSignPsPath = path.join(scriptsDir, 'sign-windows.ps1');

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

  it('tauri.conf.json has NSIS bundle target and Windows signing configuration', () => {
    const content = JSON.parse(fs.readFileSync(tauriConfPath, 'utf-8'));
    
    expect(content.bundle.targets).toContain('nsis');
    expect(content.bundle.windows).toBeDefined();
    expect(content.bundle.windows.digestAlgorithm).toBe('sha256');
    expect(content.bundle.windows.timestampUrl).toContain('timestamp.digicert.com');
    expect(content.bundle.windows.nsis).toBeDefined();
    expect(content.bundle.windows.nsis.installerIcon).toBe('icons/icon.ico');
    expect(content.bundle.windows.nsis.headerImage).toBe('icons/Square150x150Logo.png');
    expect(content.bundle.windows.nsis.installMode).toBe('currentUser');
    expect(content.bundle.windows.nsis.displayLanguageSelector).toBe(false);
  });

  it('scripts/sign-windows.sh exists, is executable, and supports --dry-run', () => {
    expect(fs.existsSync(winSignShPath)).toBe(true);
    const stats = fs.statSync(winSignShPath);
    expect((stats.mode & 0o111) !== 0).toBe(true);

    const content = fs.readFileSync(winSignShPath, 'utf-8');
    expect(content).toContain('signtool');
    expect(content).toContain('--dry-run');
    expect(content).toContain('timestamp.digicert.com');
  });

  it('scripts/sign-windows.ps1 exists and supports -DryRun', () => {
    expect(fs.existsSync(winSignPsPath)).toBe(true);
    const content = fs.readFileSync(winSignPsPath, 'utf-8');
    expect(content).toContain('signtool');
    expect(content).toContain('DryRun');
    expect(content).toContain('timestamp.digicert.com');
  });

  it('strictly complies with Rule 15: Zero raw Unicode emojis in signing configurations and scripts', () => {
    const filesToCheck = [tauriConfPath, winSignShPath, winSignPsPath];
    const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u;

    for (const filePath of filesToCheck) {
      const content = fs.readFileSync(filePath, 'utf-8');
      expect(emojiRegex.test(content)).toBe(false);
    }
  });
});
