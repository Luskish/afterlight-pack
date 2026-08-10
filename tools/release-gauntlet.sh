#!/usr/bin/env bash
# Run the repeatable, local release gates for one exact clean commit.
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

run() {
  printf '\n$'
  printf ' %s' "$@"
  printf '\n'
  {
    printf '\n$'
    printf ' %s' "$@"
    printf '\n'
  } >> "$TRANSCRIPT"
  "$@" 2>&1 | tee -a "$TRANSCRIPT"
}

run_build() {
  local output_directory=$1
  printf '\n$ DIST_DIR=%s GIT_SHA=%s ./tools/build-release.sh\n' "$output_directory" "$GAUNTLET_SHA"
  printf '\n$ DIST_DIR=%s GIT_SHA=%s ./tools/build-release.sh\n' "$output_directory" "$GAUNTLET_SHA" >> "$TRANSCRIPT"
  DIST_DIR="$output_directory" GIT_SHA="$GAUNTLET_SHA" ./tools/build-release.sh 2>&1 | tee -a "$TRANSCRIPT"
}

require_clean_tree() {
  local status
  printf '\n$ git status --porcelain --untracked-files=all\n'
  printf '\n$ git status --porcelain --untracked-files=all\n' >> "$TRANSCRIPT"
  status=$(git status --porcelain --untracked-files=all)
  if [ -n "$status" ]; then
    printf '%s\n' "$status" | tee -a "$TRANSCRIPT"
    fail "the detached worktree is not clean"
  fi
  return 0
}

inner() {
  GAUNTLET_SHA=${GAUNTLET_SHA:?GAUNTLET_SHA is required}
  GAUNTLET_ENV=${GAUNTLET_ENV:?GAUNTLET_ENV is required}
  GAUNTLET_OUTPUT_DIR=${GAUNTLET_OUTPUT_DIR:?GAUNTLET_OUTPUT_DIR is required}
  cd "$REPOSITORY_ROOT"
  # shellcheck disable=SC1091
  source tools/versions.env
  export PATH="$PATH_EXTRA:$PATH"

  TRANSCRIPT="$REPOSITORY_ROOT/dist/.release-gauntlet-transcript.txt"
  FIRST="$REPOSITORY_ROOT/dist/.release-gauntlet-first"
  SECOND="$REPOSITORY_ROOT/dist/.release-gauntlet-second"
  rm -rf "$FIRST" "$SECOND" "$TRANSCRIPT"
  mkdir -p "$FIRST" "$SECOND"
  : > "$TRANSCRIPT"

  run python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
  run ./tools/verify-pack.sh
  run env BOOT_TIMEOUT=600 ./tools/server-test.sh
  run docker compose --project-name afterlight-gauntlet --env-file "$GAUNTLET_ENV" -f server/docker-compose.yml config --quiet
  rm -f "$GAUNTLET_ENV"

  SHELL_FILES=$(git ls-files '*.sh')
  [ -n "$SHELL_FILES" ] || fail "no tracked Bash files found for ShellCheck"
  while IFS= read -r shell_file; do
    run shellcheck -x "$shell_file"
  done <<EOF
$SHELL_FILES
EOF

  run_build "$FIRST"
  run_build "$SECOND"
  run cmp "$FIRST/AFTERLIGHT-prism-instance.zip" "$SECOND/AFTERLIGHT-prism-instance.zip"
  run ./tools/client-install-test.sh "$FIRST/AFTERLIGHT-prism-instance.zip"
  run git diff --exit-code
  require_clean_tree

  STARTED_AT=${GAUNTLET_STARTED_AT:?GAUNTLET_STARTED_AT is required}
  if [ -x "${JAVA_HOME:-}/bin/java" ]; then
    JAVA_BINARY="$JAVA_HOME/bin/java"
  else
    JAVA_BINARY=$(command -v java) || fail "Java is not available"
  fi
  JAVA_VERSION=$("$JAVA_BINARY" -version 2>&1)
  JAVA_VERSION=${JAVA_VERSION%%$'\n'*}
  JAVA_VERSION_PATTERN='^(openjdk|java) version "([0-9]+)([.][0-9]+)*"([[:space:]][^"]*)?$'
  [[ "$JAVA_VERSION" =~ $JAVA_VERSION_PATTERN ]] || fail "malformed or missing Java version: $JAVA_VERSION"
  JAVA_MAJOR=${BASH_REMATCH[2]}
  [ "$JAVA_MAJOR" = "21" ] || fail "Java 21 is required: $JAVA_VERSION"
  PACKWIZ_BINARY=$(command -v packwiz) || fail "packwiz is not on PATH"
  PACKWIZ_BUILD=$(go version -m "$PACKWIZ_BINARY")
  PACKWIZ_PATH=$(printf '%s\n' "$PACKWIZ_BUILD" | awk '$1 == "path" {print $2}')
  PACKWIZ_VERSION=$(printf '%s\n' "$PACKWIZ_BUILD" | awk '$1 == "mod" && $2 == "github.com/packwiz/packwiz" {print $3}')
  [ "$PACKWIZ_PATH" = "github.com/packwiz/packwiz" ] || fail "unexpected Packwiz module path: $PACKWIZ_PATH"
  [ -n "$PACKWIZ_VERSION" ] || fail "missing Packwiz module version"
  case "$PACKWIZ_VERSION" in *dfd8b68a4796*) ;; *) fail "unexpected Packwiz module version: $PACKWIZ_VERSION";; esac
  PACK_VERSION=$(sed -n 's/^version = "\(.*\)"$/\1/p' pack.toml | head -n 1)
  MINECRAFT_VERSION=$(sed -n 's/^minecraft = "\(.*\)"$/\1/p' pack.toml | head -n 1)
  NEOFORGE_VERSION=$(sed -n 's/^neoforge = "\(.*\)"$/\1/p' pack.toml | head -n 1)
  PRISM_SHA256=$(shasum -a 256 "$FIRST/AFTERLIGHT-prism-instance.zip" | awk '{print $1}')
  PACK_SHA256=$(shasum -a 256 pack.toml | awk '{print $1}')
  INDEX_SHA256=$(shasum -a 256 index.toml | awk '{print $1}')

  if [ -e "$GAUNTLET_OUTPUT_DIR" ] || [ -L "$GAUNTLET_OUTPUT_DIR" ]; then
    fail "controller output already exists: $GAUNTLET_OUTPUT_DIR"
  fi
  OUTPUT_PARENT=$(dirname "$GAUNTLET_OUTPUT_DIR")
  mkdir -p "$OUTPUT_PARENT"
  STAGING=$(mktemp -d "$OUTPUT_PARENT/.${GAUNTLET_SHA}.staging.XXXXXX")
  trap 'rm -rf "$STAGING"' EXIT
  mkdir -p "$STAGING/public" "$STAGING/friends-only"
  cp "$FIRST/AFTERLIGHT-prism-instance.zip" "$STAGING/public/"
  cp "$FIRST/release-metadata.json" "$STAGING/public/"
  cp "$FIRST/SHA256SUMS" "$STAGING/public/"
  cp "$FIRST/AFTERLIGHT-${PACK_VERSION}.mrpack" "$STAGING/friends-only/"
  cp "$FIRST/AFTERLIGHT-${PACK_VERSION}-curseforge.zip" "$STAGING/friends-only/"
  FINISHED_AT=$(date -u '+%Y-%m-%dT%H:%M:%SZ')
  {
    printf 'AFTERLIGHT release gauntlet\n'
    printf 'SHA: %s\n' "$GAUNTLET_SHA"
    printf 'UTC start: %s\n' "$STARTED_AT"
    printf 'UTC finish: %s\n' "$FINISHED_AT"
    printf 'Java: %s\n' "$JAVA_VERSION"
    printf 'Packwiz: %s %s\n' "$PACKWIZ_PATH" "$PACKWIZ_VERSION"
    printf 'Pack version: %s\n' "$PACK_VERSION"
    printf 'Minecraft version: %s\n' "$MINECRAFT_VERSION"
    printf 'NeoForge version: %s\n' "$NEOFORGE_VERSION"
    printf 'Prism SHA-256: %s\n' "$PRISM_SHA256"
    printf 'Pack SHA-256: %s\n' "$PACK_SHA256"
    printf 'Index SHA-256: %s\n' "$INDEX_SHA256"
    printf '\nCommand transcript:\n'
    cat "$TRANSCRIPT"
  } > "$STAGING/gauntlet.txt"
  mv "$STAGING" "$GAUNTLET_OUTPUT_DIR"
  STAGING=""

  echo "GAUNTLET: ACCEPTED $GAUNTLET_SHA"
}

