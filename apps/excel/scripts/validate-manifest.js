#!/usr/bin/env node
/**
 * Automated Manifest Validator for FinTrace Excel Add-in
 * Governed by 529 Engineering Standards:
 * - Evidence Before Assertions (Hardened DoD)
 * - Microsoft 365 AppSource Compliance
 */

import { existsSync, readFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootExcelDir = resolve(__dirname, '..');

const manifestsToValidate = process.argv.slice(2).length > 0
  ? process.argv.slice(2)
  : [
      resolve(rootExcelDir, 'manifest.appsource.xml'),
      resolve(rootExcelDir, 'manifest.prod.xml'),
      resolve(rootExcelDir, 'manifest.xml'),
    ];

console.log('=== FinTrace Microsoft Office Add-in Manifest Validator ===\n');

let totalErrors = 0;

for (const manifestPath of manifestsToValidate) {
  const relPath = manifestPath.replace(rootExcelDir + '/', '');
  console.log(`Checking manifest: ${relPath}`);

  if (!existsSync(manifestPath)) {
    console.error(`  [FAIL] Manifest file does not exist: ${manifestPath}`);
    totalErrors++;
    continue;
  }

  const content = readFileSync(manifestPath, 'utf8');

  // 1. Basic XML structure checks
  const requiredTags = [
    '<OfficeApp',
    '<Id>',
    '<Version>',
    '<ProviderName>',
    '<DefaultLocale>',
    '<DisplayName',
    '<Description',
    '<IconUrl',
    '<HighResolutionIconUrl',
    '<SupportUrl',
    '<AppDomains>',
    '<Hosts>',
    '<DefaultSettings>',
    '<Permissions>',
  ];

  let missingTags = 0;
  for (const tag of requiredTags) {
    if (!content.includes(tag)) {
      console.error(`  [FAIL] Missing required XML element: ${tag}`);
      missingTags++;
    }
  }

  if (missingTags > 0) {
    totalErrors += missingTags;
    continue;
  }

  // 2. Security validation: No unencrypted HTTP endpoints in production
  if (manifestPath.includes('.prod.') || manifestPath.includes('.appsource.')) {
    // Extract actual endpoint and resource values inside tags, ignoring XML namespaces
    const urlMatches = content.match(/<(SourceLocation|IconUrl|HighResolutionIconUrl|SupportUrl|AppDomain)[^>]*DefaultValue="([^"]+)"|<AppDomain>([^<]+)<\/AppDomain>/g) || [];
    let foundInsecure = false;
    for (const match of urlMatches) {
      if (match.includes('http://') && !match.includes('localhost') && !match.includes('127.0.0.1')) {
        console.error(`  [FAIL] Insecure HTTP URL detected: ${match}`);
        foundInsecure = true;
      }
    }
    if (foundInsecure) {
      totalErrors++;
      continue;
    }
  }

  // 3. Provider and Branding Checks
  if (!content.includes('<ProviderName>529 Studio</ProviderName>')) {
    console.error(`  [FAIL] Invalid ProviderName. Expected '529 Studio'.`);
    totalErrors++;
  }

  if (!content.includes('FinTrace')) {
    console.error(`  [FAIL] Brand name 'FinTrace' missing in manifest.`);
    totalErrors++;
  }

  // 4. Run official office-addin-manifest CLI validator
  try {
    const cmd = `npx --yes office-addin-manifest validate "${manifestPath}"`;
    const output = execSync(cmd, { encoding: 'utf8', stdio: ['pipe', 'pipe', 'pipe'] });
    if (output.includes('The manifest is valid.')) {
      console.log(`  [PASS] office-addin-manifest validation succeeded.`);
    } else {
      console.warn(`  [WARN] Output did not contain explicit success string:\n${output}`);
    }
  } catch (err) {
    console.error(`  [FAIL] office-addin-manifest validation failed:\n${err.stdout || err.message}`);
    totalErrors++;
  }

  console.log(`  [OK] ${relPath} passed checks.\n`);
}

// 5. Asset presence checks
console.log('Checking AppSource required brand assets...');
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
  if (!existsSync(assetPath)) {
    console.error(`  [FAIL] Required brand asset missing: ${asset}`);
    totalErrors++;
  } else {
    console.log(`  [PASS] ${asset} present.`);
  }
}

console.log('\n===========================================================');
if (totalErrors === 0) {
  console.log('ALL MANIFESTS & BRAND ASSETS VALIDATED SUCCESSFULLY (0 errors).');
  process.exit(0);
} else {
  console.error(`VALIDATION FAILED WITH ${totalErrors} ERROR(S).`);
  process.exit(1);
}
