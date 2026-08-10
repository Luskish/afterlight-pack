#!/usr/bin/env bash
# Build and classify the complete AFTERLIGHT friend release.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

DIST_DIR=${DIST_DIR:-dist}
GIT_SHA=${GIT_SHA:-$(git rev-parse HEAD)}
PACK_URL=${PACK_URL:-https://luskish.github.io/afterlight-pack/pack.toml}
VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')

PRISM_ZIP="$DIST_DIR/AFTERLIGHT-prism-instance.zip"
METADATA="$DIST_DIR/release-metadata.json"
CHECKSUMS="$DIST_DIR/SHA256SUMS"
MRPACK="$DIST_DIR/AFTERLIGHT-${VERSION}.mrpack"
CURSEFORGE_ZIP="$DIST_DIR/AFTERLIGHT-${VERSION}-curseforge.zip"

python3 tools/release_artifacts.py scan-repository --root .

mkdir -p "$DIST_DIR"
rm -f -- "$PRISM_ZIP" "$METADATA" "$CHECKSUMS" "$MRPACK" "$CURSEFORGE_ZIP"

OUTPUT="$PRISM_ZIP" PACK_URL="$PACK_URL" ./tools/build-prism-instance.sh

DIST_DIR="$DIST_DIR" ./tools/export.sh

python3 tools/release_artifacts.py inspect-friends --archive "$MRPACK"
python3 tools/release_artifacts.py inspect-friends --archive "$CURSEFORGE_ZIP"

python3 tools/release_artifacts.py write-metadata \
  --dist-dir "$DIST_DIR" \
  --version "$VERSION" \
  --git-sha "$GIT_SHA" \
  --minecraft "$MC_VERSION" \
  --neoforge "$NEOFORGE_VERSION" \
  --pack-url "$PACK_URL"

python3 tools/release_artifacts.py write-checksums --dist-dir "$DIST_DIR"

echo "PUBLIC:"
printf '  %s\n' "$PRISM_ZIP" "$METADATA" "$CHECKSUMS"
echo "FRIENDS-ONLY:"
printf '  %s\n' "$MRPACK" "$CURSEFORGE_ZIP"
