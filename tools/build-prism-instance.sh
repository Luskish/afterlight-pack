#!/usr/bin/env bash
# Build the friend-facing auto-updating Prism instance zip.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env

BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v${PACKWIZ_BOOTSTRAP_VERSION}/packwiz-installer-bootstrap.jar"
PACK_URL=${PACK_URL:-https://luskish.github.io/afterlight-pack/pack.toml}
OUTPUT=${OUTPUT:-dist/AFTERLIGHT-prism-instance.zip}

mkdir -p "$(dirname "$OUTPUT")"
rm -f "$OUTPUT"
BOOTSTRAP_PATH=$(mktemp)
trap 'rm -f "$BOOTSTRAP_PATH"' EXIT

curl --fail --location --silent --show-error \
  --output "$BOOTSTRAP_PATH" \
  "$BOOTSTRAP_URL" \
  || { echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)" >&2; exit 3; }

if command -v shasum >/dev/null 2>&1; then
  BOOTSTRAP_DIGEST=$(shasum -a 256 "$BOOTSTRAP_PATH")
elif command -v sha256sum >/dev/null 2>&1; then
  BOOTSTRAP_DIGEST=$(sha256sum "$BOOTSTRAP_PATH")
else
  echo "FAIL: shasum or sha256sum is required" >&2
  exit 4
fi
BOOTSTRAP_DIGEST=${BOOTSTRAP_DIGEST%% *}

if [ "$BOOTSTRAP_DIGEST" != "$PACKWIZ_BOOTSTRAP_SHA256" ]; then
  echo "FAIL: packwiz bootstrap SHA-256 mismatch" >&2
  echo "expected: $PACKWIZ_BOOTSTRAP_SHA256" >&2
  echo "actual:   $BOOTSTRAP_DIGEST" >&2
  exit 4
fi

python3 tools/release_artifacts.py build-prism \
  --bootstrap "$BOOTSTRAP_PATH" \
  --output "$OUTPUT" \
  --pack-url "$PACK_URL" \
  --minecraft-version "$MC_VERSION" \
  --neoforge-version "$NEOFORGE_VERSION"

python3 tools/release_artifacts.py inspect-prism \
  --archive "$OUTPUT" \
  --pack-url "$PACK_URL" \
  --bootstrap-sha256 "$PACKWIZ_BOOTSTRAP_SHA256"

echo "Built $OUTPUT (pack URL: $PACK_URL)"
