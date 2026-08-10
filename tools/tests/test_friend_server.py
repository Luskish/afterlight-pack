from __future__ import annotations

import os
import re
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())


ROOT = Path(__file__).resolve().parents[2]
SERVER_DIR = ROOT / "server"
COMPOSE_FILE = SERVER_DIR / "docker-compose.yml"
OPERATOR = SERVER_DIR / "afterlight-server.sh"

EXPECTED_MINECRAFT_IMAGE = (
    "itzg/minecraft-server:2026.8.0-java21@sha256:"
    "b76b9298a2a60d5cf9d223e009cd0b8ad620c2080abd83f9a1fa5084fa87f9ab"
)
EXPECTED_BACKUP_IMAGE = (
    "itzg/mc-backup:2026.8.0@sha256:"
    "ae54d88d1a5dfbc185f1f94e50bb2e9b68484719013f4f21c573422dd4950f32"
)
EXPECTED_PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
REQUIRED_OPERATOR_TESTS = {
    "test_unknown_command_fails_with_usage",
    "test_doctor_rejects_relative_nested_or_symlinked_paths",
    "test_start_copies_properties_once_then_starts_both_services",
    "test_backup_requires_a_new_regular_archive",
    "test_update_backs_up_before_recreating_minecraft",
    "test_failed_update_stops_services_and_prints_exact_rollback_command",
    "test_rollback_requires_confirm_and_archive_beneath_backup_root",
    "test_rollback_renames_data_restores_and_never_invokes_rm",
}


class FriendServerTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name)
        self.data_dir = self.temp_path / "data"
        self.backup_dir = self.temp_path / "backups"
        self.secrets_dir = self.temp_path / "secrets"
        self.fake_bin = self.temp_path / "bin"
        for directory in (
            self.data_dir,
            self.backup_dir,
            self.secrets_dir,
            self.fake_bin,
        ):
            directory.mkdir()

        self.secret_file = self.secrets_dir / "rcon_password"
        self.secret_file.write_text("test-only-rcon-password\n", encoding="utf-8")
        self.secret_file.chmod(0o600)
        self.env_file = self.temp_path / "server.env"
        self.docker_log = self.temp_path / "docker.log"
        self.rm_log = self.temp_path / "rm.log"
        self._write_env()
        self._install_fakes()

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "AFTERLIGHT_ENV_FILE": str(self.env_file),
                "AFTERLIGHT_HEALTH_TIMEOUT": "0",
                "FAKE_DOCKER_LOG": str(self.docker_log),
                "FAKE_RM_LOG": str(self.rm_log),
            }
        )

    def _assert_task_file(self, path: Path) -> None:
        self.assertTrue(path.is_file(), f"missing Task 1 file: {path}")

    def _write_executable(self, name: str, source: str) -> None:
        path = self.fake_bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _install_fakes(self) -> None:
        self._write_executable(
            "docker",
            r"""
            #!/usr/bin/env bash
            set -u
            {
              first=1
              for argument in "$@"; do
                if [ "$first" -eq 0 ]; then printf '\037'; fi
                printf '%s' "$argument"
                first=0
              done
              printf '\n'
            } >> "$FAKE_DOCKER_LOG"

            [ "${1:-}" = "compose" ] || exit 91
            shift
            if [ "${1:-}" = "version" ]; then
              printf '%s\n' "${FAKE_DOCKER_VERSION_OUTPUT:-Docker Compose version v2.test}"
              exit "${FAKE_DOCKER_VERSION_EXIT:-0}"
            fi

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

            command_name="${1:-}"
            case "$command_name" in
              config)
                output="${FAKE_DOCKER_CONFIG_OUTPUT:-}"
                exit_code="${FAKE_DOCKER_CONFIG_EXIT:-0}"
                ;;
              ps)
                output="${FAKE_DOCKER_PS_OUTPUT:-[{\"Service\":\"minecraft\",\"State\":\"running\",\"Health\":\"healthy\"}]}"
                exit_code="${FAKE_DOCKER_PS_EXIT:-0}"
                ;;
              up)
                output="${FAKE_DOCKER_UP_OUTPUT:-}"
                exit_code="${FAKE_DOCKER_UP_EXIT:-0}"
                ;;
              stop)
                output="${FAKE_DOCKER_STOP_OUTPUT:-}"
                exit_code="${FAKE_DOCKER_STOP_EXIT:-0}"
                ;;
              exec)
                output="${FAKE_DOCKER_EXEC_OUTPUT:-}"
                exit_code="${FAKE_DOCKER_EXEC_EXIT:-0}"
                if [ "$exit_code" -eq 0 ] && [ -n "${FAKE_DOCKER_EXEC_CREATE_ARCHIVE:-}" ]; then
                  printf 'fake backup archive\n' > "$FAKE_DOCKER_EXEC_CREATE_ARCHIVE"
                fi
                ;;
              logs)
                output="${FAKE_DOCKER_LOGS_OUTPUT:-}"
                exit_code="${FAKE_DOCKER_LOGS_EXIT:-0}"
                ;;
              *)
                printf 'unexpected fake Docker command: %s\n' "$command_name" >&2
                exit 92
                ;;
            esac
            if [ -n "$output" ]; then printf '%s\n' "$output"; fi
            exit "$exit_code"
            """,
        )
        self._write_executable(
            "realpath",
            r"""
            #!/usr/bin/env python3
            import os
            import sys

            arguments = sys.argv[1:]
            if arguments and arguments[0] == "-m":
                arguments = arguments[1:]
            if len(arguments) != 1:
                raise SystemExit(2)
            print(os.path.realpath(os.path.abspath(arguments[0])))
            """,
        )
        self._write_executable(
            "ss",
            r"""
            #!/usr/bin/env bash
            case " $* " in
              *" -ltn "*) printf '%s' "${FAKE_SS_TCP_OUTPUT:-}" ;;
              *" -lun "*) printf '%s' "${FAKE_SS_UDP_OUTPUT:-}" ;;
              *) exit 93 ;;
            esac
            """,
        )
        self._write_executable(
            "date",
            r"""
            #!/usr/bin/env bash
            if [ "$*" = "-u +%Y%m%dT%H%M%SZ" ]; then
              printf '%s\n' "${FAKE_DATE_OUTPUT:-20260809T120000Z}"
            else
              /bin/date "$@"
            fi
            """,
        )
        self._write_executable(
            "rm",
            r"""
            #!/usr/bin/env bash
            printf '%s\n' "$*" >> "$FAKE_RM_LOG"
            exit 97
            """,
        )

    def _write_env(
        self,
        *,
        data_dir: str | Path | None = None,
        backup_dir: str | Path | None = None,
        secrets_dir: str | Path | None = None,
    ) -> None:
        data_value = self.data_dir if data_dir is None else data_dir
        backup_value = self.backup_dir if backup_dir is None else backup_dir
        secrets_value = self.secrets_dir if secrets_dir is None else secrets_dir
        self.env_file.write_text(
            "\n".join(
                (
                    f"DATA_DIR={data_value}",
                    f"BACKUP_DIR={backup_value}",
                    f"SECRETS_DIR={secrets_value}",
                    "",
                )
            ),
            encoding="utf-8",
        )

    def _run_operator(
        self, *arguments: str, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        self._assert_task_file(OPERATOR)
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            ["/bin/bash", str(OPERATOR), *arguments],
            cwd=ROOT,
            env=command_environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def _docker_calls(self) -> list[tuple[str, ...]]:
        if not self.docker_log.exists():
            return []
        return [
            tuple(line.split("\x1f"))
            for line in self.docker_log.read_text(encoding="utf-8").splitlines()
        ]

    def _compose_commands(self) -> list[tuple[str, ...]]:
        commands: list[tuple[str, ...]] = []
        for recorded_call in self._docker_calls():
            arguments = list(recorded_call)
            self.assertEqual(arguments.pop(0), "compose")
            if arguments == ["version"]:
                commands.append(("version",))
                continue
            while arguments and arguments[0] in {
                "--project-name",
                "--env-file",
                "-f",
            }:
                arguments = arguments[2:]
            commands.append(tuple(arguments))
        return commands

    def _clear_command_logs(self) -> None:
        self.docker_log.write_text("", encoding="utf-8")
        self.rm_log.write_text("", encoding="utf-8")

    def _make_backup_archive(self, relative_path: str = "nested/restore.tar.zst") -> Path:
        archive = self.backup_dir / relative_path
        archive.parent.mkdir(parents=True, exist_ok=True)
        payload = self.temp_path / "restore-payload"
        (payload / "world").mkdir(parents=True)
        (payload / "world" / "level.dat").write_text(
            "restored world\n", encoding="utf-8"
        )
        uncompressed = self.temp_path / "restore.tar"
        subprocess.run(
            ["tar", "-C", str(payload), "-cf", str(uncompressed), "."],
            check=True,
        )
        subprocess.run(
            ["zstd", "-q", "-f", str(uncompressed), "-o", str(archive)],
            check=True,
        )
        return archive

    def test_required_operator_contract_is_complete(self) -> None:
        methods = {
            name
            for name in dir(type(self))
            if name.startswith("test_")
        }
        self.assertTrue(REQUIRED_OPERATOR_TESTS.issubset(methods))

    def test_compose_contract_is_exact_and_does_not_publish_rcon(self) -> None:
        self._assert_task_file(COMPOSE_FILE)
        source = COMPOSE_FILE.read_text(encoding="utf-8")
        self.assertIn(EXPECTED_MINECRAFT_IMAGE, source)
        self.assertIn(EXPECTED_BACKUP_IMAGE, source)
        self.assertIn(EXPECTED_PACK_URL, source)
        self.assertIn('BACKUP_INTERVAL: "6h"', source)
        self.assertIn('PRUNE_BACKUPS_DAYS: "14"', source)
        self.assertEqual(source.count("restart: unless-stopped"), 2)
        self.assertNotIn("25575:", source)
        self.assertRegex(source, r"(?m)^name: afterlight$")
        self.assertRegex(source, r'(?m)^\s+- "25565:25565/tcp"$')
        self.assertRegex(source, r'(?m)^\s+- "24454:24454/udp"$')

    def test_operator_owned_inputs_match_the_approved_values(self) -> None:
        expected_env = (
            "DATA_DIR=/srv/afterlight/data\n"
            "BACKUP_DIR=/srv/afterlight/backups\n"
            "SECRETS_DIR=/etc/afterlight/secrets\n"
        )
        env_example = SERVER_DIR / ".env.example"
        properties_example = SERVER_DIR / "server.properties.example"
        excludes_file = SERVER_DIR / "backup-excludes.txt"
        for path in (env_example, properties_example, excludes_file):
            self._assert_task_file(path)
        self.assertEqual(env_example.read_text(encoding="utf-8"), expected_env)

        properties = set(
            properties_example.read_text(encoding="utf-8").splitlines()
        )
        self.assertTrue(
            {
                "online-mode=true",
                "white-list=true",
                "enforce-whitelist=true",
                "enforce-secure-profile=true",
                "max-players=12",
                "view-distance=10",
                "simulation-distance=8",
            }.issubset(properties)
        )

        exclusions = set(excludes_file.read_text(encoding="utf-8").splitlines())
        self.assertTrue(
            {
                "*.jar",
                "cache/",
                "caches/",
                "libraries/",
                "versions/",
                "logs/",
                "crash-reports/",
                "*.lock",
                "*.partial",
                "*.part",
                "server.properties",
            }.issubset(exclusions)
        )

    def test_docs_exclusions_and_tooling_cover_server_operations(self) -> None:
        paths = (
            ROOT / ".gitignore",
            ROOT / ".packwizignore",
            ROOT / "README.md",
            ROOT / "docs" / "SERVER.md",
            SERVER_DIR / "README.md",
            ROOT / "tools" / "verify-pack.sh",
        )
        for path in paths:
            self._assert_task_file(path)
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            "server/.env",
            "server/data/",
            "server/backups/",
            "server/*.rescue-*/",
        ):
            self.assertIn(pattern, gitignore.splitlines())
        packwizignore = (ROOT / ".packwizignore").read_text(encoding="utf-8")
        self.assertIn("server/**", packwizignore.splitlines())
        self.assertIn(
            "docs/SERVER.md", (ROOT / "README.md").read_text(encoding="utf-8")
        )
        self.assertIn(
            "server/afterlight-server.sh",
            (ROOT / "tools" / "verify-pack.sh").read_text(encoding="utf-8"),
        )

        docs = "\n".join(
            (
                (ROOT / "docs" / "SERVER.md").read_text(encoding="utf-8"),
                (SERVER_DIR / "README.md").read_text(encoding="utf-8"),
            )
        )
        for command in (
            "cp server/.env.example server/.env",
            "sudo install -d -m 0750 /srv/afterlight/data /srv/afterlight/backups",
            "sudo install -d -m 0700 /etc/afterlight/secrets",
            "openssl rand -base64 36 | sudo tee /etc/afterlight/secrets/rcon_password >/dev/null",
            "sudo chmod 0600 /etc/afterlight/secrets/rcon_password",
            "server/afterlight-server.sh doctor",
            "server/afterlight-server.sh start",
            "server/afterlight-server.sh backup",
            "server/afterlight-server.sh update",
            "server/afterlight-server.sh rollback /srv/afterlight/backups/afterlight-20260809-120000.tar.zst --confirm",
        ):
            self.assertIn(command, docs)
        self.assertIn("25565/tcp", docs)
        self.assertIn("24454/udp", docs)
        self.assertIn("default deny incoming", docs)
        self.assertRegex(docs, r"(?i)RCON `25575` must never be forwarded")
        self.assertRegex(docs, r"(?i)whitelist.*before.*address")

    def test_unknown_command_fails_with_usage(self) -> None:
        result = self._run_operator("not-a-command")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Usage: server/afterlight-server.sh "
            "doctor|start|stop|status|backup|update|rollback BACKUP --confirm",
            result.stderr,
        )
        self.assertEqual(self._docker_calls(), [])

    def test_doctor_rejects_relative_nested_or_symlinked_paths(self) -> None:
        path_cases: list[tuple[str, str | Path, str | Path]] = []
        path_cases.append(("relative", "relative-data", self.backup_dir))

        nested_backup = self.data_dir / "backups"
        nested_backup.mkdir()
        path_cases.append(("nested", self.data_dir, nested_backup))

        real_data = self.temp_path / "real-data"
        real_data.mkdir()
        linked_data = self.temp_path / "linked-data"
        linked_data.symlink_to(real_data, target_is_directory=True)
        path_cases.append(("symlinked", linked_data, self.backup_dir))

        for label, data_path, backup_path in path_cases:
            with self.subTest(label=label):
                self._clear_command_logs()
                self._write_env(data_dir=data_path, backup_dir=backup_path)
                result = self._run_operator("doctor")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self._docker_calls(), [])

    def test_env_assignments_are_never_executed(self) -> None:
        marker = self.temp_path / "executed"
        self._write_env(data_dir=f"$(touch {marker})")
        result = self._run_operator("doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())

        source = OPERATOR.read_text(encoding="utf-8")
        self.assertNotRegex(source, r"(?m)^\s*(?:source|\.)\s+.*\.env")
        self.assertNotRegex(source, r"(?m)(?:^|[;&|]\s*)eval(?:\s|$)")
        self.assertNotRegex(source, r"(?m)(?:^|[;&|]\s*)rm(?:\s|$)")

    def test_start_copies_properties_once_then_starts_both_services(self) -> None:
        expected_properties = SERVER_DIR / "server.properties.example"
        self._assert_task_file(expected_properties)
        first = self._run_operator("start")
        self.assertEqual(first.returncode, 0, first.stderr)
        installed_properties = self.data_dir / "server.properties"
        self.assertEqual(
            installed_properties.read_text(encoding="utf-8"),
            expected_properties.read_text(encoding="utf-8"),
        )
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("up", "-d", "minecraft", "backup"),
            ],
        )

        installed_properties.write_text("operator-owned=true\n", encoding="utf-8")
        self._clear_command_logs()
        second = self._run_operator("start")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(
            installed_properties.read_text(encoding="utf-8"),
            "operator-owned=true\n",
        )
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("up", "-d", "minecraft", "backup"),
            ],
        )

    def test_backup_requires_a_new_regular_archive(self) -> None:
        no_archive = self._run_operator("backup")
        self.assertNotEqual(no_archive.returncode, 0)
        self.assertIn("no new regular backup archive", no_archive.stderr.lower())
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("exec", "backup", "backup", "now"),
            ],
        )

        archive = self.backup_dir / "afterlight-20260809-120000.tar.zst"
        self._clear_command_logs()
        created = self._run_operator(
            "backup",
            environment={"FAKE_DOCKER_EXEC_CREATE_ARCHIVE": str(archive)},
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertEqual(created.stdout.strip(), str(archive))
        self.assertTrue(archive.is_file())

    def test_update_backs_up_before_recreating_minecraft(self) -> None:
        archive = self.backup_dir / "afterlight-20260809-120000.tar.zst"
        result = self._run_operator(
            "update",
            environment={"FAKE_DOCKER_EXEC_CREATE_ARCHIVE": str(archive)},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"Backup: {archive}", result.stdout)
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("exec", "backup", "backup", "now"),
                ("stop", "backup", "minecraft"),
                ("up", "-d", "--force-recreate", "minecraft"),
                ("ps", "--format", "json", "minecraft"),
                ("up", "-d", "backup"),
            ],
        )

    def test_failed_update_stops_services_and_prints_exact_rollback_command(self) -> None:
        archive = self.backup_dir / "afterlight-20260809-120000.tar.zst"
        result = self._run_operator(
            "update",
            environment={
                "FAKE_DOCKER_EXEC_CREATE_ARCHIVE": str(archive),
                "FAKE_DOCKER_PS_OUTPUT": (
                    '[{"Service":"minecraft","State":"running",'
                    '"Health":"starting"}]'
                ),
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "Rollback: server/afterlight-server.sh rollback "
            f"'{archive}' --confirm\n",
            result.stdout,
        )
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("exec", "backup", "backup", "now"),
                ("stop", "backup", "minecraft"),
                ("up", "-d", "--force-recreate", "minecraft"),
                ("ps", "--format", "json", "minecraft"),
                ("stop", "backup", "minecraft"),
            ],
        )

    def test_rollback_requires_confirm_and_archive_beneath_backup_root(self) -> None:
        archive = self._make_backup_archive()
        missing_confirm = self._run_operator("rollback", str(archive))
        self.assertNotEqual(missing_confirm.returncode, 0)
        self.assertIn("--confirm", missing_confirm.stderr)
        self.assertEqual(self._docker_calls(), [])

        outside_archive = self.temp_path / "outside.tar.zst"
        outside_archive.write_bytes(archive.read_bytes())
        self._clear_command_logs()
        outside = self._run_operator(
            "rollback", str(outside_archive), "--confirm"
        )
        self.assertNotEqual(outside.returncode, 0)
        self.assertIn("beneath BACKUP_DIR", outside.stderr)
        self.assertEqual(self._docker_calls(), [])

        linked_archive = self.backup_dir / "linked.tar.zst"
        linked_archive.symlink_to(archive)
        linked = self._run_operator(
            "rollback", str(linked_archive), "--confirm"
        )
        self.assertNotEqual(linked.returncode, 0)
        self.assertIn("symlink", linked.stderr.lower())
        self.assertEqual(self._docker_calls(), [])

    def test_rollback_renames_data_restores_and_never_invokes_rm(self) -> None:
        (self.data_dir / "world").mkdir()
        (self.data_dir / "world" / "level.dat").write_text(
            "current world\n", encoding="utf-8"
        )
        archive = self._make_backup_archive()
        result = self._run_operator("rollback", str(archive), "--confirm")
        self.assertEqual(result.returncode, 0, result.stderr)

        rescue = self.temp_path / "data.rescue-20260809T120000Z"
        self.assertEqual(
            (rescue / "world" / "level.dat").read_text(encoding="utf-8"),
            "current world\n",
        )
        self.assertEqual(
            (self.data_dir / "world" / "level.dat").read_text(encoding="utf-8"),
            "restored world\n",
        )
        restored_properties = self.data_dir / "server.properties"
        self.assertTrue(
            restored_properties.is_file(),
            "rollback must reseed excluded server.properties before startup",
        )
        self.assertEqual(
            restored_properties.read_text(encoding="utf-8"),
            (SERVER_DIR / "server.properties.example").read_text(encoding="utf-8"),
        )
        self.assertTrue(archive.is_file())
        self.assertFalse(self.rm_log.exists())
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("stop", "backup", "minecraft"),
                ("up", "-d", "minecraft", "backup"),
                ("ps", "--format", "json", "minecraft"),
            ],
        )

    def test_failed_rollback_preserves_archive_rescue_and_restored_tree(self) -> None:
        (self.data_dir / "world").mkdir()
        (self.data_dir / "world" / "level.dat").write_text(
            "current world\n", encoding="utf-8"
        )
        archive = self._make_backup_archive()
        result = self._run_operator(
            "rollback",
            str(archive),
            "--confirm",
            environment={
                "FAKE_DOCKER_PS_OUTPUT": (
                    '[{"Service":"minecraft","State":"running",'
                    '"Health":"starting"}]'
                )
            },
        )
        self.assertNotEqual(result.returncode, 0)
        rescue = self.temp_path / "data.rescue-20260809T120000Z"
        self.assertTrue(archive.is_file())
        self.assertTrue((rescue / "world" / "level.dat").is_file())
        self.assertTrue((self.data_dir / "world" / "level.dat").is_file())
        self.assertEqual(
            self._compose_commands(),
            [
                ("version",),
                ("config", "--quiet"),
                ("ps", "--format", "json", "minecraft"),
                ("stop", "backup", "minecraft"),
                ("up", "-d", "minecraft", "backup"),
                ("ps", "--format", "json", "minecraft"),
                ("stop", "backup", "minecraft"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
