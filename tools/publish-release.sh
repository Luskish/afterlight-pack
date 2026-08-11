#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

EXPECTED_ACCEPTED_ROOT=$'gauntlet.txt\npublic'
EXPECTED_PUBLIC=$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nSHA256SUMS\nrelease-metadata.json'
EXPECTED_CHECKSUM_TARGETS=$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nrelease-metadata.json'

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

validate_public_checksums() {
  local directory=$1
  local checksum_targets
  if ! checksum_targets=$(awk '
    length($0) > 66 && substr($0, 65, 2) == "  " {
      digest = substr($0, 1, 64)
      name = substr($0, 67)
      if (digest ~ /^[0-9a-f]+$/ && name !~ /\// && name !~ /[[:space:]]/) {
        print name
        next
      }
    }
    { exit 1 }
  ' "$directory/SHA256SUMS"); then
    fail "accepted public checksums are malformed"
  fi
  [ "$checksum_targets" = "$EXPECTED_CHECKSUM_TARGETS" ] ||
    fail "accepted public checksums do not cover the exact artifact inventory"
  (cd "$directory" && shasum -a 256 -c SHA256SUMS) ||
    fail "accepted public checksum verification failed"
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
METADATA="$PUBLIC_ROOT/release-metadata.json"

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
ACTUAL_PUBLIC=$(find "$PUBLIC_ROOT" -mindepth 1 -maxdepth 1 -exec basename {} \; | LC_ALL=C sort)
[ "$ACTUAL_ACCEPTED_ROOT" = "$EXPECTED_ACCEPTED_ROOT" ] || fail "accepted release root inventory changed"
[ "$ACTUAL_PUBLIC" = "$EXPECTED_PUBLIC" ] || fail "accepted public artifact inventory changed"
for artifact in \
  "$PUBLIC_ROOT/AFTERLIGHT-curseforge.zip" \
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip" \
  "$PUBLIC_ROOT/AFTERLIGHT.mrpack" \
  "$PUBLIC_ROOT/release-metadata.json" \
  "$PUBLIC_ROOT/SHA256SUMS"; do
  if [ ! -f "$artifact" ] || [ -L "$artifact" ]; then
    fail "release artifact is not a regular file: $artifact"
  fi
done

python3 - "$METADATA" "$VERSION" "$SHA" <<'PY'
import hashlib
import json
import re
import stat
import sys
from pathlib import Path

metadata = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
version = sys.argv[2]
git_sha = sys.argv[3]
if metadata.get("format") != 3:
    raise SystemExit("FAIL: release metadata format does not match")
if metadata.get("version") != version:
    raise SystemExit("FAIL: release metadata version does not match")
if metadata.get("git_sha") != git_sha:
    raise SystemExit("FAIL: release metadata SHA does not match")
if "private_artifacts" in metadata:
    raise SystemExit("FAIL: release metadata classifies public launchers as private")
expected_public = {
    "AFTERLIGHT-curseforge.zip",
    "AFTERLIGHT-prism-instance.zip",
    "AFTERLIGHT.mrpack",
}
public_artifacts = metadata.get("public_artifacts")
if not isinstance(public_artifacts, dict) or set(public_artifacts) != expected_public:
    raise SystemExit("FAIL: release metadata public artifacts do not match")
for artifact_name in sorted(expected_public):
    record = public_artifacts[artifact_name]
    if not isinstance(record, dict) or set(record) != {"sha256", "size"}:
        raise SystemExit(f"FAIL: release metadata record is malformed: {artifact_name}")
    if not isinstance(record["sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", record["sha256"]
    ):
        raise SystemExit(f"FAIL: release metadata SHA-256 is malformed: {artifact_name}")
    if type(record["size"]) is not int or record["size"] <= 0:
        raise SystemExit(f"FAIL: release metadata size is malformed: {artifact_name}")
    artifact_path = Path(sys.argv[1]).parent / artifact_name
    artifact_status = artifact_path.lstat()
    if not stat.S_ISREG(artifact_status.st_mode):
        raise SystemExit(f"FAIL: release metadata artifact is not regular: {artifact_name}")
    if artifact_status.st_size != record["size"]:
        raise SystemExit(f"FAIL: release metadata size does not match: {artifact_name}")
    if hashlib.sha256(artifact_path.read_bytes()).hexdigest() != record["sha256"]:
        raise SystemExit(f"FAIL: release metadata SHA-256 does not match: {artifact_name}")
PY
validate_public_checksums "$PUBLIC_ROOT"

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
  "$PUBLIC_ROOT/AFTERLIGHT-curseforge.zip"
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip"
  "$PUBLIC_ROOT/AFTERLIGHT.mrpack"
  "$PUBLIC_ROOT/release-metadata.json"
  "$PUBLIC_ROOT/SHA256SUMS"
)
gh "${CREATE_ARGUMENTS[@]}"

ACTUAL_ASSETS=$(gh release view "$TAG" --json assets --jq '.assets[].name' | LC_ALL=C sort)
[ "$ACTUAL_ASSETS" = "$EXPECTED_PUBLIC" ] || fail "published release asset inventory changed"
echo "PUBLICATION: OK $TAG $SHA"
