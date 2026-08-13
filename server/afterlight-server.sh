#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}"
PROPERTIES_TEMPLATE="$SCRIPT_DIR/server.properties.example"
AFTERLIGHT_HEALTH_TIMEOUT="${AFTERLIGHT_HEALTH_TIMEOUT:-600}"
CONFIGURED_PATH_GRAMMAR='^/([A-Za-z0-9._-]+/)*[A-Za-z0-9._-]+$'
MEMORY_GRAMMAR='^[1-9][0-9]*G$'
PACK_SHA_FILE_NAME=.afterlight-pack-sha
RAW_PACK_URL_PREFIX=https://raw.githubusercontent.com/Luskish/afterlight-pack
QUARANTINE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
SAFETY_HELPER=${AFTERLIGHT_SAFETY_HELPER:-$SCRIPT_DIR/afterlight-safety.py}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
RUNTIME_MODE=${AFTERLIGHT_RUNTIME_MODE:-750}
LOCK_MODE=${AFTERLIGHT_LOCK_MODE:-660}
STATE_DIR_MODE=${AFTERLIGHT_STATE_DIR_MODE:-750}
STATE_FILE_MODE=${AFTERLIGHT_STATE_FILE_MODE:-640}
SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-/var/lib/afterlight/quest-update-snapshots}
SNAPSHOT_ROOT_MODE=${AFTERLIGHT_SNAPSHOT_ROOT_MODE:-700}

DATA_DIR=""
BACKUP_DIR=""
SECRETS_DIR=""
AFTERLIGHT_INIT_MEMORY=4G
AFTERLIGHT_MAX_MEMORY=10G
AFTERLIGHT_MEMORY_LIMIT=13G
PACKWIZ_URL_OVERRIDE=""

