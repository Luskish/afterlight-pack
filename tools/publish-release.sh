#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

EXPECTED_ACCEPTED_ROOT=$'gauntlet.txt\npublic'
EXPECTED_PUBLIC=$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nSHA256SUMS\nrelease-metadata.json'

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

if [ "$#" -eq 4 ] && [ "$3" = "--prerelease" ] && [ "$4" = "--confirm" ]; then
  PRERELEASE=1
elif [ "$#" -eq 3 ] && [ "$3" = "--confirm" ]; then
  PRERELEASE=0
else
  fail "usage: $0 SHA VERSION [--prerelease] --confirm"
fi

SHA=$1
VERSION=$2
[[ "$SHA" =~ ^[0-9a-f]{40}$ ]] || fail "SHA must be exactly 40 lowercase hexadecimal characters"
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]] || fail "VERSION is not a supported release version"
case "$VERSION" in
  *-rc.*)
    [ "$PRERELEASE" -eq 1 ] || fail "$VERSION requires --prerelease"
    ;;
  *)
    [ "$PRERELEASE" -eq 0 ] || fail "$VERSION must not use --prerelease"
    ;;
esac

[ "$(git branch --show-current)" = "dev" ] || fail "publication must run from dev"
CURRENT_VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
[ "$CURRENT_VERSION" = "$VERSION" ] || fail "pack.toml version does not match requested version"
ACCEPTED_VERSION=$(git show "$SHA:pack.toml" | python3 -c 'import sys,tomllib; print(tomllib.load(sys.stdin.buffer)["version"])')
[ "$ACCEPTED_VERSION" = "$VERSION" ] || fail "accepted commit version does not match requested version"

TAG="v$VERSION"
RELEASE_DOC="docs/releases/$VERSION.md"
ACCEPTED_ROOT="dist/gauntlet/$SHA"
PUBLIC_ROOT="$ACCEPTED_ROOT/public"

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
  --git-sha "$SHA"
gh "${CREATE_ARGUMENTS[@]}"

ACTUAL_ASSETS=$(gh release view "$TAG" --json assets --jq '.assets[].name' | LC_ALL=C sort)
[ "$ACTUAL_ASSETS" = "$EXPECTED_PUBLIC" ] || fail "published release asset inventory changed"
echo "PUBLICATION: OK $TAG $SHA"
