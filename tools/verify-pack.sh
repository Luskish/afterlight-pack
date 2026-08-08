#!/usr/bin/env bash
# AFTERLIGHT pack integrity verifier.
# Checks: refresh idempotence, per-mod side values, and — against the live
# Modrinth API — that every mod's pinned version really supports this pack's
# loader and Minecraft version. Exit 0 = all green.
set -euo pipefail
cd "$(dirname "$0")/.."
source tools/versions.env
[ -n "${PATH_EXTRA:-}" ] && export PATH="$PATH_EXTRA:$PATH"

UA="AFTERLIGHT-pack-verifier (github.com/Luskish/afterlight-pack)"
FAIL=0

echo "== 1/3 refresh idempotence =="
packwiz refresh >/dev/null 2>&1
if [ -n "$(git status --porcelain index.toml pack.toml)" ]; then
  echo "FAIL: refresh dirtied index.toml/pack.toml (uncommitted hash drift)"
  git status --short index.toml pack.toml
  FAIL=1
else
  echo "OK: index/pack hashes committed and stable"
fi

echo "== 2/3 mod manifest =="
printf '%-28s %-8s %s\n' "MOD" "SIDE" "MODRINTH: loader/mc-version"
for f in mods/*.pw.toml; do
  name=$(sed -n 's/^name = "\(.*\)"/\1/p' "$f" | head -1)
  side=$(sed -n 's/^side = "\(.*\)"/\1/p' "$f" | head -1)
  vid=$(sed -n 's/^version = "\(.*\)"/\1/p' "$f" | head -1)
  if [ -z "$vid" ]; then
    printf '%-28s %-8s %s\n' "$name" "${side:-MISSING}" "SKIP (no modrinth version id)"
    continue
  fi
  json=$(curl -sf -A "$UA" "https://api.modrinth.com/v2/version/$vid" || echo "")
  if [ -z "$json" ]; then
    printf '%-28s %-8s %s\n' "$name" "${side:-MISSING}" "FAIL (API unreachable for $vid)"
    FAIL=1; continue
  fi
  loaders_ok=$(printf '%s' "$json" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("yes" if "neoforge" in d.get("loaders",[]) else "no")')
  mc_ok=$(printf '%s' "$json" | python3 -c "import sys,json; d=json.load(sys.stdin); print('yes' if '$MC_VERSION' in d.get('game_versions',[]) else 'no')")
  if [ "$loaders_ok" = "yes" ] && [ "$mc_ok" = "yes" ]; then
    printf '%-28s %-8s %s\n' "$name" "${side:-MISSING}" "OK (neoforge + $MC_VERSION)"
  else
    printf '%-28s %-8s %s\n' "$name" "${side:-MISSING}" "FAIL (neoforge:$loaders_ok mc$MC_VERSION:$mc_ok)"
    FAIL=1
  fi
  [ -z "$side" ] && { echo "  ^ FAIL: missing side value in $f"; FAIL=1; }
  sleep 0.15
done

echo "== 3/3 tooling sanity =="
for s in tools/export.sh; do
  bash -n "$s" && echo "OK: $s parses" || { echo "FAIL: $s syntax"; FAIL=1; }
done
[ -x tools/export.sh ] && echo "OK: export.sh executable" || { echo "FAIL: export.sh not executable"; FAIL=1; }

if [ "$FAIL" -eq 0 ]; then echo "VERIFY: ALL GREEN"; else echo "VERIFY: FAILURES PRESENT"; exit 1; fi
