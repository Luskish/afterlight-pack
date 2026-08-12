#!/usr/bin/env bash
set -euo pipefail
export GIT_NO_REPLACE_OBJECTS=1

cd "$(dirname "$0")/.."

REPOSITORY=Luskish/afterlight-pack
WORKFLOW_FILE=pack-ci.yml
WORKFLOW_PATH=.github/workflows/pack-ci.yml
WORKFLOW_ID=""
CI_POLL_ATTEMPTS=${AFTERLIGHT_CI_POLL_ATTEMPTS:-60}
CI_POLL_SECONDS=${AFTERLIGHT_CI_POLL_SECONDS:-5}
PAGES_POLL_ATTEMPTS=${AFTERLIGHT_PAGES_POLL_ATTEMPTS:-60}
PAGES_POLL_SECONDS=${AFTERLIGHT_PAGES_POLL_SECONDS:-5}
CI_RUN_URL=""
EXPECTED_ACCEPTED_ROOT=$'gauntlet-receipt.json\ngauntlet.txt\npublic'
TAG_MESSAGE_FILE=""
START_BRANCH=""
BRANCH_CHANGED=0

fail() {
  printf 'FAIL: %s\n' "$*" >&2
  return 1
}

require_positive_integer() {
  local label=$1
  local value=$2
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    fail "$label must be a positive integer"
    return 1
  fi
}

require_nonnegative_integer() {
  local label=$1
  local value=$2
  if [[ ! "$value" =~ ^(0|[1-9][0-9]*)$ ]]; then
    fail "$label must be a nonnegative integer"
    return 1
  fi
}

cleanup() {
  local exit_status=$?
  local current_branch
  trap - EXIT
  if [[ -n "$TAG_MESSAGE_FILE" ]]; then
    rm -f "$TAG_MESSAGE_FILE"
    TAG_MESSAGE_FILE=""
  fi
  if [[ "$BRANCH_CHANGED" -eq 1 ]]; then
    current_branch=$(git branch --show-current 2>/dev/null || true)
    if [[ -n "$START_BRANCH" && "$current_branch" != "$START_BRANCH" ]]; then
      git switch "$START_BRANCH" >/dev/null 2>&1 || true
    fi
  fi
  exit "$exit_status"
}

wait_for_exact_ci() {
  local branch=$1
  local sha=$2
  local poll_attempt=1
  local actual_conclusion
  local actual_event
  local actual_branch
  local actual_attempt
  local actual_sha
  local actual_status
  local actual_workflow_id
  local run_id=""
  local run_record
  local run_url
  local workflow_record workflow_path workflow_state

  if [[ -z "$WORKFLOW_ID" ]]; then
    workflow_record=$(gh api --hostname github.com \
      "repos/$REPOSITORY/actions/workflows/$WORKFLOW_FILE" \
      --jq '[.id,.path,.state] | @tsv') || return 1
    IFS=$'\t' read -r WORKFLOW_ID workflow_path workflow_state <<< "$workflow_record"
    [[ "$WORKFLOW_ID" =~ ^[1-9][0-9]*$ ]] || {
      fail "pack-ci workflow ID is malformed"
      return 1
    }
    [[ "$workflow_path" == "$WORKFLOW_PATH" && "$workflow_state" == active ]] || {
      fail "pack-ci workflow identity changed"
      return 1
    }
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

  if [[ -z "$run_id" ]]; then
    fail "No exact push CI run appeared for $branch at $sha"
    return 1
  fi

  gh run watch "$run_id" --repo "$REPOSITORY" --exit-status
  run_record=$(gh run view "$run_id" \
    --repo "$REPOSITORY" \
    --json headSha,headBranch,event,status,conclusion,url,workflowDatabaseId,attempt \
    --jq '[.headSha,.headBranch,.event,.status,.conclusion,.url,.workflowDatabaseId,.attempt] | @tsv') || return 1
  IFS=$'\t' read -r actual_sha actual_branch actual_event actual_status actual_conclusion run_url actual_workflow_id actual_attempt <<< "$run_record"
  if [[ "$actual_sha" != "$sha" || "$actual_branch" != "$branch" ||
    "$actual_event" != "push" || "$actual_status" != "completed" ||
    "$actual_conclusion" != "success" || "$actual_workflow_id" != "$WORKFLOW_ID" ||
    ! "$actual_attempt" =~ ^[1-9][0-9]*$ || -z "$run_url" ]]; then
    fail "CI evidence did not match successful push run $run_id for $branch at $sha"
    return 1
  fi
  CI_RUN_URL=$run_url
}

