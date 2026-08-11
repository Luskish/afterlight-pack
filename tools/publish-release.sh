#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

EXPECTED_ACCEPTED_ROOT=$'gauntlet-receipt.json\ngauntlet.txt\npublic'
EXPECTED_PUBLIC=$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nSHA256SUMS\nrelease-metadata.json'
TAG_MESSAGE_FILE=""

cleanup() {
  if [ -n "$TAG_MESSAGE_FILE" ]; then
    rm -f "$TAG_MESSAGE_FILE"
    TAG_MESSAGE_FILE=""
  fi
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

if [ "$#" -eq 5 ] && [ "$4" = "--prerelease" ] && [ "$5" = "--confirm" ]; then
  PRERELEASE=1
elif [ "$#" -eq 4 ] && [ "$4" = "--confirm" ]; then
  PRERELEASE=0
else
  fail "usage: $0 SHA VERSION RECEIPT_SHA256 [--prerelease] --confirm"
fi

SHA=$1
VERSION=$2
RECEIPT_SHA256=$3
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA must be exactly 40 lowercase hexadecimal characters"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]] || fail "VERSION is not a supported release version"
[[ "$RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] || fail "RECEIPT_SHA256 must be exactly 64 lowercase hexadecimal characters"
case "$VERSION" in
  *-rc.*)
    [ "$PRERELEASE" -eq 1 ] || fail "$VERSION requires --prerelease"
    ;;
  *)
    [ "$PRERELEASE" -eq 0 ] || fail "$VERSION must not use --prerelease"
    ;;
esac

[ "$(git branch --show-current)" = "dev" ] || fail "publication must run from dev"
STATUS=$(git status --porcelain --untracked-files=all)
[ -z "$STATUS" ] || fail "publication requires a clean tracked release configuration"
# shellcheck disable=SC1091
source tools/release-policy.env
CURRENT_VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
[ "$CURRENT_VERSION" = "$VERSION" ] || fail "pack.toml version does not match requested version"
ACCEPTED_VERSION=$(git show "$SHA:pack.toml" | python3 -c 'import sys,tomllib; print(tomllib.load(sys.stdin.buffer)["version"])')
[ "$ACCEPTED_VERSION" = "$VERSION" ] || fail "accepted commit version does not match requested version"

TAG="v$VERSION"
RELEASE_DOC="docs/releases/$VERSION.md"
ACCEPTED_ROOT="dist/gauntlet/$SHA"
PUBLIC_ROOT="$ACCEPTED_ROOT/public"
RECEIPT_PATH="$ACCEPTED_ROOT/gauntlet-receipt.json"

if [ ! -f "$RELEASE_DOC" ] || [ -L "$RELEASE_DOC" ]; then
  fail "release notes are missing: $RELEASE_DOC"
fi
[ "$(head -1 "$RELEASE_DOC")" = "# AFTERLIGHT $VERSION" ] || fail "release-note title does not match requested version"
grep -Fqx "## Automated Evidence" "$RELEASE_DOC" || fail "release notes lack Automated Evidence"
grep -Fqx "## Known Boundaries" "$RELEASE_DOC" || fail "release notes lack Known Boundaries"
AUTOMATED_EVIDENCE=$(sed -n '/^## Automated Evidence$/,/^## Known Boundaries$/p' "$RELEASE_DOC")
if printf '%s\n' "$AUTOMATED_EVIDENCE" | grep -Fq "NOT RUN"; then
  fail "release notes still contain automated NOT RUN evidence"
fi

if [ ! -d "$PUBLIC_ROOT" ] || [ -L "$PUBLIC_ROOT" ]; then
  fail "accepted public directory is missing"
fi
ACTUAL_ACCEPTED_ROOT=$(find "$ACCEPTED_ROOT" -mindepth 1 -maxdepth 1 -exec basename {} \; | LC_ALL=C sort)
[ "$ACTUAL_ACCEPTED_ROOT" = "$EXPECTED_ACCEPTED_ROOT" ] || fail "accepted release root inventory changed"

LOCAL_TAG_TYPE=$(git cat-file -t "refs/tags/$TAG")
[ "$LOCAL_TAG_TYPE" = "tag" ] || fail "local release reference is not an annotated tag"
LOCAL_TAG_OBJECT=$(git rev-parse "refs/tags/$TAG")
[[ "$LOCAL_TAG_OBJECT" =~ ^[0-9a-f]{40}$ ]] || fail "local tag object ID is malformed"
REMOTE_TAG_OBJECT=$(git ls-remote origin "refs/tags/$TAG" | awk -v expected="refs/tags/$TAG" '$2 == expected {print $1}')
[[ "$REMOTE_TAG_OBJECT" =~ ^[0-9a-f]{40}$ ]] || fail "remote tag object ID is missing or malformed"
[ "$LOCAL_TAG_OBJECT" = "$REMOTE_TAG_OBJECT" ] || fail "local and remote tag object IDs differ"
LOCAL_TAG_SHA=$(git rev-parse "refs/tags/$TAG^{}")
[ "$LOCAL_TAG_SHA" = "$SHA" ] || fail "local tag does not resolve to accepted SHA"
REMOTE_TAG_SHA=$(git ls-remote origin "refs/tags/$TAG^{}" | awk -v expected="refs/tags/$TAG^{}" '$2 == expected {print $1}')
[ "$REMOTE_TAG_SHA" = "$SHA" ] || fail "remote tag does not resolve to accepted SHA"
TAG_MESSAGE_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-tag-message.XXXXXX")
python3 tools/release_artifacts.py render-gauntlet-tag-message \
  --receipt "$RECEIPT_PATH" \
  --receipt-sha256 "$RECEIPT_SHA256" > "$TAG_MESSAGE_FILE"
EXPECTED_TAG_MESSAGE=$(cat "$TAG_MESSAGE_FILE")
ACTUAL_TAG_MESSAGE=$(git for-each-ref --format='%(contents)' "refs/tags/$TAG")
[ "$ACTUAL_TAG_MESSAGE" = "$EXPECTED_TAG_MESSAGE" ] || fail "annotated tag message does not bind the accepted gauntlet receipt"
if gh release view "$TAG" >/dev/null 2>&1; then
  fail "release already exists: $TAG"
fi

CREATE_ARGUMENTS=(release create "$TAG" --verify-tag)
if [ "$PRERELEASE" -eq 1 ]; then
  CREATE_ARGUMENTS+=(--prerelease)
fi
CREATE_ARGUMENTS+=(
  --title "AFTERLIGHT $VERSION"
  --notes-file "$RELEASE_DOC"
  "$PUBLIC_ROOT/AFTERLIGHT-curseforge.zip"
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip"
  "$PUBLIC_ROOT/AFTERLIGHT.mrpack"
  "$PUBLIC_ROOT/release-metadata.json"
  "$PUBLIC_ROOT/SHA256SUMS"
)
python3 tools/release_artifacts.py verify-public-release \
  --dist-dir "$PUBLIC_ROOT" \
  --version "$VERSION" \
  --git-sha "$SHA" \
  --pack-url "$RELEASE_PACK_URL" \
  --bootstrap-version "$RELEASE_PACKWIZ_BOOTSTRAP_VERSION" \
  --bootstrap-size "$RELEASE_PACKWIZ_BOOTSTRAP_SIZE" \
  --bootstrap-sha256 "$RELEASE_PACKWIZ_BOOTSTRAP_SHA256" \
  --installer-version "$RELEASE_PACKWIZ_INSTALLER_VERSION" \
  --installer-size "$RELEASE_PACKWIZ_INSTALLER_SIZE" \
  --installer-sha256 "$RELEASE_PACKWIZ_INSTALLER_SHA256" \
  --receipt "$RECEIPT_PATH" \
  --receipt-sha256 "$RECEIPT_SHA256"
gh "${CREATE_ARGUMENTS[@]}"

ACTUAL_ASSETS=$(gh release view "$TAG" --json assets --jq '.assets[].name' | LC_ALL=C sort)
[ "$ACTUAL_ASSETS" = "$EXPECTED_PUBLIC" ] || fail "published release asset inventory changed"
echo "PUBLICATION: OK $TAG $SHA"
