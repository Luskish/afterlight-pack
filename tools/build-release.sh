#!/usr/bin/env bash
# Build and classify the complete AFTERLIGHT friend release.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

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

validate_release_entries() {
  local directory=$1
  local entry entry_name
  local entries=()
  shopt -s dotglob nullglob
  entries=("$directory"/*)
  shopt -u dotglob nullglob
  for entry in "${entries[@]}"; do
    entry_name=${entry##*/}
    case "$entry_name" in
      "$PRISM_NAME"|"$METADATA_NAME"|"$CHECKSUMS_NAME"|"$MRPACK_NAME"|"$CURSEFORGE_NAME")
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

OUTPUT="$PRISM_ZIP" PACK_URL="$PACK_URL" ./tools/build-prism-instance.sh

DIST_DIR="$STAGING_DIR" ./tools/export.sh

python3 tools/release_artifacts.py inspect-friends --archive "$MRPACK"
python3 tools/release_artifacts.py inspect-friends --archive "$CURSEFORGE_ZIP"

python3 tools/release_artifacts.py write-metadata \
  --dist-dir "$STAGING_DIR" \
  --version "$VERSION" \
  --git-sha "$GIT_SHA" \
  --minecraft "$MC_VERSION" \
  --neoforge "$NEOFORGE_VERSION" \
  --pack-url "$PACK_URL"

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
  "$DIST_DIR/$PRISM_NAME" \
  "$DIST_DIR/$METADATA_NAME" \
  "$DIST_DIR/$CHECKSUMS_NAME"
echo "FRIENDS-ONLY:"
printf '  %s\n' "$DIST_DIR/$MRPACK_NAME" "$DIST_DIR/$CURSEFORGE_NAME"
