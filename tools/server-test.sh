#!/usr/bin/env bash
# Headless AFTERLIGHT server boot test. Pure JVM, no Docker required.
# Exit 0 means the server reached Done, passed the audit, and shut down cleanly.
# Exit codes: 1 boot failed | 2 missing tool | 3 download failed | 4 port in use
#             5 serve not ready | 6 NeoForge install failed | 7 pack install failed
#             8 quest or boot oracle failed | 9 RC hygiene validation failed
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

JAVA_HOME=${JAVA_HOME:-$(/usr/libexec/java_home -v 21)}
JAVA="$JAVA_HOME/bin/java"
if [ ! -x "$JAVA" ]; then
  JAVA=$(command -v java)
  JAVA_HOME=$(cd "$(dirname "$JAVA")/.." && pwd)
fi
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"

if command -v gtimeout >/dev/null 2>&1; then
  TIMEOUT_BIN=$(command -v gtimeout)
elif command -v timeout >/dev/null 2>&1; then
  TIMEOUT_BIN=$(command -v timeout)
else
  echo "need coreutils: brew install coreutils"
  exit 2
fi
command -v packwiz >/dev/null || {
  echo "need packwiz (go install github.com/packwiz/packwiz@latest)"
  exit 2
}

BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v0.0.3/packwiz-installer-bootstrap.jar"
BOOTSTRAP_SHA256="a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c"
DIR=server-test
BOOT_TIMEOUT=${BOOT_TIMEOUT:-420}
SERVE_PORT=${SERVE_PORT:-8199}
AFTERLIGHT_CACHE_DIR=${AFTERLIGHT_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/afterlight}
NEOFORGE_INSTALLER_CACHE="$AFTERLIGHT_CACHE_DIR/neoforge-${NEOFORGE_VERSION}-installer.jar"
SERVE_PID=""

python3 tools/rc_hygiene.py verify-manifest --root .
MANIFEST_STATE=$(shasum -a 256 pack.toml index.toml)

assert_manifest_unchanged() {
  local current_state
  current_state=$(shasum -a 256 pack.toml index.toml)
  if [ "$current_state" != "$MANIFEST_STATE" ]; then
    echo "FAIL: pack.toml or index.toml changed during server verification"
    exit 9
  fi
  python3 tools/rc_hygiene.py verify-manifest --root . >/dev/null
}

cleanup() {
  if [ -n "$SERVE_PID" ] && kill -0 "$SERVE_PID" 2>/dev/null; then
    if ! kill "$SERVE_PID"; then
      :
    fi
    if ! wait "$SERVE_PID" 2>/dev/null; then
      :
    fi
  fi
}

if curl -sf "http://localhost:${SERVE_PORT}/" >/dev/null 2>&1; then
  echo "FAIL: port ${SERVE_PORT} already in use"
  exit 4
fi

packwiz serve --refresh=false --port "$SERVE_PORT" &
SERVE_PID=$!
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM

READY=0
for _ in $(seq 1 20); do
  if curl -sf "http://localhost:${SERVE_PORT}/pack.toml" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.5
done
if [ "$READY" -ne 1 ]; then
  echo "FAIL: packwiz serve not ready on port ${SERVE_PORT}"
  exit 5
fi
assert_manifest_unchanged

rm -rf "$DIR"
mkdir -p "$DIR"
AUDIT_NONCE="$(date +%s)-$$-${RANDOM}"
printf '%s\n' "$AUDIT_NONCE" > "$DIR/afterlight-audit-nonce.txt"

NEOFORGE_URL="https://maven.neoforged.net/releases/net/neoforged/neoforge/${NEOFORGE_VERSION}/neoforge-${NEOFORGE_VERSION}-installer.jar"
mkdir -p "$AFTERLIGHT_CACHE_DIR"
if [ ! -f "$NEOFORGE_INSTALLER_CACHE" ]; then
  NEOFORGE_INSTALLER_TMP="${NEOFORGE_INSTALLER_CACHE}.tmp.$$"
  if ! curl -sfL -o "$NEOFORGE_INSTALLER_TMP" "$NEOFORGE_URL"; then
    rm -f "$NEOFORGE_INSTALLER_TMP"
    echo "FAIL: download NeoForge ${NEOFORGE_VERSION} installer ($NEOFORGE_URL)"
    exit 3
  fi
  mv "$NEOFORGE_INSTALLER_TMP" "$NEOFORGE_INSTALLER_CACHE"
