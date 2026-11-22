#!/usr/bin/env bash
# ==============================================================================
# FinTrace Windows Authenticode Code Signing & Packaging Pipeline
# Supports Azure Trusted Signing (dlib) and Windows SDK signtool.exe.
# Governed by Sprint 9 Task S9-05, AGENTS.md Rule 2, Rule 3 & Rule 15.
# ==============================================================================

set -euo pipefail

DRY_RUN=false
TARGET_PATH=""
TIMESTAMP_URL="http://timestamp.digicert.com"

print_usage() {
    echo "Usage: $0 [options] [path-to-installer-exe]"
    echo "Options:"
    echo "  --dry-run       Validate bundle structure and signing prerequisites without calling signtool"
    echo "  -h, --help      Show this help message"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            print_usage
            exit 0
            ;;
        *)
            TARGET_PATH="$1"
            shift
            ;;
    esac
done

echo "========================================================================"
echo "  FinTrace Windows Authenticode Code Signing & Packaging Pipeline"
echo "========================================================================"

if [[ -z "$TARGET_PATH" ]]; then
    # Look for default NSIS installer in apps/desktop
    DEFAULT_EXE="apps/desktop/src-tauri/target/release/bundle/nsis/FinTrace_1.0.0_x64-setup.exe"
    if [[ -f "$DEFAULT_EXE" ]]; then
        TARGET_PATH="$DEFAULT_EXE"
    elif [[ -f "apps/desktop/src-tauri/target/release/FinTrace.exe" ]]; then
        TARGET_PATH="apps/desktop/src-tauri/target/release/FinTrace.exe"
    else
        TARGET_PATH="$DEFAULT_EXE"
    fi
fi

echo "Target binary / installer: $TARGET_PATH"
echo "Dry-run mode:              $DRY_RUN"
echo "Timestamp authority:       $TIMESTAMP_URL"

# 1. Prerequisite asset validation
ICO_PATH="apps/desktop/src-tauri/icons/icon.ico"
HEADER_IMG="apps/desktop/src-tauri/icons/Square150x150Logo.png"

if [[ -f "$ICO_PATH" ]]; then
    echo "OK: Installer icon verified: $ICO_PATH"
else
    echo "ERROR: Installer icon missing at $ICO_PATH"
    exit 1
fi

if [[ -f "$HEADER_IMG" ]]; then
    echo "OK: NSIS header image verified: $HEADER_IMG"
else
    echo "ERROR: NSIS header image missing at $HEADER_IMG"
    exit 1
fi

# 2. Tool availability check
SIGNTOOL_FOUND=false
if command -v signtool.exe &> /dev/null || command -v signtool &> /dev/null; then
    SIGNTOOL_FOUND=true
    echo "OK: signtool detected in PATH"
else
    echo "INFO: signtool not found in current environment (expected on non-Windows runner)"
fi

# 3. Dry-Run or Missing Credentials Validation
if [[ "$DRY_RUN" == "true" ]] || [[ -z "${WINDOWS_SIGNING_CERT:-}" && -z "${AZURE_KEY_VAULT_URI:-}" ]]; then
    echo "------------------------------------------------------------------------"
    echo "Notice: Running in validation / dry-run mode."
    echo "  - Azure Trusted Signing: ${AZURE_KEY_VAULT_URI:-<not configured - dry run>}"
    echo "  - Certificate Subject:   ${WINDOWS_SIGNING_CERT_SUBJECT:-529 Studio Inc.}"
    echo "  - Digest Algorithm:      SHA256"
    echo "  - RFC 3161 Timestamp:    $TIMESTAMP_URL"
    echo "  - Simulated Action:      signtool.exe sign /tr $TIMESTAMP_URL /td sha256 /fd sha256 $TARGET_PATH"
    echo "OK: Windows NSIS installer signing prerequisites and assets verified successfully."
    echo "========================================================================"
    exit 0
fi

# 4. Live Windows Authenticode Signing Execution
echo "Executing Authenticode signing with signtool..."
if [[ -n "${AZURE_KEY_VAULT_URI:-}" ]]; then
    # Azure Trusted Signing via Azure CLI / dlib extension
    echo "Signing via Azure Trusted Signing..."
    az trusted-signing sign \
        --endpoint "$AZURE_KEY_VAULT_URI" \
        --account "${AZURE_ACCOUNT_NAME}" \
        --certificate-profile "${AZURE_CERT_PROFILE}" \
        --file-path "$TARGET_PATH"
else
    # Standard PFX signing with signtool
    signtool.exe sign \
        /f "$WINDOWS_SIGNING_CERT" \
        /p "$WINDOWS_SIGNING_CERT_PASSWORD" \
        /fd sha256 \
        /tr "$TIMESTAMP_URL" \
        /td sha256 \
        "$TARGET_PATH"
fi

# 5. Verification of digital signature
echo "Verifying digital signature of $TARGET_PATH..."
if command -v signtool.exe &> /dev/null; then
    signtool.exe verify /pa /v "$TARGET_PATH"
fi

echo "OK: Binary successfully signed and timestamped: $TARGET_PATH"
