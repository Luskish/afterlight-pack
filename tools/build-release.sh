#!/usr/bin/env bash
# Build and classify the complete AFTERLIGHT public release.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

APPROVED_PACKWIZ_BOOTSTRAP_VERSION=0.0.3
APPROVED_PACKWIZ_BOOTSTRAP_SIZE=98989
APPROVED_PACKWIZ_BOOTSTRAP_SHA256=a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c
APPROVED_PACKWIZ_INSTALLER_VERSION=0.5.14
APPROVED_PACKWIZ_INSTALLER_SIZE=4378828
APPROVED_PACKWIZ_INSTALLER_SHA256=c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598
if [ "$PACKWIZ_BOOTSTRAP_VERSION" != "$APPROVED_PACKWIZ_BOOTSTRAP_VERSION" ] ||
  [ "$PACKWIZ_BOOTSTRAP_SIZE" != "$APPROVED_PACKWIZ_BOOTSTRAP_SIZE" ] ||
  [ "$PACKWIZ_BOOTSTRAP_SHA256" != "$APPROVED_PACKWIZ_BOOTSTRAP_SHA256" ] ||
  [ "$PACKWIZ_INSTALLER_VERSION" != "$APPROVED_PACKWIZ_INSTALLER_VERSION" ] ||
  [ "$PACKWIZ_INSTALLER_SIZE" != "$APPROVED_PACKWIZ_INSTALLER_SIZE" ] ||
  [ "$PACKWIZ_INSTALLER_SHA256" != "$APPROVED_PACKWIZ_INSTALLER_SHA256" ]; then
  echo "FAIL: release builds require the approved Packwiz installer pins" >&2
  exit 2
fi

DIST_DIR=${DIST_DIR:-dist}
GIT_SHA=${GIT_SHA:-$(git rev-parse HEAD)}
if [ "${PACK_URL+x}" = x ]; then
  echo "FAIL: PACK_URL override is not allowed for release builds" >&2
  exit 2
fi
PACK_URL=https://luskish.github.io/afterlight-pack/pack.toml
VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
PRISM_NAME=AFTERLIGHT-prism-instance.zip
METADATA_NAME=release-metadata.json
CHECKSUMS_NAME=SHA256SUMS
MRPACK_NAME="AFTERLIGHT-${VERSION}.mrpack"
CURSEFORGE_NAME="AFTERLIGHT-${VERSION}-curseforge.zip"
PUBLIC_MRPACK_NAME=AFTERLIGHT.mrpack
PUBLIC_CURSEFORGE_NAME=AFTERLIGHT-curseforge.zip

validate_release_entries() {
  local directory=$1
  local entry entry_name
  local entries=()
  shopt -s dotglob nullglob
  entries=("$directory"/*)
  shopt -u dotglob nullglob
  if ((${#entries[@]})); then
    for entry in "${entries[@]}"; do
      entry_name=${entry##*/}
      case "$entry_name" in
        "$PRISM_NAME"|"$PUBLIC_MRPACK_NAME"|"$PUBLIC_CURSEFORGE_NAME"|"$METADATA_NAME"|"$CHECKSUMS_NAME")
          ;;
        *)
          echo "FAIL: unclassified release output entry: $entry" >&2
          return 2
          ;;
      esac
      if [ -L "$entry" ] || [ ! -f "$entry" ]; then
        echo "FAIL: nonregular release output entry: $entry" >&2
        return 2
      fi
    done
  fi
}

if [ -L "$DIST_DIR" ]; then
  echo "FAIL: release output directory is a symlink: $DIST_DIR" >&2
  exit 2
fi
if [ -e "$DIST_DIR" ] && [ ! -d "$DIST_DIR" ]; then
  echo "FAIL: release output path is not a directory: $DIST_DIR" >&2
  exit 2
fi

DIST_PARENT=$(dirname "$DIST_DIR")
DIST_NAME=$(basename "$DIST_DIR")
if [ "$DIST_NAME" = "." ] || [ "$DIST_NAME" = ".." ] || [ "$DIST_NAME" = "/" ]; then
  echo "FAIL: release output directory is unsafe: $DIST_DIR" >&2
  exit 2
fi
mkdir -p "$DIST_PARENT"
if [ -L "$DIST_DIR" ]; then
  echo "FAIL: release output directory is a symlink: $DIST_DIR" >&2
  exit 2
