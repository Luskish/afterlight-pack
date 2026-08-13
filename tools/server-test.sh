#!/usr/bin/env bash
# Headless AFTERLIGHT server boot test. Pure JVM, no Docker required.
# Exit 0 means the server reached Done, passed the audit, and shut down cleanly.
# Exit codes: 1 boot failed | 2 missing tool | 3 download failed | 4 port in use
#             5 serve not ready | 6 NeoForge install failed | 7 pack install failed
#             8 audit or boot oracle failed | 9 RC hygiene validation failed
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
export PATH="$PATH_EXTRA:$PATH"

DIR=server-test
BOOT_TIMEOUT=${BOOT_TIMEOUT:-420}
SERVE_PORT=${SERVE_PORT:-8199}
SERVER_PORT=${SERVER_PORT:-25599}
AFTERLIGHT_CACHE_DIR=${AFTERLIGHT_CACHE_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/afterlight}
NEOFORGE_INSTALLER_CACHE="$AFTERLIGHT_CACHE_DIR/neoforge-${NEOFORGE_VERSION}-installer.jar"
PACKWIZ_INSTALLER_CACHE="$AFTERLIGHT_CACHE_DIR/packwiz-installer-${PACKWIZ_INSTALLER_VERSION}.jar"
RUN_ID="${GITHUB_RUN_ID:-local}-$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM}"
EVIDENCE_DIR="$DIR/evidence/$RUN_ID"
SERVE_PID=""
SERVER_PID=""
NEOFORGE_INSTALLER_TMP=""
PACKWIZ_INSTALLER_TMP=""
RUN_FILES_FRESH=0

if ! python3 - "$DIR" "$EVIDENCE_DIR" <<'PY'
import os
import stat
import sys
from pathlib import Path

for raw_candidate in sys.argv[1:]:
    candidate = Path(os.path.abspath(raw_candidate))
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            break
        if stat.S_ISLNK(current_stat.st_mode):
            print(f"FAIL: symlink in install or evidence path: {current}")
            raise SystemExit(1)
PY
then
  exit 9
fi
python3 tools/rc_hygiene.py verify-install-root --install "$DIR" --allow-missing >/dev/null

mkdir -p "$EVIDENCE_DIR"
cat > "$EVIDENCE_DIR/afterlight-run-marker.txt" <<MARKER
run_id=$RUN_ID
started_utc=$(date -u +%Y-%m-%dT%H:%M:%SZ)
pid=$$
MARKER

copy_evidence() {
  local source_path=$1
  local destination_path=$2
  if [ -f "$source_path" ]; then
    mkdir -p "$(dirname "$EVIDENCE_DIR/$destination_path")"
    if ! cp "$source_path" "$EVIDENCE_DIR/$destination_path"; then
      echo "WARN: could not capture evidence $source_path" >&2
    fi
  fi
}

cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    if ! kill -TERM -- "-$SERVER_PID" 2>/dev/null; then
      if ! kill -TERM "$SERVER_PID" 2>/dev/null; then
        :
      fi
    fi
    if ! wait "$SERVER_PID" 2>/dev/null; then
      :
    fi
  fi
  if [ -n "$SERVE_PID" ] && kill -0 "$SERVE_PID" 2>/dev/null; then
    if ! kill "$SERVE_PID"; then
      :
    fi
    if ! wait "$SERVE_PID" 2>/dev/null; then
      :
    fi
  fi
  if [ -n "$NEOFORGE_INSTALLER_TMP" ]; then
    rm -f "$NEOFORGE_INSTALLER_TMP"
  fi
  if [ -n "$PACKWIZ_INSTALLER_TMP" ]; then
    rm -f "$PACKWIZ_INSTALLER_TMP"
  fi
}

capture_evidence() {
  local status=$1
  printf '%s\n' "$status" > "$EVIDENCE_DIR/harness-exit-status.txt"
  if [ "$RUN_FILES_FRESH" -eq 1 ]; then
    copy_evidence "$DIR/installer.log" "installer.log"
    copy_evidence "$DIR/packwiz-install.log" "packwiz-install.log"
    copy_evidence "$DIR/boot.log" "boot.log"
    copy_evidence "$DIR/logs/latest.log" "logs/latest.log"
    copy_evidence "$DIR/logs/debug.log" "logs/debug.log"
    copy_evidence "$DIR/logs/kubejs/server.log" "logs/kubejs/server.log"
    copy_evidence "$DIR/afterlight-audit-nonce.txt" "afterlight-audit-nonce.txt"
    copy_evidence "$DIR/afterlight-runtime-audit-provenance.json" "afterlight-runtime-audit-provenance.json"
    copy_evidence "$DIR/afterlight-server-exit-status.txt" "afterlight-server-exit-status.txt"
    copy_evidence "$DIR/packwiz.json" "packwiz.json"
    copy_evidence "$DIR/afterlight-provenance.txt" "afterlight-provenance.txt"
    copy_evidence "$DIR/afterlight-live-tests-ready.txt" "afterlight-live-tests-ready.txt"
  fi
}