usage() {
  printf '%s\n' \
    'Usage: server/afterlight-server.sh doctor|start|stop|status|backup|update|rollback BACKUP --confirm' >&2
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

require_command() {
  local command_name=$1
  if ! command -v "$command_name" >/dev/null 2>&1; then
    fail "Required command not found: $command_name"
    return 1
  fi
}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

derive_lock_identity() {
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory is missing or unsafe"
  [[ -d "$QUARANTINE_DIR" && ! -L "$QUARANTINE_DIR" ]] || fail "Transaction authority directory is missing or unsafe"
  [[ -d "$SNAPSHOT_ROOT" && ! -L "$SNAPSHOT_ROOT" ]] || fail "Snapshot root is missing or unsafe"
  LOCK_OWNER_UID=${AFTERLIGHT_LOCK_OWNER_UID:-$(stat_value '%u' "$RUNTIME_DIR")}
  LOCK_GROUP_GID=${AFTERLIGHT_LOCK_GROUP_GID:-$(stat_value '%g' "$RUNTIME_DIR")}
  STATE_OWNER_UID=${AFTERLIGHT_STATE_OWNER_UID:-$(stat_value '%u' "$QUARANTINE_DIR")}
  STATE_GROUP_GID=${AFTERLIGHT_STATE_GROUP_GID:-$(stat_value '%g' "$QUARANTINE_DIR")}
  SNAPSHOT_OWNER_UID=${AFTERLIGHT_SNAPSHOT_OWNER_UID:-$(stat_value '%u' "$SNAPSHOT_ROOT")}
  SNAPSHOT_GROUP_GID=${AFTERLIGHT_SNAPSHOT_GROUP_GID:-$(stat_value '%g' "$SNAPSHOT_ROOT")}
}

state_arguments() {
  printf '%s\0' \
    --state-dir "$QUARANTINE_DIR" \
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
  "$SAFETY_HELPER" "$command_name" "${common[@]}" "$@"
}

acquire_mutation_lock() {
  if [[ ${AFTERLIGHT_LOCK_HELD:-0} == 1 ]]; then return 0; fi
  derive_lock_identity || return 1
  exec "$SAFETY_HELPER" lock-run \
    --runtime-dir "$RUNTIME_DIR" \
    --runtime-mode "$RUNTIME_MODE" \
    --lock-mode "$LOCK_MODE" \
    --owner-uid "$LOCK_OWNER_UID" \
    --group-gid "$LOCK_GROUP_GID" \
    -- "$0" "$@"
}

verify_mutation_authority() {
  local command_name=$1
  derive_lock_identity || return 1
  local authority_status=0
  if authority_command authority-status >/dev/null 2>&1; then
    local recovery_id=${AFTERLIGHT_RECOVERY_TRANSACTION_ID:-}
    if [[ -z "$recovery_id" ]]; then
      fail "Operation rejected because a quest update transaction is active"
      return 1
    fi
    if [[ "$command_name" != "start" && "$command_name" != "stop" ]]; then
      fail "Only recovery start and stop are allowed while transaction authority is active"
      return 1
    fi
    local recorded_id gate_comment
    recorded_id=$(authority_command authority-status --field transaction_id) || return 1
    gate_comment=$(authority_command authority-status --field gate_comment) || return 1
    [[ "$recorded_id" == "$recovery_id" ]] || {
      fail "Recovery transaction identifier mismatch"
      return 1
    }
    local -a rule=(
      -p tcp --dport 25565
      -m conntrack --ctstate NEW
      -m comment --comment "$gate_comment"
      -j REJECT
    )
    iptables -w -C DOCKER-USER "${rule[@]}" || {
      fail "Recovery start rejected because the exact owned firewall gate is absent"
      return 1
    }
    return 0
  else
    authority_status=$?
  fi
  if [[ "$authority_status" -ne 3 ]]; then
    fail "Operation rejected because transaction authority is unsafe"
    return 1
  fi
}

validate_configured_path_syntax() {
  local label=$1
  local configured_path=$2
  if [[ ! "$configured_path" =~ $CONFIGURED_PATH_GRAMMAR ]]; then
    fail "$label must match conservative absolute Linux path grammar $CONFIGURED_PATH_GRAMMAR"
    return 1
  fi
}

validate_memory_budget() {
  local label
  local value
  for label in AFTERLIGHT_INIT_MEMORY AFTERLIGHT_MAX_MEMORY AFTERLIGHT_MEMORY_LIMIT; do
    value=${!label}
    if [[ ! "$value" =~ $MEMORY_GRAMMAR ]]; then
      fail "$label must use positive whole gigabytes such as 6G"
      return 1
    fi
  done

  local init_gib=${AFTERLIGHT_INIT_MEMORY%G}
  local max_gib=${AFTERLIGHT_MAX_MEMORY%G}
  local limit_gib=${AFTERLIGHT_MEMORY_LIMIT%G}
  if ((init_gib > max_gib)); then
    fail "AFTERLIGHT_INIT_MEMORY must not exceed AFTERLIGHT_MAX_MEMORY"
    return 1
  fi
  if ((limit_gib < max_gib + 2)); then
    fail "AFTERLIGHT_MEMORY_LIMIT must leave at least 2G above AFTERLIGHT_MAX_MEMORY"
    return 1
  fi
}

load_paths() {
  [[ -f "$ENV_FILE" ]] || fail "Environment file not found: $ENV_FILE"

  local data_seen=0
  local backup_seen=0
  local secrets_seen=0
  local init_memory_seen=0
  local max_memory_seen=0
  local memory_limit_seen=0
  local assignment
  while IFS= read -r assignment || [[ -n "$assignment" ]]; do
    case "$assignment" in
      DATA_DIR=*)
        if [[ "$data_seen" -ne 0 ]]; then
          fail "Duplicate DATA_DIR assignment in $ENV_FILE"
          return 1
        fi
        DATA_DIR=${assignment#DATA_DIR=}
        data_seen=1
        ;;
      BACKUP_DIR=*)
        if [[ "$backup_seen" -ne 0 ]]; then
          fail "Duplicate BACKUP_DIR assignment in $ENV_FILE"
          return 1
        fi
        BACKUP_DIR=${assignment#BACKUP_DIR=}
        backup_seen=1
        ;;
      SECRETS_DIR=*)
        if [[ "$secrets_seen" -ne 0 ]]; then
          fail "Duplicate SECRETS_DIR assignment in $ENV_FILE"
          return 1
        fi
        SECRETS_DIR=${assignment#SECRETS_DIR=}
        secrets_seen=1
        ;;
      AFTERLIGHT_INIT_MEMORY=*)
        if [[ "$init_memory_seen" -ne 0 ]]; then
          fail "Duplicate AFTERLIGHT_INIT_MEMORY assignment in $ENV_FILE"
          return 1
        fi
        AFTERLIGHT_INIT_MEMORY=${assignment#AFTERLIGHT_INIT_MEMORY=}
        init_memory_seen=1
        ;;
      AFTERLIGHT_MAX_MEMORY=*)
        if [[ "$max_memory_seen" -ne 0 ]]; then
          fail "Duplicate AFTERLIGHT_MAX_MEMORY assignment in $ENV_FILE"
          return 1
        fi
        AFTERLIGHT_MAX_MEMORY=${assignment#AFTERLIGHT_MAX_MEMORY=}
        max_memory_seen=1
        ;;
      AFTERLIGHT_MEMORY_LIMIT=*)
        if [[ "$memory_limit_seen" -ne 0 ]]; then
          fail "Duplicate AFTERLIGHT_MEMORY_LIMIT assignment in $ENV_FILE"
          return 1
        fi
        AFTERLIGHT_MEMORY_LIMIT=${assignment#AFTERLIGHT_MEMORY_LIMIT=}
        memory_limit_seen=1
        ;;
      *)
        fail "Invalid assignment in $ENV_FILE: $assignment"
        return 1
        ;;
    esac
  done < "$ENV_FILE"

  if [[ "$data_seen" -ne 1 || -z "$DATA_DIR" ]]; then
    fail "DATA_DIR must be assigned once"
    return 1
  fi
  if [[ "$backup_seen" -ne 1 || -z "$BACKUP_DIR" ]]; then
    fail "BACKUP_DIR must be assigned once"
    return 1
  fi
  if [[ "$secrets_seen" -ne 1 || -z "$SECRETS_DIR" ]]; then
    fail "SECRETS_DIR must be assigned once"
    return 1
  fi
  validate_configured_path_syntax DATA_DIR "$DATA_DIR" || return 1
  validate_configured_path_syntax BACKUP_DIR "$BACKUP_DIR" || return 1
  validate_configured_path_syntax SECRETS_DIR "$SECRETS_DIR" || return 1
  validate_memory_budget || return 1
}