fi
if [ -e "$DIST_DIR" ]; then
  validate_release_entries "$DIST_DIR"
fi

python3 tools/release_artifacts.py scan-repository --root .

STAGING_DIR=$(mktemp -d "$DIST_PARENT/.${DIST_NAME}.staging.XXXXXX")
BACKUP_DIR=""
cleanup() {
  if [ -n "$STAGING_DIR" ] && [ -d "$STAGING_DIR" ] && [ ! -L "$STAGING_DIR" ]; then
    rm -rf -- "$STAGING_DIR"
  fi
  if [ -n "$BACKUP_DIR" ] && [ -e "$BACKUP_DIR" ] && [ ! -e "$DIST_DIR" ]; then
    mv "$BACKUP_DIR" "$DIST_DIR"
  fi
}
trap cleanup EXIT

PRISM_ZIP="$STAGING_DIR/$PRISM_NAME"
MRPACK="$STAGING_DIR/$MRPACK_NAME"
CURSEFORGE_ZIP="$STAGING_DIR/$CURSEFORGE_NAME"

DIST_DIR="$STAGING_DIR" ./tools/export.sh >/dev/null

OUTPUT="$PRISM_ZIP" PACK_URL="$PACK_URL" ./tools/build-prism-instance.sh

python3 tools/release_artifacts.py inspect-public-launcher --archive "$MRPACK"
python3 tools/release_artifacts.py inspect-public-launcher --archive "$CURSEFORGE_ZIP"
mv "$MRPACK" "$STAGING_DIR/$PUBLIC_MRPACK_NAME"
mv "$CURSEFORGE_ZIP" "$STAGING_DIR/$PUBLIC_CURSEFORGE_NAME"

python3 tools/release_artifacts.py write-metadata \
  --dist-dir "$STAGING_DIR" \
  --version "$VERSION" \
  --git-sha "$GIT_SHA" \
  --minecraft "$MC_VERSION" \
  --neoforge "$NEOFORGE_VERSION" \
  --pack-url "$PACK_URL" \
  --bootstrap-version "$PACKWIZ_BOOTSTRAP_VERSION" \
  --bootstrap-size "$PACKWIZ_BOOTSTRAP_SIZE" \
  --bootstrap-sha256 "$PACKWIZ_BOOTSTRAP_SHA256" \
  --installer-version "$PACKWIZ_INSTALLER_VERSION" \
  --installer-size "$PACKWIZ_INSTALLER_SIZE" \
  --installer-sha256 "$PACKWIZ_INSTALLER_SHA256"

python3 tools/release_artifacts.py write-checksums --dist-dir "$STAGING_DIR"

if [ -L "$DIST_DIR" ]; then
  echo "FAIL: release output directory became a symlink: $DIST_DIR" >&2
  exit 2
fi
if [ -e "$DIST_DIR" ]; then
  if [ ! -d "$DIST_DIR" ]; then
    echo "FAIL: release output path is not a directory: $DIST_DIR" >&2
    exit 2
  fi
  validate_release_entries "$DIST_DIR"
  BACKUP_DIR=$(mktemp -d "$DIST_PARENT/.${DIST_NAME}.previous.XXXXXX")
  rmdir "$BACKUP_DIR"
  mv "$DIST_DIR" "$BACKUP_DIR"
  if ! validate_release_entries "$BACKUP_DIR"; then
    mv "$BACKUP_DIR" "$DIST_DIR"
    BACKUP_DIR=""
    exit 2
  fi
fi
if ! mv "$STAGING_DIR" "$DIST_DIR"; then
  if [ -n "$BACKUP_DIR" ] && [ -e "$BACKUP_DIR" ]; then
    mv "$BACKUP_DIR" "$DIST_DIR"
    BACKUP_DIR=""
  fi
  echo "FAIL: could not promote validated release output" >&2
  exit 2
fi
STAGING_DIR=""
if [ -n "$BACKUP_DIR" ]; then
  rm -rf -- "$BACKUP_DIR"
  BACKUP_DIR=""
fi

echo "PUBLIC:"
printf '  %s\n' \
  "$DIST_DIR/$PUBLIC_CURSEFORGE_NAME" \
  "$DIST_DIR/$PRISM_NAME" \
  "$DIST_DIR/$PUBLIC_MRPACK_NAME" \
  "$DIST_DIR/$METADATA_NAME" \
  "$DIST_DIR/$CHECKSUMS_NAME"
