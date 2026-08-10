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
        self.operator_log = self.temp_path / "operator.log"
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
                "AFTERLIGHT_MIN_UPTIME_SECONDS": "0",
                "FAKE_BACKUP_PATH": str(self.backup_path),
                "FAKE_DOCKER_LOG": str(self.docker_log),
                "FAKE_OPERATOR_LOG": str(self.operator_log),
                "FAKE_RCON_OUTPUT": (
                    "There are 0 of a max of 12 players online: "
                ),
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
              printf '1000000\n'
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
                  printf '%s\n' "${FAKE_CONTAINER_ID:-test-container}"
                  exit 0
                fi
                ;;
              inspect)
                case "${3:-}" in
                  *State.Status*)
                    printf '%s\n' "${FAKE_CONTAINER_STATE:-running|healthy}"
                    exit 0
                    ;;
                  *State.StartedAt*)
                    printf '%s\n' "${FAKE_STARTED_AT:-2020-01-01T00:00:00Z}"
                    exit 0
                    ;;
                esac
                ;;
              exec)
                printf '%s\n' "$FAKE_RCON_OUTPUT"
                exit "${FAKE_RCON_EXIT:-0}"
                ;;
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
            if [ "$command_name" = "backup" ]; then
              [ "${FAKE_BACKUP_EXIT:-0}" -eq 0 ] || exit "$FAKE_BACKUP_EXIT"
              printf 'verified\n' > "$FAKE_BACKUP_PATH"
              printf '%s\n' "$FAKE_BACKUP_PATH"
            fi
            exit 0
            """,
        )

    def _run(self) -> subprocess.CompletedProcess[str]:
        self.assertTrue(MAINTENANCE.is_file(), "maintenance script is missing")
        return subprocess.run(
            [str(MAINTENANCE)],
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

    def test_unparseable_player_count_fails_closed(self) -> None:
        self.environment["FAKE_RCON_OUTPUT"] = "unknown response"

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self._operator_calls(), [])
        self.assertIn("Unable to parse RCON player count", result.stderr)

    def test_systemd_timer_runs_hardened_idle_checks_every_two_hours(self) -> None:
        self.assertTrue(SERVICE.is_file(), "maintenance service is missing")
        self.assertTrue(TIMER.is_file(), "maintenance timer is missing")
        service = SERVICE.read_text(encoding="utf-8")
        timer = TIMER.read_text(encoding="utf-8")

        for expected in (
            "User=afterlight",
            "SupplementaryGroups=docker",
            "WorkingDirectory=/opt/afterlight",
            "RuntimeDirectory=afterlight",
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "AFTERLIGHT_MIN_UPTIME_SECONDS=72000",
        ):
            self.assertIn(expected, service)
        for expected in (
            "Persistent=true",
            "RandomizedDelaySec=5m",
            "01,03,05,07,09,11,13,15,17,19,21,23:00:00 UTC",
        ):
            self.assertIn(expected, timer)

        verifier = (ROOT / "tools" / "verify-pack.sh").read_text(encoding="utf-8")
        self.assertIn("server/afterlight-maintenance.sh", verifier)

        docs = "\n".join(
            (
                (ROOT / "docs" / "SERVER.md").read_text(encoding="utf-8"),
                (ROOT / "server" / "README.md").read_text(encoding="utf-8"),
            )
        )
        for expected in (
            "systemctl enable --now afterlight-maintenance.timer",
            "AFTERLIGHT_MIN_UPTIME_SECONDS=72000",
            "zero players",
            "verified backup",
        ):
            self.assertIn(expected, docs)


if __name__ == "__main__":
    unittest.main()