compose() {
  if [[ -n "$PACKWIZ_URL_OVERRIDE" ]]; then
    AFTERLIGHT_PACKWIZ_URL="$PACKWIZ_URL_OVERRIDE" \
      AFTERLIGHT_INIT_MEMORY="$AFTERLIGHT_INIT_MEMORY" \
      AFTERLIGHT_MAX_MEMORY="$AFTERLIGHT_MAX_MEMORY" \
      AFTERLIGHT_MEMORY_LIMIT="$AFTERLIGHT_MEMORY_LIMIT" \
      docker compose \
      --project-name afterlight \
      --env-file "$ENV_FILE" \
      -f "$COMPOSE_FILE" \
      "$@"
  else
    AFTERLIGHT_INIT_MEMORY="$AFTERLIGHT_INIT_MEMORY" \
      AFTERLIGHT_MAX_MEMORY="$AFTERLIGHT_MAX_MEMORY" \
      AFTERLIGHT_MEMORY_LIMIT="$AFTERLIGHT_MEMORY_LIMIT" \
      docker compose \
      --project-name afterlight \
      --env-file "$ENV_FILE" \
      -f "$COMPOSE_FILE" \
      "$@"
  fi
}

pack_sha_is_valid() {
  local pack_sha=$1
  [[ "$pack_sha" =~ ^[0-9a-f]{40}$ ]]
}

