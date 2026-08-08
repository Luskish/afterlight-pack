#!/usr/bin/env bash
# Headless AFTERLIGHT server boot test. Pure JVM, no Docker required.
# Exit 0 = server booted to "Done". Nonzero = failure; see server-test/logs/.
# Exit codes: 1 boot failed | 2 missing tool | 3 download failed | 4 port in use
#             5 serve not ready | 6 NeoForge install failed | 7 pack install failed
#             8 quest item registry audit failed | 9 RC hygiene validation failed
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
[ -n "${PATH_EXTRA:-}" ] && export PATH="$PATH_EXTRA:$PATH"
JAVA_HOME=${JAVA_HOME:-$(/usr/libexec/java_home -v 21)}
JAVA="$JAVA_HOME/bin/java"
# Resilience: if versions.env points at a JDK this runner doesn't have, fall back to
# whatever java is on PATH rather than dying on a stale hardcoded path.
[ -x "$JAVA" ] || { JAVA=$(command -v java); JAVA_HOME=$(cd "$(dirname "$JAVA")/.." && pwd); }
# NeoForge's generated run.sh invokes bare `java`; put the pinned JDK first on PATH
# (and export JAVA_HOME) so the server boots on the same JVM this script validates.
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"
TIMEOUT_BIN=$(command -v gtimeout || command -v timeout || true)
[ -z "$TIMEOUT_BIN" ] && { echo "need coreutils: brew install coreutils"; exit 2; }
command -v packwiz >/dev/null || { echo "need packwiz (go install github.com/packwiz/packwiz@latest)"; exit 2; }
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
DIR=server-test
BOOT_TIMEOUT=${BOOT_TIMEOUT:-420}
SERVE_PORT=${SERVE_PORT:-8199}

# 1) Serve the working-dir pack locally
# Refuse to run if something already owns the port. Otherwise packwiz stays alive
# without binding and the installer would silently pull from the foreign server.
# The guard and readiness poll need no scratch dir, so they run before the wipe:
# an abort here leaves the previous run's logs intact for diagnosis.
if curl -sf "http://localhost:${SERVE_PORT}/" >/dev/null 2>&1; then
  echo "FAIL: port ${SERVE_PORT} already in use"; exit 4
fi
cleanup() { kill "$SERVE_PID" 2>/dev/null || true; }
packwiz serve --port "$SERVE_PORT" & SERVE_PID=$!
trap cleanup EXIT
trap 'cleanup; exit 130' INT TERM
READY=0
for _ in $(seq 1 20); do
  if curl -sf "http://localhost:${SERVE_PORT}/pack.toml" >/dev/null 2>&1; then READY=1; break; fi
  sleep 0.5
done
[ "$READY" -eq 1 ] || { echo "FAIL: packwiz serve not ready on port ${SERVE_PORT}"; exit 5; }

rm -rf "$DIR" && mkdir -p "$DIR"
AUDIT_NONCE="$(date +%s)-$$-${RANDOM}"
printf '%s\n' "$AUDIT_NONCE" > "$DIR/afterlight-audit-nonce.txt"

# 2) Install NeoForge server
NEOFORGE_URL="https://maven.neoforged.net/releases/net/neoforged/neoforge/${NEOFORGE_VERSION}/neoforge-${NEOFORGE_VERSION}-installer.jar"
curl -sfL -o "$DIR/neoforge-installer.jar" "$NEOFORGE_URL" || { echo "FAIL: download NeoForge ${NEOFORGE_VERSION} installer ($NEOFORGE_URL)"; exit 3; }
(cd "$DIR" && "$JAVA" -jar neoforge-installer.jar --install-server . > installer.log 2>&1) || { echo "FAIL: NeoForge server install"; tail -30 "$DIR/installer.log"; exit 6; }

# 3) Install the pack's server side via packwiz-installer
curl -sfL -o "$DIR/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL" || { echo "FAIL: download packwiz-installer-bootstrap ($BOOTSTRAP_URL)"; exit 3; }
(cd "$DIR" && "$JAVA" -jar packwiz-installer-bootstrap.jar -g -s server "http://localhost:${SERVE_PORT}/pack.toml" > packwiz-install.log 2>&1) || { echo "FAIL: packwiz-installer server side"; tail -30 "$DIR/packwiz-install.log"; exit 7; }
AUDIT_SCRIPT="$DIR/kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
[ -f "$AUDIT_SCRIPT" ] || { echo "FAIL: generated quest item audit script missing"; exit 7; }
awk -v nonce="$AUDIT_NONCE" '{ gsub(/__AFTERLIGHT_BOOT_NONCE__/, nonce); print }' "$AUDIT_SCRIPT" > "$AUDIT_SCRIPT.tmp"
mv "$AUDIT_SCRIPT.tmp" "$AUDIT_SCRIPT"

# 4) Boot headless with a watchdog, EULA accepted for local test only
echo "eula=true" > "$DIR/eula.txt"
cat > "$DIR/server.properties" <<'PROPS'
level-seed=afterlight-ci
server-port=25599
PROPS
(cd "$DIR" && (echo "stop" | "$TIMEOUT_BIN" "$BOOT_TIMEOUT" ./run.sh nogui > boot.log 2>&1 || true))

# 5) Verdict
if grep -q 'Done (' "$DIR"/boot.log || grep -rq 'Done (' "$DIR"/logs/ 2>/dev/null; then
  if ! grep -rhF " $AUDIT_NONCE" "$DIR"/logs/ 2>/dev/null | grep -qF '[AFTERLIGHT QUEST ITEM AUDIT] OK '; then
    echo "SERVER BOOT: FAILED: quest item registry audit did not pass for this boot"
    grep -rhF '[AFTERLIGHT QUEST ITEM AUDIT]' "$DIR"/logs/ 2>/dev/null || true
    exit 8
  fi
  if ! python3 tools/tests/test_rc_hygiene.py; then
    echo "SERVER BOOT: FAILED: RC hygiene validation did not pass"
    exit 9
  fi
  echo "SERVER BOOT: OK"
  exit 0
else
  echo "SERVER BOOT: FAILED: tail of boot.log:"
  tail -50 "$DIR/boot.log" || true
  exit 1
fi
