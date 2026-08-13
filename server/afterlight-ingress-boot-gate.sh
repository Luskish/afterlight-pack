#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
SAFETY_HELPER=${AFTERLIGHT_SAFETY_HELPER:-$SCRIPT_DIR/afterlight-safety.py}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
RUNTIME_MODE=${AFTERLIGHT_RUNTIME_MODE:-750}
LOCK_MODE=${AFTERLIGHT_LOCK_MODE:-660}
STATE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
STATE_DIR_MODE=${AFTERLIGHT_STATE_DIR_MODE:-750}
STATE_FILE_MODE=${AFTERLIGHT_STATE_FILE_MODE:-640}
SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-/var/lib/afterlight/quest-update-snapshots}
SNAPSHOT_ROOT_MODE=${AFTERLIGHT_SNAPSHOT_ROOT_MODE:-700}
EMERGENCY_COMMENT=afterlight-transaction-emergency
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-120}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-300}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

run_bounded() {
  "$SAFETY_HELPER" run-command --timeout "$COMMAND_TIMEOUT" -- "$@"
}

acquire_shared_lock() {
  if [[ ${AFTERLIGHT_LOCK_HELD:-0} == 1 ]]; then return 0; fi
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || return 1
  local lock_owner lock_group
  lock_owner=${AFTERLIGHT_LOCK_OWNER_UID:-$(stat_value '%u' "$RUNTIME_DIR")}
  lock_group=${AFTERLIGHT_LOCK_GROUP_GID:-$(stat_value '%g' "$RUNTIME_DIR")}
  exec "$SAFETY_HELPER" lock-run \
    --runtime-dir "$RUNTIME_DIR" \
    --runtime-mode "$RUNTIME_MODE" \
    --lock-mode "$LOCK_MODE" \
    --timeout "$TRANSACTION_TIMEOUT" \
    --owner-uid "$lock_owner" \
    --group-gid "$lock_group" \
    -- "$0" "$@"
}

main() {
  [[ -x "$SAFETY_HELPER" ]] || {
    printf '%s\n' 'ERROR: Safety helper is unavailable' >&2
    return 1
  }
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    printf '%s\n' 'ERROR: Boot gate timing values are invalid' >&2
    return 1
  }
  acquire_shared_lock "$@"
  local state_owner state_group snapshot_owner snapshot_group
  state_owner=${AFTERLIGHT_STATE_OWNER_UID:-$(stat_value '%u' "$STATE_DIR")}
  state_group=${AFTERLIGHT_STATE_GROUP_GID:-$(stat_value '%g' "$STATE_DIR")}
  snapshot_owner=${AFTERLIGHT_SNAPSHOT_OWNER_UID:-$(stat_value '%u' "$SNAPSHOT_ROOT")}
  snapshot_group=${AFTERLIGHT_SNAPSHOT_GROUP_GID:-$(stat_value '%g' "$SNAPSHOT_ROOT")}
  local -a common=(
    --state-dir "$STATE_DIR"
    --state-dir-mode "$STATE_DIR_MODE"
    --state-file-mode "$STATE_FILE_MODE"
    --owner-uid "$state_owner"
    --group-gid "$state_group"
    --snapshot-owner-uid "$snapshot_owner"
    --snapshot-group-gid "$snapshot_group"
    --snapshot-root-mode "$SNAPSHOT_ROOT_MODE"
    --canonical-snapshot-root "$SNAPSHOT_ROOT"
  )
  local authority_result=0 comment=$EMERGENCY_COMMENT
  if run_bounded "$SAFETY_HELPER" authority-status "${common[@]}" >/dev/null 2>&1; then
    comment=$(run_bounded "$SAFETY_HELPER" authority-status "${common[@]}" --field gate_comment) || return 1
  else
    authority_result=$?
    if [[ "$authority_result" -eq 3 ]]; then
      return 0
    fi
  fi
  command -v iptables >/dev/null 2>&1 || {
    printf '%s\n' 'ERROR: iptables is unavailable' >&2
    return 1
  }
  if ! run_bounded iptables -w -n -L DOCKER-USER >/dev/null 2>&1; then
    run_bounded iptables -w -N DOCKER-USER || return 1
  fi
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$comment"
    -j REJECT
  )
  if ! run_bounded iptables -w -C DOCKER-USER "${rule[@]}" >/dev/null 2>&1; then
    run_bounded iptables -w -I DOCKER-USER 1 "${rule[@]}" || return 1
  fi
  run_bounded iptables -w -C DOCKER-USER "${rule[@]}" || return 1
  if [[ "$authority_result" -ne 0 ]]; then
    printf '%s\n' 'ERROR: malformed transaction authority, emergency ingress gate installed' >&2
    return 1
  fi
  printf 'INGRESS BOOT GATE: ACTIVE\n'
}

main "$@"