wait_for_pages_parity() {
  local sha=$1
  local attempt=1
  local local_index_sha
  local local_pack_sha
  local bare_index_sha=""
  local bare_pack_sha=""
  local pages_index_sha=""
  local pages_pack_sha=""

  local_pack_sha=$(shasum -a 256 pack.toml | awk '{print $1}')
  local_index_sha=$(shasum -a 256 index.toml | awk '{print $1}')

  while [[ "$attempt" -le "$PAGES_POLL_ATTEMPTS" ]]; do
    bare_pack_sha=$(curl --disable -fsSL \
      --proto '=https' --proto-redir '=https' --tlsv1.2 \
      "https://luskish.github.io/afterlight-pack/pack.toml" |
      shasum -a 256 | awk '{print $1}') || bare_pack_sha=""
    bare_index_sha=$(curl --disable -fsSL \
      --proto '=https' --proto-redir '=https' --tlsv1.2 \
      "https://luskish.github.io/afterlight-pack/index.toml" |
      shasum -a 256 | awk '{print $1}') || bare_index_sha=""
    pages_pack_sha=$(curl --disable -fsSL \
      --proto '=https' --proto-redir '=https' --tlsv1.2 \
      "https://luskish.github.io/afterlight-pack/pack.toml?sha=$sha&attempt=$attempt" |
      shasum -a 256 | awk '{print $1}') || pages_pack_sha=""
    pages_index_sha=$(curl --disable -fsSL \
      --proto '=https' --proto-redir '=https' --tlsv1.2 \
      "https://luskish.github.io/afterlight-pack/index.toml?sha=$sha&attempt=$attempt" |
      shasum -a 256 | awk '{print $1}') || pages_index_sha=""
    if [[ "$bare_pack_sha" == "$local_pack_sha" &&
      "$bare_index_sha" == "$local_index_sha" &&
      "$pages_pack_sha" == "$local_pack_sha" &&
      "$pages_index_sha" == "$local_index_sha" ]]; then
      PAGES_PACK_SHA=$bare_pack_sha
      PAGES_INDEX_SHA=$bare_index_sha
      return 0
    fi
    sleep "$PAGES_POLL_SECONDS"
    attempt=$((attempt + 1))
  done

  fail "GitHub Pages did not match pack.toml and index.toml for $sha"
}

if [[ "$#" -ne 3 || "$3" != "--confirm" ]]; then
  fail "Usage: tools/promote-release.sh SHA RECEIPT_SHA256 --confirm"
  exit 2
fi

SHA=$1
RECEIPT_SHA256=$2
if [[ ! "$SHA" =~ ^[0-9a-f]{40}$ ]]; then
  fail "SHA must be exactly 40 lowercase hexadecimal characters"
  exit 2
fi
if [[ ! "$RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]]; then
  fail "RECEIPT_SHA256 must be exactly 64 lowercase hexadecimal characters"
  exit 2
fi
require_positive_integer AFTERLIGHT_CI_POLL_ATTEMPTS "$CI_POLL_ATTEMPTS"
require_nonnegative_integer AFTERLIGHT_CI_POLL_SECONDS "$CI_POLL_SECONDS"
require_positive_integer AFTERLIGHT_PAGES_POLL_ATTEMPTS "$PAGES_POLL_ATTEMPTS"
require_nonnegative_integer AFTERLIGHT_PAGES_POLL_SECONDS "$PAGES_POLL_SECONDS"

START_BRANCH=$(git branch --show-current)
if [[ "$START_BRANCH" != "dev" ]]; then
  fail "Promotion must start from the dev branch"
  exit 2
fi
if [[ "$(git rev-parse HEAD)" != "$SHA" ]]; then
  fail "Promotion SHA must equal the exact dev HEAD"
  exit 2
fi
status=$(git status --porcelain --untracked-files=all)
if [[ -n "$status" ]]; then
  printf '%s\n' "$status" >&2
  fail "Promotion requires a clean dev worktree"
  exit 2
fi
ORIGIN_URL=$(git remote get-url origin) || {
  fail "Unable to resolve the production repository origin"
  exit 2
}
case "$ORIGIN_URL" in
  https://github.com/Luskish/afterlight-pack.git|git@github.com:Luskish/afterlight-pack.git|ssh://git@github.com/Luskish/afterlight-pack.git) ;;
  *)
    fail "origin is not the production repository"
    exit 2
    ;;
esac
PUSH_URL=$(git remote get-url --push --all origin) || {
  fail "Unable to resolve the production repository push URL"
  exit 2
}
case "$PUSH_URL" in
  https://github.com/Luskish/afterlight-pack.git|git@github.com:Luskish/afterlight-pack.git|ssh://git@github.com/Luskish/afterlight-pack.git) ;;
  *)
    fail "origin push URL is not exactly one production repository URL"
    exit 2
    ;;
