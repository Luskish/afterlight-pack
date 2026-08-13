from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MAINTENANCE = ROOT / "server" / "afterlight-maintenance.sh"
SERVICE = ROOT / "server" / "systemd" / "afterlight-maintenance.service"
TIMER = ROOT / "server" / "systemd" / "afterlight-maintenance.timer"


class ServerMaintenanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)
        self.fake_bin = self.temp_path / "bin"
        self.runtime_dir = self.temp_path / "run"
        self.fake_bin.mkdir()
        self.runtime_dir.mkdir()
        self.docker_log = self.temp_path / "docker.log"
        self.event_log = self.temp_path / "events.log"
        self.operator_log = self.temp_path / "operator.log"
        self.quarantine_dir = self.temp_path / "quarantine"
        self.backup_path = self.temp_path / "backups" / "verified.tar.zst"
        self.backup_path.parent.mkdir()
        self.operator = self.temp_path / "operator"
        self._install_fakes()

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "AFTERLIGHT_OPERATOR": str(self.operator),
                "AFTERLIGHT_RUNTIME_DIR": str(self.runtime_dir),
                "FAKE_BACKUP_PATH": str(self.backup_path),
                "FAKE_DOCKER_LOG": str(self.docker_log),
                "FAKE_DOCKER_STATE_DIR": str(self.temp_path),
                "FAKE_EVENT_LOG": str(self.event_log),
                "FAKE_OPERATOR_LOG": str(self.operator_log),
                "FAKE_RCON_OUTPUT": (
                    "There are 0 of a max of 12 players online: "
                ),
                "AFTERLIGHT_QUARANTINE_DIR": str(self.quarantine_dir),
            }
        )

    def _write_executable(self, path: Path, source: str) -> None:
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _install_fakes(self) -> None:
        self._write_executable(
            self.fake_bin / "date",
            """
            #!/usr/bin/env bash
            if [ "${1:-}" = "-d" ]; then
              printf '0\n'
            elif [ "$*" = "-u +%s" ]; then
              printf '%s\n' "${FAKE_NOW_EPOCH:-1000000}"
            else
              exit 91
            fi
            """,
        )
        self._write_executable(
            self.fake_bin / "flock",
            """
            #!/usr/bin/env bash
            exit 0
            """,
        )
        self._write_executable(
            self.fake_bin / "sleep",
            """
            #!/usr/bin/env bash
            set -u
            [ "$#" -eq 1 ] || exit 90
            case "$1" in
              600|240|60) ;;
              *) exit 91 ;;
            esac
            printf 'sleep:%s\n' "$1" >> "$FAKE_EVENT_LOG"
            """,
        )
        self._write_executable(
            self.fake_bin / "docker",
            r"""
            #!/usr/bin/env bash
            set -u
            printf '%s\n' "$*" >> "$FAKE_DOCKER_LOG"
            case "${1:-}" in
              compose)
                shift
                while [ "$#" -gt 0 ]; do
                  case "$1" in
                    --project-name|--env-file|-f)
                      shift 2
                      ;;
                    *)
                      break
                      ;;
                  esac
                done
                if [ "$*" = "ps -q minecraft" ]; then
                  if [ "${FAKE_SERVER_STOPPED:-0}" -eq 1 ]; then
                    exit 0
                  fi
                  count_file="$FAKE_DOCKER_STATE_DIR/compose-ps-count"
                  count=0
                  [ ! -f "$count_file" ] || count=$(cat "$count_file")
                  count=$((count + 1))
                  printf '%s\n' "$count" > "$count_file"
                  if [ "$count" -ge "${FAKE_CONTAINER_ID_CHANGE_AT:-2}" ] && [ -n "${FAKE_CONTAINER_ID_AFTER_BACKUP:-}" ]; then
                    printf '%s\n' "$FAKE_CONTAINER_ID_AFTER_BACKUP"
                  else
                    printf '%s\n' "${FAKE_CONTAINER_ID:-test-container}"
                  fi
                  exit 0
                fi
                ;;
              inspect)
                case "${3:-}" in
                  *State.Status*)
                    count_file="$FAKE_DOCKER_STATE_DIR/health-count"
                    count=0
                    [ ! -f "$count_file" ] || count=$(cat "$count_file")
                    count=$((count + 1))
                    printf '%s\n' "$count" > "$count_file"
                    if [ "$count" -ge "${FAKE_CONTAINER_STATE_CHANGE_AT:-2}" ] && [ -n "${FAKE_CONTAINER_STATE_AFTER_BACKUP:-}" ]; then
                      printf '%s\n' "$FAKE_CONTAINER_STATE_AFTER_BACKUP"
                    else
                      printf '%s\n' "${FAKE_CONTAINER_STATE:-running|healthy}"
                    fi
                    exit 0
                    ;;
                  *State.StartedAt*)
                    count_file="$FAKE_DOCKER_STATE_DIR/started-at-count"
                    count=0
                    [ ! -f "$count_file" ] || count=$(cat "$count_file")
                    count=$((count + 1))
                    printf '%s\n' "$count" > "$count_file"
                    if [ "$count" -ge "${FAKE_STARTED_AT_CHANGE_AT:-2}" ] && [ -n "${FAKE_STARTED_AT_AFTER_BACKUP:-}" ]; then
                      printf '%s\n' "$FAKE_STARTED_AT_AFTER_BACKUP"
                    else
                      printf '%s\n' "${FAKE_STARTED_AT:-2020-01-01T00:00:00Z}"
                    fi
                    exit 0
                    ;;
                esac
                ;;
              exec)
                case "${4:-}" in
                  list)
                    count_file="$FAKE_DOCKER_STATE_DIR/rcon-list-count"
                    count=0
                    [ ! -f "$count_file" ] || count=$(cat "$count_file")
                    count=$((count + 1))
                    printf '%s\n' "$count" > "$count_file"
                    if [ "$count" -gt 1 ] && [ -n "${FAKE_RCON_OUTPUT_AFTER_BACKUP:-}" ]; then
                      printf '%s\n' "$FAKE_RCON_OUTPUT_AFTER_BACKUP"
                    else
                      printf '%s\n' "$FAKE_RCON_OUTPUT"
                    fi
                    exit "${FAKE_RCON_EXIT:-0}"
                    ;;
                  say)
                    count_file="$FAKE_DOCKER_STATE_DIR/rcon-say-count"
                    count=0
                    [ ! -f "$count_file" ] || count=$(cat "$count_file")
                    count=$((count + 1))
                    printf '%s\n' "$count" > "$count_file"
                    printf 'rcon-say:%s\n' "${5:-}" >> "$FAKE_EVENT_LOG"
                    if [ "$count" -eq "${FAKE_RCON_SAY_FAIL_AT:-0}" ]; then
                      exit 72
                    fi
                    printf 'Rcon command successful\n'
                    exit 0
                    ;;
                  *)
                    printf 'unexpected fake RCON command: %s\n' "$*" >&2
                    exit 90
                    ;;
                esac
            esac
            printf 'unexpected fake Docker command: %s\n' "$*" >&2
            exit 90
            """,
        )
        self._write_executable(
            self.operator,
            r"""
            #!/usr/bin/env bash
            set -u
            command_name=${1:-}
            printf '%s\n' "$command_name" >> "$FAKE_OPERATOR_LOG"
            printf 'operator:%s\n' "$command_name" >> "$FAKE_EVENT_LOG"
            if [ "$command_name" = "backup" ]; then
              [ "${FAKE_BACKUP_EXIT:-0}" -eq 0 ] || exit "$FAKE_BACKUP_EXIT"
              printf 'verified\n' > "$FAKE_BACKUP_PATH"
              printf '%s\n' "$FAKE_BACKUP_PATH"
            fi
            exit 0
            """,
        )

    def _run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        self.assertTrue(MAINTENANCE.is_file(), "maintenance script is missing")
        return subprocess.run(
            [str(MAINTENANCE), *arguments],
            cwd=ROOT,
            env=self.environment,
            text=True,
            capture_output=True,
            check=False,
        )

    def _operator_calls(self) -> list[str]:
        if not self.operator_log.exists():
            return []
        return self.operator_log.read_text(encoding="utf-8").splitlines()

    def _events(self) -> list[str]:
        if not self.event_log.exists():
            return []
        return self.event_log.read_text(encoding="utf-8").splitlines()

    def _countdown_events(self) -> list[str]:
        return [
            "rcon-say:AFTERLIGHT restarts daily at 5:00 AM Eastern. "
            "Restart in 15 minutes.",
            "sleep:600",
            "rcon-say:AFTERLIGHT restart in 5 minutes. "
            "Please reach a safe stopping point.",
            "sleep:240",
            "rcon-say:AFTERLIGHT restart in 1 minute. "
            "Please disconnect safely.",
            "sleep:60",
        ]

    def _final_warning_event(self) -> str:
        return (
            "rcon-say:AFTERLIGHT is restarting now. "
            "World backup verified."
        )

    def _reset_fake_state(self) -> None:
        for path in (
            self.docker_log,
            self.event_log,
            self.operator_log,
            self.backup_path,
            self.temp_path / "compose-ps-count",
            self.temp_path / "health-count",
            self.temp_path / "started-at-count",
            self.temp_path / "rcon-list-count",
            self.temp_path / "rcon-say-count",
        ):
            path.unlink(missing_ok=True)

    def _assert_scheduled_warning_failure(self, failure_index: int) -> None:
        self.environment["FAKE_RCON_SAY_FAIL_AT"] = str(failure_index)

        result = self._run("scheduled")

        self.assertNotEqual(result.returncode, 0)
        expected_calls = [] if failure_index < 4 else ["backup"]
        self.assertEqual(self._operator_calls(), expected_calls)
        self.assertIn("RCON restart warning failed", result.stderr)

    def _assert_scheduled_drift_failure(
        self,
        *,
        changed_value_variable: str,
        changed_value: str,
        change_at_variable: str,
        expected_error: str,
    ) -> None:
        self.environment[changed_value_variable] = changed_value
        for checkpoint in range(2, 6):
            with self.subTest(checkpoint=checkpoint):
                self._reset_fake_state()
                self.environment[change_at_variable] = str(checkpoint)

                result = self._run("scheduled")

                self.assertNotEqual(result.returncode, 0)
                expected_calls = ["backup"] if checkpoint == 5 else []
                self.assertEqual(self._operator_calls(), expected_calls)
                self.assertNotIn(self._final_warning_event(), self._events())
                self.assertIn(expected_error, result.stderr)

    def test_idle_healthy_server_restarts_after_verified_backup(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._operator_calls(), ["backup", "stop", "start", "status"]
        )
        self.assertTrue(self.backup_path.is_file())
        self.assertIn("Maintenance restart: OK", result.stdout)
        docker_calls = self.docker_log.read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            sum("exec test-container rcon-cli list" in call for call in docker_calls),
            2,
        )

    def test_online_players_make_maintenance_skip_without_backup(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = (
            "There are 1 of a max of 12 players online: Friend"
        )

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("players online", result.stdout)

    def test_same_container_restart_during_backup_fails_closed(self) -> None:
        self.environment["FAKE_STARTED_AT_AFTER_BACKUP"] = (
            "2020-01-02T00:00:00Z"
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertIn("start time changed during maintenance", result.stderr)

    def test_uptime_threshold_cannot_be_lowered_below_twenty_hours(self) -> None:
        self.environment["AFTERLIGHT_MIN_UPTIME_SECONDS"] = "0"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertFalse(self.docker_log.exists())
        self.assertIn("at least 72000", result.stderr)

    def test_recent_container_skips_without_backup(self) -> None:
        self.environment["FAKE_NOW_EPOCH"] = "71999"

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("uptime 71999s is below 72000s", result.stdout)

    def test_rcon_query_failure_stops_before_backup(self) -> None:
        self.environment["FAKE_RCON_EXIT"] = "1"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("RCON player query failed", result.stderr)

    def test_backup_failure_never_stops_server(self) -> None:
        self.environment["FAKE_BACKUP_EXIT"] = "7"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertIn("server was not stopped", result.stderr)

    def test_durable_quest_quarantine_rejects_all_maintenance_before_docker(self) -> None:
        self.quarantine_dir.mkdir(mode=0o700)
        marker = self.quarantine_dir / "state"
        marker.write_text("test-only-marker\n", encoding="utf-8")
        marker.chmod(0o600)

        for mode in ("idle", "scheduled"):
            with self.subTest(mode=mode):
                result = self._run(mode)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("quest update quarantine", result.stderr.lower())
                self.assertFalse(self.docker_log.exists())

    def test_health_drift_after_backup_never_stops_server(self) -> None:
        self.environment["FAKE_CONTAINER_STATE_AFTER_BACKUP"] = (
            "running|unhealthy"
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertIn("became unhealthy", result.stderr)

    def test_container_replacement_after_backup_never_stops_server(self) -> None:
        self.environment["FAKE_CONTAINER_ID_AFTER_BACKUP"] = "replacement"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertIn("container changed", result.stderr)

    def test_players_arriving_after_backup_cancel_restart(self) -> None:
        self.environment["FAKE_RCON_OUTPUT_AFTER_BACKUP"] = (
            "There are 1 of a max of 12 players online: Friend"
        )

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertIn("skipped after backup: 1 players online", result.stdout)

    def test_unparseable_player_count_fails_closed(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = "unknown response"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("Unable to parse RCON player count", result.stderr)

    def test_contradictory_player_counts_fail_closed(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = (
            "There are 0 of a max of 12 players online: \n"
            "There are 1 of a max of 12 players online: Friend"
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("Unable to parse RCON player count", result.stderr)

    def test_zero_player_count_with_listed_name_fails_closed(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = (
            "There are 0 of a max of 12 players online: Friend"
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("contradicts listed names", result.stderr)

    def test_explicit_idle_mode_preserves_idle_restart_behavior(self) -> None:
        result = self._run("idle")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._operator_calls(), ["backup", "stop", "start", "status"]
        )
        self.assertIn("Maintenance restart: OK", result.stdout)

    def test_scheduled_mode_restarts_with_online_players(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = (
            "There are 2 of a max of 12 players online: FriendOne, FriendTwo"
        )

        result = self._run("scheduled")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._operator_calls(), ["backup", "stop", "start", "status"]
        )
        self.assertIn("Scheduled restart: 2 players online", result.stdout)
        self.assertIn("Scheduled restart: OK", result.stdout)

    def test_scheduled_mode_orders_warnings_waits_backup_and_restart(self) -> None:
        result = self._run("scheduled")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            self._events(),
            self._countdown_events()
            + [
                "operator:backup",
                self._final_warning_event(),
                "operator:stop",
                "operator:start",
                "operator:status",
            ],
        )

    def test_scheduled_first_warning_failure_stops_before_backup(self) -> None:
        self._assert_scheduled_warning_failure(1)

    def test_scheduled_second_warning_failure_stops_before_backup(self) -> None:
        self._assert_scheduled_warning_failure(2)

    def test_scheduled_third_warning_failure_stops_before_backup(self) -> None:
        self._assert_scheduled_warning_failure(3)

    def test_scheduled_final_warning_failure_stops_after_backup_before_shutdown(
        self,
    ) -> None:
        self._assert_scheduled_warning_failure(4)

    def test_scheduled_container_replacement_fails_at_every_checkpoint(
        self,
    ) -> None:
        self._assert_scheduled_drift_failure(
            changed_value_variable="FAKE_CONTAINER_ID_AFTER_BACKUP",
            changed_value="replacement",
            change_at_variable="FAKE_CONTAINER_ID_CHANGE_AT",
            expected_error="container changed during maintenance",
        )

    def test_scheduled_start_time_drift_fails_at_every_checkpoint(
        self,
    ) -> None:
        self._assert_scheduled_drift_failure(
            changed_value_variable="FAKE_STARTED_AT_AFTER_BACKUP",
            changed_value="2020-01-02T00:00:00Z",
            change_at_variable="FAKE_STARTED_AT_CHANGE_AT",
            expected_error="start time changed during maintenance",
        )

    def test_scheduled_health_drift_fails_at_every_checkpoint(self) -> None:
        self._assert_scheduled_drift_failure(
            changed_value_variable="FAKE_CONTAINER_STATE_AFTER_BACKUP",
            changed_value="running|unhealthy",
            change_at_variable="FAKE_CONTAINER_STATE_CHANGE_AT",
            expected_error="became unhealthy during maintenance",
        )

    def test_scheduled_backup_failure_never_stops_server(self) -> None:
        self.environment["FAKE_BACKUP_EXIT"] = "7"

        result = self._run("scheduled")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), ["backup"])
        self.assertEqual(
            self._events(), self._countdown_events() + ["operator:backup"]
        )
        self.assertIn("server was not stopped", result.stderr)

    def test_scheduled_intentionally_stopped_server_skips(self) -> None:
        self.environment["FAKE_SERVER_STOPPED"] = "1"

        result = self._run("scheduled")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("intentionally stopped", result.stdout)

    def test_scheduled_rcon_query_failure_stops_before_warning(self) -> None:
        self.environment["FAKE_RCON_EXIT"] = "1"

        result = self._run("scheduled")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._events(), [])
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("RCON player query failed", result.stderr)

    def test_unknown_mode_and_extra_arguments_fail_before_docker(self) -> None:
        for arguments in (("unknown",), ("scheduled", "extra")):
            with self.subTest(arguments=arguments):
                result = self._run(*arguments)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.docker_log.exists())
                self.assertIn("Usage:", result.stderr)

    def test_systemd_timer_runs_warned_restart_daily_at_five_eastern(
        self,
    ) -> None:
        self.assertTrue(SERVICE.is_file(), "maintenance service is missing")
        self.assertTrue(TIMER.is_file(), "maintenance timer is missing")
        service = SERVICE.read_text(encoding="utf-8")
        timer = TIMER.read_text(encoding="utf-8")

        for expected in (
            "Description=AFTERLIGHT daily warned server restart",
            "ConditionFileIsExecutable=/opt/afterlight/server/afterlight-maintenance.sh",
            "User=afterlight",
            "SupplementaryGroups=docker",
            "WorkingDirectory=/opt/afterlight",
            "RuntimeDirectory=afterlight",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ExecStart=/opt/afterlight/server/afterlight-maintenance.sh scheduled",
            "TimeoutStartSec=infinity",
        ):
            self.assertIn(expected, service)
        self.assertNotIn("ConditionPathIsExecutable", service)
        self.assertNotIn("TimeoutStartSec=20min", service)
        self.assertNotIn("AFTERLIGHT_MIN_UPTIME_SECONDS", service)
        for expected in (
            "Description=Warn at 4:45 AM and restart AFTERLIGHT around 5:00 AM Eastern",
            "OnCalendar=*-*-* 04:45:00 America/New_York",
            "Persistent=false",
            "AccuracySec=1s",
            "Unit=afterlight-maintenance.service",
        ):
            self.assertIn(expected, timer)
        self.assertNotIn("RandomizedDelaySec", timer)
        self.assertNotIn("01,03,05,07,09,11,13,15,17,19,21,23", timer)

        verifier = (ROOT / "tools" / "verify-pack.sh").read_text(encoding="utf-8")
        self.assertIn("server/afterlight-maintenance.sh", verifier)

        docs = "\n".join(
            (
                (ROOT / "docs" / "SERVER.md").read_text(encoding="utf-8"),
                (ROOT / "server" / "README.md").read_text(encoding="utf-8"),
                (ROOT / "docs" / "HANDOFF.md").read_text(encoding="utf-8"),
            )
        )
        for expected in (
            "systemctl enable --now afterlight-maintenance.timer",
            "5:00 AM Eastern",
            "15 minutes",
            "even when players are online",
            "verified backup",
            "Pregen remains deferred",
        ):
            self.assertIn(expected, docs)


if __name__ == "__main__":
    unittest.main()
