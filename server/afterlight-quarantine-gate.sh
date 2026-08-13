#!/usr/bin/env bash
set -euo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE=${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}
QUARANTINE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
ATTEMPTS=${AFTERLIGHT_QUARANTINE_GATE_ATTEMPTS:-30}
INTERVAL=${AFTERLIGHT_QUARANTINE_GATE_INTERVAL:-2}
MARKER="$QUARANTINE_DIR/state"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
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

compose() {
  docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

container_state() {
  docker inspect --format '{{.State.Status}}' "$1"
}

container_restart_policy() {
  docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$1"
}

disable_containers() {
  local minecraft_id
  local backup_id
  minecraft_id=$(compose ps -aq minecraft) || return 1
  backup_id=$(compose ps -aq backup) || return 1
  [[ -n "$minecraft_id" && -n "$backup_id" ]] || {
    fail "Quarantined containers could not be identified"
    return 1
  }
  docker update --restart=no "$minecraft_id" "$backup_id" >/dev/null || return 1
  docker stop "$minecraft_id" "$backup_id" >/dev/null || return 1
  local container_id
  for container_id in "$minecraft_id" "$backup_id"; do
    [[ "$(container_restart_policy "$container_id")" == "no" ]] || return 1
    [[ "$(container_state "$container_id")" != "running" ]] || return 1
  done
}

read_marker() {
  [[ -d "$QUARANTINE_DIR" && ! -L "$QUARANTINE_DIR" ]] || {
    fail "Quarantine directory is unsafe"
    return 1
  }
  [[ "$(stat_mode "$QUARANTINE_DIR")" == "711" ]] || {
    fail "Quarantine directory mode must be 0711"
    return 1
  }
  [[ -f "$MARKER" && ! -L "$MARKER" ]] || {
    fail "Quarantine marker is unsafe"
    return 1
  }
  [[ "$(stat_mode "$MARKER")" == "600" ]] || {
    fail "Quarantine marker mode must be 0600"
    return 1
  }
  local schema=""
  local comment=""
  local expected_sha=""
  local snapshot_dir=""
  local line
  local schema_seen=0
  local comment_seen=0
  local sha_seen=0
  local snapshot_seen=0
  while IFS= read -r line || [[ -n "$line" ]]; do
    case "$line" in
      schema=*) ((schema_seen += 1)); schema=${line#schema=} ;;
      comment=*) ((comment_seen += 1)); comment=${line#comment=} ;;
      expected_sha=*) ((sha_seen += 1)); expected_sha=${line#expected_sha=} ;;
      snapshot_dir=*) ((snapshot_seen += 1)); snapshot_dir=${line#snapshot_dir=} ;;
      *) fail "Quarantine marker is malformed"; return 1 ;;
    esac
  done < "$MARKER"
  if [[ "$schema_seen" -ne 1 || "$comment_seen" -ne 1 || "$sha_seen" -ne 1 || "$snapshot_seen" -ne 1 ]]; then
    fail "Quarantine marker is malformed"
    return 1
  fi
  [[ "$schema" == "1" && "$expected_sha" =~ ^[0-9a-f]{40}$ ]] || {
    fail "Quarantine marker is malformed"
    return 1
  }
  [[ "$comment" =~ ^afterlight-quest-update-${expected_sha}-[0-9]+$ ]] || {
    fail "Quarantine marker is malformed"
    return 1
  }
  [[ "$snapshot_dir" =~ ^/[A-Za-z0-9._/-]+$ && "$snapshot_dir" != *"/../"* ]] || {
    fail "Quarantine marker is malformed"
    return 1
  }
  [[ -d "$snapshot_dir" && ! -L "$snapshot_dir" && "$(stat_mode "$snapshot_dir")" == "700" ]] || {
    fail "Quarantine snapshot is missing or unsafe"
    return 1
  }
  printf '%s\n' "$comment"
}

wait_for_chain() {
  local attempt
  for ((attempt = 1; attempt <= ATTEMPTS; attempt += 1)); do
    if iptables -w -n -L DOCKER-USER >/dev/null 2>&1; then
      return 0
    fi
    if ((attempt < ATTEMPTS)); then
      sleep "$INTERVAL"
    fi
  done
  fail "DOCKER-USER did not appear before the quarantine deadline"
}

main() {
  if [[ ! -e "$MARKER" && ! -L "$MARKER" ]]; then
    return 0
  fi
  [[ "$ATTEMPTS" =~ ^[1-9][0-9]*$ && "$INTERVAL" =~ ^[0-9]+$ ]] || {
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
  disable_containers || {
    fail "Quarantined containers could not be disabled"
    return 1
  }
  local comment
  comment=$(read_marker) || return 1
  wait_for_chain || return 1
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$comment"
    -j REJECT
  )
  if ! iptables -w -C DOCKER-USER "${rule[@]}"; then
    iptables -w -I DOCKER-USER 1 "${rule[@]}" || {
      fail "Quarantine firewall reconstruction failed"
      return 1
    }
  fi
  iptables -w -C DOCKER-USER "${rule[@]}" || {
    fail "Quarantine firewall verification failed"
    return 1
  }
  disable_containers || {
    fail "Quarantined containers did not remain disabled"
    return 1
  }
  printf 'QUARANTINE GATE: ACTIVE\n'
}

main "$@"
