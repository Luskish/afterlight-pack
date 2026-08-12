#!/usr/bin/env bash
set -euo pipefail
export GIT_NO_REPLACE_OBJECTS=1

cd "$(dirname "$0")/.."

EXPECTED_ACCEPTED_ROOT=$'gauntlet-receipt.json\ngauntlet.txt\npublic'
EXPECTED_PUBLIC=$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nSHA256SUMS\nrelease-metadata.json'
REPOSITORY=Luskish/afterlight-pack
WORKFLOW_FILE=pack-ci.yml
WORKFLOW_PATH=.github/workflows/pack-ci.yml
WORKFLOW_ID=""
CI_POLL_ATTEMPTS=${AFTERLIGHT_CI_POLL_ATTEMPTS:-60}
CI_POLL_SECONDS=${AFTERLIGHT_CI_POLL_SECONDS:-5}
CI_RUN_URL=""
TAG_MESSAGE_FILE=""
CHANGED_PATH_FILE=""
CREATE_REQUEST_FILE=""
PUBLISH_REQUEST_FILE=""
ASSET_RECORD_FILE=""
AUTH_DOWNLOAD_DIR=""
PUBLIC_DOWNLOAD_DIR=""
RELEASE_CREATED=0
RELEASE_ID=""
TAG=""

cleanup() {
  local exit_status=$?
  trap - EXIT
  if [ -n "$TAG_MESSAGE_FILE" ]; then
    rm -f "$TAG_MESSAGE_FILE"
    TAG_MESSAGE_FILE=""
  fi
  if [ -n "$CHANGED_PATH_FILE" ]; then
    rm -f "$CHANGED_PATH_FILE"
    CHANGED_PATH_FILE=""
  fi
  if [ -n "$CREATE_REQUEST_FILE" ]; then
    rm -f "$CREATE_REQUEST_FILE"
    CREATE_REQUEST_FILE=""
  fi
  if [ -n "$PUBLISH_REQUEST_FILE" ]; then
    rm -f "$PUBLISH_REQUEST_FILE"
    PUBLISH_REQUEST_FILE=""
  fi
  if [ -n "$ASSET_RECORD_FILE" ]; then
    rm -f "$ASSET_RECORD_FILE"
    ASSET_RECORD_FILE=""
  fi
  if [ -n "$AUTH_DOWNLOAD_DIR" ]; then
    rm -rf "$AUTH_DOWNLOAD_DIR"
    AUTH_DOWNLOAD_DIR=""
  fi
  if [ -n "$PUBLIC_DOWNLOAD_DIR" ]; then
    rm -rf "$PUBLIC_DOWNLOAD_DIR"
    PUBLIC_DOWNLOAD_DIR=""
  fi
  if [ "$exit_status" -ne 0 ] && [ "$RELEASE_CREATED" -eq 1 ]; then
    if [ -z "$RELEASE_ID" ]; then
      echo "FAIL: unable to identify incomplete release, inspect $TAG manually" >&2
    else
      echo "FAIL: incomplete GitHub release may remain, inspect release ID $RELEASE_ID for $TAG" >&2
    fi
  fi
  exit "$exit_status"
}
trap cleanup EXIT

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

require_positive_integer() {
  local label=$1
  local value=$2
  [[ "$value" =~ ^[1-9][0-9]*$ ]] || fail "$label must be a positive integer"
}

require_nonnegative_integer() {
  local label=$1
  local value=$2
  [[ "$value" =~ ^(0|[1-9][0-9]*)$ ]] || fail "$label must be a nonnegative integer"
}