esac
# shellcheck disable=SC1091
source tools/release-policy.env

VERSION=$(python3 -c 'import tomllib; print(tomllib.load(open("pack.toml", "rb"))["version"])')
TAG="v$VERSION"
ACCEPTED_ROOT="dist/gauntlet/$SHA"
PUBLIC_ROOT="$ACCEPTED_ROOT/public"
RECEIPT_PATH="$ACCEPTED_ROOT/gauntlet-receipt.json"
ACTUAL_ACCEPTED_ROOT=$(find "$ACCEPTED_ROOT" -mindepth 1 -maxdepth 1 -exec basename {} \; 2>/dev/null | LC_ALL=C sort)
if [[ "$ACTUAL_ACCEPTED_ROOT" != "$EXPECTED_ACCEPTED_ROOT" ]]; then
  fail "Accepted gauntlet artifact inventory is incomplete or contains extra files"
  exit 2
fi
if [[ ! -f "$ACCEPTED_ROOT/gauntlet.txt" || -L "$ACCEPTED_ROOT/gauntlet.txt" ]] ||
  ! grep -Fqx "SHA: $SHA" "$ACCEPTED_ROOT/gauntlet.txt"; then
  fail "Accepted gauntlet transcript does not bind the promotion SHA"
  exit 2
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

if [[ -n "$(git tag --list "$TAG")" ]]; then
  fail "Local tag already exists: $TAG"
  exit 2
fi
if git ls-remote --exit-code --tags origin "refs/tags/$TAG" >/dev/null 2>&1; then
  fail "Remote tag already exists: $TAG"
  exit 2
else
  remote_tag_status=$?
  if [[ "$remote_tag_status" -ne 2 ]]; then
    fail "Unable to verify remote tag availability: $TAG"
    exit 2
  fi
fi

trap cleanup EXIT
TAG_MESSAGE_FILE=$(mktemp "${TMPDIR:-/tmp}/afterlight-tag-message.XXXXXX")
python3 tools/release_artifacts.py render-gauntlet-tag-message \
  --receipt "$RECEIPT_PATH" \
  --receipt-sha256 "$RECEIPT_SHA256" > "$TAG_MESSAGE_FILE"

git push "$PUSH_URL" HEAD:refs/heads/dev
wait_for_exact_ci dev "$SHA"
DEV_CI_URL=$CI_RUN_URL

git switch main
BRANCH_CHANGED=1
git merge --ff-only "$SHA"
if [[ "$(git rev-parse HEAD)" != "$SHA" ]]; then
  fail "main did not fast-forward to the accepted SHA"
  exit 1
fi
git push "$PUSH_URL" HEAD:refs/heads/main
wait_for_exact_ci main "$SHA"
MAIN_CI_URL=$CI_RUN_URL

wait_for_pages_parity "$SHA"
LOCAL_CLIENT_OUTPUT=$(./tools/client-install-test.sh \
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip" local)
printf '%s\n' "$LOCAL_CLIENT_OUTPUT"
EXPECTED_MODSET_SHA256=$(printf '%s\n' "$LOCAL_CLIENT_OUTPUT" |
  sed -n 's/^Client mod-set SHA-256: //p')
[[ "$EXPECTED_MODSET_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
  fail "Accepted local client install did not report one canonical mod-set SHA-256"
  exit 1
}
EXPECTED_PAYLOAD_SHA256=$(printf '%s\n' "$LOCAL_CLIENT_OUTPUT" |
  sed -n 's/^Client payload SHA-256: //p')
[[ "$EXPECTED_PAYLOAD_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
  fail "Accepted local client install did not report one canonical payload SHA-256"
  exit 1
}
./tools/client-install-test.sh \
  "$PUBLIC_ROOT/AFTERLIGHT-prism-instance.zip" production \
  "$EXPECTED_MODSET_SHA256" \
  "$EXPECTED_PAYLOAD_SHA256"
wait_for_pages_parity "$SHA"
git tag -a "$TAG" "$SHA" -F "$TAG_MESSAGE_FILE"
git push "$PUSH_URL" "refs/tags/$TAG:refs/tags/$TAG"
git switch "$START_BRANCH"
BRANCH_CHANGED=0

printf 'PROMOTION: CODE ACCEPTED %s\n' "$SHA"
printf 'DEV_CI_URL=%s\n' "$DEV_CI_URL"
printf 'MAIN_CI_URL=%s\n' "$MAIN_CI_URL"
printf 'PAGES_PACK_SHA=%s\n' "$PAGES_PACK_SHA"
printf 'PAGES_INDEX_SHA=%s\n' "$PAGES_INDEX_SHA"
printf 'RECEIPT_SHA256=%s\n' "$RECEIPT_SHA256"