repository_pack_sha() {
  local pack_sha
  require_command git || return 1
  pack_sha=$(git -C "$REPOSITORY_ROOT" rev-parse --verify 'HEAD^{commit}') || {
    fail "Unable to resolve the repository pack revision"
    return 1
  }
  if ! pack_sha_is_valid "$pack_sha"; then
    fail "Repository pack revision must be 40 lowercase hexadecimal characters"
    return 1
  fi
  printf '%s\n' "$pack_sha"
}

use_pack_sha() {
  local pack_sha=$1
  if ! pack_sha_is_valid "$pack_sha"; then
    fail "Pack revision must be 40 lowercase hexadecimal characters"
    return 1
  fi
  PACKWIZ_URL_OVERRIDE="$RAW_PACK_URL_PREFIX/$pack_sha/pack.toml"
}

write_pack_sha() {
  local pack_sha=$1
  local marker_path="$DATA_DIR/$PACK_SHA_FILE_NAME"
  local temporary_path="$DATA_DIR/.${PACK_SHA_FILE_NAME}.tmp.$$"
  use_pack_sha "$pack_sha" || return 1
  printf '%s\n' "$pack_sha" > "$temporary_path" || return 1
  mv "$temporary_path" "$marker_path"
}

tree_pack_sha() {
  local tree_root=$1
  local marker_path="$tree_root/$PACK_SHA_FILE_NAME"
  local line_count
  local pack_sha

  [[ -f "$marker_path" && ! -L "$marker_path" ]] || return 1
  line_count=$(awk 'END { print NR }' "$marker_path") || return 1
  pack_sha=$(sed -n '1p' "$marker_path") || return 1
  [[ "$line_count" -eq 1 ]] || return 1
  pack_sha_is_valid "$pack_sha" || return 1
  printf '%s\n' "$pack_sha"
}

restored_tree_is_valid() {
  local tree_root=$1
  local level_file="$tree_root/world/level.dat"
  local symlink
  local size

  [[ -d "$tree_root/world" && ! -L "$tree_root/world" ]] || return 1
  [[ -f "$level_file" && ! -L "$level_file" ]] || return 1
  size=$(stat_size "$level_file") || return 1
  [[ "$size" =~ ^[0-9]+$ && "$size" -gt 0 ]] || return 1
  symlink=$(find "$tree_root" -type l -print -quit) || return 1
  [[ -z "$symlink" ]] || return 1
  tree_pack_sha "$tree_root" >/dev/null
}