wait_for_exact_ci() {
  local branch=$1
  local sha=$2
  local poll_attempt=1
  local run_id=""
  local run_record
  local actual_sha actual_branch actual_event actual_status actual_conclusion
  local run_url actual_workflow_id actual_attempt
  local workflow_record workflow_path workflow_state

  if [ -z "$WORKFLOW_ID" ]; then
    workflow_record=$(gh api --hostname github.com \
      "repos/$REPOSITORY/actions/workflows/$WORKFLOW_FILE" \
      --jq '[.id,.path,.state] | @tsv') || return 1
    IFS=$'\t' read -r WORKFLOW_ID workflow_path workflow_state <<< "$workflow_record"
    [[ "$WORKFLOW_ID" =~ ^[1-9][0-9]*$ ]] || fail "pack-ci workflow ID is malformed"
    [ "$workflow_path" = "$WORKFLOW_PATH" ] || fail "pack-ci workflow path changed"
    [ "$workflow_state" = active ] || fail "pack-ci workflow is not active"
  fi

  while [[ "$poll_attempt" -le "$CI_POLL_ATTEMPTS" ]]; do
    run_id=$(gh run list \
      --repo "$REPOSITORY" \
      --workflow "$WORKFLOW_FILE" \
      --branch "$branch" \
      --event push \
      --commit "$sha" \
      --limit 1 \
      --json databaseId \
      --jq '.[0].databaseId // empty') || return 1
    if [[ "$run_id" =~ ^[0-9]+$ ]]; then
      break
    fi
    run_id=""
    sleep "$CI_POLL_SECONDS"
    poll_attempt=$((poll_attempt + 1))
  done
  [[ -n "$run_id" ]] || fail "no exact $branch push CI run appeared for $sha"

  gh run watch "$run_id" --repo "$REPOSITORY" --exit-status
  run_record=$(gh run view "$run_id" \
    --repo "$REPOSITORY" \
    --json headSha,headBranch,event,status,conclusion,url,workflowDatabaseId,attempt \
    --jq '[.headSha,.headBranch,.event,.status,.conclusion,.url,.workflowDatabaseId,.attempt] | @tsv') || return 1
  IFS=$'\t' read -r actual_sha actual_branch actual_event actual_status actual_conclusion run_url actual_workflow_id actual_attempt <<< "$run_record"
  if [[ "$actual_sha" != "$sha" || "$actual_branch" != "$branch" ||
    "$actual_event" != push ||
    "$actual_status" != completed || "$actual_conclusion" != success ||
    "$actual_workflow_id" != "$WORKFLOW_ID" ||
    ! "$actual_attempt" =~ ^[1-9][0-9]*$ || -z "$run_url" ]]; then
    fail "CI evidence did not match a successful $branch push for $sha"
  fi
  CI_RUN_URL=$run_url
}

require_release_evidence_line() {
  local expected_line=$1
  local count

  count=$(printf '%s\n' "$AUTOMATED_EVIDENCE" |
    grep -Fxc -- "$expected_line" || true)
  [ "$count" -eq 1 ] || fail "release evidence is missing, duplicated, or fabricated"
}

validate_release_evidence() {
  local transcript_sha256 pack_sha256 index_sha256
  local receipt_public_records
  local public_name public_sha256 public_size

  transcript_sha256=$(shasum -a 256 "$ACCEPTED_ROOT/gauntlet.txt" | awk '{print $1}')
  pack_sha256=$(shasum -a 256 pack.toml | awk '{print $1}')
  index_sha256=$(shasum -a 256 index.toml | awk '{print $1}')
  receipt_public_records=$(python3 - "$RECEIPT_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], "rb") as receipt_file:
    receipt = json.load(receipt_file)
for name, record in sorted(receipt["public_files"].items()):
    print(f"{name}\t{record['sha256']}\t{record['size']}")
PY
  ) || fail "unable to read release evidence from the gauntlet receipt"
  [ -n "$receipt_public_records" ] || fail "gauntlet receipt has no public release evidence"

  require_release_evidence_line "- Accepted commit and annotated tag target: \`$SHA\`"
  require_release_evidence_line "- Local gauntlet receipt SHA-256: \`$RECEIPT_SHA256\`"
  require_release_evidence_line "- Local gauntlet transcript SHA-256: \`$transcript_sha256\`"
  require_release_evidence_line "- Exact accepted \`dev\` CI URL: \`$ACCEPTED_DEV_CI_URL\`"
  require_release_evidence_line "- Exact \`main\` CI URL: \`$MAIN_CI_URL\`"
  require_release_evidence_line "- GitHub Pages \`pack.toml\` SHA-256: \`$pack_sha256\`"
  require_release_evidence_line "- GitHub Pages \`index.toml\` SHA-256: \`$index_sha256\`"
  require_release_evidence_line "- Signal source: \`a3d95a74a56855a026f9f2786f1e925065a3b151\`"
  require_release_evidence_line "- Signal release JAR SHA-256: \`81387eff5e6f5dad555a936d605c114af8fff1cf69778251cc3a7ec660f15947\`"
  require_release_evidence_line "- Signal release JAR SHA-512: \`902d3f64ac6f2e3302da26daefa29cfd03e19f39d293daa81da7b04cb3f115d3e0ed933da189f2622bd1284e6a3292fd7a4ddc6f8c115e3e43d2123e56f7d74f\`"
  require_release_evidence_line "- Signal evidence CI: \`https://github.com/Luskish/afterlight-signal/actions/runs/31588113497\`"
  while IFS=$'\t' read -r public_name public_sha256 public_size; do
    require_release_evidence_line "- \`$public_name\`: SHA-256 \`$public_sha256\`, size \`$public_size\` bytes."
  done <<< "$receipt_public_records"
}

