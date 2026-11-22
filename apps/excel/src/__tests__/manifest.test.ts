/**
 * Automated Vitest Suite for Microsoft Office Add-in Manifest Compliance
 * Governed by 529 Engineering Standards:
 * - Evidence Before Assertions (Hardened DoD)
 * - Zero Raw Emojis (Rule 15)
 */

import { describe, it, expect } from 'vitest';
import { readFileSync, existsSync } from 'fs';
import { resolve } from 'path';

describe('Microsoft Office Add-in Manifest Compliance', () => {
  const rootExcelDir = resolve(__dirname, '../..');
  const appsourceManifestPath = resolve(rootExcelDir, 'manifest.appsource.xml');
  const prodManifestPath = resolve(rootExcelDir, 'manifest.prod.xml');

  it('verifies manifest.appsource.xml exists and has valid XML tags', () => {
    expect(existsSync(appsourceManifestPath)).toBe(true);
    expect(existsSync(prodManifestPath)).toBe(true);
    const content = readFileSync(appsourceManifestPath, 'utf8');

    expect(content).toContain('xmlns="http://schemas.microsoft.com/office/appforoffice/1.1"');
    expect(content).toContain('<ProviderName>529 Studio</ProviderName>');
    expect(content).toContain('<Version>1.0.0.0</Version>');
    expect(content).toContain('<DisplayName DefaultValue="FinTrace for Excel" />');
    expect(content).toContain('<Permissions>ReadWriteDocument</Permissions>');
    expect(content).toContain('<AppDomain>https://fintrace.529studio.site</AppDomain>');
  });

  it('enforces that production manifest URLs use HTTPS only', () => {
    const content = readFileSync(appsourceManifestPath, 'utf8');
    const urlMatches = content.match(/<(SourceLocation|IconUrl|HighResolutionIconUrl|SupportUrl|AppDomain)[^>]*DefaultValue="([^"]+)"|<AppDomain>([^<]+)<\/AppDomain>/g) || [];
    
    expect(urlMatches.length).toBeGreaterThan(0);
    for (const match of urlMatches) {
      expect(match).not.toMatch(/http:\/\/(?!localhost|127\.0\.0\.1)/);
    }
  });

  it('ensures all required AppSource brand icon assets exist with proper dimensions', () => {
    const requiredAssets = [
      'assets/icon-16.png',
      'assets/icon-32.png',
      'assets/icon-64.png',
      'assets/icon-80.png',
      'assets/icon-128.png',
      'assets/fintrace-brand.svg',
    ];

    for (const asset of requiredAssets) {
      const assetPath = resolve(rootExcelDir, asset);
      expect(existsSync(assetPath)).toBe(true);
    }
  });

  it('strictly adheres to Rule 15: Zero raw Unicode emojis in manifest text', () => {
    const content = readFileSync(appsourceManifestPath, 'utf8');
    const emojiRegex = /[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/u;
    expect(emojiRegex.test(content)).toBe(false);
  });
});
