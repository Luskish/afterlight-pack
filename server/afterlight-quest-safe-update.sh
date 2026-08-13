#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
TRANSACTION_COMPOSE_FILE="$SCRIPT_DIR/docker-compose.transaction.yml"
ENV_FILE=${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}
OPERATOR=${AFTERLIGHT_OPERATOR:-$SCRIPT_DIR/afterlight-server.sh}
PROGRESS_GUARD=${AFTERLIGHT_PROGRESS_GUARD:-$SCRIPT_DIR/afterlight-progress-guard.py}
SAFETY_HELPER=${AFTERLIGHT_SAFETY_HELPER:-$SCRIPT_DIR/afterlight-safety.py}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
RUNTIME_MODE=${AFTERLIGHT_RUNTIME_MODE:-750}
LOCK_MODE=${AFTERLIGHT_LOCK_MODE:-660}
SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-/var/lib/afterlight/quest-update-snapshots}
SNAPSHOT_ROOT_MODE=${AFTERLIGHT_SNAPSHOT_ROOT_MODE:-700}
STATE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
STATE_DIR_MODE=${AFTERLIGHT_STATE_DIR_MODE:-750}
STATE_FILE_MODE=${AFTERLIGHT_STATE_FILE_MODE:-640}
ACCEPTED_RECEIPT=${AFTERLIGHT_ACCEPTED_RECEIPT:-}
ACCEPTED_RECEIPT_SHA256=${AFTERLIGHT_ACCEPTED_RECEIPT_SHA256:-}
HEALTH_TIMEOUT=${AFTERLIGHT_HEALTH_TIMEOUT:-600}
POLL_INTERVAL=${AFTERLIGHT_POLL_INTERVAL:-2}
COMMAND_TIMEOUT=${AFTERLIGHT_COMMAND_TIMEOUT:-120}
TRANSACTION_TIMEOUT=${AFTERLIGHT_TRANSACTION_TIMEOUT:-3600}
CLEANUP_TIMEOUT=${AFTERLIGHT_CLEANUP_TIMEOUT:-300}
RAW_PACK_URL_PREFIX=https://raw.githubusercontent.com/Luskish/afterlight-pack
PLAYER_PATTERN='^There are ([0-9]+) of a max of ([0-9]+) players online: ?([A-Za-z0-9_, ]*)$'

EXPECTED_SHA=""
PRIOR_SHA=""
ACTIVE_SHA=""
DATA_DIR=""
BACKUP_DIR=""
SECRETS_DIR=""
MINECRAFT_ID=""
BACKUP_ID=""
SNAPSHOT_DIR=""
ARCHIVE_PATH=""
ARCHIVE_RECEIPT=""
WHITELIST_SHA=""
USERCACHE_SHA=""
GATE_COMMENT=""
TRANSACTION_ID=""
SNAPSHOT_READY=0
BACKUP_VERIFIED=0
TRANSACTION_COMPLETE=0
CLEANUP_ACTIVE=0