path_is_nested() {
  local candidate=$1
  local parent=$2
  [[ "$candidate" == "$parent" || "$candidate" == "$parent"/* ]]
}

canonicalize_one_path() {
  local label=$1
  local configured_path=$2
  local canonical_path

  if [[ "$configured_path" != /* ]]; then
    fail "$label must be absolute: $configured_path"
    return 1
  fi
  if [[ "$configured_path" == "/" ]]; then
    fail "$label must not be the filesystem root"
    return 1
  fi
  canonical_path=$(realpath -m "$configured_path") || return 1
  if [[ "$configured_path" != "$canonical_path" ]]; then
    fail "$label must be canonical and must not use symlinks: $configured_path"
    return 1
  fi
  printf '%s\n' "$canonical_path"
}

canonicalize_paths() {
  DATA_DIR=$(canonicalize_one_path DATA_DIR "$DATA_DIR") || return 1
  BACKUP_DIR=$(canonicalize_one_path BACKUP_DIR "$BACKUP_DIR") || return 1
  SECRETS_DIR=$(canonicalize_one_path SECRETS_DIR "$SECRETS_DIR") || return 1

  if path_is_nested "$DATA_DIR" "$BACKUP_DIR" || path_is_nested "$BACKUP_DIR" "$DATA_DIR"; then
    fail "DATA_DIR and BACKUP_DIR must not be equal or nested"
    return 1
  fi
  if path_is_nested "$DATA_DIR" "$SECRETS_DIR" || path_is_nested "$SECRETS_DIR" "$DATA_DIR"; then
    fail "DATA_DIR and SECRETS_DIR must not be equal or nested"
    return 1
  fi
  if path_is_nested "$BACKUP_DIR" "$SECRETS_DIR" || path_is_nested "$SECRETS_DIR" "$BACKUP_DIR"; then
    fail "BACKUP_DIR and SECRETS_DIR must not be equal or nested"
    return 1
  fi
}

prepare_paths() {
  require_command realpath || return 1
  load_paths || return 1
  canonicalize_paths || return 1
}

validate_writable_dirs() {
  local directory
  for directory in "$DATA_DIR" "$BACKUP_DIR"; do
    if [[ ! -d "$directory" ]]; then
      fail "Required directory does not exist: $directory"
      return 1
    fi
    if [[ -L "$directory" ]]; then
      fail "Required directory must not be a symlink: $directory"
      return 1
    fi
    if [[ ! -w "$directory" ]]; then
      fail "Required directory is not writable: $directory"
      return 1
    fi
  done
  if [[ ! -d "$SECRETS_DIR" ]]; then
    fail "Secrets directory does not exist: $SECRETS_DIR"
    return 1
  fi
  if [[ -L "$SECRETS_DIR" ]]; then
    fail "Secrets directory must not be a symlink: $SECRETS_DIR"
    return 1
  fi
}

validate_data_parent() {
  local data_parent=$1
  local canonical_parent

  canonical_parent=$(realpath -m "$data_parent") || return 1
  if [[ "$data_parent" != "$canonical_parent" ]]; then
    fail "Rollback data parent must be canonical and must not use symlinks: $data_parent"
    return 1
  fi
  if [[ ! -d "$data_parent" || -L "$data_parent" ]]; then
    fail "Rollback data parent must be an existing non-symlinked directory: $data_parent"
    return 1
  fi
  if [[ ! -w "$data_parent" ]]; then
    fail "Rollback data parent is not writable: $data_parent"
    return 1
  fi
}

stat_mode() {
  local target=$1
  local mode
  if mode=$(stat -c '%a' "$target" 2>/dev/null); then
    printf '%s\n' "$mode"
  else
    stat -f '%Lp' "$target"
  fi
}

stat_size() {
  local target=$1
  local size
  if size=$(stat -c '%s' "$target" 2>/dev/null); then
    printf '%s\n' "$size"
  else
    stat -f '%z' "$target"
  fi
}

stat_mtime() {
  local target=$1
  local mtime
  if mtime=$(stat -c '%Y' "$target" 2>/dev/null); then
    printf '%s\n' "$mtime"
  else
    stat -f '%m' "$target"
  fi
}

validate_secret() {
  local secret_file="$SECRETS_DIR/rcon_password"
  local line_count
  local secret_value
  local mode

  if [[ -L "$secret_file" ]]; then
    fail "RCON secret must not be a symlink: $secret_file"
    return 1
  fi
  if [[ ! -f "$secret_file" ]]; then
    fail "RCON secret must be a regular file: $secret_file"
    return 1
  fi
  mode=$(stat_mode "$secret_file")
  if [[ "$mode" != "600" ]]; then
    fail "RCON secret mode must be 600, found $mode"
    return 1
  fi
  line_count=$(awk 'END { print NR }' "$secret_file")
  secret_value=$(sed -n '1p' "$secret_file")
  if [[ "$line_count" -ne 1 || -z "$secret_value" ]]; then
    fail "RCON secret must contain exactly one nonempty line"
    return 1
  fi
}

minecraft_state() {
  compose ps --format json minecraft
}

minecraft_is_running() {
  local state=$1
  printf '%s\n' "$state" | grep -Eq '"State"[[:space:]]*:[[:space:]]*"running"'
}

minecraft_is_healthy() {
  local state=$1
  printf '%s\n' "$state" | grep -Eq '"Health"[[:space:]]*:[[:space:]]*"healthy"'
}

validate_ports() {
  local tcp_listeners
  local udp_listeners
  tcp_listeners=$(ss -H -ltn 'sport = :25565') || {
    fail "Unable to inspect TCP port 25565"
    return 1
  }
  udp_listeners=$(ss -H -lun 'sport = :24454') || {
    fail "Unable to inspect UDP port 24454"
    return 1
  }
  if [[ -n "$tcp_listeners" ]]; then
    fail "TCP port 25565 is already in use"
    return 1
  fi
  if [[ -n "$udp_listeners" ]]; then
    fail "UDP port 24454 is already in use"
    return 1
  fi
}

wait_healthy() {
  if [[ ! "$AFTERLIGHT_HEALTH_TIMEOUT" =~ ^[0-9]+$ ]]; then
    fail "AFTERLIGHT_HEALTH_TIMEOUT must be a nonnegative integer"
    return 1
  fi
  local deadline=$((SECONDS + AFTERLIGHT_HEALTH_TIMEOUT))
  local state

  while true; do
    state=$(minecraft_state 2>/dev/null || true)
    if minecraft_is_healthy "$state"; then
      return 0
    fi
    if ((SECONDS >= deadline)); then
      fail "Minecraft did not become healthy within ${AFTERLIGHT_HEALTH_TIMEOUT}s"
      return 1
    fi
    sleep 2
  done
}

latest_backup_snapshot() {
  local backup_file
  local relative_name
  local size
  local mtime

  find "$BACKUP_DIR" -type f -print |
    while IFS= read -r backup_file; do
      [[ ! -L "$backup_file" ]] || continue
      relative_name=${backup_file#"$BACKUP_DIR"/}
      size=$(stat_size "$backup_file")
      mtime=$(stat_mtime "$backup_file")
      printf '%s\t%s\t%s\n' "$relative_name" "$size" "$mtime"
    done |
    LC_ALL=C sort
}

archive_name_is_approved() {
  local relative_name=$1
  [[ "$relative_name" =~ ^([A-Za-z0-9][A-Za-z0-9._-]*/)*[A-Za-z0-9][A-Za-z0-9._-]*\.tar\.zst$ ]]
}