finish() {
  local status=$1
  trap - EXIT INT TERM
  cleanup
  capture_evidence "$status"
  exit "$status"
}

trap 'finish $?' EXIT
trap 'exit 130' INT TERM

JAVA_HOME=${JAVA_HOME:-}
JAVA=${JAVA_HOME:+$JAVA_HOME/bin/java}
if [ ! -x "$JAVA" ]; then
  if JAVA_CANDIDATE=$(command -v java 2>/dev/null); then
    JAVA="$JAVA_CANDIDATE"
  else
    JAVA=""
  fi
fi
if [ -z "$JAVA" ] || [ ! -x "$JAVA" ]; then
  echo "need a working Java 21 runtime"
  exit 2
fi
if ! JAVA_VERSION_OUTPUT=$("$JAVA" -version 2>&1); then
  echo "need a working Java 21 runtime"
  exit 2
fi
case "$(printf '%s\n' "$JAVA_VERSION_OUTPUT" | head -1)" in
  *'version "21.'*) ;;
  *)
    echo "need a working Java 21 runtime"
    exit 2
    ;;
esac
RESOLVED_JAVA_HOME=$("$JAVA" -XshowSettings:properties -version 2>&1 | sed -n 's/^[[:space:]]*java.home = //p' | head -1)
if [ -n "$RESOLVED_JAVA_HOME" ]; then
  JAVA_HOME="$RESOLVED_JAVA_HOME"
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

BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/download/v${PACKWIZ_BOOTSTRAP_VERSION}/packwiz-installer-bootstrap.jar"
PACKWIZ_INSTALLER_URL="https://github.com/packwiz/packwiz-installer/releases/download/v${PACKWIZ_INSTALLER_VERSION}/packwiz-installer.jar"

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

if ! python3 - "$SERVE_PORT" <<'PY'
import socket
import sys

port = int(sys.argv[1])
socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    socket.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    socket.close()
PY
then
  echo "FAIL: port ${SERVE_PORT} already in use"
  exit 4
fi

packwiz serve --refresh=false --port "$SERVE_PORT" &
SERVE_PID=$!

READY=0
for _ in $(seq 1 20); do
  if ! kill -0 "$SERVE_PID" 2>/dev/null; then
    echo "FAIL: packwiz serve exited before readiness"
    if ! wait "$SERVE_PID"; then
      :
    fi
    exit 4
  fi
  if curl -sf "http://localhost:${SERVE_PORT}/pack.toml" >/dev/null 2>&1; then
    READY=1
    break
  fi
  sleep 0.5
done
if ! kill -0 "$SERVE_PID" 2>/dev/null; then
  echo "FAIL: packwiz serve exited before readiness"
  if ! wait "$SERVE_PID"; then
    :
  fi
  exit 4
fi
if [ "$READY" -ne 1 ]; then
  echo "FAIL: packwiz serve not ready on port ${SERVE_PORT}"
  exit 5
fi
assert_manifest_unchanged

mkdir -p "$DIR"
find "$DIR" -mindepth 1 -maxdepth 1 ! -name evidence -exec rm -rf {} +
RUN_FILES_FRESH=1
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
  ACTUAL_NEOFORGE_SHA256=$(shasum -a 256 "$NEOFORGE_INSTALLER_TMP" | awk '{print $1}')
  if [ "$ACTUAL_NEOFORGE_SHA256" != "$NEOFORGE_INSTALLER_SHA256" ]; then
    rm -f "$NEOFORGE_INSTALLER_TMP"
    echo "FAIL: NEOFORGE_INSTALLER_SHA256 mismatch"
    echo "expected $NEOFORGE_INSTALLER_SHA256"
    echo "actual   $ACTUAL_NEOFORGE_SHA256"
    exit 3
  fi
  mv "$NEOFORGE_INSTALLER_TMP" "$NEOFORGE_INSTALLER_CACHE"
  NEOFORGE_INSTALLER_TMP=""
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