outer() {
  [ "$#" -eq 1 ] || fail "usage: $0 <exact-40-character-commit-sha>"
  REQUESTED_SHA=$1
  [ "${#REQUESTED_SHA}" -eq 40 ] || fail "commit SHA must be exactly 40 lowercase hexadecimal characters"
  case "$REQUESTED_SHA" in
    *[!0123456789abcdef]*)
      fail "commit SHA must be exactly 40 lowercase hexadecimal characters"
      ;;
  esac

  cd "$REPOSITORY_ROOT"
  [ -z "$(git status --porcelain --untracked-files=all)" ] || fail "controller tree is not clean"
  HEAD_SHA=$(git rev-parse HEAD)
  RESOLVED_SHA=$(git rev-parse --verify "${REQUESTED_SHA}^{commit}") || fail "commit is not reachable locally: $REQUESTED_SHA"
  [ "$RESOLVED_SHA" = "$REQUESTED_SHA" ] || fail "commit SHA must not be abbreviated"
  [ "$HEAD_SHA" = "$REQUESTED_SHA" ] || fail "commit SHA is not the exact clean HEAD"

  OUTPUT_DIR="$REPOSITORY_ROOT/dist/gauntlet/$REQUESTED_SHA"
  if [ -e "$OUTPUT_DIR" ] || [ -L "$OUTPUT_DIR" ]; then
    fail "controller output already exists: $OUTPUT_DIR"
  fi

  WORKTREE=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-gauntlet.XXXXXX")
  cleanup() {
    if [ -n "${WORKTREE:-}" ] && [ -d "$WORKTREE" ]; then
      git -C "$REPOSITORY_ROOT" worktree remove --force "$WORKTREE" || true
      rm -rf "$WORKTREE"
      WORKTREE=""
    fi
  }
  trap cleanup EXIT
  trap 'exit 1' HUP INT TERM

  git worktree add --detach "$WORKTREE" "$REQUESTED_SHA"
  cp "$WORKTREE/server/.env.example" "$WORKTREE/server/.env.gauntlet"
  AFTERLIGHT_GAUNTLET_INNER=1 \
    GAUNTLET_SHA="$REQUESTED_SHA" \
    GAUNTLET_ENV="$WORKTREE/server/.env.gauntlet" \
    GAUNTLET_OUTPUT_DIR="$OUTPUT_DIR" \
    GAUNTLET_STARTED_AT="$(date -u '+%Y-%m-%dT%H:%M:%SZ')" \
    "$WORKTREE/tools/release-gauntlet.sh"
}

if [ "${AFTERLIGHT_GAUNTLET_INNER:-}" = "1" ]; then
  inner "$@"
else
  outer "$@"
fi
