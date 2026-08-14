#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-900}
RETENTION_DAYS=7

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

run_bounded() {
  "$SAFETY_HELPER" run-command --timeout "$COMMAND_TIMEOUT" -- "$@"
}

state_arguments() {
  afterlight_state_arguments
}

authority_status() {
  local -a common=()
  local value
  while IFS= read -r -d '' value; do common+=("$value"); done < <(state_arguments)
  run_bounded "$SAFETY_HELPER" authority-status "${common[@]}" >/dev/null 2>&1
}

acquire_shared_lock() {
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory is missing or unsafe"
  [[ $(stat_value '%u' "$RUNTIME_DIR") == "$CONTROL_UID" ]] || fail "Runtime directory owner is invalid"
  [[ $(stat_value '%g' "$RUNTIME_DIR") == "$CONTROL_GID" ]] || fail "Runtime directory group is invalid"
  afterlight_verify_or_reexec_lock "$COMMAND_TIMEOUT" 30 "$@"
}

main() {
  [[ "$#" -eq 0 ]] || {
    fail "Usage: server/afterlight-snapshot-retention.sh"
    return 1
  }
  afterlight_require_control_root || return 1
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    fail "Command timeout must be a positive integer"
    return 1
  }
  [[ -x "$SAFETY_HELPER" ]] || {
    fail "Safety helper is unavailable"
    return 1
  }
  acquire_shared_lock "$@"
  local authority_result=0
  if authority_status; then
    fail "Snapshot retention rejected because a quest update transaction is active"
    return 1
  else
    authority_result=$?
  fi
  if [[ "$authority_result" -ne 3 ]]; then
    fail "Snapshot retention rejected because transaction authority is unsafe"
    return 1
  fi
  local current_epoch threshold
  current_epoch=$(date -u +%s) || return 1
  threshold=$((current_epoch - RETENTION_DAYS * 86400))
  run_bounded "$SAFETY_HELPER" snapshot-prune \
    --snapshot-root "$SNAPSHOT_ROOT" \
    --older-than "$threshold" \
    --owner-uid "$CONTROL_UID" \
    --group-gid "$CONTROL_GID"
  printf '\nSNAPSHOT RETENTION: OK\n'
}

main "$@"
