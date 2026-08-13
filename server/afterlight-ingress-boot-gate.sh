#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
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
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || return 1
  afterlight_verify_or_reexec_lock "$TRANSACTION_TIMEOUT" 60 "$@"
}

main() {
  afterlight_require_control_root || return 1
  [[ -x "$SAFETY_HELPER" ]] || {
    printf '%s\n' 'ERROR: Safety helper is unavailable' >&2
    return 1
  }
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    printf '%s\n' 'ERROR: Boot gate timing values are invalid' >&2
    return 1
  }
  acquire_shared_lock "$@"
  local value
  local -a common=()
  while IFS= read -r -d '' value; do common+=("$value"); done < <(afterlight_state_arguments)
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