fi
ACTUAL_NEOFORGE_SHA256=$(shasum -a 256 "$NEOFORGE_INSTALLER_CACHE" | awk '{print $1}')
if [ "$ACTUAL_NEOFORGE_SHA256" != "$NEOFORGE_INSTALLER_SHA256" ]; then
  rm -f "$NEOFORGE_INSTALLER_CACHE"
  echo "FAIL: NEOFORGE_INSTALLER_SHA256 mismatch"
  echo "expected $NEOFORGE_INSTALLER_SHA256"
  echo "actual   $ACTUAL_NEOFORGE_SHA256"
  exit 3
fi
cp "$NEOFORGE_INSTALLER_CACHE" "$DIR/neoforge-installer.jar"
ACTUAL_NEOFORGE_SHA256=$(shasum -a 256 "$DIR/neoforge-installer.jar" | awk '{print $1}')
if [ "$ACTUAL_NEOFORGE_SHA256" != "$NEOFORGE_INSTALLER_SHA256" ]; then
  echo "FAIL: NEOFORGE_INSTALLER_SHA256 mismatch after cache copy"
  echo "expected $NEOFORGE_INSTALLER_SHA256"
  echo "actual   $ACTUAL_NEOFORGE_SHA256"
  exit 3
fi
if ! (cd "$DIR" && "$JAVA" -jar neoforge-installer.jar --install-server . > installer.log 2>&1); then
  echo "FAIL: NeoForge server install"
  tail -30 "$DIR/installer.log"
  exit 6
fi
assert_manifest_unchanged

if ! curl -sfL -o "$DIR/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL"; then
  echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)"
  exit 3
fi
ACTUAL_BOOTSTRAP_SHA256=$(shasum -a 256 "$DIR/packwiz-installer-bootstrap.jar" | awk '{print $1}')
if [ "$ACTUAL_BOOTSTRAP_SHA256" != "$BOOTSTRAP_SHA256" ]; then
  echo "FAIL: packwiz-installer-bootstrap SHA-256 mismatch"
  echo "expected $BOOTSTRAP_SHA256"
  echo "actual   $ACTUAL_BOOTSTRAP_SHA256"
  exit 3
fi
if ! (cd "$DIR" && "$JAVA" -jar packwiz-installer-bootstrap.jar -g -s server "http://localhost:${SERVE_PORT}/pack.toml" > packwiz-install.log 2>&1); then
  echo "FAIL: packwiz-installer server side"
  tail -30 "$DIR/packwiz-install.log"
  exit 7
fi
assert_manifest_unchanged
python3 tools/rc_hygiene.py verify-provenance --root . --install "$DIR"

AUDIT_SCRIPT="$DIR/kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
if [ ! -f "$AUDIT_SCRIPT" ]; then
  echo "FAIL: generated quest item audit script missing"
  exit 7
fi
awk -v nonce="$AUDIT_NONCE" '{ gsub(/__AFTERLIGHT_BOOT_NONCE__/, nonce); print }' "$AUDIT_SCRIPT" > "$AUDIT_SCRIPT.tmp"
mv "$AUDIT_SCRIPT.tmp" "$AUDIT_SCRIPT"

echo "eula=true" > "$DIR/eula.txt"
cat > "$DIR/server.properties" <<'PROPS'
level-seed=afterlight-ci
server-port=25599
PROPS

set +e
(cd "$DIR" && printf 'stop\n' | "$TIMEOUT_BIN" "$BOOT_TIMEOUT" ./run.sh nogui > boot.log 2>&1)
SERVER_STATUS=$?
set -e
printf '%s\n' "$SERVER_STATUS" > "$DIR/afterlight-server-exit-status.txt"
assert_manifest_unchanged

if ! python3 tools/rc_hygiene.py verify-boot --root . --install "$DIR" --nonce "$AUDIT_NONCE" --status "$SERVER_STATUS"; then
  echo "SERVER BOOT: FAILED: authoritative boot oracle did not pass"
  if [ -f "$DIR/logs/latest.log" ]; then
    tail -50 "$DIR/logs/latest.log"
  elif [ -f "$DIR/boot.log" ]; then
    tail -50 "$DIR/boot.log"
  fi
  exit 8
fi

if ! python3 tools/tests/test_rc_hygiene_reliability.py; then
  echo "SERVER BOOT: FAILED: RC hygiene reliability probes did not pass"
  exit 9
fi
if ! python3 tools/tests/test_rc_hygiene.py; then
  echo "SERVER BOOT: FAILED: RC hygiene fixture validation did not pass"
  exit 9
fi
assert_manifest_unchanged

echo "SERVER BOOT: OK"
