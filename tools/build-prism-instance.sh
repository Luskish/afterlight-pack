#!/usr/bin/env bash
# Build the friend-facing auto-updating Prism instance zip.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env

BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v${PACKWIZ_BOOTSTRAP_VERSION}/packwiz-installer-bootstrap.jar"
INSTALLER_URL="https://github.com/packwiz/packwiz-installer/releases/download/v${PACKWIZ_INSTALLER_VERSION}/packwiz-installer.jar"
PACK_URL=${PACK_URL:-https://luskish.github.io/afterlight-pack/pack.toml}
OUTPUT=${OUTPUT:-dist/AFTERLIGHT-prism-instance.zip}

mkdir -p "$(dirname "$OUTPUT")"
rm -f "$OUTPUT"
BOOTSTRAP_PATH=$(mktemp)
INSTALLER_PATH=$(mktemp)
trap 'rm -f "$BOOTSTRAP_PATH" "$INSTALLER_PATH"' EXIT

curl --fail --location --silent --show-error \
  --output "$BOOTSTRAP_PATH" \
  "$BOOTSTRAP_URL" \
  || { echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)" >&2; exit 3; }

curl --fail --location --silent --show-error \
  --output "$INSTALLER_PATH" \
  "$INSTALLER_URL" \
  || { echo "FAIL: download packwiz-installer ($INSTALLER_URL)" >&2; exit 3; }

sha256_file() {
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$1" | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$1" | awk '{print $1}'
  else
    echo "FAIL: shasum or sha256sum is required" >&2
    return 4
  fi
}

verify_download() {
  local label=$1
  local path=$2
  local expected_size=$3
  local expected_digest=$4
  local actual_size actual_digest
  actual_size=$(wc -c < "$path" | tr -d '[:space:]')
  actual_digest=$(sha256_file "$path")
  if [ "$actual_size" != "$expected_size" ]; then
    echo "FAIL: $label size mismatch" >&2
    echo "expected: $expected_size" >&2
    echo "actual:   $actual_size" >&2
    return 4
  fi
  if [ "$actual_digest" != "$expected_digest" ]; then
    echo "FAIL: $label SHA-256 mismatch" >&2
    echo "expected: $expected_digest" >&2
    echo "actual:   $actual_digest" >&2
    return 4
  fi
}

verify_download \
  "packwiz bootstrap" \
  "$BOOTSTRAP_PATH" \
  "$PACKWIZ_BOOTSTRAP_SIZE" \
  "$PACKWIZ_BOOTSTRAP_SHA256"
verify_download \
  "packwiz installer" \
  "$INSTALLER_PATH" \
  "$PACKWIZ_INSTALLER_SIZE" \
  "$PACKWIZ_INSTALLER_SHA256"

python3 tools/release_artifacts.py build-prism \
  --bootstrap "$BOOTSTRAP_PATH" \
  --installer "$INSTALLER_PATH" \
  --output "$OUTPUT" \
  --pack-url "$PACK_URL" \
  --minecraft-version "$MC_VERSION" \
  --neoforge-version "$NEOFORGE_VERSION"

python3 tools/release_artifacts.py inspect-prism \
  --archive "$OUTPUT" \
  --pack-url "$PACK_URL" \
  --bootstrap-sha256 "$PACKWIZ_BOOTSTRAP_SHA256" \
  --installer-sha256 "$PACKWIZ_INSTALLER_SHA256" \
  --installer-size "$PACKWIZ_INSTALLER_SIZE"

echo "Built $OUTPUT (pack URL: $PACK_URL)"
