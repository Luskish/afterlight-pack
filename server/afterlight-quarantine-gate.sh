#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ATTEMPTS=${AFTERLIGHT_QUARANTINE_GATE_ATTEMPTS:-30}
INTERVAL=${AFTERLIGHT_QUARANTINE_GATE_INTERVAL:-2}
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-120}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-900}
EMERGENCY_COMMENT=afterlight-transaction-emergency

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
  [[ -d "$SNAPSHOT_ROOT" && ! -L "$SNAPSHOT_ROOT" ]] || fail "Snapshot root is missing or unsafe"
  [[ $(stat_value '%u' "$RUNTIME_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$RUNTIME_DIR") == "$CONTROL_GID" ]] ||
    fail "Runtime directory owner or group is invalid"
  [[ $(stat_value '%u' "$STATE_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$STATE_DIR") == "$CONTROL_GID" ]] ||
    fail "State directory owner or group is invalid"
  [[ $(stat_value '%u' "$SNAPSHOT_ROOT") == "$CONTROL_UID" && $(stat_value '%g' "$SNAPSHOT_ROOT") == "$CONTROL_GID" ]] ||
    fail "Snapshot root owner or group is invalid"
}

state_arguments() {
  afterlight_state_arguments
}

authority_command() {
  local command_name=$1
  shift
  local -a common=()
  while IFS= read -r -d '' value; do common+=("$value"); done < <(state_arguments)
  run_bounded "$SAFETY_HELPER" "$command_name" "${common[@]}" "$@"
}

run_bounded() {
  "$SAFETY_HELPER" run-command --timeout "$COMMAND_TIMEOUT" -- "$@"
}

acquire_shared_lock() {
  derive_identity || return 1
  afterlight_verify_or_reexec_lock "$TRANSACTION_TIMEOUT" 120 "$@"
}

compose() {
  run_bounded docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

container_state() {
  run_bounded docker inspect --format '{{.State.Status}}' "$1"
}

container_restart_policy() {
  run_bounded docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$1"
}

wait_for_chain() {
  local attempt
  for ((attempt = 1; attempt <= ATTEMPTS; attempt += 1)); do
    if run_bounded iptables -w -n -L DOCKER-USER >/dev/null 2>&1; then return 0; fi
    if ((attempt < ATTEMPTS)); then sleep "$INTERVAL"; fi
  done
  fail "DOCKER-USER did not appear before the quarantine deadline"
}

ensure_rule() {
  local comment=$1
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$comment"
    -j REJECT
  )
  if ! run_bounded iptables -w -C DOCKER-USER "${rule[@]}" >/dev/null 2>&1; then
    run_bounded iptables -w -I DOCKER-USER 1 "${rule[@]}" || return 1
  fi
  run_bounded iptables -w -C DOCKER-USER "${rule[@]}"
}

reconcile_service() {
  local service=$1 transaction_id=${2:-}
  local failed=0 container_id=""
  container_id=$(compose ps -aq "$service") || failed=1
  if [[ -z "$container_id" ]]; then
    return 1
  fi
  if run_bounded docker update --restart=no "$container_id" >/dev/null; then
    if [[ "$(container_restart_policy "$container_id")" == "no" ]]; then
      if [[ -n "$transaction_id" ]]; then
        authority_command authority-update \
          --transaction-id "$transaction_id" \
          --service "$service" \
          --restart-disabled true || failed=1
      fi
    else
      failed=1
    fi
  else
    failed=1
  fi
  if run_bounded docker stop "$container_id" >/dev/null; then
    if [[ "$(container_state "$container_id")" != "running" ]]; then
      if [[ -n "$transaction_id" ]]; then
        authority_command authority-update \
          --transaction-id "$transaction_id" \
          --service "$service" \
          --stopped true || failed=1
      fi
    else
      failed=1
    fi
  else
    failed=1
  fi
  return "$failed"
}

main() {
  afterlight_require_control_root || return 1
  [[ "$ATTEMPTS" =~ ^[1-9][0-9]*$ && "$INTERVAL" =~ ^[0-9]+$ &&
     "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    fail "Quarantine gate timing values are invalid"
    return 1
  }
  local command_name
  for command_name in docker iptables sleep stat; do
    command -v "$command_name" >/dev/null 2>&1 || {
      fail "Required command not found: $command_name"
      return 1
    }
  done
  [[ -x "$SAFETY_HELPER" ]] || { fail "Safety helper is unavailable"; return 1; }
  acquire_shared_lock "$@"
  derive_identity || return 1

  local authority_result=0
  local transaction_id="" gate_comment="$EMERGENCY_COMMENT"
  if authority_command authority-status >/dev/null 2>&1; then
    transaction_id=$(authority_command authority-status --field transaction_id) || authority_result=1
    gate_comment=$(authority_command authority-status --field gate_comment) || authority_result=1
  else
    authority_result=$?
    if [[ "$authority_result" -eq 3 ]]; then
      return 0
    fi
  fi

  if ! wait_for_chain; then
    reconcile_service minecraft "$transaction_id" || true
    reconcile_service backup "$transaction_id" || true
    return 1
  fi
  ensure_rule "$gate_comment" || {
    fail "Quarantine firewall reconstruction failed"
    return 1
  }
  local failed=0
  reconcile_service minecraft "$transaction_id" || failed=1
  reconcile_service backup "$transaction_id" || failed=1
  if [[ "$authority_result" -ne 0 || -z "$transaction_id" ]]; then
    fail "Transaction authority is malformed or unsafe, emergency gate remains active"
    return 1
  fi
  if [[ "$failed" -ne 0 ]]; then
    authority_command authority-update \
      --transaction-id "$transaction_id" \
      --status quarantine \
      --phase quarantine-incomplete >/dev/null 2>&1 || true
    fail "Quarantined containers could not be completely reconciled"
    return 1
  fi
  authority_command authority-update \
    --transaction-id "$transaction_id" \
    --status quarantine \
    --phase boot-reconciled || return 1
  printf 'QUARANTINE GATE: ACTIVE\n'
}

main "$@"