archive_is_recoverable() {
  local archive_path=$1
  local recoverable=false
  local size
  local validation_path

  [[ -f "$archive_path" && ! -L "$archive_path" ]] || return 1
  size=$(stat_size "$archive_path") || return 1
  [[ "$size" =~ ^[0-9]+$ && "$size" -gt 0 ]] || return 1
  validation_path=$(mktemp -d "$BACKUP_DIR/.afterlight-verify.XXXXXX") || return 1
  if zstd --decompress --stdout "$archive_path" 2>/dev/null |
    tar --extract --file - --directory "$validation_path" --no-same-owner --no-same-permissions 2>/dev/null; then
    if restored_tree_is_valid "$validation_path"; then
      recoverable=true
    fi
  fi
  find "$validation_path" -depth -delete || return 1
  [[ "$recoverable" == "true" ]]
}

run_doctor() {
  local quiet=${1:-false}
  local state

  prepare_paths || return 1
  require_command docker || return 1
  require_command realpath || return 1
  require_command tar || return 1
  require_command zstd || return 1
  require_command ss || return 1
  validate_writable_dirs || return 1
  validate_secret || return 1
  docker compose version >/dev/null || return 1
  compose config --quiet || return 1
  state=$(minecraft_state) || return 1
  if ! minecraft_is_running "$state"; then
    validate_ports || return 1
  fi
  if [[ "$quiet" != "true" ]]; then
    printf 'Doctor: OK\n'
  fi
}

install_properties_once() {
  local data_root=${1:-$DATA_DIR}
  local properties_file
  properties_file="$data_root/server.properties"
  if [[ -L "$properties_file" ]]; then
    fail "server.properties must not be a symlink"
    return 1
  fi
  if [[ ! -e "$properties_file" ]]; then
    cp "$PROPERTIES_TEMPLATE" "$properties_file" || return 1
  elif [[ ! -f "$properties_file" ]]; then
    fail "server.properties must be a regular file"
    return 1
  fi
}

