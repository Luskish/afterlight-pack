#!/usr/bin/env bash

AFTERLIGHT_TEST_CONTRACT_MAGIC='AFTERLIGHT SAFETY TEST CONTRACT v1'

afterlight_contract_fail() {
  printf 'ERROR: %s\n' "$*" >&2
  return 1
}

afterlight_contract_stat() {
  local format=$1 target=$2
  stat -c "$format" "$target" 2>/dev/null || stat -f "$format" "$target"
}

afterlight_reject_production_override() {
  local variable_name
  for variable_name in \
    AFTERLIGHT_ENV_FILE \
    AFTERLIGHT_RUNTIME_DIR \
    AFTERLIGHT_QUARANTINE_DIR \
    AFTERLIGHT_SNAPSHOT_ROOT \
    AFTERLIGHT_SAFETY_HELPER \
    AFTERLIGHT_OPERATOR \
    AFTERLIGHT_PROGRESS_GUARD \
    AFTERLIGHT_LOCK_OWNER_UID \
    AFTERLIGHT_LOCK_GROUP_GID \
    AFTERLIGHT_STATE_OWNER_UID \
    AFTERLIGHT_STATE_GROUP_GID \
    AFTERLIGHT_SNAPSHOT_OWNER_UID \
    AFTERLIGHT_SNAPSHOT_GROUP_GID \
    AFTERLIGHT_DATA_PARENT_UID; do
    if [[ -n ${!variable_name+x} ]]; then
      afterlight_contract_fail "Production safety path or identity override is forbidden: $variable_name"
      return 1
    fi
  done
}

afterlight_require_test_path() {
  local actual=$1 expected=$2 label=$3
  if [[ "$actual" != "$expected" ]]; then
    afterlight_contract_fail "$label must be derived from AFTERLIGHT_SAFETY_TEST_ROOT"
    return 1
  fi
}

