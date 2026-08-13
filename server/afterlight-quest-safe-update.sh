#!/usr/bin/env bash
set -Eeuo pipefail

umask 077

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)
REPOSITORY_ROOT=$(cd "$SCRIPT_DIR/.." && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
ENV_FILE=${AFTERLIGHT_ENV_FILE:-$SCRIPT_DIR/.env}
OPERATOR=${AFTERLIGHT_OPERATOR:-$SCRIPT_DIR/afterlight-server.sh}
PROGRESS_GUARD=${AFTERLIGHT_PROGRESS_GUARD:-$SCRIPT_DIR/afterlight-progress-guard.py}
RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-/run/afterlight}
SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-/var/lib/afterlight/quest-update-snapshots}
QUARANTINE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-/var/lib/afterlight/quest-update-quarantine}
HEALTH_TIMEOUT=${AFTERLIGHT_HEALTH_TIMEOUT:-600}
POLL_INTERVAL=${AFTERLIGHT_POLL_INTERVAL:-2}
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
WHITELIST_SHA=""
USERCACHE_SHA=""
GATE_COMMENT=""
GATE_INSTALLED=0
SNAPSHOT_READY=0
BACKUP_VERIFIED=0
TRANSACTION_COMPLETE=0
CLEANUP_ACTIVE=0

usage() {
  printf '%s\n' \
    'Usage: server/afterlight-quest-safe-update.sh EXPECTED_SHA --confirm' >&2
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
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

sha256_file() {
  sha256sum "$1" | awk '{print $1}'
}

load_paths() {
  [[ -f "$ENV_FILE" && ! -L "$ENV_FILE" ]] || fail "Environment file is missing or unsafe"
  local assignment
  local data_seen=0
  local backup_seen=0
  local secrets_seen=0
  while IFS= read -r assignment || [[ -n "$assignment" ]]; do
    case "$assignment" in
      DATA_DIR=*)
        ((data_seen += 1))
        DATA_DIR=${assignment#DATA_DIR=}
        ;;
      BACKUP_DIR=*)
        ((backup_seen += 1))
        BACKUP_DIR=${assignment#BACKUP_DIR=}
        ;;
      SECRETS_DIR=*)
        ((secrets_seen += 1))
        SECRETS_DIR=${assignment#SECRETS_DIR=}
        ;;
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
    [[ -d "$configured_path" && ! -L "$configured_path" ]] || {
      fail "Environment paths must be real directories"
      return 1
    }
  done
}

compose() {
  AFTERLIGHT_PACKWIZ_URL="$RAW_PACK_URL_PREFIX/$ACTIVE_SHA/pack.toml" \
    docker compose \
    --project-name afterlight \
    --env-file "$ENV_FILE" \
    -f "$COMPOSE_FILE" \
    "$@"
}

container_health() {
  docker inspect \
    --format '{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
    "$1"
}

container_state() {
  docker inspect --format '{{.State.Status}}' "$1"
}

container_restart_policy() {
  docker inspect --format '{{.HostConfig.RestartPolicy.Name}}' "$1"
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
  local output
  local cleaned
  local reported
  local maximum
  local listed
  if ! output=$(docker exec "$MINECRAFT_ID" rcon-cli list </dev/null 2>&1); then
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

insert_gate() {
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$GATE_COMMENT"
    -j REJECT
  )
  if ! iptables -w -I DOCKER-USER 1 "${rule[@]}"; then
    if iptables -w -C DOCKER-USER "${rule[@]}"; then
      GATE_INSTALLED=1
    fi
    fail "Firewall gate insertion failed"
    return 1
  fi
  GATE_INSTALLED=1
  if ! iptables -w -C DOCKER-USER "${rule[@]}"; then
    fail "Firewall gate verification failed"
    return 1
  fi
}

remove_gate() {
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$GATE_COMMENT"
    -j REJECT
  )
  iptables -w -C DOCKER-USER "${rule[@]}" || {
    fail "Owned firewall rule is missing"
    return 1
  }
  iptables -w -D DOCKER-USER "${rule[@]}" || {
    fail "Owned firewall rule deletion failed"
    return 1
  }
  if iptables -w -C DOCKER-USER "${rule[@]}"; then
    fail "Owned firewall rule persisted after deletion"
    return 1
  fi
  GATE_INSTALLED=0
}

