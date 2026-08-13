#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-120}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-900}
FIREWALL_TIMEOUT=${AFTERLIGHT_FIREWALL_TIMEOUT:-30}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

derive_identity() {
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory is missing or unsafe"
  [[ -d "$STATE_DIR" && ! -L "$STATE_DIR" ]] || fail "Transaction authority directory is missing or unsafe"
  [[ -d "$SNAPSHOT_ROOT" && ! -L "$SNAPSHOT_ROOT" ]] || fail "Snapshot root is missing or unsafe"
  [[ $(stat_value '%u' "$RUNTIME_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$RUNTIME_DIR") == "$CONTROL_GID" ]] ||
    fail "Runtime directory owner or group is invalid"
  [[ $(stat_value '%u' "$STATE_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$STATE_DIR") == "$CONTROL_GID" ]] ||
    fail "Transaction authority directory owner or group is invalid"
  [[ $(stat_value '%u' "$SNAPSHOT_ROOT") == "$CONTROL_UID" && $(stat_value '%g' "$SNAPSHOT_ROOT") == "$CONTROL_GID" ]] ||
    fail "Snapshot root owner or group is invalid"
}

run_bounded() {
  "$SAFETY_HELPER" run-command --timeout "$COMMAND_TIMEOUT" -- "$@"
}

authority_command() {
  local command_name=$1
  shift
  local -a common=()
  while IFS= read -r -d '' value; do common+=("$value"); done < <(afterlight_state_arguments)
  run_bounded "$SAFETY_HELPER" "$command_name" "${common[@]}" "$@"
}

authority_update() {
  authority_command authority-update --transaction-id "$TRANSACTION_ID" "$@"
}

acquire_lock() {
  derive_identity || return 1
  afterlight_verify_or_reexec_lock "$TRANSACTION_TIMEOUT" "$COMMAND_TIMEOUT" "$@"
}

compose() {
  run_bounded docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

restore_restart_policies() {
  local service container_id policy
  for service in minecraft backup; do
    container_id=$(compose ps -aq "$service") || return 1
    [[ -n "$container_id" ]] || {
      fail "$service container identity is unavailable during terminal cleanup"
      return 1
    }
    run_bounded docker update --restart=unless-stopped "$container_id" >/dev/null || return 1
    policy=$(run_bounded docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$container_id") || return 1
    [[ "$policy" == unless-stopped ]] || {
      fail "$service restart policy reconciliation failed"
      return 1
    }
  done
}

remove_gate() {
  local gate_comment
  gate_comment=$(authority_command authority-status --field gate_comment) || return 1
  run_bounded "$SAFETY_HELPER" firewall-gate-remove \
    --comment "$gate_comment" \
    --timeout "$FIREWALL_TIMEOUT"
}

reconcile_systemd() {
  run_bounded systemctl reset-failed afterlight-quarantine-gate.service
  run_bounded systemctl enable afterlight-quarantine-gate.service
  run_bounded systemctl is-enabled --quiet afterlight-quarantine-gate.service
  run_bounded systemctl enable --now afterlight-maintenance.timer
  run_bounded systemctl is-enabled --quiet afterlight-maintenance.timer
  run_bounded systemctl is-active --quiet afterlight-maintenance.timer
}

main() {
  [[ "$#" -eq 2 && "$1" == --transaction-id && "$2" =~ ^[0-9a-f]{32}$ ]] || {
    fail "Usage: server/afterlight-transaction-finalize.sh --transaction-id TRANSACTION_ID"
    return 1
  }
  TRANSACTION_ID=$2
  afterlight_require_control_root || return 1
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ &&
     "$FIREWALL_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    fail "Terminal cleanup timing values must be positive integers"
    return 1
  }
  [[ -x "$SAFETY_HELPER" ]] || { fail "Safety helper is unavailable"; return 1; }
  acquire_lock "$@"
  derive_identity || return 1
  local recorded_id status phase
  recorded_id=$(authority_command authority-status --field transaction_id) || return 1
  [[ "$recorded_id" == "$TRANSACTION_ID" ]] || {
    fail "Transaction identifier differs from durable authority"
    return 1
  }
  status=$(authority_command authority-status --field status) || return 1
  [[ "$status" == terminal ]] || {
    fail "Terminal cleanup requires verified terminal authority"
    return 1
  }
  while true; do
    phase=$(authority_command authority-status --field phase) || return 1
    case "$phase" in
      transaction-verified|rollback-verified)
        authority_update --status terminal --phase cleanup-restart-policies
        ;;
      cleanup-restart-policies)
        restore_restart_policies
        authority_update --status terminal --phase cleanup-systemd
        ;;
      cleanup-systemd)
        reconcile_systemd
        authority_update --status terminal --phase cleanup-gate
        ;;
      cleanup-gate)
        remove_gate
        authority_update --status terminal --phase cleanup-complete
        ;;
      cleanup-complete)
        authority_command authority-complete --transaction-id "$TRANSACTION_ID"
        printf 'TRANSACTION CLEANUP: OK %s\n' "$TRANSACTION_ID"
        return 0
        ;;
      *)
        fail "Transaction is not at a reviewed terminal cleanup phase"
        return 1
        ;;
    esac
  done
}

main "$@"