validate_downloaded_release() {
  local directory=$1
  local actual_inventory
  local public_name

  actual_inventory=$(find "$directory" -mindepth 1 -maxdepth 1 -exec basename {} \; |
    LC_ALL=C sort)
  [ "$actual_inventory" = "$EXPECTED_PUBLIC" ] ||
    fail "downloaded release inventory changed"
  while IFS= read -r public_name; do
    if [ ! -f "$directory/$public_name" ] || [ -L "$directory/$public_name" ]; then
      fail "downloaded release entry is not a regular file: $public_name"
    fi
    cmp "$PUBLIC_ROOT/$public_name" "$directory/$public_name" ||
      fail "downloaded release bytes differ: $public_name"
  done <<< "$EXPECTED_PUBLIC"
  (cd "$directory" && shasum -a 256 -c SHA256SUMS) ||
    fail "downloaded release checksums failed"
}

verify_remote_release_state() {
  local expected_draft=$1
  local expected_prerelease=false
  local record

  if [ "$PRERELEASE" -eq 1 ]; then
    expected_prerelease=true
  fi
  record=$(gh api --hostname github.com \
    "repos/$REPOSITORY/releases/$RELEASE_ID" \
    --jq '[.id,.draft,.prerelease,.tag_name,.html_url,(.published_at // ""),([.assets[] | "\(.name):\(.id):\(.size)"] | sort | join(","))] | map(tostring) | join("|")') ||
    return 1
  IFS='|' read -r REMOTE_RELEASE_ID REMOTE_IS_DRAFT REMOTE_IS_PRERELEASE REMOTE_TAG RELEASE_URL RELEASE_PUBLISHED_AT REMOTE_ASSETS <<< "$record"
  [ "$REMOTE_RELEASE_ID" = "$RELEASE_ID" ] ||
    fail "remote release identity changed"
  [ "$REMOTE_IS_DRAFT" = "$expected_draft" ] ||
    fail "remote release draft state changed"
  [ "$REMOTE_IS_PRERELEASE" = "$expected_prerelease" ] ||
    fail "remote release prerelease state changed"
  [ "$REMOTE_TAG" = "$TAG" ] || fail "remote release tag changed"
  [ -n "$RELEASE_URL" ] || fail "remote release URL is missing"
  if [ "$expected_draft" = false ] && [ -z "$RELEASE_PUBLISHED_AT" ]; then
    fail "remote release publication timestamp is missing"
  fi
  EXPECTED_REMOTE_ASSETS=$(LC_ALL=C sort -t $'\t' -k2,2 "$ASSET_RECORD_FILE" |
    awk -F '\t' 'BEGIN { separator = "" } { printf "%s%s:%s:%s", separator, $2, $1, $3; separator = "," } END { print "" }')
  [ "$REMOTE_ASSETS" = "$EXPECTED_REMOTE_ASSETS" ] ||
    fail "published release asset inventory changed"
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
require_positive_integer AFTERLIGHT_CI_POLL_ATTEMPTS "$CI_POLL_ATTEMPTS"
require_nonnegative_integer AFTERLIGHT_CI_POLL_SECONDS "$CI_POLL_SECONDS"
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
ORIGIN_URL=$(git remote get-url origin) || fail "unable to resolve the production repository origin"
case "$ORIGIN_URL" in
  https://github.com/Luskish/afterlight-pack.git|git@github.com:Luskish/afterlight-pack.git|ssh://git@github.com/Luskish/afterlight-pack.git) ;;
  *) fail "origin is not the production repository" ;;