write_pack_sha() {
  local pack_sha=$1
  local temporary="$DATA_DIR/.afterlight-pack-sha.tmp.$$"
  printf '%s\n' "$pack_sha" > "$temporary"
  mv "$temporary" "$DATA_DIR/.afterlight-pack-sha"
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
    docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' "$MINECRAFT_ID" |
      sed -n 's/^PACKWIZ_URL=//p'
  ) || return 1
  [[ "$configured_urls" == "$expected_url" ]] || return 1
  write_pack_sha "$pack_sha" || return 1
}

verify_integrity_files() {
  [[ -f "$DATA_DIR/whitelist.json" && ! -L "$DATA_DIR/whitelist.json" ]] || return 1
  [[ -f "$DATA_DIR/usercache.json" && ! -L "$DATA_DIR/usercache.json" ]] || return 1
  [[ "$(sha256_file "$DATA_DIR/whitelist.json")" == "$WHITELIST_SHA" ]] || return 1
  [[ "$(sha256_file "$DATA_DIR/usercache.json")" == "$USERCACHE_SHA" ]]
}

create_snapshot() {
  local stamp
  local progress_snapshot
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  SNAPSHOT_DIR="$SNAPSHOT_ROOT/quest-update-$stamp-$$-$RANDOM"
  mkdir -m 0700 "$SNAPSHOT_DIR" || return 1
  [[ "$(stat_mode "$SNAPSHOT_DIR")" == "700" ]] || return 1
  progress_snapshot="$SNAPSHOT_DIR/progress"
  mkdir -m 0700 "$progress_snapshot" || return 1
  "$PROGRESS_GUARD" snapshot \
    --world "$DATA_DIR/world" \
    --output "$progress_snapshot" || return 1
  [[ "$(stat_mode "$SNAPSHOT_DIR")" == "700" ]] || return 1
  [[ "$(stat_mode "$progress_snapshot")" == "700" ]] || return 1
  SNAPSHOT_READY=1
}

create_verified_archive() {
  local verify_dir="$SNAPSHOT_DIR/preflight-$RANDOM"
  local digest
  ARCHIVE_PATH="$SNAPSHOT_DIR/full-backup.tar.zst"
  tar --create --zstd --file "$ARCHIVE_PATH" --directory "$DATA_DIR" . || return 1
  [[ -f "$ARCHIVE_PATH" && ! -L "$ARCHIVE_PATH" && -s "$ARCHIVE_PATH" ]] || return 1
  mkdir -m 0700 "$verify_dir" || return 1
  if ! tar --extract --zstd --file "$ARCHIVE_PATH" \
    --directory "$verify_dir" --no-same-owner --no-same-permissions; then
    return 1
  fi
  [[ -s "$verify_dir/world/level.dat" ]] || return 1
  [[ -d "$verify_dir/world/ftbquests" && -d "$verify_dir/world/ftbteams" ]] || return 1
  [[ -z "$(find "$verify_dir" -type l -print -quit)" ]] || return 1
  [[ "$(cat "$verify_dir/.afterlight-pack-sha")" == "$PRIOR_SHA" ]] || return 1
  [[ "$(sha256_file "$verify_dir/whitelist.json")" == "$WHITELIST_SHA" ]] || return 1
  [[ "$(sha256_file "$verify_dir/usercache.json")" == "$USERCACHE_SHA" ]] || return 1
  find "$verify_dir" -depth -delete || return 1
  digest=$(sha256_file "$ARCHIVE_PATH") || return 1
  printf '%s  %s\n' "$digest" "full-backup.tar.zst" > "$SNAPSHOT_DIR/full-backup.sha256"
  chmod 0600 "$SNAPSHOT_DIR/full-backup.sha256"
  printf '{"archive_sha256":"%s","pack_sha":"%s","usercache_sha256":"%s","whitelist_sha256":"%s"}\n' \
    "$digest" "$PRIOR_SHA" "$USERCACHE_SHA" "$WHITELIST_SHA" \
    > "$SNAPSHOT_DIR/backup-preflight.json"
  chmod 0600 "$SNAPSHOT_DIR/backup-preflight.json"
  [[ "$(sha256_file "$ARCHIVE_PATH")" == "$digest" ]] || return 1
  BACKUP_VERIFIED=1
}