usage() {
  printf '%s\n' \
    'Usage: server/afterlight-quest-safe-update.sh EXPECTED_SHA [RECEIPT_PATH RECEIPT_SHA256] --confirm' >&2
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

stat_value() {
  local format=$1
  local target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

path_uid() {
  stat_value '%u' "$1"
}

path_gid() {
  stat_value '%g' "$1"
}

path_mode() {
  stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1"
}

sha256_file() {
  run_bounded sha256sum "$1" | awk '{print $1}'
}

run_bounded() {
  "$SAFETY_HELPER" run-command --timeout "$COMMAND_TIMEOUT" -- "$@"
}

derive_security_identity() {
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory is missing or unsafe"
  [[ -d "$SNAPSHOT_ROOT" && ! -L "$SNAPSHOT_ROOT" ]] || fail "Snapshot root is missing or unsafe"
  LOCK_OWNER_UID=${AFTERLIGHT_LOCK_OWNER_UID:-$(path_uid "$RUNTIME_DIR")}
  LOCK_GROUP_GID=${AFTERLIGHT_LOCK_GROUP_GID:-$(path_gid "$RUNTIME_DIR")}
  STATE_OWNER_UID=${AFTERLIGHT_STATE_OWNER_UID:-$(id -u)}
  STATE_GROUP_GID=${AFTERLIGHT_STATE_GROUP_GID:-$LOCK_GROUP_GID}
  SNAPSHOT_OWNER_UID=${AFTERLIGHT_SNAPSHOT_OWNER_UID:-$(path_uid "$SNAPSHOT_ROOT")}
  SNAPSHOT_GROUP_GID=${AFTERLIGHT_SNAPSHOT_GROUP_GID:-$(path_gid "$SNAPSHOT_ROOT")}
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
  while IFS= read -r -d '' value; do
    common+=("$value")
  done < <(state_arguments)
  run_bounded "$SAFETY_HELPER" "$command_name" "${common[@]}" "$@"
}

authority_update() {
  authority_command authority-update --transaction-id "$TRANSACTION_ID" "$@"
}

acquire_shared_lock() {
  if [[ ${AFTERLIGHT_LOCK_HELD:-0} == 1 ]]; then
    return 0
  fi
  derive_security_identity || return 1
  exec "$SAFETY_HELPER" lock-run \
    --runtime-dir "$RUNTIME_DIR" \
    --runtime-mode "$RUNTIME_MODE" \
    --lock-mode "$LOCK_MODE" \
    --timeout "$TRANSACTION_TIMEOUT" \
    --termination-grace "$CLEANUP_TIMEOUT" \
    --owner-uid "$LOCK_OWNER_UID" \
    --group-gid "$LOCK_GROUP_GID" \
    -- "$0" "$@"
}

load_paths() {
  [[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || fail "Environment file is missing or unsafe"
  local assignment
  local data_seen=0
  local backup_seen=0
  local secrets_seen=0
  while IFS= read -r assignment || [[ -n "$assignment" ]]; do
    case "$assignment" in
      DATA_DIR=*) ((data_seen += 1)); DATA_DIR=${assignment#DATA_DIR=} ;;
      BACKUP_DIR=*) ((backup_seen += 1)); BACKUP_DIR=${assignment#BACKUP_DIR=} ;;
      SECRETS_DIR=*) ((secrets_seen += 1)); SECRETS_DIR=${assignment#SECRETS_DIR=} ;;
      AFTERLIGHT_INIT_MEMORY=*|AFTERLIGHT_MAX_MEMORY=*|AFTERLIGHT_MEMORY_LIMIT=*) ;;
      *) fail "Environment file contains an unsupported assignment"; return 1 ;;
    esac
  done < "$ENV_FILE"
  if [[ "$data_seen" -ne 1 || "$backup_seen" -ne 1 || "$secrets_seen" -ne 1 ]]; then
    fail "Environment paths must each be assigned exactly once"
    return 1
  fi
  local configured_path
  for configured_path in "$DATA_DIR" "$BACKUP_DIR" "$SECRETS_DIR"; do
    [[ "$configured_path" == /* && "$configured_path" != "/" ]] || {
      fail "Environment paths must be absolute"
      return 1
    }
    [[ -d "$configured_path" && ! -L "$configured_path" && "$(cd "$configured_path" && pwd -P)" == "$configured_path" ]] || {
      fail "Environment paths must be canonical real directories"
      return 1
    }
  done
  DATA_OWNER_UID=$(path_uid "$DATA_DIR")
  DATA_GROUP_GID=$(path_gid "$DATA_DIR")
  DATA_PARENT=$(dirname "$DATA_DIR")
  DATA_PARENT_UID=$(path_uid "$DATA_PARENT")
  DATA_PARENT_GID=$(path_gid "$DATA_PARENT")
  local expected_parent_uid=${AFTERLIGHT_DATA_PARENT_UID:-$DATA_PARENT_UID}
  if [[ $(id -u) -eq 0 ]]; then
    expected_parent_uid=${AFTERLIGHT_DATA_PARENT_UID:-0}
  fi
  [[ "$DATA_PARENT_UID" == "$expected_parent_uid" ]] || {
    fail "Data parent must have the configured canonical owner"
    return 1
  }
  local parent_mode
  parent_mode=$(path_mode "$DATA_PARENT") || return 1
  (((8#$parent_mode & 8#022) == 0)) || {
    fail "Data parent must not be group or other writable"
    return 1
  }
}

compose() {
  AFTERLIGHT_PACKWIZ_URL="$RAW_PACK_URL_PREFIX/$ACTIVE_SHA/pack.toml" \
    run_bounded docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    -f "$TRANSACTION_COMPOSE_FILE" \
    "$@"
}

container_health() {
  run_bounded docker inspect \
    --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "$1"
}

container_state() {
  run_bounded docker inspect --format '{{.State.Status}}' "$1"
}

container_restart_policy() {
  run_bounded docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$1"
}

wait_healthy() {
  local container_id=$1
  local deadline=$((SECONDS + HEALTH_TIMEOUT))
  local health
  while true; do
    health=$(container_health "$container_id" 2>/dev/null || true)
    if [[ "$health" == "running|healthy" ]]; then
      return 0
    fi
    if ((SECONDS >= deadline)); then
      return 1
    fi
    sleep "$POLL_INTERVAL"
  done
}

player_count() {
  local output cleaned reported maximum listed
  if ! output=$(run_bounded docker exec "$MINECRAFT_ID" rcon-cli list </dev/null 2>&1); then
    fail "RCON player query failed"
    return 1
  fi
  cleaned=$(printf '%s\n' "$output" | sed $'s/\033\\[[0-9;]*[[:alpha:]]//g')
  cleaned=${cleaned//$'\r'/}
  if [[ "$cleaned" == *$'\n'* || ! "$cleaned" =~ $PLAYER_PATTERN ]]; then
    fail "Unable to parse RCON player count"
    return 1
  fi
  reported=${BASH_REMATCH[1]}
  maximum=${BASH_REMATCH[2]}
  listed=${BASH_REMATCH[3]// /}
  if ((reported > maximum)) || { ((reported == 0)) && [[ -n "$listed" ]]; }; then
    fail "RCON player count is contradictory"
    return 1
  fi
  printf '%s\n' "$reported"
}

require_zero_players() {
  local players
  players=$(player_count) || return 1
  if ((players != 0)); then
    fail "Quest update rejected because players online are nonzero"
    return 1
  fi
}

gate_rule() {
  printf '%s\0' \
    -p tcp --dport 25565 \
    -m conntrack --ctstate NEW \
    -m comment --comment "$GATE_COMMENT" \
    -j REJECT
}

ensure_gate() {
  local -a rule=()
  while IFS= read -r -d '' value; do rule+=("$value"); done < <(gate_rule)
  if ! run_bounded iptables -w -C DOCKER-USER "${rule[@]}" >/dev/null 2>&1; then
    run_bounded iptables -w -I DOCKER-USER 1 "${rule[@]}" || return 1
  fi
  run_bounded iptables -w -C DOCKER-USER "${rule[@]}" || return 1
}

remove_gate() {
  local -a rule=()
  while IFS= read -r -d '' value; do rule+=("$value"); done < <(gate_rule)
  run_bounded iptables -w -C DOCKER-USER "${rule[@]}" || return 1
  run_bounded iptables -w -D DOCKER-USER "${rule[@]}" || return 1
  if run_bounded iptables -w -C DOCKER-USER "${rule[@]}"; then
    return 1
  fi
}

write_pack_sha() {
  local pack_sha=$1
  local temporary="$DATA_DIR/.afterlight-pack-sha.tmp.$$"
  printf '%s\n' "$pack_sha" > "$temporary"
  run_bounded mv "$temporary" "$DATA_DIR/.afterlight-pack-sha"
  [[ "$(cat "$DATA_DIR/.afterlight-pack-sha")" == "$pack_sha" ]]
}

verify_stopped() {
  [[ "$(container_state "$MINECRAFT_ID")" != "running" ]] || return 1
  [[ "$(container_state "$BACKUP_ID")" != "running" ]] || return 1
}

stop_both_cleanly() {
  compose stop backup minecraft || return 1
  verify_stopped
}

stop_minecraft_cleanly() {
  compose stop minecraft || return 1
  [[ "$(container_state "$MINECRAFT_ID")" != "running" ]]
}

verify_live_release() {
  run_bounded "$SAFETY_HELPER" live-verify \
    --repository "$REPOSITORY_ROOT" \
    --data "$DATA_DIR" \
    --expected-sha "$1" >/dev/null
}

start_minecraft() {
  local pack_sha=$1
  local expected_url="$RAW_PACK_URL_PREFIX/$pack_sha/pack.toml"
  local configured_urls
  ACTIVE_SHA=$pack_sha
  compose up -d --force-recreate minecraft || return 1
  MINECRAFT_ID=$(compose ps -q minecraft) || return 1
  [[ -n "$MINECRAFT_ID" ]] || return 1
  wait_healthy "$MINECRAFT_ID" || return 1
  configured_urls=$(
    run_bounded docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$MINECRAFT_ID" |
      sed -n 's/^PACKWIZ_URL=//p'
  ) || return 1
  [[ "$configured_urls" == "$expected_url" ]] || return 1
  write_pack_sha "$pack_sha" || return 1
  verify_live_release "$pack_sha" || return 1
}

verify_integrity_files() {
  [[ -f "$DATA_DIR/whitelist.json" && ! -L "$DATA_DIR/whitelist.json" ]] || return 1
  [[ -f "$DATA_DIR/usercache.json" && ! -L "$DATA_DIR/usercache.json" ]] || return 1
  [[ "$(sha256_file "$DATA_DIR/whitelist.json")" == "$WHITELIST_SHA" ]] || return 1
  [[ "$(sha256_file "$DATA_DIR/usercache.json")" == "$USERCACHE_SHA" ]]
}

create_snapshot() {
  local stamp progress_snapshot
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  SNAPSHOT_DIR="$SNAPSHOT_ROOT/quest-update-$stamp-$TRANSACTION_ID"
  run_bounded mkdir -m 0700 "$SNAPSHOT_DIR" || return 1
  progress_snapshot="$SNAPSHOT_DIR/progress"
  run_bounded mkdir -m 0700 "$progress_snapshot" || return 1
  run_bounded "$PROGRESS_GUARD" snapshot \
    --world "$DATA_DIR/world" \
    --output "$progress_snapshot" || return 1
  [[ ! -L "$progress_snapshot" && "$(path_mode "$progress_snapshot")" == "700" ]] || {
    fail "Progress snapshot directory must retain mode 0700"
    return 1
  }
  authority_update --phase snapshot-created --snapshot-dir "$SNAPSHOT_DIR" || return 1
  SNAPSHOT_READY=1
}

create_verified_archive() {
  ARCHIVE_PATH="$SNAPSHOT_DIR/full-backup.tar.gz"
  ARCHIVE_RECEIPT="$SNAPSHOT_DIR/backup-preflight.json"
  run_bounded "$SAFETY_HELPER" archive-create \
    --source "$DATA_DIR" \
    --archive "$ARCHIVE_PATH" \
    --receipt "$ARCHIVE_RECEIPT" \
    --owner-uid "$SNAPSHOT_OWNER_UID" \
    --group-gid "$SNAPSHOT_GROUP_GID" \
    --source-owner-uid "$DATA_OWNER_UID" \
    --source-group-gid "$DATA_GROUP_GID" >/dev/null || return 1
  BACKUP_VERIFIED=1
  authority_update --phase backup-authenticated || return 1
}

restore_verified_archive() {
  local data_name staging rescue
  data_name=$(basename "$DATA_DIR")
  staging="$DATA_PARENT/.${data_name}.quest-restore-$TRANSACTION_ID"
  rescue="$DATA_PARENT/${data_name}.rejected-$EXPECTED_SHA-$TRANSACTION_ID"
  [[ ! -e "$staging" && ! -L "$staging" && ! -e "$rescue" && ! -L "$rescue" ]] || return 1
  run_bounded "$SAFETY_HELPER" archive-restore \
    --archive "$ARCHIVE_PATH" \
    --receipt "$ARCHIVE_RECEIPT" \
    --destination "$staging" \
    --activate-current "$DATA_DIR" \
    --rescue "$rescue" \
    --owner-uid "$SNAPSHOT_OWNER_UID" \
    --group-gid "$SNAPSHOT_GROUP_GID" \
    --parent-owner-uid "$DATA_PARENT_UID" \
    --parent-group-gid "$DATA_PARENT_GID" \
    --destination-owner-uid "$DATA_OWNER_UID" \
    --destination-group-gid "$DATA_GROUP_GID" || return 1
  [[ -s "$DATA_DIR/world/level.dat" ]] || return 1
  [[ "$(cat "$DATA_DIR/.afterlight-pack-sha")" == "$PRIOR_SHA" ]] || return 1
}

compare_progress() {
  run_bounded "$PROGRESS_GUARD" compare \
    --world "$DATA_DIR/world" \
    --snapshot "$SNAPSHOT_DIR/progress"
}

rollback_transaction() {
  [[ "$SNAPSHOT_READY" -eq 1 && "$BACKUP_VERIFIED" -eq 1 ]] || return 1
  authority_update --phase rollback-started || return 1
  ACTIVE_SHA=$PRIOR_SHA
  compose stop backup minecraft >/dev/null 2>&1 || true
  restore_verified_archive || return 1
  write_pack_sha "$PRIOR_SHA" || return 1
  start_minecraft "$PRIOR_SHA" || return 1
  stop_minecraft_cleanly || return 1
  compare_progress || return 1
  verify_integrity_files || return 1
  start_minecraft "$PRIOR_SHA" || return 1
  ACTIVE_SHA=$PRIOR_SHA
  compose up -d backup || return 1
  BACKUP_ID=$(compose ps -q backup) || return 1
  [[ -n "$BACKUP_ID" ]] || return 1
  [[ "$(container_health "$BACKUP_ID")" == "running|healthy" ]] || return 1
  authority_update --phase rollback-verified || return 1
}

reconcile_one_container() {
  local service=$1
  local container_id=""
  local failed=0
  container_id=$(compose ps -aq "$service") || failed=1
  if [[ -z "$container_id" ]]; then
    failed=1
  else
    if run_bounded docker update --restart=no "$container_id" >/dev/null; then
      if [[ "$(container_restart_policy "$container_id")" == "no" ]]; then
        authority_update --service "$service" --restart-disabled true || failed=1
      else
        failed=1
      fi
    else
      failed=1
    fi
    if run_bounded docker stop "$container_id" >/dev/null; then
      if [[ "$(container_state "$container_id")" != "running" ]]; then
        authority_update --service "$service" --stopped true || failed=1
      else
        failed=1
      fi
    else
      failed=1
    fi
  fi
  return "$failed"
}

restore_restart_policies() {
  local failed=0
  local service container_id
  for service in minecraft backup; do
    container_id=$(compose ps -aq "$service") || failed=1
    if [[ -z "$container_id" ]]; then
      failed=1
      continue
    fi
    run_bounded docker update --restart=unless-stopped "$container_id" >/dev/null || failed=1
    [[ "$(container_restart_policy "$container_id")" == "unless-stopped" ]] || failed=1
  done
  return "$failed"
}

quarantine_reconcile() {
  local failed=0
  authority_update --status quarantine --phase quarantine-reconciling || failed=1
  ensure_gate || failed=1
  reconcile_one_container minecraft || failed=1
  reconcile_one_container backup || failed=1
  if [[ "$failed" -eq 0 ]]; then
    authority_update --status quarantine --phase quarantined || return 1
    return 0
  fi
  authority_update --status quarantine --phase quarantine-incomplete >/dev/null 2>&1 || true
  return 1
}

on_signal() {
  fail "Quest-safe update interrupted"
  exit 130
}

on_exit() {
  local status=$?
  trap - EXIT INT TERM HUP
  if [[ "$TRANSACTION_COMPLETE" -eq 1 || "$CLEANUP_ACTIVE" -eq 1 || -z "$TRANSACTION_ID" ]]; then
    exit "$status"
  fi
  CLEANUP_ACTIVE=1
  ensure_gate >/dev/null 2>&1 || true
  if rollback_transaction && restore_restart_policies && remove_gate && authority_command authority-complete --transaction-id "$TRANSACTION_ID"; then
    printf 'ROLLBACK: VERIFIED\n' >&2
  elif quarantine_reconcile; then
    printf 'ROLLBACK FAILED: QUARANTINED\n' >&2
  else
    printf 'ROLLBACK FAILED: QUARANTINE INCOMPLETE\n' >&2
  fi
  exit "$status"
}

verify_release_acceptance() {
  [[ -n "$ACCEPTED_RECEIPT" && -n "$ACCEPTED_RECEIPT_SHA256" ]] || {
    fail "Accepted release receipt and digest are required"
    return 1
  }
  [[ "$ACCEPTED_RECEIPT_SHA256" =~ ^[0-9a-f]{64}$ ]] || {
    fail "Accepted release receipt digest is invalid"
    return 1
  }
  local receipt_uid receipt_gid
  receipt_uid=$(path_uid "$ACCEPTED_RECEIPT") || return 1
  receipt_gid=$(path_gid "$ACCEPTED_RECEIPT") || return 1
  run_bounded "$SAFETY_HELPER" receipt-verify \
    --repository "$REPOSITORY_ROOT" \
    --receipt "$ACCEPTED_RECEIPT" \
    --receipt-sha256 "$ACCEPTED_RECEIPT_SHA256" \
    --expected-sha "$EXPECTED_SHA" \
    --receipt-owner-uid "$receipt_uid" \
    --receipt-group-gid "$receipt_gid" >/dev/null
}

main() {
  if [[ "$#" -eq 4 && "$4" == "--confirm" ]]; then
    ACCEPTED_RECEIPT=$2
    ACCEPTED_RECEIPT_SHA256=$3
  elif [[ "$#" -ne 2 || "$2" != "--confirm" ]]; then
    usage
    return 1
  fi
  EXPECTED_SHA=$1
  if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    fail "EXPECTED_SHA must be 40 lowercase hexadecimal characters"
    return 1
  fi
  if [[ ! "$HEALTH_TIMEOUT" =~ ^[0-9]+$ || ! "$POLL_INTERVAL" =~ ^[0-9]+$ ||
        ! "$COMMAND_TIMEOUT" =~ ^[1-9][0-9]*$ || ! "$TRANSACTION_TIMEOUT" =~ ^[1-9][0-9]*$ ]]; then
    fail "Health timing values must be nonnegative integers"
    return 1
  fi
  [[ "$CLEANUP_TIMEOUT" =~ ^[1-9][0-9]*$ ]] || {
    fail "Cleanup timeout must be a positive integer"
    return 1
  }
  local command_name
  for command_name in awk cat date docker git id iptables mkdir mv sed sha256sum stat; do
    require_command "$command_name" || return 1
  done
  [[ -x "$OPERATOR" ]] || { fail "Operator preflight command is unavailable"; return 1; }
  [[ -x "$PROGRESS_GUARD" ]] || { fail "Progress guard is unavailable"; return 1; }
  [[ -x "$SAFETY_HELPER" ]] || { fail "Safety helper is unavailable"; return 1; }
  acquire_shared_lock "$@"
  derive_security_identity || return 1
  load_paths || return 1
  if ! run_bounded "$OPERATOR" doctor </dev/null >/dev/null; then
    fail "Operator preflight failed"
    return 1
  fi
  verify_release_acceptance || return 1
  if authority_command authority-status >/dev/null 2>&1; then
    fail "Durable quest update authority is already active"
    return 1
  else
    local authority_status=$?
    if [[ "$authority_status" -ne 3 ]]; then
      fail "Durable quest update authority is unsafe"
      return 1
    fi
  fi
  PRIOR_SHA=$(cat "$DATA_DIR/.afterlight-pack-sha") || return 1
  [[ "$PRIOR_SHA" =~ ^[0-9a-f]{40}$ ]] || {
    fail "Prior pack SHA marker is invalid"
    return 1
  }
  ACTIVE_SHA=$PRIOR_SHA
  MINECRAFT_ID=$(compose ps -q minecraft) || return 1
  BACKUP_ID=$(compose ps -q backup) || return 1
  [[ -n "$MINECRAFT_ID" && -n "$BACKUP_ID" ]] || {
    fail "Current Minecraft and backup containers must be running"
    return 1
  }
  [[ "$(container_health "$MINECRAFT_ID")" == "running|healthy" ]] || {
    fail "Current Minecraft container is not healthy"
    return 1
  }
  WHITELIST_SHA=$(sha256_file "$DATA_DIR/whitelist.json") || return 1
  USERCACHE_SHA=$(sha256_file "$DATA_DIR/usercache.json") || return 1
  require_zero_players || return 1
  TRANSACTION_ID=$(authority_command authority-create \
    --expected-sha "$EXPECTED_SHA" \
    --prior-sha "$PRIOR_SHA" \
    --snapshot-root "$SNAPSHOT_ROOT" \
    --receipt-sha256 "$ACCEPTED_RECEIPT_SHA256") || return 1
  GATE_COMMENT="afterlight-quest-update-$EXPECTED_SHA-$TRANSACTION_ID"
  authority_update --phase gate-installing || return 1
  ensure_gate || { fail "Firewall gate insertion failed"; return 1; }
  authority_update --phase gate-closed || return 1
  require_zero_players || return 1
  if ! run_bounded docker exec "$MINECRAFT_ID" rcon-cli save-all flush </dev/null >/dev/null; then
    fail "RCON save-all flush failed"
    return 1
  fi
  authority_update --phase shutdown-started || return 1
  if ! stop_both_cleanly; then
    fail "Clean shutdown failed"
    return 1
  fi
  authority_update --phase stopped || return 1
  if ! create_snapshot; then
    fail "Snapshot creation or mode verification failed"
    return 1
  fi
  if ! create_verified_archive; then
    fail "Direct backup authentication failed"
    return 1
  fi
  authority_update --phase candidate-starting || return 1
  if ! start_minecraft "$EXPECTED_SHA"; then
    fail "Candidate start or accepted release verification failed"
    return 1
  fi
  authority_update --phase candidate-started || return 1
  if ! stop_minecraft_cleanly; then
    fail "Candidate verification shutdown failed"
    return 1
  fi
  if ! compare_progress; then
    fail "Canonical progress comparison failed"
    return 1
  fi
  if ! verify_integrity_files; then
    fail "Whitelist integrity verification failed"
    return 1
  fi
  authority_update --phase candidate-verified || return 1
  if ! start_minecraft "$EXPECTED_SHA"; then
    fail "Second candidate start failed"
    return 1
  fi
  ACTIVE_SHA=$EXPECTED_SHA
  if ! compose up -d backup; then
    fail "Backup service restart failed"
    return 1
  fi
  BACKUP_ID=$(compose ps -q backup) || return 1
  [[ -n "$BACKUP_ID" && "$(container_health "$BACKUP_ID")" == "running|healthy" ]] || {
    fail "Backup service did not become healthy"
    return 1
  }
  verify_integrity_files || { fail "Whitelist integrity verification failed"; return 1; }
  verify_live_release "$EXPECTED_SHA" || { fail "Final accepted release verification failed"; return 1; }
  verify_release_acceptance || { fail "Final accepted release receipt verification failed"; return 1; }
  authority_update --phase release-proven || return 1
  restore_restart_policies || { fail "Container restart policy restoration failed"; return 1; }
  remove_gate || return 1
  authority_command authority-complete --transaction-id "$TRANSACTION_ID" || return 1
  TRANSACTION_COMPLETE=1
  printf 'QUEST-SAFE UPDATE: OK %s\n' "$EXPECTED_SHA"
}

trap on_signal INT TERM HUP
trap on_exit EXIT
main "$@"
