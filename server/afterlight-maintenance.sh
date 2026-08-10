#!/usr/bin/env bash
set -euo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
OPERATOR=${AFTERLIGHT_OPERATOR:-$SCRIPT_DIR/afterlight-server.sh}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
MIN_UPTIME_SECONDS=${AFTERLIGHT_MIN_UPTIME_SECONDS:-72000}
ENV_FILE="$SCRIPT_DIR/.env"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
PLAYER_PATTERN='^There are ([0-9]+) of a max of ([0-9]+) players online: ?[A-Za-z0-9_, ]*$'

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

player_count() {
  local container_id=$1
  local cleaned_output
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
  if ((${BASH_REMATCH[1]} > ${BASH_REMATCH[2]})); then
    fail "RCON player count exceeds configured maximum"
    return 1
  fi
  printf '%s\n' "${BASH_REMATCH[1]}"
}

container_health() {
  local container_id=$1
  docker inspect \
    --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "$container_id"
}

main() {
  local backup_path
  local container_age
  local container_id
  local current_container_id
  local current_epoch
  local current_started_at
  local health
  local players
  local started_at
  local started_epoch

  require_command date || return 1
  require_command docker || return 1
  require_command flock || return 1
  require_command sed || return 1
  [[ -x "$OPERATOR" ]] || fail "Operator is not executable: $OPERATOR"
  [[ -d "$RUNTIME_DIR" ]] || fail "Runtime directory is missing: $RUNTIME_DIR"
  if [[ ! "$MIN_UPTIME_SECONDS" =~ ^[0-9]+$ ]]; then
    fail "AFTERLIGHT_MIN_UPTIME_SECONDS must be a nonnegative integer"
    return 1
  fi
  if ((MIN_UPTIME_SECONDS < 72000)); then
    fail "AFTERLIGHT_MIN_UPTIME_SECONDS must be at least 72000"
    return 1
  fi

  cd "$REPOSITORY_ROOT"
  exec 9>"$RUNTIME_DIR/maintenance.lock"
  if ! flock -n 9; then
    printf 'Maintenance skipped: another maintenance process holds the lock\n'
    return 0
  fi

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

  printf 'Maintenance backup: starting\n'
  backup_path=$("$OPERATOR" backup </dev/null) || {
    fail "Verified backup failed, server was not stopped"
    return 1
  }
  if [[ -z "$backup_path" || ! -f "$backup_path" ]]; then
    fail "Backup command did not return a regular archive"
    return 1
  fi

  current_container_id=$(compose ps -q minecraft)
  if [[ "$current_container_id" != "$container_id" ]]; then
    fail "Minecraft container changed during maintenance"
    return 1
  fi
  current_started_at=$(docker inspect --format '{{.State.StartedAt}}' "$container_id") || return 1
  if [[ "$current_started_at" != "$started_at" ]]; then
    fail "Minecraft container start time changed during maintenance"
    return 1
  fi
  health=$(container_health "$container_id") || return 1
  if [[ "$health" != "running|healthy" ]]; then
    fail "Minecraft became unhealthy during maintenance: $health"
    return 1
  fi
  players=$(player_count "$container_id") || return 1
  if ((players > 0)); then
    printf 'Maintenance skipped after backup: %s players online\n' "$players"
    return 0
  fi

  printf 'Maintenance restart: backup=%s\n' "$backup_path"
  "$OPERATOR" stop </dev/null
  "$OPERATOR" start </dev/null
  "$OPERATOR" status </dev/null
  printf 'Maintenance restart: OK\n'
}

main "$@"