archive_digest_is_valid() {
  local checksum_file="$SNAPSHOT_DIR/full-backup.sha256"
  local expected_line
  local expected_digest
  [[ -f "$ARCHIVE_PATH" && ! -L "$ARCHIVE_PATH" && -s "$ARCHIVE_PATH" ]] || return 1
  [[ -f "$checksum_file" && ! -L "$checksum_file" ]] || return 1
  [[ "$(stat_mode "$checksum_file")" == "600" ]] || return 1
  [[ "$(awk 'END {print NR}' "$checksum_file")" -eq 1 ]] || return 1
  expected_line=$(cat "$checksum_file") || return 1
  [[ "$expected_line" =~ ^([0-9a-f]{64})[[:space:]][[:space:]]full-backup\.tar\.zst$ ]] || return 1
  expected_digest=${BASH_REMATCH[1]}
  [[ "$(sha256_file "$ARCHIVE_PATH")" == "$expected_digest" ]]
}

restore_verified_archive() {
  local data_parent
  local data_name
  local staging
  local rescue
  data_parent=$(dirname "$DATA_DIR")
  data_name=$(basename "$DATA_DIR")
  staging="$data_parent/.${data_name}.quest-restore-$$"
  rescue="$data_parent/${data_name}.rejected-$EXPECTED_SHA-$$"
  [[ ! -e "$staging" && ! -L "$staging" && ! -e "$rescue" && ! -L "$rescue" ]] || return 1
  archive_digest_is_valid || return 1
  mkdir -m 0700 "$staging" || return 1
  tar --extract --zstd --file "$ARCHIVE_PATH" \
    --directory "$staging" --no-same-owner --no-same-permissions || return 1
  [[ -s "$staging/world/level.dat" ]] || return 1
  [[ "$(cat "$staging/.afterlight-pack-sha")" == "$PRIOR_SHA" ]] || return 1
  mv "$DATA_DIR" "$rescue" || return 1
  mv "$staging" "$DATA_DIR" || return 1
}

compare_progress() {
  "$PROGRESS_GUARD" compare \
    --world "$DATA_DIR/world" \
    --snapshot "$SNAPSHOT_DIR/progress"
}

rollback_transaction() {
  ACTIVE_SHA=$PRIOR_SHA
  compose stop backup minecraft >/dev/null 2>&1 || true
  if [[ "$SNAPSHOT_READY" -ne 1 ]]; then
    create_snapshot || return 1
  fi
  if [[ "$BACKUP_VERIFIED" -ne 1 ]]; then
    create_verified_archive || return 1
  fi
  restore_verified_archive || return 1
  write_pack_sha "$PRIOR_SHA" || return 1
  start_minecraft "$PRIOR_SHA" || return 1
  stop_minecraft_cleanly || return 1
  if [[ "$SNAPSHOT_READY" -eq 1 ]]; then
    compare_progress || return 1
  fi
  verify_integrity_files || return 1
  start_minecraft "$PRIOR_SHA" || return 1
  ACTIVE_SHA=$PRIOR_SHA
  compose up -d backup || return 1
  BACKUP_ID=$(compose ps -q backup) || return 1
  [[ -n "$BACKUP_ID" ]] || return 1
  [[ "$(container_health "$BACKUP_ID")" == "running|healthy" ]] || return 1
}

write_quarantine() {
  local -a rule=(
    -p tcp --dport 25565
    -m conntrack --ctstate NEW
    -m comment --comment "$GATE_COMMENT"
    -j REJECT
  )
  docker update --restart=no "$MINECRAFT_ID" "$BACKUP_ID" >/dev/null || return 1
  docker stop "$MINECRAFT_ID" "$BACKUP_ID" >/dev/null || return 1
  local container_id
  for container_id in "$MINECRAFT_ID" "$BACKUP_ID"; do
    [[ "$(container_restart_policy "$container_id")" == "no" ]] || return 1
    [[ "$(container_state "$container_id")" != "running" ]] || return 1
  done
  iptables -w -C DOCKER-USER "${rule[@]}" || return 1
  mkdir -p "$QUARANTINE_DIR" || return 1
  chmod 0711 "$QUARANTINE_DIR" || return 1
  local temporary="$QUARANTINE_DIR/.state.tmp.$$"
  {
    printf 'schema=1\n'
    printf 'comment=%s\n' "$GATE_COMMENT"
    printf 'expected_sha=%s\n' "$EXPECTED_SHA"
    printf 'snapshot_dir=%s\n' "${SNAPSHOT_DIR:-none}"
  } > "$temporary"
  chmod 0600 "$temporary"
  mv "$temporary" "$QUARANTINE_DIR/state"
  [[ "$(stat_mode "$QUARANTINE_DIR/state")" == "600" ]]
}