afterlight_load_safety_contract() {
  local script_dir=$1
  local test_root=${AFTERLIGHT_SAFETY_TEST_ROOT:-}
  if [[ -n "$test_root" ]]; then
    if [[ "$script_dir" == /opt/afterlight/server ]]; then
      afterlight_contract_fail "Installed production scripts reject the test contract"
      return 1
    fi
    [[ "$test_root" == /* && "$test_root" != / ]] || {
      afterlight_contract_fail "AFTERLIGHT_SAFETY_TEST_ROOT must be absolute"
      return 1
    }
    test_root=$(cd "$test_root" 2>/dev/null && pwd -P) || {
      afterlight_contract_fail "AFTERLIGHT_SAFETY_TEST_ROOT is unavailable"
      return 1
    }
    local temp_base
    temp_base=$(cd "${TMPDIR:-/tmp}" && pwd -P)
    case "$test_root" in
      /tmp/*|/private/tmp/*|"$temp_base"/*) ;;
      *)
        afterlight_contract_fail "AFTERLIGHT_SAFETY_TEST_ROOT must be beneath a temporary root"
        return 1
        ;;
    esac
    local marker="$test_root/.afterlight-safety-test-contract"
    [[ -f "$marker" && ! -L "$marker" ]] || {
      afterlight_contract_fail "Explicit safety test contract marker is missing"
      return 1
    }
    [[ $(cat "$marker") == "$AFTERLIGHT_TEST_CONTRACT_MAGIC" ]] || {
      afterlight_contract_fail "Explicit safety test contract marker is invalid"
      return 1
    }
    [[ $(afterlight_contract_stat '%Lp' "$marker") == 600 ]] || {
      afterlight_contract_fail "Explicit safety test contract marker mode must be 0600"
      return 1
    }
    [[ $(afterlight_contract_stat '%u' "$marker") == "$(id -u)" ]] || {
      afterlight_contract_fail "Explicit safety test contract marker owner is invalid"
      return 1
    }
    [[ $(afterlight_contract_stat '%g' "$marker") == "$(id -g)" ]] || {
      afterlight_contract_fail "Explicit safety test contract marker group is invalid"
      return 1
    }

    REPOSITORY_ROOT=$(cd "$script_dir/.." && pwd -P)
    ENV_FILE=${AFTERLIGHT_ENV_FILE:-$test_root/server.env}
    RUNTIME_DIR=${AFTERLIGHT_RUNTIME_DIR:-$test_root/run}
    STATE_DIR=${AFTERLIGHT_QUARANTINE_DIR:-$test_root/quarantine}
    QUARANTINE_DIR=$STATE_DIR
    SNAPSHOT_ROOT=${AFTERLIGHT_SNAPSHOT_ROOT:-$test_root/snapshots}
    DATA_DIR=$test_root/data
    BACKUP_DIR=$test_root/backups
    SECRETS_DIR=$test_root/secrets
    SAFETY_HELPER=${AFTERLIGHT_SAFETY_HELPER:-$script_dir/afterlight-safety.py}
    OPERATOR=${AFTERLIGHT_OPERATOR:-$script_dir/afterlight-server.sh}
    PROGRESS_GUARD=${AFTERLIGHT_PROGRESS_GUARD:-$script_dir/afterlight-progress-guard.py}
    afterlight_require_test_path "$ENV_FILE" "$test_root/server.env" "Test environment file" || return 1
    afterlight_require_test_path "$RUNTIME_DIR" "$test_root/run" "Test runtime directory" || return 1
    afterlight_require_test_path "$STATE_DIR" "$test_root/quarantine" "Test state directory" || return 1
    afterlight_require_test_path "$SNAPSHOT_ROOT" "$test_root/snapshots" "Test snapshot root" || return 1
    CONTROL_UID=$(id -u)
    CONTROL_GID=$(id -g)
    RUNTIME_MODE=750
    LOCK_MODE=660
    STATE_DIR_MODE=750
    STATE_FILE_MODE=640
    SNAPSHOT_ROOT_MODE=700
    AFTERLIGHT_CONTRACT_MODE='test'
    export REPOSITORY_ROOT ENV_FILE RUNTIME_DIR STATE_DIR QUARANTINE_DIR SNAPSHOT_ROOT
    export DATA_DIR BACKUP_DIR SECRETS_DIR SAFETY_HELPER OPERATOR PROGRESS_GUARD
    export CONTROL_UID CONTROL_GID RUNTIME_MODE LOCK_MODE STATE_DIR_MODE STATE_FILE_MODE
    export SNAPSHOT_ROOT_MODE AFTERLIGHT_CONTRACT_MODE
    return 0
  fi

  afterlight_reject_production_override || return 1
  [[ "$script_dir" == /opt/afterlight/server ]] || {
    afterlight_contract_fail "Production safety scripts must run from /opt/afterlight/server"
    return 1
  }
  REPOSITORY_ROOT=/opt/afterlight
  ENV_FILE=/opt/afterlight/server/.env
  RUNTIME_DIR=/run/afterlight
  STATE_DIR=/var/lib/afterlight/quest-update-quarantine
  QUARANTINE_DIR=$STATE_DIR
  SNAPSHOT_ROOT=/var/lib/afterlight/quest-update-snapshots
  DATA_DIR=/srv/afterlight/data
  BACKUP_DIR=/srv/afterlight/backups
  SECRETS_DIR=/etc/afterlight/secrets
  SAFETY_HELPER=/opt/afterlight/server/afterlight-safety.py
  OPERATOR=/opt/afterlight/server/afterlight-server.sh
  PROGRESS_GUARD=/opt/afterlight/server/afterlight-progress-guard.py
  CONTROL_UID=0
  CONTROL_GID=0
  RUNTIME_MODE=700
  LOCK_MODE=600
  STATE_DIR_MODE=700
  STATE_FILE_MODE=600
  SNAPSHOT_ROOT_MODE=700
  AFTERLIGHT_CONTRACT_MODE='production'
  export REPOSITORY_ROOT ENV_FILE RUNTIME_DIR STATE_DIR QUARANTINE_DIR SNAPSHOT_ROOT
  export DATA_DIR BACKUP_DIR SECRETS_DIR SAFETY_HELPER OPERATOR PROGRESS_GUARD
  export CONTROL_UID CONTROL_GID RUNTIME_MODE LOCK_MODE STATE_DIR_MODE STATE_FILE_MODE
  export SNAPSHOT_ROOT_MODE AFTERLIGHT_CONTRACT_MODE
}

afterlight_require_control_root() {
  if [[ "$AFTERLIGHT_CONTRACT_MODE" == production && $(id -u) -ne 0 ]]; then
    afterlight_contract_fail "AFTERLIGHT host control actions must run as root"
    return 1
  fi
}

afterlight_verify_or_reexec_lock() {
  local timeout=$1 termination_grace=$2
  shift 2
  if [[ -n ${AFTERLIGHT_LOCK_FD:-} ]]; then
    "$SAFETY_HELPER" lock-verify \
      --runtime-dir "$RUNTIME_DIR" \
      --runtime-mode "$RUNTIME_MODE" \
      --lock-mode "$LOCK_MODE" \
      --lock-fd "$AFTERLIGHT_LOCK_FD" \
      --owner-uid "$CONTROL_UID" \
      --group-gid "$CONTROL_GID"
    return
  fi
  exec "$SAFETY_HELPER" lock-run \
    --runtime-dir "$RUNTIME_DIR" \
    --runtime-mode "$RUNTIME_MODE" \
    --lock-mode "$LOCK_MODE" \
    --timeout "$timeout" \
    --termination-grace "$termination_grace" \
    --owner-uid "$CONTROL_UID" \
    --group-gid "$CONTROL_GID" \
    -- "$0" "$@"
}

afterlight_state_arguments() {
  printf '%s\0' \
    --state-dir "$STATE_DIR" \
    --state-dir-mode "$STATE_DIR_MODE" \
    --state-file-mode "$STATE_FILE_MODE" \
    --owner-uid "$CONTROL_UID" \
    --group-gid "$CONTROL_GID" \
    --snapshot-owner-uid "$CONTROL_UID" \
    --snapshot-group-gid "$CONTROL_GID" \
    --snapshot-root-mode "$SNAPSHOT_ROOT_MODE" \
    --canonical-snapshot-root "$SNAPSHOT_ROOT"
}
