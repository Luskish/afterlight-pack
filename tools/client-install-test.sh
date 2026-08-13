#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

PRISM_ZIP=${1:-dist/AFTERLIGHT-prism-instance.zip}
INSTALL_MODE=${2:-local}
EXPECTED_MODSET_SHA256=${3:-}
EXPECTED_PAYLOAD_SHA256=${4:-}
PACK_URL=https://luskish.github.io/afterlight-pack/pack.toml
INSTALL_PACK_URL=""
SERVE_PID=""
TEMP_ROOT=$(mktemp -d "${TMPDIR:-/tmp}/afterlight-client-install.XXXXXX")
INSTANCE_DIR="$TEMP_ROOT/instance"
PRISM_DIR="$TEMP_ROOT/prism"

fail() {
  echo "FAIL: $*" >&2
  exit 2
}

if [ "$#" -gt 4 ]; then
  fail "usage: $0 [prism-archive] [local|production] [expected-modset-sha256] [expected-payload-sha256]"
fi
case "$INSTALL_MODE" in
  local|production) ;;
  *) fail "usage: $0 [prism-archive] [local|production] [expected-modset-sha256] [expected-payload-sha256]" ;;
esac
if [ "$INSTALL_MODE" = production ]; then
  [[ "$EXPECTED_MODSET_SHA256" =~ ^[0-9a-f]{64}$ ]] ||
    fail "production install requires the accepted client mod-set SHA-256"
  [[ "$EXPECTED_PAYLOAD_SHA256" =~ ^[0-9a-f]{64}$ ]] ||
    fail "production install requires the accepted client payload SHA-256"
elif [ -n "$EXPECTED_MODSET_SHA256" ] || [ -n "$EXPECTED_PAYLOAD_SHA256" ]; then
  fail "expected client digests are valid only in production mode"
fi

cleanup() {
  local status=$?
  trap - EXIT HUP INT TERM
  if [ -n "$SERVE_PID" ] && kill -0 "$SERVE_PID" 2>/dev/null; then
    kill "$SERVE_PID" 2>/dev/null || true
    wait "$SERVE_PID" 2>/dev/null || true
  fi
  rm -rf -- "$TEMP_ROOT"
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' HUP INT TERM

for command_name in curl packwiz python3 unzip; do
  command -v "$command_name" >/dev/null 2>&1 || fail "$command_name is required"
done

JAVA=""
if [ -x "${JAVA_HOME:-}/bin/java" ]; then
  JAVA="$JAVA_HOME/bin/java"
elif JAVA_CANDIDATE=$(command -v java 2>/dev/null); then
  JAVA="$JAVA_CANDIDATE"
fi
if [ -z "$JAVA" ] || [ ! -x "$JAVA" ]; then
  fail "need a working Java 21 runtime"
fi
if ! JAVA_VERSION_OUTPUT=$("$JAVA" -version 2>&1); then
  fail "need a working Java 21 runtime"
fi
case "$(printf '%s\n' "$JAVA_VERSION_OUTPUT" | head -1)" in
  *'version "21.'*) ;;
  *) fail "need a working Java 21 runtime" ;;
esac

if [ ! -f "$PRISM_ZIP" ] || [ -L "$PRISM_ZIP" ]; then
  fail "Prism archive is not a regular file: $PRISM_ZIP"
fi
python3 tools/release_artifacts.py inspect-prism \
  --archive "$PRISM_ZIP" \
  --pack-url "$PACK_URL" \
  --bootstrap-sha256 "$PACKWIZ_BOOTSTRAP_SHA256" \
  --installer-sha256 "$PACKWIZ_INSTALLER_SHA256" \
  --installer-size "$PACKWIZ_INSTALLER_SIZE" >/dev/null

mkdir -p "$INSTANCE_DIR" "$PRISM_DIR"
unzip -qq "$PRISM_ZIP" -d "$PRISM_DIR"
cp "$PRISM_DIR/.minecraft/packwiz-installer-bootstrap.jar" "$INSTANCE_DIR/"
cp "$PRISM_DIR/.minecraft/packwiz-installer.jar" "$INSTANCE_DIR/"

MANIFEST_STATE=$(shasum -a 256 pack.toml index.toml)
if [ "$INSTALL_MODE" = production ]; then
  INSTALL_PACK_URL="$PACK_URL"
