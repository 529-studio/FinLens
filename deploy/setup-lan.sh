#!/usr/bin/env bash
# ==============================================================================
# FinTrace Enterprise LAN Deployment Initialization Script
# Implements 529 Engineering Standard: docker-runtime-patching-and-secrets
# Automatically generates cryptographically secure secrets and validates compose setup.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.lan"
EXAMPLE_FILE="${SCRIPT_DIR}/.env.lan.example"

echo "========================================================================"
echo "  FinTrace Enterprise Banking LAN Box Setup"
echo "========================================================================"

# 1. Prerequisite tool checks
if ! command -v docker &> /dev/null; then
    echo "✗ Error: Docker is not installed or not in PATH."
    exit 1
fi

if ! docker compose version &> /dev/null; then
    echo "✗ Error: Docker Compose (v2) is not available."
    exit 1
fi

echo "✓ Docker and Docker Compose detected."

# 2. Cryptographic Secret Generation (Zero-Leak Policy)
generate_secret() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        # Fallback to /dev/urandom
        head -c 32 /dev/urandom | xxd -p -c 32
    fi
}

if [[ ! -f "$ENV_FILE" ]]; then
    echo "Generating .env.lan from template with cryptographically secure keys..."
    SECRET_KEY="$(generate_secret)"
    sed -e "s/CHANGE_ME_CRYPTOGRAPHIC_SECRET_KEY/${SECRET_KEY}/g" \
        "$EXAMPLE_FILE" > "$ENV_FILE"
    chmod 600 "$ENV_FILE"
    echo "✓ Created ${ENV_FILE} with restricted permissions (chmod 600)."
    echo "  NOTE: Please add your frontier BYOK API key (Anthropic or OpenAI) into ${ENV_FILE}."
else
    echo "✓ ${ENV_FILE} already exists. Skipping secret generation."
fi

# 3. Docker Compose Configuration Validation
echo "Validating Docker Compose configuration..."
docker compose -f "${SCRIPT_DIR}/docker-compose.yml" --env-file "$ENV_FILE" config --quiet
echo "✓ Docker Compose configuration syntax is valid."

echo "========================================================================"
echo "Setup complete! To launch FinTrace LAN Box, run:"
echo "  docker compose -f ${SCRIPT_DIR}/docker-compose.yml --env-file ${ENV_FILE} up -d --build"
echo "========================================================================"