if [ -f "$PACKWIZ_INSTALLER_CACHE" ]; then
  ACTUAL_PACKWIZ_INSTALLER_SIZE=$(wc -c < "$PACKWIZ_INSTALLER_CACHE" | tr -d '[:space:]')
  ACTUAL_PACKWIZ_INSTALLER_SHA256=$(shasum -a 256 "$PACKWIZ_INSTALLER_CACHE" | awk '{print $1}')
  if [ "$ACTUAL_PACKWIZ_INSTALLER_SIZE" != "$PACKWIZ_INSTALLER_SIZE" ]; then
    rm -f "$PACKWIZ_INSTALLER_CACHE"
    echo "FAIL: PACKWIZ_INSTALLER size mismatch"
    echo "expected $PACKWIZ_INSTALLER_SIZE"
    echo "actual   $ACTUAL_PACKWIZ_INSTALLER_SIZE"
    exit 3
  fi
  if [ "$ACTUAL_PACKWIZ_INSTALLER_SHA256" != "$PACKWIZ_INSTALLER_SHA256" ]; then
    rm -f "$PACKWIZ_INSTALLER_CACHE"
    echo "FAIL: PACKWIZ_INSTALLER SHA-256 mismatch"
    echo "expected $PACKWIZ_INSTALLER_SHA256"
    echo "actual   $ACTUAL_PACKWIZ_INSTALLER_SHA256"
    exit 3
  fi
else
  PACKWIZ_INSTALLER_TMP="${PACKWIZ_INSTALLER_CACHE}.tmp.$$"
  if ! curl -sfL -o "$PACKWIZ_INSTALLER_TMP" "$PACKWIZ_INSTALLER_URL"; then
    rm -f "$PACKWIZ_INSTALLER_TMP"
    echo "FAIL: download Packwiz installer ${PACKWIZ_INSTALLER_VERSION} ($PACKWIZ_INSTALLER_URL)"
    exit 3
  fi
  ACTUAL_PACKWIZ_INSTALLER_SIZE=$(wc -c < "$PACKWIZ_INSTALLER_TMP" | tr -d '[:space:]')
  ACTUAL_PACKWIZ_INSTALLER_SHA256=$(shasum -a 256 "$PACKWIZ_INSTALLER_TMP" | awk '{print $1}')
  if [ "$ACTUAL_PACKWIZ_INSTALLER_SIZE" != "$PACKWIZ_INSTALLER_SIZE" ]; then
    rm -f "$PACKWIZ_INSTALLER_TMP"
    echo "FAIL: PACKWIZ_INSTALLER size mismatch"
    echo "expected $PACKWIZ_INSTALLER_SIZE"
    echo "actual   $ACTUAL_PACKWIZ_INSTALLER_SIZE"
    exit 3
  fi
  if [ "$ACTUAL_PACKWIZ_INSTALLER_SHA256" != "$PACKWIZ_INSTALLER_SHA256" ]; then
    rm -f "$PACKWIZ_INSTALLER_TMP"
    echo "FAIL: PACKWIZ_INSTALLER SHA-256 mismatch"
    echo "expected $PACKWIZ_INSTALLER_SHA256"
    echo "actual   $ACTUAL_PACKWIZ_INSTALLER_SHA256"
    exit 3
  fi
  mv "$PACKWIZ_INSTALLER_TMP" "$PACKWIZ_INSTALLER_CACHE"
  PACKWIZ_INSTALLER_TMP=""
fi
cp "$PACKWIZ_INSTALLER_CACHE" "$DIR/packwiz-installer.jar"
if [ ! -f "$DIR/packwiz-installer.jar" ]; then
  echo "FAIL: packwiz-installer.jar missing before bootstrap execution"
  exit 3
fi
ACTUAL_PACKWIZ_INSTALLER_SIZE=$(wc -c < "$DIR/packwiz-installer.jar" | tr -d '[:space:]')
ACTUAL_PACKWIZ_INSTALLER_SHA256=$(shasum -a 256 "$DIR/packwiz-installer.jar" | awk '{print $1}')
if [ "$ACTUAL_PACKWIZ_INSTALLER_SIZE" != "$PACKWIZ_INSTALLER_SIZE" ]; then
  echo "FAIL: PACKWIZ_INSTALLER size mismatch after cache copy"
  exit 3
