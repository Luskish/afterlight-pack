#!/usr/bin/env bash
# Export AFTERLIGHT distribution artifacts from the packwiz source.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
[ -n "${PATH_EXTRA:-}" ] && export PATH="$PATH_EXTRA:$PATH"
VERSION=$(grep '^version' pack.toml | head -1 | sed 's/.*"\(.*\)"/\1/')
mkdir -p dist
packwiz refresh
packwiz mr export -o "dist/AFTERLIGHT-${VERSION}.mrpack"
packwiz cf export -o "dist/AFTERLIGHT-${VERSION}-curseforge.zip"
echo "Artifacts:"
ls -lh dist/
