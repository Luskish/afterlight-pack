#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

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
PRIVATE_ROOT="$ACCEPTED_ROOT/friends-only"
METADATA="$PUBLIC_ROOT/release-metadata.json"
EXPECTED_PUBLIC=$'AFTERLIGHT-prism-instance.zip\nSHA256SUMS\nrelease-metadata.json'
EXPECTED_PRIVATE=$(printf '%s\n' "AFTERLIGHT-$VERSION-curseforge.zip" "AFTERLIGHT-$VERSION.mrpack" | LC_ALL=C sort)

[ -f "$RELEASE_DOC" ] && [ ! -L "$RELEASE_DOC" ] || fail "release notes are missing: $RELEASE_DOC"
[ "$(head -1 "$RELEASE_DOC")" = "# AFTERLIGHT $VERSION" ] || fail "release-note title does not match requested version"
grep -Fqx "## Automated Evidence" "$RELEASE_DOC" || fail "release notes lack Automated Evidence"
grep -Fqx "## Known Boundaries" "$RELEASE_DOC" || fail "release notes lack Known Boundaries"
AUTOMATED_EVIDENCE=$(sed -n '/^## Automated Evidence$/,/^## Known Boundaries$/p' "$RELEASE_DOC")
if printf '%s\n' "$AUTOMATED_EVIDENCE" | grep -Fq "NOT RUN"; then
  fail "release notes still contain automated NOT RUN evidence"
fi

[ -d "$PUBLIC_ROOT" ] && [ ! -L "$PUBLIC_ROOT" ] || fail "accepted public directory is missing"
[ -d "$PRIVATE_ROOT" ] && [ ! -L "$PRIVATE_ROOT" ] || fail "accepted friends-only directory is missing"
ACTUAL_PUBLIC=$(find "$PUBLIC_ROOT" -mindepth 1 -maxdepth 1 -exec basename {} \; | LC_ALL=C sort)
ACTUAL_PRIVATE=$(find "$PRIVATE_ROOT" -mindepth 1 -maxdepth 1 -exec basename {} \; | LC_ALL=C sort)
[ "$ACTUAL_PUBLIC" = "$EXPECTED_PUBLIC" ] || fail "accepted public artifact inventory changed"
[ "$ACTUAL_PRIVATE" = "$EXPECTED_PRIVATE" ] || fail "accepted friends-only artifact inventory changed"
for artifact in \
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip" \
  "$PUBLIC_ROOT/release-metadata.json" \
  "$PUBLIC_ROOT/SHA256SUMS" \
  "$PRIVATE_ROOT/AFTERLIGHT-$VERSION.mrpack" \
  "$PRIVATE_ROOT/AFTERLIGHT-$VERSION-curseforge.zip"; do
  [ -f "$artifact" ] && [ ! -L "$artifact" ] || fail "release artifact is not a regular file: $artifact"
done

python3 - "$METADATA" "$VERSION" "$SHA" <<'PY'
import json
import sys
from pathlib import Path

metadata = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = sys.argv[2]
git_sha = sys.argv[3]
if metadata.get("format") != 2:
    raise SystemExit("FAIL: release metadata format does not match")
if metadata.get("version") != version:
    raise SystemExit("FAIL: release metadata version does not match")
if metadata.get("git_sha") != git_sha:
    raise SystemExit("FAIL: release metadata SHA does not match")
expected_private = sorted(
    (f"AFTERLIGHT-{version}-curseforge.zip", f"AFTERLIGHT-{version}.mrpack")
)
if metadata.get("private_artifacts") != expected_private:
    raise SystemExit("FAIL: release metadata private artifacts do not match")
if set(metadata.get("public_artifacts", {})) != {"AFTERLIGHT-prism-instance.zip"}:
    raise SystemExit("FAIL: release metadata public artifacts do not match")
PY
(cd "$PUBLIC_ROOT" && shasum -a 256 -c SHA256SUMS)

LOCAL_TAG_SHA=$(git rev-parse "refs/tags/$TAG^{}")
[ "$LOCAL_TAG_SHA" = "$SHA" ] || fail "local tag does not resolve to accepted SHA"
REMOTE_TAG_SHA=$(git ls-remote origin "refs/tags/$TAG^{}" | awk '{print $1}')
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
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip"
  "$PUBLIC_ROOT/release-metadata.json"
  "$PUBLIC_ROOT/SHA256SUMS"
)
gh "${CREATE_ARGUMENTS[@]}"

ACTUAL_ASSETS=$(gh release view "$TAG" --json assets --jq '.assets[].name' | LC_ALL=C sort)
[ "$ACTUAL_ASSETS" = "$EXPECTED_PUBLIC" ] || fail "published release asset inventory changed"
echo "PUBLICATION: OK $TAG $SHA"
