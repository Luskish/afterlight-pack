#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
ENV_FILE=${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}
OPERATOR=${AFTERLIGHT_OPERATOR:-$SCRIPT_DIR/afterlight-server.sh}
PROGRESS_GUARD=${AFTERLIGHT_PROGRESS_GUARD:-$SCRIPT_DIR/afterlight-progress-guard.py}
SAFETY_HELPER=${AFTERLIGHT_SAFETY_HELPER:-$SCRIPT_DIR/afterlight-safety.py}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
RUNTIME_MODE=${AFTERLIGHT_RUNTIME_MODE:-750}
LOCK_MODE=${AFTERLIGHT_LOCK_MODE:-660}
STATE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
STATE_DIR_MODE=${AFTERLIGHT_STATE_DIR_MODE:-750}
STATE_FILE_MODE=${AFTERLIGHT_STATE_FILE_MODE:-640}
SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-/var/lib/afterlight/quest-update-snapshots}
SNAPSHOT_ROOT_MODE=${AFTERLIGHT_SNAPSHOT_ROOT_MODE:-700}
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-600}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-3600}

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
  LOCK_OWNER_UID=${AFTERLIGHT_LOCK_OWNER_UID:-$(stat_value '%u' "$RUNTIME_DIR")}
  LOCK_GROUP_GID=${AFTERLIGHT_LOCK_GROUP_GID:-$(stat_value '%g' "$RUNTIME_DIR")}
  STATE_OWNER_UID=${AFTERLIGHT_STATE_OWNER_UID:-$(stat_value '%u' "$STATE_DIR")}
  STATE_GROUP_GID=${AFTERLIGHT_STATE_GROUP_GID:-$(stat_value '%g' "$STATE_DIR")}
  SNAPSHOT_OWNER_UID=${AFTERLIGHT_SNAPSHOT_OWNER_UID:-$(stat_value '%u' "$SNAPSHOT_ROOT")}
  SNAPSHOT_GROUP_GID=${AFTERLIGHT_SNAPSHOT_GROUP_GID:-$(stat_value '%g' "$SNAPSHOT_ROOT")}
}

