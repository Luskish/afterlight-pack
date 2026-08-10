#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE="${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}"
PROPERTIES_TEMPLATE="$SCRIPT_DIR/server.properties.example"
AFTERLIGHT_HEALTH_TIMEOUT="${AFTERLIGHT_HEALTH_TIMEOUT:-600}"

DATA_DIR=""
BACKUP_DIR=""
SECRETS_DIR=""

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

load_paths() {
  [[ -f "$ENV_FILE" ]] || fail "Environment file not found: $ENV_FILE"

  local data_seen=0
  local backup_seen=0
  local secrets_seen=0
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
}

compose() {
  docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
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
  local properties_file
  properties_file="$DATA_DIR/server.properties"
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

run_start() {
  run_doctor true || return 1
  install_properties_once || return 1
  compose up -d minecraft backup
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
  local before_names
  local after_snapshot
  local relative_name
  local size
  local mtime
  local backup_path=""

  run_doctor true || return 1
  before_snapshot=$(latest_backup_snapshot) || return 1
  before_names=$(printf '%s\n' "$before_snapshot" | cut -f1)
  compose exec backup backup now || return 1
  after_snapshot=$(latest_backup_snapshot) || return 1

  while IFS=$'\t' read -r relative_name size mtime; do
    [[ -n "$relative_name" ]] || continue
    if ! printf '%s\n' "$before_names" | grep -Fqx "$relative_name"; then
      backup_path="$BACKUP_DIR/$relative_name"
    fi
  done <<< "$after_snapshot"

  if [[ -z "$backup_path" || ! -f "$backup_path" || -L "$backup_path" ]]; then
    fail "Backup command produced no new regular backup archive"
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

  run_doctor true || return 1
  data_parent=$(dirname "$DATA_DIR")
  data_basename=$(basename "$DATA_DIR")
  rescue_path="$data_parent/$data_basename.rescue-$(date -u +%Y%m%dT%H%M%SZ)"
  [[ ! -e "$rescue_path" && ! -L "$rescue_path" ]] ||
    fail "Rollback rescue path already exists: $rescue_path"

  compose stop backup minecraft
  mv "$DATA_DIR" "$rescue_path"
  mkdir "$DATA_DIR"
  if ! zstd --decompress --stdout "$canonical_backup" |
    tar --extract --file - --directory "$DATA_DIR" --no-same-owner --no-same-permissions; then
    fail "Rollback extraction failed; archive, rescue tree, and restored tree were preserved"
    return 1
  fi
  if ! install_properties_once; then
    fail "Rollback properties setup failed; archive, rescue tree, and restored tree were preserved"
    return 1
  fi
  if ! compose up -d minecraft backup; then
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