esac
HEAD_SHA=$(git rev-parse HEAD)
[[ "$HEAD_SHA" =~ ^[0-9a-f]{40}$ ]] || fail "dev HEAD is malformed"
[ "$HEAD_SHA" != "$SHA" ] || fail "publication requires a distinct documentation evidence commit"
git merge-base --is-ancestor "$SHA" "$HEAD_SHA" ||
  fail "dev HEAD is not a descendant of the accepted SHA"
REMOTE_DEV_SHA=$(git ls-remote origin refs/heads/dev |
  awk '$2 == "refs/heads/dev" {print $1}')
[ "$REMOTE_DEV_SHA" = "$HEAD_SHA" ] || fail "local dev does not equal remote dev"
REMOTE_MAIN_SHA=$(git ls-remote origin refs/heads/main |
  awk '$2 == "refs/heads/main" {print $1}')
[ "$REMOTE_MAIN_SHA" = "$SHA" ] || fail "remote main does not equal the accepted SHA"
CHANGED_PATH_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-publish-paths.XXXXXX")
git diff --name-only -z "$SHA" "$HEAD_SHA" > "$CHANGED_PATH_FILE" ||
  fail "unable to inspect post-acceptance changes"
while IFS= read -r -d '' changed_path; do
  case "$changed_path" in
    docs/HANDOFF.md|"docs/releases/$VERSION.md") ;;
    *) fail "post-acceptance change is not approved release evidence: $changed_path" ;;
  esac
done < "$CHANGED_PATH_FILE"
git diff --quiet "$SHA" "$HEAD_SHA" -- \
  tools/publish-release.sh \
  tools/release_artifacts.py \
  tools/release-policy.env ||
  fail "trusted publication tooling differs from the accepted SHA"
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
if printf '%s\n' "$AUTOMATED_EVIDENCE" | grep -Fq "PENDING"; then
  fail "release notes still contain automated PENDING evidence"
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
if gh release view "$TAG" --repo "$REPOSITORY" >/dev/null 2>&1; then
  fail "release already exists: $TAG"
fi

python3 tools/release_artifacts.py verify-public-release \
  --dist-dir "$PUBLIC_ROOT" \
  --pack-root . \
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
wait_for_exact_ci dev "$SHA"
ACCEPTED_DEV_CI_URL=$CI_RUN_URL
wait_for_exact_ci main "$SHA"
MAIN_CI_URL=$CI_RUN_URL
wait_for_exact_ci dev "$HEAD_SHA"
EVIDENCE_CI_URL=$CI_RUN_URL
validate_release_evidence
CREATE_REQUEST_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-release-create.XXXXXX")
python3 - "$TAG" "$VERSION" "$RELEASE_DOC" "$PRERELEASE" > "$CREATE_REQUEST_FILE" <<'PY'
import json
import sys
from pathlib import Path

tag, version, notes_path, prerelease = sys.argv[1:]
request = {
    "body": Path(notes_path).read_text(encoding="utf-8"),
    "draft": True,
    "name": f"AFTERLIGHT {version}",
    "prerelease": prerelease == "1",
    "tag_name": tag,
}
json.dump(request, sys.stdout, separators=(",", ":"), sort_keys=True)
sys.stdout.write("\n")
PY
if ! CREATE_RECORD=$(gh api --hostname github.com \
  --method POST \
  "repos/$REPOSITORY/releases" \
  --input "$CREATE_REQUEST_FILE" \
  --jq '[.id,.draft,.tag_name,.upload_url] | @tsv'); then
  echo "FAIL: release creation failed, creation outcome is unknown, inspect $TAG manually" >&2
  exit 2
