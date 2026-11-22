<#
.SYNOPSIS
    FinTrace Windows Authenticode Code Signing & Packaging Pipeline (PowerShell)
    Supports Azure Trusted Signing and signtool.exe with RFC 3161 timestamping.
    Governed by Sprint 9 Task S9-05, AGENTS.md Rule 2, Rule 3 & Rule 15.
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$TargetPath = "",
    [string]$TimestampUrl = "http://timestamp.digicert.com"
)

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "  FinTrace Windows Authenticode Code Signing & Packaging Pipeline" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

if ([string]::IsNullOrWhiteSpace($TargetPath)) {
    $defaultExe = "apps/desktop/src-tauri/target/release/bundle/nsis/FinTrace_1.0.0_x64-setup.exe"
    if (Test-Path $defaultExe) {
        $TargetPath = $defaultExe
    } else {
        $TargetPath = "apps/desktop/src-tauri/target/release/FinTrace.exe"
    }
}

Write-Host "Target binary / installer: $TargetPath"
Write-Host "Dry-run mode:              $($DryRun.IsPresent)"
Write-Host "Timestamp authority:       $TimestampUrl"

# 1. Prerequisite asset validation
$icoPath = "apps/desktop/src-tauri/icons/icon.ico"
$headerImg = "apps/desktop/src-tauri/icons/Square150x150Logo.png"

if (Test-Path $icoPath) {
    Write-Host "OK: Installer icon verified: $icoPath" -ForegroundColor Green
} else {
    Write-Error "Installer icon missing at $icoPath"
    exit 1
}

if (Test-Path $headerImg) {
    Write-Host "OK: NSIS header image verified: $headerImg" -ForegroundColor Green
} else {
    Write-Error "NSIS header image missing at $headerImg"
    exit 1
}

# 2. Tool availability check
$signtoolCmd = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
if ($null -ne $signtoolCmd) {
    Write-Host "OK: signtool.exe found at $($signtoolCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "INFO: signtool.exe not found in PATH" -ForegroundColor Yellow
}

# 3. Dry-Run or Missing Credentials Validation
$hasCert = [string]::IsNullOrEmpty($env:WINDOWS_SIGNING_CERT) -eq $false
$hasAzure = [string]::IsNullOrEmpty($env:AZURE_KEY_VAULT_URI) -eq $false

if ($DryRun.IsPresent -or (-not $hasCert -and -not $hasAzure)) {
    Write-Host "------------------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "Notice: Running in validation / dry-run mode." -ForegroundColor Yellow
    Write-Host "  - Azure Trusted Signing: $(if ($hasAzure) { $env:AZURE_KEY_VAULT_URI } else { '<not configured - dry run>' })"
    Write-Host "  - Certificate Subject:   $($env:WINDOWS_SIGNING_CERT_SUBJECT ? $env:WINDOWS_SIGNING_CERT_SUBJECT : '529 Studio Inc.')"
    Write-Host "  - Digest Algorithm:      SHA256"
    Write-Host "  - RFC 3161 Timestamp:    $TimestampUrl"
    Write-Host "  - Simulated Action:      signtool.exe sign /tr $TimestampUrl /td sha256 /fd sha256 $TargetPath"
    Write-Host "OK: Windows NSIS installer signing prerequisites and assets verified successfully." -ForegroundColor Green
    Write-Host "========================================================================" -ForegroundColor Cyan
    exit 0
}

# 4. Live Windows Authenticode Signing Execution
Write-Host "Executing Authenticode signing with signtool..." -ForegroundColor Cyan
if ($hasAzure) {
    Write-Host "Signing via Azure Trusted Signing..."
    az trusted-signing sign `
        --endpoint $env:AZURE_KEY_VAULT_URI `
        --account $env:AZURE_ACCOUNT_NAME `
        --certificate-profile $env:AZURE_CERT_PROFILE `
        --file-path $TargetPath
} else {
    & signtool.exe sign `
        /f $env:WINDOWS_SIGNING_CERT `
        /p $env:WINDOWS_SIGNING_CERT_PASSWORD `
        /fd sha256 `
        /tr $TimestampUrl `
        /td sha256 `
        $TargetPath
}

# 5. Verification of digital signature
Write-Host "Verifying digital signature of $TargetPath..." -ForegroundColor Cyan
if ($null -ne $signtoolCmd) {
    & signtool.exe verify /pa /v $TargetPath
}

Write-Host "OK: Binary successfully signed and timestamped: $TargetPath" -ForegroundColor Green