on_signal() {
  fail "Quest-safe update interrupted"
  exit 130
}

on_exit() {
  local status=$?
  trap - EXIT INT TERM HUP
  if [[ "$TRANSACTION_COMPLETE" -eq 1 || "$CLEANUP_ACTIVE" -eq 1 ]]; then
    exit "$status"
  fi
  CLEANUP_ACTIVE=1
  if [[ "$GATE_INSTALLED" -eq 1 ]]; then
    if rollback_transaction && remove_gate; then
      printf 'ROLLBACK: VERIFIED\n' >&2
    else
      if write_quarantine; then
        printf 'ROLLBACK FAILED: QUARANTINED\n' >&2
      else
        printf 'ROLLBACK FAILED: QUARANTINE INCOMPLETE\n' >&2
      fi
    fi
  fi
  exit "$status"
}

main() {
  if [[ "$#" -ne 2 || "$2" != "--confirm" ]]; then
    usage
    return 1
  fi
  EXPECTED_SHA=$1
  if [[ ! "$EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]; then
    fail "EXPECTED_SHA must be 40 lowercase hexadecimal characters"
    return 1
  fi
  if [[ ! "$HEALTH_TIMEOUT" =~ ^[0-9]+$ || ! "$POLL_INTERVAL" =~ ^[0-9]+$ ]]; then
    fail "Health timing values must be nonnegative integers"
    return 1
  fi
  local command_name
  for command_name in awk cat date docker find flock git iptables mkdir mv sed sha256sum stat tar; do
    require_command "$command_name" || return 1
  done
  [[ -x "$OPERATOR" ]] || { fail "Operator preflight command is unavailable"; return 1; }
  [[ -x "$PROGRESS_GUARD" ]] || { fail "Progress guard is unavailable"; return 1; }
  [[ -d "$RUNTIME_DIR" && -d "$SNAPSHOT_ROOT" ]] || {
    fail "Runtime or snapshot root is missing"
    return 1
  }
  [[ ! -e "$QUARANTINE_DIR/state" && ! -L "$QUARANTINE_DIR/state" ]] || {
    fail "Durable quest update quarantine is active"
    return 1
  }
  exec 9>"$RUNTIME_DIR/maintenance.lock"
  if ! flock -n 9; then
    fail "Unable to acquire maintenance lock"
    return 1
  fi
  load_paths || return 1
  if ! "$OPERATOR" doctor </dev/null >/dev/null; then
    fail "Operator preflight failed"
    return 1
  fi
  local repository_sha
  repository_sha=$(git -C "$REPOSITORY_ROOT" rev-parse --verify 'HEAD^{commit}') || return 1
  if [[ "$repository_sha" != "$EXPECTED_SHA" ]]; then
    fail "Repository HEAD does not equal EXPECTED_SHA"
    return 1
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
  GATE_COMMENT="afterlight-quest-update-$EXPECTED_SHA-$$"
  insert_gate || return 1
  require_zero_players || return 1
  if ! docker exec "$MINECRAFT_ID" rcon-cli save-all flush </dev/null >/dev/null; then
    fail "RCON save-all flush failed"
    return 1
  fi
  if ! stop_both_cleanly; then
    fail "Clean shutdown failed"
    return 1
  fi
  if ! create_snapshot; then
    fail "Snapshot creation or mode 0700 verification failed"
    return 1
  fi
  if ! create_verified_archive; then
    fail "Direct backup verification failed"
    return 1
  fi
  if ! start_minecraft "$EXPECTED_SHA"; then
    fail "Candidate start or pack SHA verification failed"
    return 1
  fi
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
  remove_gate || return 1
  TRANSACTION_COMPLETE=1
  printf 'Snapshot digest: %s\n' "$(awk '{print $1}' "$SNAPSHOT_DIR/full-backup.sha256")"
  printf 'QUEST-SAFE UPDATE: OK %s\n' "$EXPECTED_SHA"
}

trap on_signal INT TERM HUP
trap on_exit EXIT
main "$@"