fi
if [ "$ACTUAL_PACKWIZ_INSTALLER_SHA256" != "$PACKWIZ_INSTALLER_SHA256" ]; then
  echo "FAIL: PACKWIZ_INSTALLER SHA-256 mismatch after cache copy"
  exit 3
fi

if ! curl -sfL -o "$DIR/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL"; then
  echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)"
  exit 3
fi
ACTUAL_BOOTSTRAP_SHA256=$(shasum -a 256 "$DIR/packwiz-installer-bootstrap.jar" | awk '{print $1}')
if [ "$ACTUAL_BOOTSTRAP_SHA256" != "$PACKWIZ_BOOTSTRAP_SHA256" ]; then
  echo "FAIL: packwiz-installer-bootstrap SHA-256 mismatch"
  echo "expected $PACKWIZ_BOOTSTRAP_SHA256"
  echo "actual   $ACTUAL_BOOTSTRAP_SHA256"
  exit 3
fi
if ! (cd "$DIR" && "$JAVA" -jar packwiz-installer-bootstrap.jar --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g -s server "http://localhost:${SERVE_PORT}/pack.toml" > packwiz-install.log 2>&1); then
  echo "FAIL: packwiz-installer server side"
  tail -30 "$DIR/packwiz-install.log"
  exit 7
fi
assert_manifest_unchanged
python3 tools/build_server_mod_manifest_lock.py \
  --repository . \
  --installed-mods "$DIR/mods" \
  --output "$DIR/server-mod-manifest-lock.json"
if ! cmp -s tools/server-mod-manifest-lock.json "$DIR/server-mod-manifest-lock.json"; then
  echo "FAIL: server mod manifest lock differs from the clean Packwiz install"
  exit 7
fi
python3 tools/rc_hygiene.py verify-provenance --root . --install "$DIR" | tee "$DIR/afterlight-provenance.txt"
python3 tools/rc_hygiene.py verify-seal-sources --root . --install "$DIR"

python3 tools/rc_hygiene.py render-installed-quest-audits --root . --install "$DIR" --nonce "$AUDIT_NONCE"
python3 tools/rc_hygiene.py verify-quest-audits --root . --install "$DIR" --nonce "$AUDIT_NONCE"

GATE_AUDIT_SCRIPT="$DIR/kubejs/server_scripts/afterlight/gate_recipe_audit.js"
if [ ! -f "$GATE_AUDIT_SCRIPT" ]; then
  echo "FAIL: Gate recipe audit script missing"
  exit 7
fi
python3 tools/rc_hygiene.py render-installed-gate-audit --root . --install "$DIR" --nonce "$AUDIT_NONCE"
python3 tools/rc_hygiene.py verify-gate-audit --root . --install "$DIR" --nonce "$AUDIT_NONCE"

echo "eula=true" > "$DIR/eula.txt"
cat > "$DIR/server.properties" <<PROPS
level-seed=afterlight-ci
server-port=$SERVER_PORT
PROPS

set +e
python3 -c '
import os
import sys

os.chdir(sys.argv[1])
read_fd, write_fd = os.pipe()
os.write(write_fd, b"stop\n")
os.close(write_fd)
os.dup2(read_fd, 0)
os.close(read_fd)
os.setsid()
os.execv(sys.argv[2], [sys.argv[2], sys.argv[3], "./run.sh", "nogui"])
' "$DIR" "$TIMEOUT_BIN" "$BOOT_TIMEOUT" > "$DIR/boot.log" 2>&1 &
SERVER_PID=$!
wait "$SERVER_PID"
SERVER_STATUS=$?
SERVER_PID=""
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

PACK_SHA256=$(shasum -a 256 pack.toml | awk '{print $1}')
INDEX_SHA256=$(shasum -a 256 index.toml | awk '{print $1}')
cat > "$DIR/afterlight-live-tests-ready.txt" <<READY
run_id=$RUN_ID
nonce=$AUDIT_NONCE
pack_sha256=$PACK_SHA256
index_sha256=$INDEX_SHA256
READY

if ! AFTERLIGHT_REQUIRE_LIVE_TESTS=1 AFTERLIGHT_LIVE_RUN_ID="$RUN_ID" \
  python3 -m unittest discover -s tools/tests -p 'test_*.py'; then
  echo "SERVER BOOT: FAILED: authenticated live Python suite did not pass"
  exit 9
fi
assert_manifest_unchanged

echo "SERVER BOOT: OK"