else
  SERVE_PORT=${CLIENT_SERVE_PORT:-$(python3 - <<'PY'
import socket

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
    listener.bind(("127.0.0.1", 0))
    print(listener.getsockname()[1])
PY
  )}
  packwiz serve --refresh=false --port "$SERVE_PORT" >"$TEMP_ROOT/packwiz-serve.log" 2>&1 &
  SERVE_PID=$!
  READY=0
  for _ in $(seq 1 40); do
    if ! kill -0 "$SERVE_PID" 2>/dev/null; then
      cat "$TEMP_ROOT/packwiz-serve.log" >&2
      fail "packwiz serve exited before client-install readiness"
    fi
    if curl -fsS "http://127.0.0.1:${SERVE_PORT}/pack.toml" >/dev/null 2>&1; then
      READY=1
      break
    fi
    sleep 0.25
  done
  [ "$READY" -eq 1 ] || fail "packwiz serve did not become ready"
  LOCAL_PACK_URL="http://127.0.0.1:${SERVE_PORT}/pack.toml"
  INSTALL_PACK_URL="$LOCAL_PACK_URL"
fi

run_installer() {
  (
    cd "$INSTANCE_DIR"
    "$JAVA" -jar packwiz-installer-bootstrap.jar \
      --bootstrap-no-update \
      --bootstrap-main-jar packwiz-installer.jar \
      -g "$INSTALL_PACK_URL"
  )
}

run_installer
FIRST_SUMMARY=$(python3 tools/client_install_support.py \
  --instance-dir "$INSTANCE_DIR" \
  --mods-dir mods \
  --pack-root .)
FIRST_MODSET_SHA256=$(printf '%s' "$FIRST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["modset_sha256"])')
FIRST_PAYLOAD_SHA256=$(printf '%s' "$FIRST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["payload_sha256"])')
FIRST_CLIENT_COUNT=$(printf '%s' "$FIRST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["client_mod_count"])')
FIRST_SERVER_COUNT=$(printf '%s' "$FIRST_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["server_only_count"])')
[ "$FIRST_CLIENT_COUNT" = 157 ] || fail "client install count changed: $FIRST_CLIENT_COUNT"
[ "$FIRST_SERVER_COUNT" = 13 ] || fail "server-only exclusion count changed: $FIRST_SERVER_COUNT"
if [ -n "$EXPECTED_MODSET_SHA256" ]; then
  [ "$FIRST_MODSET_SHA256" = "$EXPECTED_MODSET_SHA256" ] ||
    fail "production client mod set differs from the accepted local install"
fi
if [ -n "$EXPECTED_PAYLOAD_SHA256" ]; then
  [ "$FIRST_PAYLOAD_SHA256" = "$EXPECTED_PAYLOAD_SHA256" ] ||
    fail "production client payload differs from the accepted local install"
fi

run_installer
SECOND_SUMMARY=$(python3 tools/client_install_support.py \
  --instance-dir "$INSTANCE_DIR" \
  --mods-dir mods \
  --pack-root .)
SECOND_MODSET_SHA256=$(printf '%s' "$SECOND_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["modset_sha256"])')
SECOND_PAYLOAD_SHA256=$(printf '%s' "$SECOND_SUMMARY" | python3 -c 'import json,sys; print(json.load(sys.stdin)["payload_sha256"])')
[ "$FIRST_MODSET_SHA256" = "$SECOND_MODSET_SHA256" ] || fail "second client update changed the mod set"
[ "$FIRST_PAYLOAD_SHA256" = "$SECOND_PAYLOAD_SHA256" ] || fail "second client update changed the payload"
if [ -n "$EXPECTED_MODSET_SHA256" ]; then
  [ "$SECOND_MODSET_SHA256" = "$EXPECTED_MODSET_SHA256" ] ||
    fail "second production client update differs from the accepted local install"
fi
if [ -n "$EXPECTED_PAYLOAD_SHA256" ]; then
  [ "$SECOND_PAYLOAD_SHA256" = "$EXPECTED_PAYLOAD_SHA256" ] ||
    fail "second production client update differs from the accepted local payload"
fi
[ "$MANIFEST_STATE" = "$(shasum -a 256 pack.toml index.toml)" ] || fail "client install changed Packwiz source"

printf 'Client mods: %s\n' "$FIRST_CLIENT_COUNT"
printf 'Server-only exclusions: %s\n' "$FIRST_SERVER_COUNT"
printf 'Client mod-set SHA-256: %s\n' "$FIRST_MODSET_SHA256"
printf 'Client payload SHA-256: %s\n' "$FIRST_PAYLOAD_SHA256"
echo "CLIENT INSTALL: OK"