fi
RELEASE_CREATED=1
IFS=$'\t' read -r CAPTURED_RELEASE_ID CREATED_DRAFT CREATED_TAG UPLOAD_URL <<< "$CREATE_RECORD"
[[ "$CAPTURED_RELEASE_ID" =~ ^[1-9][0-9]*$ ]] || fail "created release ID is malformed"
RELEASE_ID=$CAPTURED_RELEASE_ID
[ "$CREATED_DRAFT" = true ] || fail "created release is not a draft"
[ "$CREATED_TAG" = "$TAG" ] || fail "created release tag changed"
UPLOAD_URL=${UPLOAD_URL%%\{*}
[ "$UPLOAD_URL" = "https://uploads.github.com/repos/$REPOSITORY/releases/$RELEASE_ID/assets" ] ||
  fail "created release upload URL changed"

ASSET_RECORD_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-release-assets.XXXXXX")
while IFS= read -r public_name; do
  public_path="$PUBLIC_ROOT/$public_name"
  expected_size=$(wc -c < "$public_path" | tr -d ' ')
  upload_record=$(gh api \
    --method POST \
    -H 'Accept: application/vnd.github+json' \
    -H 'Content-Type: application/octet-stream' \
    "$UPLOAD_URL?name=$public_name" \
    --input "$public_path" \
    --jq '[.id,.name,.size] | @tsv')
  IFS=$'\t' read -r asset_id asset_name asset_size <<< "$upload_record"
  [[ "$asset_id" =~ ^[1-9][0-9]*$ ]] || fail "uploaded asset ID is malformed"
  [ "$asset_name" = "$public_name" ] || fail "uploaded asset name changed"
  [ "$asset_size" = "$expected_size" ] || fail "uploaded asset size changed"
  printf '%s\t%s\t%s\n' "$asset_id" "$asset_name" "$asset_size" >> "$ASSET_RECORD_FILE"
done <<< "$EXPECTED_PUBLIC"
[ "$(cut -f1 "$ASSET_RECORD_FILE" | LC_ALL=C sort -u | wc -l | tr -d ' ')" -eq 5 ] ||
  fail "uploaded asset IDs are not unique"
verify_remote_release_state true

AUTH_DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-release-auth.XXXXXX")
while IFS=$'\t' read -r asset_id asset_name asset_size; do
  gh api --hostname github.com \
    -H 'Accept: application/octet-stream' \
    "repos/$REPOSITORY/releases/assets/$asset_id" > "$AUTH_DOWNLOAD_DIR/$asset_name"
done < "$ASSET_RECORD_FILE"
validate_downloaded_release "$AUTH_DOWNLOAD_DIR"

python3 tools/release_artifacts.py verify-public-release \
  --dist-dir "$PUBLIC_ROOT" \
  --pack-root . \
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

PUBLISH_REQUEST_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-release-publish.XXXXXX")
printf '{"draft":false}\n' > "$PUBLISH_REQUEST_FILE"
if ! gh api --hostname github.com \
  --method PATCH \
  "repos/$REPOSITORY/releases/$RELEASE_ID" \
  --input "$PUBLISH_REQUEST_FILE" >/dev/null; then
  echo "FAIL: release publication outcome is unknown, inspect release ID $RELEASE_ID manually" >&2
  exit 2
fi
verify_remote_release_state false

PUBLIC_DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-release-public.XXXXXX")
while IFS= read -r public_name; do
  curl --disable -fsSL \
    --proto '=https' \
    --proto-redir '=https' \
    --tlsv1.2 \
    --retry 8 \
    --retry-delay 2 \
    --retry-all-errors \
    --connect-timeout 15 \
    "https://github.com/$REPOSITORY/releases/download/$TAG/$public_name" \
    -o "$PUBLIC_DOWNLOAD_DIR/$public_name"
done <<< "$EXPECTED_PUBLIC"
validate_downloaded_release "$PUBLIC_DOWNLOAD_DIR"
verify_remote_release_state false
echo "PUBLICATION: OK $TAG $SHA"
echo "EVIDENCE_CI_URL=$EVIDENCE_CI_URL"
echo "RELEASE_URL=$RELEASE_URL"
echo "RELEASE_PUBLISHED_AT=$RELEASE_PUBLISHED_AT"