validate_start_revision() {
  local expected_pack_sha=$1
  local existing_pack_sha
  local world_path="$DATA_DIR/world"

  if [[ ! -e "$world_path" && ! -L "$world_path" ]]; then
    return 0
  fi
  if [[ ! -d "$world_path" || -L "$world_path" ]]; then
    fail "Existing world path must be a regular directory"
    return 1
  fi
  existing_pack_sha=$(tree_pack_sha "$DATA_DIR") || {
    fail "Existing world requires a valid pack revision marker; use a new DATA_DIR or restore a verified backup"
    return 1
  }
  if [[ "$existing_pack_sha" != "$expected_pack_sha" ]]; then
    fail "Existing world uses pack revision $existing_pack_sha; run update instead of start"
    return 1
  fi
}

run_start() {
  local pack_sha
  pack_sha=$(repository_pack_sha) || return 1
  use_pack_sha "$pack_sha" || return 1
  run_doctor true || return 1
  validate_start_revision "$pack_sha" || return 1
  install_properties_once || return 1
  if ! compose up -d minecraft; then
    compose stop backup minecraft || true
    fail "Minecraft start failed"
    return 1
  fi
  if ! wait_healthy; then
    compose stop backup minecraft || true
    fail "Minecraft health check failed"
    return 1
  fi
  if ! write_pack_sha "$pack_sha"; then
    compose stop backup minecraft || true
    fail "Pack revision marker update failed"
    return 1
  fi
  if ! compose up -d backup; then
    compose stop backup minecraft || true
    fail "Backup service start failed"
    return 1
  fi
}

run_stop() {
  prepare_paths
  require_command docker
  compose stop backup minecraft
}

run_status() {
  local state
  prepare_paths
  require_command docker
  compose ps
  state=$(minecraft_state)
  printf 'Minecraft health: %s\n' "$state"
}

run_backup() {
  local before_snapshot
  local after_snapshot
  local relative_name
  local size
  local mtime
  local inventory_record
  local candidate_path
  local backup_path=""

  run_doctor true || return 1
  before_snapshot=$(latest_backup_snapshot) || return 1
  compose exec backup backup now >&2 || return 1
  after_snapshot=$(latest_backup_snapshot) || return 1

  while IFS=$'\t' read -r relative_name size mtime; do
    [[ -n "$relative_name" ]] || continue
    inventory_record=$(printf '%s\t%s\t%s' "$relative_name" "$size" "$mtime")
    if ! printf '%s\n' "$before_snapshot" | grep -Fqx "$inventory_record"; then
      candidate_path="$BACKUP_DIR/$relative_name"
      if archive_name_is_approved "$relative_name" && archive_is_recoverable "$candidate_path"; then
        backup_path="$candidate_path"
      fi
    fi
  done <<< "$after_snapshot"

  if [[ -z "$backup_path" ]]; then
    fail "Backup command produced no new or changed recoverable backup archive"
    return 1
  fi
  printf '%s\n' "$backup_path"
}

print_rollback_command() {
  local backup_path=$1
  printf "Rollback: server/afterlight-server.sh rollback '%s' --confirm\n" "$backup_path"
}

stop_after_failed_update() {
  local backup_path=$1
  compose stop backup minecraft || true
  print_rollback_command "$backup_path"
  return 1
}

run_update() {
  local backup_path
  local pack_sha
  prepare_paths || return 1
  pack_sha=$(repository_pack_sha) || return 1
  use_pack_sha "$pack_sha" || return 1
  backup_path=$(run_backup) || return 1
  if ! compose stop backup minecraft; then
    stop_after_failed_update "$backup_path"
    return 1
  fi
  if ! compose up -d --force-recreate minecraft; then
    stop_after_failed_update "$backup_path"
    return 1
  fi
  if ! wait_healthy; then
    stop_after_failed_update "$backup_path"
    return 1
  fi
  if ! write_pack_sha "$pack_sha"; then
    stop_after_failed_update "$backup_path"
    return 1
  fi
  if ! compose up -d backup; then
    stop_after_failed_update "$backup_path"
    return 1
  fi
  printf 'Backup: %s\n' "$backup_path"
}

