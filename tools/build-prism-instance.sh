#!/usr/bin/env bash
# Build the friend-facing auto-updating Prism instance zip.
# Usage: PACK_URL=https://<user>.github.io/<repo>/pack.toml ./tools/build-prism-instance.sh
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
: "${PACK_URL:?Set PACK_URL to the hosted pack.toml URL (GitHub Pages) before building}"
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
STAGE=dist/prism-instance
ZIP=dist/AFTERLIGHT-prism-instance.zip
rm -rf "$STAGE" && mkdir -p "$STAGE/.minecraft"

curl -sfL -o "$STAGE/.minecraft/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL" \
  || { echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)"; exit 3; }

cat > "$STAGE/instance.cfg" <<CFG
InstanceType=OneSix
name=AFTERLIGHT
iconKey=default
OverrideCommands=true
PreLaunchCommand="\$INST_JAVA" -jar packwiz-installer-bootstrap.jar ${PACK_URL}
CFG

cat > "$STAGE/mmc-pack.json" <<JSON
{
  "components": [
    { "uid": "net.minecraft", "version": "${MC_VERSION}", "important": true },
    { "uid": "net.neoforged", "version": "${NEOFORGE_VERSION}" }
  ],
  "formatVersion": 1
}
JSON

# Start from a clean archive. `zip -r` otherwise updates an existing zip in place,
# which would let a stale entry from a previous build survive a rebuild.
rm -f "$ZIP"
(cd "$STAGE" && zip -qr "../$(basename "$ZIP")" .)
echo "Built $ZIP (pack URL: ${PACK_URL})"
