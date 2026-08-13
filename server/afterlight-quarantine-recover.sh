#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-600}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-}
HEALTH_TIMEOUT=${AFTERLIGHT_HEALTH_TIMEOUT:-600}
POLL_INTERVAL=${AFTERLIGHT_POLL_INTERVAL:-2}
RECOVERY_COMMAND_STEPS=26
RECOVERY_OPERATOR_START_STEPS=2
RECOVERY_DIRECT_HEALTH_STEPS=2
INNER_TERMINATION_GRACE=5
LOCK_TERMINATION_GRACE=300

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

path_mode() {
  stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1"
}

load_identity() {
  [[ $(stat_value '%u' "$RUNTIME_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$RUNTIME_DIR") == "$CONTROL_GID" ]] || return 1
  [[ $(stat_value '%u' "$STATE_DIR") == "$CONTROL_UID" && $(stat_value '%g' "$STATE_DIR") == "$CONTROL_GID" ]] || return 1
  [[ $(stat_value '%u' "$SNAPSHOT_ROOT") == "$CONTROL_UID" && $(stat_value '%g' "$SNAPSHOT_ROOT") == "$CONTROL_GID" ]] || return 1
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
  run_bounded_with_timeout "$COMMAND_TIMEOUT" "$@"
}

run_bounded_with_timeout() {
  local timeout=$1
  shift
  "$SAFETY_HELPER" run-command --timeout "$timeout" -- "$@"
}

run_operator_start() {
  local timeout=$((COMMAND_TIMEOUT + 2 * HEALTH_TIMEOUT))
  run_bounded_with_timeout "$timeout" "$OPERATOR" start
}

recovery_timeout_budget() {
  local operator_start_timeout=$((COMMAND_TIMEOUT + 2 * HEALTH_TIMEOUT))
  printf '%d\n' "$((
    RECOVERY_COMMAND_STEPS * COMMAND_TIMEOUT +
    RECOVERY_OPERATOR_START_STEPS * operator_start_timeout +
    RECOVERY_DIRECT_HEALTH_STEPS * HEALTH_TIMEOUT +
    INNER_TERMINATION_GRACE
  ))"
}

acquire_lock() {
  load_identity
  afterlight_verify_or_reexec_lock "$TRANSACTION_TIMEOUT" "$LOCK_TERMINATION_GRACE" "$@"
}

