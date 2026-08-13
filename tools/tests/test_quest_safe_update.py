from __future__ import annotations

import json
import os
import signal
import shutil
import stat
import subprocess
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROGRESS_GUARD = ROOT / "server" / "afterlight-progress-guard.py"
SAFE_UPDATE = ROOT / "server" / "afterlight-quest-safe-update.sh"
QUARANTINE_GATE = ROOT / "server" / "afterlight-quarantine-gate.sh"
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
QUARANTINE_SERVICE = (
    ROOT / "server" / "systemd" / "afterlight-quarantine-gate.service"
)
CURRENT_SHA = "2" * 40
PRIOR_SHA = "1" * 40


class ProgressGuardTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()
        self.world = self.temp_path / "world"
        self.quests = self.world / "ftbquests"
        self.teams = self.world / "ftbteams"
        self.quests.mkdir(parents=True)
        self.teams.mkdir()
        self.snapshot = self.temp_path / "snapshot"
        self.snapshot.mkdir(mode=0o700)
        self._write_baseline()

    def _write_baseline(self) -> None:
        (self.quests / "progress.snbt").write_text(
            """
            {
              completed: [1L, 2L],
              flags: {active: true, count: 2b},
              typed: [I; 1, 2, 3],
              title: "test-only-private-identity"
            }
            """,
            encoding="utf-8",
        )
        (self.teams / "team.json").write_text(
            json.dumps(
                {
                    "members": ["test-only-private-identity"],
                    "properties": {"color": "blue", "locked": False},
                }
            ),
            encoding="utf-8",
        )

    def _run(
        self,
        command: str,
        *,
        world: Path | None = None,
        snapshot: Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                "python3",
                str(PROGRESS_GUARD),
                command,
                "--world",
                str(self.world if world is None else world),
                "--output" if command == "snapshot" else "--snapshot",
                str(self.snapshot if snapshot is None else snapshot),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def _snapshot(self) -> subprocess.CompletedProcess[str]:
        result = self._run("snapshot")
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_snapshot_and_compare_canonical_complete_documents(self) -> None:
        created = self._snapshot()
        self.assertRegex(
            created.stdout,
            r"^documents=2 canonical_sha256=[0-9a-f]{64} "
            r"snapshot_sha256=[0-9a-f]{64}\n$",
        )
        self.assertNotIn("test-only-private-identity", created.stdout)
        manifest_path = self.snapshot / "progress-manifest.json"
        self.assertEqual(stat.S_IMODE(manifest_path.stat().st_mode), 0o600)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], 2)
        self.assertEqual(manifest["document_count"], 2)
        self.assertEqual(len({entry["path_sha256"] for entry in manifest["documents"]}), 2)
        self.assertNotIn("ftbquests/progress.snbt", manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(
            set(manifest["documents"][0]),
            {"path_sha256", "byte_sha256", "canonical_sha256"},
        )

        (self.quests / "progress.snbt").write_text(
            '{typed:[I;1,2,3],title:"test-only-private-identity",'
            "flags:{count:2b,active:true},completed:[1L,2L]}",
            encoding="utf-8",
        )
        (self.teams / "team.json").write_text(
            '{"properties":{"locked":false,"color":"blue"},'
            '"members":["test-only-private-identity"]}',
            encoding="utf-8",
        )
        compared = self._run("compare")
        self.assertEqual(compared.returncode, 0, compared.stderr)
        self.assertRegex(compared.stdout, r"^documents=2 canonical_sha256=[0-9a-f]{64} ")
        self.assertNotIn("test-only-private-identity", compared.stdout)

    def test_complete_value_mutation_fails_without_identity_leak(self) -> None:
        self._snapshot()
        (self.quests / "progress.snbt").write_text(
            '{completed:[1L,2L],flags:{active:true,count:3b},'
            'typed:[I;1,2,3],title:"test-only-private-identity"}',
            encoding="utf-8",
        )

        result = self._run("compare")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical progress mismatch", result.stderr.lower())
        self.assertNotIn("test-only-private-identity", result.stderr)

    def test_typed_numeric_identity_is_not_collapsed(self) -> None:
        self._snapshot()
        (self.quests / "progress.snbt").write_text(
            '{completed:[1,2L],flags:{active:true,count:2b},'
            'typed:[I;1,2,3],title:"test-only-private-identity"}',
            encoding="utf-8",
        )

        result = self._run("compare")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("canonical progress mismatch", result.stderr.lower())

    def test_missing_and_extra_documents_fail_closed(self) -> None:
        self._snapshot()
        (self.teams / "team.json").unlink()
        missing = self._run("compare")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("document inventory mismatch", missing.stderr.lower())

        (self.teams / "team.json").write_text("{}", encoding="utf-8")
        (self.teams / "extra.json").write_text("{}", encoding="utf-8")
        extra = self._run("compare")
        self.assertNotEqual(extra.returncode, 0)
        self.assertIn("document inventory mismatch", extra.stderr.lower())

    def test_permission_drift_fails_closed(self) -> None:
        self._snapshot()
        path = self.teams / "team.json"
        path.chmod(0o600)

        result = self._run("compare")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("permission, owner, group, or link mismatch", result.stderr.lower())

    def test_output_directory_must_be_empty_mode_0700(self) -> None:
        self.snapshot.chmod(0o755)
        wrong_mode = self._run("snapshot")
        self.assertNotEqual(wrong_mode.returncode, 0)
        self.assertIn("mode 0700", wrong_mode.stderr.lower())

        self.snapshot.chmod(0o700)
        (self.snapshot / "occupied").write_text("x", encoding="utf-8")
        occupied = self._run("snapshot")
        self.assertNotEqual(occupied.returncode, 0)
        self.assertIn("must be empty", occupied.stderr.lower())

    def test_snapshot_manifest_mode_drift_fails_closed(self) -> None:
        self._snapshot()
        (self.snapshot / "progress-manifest.json").chmod(0o644)

        result = self._run("compare")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("manifest mode must be 0600", result.stderr.lower())

    def test_duplicate_object_keys_are_rejected_for_snbt_and_json(self) -> None:
        cases = (
            (self.quests / "progress.snbt", "{value:1,value:2}"),
            (self.teams / "team.json", '{"value":1,"value":2}'),
        )
        for path, source in cases:
            with self.subTest(path=path.name):
                self._write_baseline()
                path.write_text(source, encoding="utf-8")
                result = self._run("snapshot")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("duplicate key", result.stderr.lower())
                self.assertNotIn(path.name, result.stderr)

    def test_malformed_documents_and_nonfinite_numbers_are_rejected(self) -> None:
        cases = (
            (self.quests / "progress.snbt", "{broken:[}"),
            (self.quests / "progress.snbt", "{value:NaN}"),
            (self.quests / "progress.snbt", "{value:NaNf}"),
            (self.quests / "progress.snbt", "{value:Infinityd}"),
            (self.teams / "team.json", '{"value": NaN}'),
            (self.teams / "team.json", '{"value": 1e999}'),
        )
        for path, source in cases:
            with self.subTest(source=source):
                shutil.rmtree(self.snapshot)
                self.snapshot.mkdir(mode=0o700)
                self._write_baseline()
                path.write_text(source, encoding="utf-8")
                result = self._run("snapshot")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("parse failure", result.stderr.lower())

    def test_links_unsafe_names_and_unsupported_formats_are_rejected(self) -> None:
        cases: list[tuple[str, callable]] = [
            (
                "link",
                lambda: (self.teams / "linked.json").symlink_to(
                    self.teams / "team.json"
                ),
            ),
            (
                "unsafe",
                lambda: (self.teams / "unsafe name.json").write_text(
                    "{}", encoding="utf-8"
                ),
            ),
            (
                "unsupported",
                lambda: (self.teams / "state.txt").write_text(
                    "{}", encoding="utf-8"
                ),
            ),
        ]
        for label, install in cases:
            with self.subTest(label=label):
                for name in ("linked.json", "unsafe name.json", "state.txt"):
                    (self.teams / name).unlink(missing_ok=True)
                self._write_baseline()
                install()
                result = self._run("snapshot")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(label, result.stderr.lower())

    def test_casefold_duplicate_manifest_identifiers_are_rejected(self) -> None:
        self._snapshot()
        manifest_path = self.snapshot / "progress-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["documents"][1]["path_sha256"] = manifest["documents"][0]["path_sha256"]
        manifest_path.write_text(
            json.dumps(manifest),
            encoding="utf-8",
        )

        result = self._run("compare")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("duplicate document identifier", result.stderr.lower())

    def test_required_progress_roots_must_be_real_directories(self) -> None:
        self.teams.rename(self.world / "real-teams")
        self.teams.symlink_to(self.world / "real-teams")

        result = self._run("snapshot")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("progress root", result.stderr.lower())


class QuestSafeUpdateTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()
        self.fake_bin = self.temp_path / "bin"
        self.data_dir = self.temp_path / "data"
        self.backup_dir = self.temp_path / "backups"
        self.secrets_dir = self.temp_path / "secrets"
        self.runtime_dir = self.temp_path / "run"
        self.snapshot_root = self.temp_path / "snapshots"
        self.quarantine_dir = self.temp_path / "quarantine"
        for directory in (
            self.fake_bin,
            self.data_dir,
            self.backup_dir,
            self.secrets_dir,
            self.runtime_dir,
            self.snapshot_root,
        ):
            directory.mkdir()
        self.runtime_dir.chmod(0o750)
        self.snapshot_root.chmod(0o700)
        self.quarantine_dir.mkdir(mode=0o750)
        world = self.data_dir / "world"
        (world / "ftbquests").mkdir(parents=True)
        (world / "ftbteams").mkdir()
        (world / "level.dat").write_text("level\n", encoding="utf-8")
        (world / "ftbquests" / "progress.snbt").write_text(
            "{completed:[1L]}", encoding="utf-8"
        )
        (world / "ftbteams" / "team.json").write_text(
            '{"members":["test-only-private-identity"]}', encoding="utf-8"
        )
        (self.data_dir / "whitelist.json").write_text(
            '[{"name":"test-only-private-identity"}]\n', encoding="utf-8"
        )
        (self.data_dir / "usercache.json").write_text(
            '[{"name":"test-only-private-identity"}]\n', encoding="utf-8"
        )
        pack_marker = self.data_dir / ".afterlight-pack-sha"
        pack_marker.write_text(
            f"{PRIOR_SHA}\n", encoding="utf-8"
        )
        pack_marker.chmod(0o600)
        (self.secrets_dir / "rcon_password").write_text(
            "test-secret\n", encoding="utf-8"
        )
        self.env_file = self.temp_path / "server.env"
        self.env_file.write_text(
            f"DATA_DIR={self.data_dir}\n"
            f"BACKUP_DIR={self.backup_dir}\n"
            f"SECRETS_DIR={self.secrets_dir}\n"
            f"AFTERLIGHT_DATA_UID={os.getuid()}\n"
            f"AFTERLIGHT_DATA_GID={os.getgid()}\n",
            encoding="utf-8",
        )
        self.state_file = self.temp_path / "docker-state.json"
        self.state_file.write_text(
            json.dumps(
                {
                    "minecraft": {"running": True, "restart": "unless-stopped"},
                    "backup": {"running": True, "restart": "unless-stopped"},
                    "start_count": 0,
                    "stop_count": 0,
                    "list_count": 0,
                    "save_count": 0,
                }
            ),
            encoding="utf-8",
        )
        self.event_log = self.temp_path / "events.log"
        self.firewall_state = self.temp_path / "firewall.json"
        self.progress_count = self.temp_path / "progress-count"
        self.tar_count = self.temp_path / "tar-count"
        self.operator = self.temp_path / "operator"
        self.progress_guard = self.temp_path / "progress-guard"
        self.safety_helper = self.temp_path / "safety-helper"
        self.accepted_receipt = self.temp_path / "gauntlet-receipt.json"
        self.accepted_receipt.write_text("{}\n", encoding="utf-8")
        self.accepted_receipt.chmod(0o600)
        self.test_contract = self.temp_path / ".afterlight-safety-test-contract"
        self.test_contract.write_text(
            "AFTERLIGHT SAFETY TEST CONTRACT v1\n",
            encoding="utf-8",
        )
        self.test_contract.chmod(0o600)
        self._install_fakes()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "AFTERLIGHT_SAFETY_TEST_ROOT": str(self.temp_path),
                "AFTERLIGHT_ENV_FILE": str(self.env_file),
                "AFTERLIGHT_RUNTIME_DIR": str(self.runtime_dir),
                "AFTERLIGHT_SNAPSHOT_ROOT": str(self.snapshot_root),
                "AFTERLIGHT_QUARANTINE_DIR": str(self.quarantine_dir),
                "AFTERLIGHT_OPERATOR": str(self.operator),
                "AFTERLIGHT_PROGRESS_GUARD": str(self.progress_guard),
                "AFTERLIGHT_SAFETY_HELPER": str(self.safety_helper),
                "AFTERLIGHT_ACCEPTED_RECEIPT": str(self.accepted_receipt),
                "AFTERLIGHT_ACCEPTED_RECEIPT_SHA256": "a" * 64,
                "AFTERLIGHT_RUNTIME_MODE": "750",
                "AFTERLIGHT_STATE_DIR_MODE": "750",
                "AFTERLIGHT_STATE_FILE_MODE": "640",
                "AFTERLIGHT_SNAPSHOT_ROOT_MODE": "700",
                "AFTERLIGHT_LOCK_OWNER_UID": str(os.getuid()),
                "AFTERLIGHT_LOCK_GROUP_GID": str(os.getgid()),
                "AFTERLIGHT_STATE_OWNER_UID": str(os.getuid()),
                "AFTERLIGHT_STATE_GROUP_GID": str(os.getgid()),
                "AFTERLIGHT_SNAPSHOT_OWNER_UID": str(os.getuid()),
                "AFTERLIGHT_SNAPSHOT_GROUP_GID": str(os.getgid()),
                "AFTERLIGHT_HEALTH_TIMEOUT": "0",
                "AFTERLIGHT_POLL_INTERVAL": "0",
                "FAKE_DATA_DIR": str(self.data_dir),
                "FAKE_DOCKER_STATE": str(self.state_file),
                "FAKE_EVENT_LOG": str(self.event_log),
                "FAKE_FIREWALL_STATE": str(self.firewall_state),
                "FAKE_GIT_SHA": CURRENT_SHA,
                "FAKE_PROGRESS_COUNT": str(self.progress_count),
                "FAKE_TAR_COUNT": str(self.tar_count),
                "FAKE_TAR_CREATE_COUNT": str(self.temp_path / "tar-create-count"),
                "FAKE_RCON_FIRST": "There are 0 of a max of 12 players online: ",
                "FAKE_RCON_SECOND": "There are 0 of a max of 12 players online: ",
            }
        )

    def _write_executable(self, path: Path, source: str) -> None:
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _install_fakes(self) -> None:
        self._write_executable(
            self.safety_helper,
            f"""
            #!/usr/bin/env bash
            set -eu
            case "${{1:-}}" in
              lock-run)
                if [ "${{FAKE_FLOCK_EXIT:-0}}" -ne 0 ]; then
                  printf '%s\n' 'ERROR: unable to acquire maintenance lock' >&2
                  exit "$FAKE_FLOCK_EXIT"
                fi
                ;;
              receipt-verify)
                if [ "${{FAKE_GIT_SHA:-{CURRENT_SHA}}}" != "{CURRENT_SHA}" ]; then
                  printf '%s\n' 'ERROR: repository HEAD does not equal the accepted release' >&2
                  exit 1
                fi
                if [ "${{FAKE_SAFETY_VERIFY_EXIT:-0}}" -eq 0 ]; then printf '%s\n' '[]'; fi
                exit "${{FAKE_SAFETY_VERIFY_EXIT:-0}}"
                ;;
              live-verify)
                exit "${{FAKE_SAFETY_VERIFY_EXIT:-0}}"
                ;;
              archive-create)
                if [ "${{FAKE_TAR_CREATE_EXIT:-0}}" -ne 0 ]; then exit "$FAKE_TAR_CREATE_EXIT"; fi
                ;;
              archive-restore)
                count_file="${{FAKE_TAR_COUNT}}"
                count=$(( $(cat "$count_file" 2>/dev/null || printf 0) + 1 ))
                printf '%s' "$count" > "$count_file"
                if [ "$count" -eq "${{FAKE_TAR_EXTRACT_FAIL_AT:-0}}" ]; then exit 77; fi
                ;;
            esac
            exec {SAFETY_HELPER} "$@"
            """,
        )
        self._write_executable(
            self.fake_bin / "git",
            """
            #!/usr/bin/env bash
            printf 'git:%s\n' "$*" >> "$FAKE_EVENT_LOG"
            if [ "$#" -eq 5 ] && [ "$1" = "-C" ] && [ "$3" = "rev-parse" ] && [ "$4" = "--verify" ]; then
              printf '%s\n' "$FAKE_GIT_SHA"
              exit 0
            fi
            exit 90
            """,
        )
        self._write_executable(
            self.fake_bin / "flock",
            """
            #!/usr/bin/env bash
            printf 'flock:%s\n' "$*" >> "$FAKE_EVENT_LOG"
            exit "${FAKE_FLOCK_EXIT:-0}"
            """,
        )
        self._write_executable(
            self.operator,
            """
            #!/usr/bin/env bash
            printf 'operator:%s\n' "$*" >> "$FAKE_EVENT_LOG"
            exit "${FAKE_OPERATOR_EXIT:-0}"
            """,
        )
        self._write_executable(
            self.progress_guard,
            r"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import stat
            import sys

            arguments = sys.argv[1:]
            command = arguments[0]
            with open(os.environ["FAKE_EVENT_LOG"], "a", encoding="utf-8") as stream:
                stream.write(f"progress:{command}\n")
            if command == "snapshot":
                output = pathlib.Path(arguments[arguments.index("--output") + 1])
                manifest = output / "progress-manifest.json"
                manifest.write_text(json.dumps({"fake": True}), encoding="utf-8")
                manifest.chmod(0o600)
                if os.environ.get("FAKE_SNAPSHOT_MODE_DRIFT") == "1":
                    drifted = pathlib.Path(
                        os.environ["FAKE_PROGRESS_COUNT"] + ".drifted"
                    )
                    if not drifted.exists():
                        drifted.write_text("1")
                        output.chmod(0o755)
            else:
                count_path = pathlib.Path(os.environ["FAKE_PROGRESS_COUNT"])
                count = int(count_path.read_text() if count_path.exists() else "0") + 1
                count_path.write_text(str(count))
                if (
                    count == 1
                    and os.environ.get("FAKE_TAMPER_ARCHIVE_ON_COMPARE") == "1"
                ):
                    snapshot = pathlib.Path(
                        arguments[arguments.index("--snapshot") + 1]
                    ).parent
                    (snapshot / "full-backup.tar.zst").write_bytes(
                        b"tampered-test-archive\n"
                    )
                    (snapshot / "full-backup.tar.gz").write_bytes(
                        b"tampered-test-archive\n"
                    )
                fail_at = int(os.environ.get("FAKE_PROGRESS_FAIL_AT", "0"))
                if count == fail_at:
                    print(
                        "ERROR: " + os.environ.get(
                            "FAKE_PROGRESS_ERROR", "canonical progress mismatch"
                        ),
                        file=sys.stderr,
                    )
                    raise SystemExit(71)
            print("documents=2 canonical_sha256=" + "a" * 64 + " snapshot_sha256=" + "b" * 64)
            """,
        )
        self._write_executable(
            self.fake_bin / "docker",
            r"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import signal
            import sys

            arguments = sys.argv[1:]
            event_log = pathlib.Path(os.environ["FAKE_EVENT_LOG"])
            with event_log.open("a", encoding="utf-8") as stream:
                stream.write("docker:" + " ".join(arguments) + "\n")
            state_path = pathlib.Path(os.environ["FAKE_DOCKER_STATE"])
            state = json.loads(state_path.read_text())

            def save():
                state_path.write_text(json.dumps(state))

            def configured_failures(name):
                return {
                    int(value)
                    for value in os.environ.get(name, "").split(",")
                    if value
                }

            if arguments[0] == "compose":
                cursor = 1
                while arguments[cursor] in {"--project-name", "--env-file", "-f"}:
                    cursor += 2
                command = arguments[cursor]
                rest = arguments[cursor + 1:]
                if command == "ps" and rest[:2] == ["-q", "minecraft"]:
                    if state["minecraft"]["running"]:
                        print("minecraft-id")
                    raise SystemExit(0)
                if command == "ps" and rest[:2] == ["-aq", "minecraft"]:
                    print("minecraft-id")
                    raise SystemExit(0)
                if command == "ps" and rest[:2] == ["-aq", "backup"]:
                    print("backup-id")
                    raise SystemExit(0)
                if command == "ps" and rest[:2] == ["-q", "backup"]:
                    if state["backup"]["running"]:
                        print("backup-id")
                    raise SystemExit(0)
                if command == "up":
                    services = [value for value in rest if not value.startswith("-") and value != "d"]
                    if "minecraft" in services:
                        state["start_count"] += 1
                        if state["start_count"] in configured_failures("FAKE_START_FAIL_AT"):
                            save()
                            raise SystemExit(72)
                        state["minecraft"]["running"] = True
                        state["pack_url"] = os.environ.get(
                            "AFTERLIGHT_PACKWIZ_URL", ""
                        )
                        if state["start_count"] == int(os.environ.get("FAKE_SIGNAL_AT_START", "0")):
                            save()
                            os.kill(os.getppid(), signal.SIGTERM)
                    if "backup" in services:
                        state["backup"]["running"] = True
                    save()
                    raise SystemExit(0)
                if command == "stop":
                    state["stop_count"] += 1
                    if state["stop_count"] in configured_failures("FAKE_STOP_FAIL_AT"):
                        save()
                        raise SystemExit(73)
                    for service in rest:
                        if service in state:
                            state[service]["running"] = False
                    if state["stop_count"] == int(os.environ.get("FAKE_WHITELIST_DRIFT_AT_STOP", "0")):
                        data = pathlib.Path(os.environ["FAKE_DATA_DIR"])
                        (data / "whitelist.json").write_text('[{"name":"changed-private-identity"}]\n')
                    save()
                    raise SystemExit(0)
                raise SystemExit(90)
            if arguments[0] == "exec":
                command = arguments[3:]
                if command == ["list"]:
                    state["list_count"] += 1
                    output = os.environ[
                        "FAKE_RCON_FIRST" if state["list_count"] == 1 else "FAKE_RCON_SECOND"
                    ]
                    save()
                    print(output)
                    raise SystemExit(int(os.environ.get("FAKE_RCON_EXIT", "0")))
                if command == ["save-all", "flush"]:
                    state["save_count"] += 1
                    save()
                    raise SystemExit(int(os.environ.get("FAKE_SAVE_EXIT", "0")))
                raise SystemExit(90)
            if arguments[0] == "inspect":
                format_value = arguments[arguments.index("--format") + 1]
                container = arguments[-1]
                service = "minecraft" if container in {"minecraft-id", "afterlight-minecraft-1"} else "backup"
                if "RestartPolicy" in format_value:
                    print(state[service]["restart"])
                elif "State.Status" in format_value and "Health" in format_value:
                    print("running|healthy" if state[service]["running"] else "exited|none")
                elif "State.Status" in format_value:
                    print("running" if state[service]["running"] else "exited")
                elif "Config.Env" in format_value:
                    active_url = state.get("pack_url", "")
                    if (
                        os.environ.get("FAKE_PACK_URL_MISMATCH") == "1"
                        and ("/" + "2" * 40 + "/") in active_url
                    ):
                        print("PACKWIZ_URL=https://example.invalid/wrong/pack.toml")
                    else:
                        print("PACKWIZ_URL=" + active_url)
                raise SystemExit(0)
            if arguments[:2] in (["update", "--restart=no"], ["update", "--restart=unless-stopped"]):
                policy = "no" if arguments[1] == "--restart=no" else "unless-stopped"
                for container in arguments[2:]:
                    service = "minecraft" if container in {"minecraft-id", "afterlight-minecraft-1"} else "backup"
                    state[service]["restart"] = policy
                save()
                raise SystemExit(0)
            if arguments[0] == "stop":
                for container in arguments[1:]:
                    service = "minecraft" if container in {"minecraft-id", "afterlight-minecraft-1"} else "backup"
                    state[service]["running"] = False
                save()
                raise SystemExit(0)
            raise SystemExit(90)
            """,
        )
        self._write_executable(
            self.fake_bin / "iptables",
            r"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import sys

            arguments = sys.argv[1:]
            with open(os.environ["FAKE_EVENT_LOG"], "a", encoding="utf-8") as stream:
                stream.write("iptables:" + " ".join(arguments) + "\n")
            if arguments[:3] == ["-w", "-n", "-L"]:
                raise SystemExit(int(os.environ.get("FAKE_CHAIN_EXIT", "0")))
            operation_index = 1 if arguments and arguments[0] == "-w" else 0
            operation = arguments[operation_index]
            rule = arguments[operation_index + 1:]
            state_path = pathlib.Path(os.environ["FAKE_FIREWALL_STATE"])
            state = json.loads(state_path.read_text()) if state_path.exists() else []
            if operation == "-I":
                if os.environ.get("FAKE_IPTABLES_INSERT_DRIFT") == "1":
                    state = rule[:1] + rule[2:]
                    state_path.write_text(json.dumps(state))
                    raise SystemExit(74)
                if int(os.environ.get("FAKE_IPTABLES_INSERT_EXIT", "0")):
                    raise SystemExit(74)
                state = rule[:1] + rule[2:]
                state_path.write_text(json.dumps(state))
                raise SystemExit(0)
            if operation == "-C":
                if int(os.environ.get("FAKE_IPTABLES_CHECK_EXIT", "0")):
                    raise SystemExit(75)
                raise SystemExit(0 if state == rule else 1)
            if operation == "-D":
                if int(os.environ.get("FAKE_IPTABLES_DELETE_EXIT", "0")):
                    raise SystemExit(76)
                if state != rule:
                    raise SystemExit(1)
                if os.environ.get("FAKE_IPTABLES_DELETE_DRIFT") != "1":
                    state_path.unlink(missing_ok=True)
                raise SystemExit(0)
            raise SystemExit(90)
            """,
        )
        self._write_executable(
            self.fake_bin / "tar",
            r"""
            #!/usr/bin/env python3
            import os
            import pathlib
            import shutil
            import sys

            arguments = sys.argv[1:]
            with open(os.environ["FAKE_EVENT_LOG"], "a", encoding="utf-8") as stream:
                stream.write("tar:" + " ".join(arguments) + "\n")
            archive = pathlib.Path(arguments[arguments.index("--file") + 1])
            payload = pathlib.Path(str(archive) + ".payload")
            if "--create" in arguments:
                create_count_path = pathlib.Path(os.environ["FAKE_TAR_CREATE_COUNT"])
                create_count = int(create_count_path.read_text() if create_count_path.exists() else "0") + 1
                create_count_path.write_text(str(create_count))
                if payload.exists():
                    shutil.rmtree(payload)
                shutil.copytree(os.environ["FAKE_DATA_DIR"], payload, symlinks=True)
                if create_count == int(os.environ.get("FAKE_TAR_SYMLINK_AT_CREATE", "0")):
                    (payload / "linked-state").symlink_to("world")
                archive.write_bytes(b"test-only-authenticated-archive\n")
                raise SystemExit(int(os.environ.get("FAKE_TAR_CREATE_EXIT", "0")))
            count_path = pathlib.Path(os.environ["FAKE_TAR_COUNT"])
            count = int(count_path.read_text() if count_path.exists() else "0") + 1
            count_path.write_text(str(count))
            if count == int(os.environ.get("FAKE_TAR_EXTRACT_FAIL_AT", "0")):
                raise SystemExit(77)
            destination = pathlib.Path(arguments[arguments.index("--directory") + 1])
            shutil.copytree(payload, destination, dirs_exist_ok=True, symlinks=True)
            """,
        )
        self._write_executable(
            self.fake_bin / "sha256sum",
            r"""
            #!/usr/bin/env python3
            import hashlib
            import pathlib
            import sys
            path = pathlib.Path(sys.argv[1])
            print(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + str(path))
            """,
        )

    def _run(
        self,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            ["/bin/bash", str(SAFE_UPDATE), *arguments],
            cwd=ROOT,
            env=command_environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def _state(self) -> dict[str, object]:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def _events(self) -> list[str]:
        if not self.event_log.exists():
            return []
        return self.event_log.read_text(encoding="utf-8").splitlines()

    def test_success_requires_exact_sha_two_zero_checks_and_two_starts(self) -> None:
        result = self._run(
            CURRENT_SHA,
            "--confirm",
            environment={"AFTERLIGHT_PROGRESS_GUARD": str(PROGRESS_GUARD)},
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        state = self._state()
        self.assertEqual(state["list_count"], 2)
        self.assertEqual(state["save_count"], 1)
        self.assertEqual(state["start_count"], 2)
        self.assertTrue(state["minecraft"]["running"])
        self.assertTrue(state["backup"]["running"])
        self.assertFalse(self.firewall_state.exists())
        self.assertEqual(
            (self.data_dir / ".afterlight-pack-sha").read_text(encoding="utf-8"),
            f"{CURRENT_SHA}\n",
        )
        snapshots = list(self.snapshot_root.iterdir())
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(stat.S_IMODE(snapshots[0].stat().st_mode), 0o700)
        self.assertTrue(
            (snapshots[0] / "progress" / "progress-manifest.json").is_file()
        )
        self.assertTrue((snapshots[0] / "full-backup.tar.gz").is_file())
        self.assertTrue((snapshots[0] / "backup-preflight.json").is_file())
        self.assertIn("QUEST-SAFE UPDATE: OK", result.stdout)
        self.assertNotIn("test-only-private-identity", result.stdout + result.stderr)
        events = self._events()
        save_event = "docker:exec minecraft-id rcon-cli save-all flush"
        stop_event = (
            "docker:compose --project-name afterlight --env-file "
            f"{self.env_file} -f {ROOT / 'server' / 'docker-compose.yml'} "
            f"-f {ROOT / 'server' / 'docker-compose.transaction.yml'} "
            "stop backup minecraft"
        )
        self.assertLess(events.index(save_event), events.index(stop_event))
        self.assertEqual(sum(event.startswith("iptables:-w -I DOCKER-USER") for event in events), 1)

    def test_arguments_lock_operator_and_repository_sha_fail_before_gate(self) -> None:
        cases = (
            ((CURRENT_SHA,), {}, "--confirm"),
            (("short", "--confirm"), {}, "40 lowercase"),
            ((CURRENT_SHA, "--confirm"), {"FAKE_FLOCK_EXIT": "1"}, "maintenance lock"),
            ((CURRENT_SHA, "--confirm"), {"FAKE_OPERATOR_EXIT": "9"}, "operator preflight"),
            ((CURRENT_SHA, "--confirm"), {"FAKE_GIT_SHA": PRIOR_SHA}, "repository head"),
        )
        for arguments, environment, expected in cases:
            with self.subTest(expected=expected):
                self.event_log.unlink(missing_ok=True)
                result = self._run(*arguments, environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr.lower())
                self.assertFalse(self.firewall_state.exists())

    def test_player_queries_fail_closed_at_both_checks(self) -> None:
        cases = (
            ({"FAKE_RCON_FIRST": "unknown"}, "parse", False),
            ({"FAKE_RCON_FIRST": "There are 1 of a max of 12 players online: Friend"}, "players online", False),
            ({"FAKE_RCON_SECOND": "There are 1 of a max of 12 players online: Friend"}, "players online", True),
        )
        for environment, expected, quarantined in cases:
            with self.subTest(environment=environment):
                result = self._run(CURRENT_SHA, "--confirm", environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr.lower())
                self.assertEqual(self._state()["start_count"], 0)
                self.assertEqual(
                    (self.data_dir / ".afterlight-pack-sha").read_text(encoding="utf-8"),
                    f"{PRIOR_SHA}\n",
                )
                self.assertEqual(self.firewall_state.exists(), quarantined)
                self.assertEqual((self.quarantine_dir / "state").exists(), quarantined)
                self.setUp()

    def test_firewall_insert_check_and_delete_failures_never_open_candidate(self) -> None:
        cases = (
            ({"FAKE_IPTABLES_INSERT_EXIT": "1"}, 0),
            ({"FAKE_IPTABLES_CHECK_EXIT": "1"}, 0),
            ({"FAKE_IPTABLES_DELETE_EXIT": "1", "FAKE_START_FAIL_AT": "1,2"}, 2),
            ({"FAKE_IPTABLES_DELETE_DRIFT": "1", "FAKE_START_FAIL_AT": "1,2"}, 2),
        )
        for environment, minimum_starts in cases:
            with self.subTest(environment=environment):
                result = self._run(CURRENT_SHA, "--confirm", environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertGreaterEqual(self._state()["start_count"], minimum_starts)
                self.setUp()

    def test_ambiguous_firewall_insert_is_detected_and_cleaned_exactly(self) -> None:
        result = self._run(
            CURRENT_SHA,
            "--confirm",
            environment={"FAKE_IPTABLES_INSERT_DRIFT": "1"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.firewall_state.exists())
        self.assertFalse(self._state()["minecraft"]["running"])
        self.assertTrue((self.quarantine_dir / "state").is_file())

    def test_save_archive_mode_shutdown_and_candidate_failures_roll_back(self) -> None:
        cases = (
            ({"FAKE_SAVE_EXIT": "1"}, "save-all", True),
            ({"FAKE_TAR_CREATE_EXIT": "77"}, "backup authentication", True),
            ({"FAKE_SNAPSHOT_MODE_DRIFT": "1"}, "mode 0700", True),
            ({"FAKE_STOP_FAIL_AT": "1"}, "clean shutdown", True),
            ({"FAKE_START_FAIL_AT": "1"}, "candidate start", False),
        )
        for environment, expected, quarantined in cases:
            with self.subTest(expected=expected):
                harness = QuestSafeUpdateTests(methodName="runTest")
                harness.setUp()
                try:
                    result = harness._run(CURRENT_SHA, "--confirm", environment=environment)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(expected, result.stderr.lower())
                    self.assertEqual(harness.firewall_state.exists(), quarantined)
                    self.assertEqual(harness._state()["minecraft"]["running"], not quarantined)
                    self.assertEqual((harness.quarantine_dir / "state").exists(), quarantined)
                    self.assertEqual(
                        (harness.data_dir / ".afterlight-pack-sha").read_text(encoding="utf-8"),
                        f"{PRIOR_SHA}\n",
                    )
                finally:
                    harness.doCleanups()

    def test_container_packwiz_url_mismatch_rolls_back(self) -> None:
        result = self._run(
            CURRENT_SHA,
            "--confirm",
            environment={"FAKE_PACK_URL_MISMATCH": "1"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted release", result.stderr.lower())
        self.assertTrue(self._state()["minecraft"]["running"])
        self.assertFalse(self.firewall_state.exists())

    def test_every_progress_mismatch_class_rolls_back_prior_release(self) -> None:
        for mismatch in (
            "document inventory mismatch",
            "canonical progress mismatch",
            "permission mismatch",
        ):
            with self.subTest(mismatch=mismatch):
                result = self._run(
                    CURRENT_SHA,
                    "--confirm",
                    environment={
                        "FAKE_PROGRESS_FAIL_AT": "1",
                        "FAKE_PROGRESS_ERROR": mismatch,
                    },
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(mismatch, result.stderr.lower())
                self.assertEqual(self._state()["start_count"], 3)
                self.assertTrue(self._state()["minecraft"]["running"])
                self.assertFalse(self.firewall_state.exists())
                self.assertNotIn(
                    "changed-private-identity",
                    (self.data_dir / "whitelist.json").read_text(encoding="utf-8"),
                )
                self.setUp()

    def test_second_start_and_whitelist_drift_roll_back(self) -> None:
        cases = (
            ({"FAKE_START_FAIL_AT": "2"}, "second candidate start"),
            ({"FAKE_WHITELIST_DRIFT_AT_STOP": "2"}, "whitelist integrity"),
        )
        for environment, expected in cases:
            with self.subTest(expected=expected):
                result = self._run(CURRENT_SHA, "--confirm", environment=environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected, result.stderr.lower())
                self.assertTrue(self._state()["minecraft"]["running"])
                self.assertFalse(self.firewall_state.exists())
                self.setUp()

    def test_signal_interruption_rolls_back_and_cleans_owned_rule(self) -> None:
        docker = self.fake_bin / "docker"
        source = docker.read_text(encoding="utf-8")
        source = source.replace("import sys\n", "import sys\nimport time\n")
        source = source.replace(
            "os.kill(os.getppid(), signal.SIGTERM)",
            "time.sleep(120)",
        )
        docker.write_text(source, encoding="utf-8")
        docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
        environment = self.environment | {"FAKE_SIGNAL_AT_START": "1"}
        process = subprocess.Popen(
            ["/bin/bash", str(SAFE_UPDATE), CURRENT_SHA, "--confirm"],
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if self._state()["start_count"] >= 1:
                break
            time.sleep(0.02)
        self.assertGreaterEqual(self._state()["start_count"], 1)
        process.send_signal(signal.SIGTERM)
        stdout, stderr = process.communicate(timeout=20)

        self.assertNotEqual(process.returncode, 0, stdout)
        self.assertIn("interrupted", stderr.lower())
        self.assertTrue(self._state()["minecraft"]["running"])
        self.assertFalse(
            self.firewall_state.exists(),
            f"stdout={stdout!r} stderr={stderr!r} state={self._state()!r} "
            f"authority={(self.quarantine_dir / 'state').exists()}",
        )

    def test_rollback_failure_disables_restarts_and_writes_durable_quarantine(self) -> None:
        result = self._run(
            CURRENT_SHA,
            "--confirm",
            environment={"FAKE_START_FAIL_AT": "1,2"},
        )

        self.assertNotEqual(result.returncode, 0)
        state = self._state()
        for service in ("minecraft", "backup"):
            self.assertFalse(state[service]["running"])
            self.assertEqual(state[service]["restart"], "no")
        marker = self.quarantine_dir / "state"
        self.assertTrue(marker.is_file())
        self.assertEqual(stat.S_IMODE(marker.stat().st_mode), 0o640)
        self.assertEqual(stat.S_IMODE(self.quarantine_dir.stat().st_mode), 0o750)
        self.assertTrue(self.firewall_state.exists())
        self.assertNotIn("test-only-private-identity", marker.read_text(encoding="utf-8"))
        self.assertIn("ROLLBACK FAILED: QUARANTINED", result.stderr)

    def test_rollback_reauthenticates_backup_before_restore(self) -> None:
        result = self._run(
            CURRENT_SHA,
            "--confirm",
            environment={
                "FAKE_PROGRESS_FAIL_AT": "1",
                "FAKE_TAMPER_ARCHIVE_ON_COMPARE": "1",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        state = self._state()
        for service in ("minecraft", "backup"):
            self.assertFalse(state[service]["running"])
            self.assertEqual(state[service]["restart"], "no")
        self.assertTrue((self.quarantine_dir / "state").is_file())
        self.assertTrue(self.firewall_state.exists())


class QuarantineGateTests(unittest.TestCase):
    _write_executable = QuestSafeUpdateTests._write_executable
    _install_fakes = QuestSafeUpdateTests._install_fakes
    _state = QuestSafeUpdateTests._state
    _events = QuestSafeUpdateTests._events

    def setUp(self) -> None:
        QuestSafeUpdateTests.setUp(self)
        self.recorded_snapshot = self.snapshot_root / "recorded"
        self.recorded_snapshot.mkdir(mode=0o700)
        self.marker = self.quarantine_dir / "state"
        common = [
            "--state-dir", str(self.quarantine_dir),
            "--state-dir-mode", "750",
            "--state-file-mode", "640",
            "--owner-uid", str(os.getuid()),
            "--group-gid", str(os.getgid()),
            "--snapshot-owner-uid", str(os.getuid()),
            "--snapshot-group-gid", str(os.getgid()),
                "--snapshot-root-mode", "700",
                "--canonical-snapshot-root", str(self.snapshot_root),
        ]
        created = subprocess.run(
            [
                str(self.safety_helper), "authority-create", *common,
                "--expected-sha", CURRENT_SHA,
                "--prior-sha", PRIOR_SHA,
                "--snapshot-root", str(self.snapshot_root),
                "--receipt-sha256", "a" * 64,
            ],
            cwd=ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        self.transaction_id = created.stdout.strip()
        updated = subprocess.run(
            [
                str(self.safety_helper), "authority-update", *common,
                "--transaction-id", self.transaction_id,
                "--snapshot-dir", str(self.recorded_snapshot),
                "--phase", "candidate-started",
            ],
            cwd=ROOT,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(updated.returncode, 0, updated.stderr)
        state = self._state()
        for service in ("minecraft", "backup"):
            state[service]["running"] = False
            state[service]["restart"] = "no"
        self.state_file.write_text(json.dumps(state), encoding="utf-8")
        self.environment.update(
            {
                "AFTERLIGHT_QUARANTINE_GATE_ATTEMPTS": "2",
                "AFTERLIGHT_QUARANTINE_GATE_INTERVAL": "0",
            }
        )

    def _run_gate(
        self, environment: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            ["/bin/bash", str(QUARANTINE_GATE)],
            cwd=ROOT,
            env=command_environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_reboot_gate_reconstructs_exact_rule_and_is_idempotent(self) -> None:
        first = self._run_gate()
        second = self._run_gate()

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        state = self._state()
        for service in ("minecraft", "backup"):
            self.assertFalse(state[service]["running"])
            self.assertEqual(state[service]["restart"], "no")
        rule = json.loads(self.firewall_state.read_text(encoding="utf-8"))
        self.assertEqual(rule[0], "DOCKER-USER")
        self.assertEqual(
            rule[rule.index("--comment") + 1],
            f"afterlight-quest-update-{CURRENT_SHA}-{self.transaction_id}",
        )
        inserts = [
            event
            for event in self._events()
            if event.startswith("iptables:-w -I DOCKER-USER")
        ]
        self.assertEqual(len(inserts), 1)
        self.assertNotIn("test-only-private-identity", first.stdout + first.stderr)

    def test_chain_absent_fails_bounded_with_restarts_disabled(self) -> None:
        result = self._run_gate({"FAKE_CHAIN_EXIT": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DOCKER-USER", result.stderr)
        state = self._state()
        for service in ("minecraft", "backup"):
            self.assertFalse(state[service]["running"])
            self.assertEqual(state[service]["restart"], "no")
        chain_checks = [
            event
            for event in self._events()
            if event == "iptables:-w -n -L DOCKER-USER"
        ]
        self.assertEqual(len(chain_checks), 2)
        self.assertFalse(self.firewall_state.exists())

    def test_malformed_or_mode_drifted_marker_fails_with_containers_disabled(self) -> None:
        cases = (
            ("malformed", 0o640),
            (
                "schema=1\ncomment=afterlight-quest-update-bad-1\n"
                f"expected_sha={CURRENT_SHA}\n"
                f"snapshot_dir={self.recorded_snapshot}\n",
                0o640,
            ),
            (
                "schema=1\n"
                f"comment=afterlight-quest-update-{CURRENT_SHA}-1234\n"
                f"expected_sha={CURRENT_SHA}\n"
                f"snapshot_dir={self.recorded_snapshot}\n",
                0o644,
            ),
        )
        for source, mode in cases:
            with self.subTest(mode=oct(mode), source=source[:12]):
                self.marker.write_text(source, encoding="utf-8")
                self.marker.chmod(mode)
                result = self._run_gate()
                self.assertNotEqual(result.returncode, 0)
                state = self._state()
                for service in ("minecraft", "backup"):
                    self.assertFalse(state[service]["running"])
                    self.assertEqual(state[service]["restart"], "no")

    def test_no_marker_is_a_noop(self) -> None:
        self.marker.unlink()
        state = self._state()
        state["minecraft"]["running"] = True
        state["minecraft"]["restart"] = "unless-stopped"
        self.state_file.write_text(json.dumps(state), encoding="utf-8")

        result = self._run_gate()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self._state()["minecraft"]["running"])
        self.assertFalse(self.firewall_state.exists())

    def test_systemd_gate_is_ordered_after_docker_and_before_maintenance(self) -> None:
        self.assertTrue(QUARANTINE_SERVICE.is_file())
        source = QUARANTINE_SERVICE.read_text(encoding="utf-8")
        for expected in (
            "Requires=docker.service",
            "After=docker.service",
            "Before=afterlight-maintenance.service",
            "ExecStart=/opt/afterlight/server/afterlight-quarantine-gate.sh",
            "Type=oneshot",
            "RemainAfterExit=yes",
            "WantedBy=multi-user.target",
        ):
            self.assertIn(expected, source)
        self.assertNotIn("Restart=", source)


if __name__ == "__main__":
    unittest.main()
