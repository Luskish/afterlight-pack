#!/usr/bin/env bash
# Headless AFTERLIGHT server boot test. Pure JVM — no Docker required.
# Exit 0 = server booted to "Done" and stopped cleanly. Nonzero = failure; see server-test/logs/.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
[ -n "${PATH_EXTRA:-}" ] && export PATH="$PATH_EXTRA:$PATH"
JAVA_HOME=${JAVA_HOME:-$(/usr/libexec/java_home -v 21)}
JAVA="$JAVA_HOME/bin/java"
# NeoForge's generated run.sh invokes bare `java`; put the pinned JDK first on PATH
# (and export JAVA_HOME) so the server boots on the same JVM this script validates.
export JAVA_HOME
export PATH="$JAVA_HOME/bin:$PATH"
TIMEOUT_BIN=$(command -v gtimeout || command -v timeout || true)
[ -z "$TIMEOUT_BIN" ] && { echo "need coreutils: brew install coreutils"; exit 2; }
BOOTSTRAP_URL="https://github.com/packwiz/packwiz-installer-bootstrap/releases/latest/download/packwiz-installer-bootstrap.jar"
DIR=server-test
BOOT_TIMEOUT=${BOOT_TIMEOUT:-420}

rm -rf "$DIR" && mkdir -p "$DIR"

# 1) Serve the working-dir pack locally
packwiz serve --port 8199 & SERVE_PID=$!
trap 'kill $SERVE_PID 2>/dev/null || true' EXIT
sleep 2

# 2) Install NeoForge server
curl -sL -o "$DIR/neoforge-installer.jar" "https://maven.neoforged.net/releases/net/neoforged/neoforge/${NEOFORGE_VERSION}/neoforge-${NEOFORGE_VERSION}-installer.jar"
(cd "$DIR" && "$JAVA" -jar neoforge-installer.jar --install-server . > installer.log 2>&1)

# 3) Install the pack's server side via packwiz-installer
curl -sL -o "$DIR/packwiz-installer-bootstrap.jar" "$BOOTSTRAP_URL"
(cd "$DIR" && "$JAVA" -jar packwiz-installer-bootstrap.jar -g -s server "http://localhost:8199/pack.toml" > packwiz-install.log 2>&1)

# 4) Boot headless with a watchdog, EULA accepted for local test only
echo "eula=true" > "$DIR/eula.txt"
echo "level-seed=afterlight-ci" > "$DIR/server.properties"
(cd "$DIR" && (echo "stop" | "$TIMEOUT_BIN" "$BOOT_TIMEOUT" ./run.sh nogui > boot.log 2>&1 || true))

# 5) Verdict
if grep -q 'Done (' "$DIR"/boot.log || grep -rq 'Done (' "$DIR"/logs/ 2>/dev/null; then
  echo "SERVER BOOT: OK"
  exit 0
else
  echo "SERVER BOOT: FAILED — tail of boot.log:"
  tail -50 "$DIR/boot.log" || true
  exit 1
fi
