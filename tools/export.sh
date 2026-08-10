#!/usr/bin/env bash
# Export AFTERLIGHT distribution artifacts from the packwiz source.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
[ -n "${PATH_EXTRA:-}" ] && export PATH="$PATH_EXTRA:$PATH"
VERSION=$(grep '^version' pack.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
DIST_DIR=${DIST_DIR:-dist}
MRPACK="$DIST_DIR/AFTERLIGHT-${VERSION}.mrpack"
CURSEFORGE_ZIP="$DIST_DIR/AFTERLIGHT-${VERSION}-curseforge.zip"
mkdir -p "$DIST_DIR"
rm -f -- "$MRPACK" "$CURSEFORGE_ZIP"
packwiz refresh
packwiz mr export -o "$MRPACK"
packwiz cf export -o "$CURSEFORGE_ZIP"
echo "FRIENDS-ONLY artifacts:"
printf '  %s\n' "$MRPACK" "$CURSEFORGE_ZIP"