run_rollback() {
  if [[ "$#" -ne 2 || "$2" != "--confirm" ]]; then
    fail "Rollback requires BACKUP --confirm"
    usage
    return 1
  fi

  local requested_backup=$1
  local canonical_backup
  local data_parent
  local data_basename
  local rescue_path
  local restored_pack_sha
  local staging_path

  prepare_paths || return 1
  if [[ "$requested_backup" != /* ]]; then
    fail "Rollback archive must be an absolute path"
    return 1
  fi
  if [[ -L "$requested_backup" ]]; then
    fail "Rollback archive must not be a symlink"
    return 1
  fi
  if [[ ! -f "$requested_backup" ]]; then
    fail "Rollback archive must be a regular file"
    return 1
  fi
  canonical_backup=$(realpath -m "$requested_backup") || return 1
  if [[ "$requested_backup" != "$canonical_backup" ]]; then
    fail "Rollback archive path must be canonical and must not use symlinks"
    return 1
  fi
  if ! path_is_nested "$canonical_backup" "$BACKUP_DIR" || [[ "$canonical_backup" == "$BACKUP_DIR" ]]; then
    fail "Rollback archive must be beneath BACKUP_DIR"
    return 1
  fi

  data_parent=$(dirname "$DATA_DIR")
  validate_data_parent "$data_parent" || return 1
  data_basename=$(basename "$DATA_DIR")
  staging_path=$(mktemp -d "$data_parent/.${data_basename}.restore.XXXXXX") || return 1
  if ! zstd --decompress --stdout "$canonical_backup" |
    tar --extract --file - --directory "$staging_path" --no-same-owner --no-same-permissions; then
    fail "Rollback archive is not recoverable; preflight extraction failed and staging was preserved at $staging_path"
    return 1
  fi
  if ! restored_tree_is_valid "$staging_path"; then
    fail "Rollback archive is not recoverable; preflight tree is invalid and staging was preserved at $staging_path"
    return 1
  fi
  restored_pack_sha=$(tree_pack_sha "$staging_path") || return 1
  use_pack_sha "$restored_pack_sha" || return 1
  install_properties_once "$staging_path" || {
    fail "Rollback preflight properties setup failed; archive and staging tree were preserved at $staging_path"
    return 1
  }
  run_doctor true || return 1
  rescue_path="$data_parent/$data_basename.rescue-$(date -u +%Y%m%dT%H%M%SZ)"
  [[ ! -e "$rescue_path" && ! -L "$rescue_path" ]] ||
    fail "Rollback rescue path already exists: $rescue_path"

  compose stop backup minecraft
  mv "$DATA_DIR" "$rescue_path"
  mv "$staging_path" "$DATA_DIR"
  if ! compose up -d minecraft backup; then
    compose stop backup minecraft || true
    fail "Rollback start failed; archive, rescue tree, and restored tree were preserved"
    return 1
  fi
  if ! wait_healthy; then
    compose stop backup minecraft || true
    fail "Rollback health check failed; archive, rescue tree, and restored tree were preserved"
    return 1
  fi
  printf 'Rescue: %s\n' "$rescue_path"
}

main() {
  local command_name=${1:-}
  if [[ -z "$command_name" ]]; then
    usage
    return 1
  fi
  case "$command_name" in
    start|stop|backup|update|rollback)
      [[ -x "$SAFETY_HELPER" ]] || { fail "Safety helper is unavailable"; return 1; }
      acquire_mutation_lock "$@"
      verify_mutation_authority "$command_name" || return 1
      ;;
  esac
  shift

  case "$command_name" in
    doctor)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_doctor
      ;;
    start)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_start
      ;;
    stop)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_stop
      ;;
    status)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_status
      ;;
    backup)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_backup
      ;;
    update)
      [[ "$#" -eq 0 ]] || { usage; return 1; }
      run_update
      ;;
    rollback)
      run_rollback "$@"
      ;;
    *)
      usage
      return 1
      ;;
  esac
}

main "$@"