load_paths() {
  local assignment configured_data=$DATA_DIR
  local data_uid_seen=0 data_gid_seen=0
  while IFS= read -r assignment || [[ -n "$assignment" ]]; do
    case "$assignment" in
      DATA_DIR=*) DATA_DIR=${assignment#DATA_DIR=} ;;
      AFTERLIGHT_DATA_UID=*) ((data_uid_seen += 1)); DATA_OWNER_UID=${assignment#AFTERLIGHT_DATA_UID=} ;;
      AFTERLIGHT_DATA_GID=*) ((data_gid_seen += 1)); DATA_GROUP_GID=${assignment#AFTERLIGHT_DATA_GID=} ;;
      BACKUP_DIR=*|SECRETS_DIR=*|AFTERLIGHT_INIT_MEMORY=*|AFTERLIGHT_MAX_MEMORY=*|AFTERLIGHT_MEMORY_LIMIT=*) ;;
      *) return 1 ;;
    esac
  done < "$ENV_FILE"
  [[ -n ${DATA_DIR:-} && "$DATA_DIR" == "$configured_data" && -d "$DATA_DIR" && ! -L "$DATA_DIR" ]] || return 1
  if [[ "$data_uid_seen" -ne "$data_gid_seen" ]]; then
    return 1
  fi
  [[ "$data_uid_seen" -le 1 && "$data_gid_seen" -le 1 ]] || return 1
  [[ "$data_uid_seen" -eq 1 && "$data_gid_seen" -eq 1 ]] || return 1
  [[ ${DATA_OWNER_UID:-} =~ ^[0-9]+$ && ${DATA_GROUP_GID:-} =~ ^[0-9]+$ ]] || return 1
  afterlight_validate_data_identity "$DATA_OWNER_UID" "$DATA_GROUP_GID" || return 1
  [[ $(stat_value '%u' "$DATA_DIR") == "$DATA_OWNER_UID" && $(stat_value '%g' "$DATA_DIR") == "$DATA_GROUP_GID" ]] || return 1
  DATA_PARENT=$(dirname "$DATA_DIR")
  DATA_PARENT_UID=$(stat_value '%u' "$DATA_PARENT")
  DATA_PARENT_GID=$(stat_value '%g' "$DATA_PARENT")
  [[ "$DATA_PARENT_UID" == "$CONTROL_UID" && "$DATA_PARENT_GID" == "$CONTROL_GID" ]] || return 1
  local parent_mode
  parent_mode=$(path_mode "$DATA_PARENT") || return 1
  (((8#$parent_mode & 8#022) == 0)) || return 1
}

compose() {
  run_bounded docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$SCRIPT_DIR/docker-compose.yml" \
    "$@"
}

read_pack_sha() {
  run_bounded "$SAFETY_HELPER" release-marker-read \
    --data "$DATA_DIR" \
    --owner-uid "$DATA_OWNER_UID" \
    --group-gid "$DATA_GROUP_GID"
}

main() {
  [[ "$#" -eq 1 && "$1" == "--confirm" ]] || {
    fail "Usage: server/afterlight-quarantine-recover.sh --confirm"
    return 1
  }
  afterlight_require_control_root || return 1
  [[ -x "$SAFETY_HELPER" && -x "$PROGRESS_GUARD" && -x "$OPERATOR" &&
     -x "$TRANSACTION_FINALIZER" ]] || {
    fail "Recovery helper dependency is unavailable"
    return 1
  }
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$HEALTH_TIMEOUT" =~ ^[0-9]+$ &&
     "$POLL_INTERVAL" =~ ^[0-9]+$ &&
     ( -z "$TRANSACTION_TIMEOUT" || "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ) ]] || {
    fail "Recovery timing values are invalid"
    return 1
  }
  local minimum_transaction_timeout
  minimum_transaction_timeout=$(recovery_timeout_budget) || return 1
  if [[ -z "$TRANSACTION_TIMEOUT" ]]; then
    TRANSACTION_TIMEOUT=$minimum_transaction_timeout
  elif ((TRANSACTION_TIMEOUT < minimum_transaction_timeout)); then
    fail "Recovery transaction timeout is below the complete operation budget"
    return 1
  fi
  acquire_lock "$@"
  load_identity
  load_paths || { fail "Server paths are invalid"; return 1; }
  local transaction_id prior_sha expected_sha snapshot_dir prior_server_mods data_mutated status
  transaction_id=$(authority_command authority-status --field transaction_id) || return 1
  status=$(authority_command authority-status --field status) || return 1
  if [[ "$status" == terminal ]]; then
    run_bounded "$TRANSACTION_FINALIZER" --transaction-id "$transaction_id" || return 1
    printf 'QUARANTINE RECOVERY: TERMINAL CLEANUP OK\n'
    return 0
  fi
  prior_sha=$(authority_command authority-status --field prior_sha) || return 1
  expected_sha=$(authority_command authority-status --field expected_sha) || return 1
  snapshot_dir=$(authority_command authority-status --field snapshot_dir) || return 1
  prior_server_mods=$(authority_command authority-server-mod-manifest --release-sha "$prior_sha") || return 1
  data_mutated=$(authority_command authority-status --field data_mutated) || return 1
  [[ "$prior_sha" =~ ^[0-9a-f]{40}$ && "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || return 1
  local has_snapshot=0
  local archive="" receipt="" staging="" rescue=""
  if [[ "$data_mutated" == "False" ]]; then
    printf 'Transaction has no authenticated snapshot; verifying unchanged original data authority\n'
    authority_command recovery-original-verify \
      --transaction-id "$transaction_id" \
      --data "$DATA_DIR" \
      --data-owner-uid "$DATA_OWNER_UID" \
      --data-group-gid "$DATA_GROUP_GID" >/dev/null || return 1
  elif [[ "$data_mutated" == "True" ]]; then
    [[ -d "$snapshot_dir/progress" && ! -L "$snapshot_dir/progress" ]] || {
      fail "Authenticated snapshot progress record is unavailable"
      return 1
    }
    has_snapshot=1
    archive="$snapshot_dir/full-backup.tar.gz"
    receipt="$snapshot_dir/backup-preflight.json"
    local data_name
    data_name=$(basename "$DATA_DIR") || return 1
    staging="$DATA_PARENT/.afterlight-recovery-$transaction_id"
    rescue="$DATA_PARENT/${data_name}.quarantined-$expected_sha-$transaction_id"
  else
    fail "Transaction data mutation phase is invalid"
    return 1
  fi
  authority_command authority-update \
    --transaction-id "$transaction_id" \
    --status quarantine \
    --phase recovery-preparing || return 1
  run_bounded systemctl disable --now afterlight-maintenance.timer >/dev/null
  run_bounded "$SCRIPT_DIR/afterlight-quarantine-gate.sh" || {
    fail "Boot quarantine reconciliation is incomplete"
    return 1
  }
  authority_command authority-update \
    --transaction-id "$transaction_id" \
    --status quarantine \
    --phase rollback-checkout-prior \
    --checkout-target-sha "$prior_sha" || return 1
  authority_command checkout-reconcile --repository "$REPOSITORY_ROOT" >/dev/null || return 1
  authority_command authority-update \
    --transaction-id "$transaction_id" \
    --status quarantine \
    --phase rollback-checkout-complete || return 1
  if [[ "$has_snapshot" -eq 1 ]]; then
    run_bounded "$SAFETY_HELPER" archive-restore \
      --archive "$archive" \
      --receipt "$receipt" \
      --destination "$staging" \
      --activate-current "$DATA_DIR" \
      --rescue "$rescue" \
      --resume \
      --owner-uid "$CONTROL_UID" \
      --group-gid "$CONTROL_GID" \
      --parent-owner-uid "$DATA_PARENT_UID" \
      --parent-group-gid "$DATA_PARENT_GID" \
      --destination-owner-uid "$DATA_OWNER_UID" \
      --destination-group-gid "$DATA_GROUP_GID" || return 1
    run_bounded "$PROGRESS_GUARD" compare \
      --world "$DATA_DIR/world" \
      --snapshot "$snapshot_dir/progress" >/dev/null || return 1
  fi
  [[ "$(read_pack_sha)" == "$prior_sha" ]] || {
    fail "Restored pack revision does not equal prior release"
    return 1
  }
  if [[ "$has_snapshot" -eq 0 ]]; then
    authority_command authority-update \
      --transaction-id "$transaction_id" \
      --status terminal \
      --phase rollback-verified || return 1
    run_bounded "$TRANSACTION_FINALIZER" --transaction-id "$transaction_id" || return 1
    printf 'QUARANTINE RECOVERY: OK %s, server remains stopped for reviewed restart\n' "$prior_sha"
    return 0
  fi
  export AFTERLIGHT_RECOVERY_TRANSACTION_ID=$transaction_id
  run_operator_start
  local minecraft_id backup_id started_at
  minecraft_id=$(compose ps -q minecraft) || return 1
  [[ "$minecraft_id" =~ ^[0-9a-f]{12,64}$ ]] || return 1
  started_at=$(run_bounded docker inspect --format '{{.State.StartedAt}}' "$minecraft_id") || return 1
  backup_id=$(compose ps -q backup) || return 1
  [[ "$backup_id" =~ ^[0-9a-f]{12,64}$ ]] || return 1
  afterlight_wait_container_healthy "$backup_id" "$HEALTH_TIMEOUT" "$POLL_INTERVAL" || return 1
  run_bounded "$SAFETY_HELPER" live-verify \
    --repository "$REPOSITORY_ROOT" \
    --data "$DATA_DIR" \
    --expected-sha "$prior_sha" \
    --container-id "$minecraft_id" \
    --started-at "$started_at" \
    --data-owner-uid "$DATA_OWNER_UID" \
    --data-group-gid "$DATA_GROUP_GID" \
    --server-mod-manifest-json "$prior_server_mods" >/dev/null
  run_bounded "$OPERATOR" stop
  run_bounded "$PROGRESS_GUARD" compare \
    --world "$DATA_DIR/world" \
    --snapshot "$snapshot_dir/progress" >/dev/null
  run_operator_start
  run_bounded "$OPERATOR" status
  backup_id=$(compose ps -q backup) || return 1
  [[ "$backup_id" =~ ^[0-9a-f]{12,64}$ ]] || return 1
  afterlight_wait_container_healthy "$backup_id" "$HEALTH_TIMEOUT" "$POLL_INTERVAL" || return 1
  authority_command authority-update \
    --transaction-id "$transaction_id" \
    --status terminal \
    --phase rollback-verified || return 1
  run_bounded "$TRANSACTION_FINALIZER" --transaction-id "$transaction_id" || return 1
  printf 'QUARANTINE RECOVERY: OK %s\n' "$prior_sha"
}

main "$@"
