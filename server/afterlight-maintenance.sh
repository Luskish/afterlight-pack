#!/usr/bin/env bash
set -euo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
source "$SCRIPT_DIR/afterlight-safety-contract.sh"
afterlight_load_safety_contract "$SCRIPT_DIR" || exit 1
MIN_UPTIME_SECONDS=${AFTERLIGHT_MIN_UPTIME_SECONDS:-72000}
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
PLAYER_PATTERN='^There are ([0-9]+) of a max of ([0-9]+) players online: ?([A-Za-z0-9_, ]*)$'

compose() {
  docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

require_command() {
  local command_name=$1
  command -v "$command_name" >/dev/null 2>&1 ||
    fail "Required command not found: $command_name"
}

stat_value() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

acquire_shared_lock() {
  [[ -x "$SAFETY_HELPER" ]] || fail "Safety helper is unavailable"
  [[ -d "$RUNTIME_DIR" && ! -L "$RUNTIME_DIR" ]] || fail "Runtime directory is missing or unsafe"
  afterlight_verify_or_reexec_lock 3600 300 "$@"
}

verify_no_transaction_authority() {
  [[ -d "$QUARANTINE_DIR" && ! -L "$QUARANTINE_DIR" ]] || fail "Transaction authority directory is missing or unsafe"
  [[ -d "$SNAPSHOT_ROOT" && ! -L "$SNAPSHOT_ROOT" ]] || fail "Snapshot root is missing or unsafe"
  local -a common=()
  while IFS= read -r -d '' value; do common+=("$value"); done < <(afterlight_state_arguments)
  local authority_status=0
  if "$SAFETY_HELPER" authority-status \
    "${common[@]}" >/dev/null 2>&1; then
    fail "Maintenance rejected because a quest update transaction is active"
    return 1
  else
    authority_status=$?
  fi
  if [[ "$authority_status" -ne 3 ]]; then
    fail "Maintenance rejected because transaction authority is unsafe"
    return 1
  fi
}

player_count() {
  local container_id=$1
  local cleaned_output
  local listed_players
  local maximum_players
  local reported_players
  local rcon_output

  if ! rcon_output=$(docker exec "$container_id" rcon-cli list </dev/null 2>&1); then
    fail "RCON player query failed"
    return 1
  fi
  cleaned_output=$(printf '%s\n' "$rcon_output" | sed $'s/\033\\[[0-9;]*[[:alpha:]]//g')
  cleaned_output=${cleaned_output//$'\r'/}
  if [[ "$cleaned_output" == *$'\n'* || ! "$cleaned_output" =~ $PLAYER_PATTERN ]]; then
    fail "Unable to parse RCON player count"
    return 1
  fi
  reported_players=${BASH_REMATCH[1]}
  maximum_players=${BASH_REMATCH[2]}
  listed_players=${BASH_REMATCH[3]// /}
  if ((reported_players > maximum_players)); then
    fail "RCON player count exceeds configured maximum"
    return 1
  fi
  if ((reported_players == 0)) && [[ -n "$listed_players" ]]; then
    fail "RCON zero player count contradicts listed names"
    return 1
  fi
  printf '%s\n' "$reported_players"
}

container_health() {
  local container_id=$1
  docker inspect \
    --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "$container_id"
}

validate_same_healthy_container() {
  local expected_container_id=$1
  local expected_started_at=$2
  local current_container_id
  local current_started_at
  local health

  current_container_id=$(compose ps -q minecraft) || return 1
  if [[ "$current_container_id" != "$expected_container_id" ]]; then
    fail "Minecraft container changed during maintenance"
    return 1
  fi
  current_started_at=$(
    docker inspect --format '{{.State.StartedAt}}' "$expected_container_id"
  ) || return 1
  if [[ "$current_started_at" != "$expected_started_at" ]]; then
    fail "Minecraft container start time changed during maintenance"
    return 1
  fi
  health=$(container_health "$expected_container_id") || return 1
  if [[ "$health" != "running|healthy" ]]; then
    fail "Minecraft became unhealthy during maintenance: $health"
    return 1
  fi
}

announce_restart() {
  local container_id=$1
  local message=$2

  if ! docker exec "$container_id" rcon-cli say "$message" \
    </dev/null >/dev/null 2>&1; then
    fail "RCON restart warning failed"
    return 1
  fi
}

main() {
  local backup_path
  local container_age
  local container_id
  local current_epoch
  local health
  local mode=${1:-idle}
  local players
  local started_at
  local started_epoch

  afterlight_require_control_root || return 1

  if [[ "$#" -gt 1 ]]; then
    fail "Usage: server/afterlight-maintenance.sh [idle|scheduled]"
    return 1
  fi
  case "$mode" in
    idle|scheduled) ;;
    *)
      fail "Usage: server/afterlight-maintenance.sh [idle|scheduled]"
      return 1
      ;;
  esac

  require_command date || return 1
  require_command docker || return 1
  require_command sed || return 1
  if [[ "$mode" == "scheduled" ]]; then
    require_command sleep || return 1
  fi
  [[ -x "$OPERATOR" ]] || fail "Operator is not executable: $OPERATOR"
  [[ -d "$RUNTIME_DIR" ]] || fail "Runtime directory is missing: $RUNTIME_DIR"
  if [[ "$mode" == "idle" ]]; then
    if [[ ! "$MIN_UPTIME_SECONDS" =~ ^[0-9]+$ ]]; then
      fail "AFTERLIGHT_MIN_UPTIME_SECONDS must be a nonnegative integer"
      return 1
    fi
    if ((MIN_UPTIME_SECONDS < 72000)); then
      fail "AFTERLIGHT_MIN_UPTIME_SECONDS must be at least 72000"
      return 1
    fi
  fi

  acquire_shared_lock "$@"
  verify_no_transaction_authority || return 1
  cd "$REPOSITORY_ROOT"

  container_id=$(compose ps -q minecraft)
  if [[ -z "$container_id" ]]; then
    printf 'Maintenance skipped: Minecraft is intentionally stopped\n'
    return 0
  fi

  health=$(container_health "$container_id") || return 1
  if [[ "$health" != "running|healthy" ]]; then
    fail "Minecraft is not healthy: $health"
    return 1
  fi

  started_at=$(docker inspect --format '{{.State.StartedAt}}' "$container_id") || return 1
  if [[ "$mode" == "scheduled" ]]; then
    players=$(player_count "$container_id") || return 1
    printf 'Scheduled restart: %s players online\n' "$players"
    announce_restart "$container_id" \
      "AFTERLIGHT restarts daily at 5:00 AM Eastern. Restart in 15 minutes." || return 1
    sleep 600 || return 1
    validate_same_healthy_container "$container_id" "$started_at" || return 1
    announce_restart "$container_id" \
      "AFTERLIGHT restart in 5 minutes. Please reach a safe stopping point." || return 1
    sleep 240 || return 1
    validate_same_healthy_container "$container_id" "$started_at" || return 1
    announce_restart "$container_id" \
      "AFTERLIGHT restart in 1 minute. Please disconnect safely." || return 1
    sleep 60 || return 1
    validate_same_healthy_container "$container_id" "$started_at" || return 1
  else
    started_epoch=$(date -d "$started_at" +%s) || {
      fail "Unable to parse container start time: $started_at"
      return 1
    }
    current_epoch=$(date -u +%s) || return 1
    if ((started_epoch > current_epoch)); then
      fail "Container start time is in the future"
      return 1
    fi
    container_age=$((current_epoch - started_epoch))
    if ((container_age < MIN_UPTIME_SECONDS)); then
      printf 'Maintenance skipped: uptime %ss is below %ss\n' \
        "$container_age" "$MIN_UPTIME_SECONDS"
      return 0
    fi

    players=$(player_count "$container_id") || return 1
    if ((players > 0)); then
      printf 'Maintenance skipped: %s players online\n' "$players"
      return 0
    fi
  fi

  printf 'Maintenance backup: starting\n'
  backup_path=$("$OPERATOR" backup </dev/null) || {
    fail "Verified backup failed, server was not stopped"
    return 1
  }
  if [[ -z "$backup_path" || ! -f "$backup_path" ]]; then
    fail "Backup command did not return a regular archive"
    return 1
  fi

  validate_same_healthy_container "$container_id" "$started_at" || return 1
  if [[ "$mode" == "idle" ]]; then
    players=$(player_count "$container_id") || return 1
    if ((players > 0)); then
      printf 'Maintenance skipped after backup: %s players online\n' "$players"
      return 0
    fi
  fi

  if [[ "$mode" == "scheduled" ]]; then
    printf 'Scheduled restart: backup=%s\n' "$backup_path"
    announce_restart "$container_id" \
      "AFTERLIGHT is restarting now. World backup verified." || return 1
  else
    printf 'Maintenance restart: backup=%s\n' "$backup_path"
  fi
  "$OPERATOR" stop </dev/null
  "$OPERATOR" start </dev/null
  "$OPERATOR" status </dev/null
  if [[ "$mode" == "scheduled" ]]; then
    printf 'Scheduled restart: OK\n'
  else
    printf 'Maintenance restart: OK\n'
  fi
}

main "$@"