state_arguments() {
  printf '%s\0' \
    --state-dir "$STATE_DIR" \
    --state-dir-mode "$STATE_DIR_MODE" \
    --state-file-mode "$STATE_FILE_MODE" \
    --owner-uid "$STATE_OWNER_UID" \
    --group-gid "$STATE_GROUP_GID" \
    --snapshot-owner-uid "$SNAPSHOT_OWNER_UID" \
    --snapshot-group-gid "$SNAPSHOT_GROUP_GID" \
    --snapshot-root-mode "$SNAPSHOT_ROOT_MODE" \
    --canonical-snapshot-root "$SNAPSHOT_ROOT"
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

acquire_lock() {
  if [[ ${AFTERLIGHT_LOCK_HELD:-0} == 1 ]]; then return 0; fi
  load_identity
  exec "$SAFETY_HELPER" lock-run \
    --runtime-dir "$RUNTIME_DIR" \
    --runtime-mode "$RUNTIME_MODE" \
    --lock-mode "$LOCK_MODE" \
    --timeout "$TRANSACTION_TIMEOUT" \
    --owner-uid "$LOCK_OWNER_UID" \
    --group-gid "$LOCK_GROUP_GID" \
    -- "$0" "$@"
}

load_paths() {
  local assignment
  while IFS= read -r assignment || [[ -n "$assignment" ]]; do
    case "$assignment" in
      DATA_DIR=*) DATA_DIR=${assignment#DATA_DIR=} ;;
      BACKUP_DIR=*|SECRETS_DIR=*|AFTERLIGHT_INIT_MEMORY=*|AFTERLIGHT_MAX_MEMORY=*|AFTERLIGHT_MEMORY_LIMIT=*) ;;
      *) return 1 ;;
    esac
  done < "$ENV_FILE"
  [[ -n ${DATA_DIR:-} && -d "$DATA_DIR" && ! -L "$DATA_DIR" ]] || return 1
  DATA_OWNER_UID=$(stat_value '%u' "$DATA_DIR")
  DATA_GROUP_GID=$(stat_value '%g' "$DATA_DIR")
  DATA_PARENT=$(dirname "$DATA_DIR")
  DATA_PARENT_UID=$(stat_value '%u' "$DATA_PARENT")
  DATA_PARENT_GID=$(stat_value '%g' "$DATA_PARENT")
  local expected_parent_uid=${AFTERLIGHT_DATA_PARENT_UID:-0}
  [[ "$DATA_PARENT_UID" == "$expected_parent_uid" ]] || return 1
  local parent_mode
  parent_mode=$(path_mode "$DATA_PARENT") || return 1
  (((8#$parent_mode & 8#022) == 0)) || return 1
}

remove_gate() {
  local comment=$1
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$comment"
    -j REJECT
  )
  run_bounded iptables -w -C DOCKER-USER "${rule[@]}" || return 1
  run_bounded iptables -w -D DOCKER-USER "${rule[@]}" || return 1
  ! run_bounded iptables -w -C DOCKER-USER "${rule[@]}"
}

main() {
  [[ "$#" -eq 1 && "$1" == "--confirm" ]] || {
    fail "Usage: server/afterlight-quarantine-recover.sh --confirm"
    return 1
  }
  [[ $(id -u) -eq 0 || -n ${AFTERLIGHT_ALLOW_NONROOT_RECOVERY:-} ]] || {
    fail "Quarantine recovery must run as root"
    return 1
  }
  [[ -x "$SAFETY_HELPER" && -x "$PROGRESS_GUARD" && -x "$OPERATOR" ]] || {
    fail "Recovery helper dependency is unavailable"
    return 1
  }
  [[ "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ && "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    fail "Recovery timing values are invalid"
    return 1
  }
  acquire_lock "$@"
  load_identity
  load_paths || { fail "Server paths are invalid"; return 1; }
  local transaction_id prior_sha expected_sha gate_comment snapshot_dir
  transaction_id=$(authority_command authority-status --field transaction_id) || return 1
  prior_sha=$(authority_command authority-status --field prior_sha) || return 1
  expected_sha=$(authority_command authority-status --field expected_sha) || return 1
  gate_comment=$(authority_command authority-status --field gate_comment) || return 1
  snapshot_dir=$(authority_command authority-status --field snapshot_dir) || return 1
  [[ "$prior_sha" =~ ^[0-9a-f]{40}$ && "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || return 1
  [[ "$snapshot_dir" != "None" && -d "$snapshot_dir/progress" ]] || {
    fail "Transaction has no authenticated recovery snapshot"
    return 1
  }
  local archive="$snapshot_dir/full-backup.tar.gz"
  local receipt="$snapshot_dir/backup-preflight.json"
  local staging="$DATA_PARENT/.afterlight-recovery-$transaction_id"
  local data_name rescue
  data_name=$(basename "$DATA_DIR") || return 1
  rescue="$DATA_PARENT/${data_name}.quarantined-$expected_sha-$transaction_id"
  [[ ! -e "$staging" && ! -L "$staging" && ! -e "$rescue" && ! -L "$rescue" ]] || {
    fail "Recovery staging or rescue path already exists"
    return 1
  }
  run_bounded systemctl disable --now afterlight-maintenance.timer >/dev/null
  run_bounded "$SCRIPT_DIR/afterlight-quarantine-gate.sh" || {
    fail "Boot quarantine reconciliation is incomplete"
    return 1
  }
  run_bounded "$SAFETY_HELPER" archive-restore \
    --archive "$archive" \
    --receipt "$receipt" \
    --destination "$staging" \
    --activate-current "$DATA_DIR" \
    --rescue "$rescue" \
    --owner-uid "$SNAPSHOT_OWNER_UID" \
    --group-gid "$SNAPSHOT_GROUP_GID" \
    --parent-owner-uid "$DATA_PARENT_UID" \
    --parent-group-gid "$DATA_PARENT_GID" \
    --destination-owner-uid "$DATA_OWNER_UID" \
    --destination-group-gid "$DATA_GROUP_GID"
  run_bounded "$PROGRESS_GUARD" compare \
    --world "$DATA_DIR/world" \
    --snapshot "$snapshot_dir/progress" >/dev/null
  [[ "$(cat "$DATA_DIR/.afterlight-pack-sha")" == "$prior_sha" ]] || {
    fail "Restored pack revision does not equal prior release"
    return 1
  }
  [[ -z "$(run_bounded git -C "$REPOSITORY_ROOT" status --porcelain=v1 --untracked-files=all)" ]] || {
    fail "Repository checkout is not clean"
    return 1
  }
  run_bounded git -C "$REPOSITORY_ROOT" cat-file -e "$prior_sha^{commit}"
  run_bounded git -C "$REPOSITORY_ROOT" checkout --detach "$prior_sha"
  export AFTERLIGHT_RECOVERY_TRANSACTION_ID=$transaction_id
  run_bounded "$OPERATOR" start
  run_bounded "$OPERATOR" stop
  run_bounded "$PROGRESS_GUARD" compare \
    --world "$DATA_DIR/world" \
    --snapshot "$snapshot_dir/progress" >/dev/null
  run_bounded "$SAFETY_HELPER" live-verify \
    --repository "$REPOSITORY_ROOT" \
    --data "$DATA_DIR" \
    --expected-sha "$prior_sha" >/dev/null
  run_bounded "$OPERATOR" start
  run_bounded "$OPERATOR" status
  local service container_id
  for service in minecraft backup; do
    container_id=$(run_bounded docker compose \
      --project-name afterlight \
      --env-file "$ENV_FILE" \
      -f "$SCRIPT_DIR/docker-compose.yml" \
      ps -aq "$service")
    [[ -n "$container_id" ]] || return 1
    run_bounded docker update --restart=unless-stopped "$container_id" >/dev/null
  done
  remove_gate "$gate_comment"
  authority_command authority-complete --transaction-id "$transaction_id"
  run_bounded systemctl reset-failed afterlight-quarantine-gate.service
  run_bounded systemctl enable --now afterlight-maintenance.timer
  printf 'QUARANTINE RECOVERY: OK %s\n' "$prior_sha"
}

main "$@"
