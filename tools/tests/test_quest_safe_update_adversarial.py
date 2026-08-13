from __future__ import annotations

import fcntl
import hashlib
import http.server
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

from tools.tests import test_friend_server as friend_server_tests
from tools.tests import test_quest_safe_update as quest_safe_tests


ROOT = Path(__file__).resolve().parents[2]
CURRENT_SHA = quest_safe_tests.CURRENT_SHA
PRIOR_SHA = quest_safe_tests.PRIOR_SHA
PROGRESS_GUARD = quest_safe_tests.PROGRESS_GUARD
QUARANTINE_GATE = quest_safe_tests.QUARANTINE_GATE
QUARANTINE_SERVICE = quest_safe_tests.QUARANTINE_SERVICE
INGRESS_SERVICE = ROOT / "server" / "systemd" / "afterlight-ingress-boot-gate.service"
INGRESS_GATE = ROOT / "server" / "afterlight-ingress-boot-gate.sh"
SAFE_UPDATE = ROOT / "server" / "afterlight-quest-safe-update.sh"
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
RECOVERY_HELPER = ROOT / "server" / "afterlight-quarantine-recover.sh"
SERVER_README = ROOT / "server" / "README.md"


class ReviewRegressionTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()

    def _quest_harness(self) -> quest_safe_tests.QuestSafeUpdateTests:
        harness = quest_safe_tests.QuestSafeUpdateTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        return harness

    def _friend_harness(self) -> friend_server_tests.FriendServerTests:
        harness = friend_server_tests.FriendServerTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        return harness

    def _git(self, repository: Path, *arguments: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def test_c1_pending_authority_is_visible_before_firewall_mutation(self) -> None:
        harness = self._quest_harness()
        observation = harness.temp_path / "authority-observed"
        iptables = harness.fake_bin / "iptables"
        original = iptables.read_text(encoding="utf-8")
        needle = 'if operation == "-I":\n'
        replacement = (
            'if operation == "-I":\n'
            '    authority = pathlib.Path(os.environ["AFTERLIGHT_QUARANTINE_DIR"]) / "state"\n'
            '    pathlib.Path(os.environ["FAKE_AUTHORITY_OBSERVATION"]).write_text('
            '"present" if authority.is_file() else "absent")\n'
        )
        self.assertIn(needle, original)
        iptables.write_text(original.replace(needle, replacement), encoding="utf-8")
        iptables.chmod(iptabless_mode := iptables.stat().st_mode | stat.S_IXUSR)
        self.assertTrue(iptabless_mode & stat.S_IXUSR)

        result = harness._run(
            CURRENT_SHA,
            "--confirm",
            environment={
                "FAKE_AUTHORITY_OBSERVATION": str(observation),
                "FAKE_IPTABLES_INSERT_EXIT": "1",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(observation.read_text(encoding="utf-8"), "present")

    def test_c1_sigkill_leaves_boot_discoverable_authority(self) -> None:
        harness = self._quest_harness()
        docker = harness.fake_bin / "docker"
        source = docker.read_text(encoding="utf-8")
        old = "os.kill(os.getppid(), signal.SIGTERM)"
        self.assertIn(old, source)
        old_line = next(line for line in source.splitlines() if old in line)
        indent = old_line[: len(old_line) - len(old_line.lstrip())]
        replacement = "\n".join(
            [
                f"{indent}helper_pid = os.getppid()",
                f"{indent}shell_pid = int(subprocess.check_output("
                "['ps', '-o', 'ppid=', '-p', str(helper_pid)], text=True).strip())",
                f"{indent}os.kill(shell_pid, signal.SIGKILL)",
            ]
        )
        docker.write_text(
            source.replace(
                "import sys\n",
                "import subprocess\nimport sys\n",
            ).replace(old_line, replacement),
            encoding="utf-8",
        )
        docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
        environment = harness.environment | {"FAKE_SIGNAL_AT_START": "1"}
        process = subprocess.run(
            ["/bin/bash", str(SAFE_UPDATE), CURRENT_SHA, "--confirm"],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            start_new_session=True,
        )

        self.assertNotEqual(process.returncode, 0)
        self.assertTrue(
            (harness.quarantine_dir / "state").is_file(),
            f"stdout={process.stdout!r} stderr={process.stderr!r} events={harness._events()!r}",
        )

    def test_c2_boot_gate_reconciles_each_container_after_partial_failure(self) -> None:
        harness = self._quest_harness()
        marker = harness.quarantine_dir / "state"
        common = [
            "--state-dir", str(harness.quarantine_dir),
            "--state-dir-mode", "750",
            "--state-file-mode", "640",
            "--owner-uid", str(os.getuid()),
            "--group-gid", str(os.getgid()),
            "--snapshot-owner-uid", str(os.getuid()),
            "--snapshot-group-gid", str(os.getgid()),
            "--snapshot-root-mode", "700",
            "--canonical-snapshot-root", str(harness.snapshot_root),
        ]
        created = subprocess.run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-create",
                *common,
                "--expected-sha",
                CURRENT_SHA,
                "--prior-sha",
                PRIOR_SHA,
                "--snapshot-root",
                str(harness.snapshot_root),
                "--receipt-sha256",
                "a" * 64,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        transaction_id = created.stdout.strip()
        updated = subprocess.run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-update",
                *common,
                "--transaction-id",
                transaction_id,
                "--phase",
                "candidate-started",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(updated.returncode, 0, updated.stderr)
        docker = harness.fake_bin / "docker"
        harness._write_executable(
            docker,
            r"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import sys

            arguments = sys.argv[1:]
            state_path = pathlib.Path(os.environ["FAKE_DOCKER_STATE"])
            state = json.loads(state_path.read_text())

            def service(container):
                return "minecraft" if "minecraft" in container else "backup"

            if arguments[0] == "compose":
                cursor = 1
                while arguments[cursor] in {"--project-name", "--env-file", "-f"}:
                    cursor += 2
                if arguments[cursor:cursor + 3] == ["ps", "-aq", "minecraft"]:
                    print("minecraft-id")
                    raise SystemExit(0)
                if arguments[cursor:cursor + 3] == ["ps", "-aq", "backup"]:
                    print("backup-id")
                    raise SystemExit(0)
            if arguments[:2] == ["update", "--restart=no"]:
                target = service(arguments[2])
                failure_marker = pathlib.Path(os.environ["FAKE_PARTIAL_FAILURE"])
                if target == "minecraft" and not failure_marker.exists():
                    failure_marker.write_text("failed-once")
                    raise SystemExit(81)
                state[target]["restart"] = "no"
                state_path.write_text(json.dumps(state))
                raise SystemExit(0)
            if arguments[0] == "stop":
                target = service(arguments[1])
                state[target]["running"] = False
                state_path.write_text(json.dumps(state))
                raise SystemExit(0)
            if arguments[0] == "inspect":
                target = service(arguments[-1])
                if "RestartPolicy" in arguments[2]:
                    print(state[target]["restart"])
                else:
                    print("running" if state[target]["running"] else "exited")
                raise SystemExit(0)
            raise SystemExit(90)
            """,
        )
        environment = harness.environment | {
            "AFTERLIGHT_QUARANTINE_GATE_ATTEMPTS": "1",
            "AFTERLIGHT_QUARANTINE_GATE_INTERVAL": "0",
            "AFTERLIGHT_SNAPSHOT_ROOT": str(harness.snapshot_root),
            "AFTERLIGHT_LOCK_OWNER_UID": str(os.getuid()),
            "AFTERLIGHT_LOCK_GROUP_GID": str(os.getgid()),
            "AFTERLIGHT_STATE_OWNER_UID": str(os.getuid()),
            "AFTERLIGHT_STATE_GROUP_GID": str(os.getgid()),
            "FAKE_PARTIAL_FAILURE": str(harness.temp_path / "partial-failure"),
        }

        result = subprocess.run(
            ["/bin/bash", str(QUARANTINE_GATE)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        state = harness._state()
        self.assertEqual(state["backup"], {"running": False, "restart": "no"})
        self.assertTrue(marker.is_file())
        authority_check = subprocess.run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-status",
                "--state-dir",
                str(harness.quarantine_dir),
                "--state-dir-mode",
                "750",
                "--state-file-mode",
                "640",
                "--owner-uid",
                str(os.getuid()),
                "--group-gid",
                str(os.getgid()),
                "--snapshot-owner-uid",
                str(os.getuid()),
                "--snapshot-group-gid",
                str(os.getgid()),
                "--snapshot-root-mode",
                "700",
                "--canonical-snapshot-root",
                str(harness.snapshot_root),
                "--print-json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(authority_check.returncode, 0, authority_check.stderr)

        resumed = subprocess.run(
            ["/bin/bash", str(QUARANTINE_GATE)],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        resumed_state = harness._state()
        self.assertEqual(resumed_state["minecraft"], {"running": False, "restart": "no"})
        self.assertEqual(resumed_state["backup"], {"running": False, "restart": "no"})

    def test_c3_archive_path_replacement_never_promotes_other_bytes(self) -> None:
        self.assertTrue(SAFETY_HELPER.is_file(), "missing descriptor-bound helper")
        source = self.temp_path / "source"
        malicious = self.temp_path / "malicious"
        source.mkdir()
        malicious.mkdir()
        (source / "world").mkdir()
        (malicious / "world").mkdir()
        (source / "world" / "level.dat").write_bytes(b"accepted")
        (malicious / "world" / "level.dat").write_bytes(b"replaced")
        (source / "padding.bin").write_bytes(b"a" * (8 * 1024 * 1024))
        (malicious / "padding.bin").write_bytes(b"b" * (8 * 1024 * 1024))
        archive = self.temp_path / "backup.tar.gz"
        receipt = self.temp_path / "backup.json"
        other_archive = self.temp_path / "other.tar.gz"
        other_receipt = self.temp_path / "other.json"
        common = [
            sys.executable,
            str(SAFETY_HELPER),
            "archive-create",
            "--owner-uid",
            str(os.getuid()),
            "--group-gid",
            str(os.getgid()),
        ]
        subprocess.run(
            common
            + ["--source", str(source), "--archive", str(archive), "--receipt", str(receipt)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            common
            + [
                "--source",
                str(malicious),
                "--archive",
                str(other_archive),
                "--receipt",
                str(other_receipt),
            ],
            check=True,
            capture_output=True,
        )
        destination = self.temp_path / "restore"
        process = subprocess.Popen(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "archive-restore",
                "--archive",
                str(archive),
                "--receipt",
                str(receipt),
                "--destination",
                str(destination),
                "--owner-uid",
                str(os.getuid()),
                "--group-gid",
                str(os.getgid()),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while process.poll() is None and time.monotonic() < deadline:
            replacement = self.temp_path / "swap.tar.gz"
            shutil.copyfile(other_archive, replacement)
            os.replace(replacement, archive)
        stdout, stderr = process.communicate(timeout=10)
        if process.returncode == 0:
            self.assertEqual(
                (destination / "world" / "level.dat").read_bytes(), b"accepted"
            )
        else:
            self.assertFalse(destination.exists(), stdout + stderr)

    def test_c3_archive_replacement_never_activates_unverified_bytes(self) -> None:
        source = self.temp_path / "accepted-source"
        malicious = self.temp_path / "malicious-source"
        current = self.temp_path / "current"
        for root, payload in (
            (source, b"accepted"),
            (malicious, b"malicious"),
            (current, b"prior-live"),
        ):
            (root / "world").mkdir(parents=True)
            (root / "world" / "level.dat").write_bytes(payload)
            (root / "padding.bin").write_bytes(payload * (1024 * 1024))
        archive = self.temp_path / "accepted.tar.gz"
        receipt = self.temp_path / "accepted.json"
        malicious_archive = self.temp_path / "malicious.tar.gz"
        malicious_receipt = self.temp_path / "malicious.json"
        create = [
            sys.executable,
            str(SAFETY_HELPER),
            "archive-create",
            "--owner-uid",
            str(os.getuid()),
            "--group-gid",
            str(os.getgid()),
        ]
        subprocess.run(
            create + ["--source", str(source), "--archive", str(archive), "--receipt", str(receipt)],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            create
            + [
                "--source",
                str(malicious),
                "--archive",
                str(malicious_archive),
                "--receipt",
                str(malicious_receipt),
            ],
            check=True,
            capture_output=True,
        )
        destination = self.temp_path / "staging"
        rescue = self.temp_path / "rescue"
        process = subprocess.Popen(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "archive-restore",
                "--archive",
                str(archive),
                "--receipt",
                str(receipt),
                "--destination",
                str(destination),
                "--activate-current",
                str(current),
                "--rescue",
                str(rescue),
                "--owner-uid",
                str(os.getuid()),
                "--group-gid",
                str(os.getgid()),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 10
        while process.poll() is None and time.monotonic() < deadline:
            replacement = self.temp_path / "activation-swap.tar.gz"
            shutil.copyfile(malicious_archive, replacement)
            os.replace(replacement, archive)
        stdout, stderr = process.communicate(timeout=10)
        live_payload = (current / "world" / "level.dat").read_bytes()
        self.assertNotEqual(live_payload, b"malicious", stdout + stderr)
        if process.returncode == 0:
            self.assertEqual(live_payload, b"accepted")

    def test_i1_progress_guard_rejects_hardlink_alias(self) -> None:
        harness = self._quest_harness()
        harness.snapshot_root.chmod(0o700)
        result = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "snapshot",
                "--world",
                str(harness.data_dir / "world"),
                "--output",
                str(harness.snapshot_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        document = harness.data_dir / "world" / "ftbteams" / "team.json"
        alias = harness.temp_path / "outside-alias.json"
        os.link(document, alias)

        compared = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "compare",
                "--world",
                str(harness.data_dir / "world"),
                "--snapshot",
                str(harness.snapshot_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(compared.returncode, 0)
        self.assertIn("link count", compared.stderr.lower())

    def test_i1_progress_guard_rejects_group_ownership_drift(self) -> None:
        harness = self._quest_harness()
        harness.snapshot_root.chmod(0o700)
        snapshotted = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "snapshot",
                "--world",
                str(harness.data_dir / "world"),
                "--output",
                str(harness.snapshot_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(snapshotted.returncode, 0, snapshotted.stderr)
        document = harness.data_dir / "world" / "ftbteams" / "team.json"
        alternate_groups = [group for group in os.getgroups() if group != document.stat().st_gid]
        self.assertTrue(alternate_groups, "test account needs a second group")
        os.chown(document, -1, alternate_groups[0])

        compared = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "compare",
                "--world",
                str(harness.data_dir / "world"),
                "--snapshot",
                str(harness.snapshot_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(compared.returncode, 0)
        self.assertRegex(compared.stderr.lower(), r"owner|group|filesystem")

    def test_i1_manifest_binds_owner_group_and_link_count(self) -> None:
        harness = self._quest_harness()
        harness.snapshot_root.chmod(0o700)
        result = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "snapshot",
                "--world",
                str(harness.data_dir / "world"),
                "--output",
                str(harness.snapshot_root),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        manifest = json.loads(
            (harness.snapshot_root / "progress-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        filesystem = manifest.get("filesystem")
        self.assertIsInstance(filesystem, list)
        self.assertGreaterEqual(len(filesystem), 5)
        for record in filesystem:
            self.assertEqual(
                set(record), {"path_sha256", "kind", "mode", "uid", "gid", "nlink"}
            )

    def test_i2_progress_guard_does_not_follow_post_stat_symlink_swap(self) -> None:
        world = self.temp_path / "world"
        quests = world / "ftbquests"
        teams = world / "ftbteams"
        quests.mkdir(parents=True)
        teams.mkdir()
        checked = teams / "team.json"
        checked.write_text('{"value":"inside"}', encoding="utf-8")
        (quests / "progress.snbt").write_text("{value:1}", encoding="utf-8")
        outside = self.temp_path / "outside.json"
        outside.write_text('{"value":"outside"}', encoding="utf-8")
        site = self.temp_path / "sitecustomize.py"
        site.write_text(
            textwrap.dedent(
                f"""
                import os
                import pathlib
                _original = pathlib.Path.read_bytes
                _original_stat = os.stat
                _swapped = False
                def _swap_after_stat(path, *args, **kwargs):
                    global _swapped
                    result = _original_stat(path, *args, **kwargs)
                    if not _swapped and path == "team.json" and kwargs.get("dir_fd") is not None:
                        checked = pathlib.Path({str(checked)!r})
                        checked.unlink()
                        checked.symlink_to({str(outside)!r})
                        _swapped = True
                    return result
                def _swap(self):
                    global _swapped
                    if not _swapped and str(self) == {str(checked)!r}:
                        self.unlink()
                        self.symlink_to({str(outside)!r})
                        _swapped = True
                    return _original(self)
                os.stat = _swap_after_stat
                pathlib.Path.read_bytes = _swap
                """
            ),
            encoding="utf-8",
        )
        snapshot = self.temp_path / "snapshot"
        snapshot.mkdir(mode=0o700)
        environment = os.environ | {"PYTHONPATH": str(self.temp_path)}

        result = subprocess.run(
            [
                sys.executable,
                str(PROGRESS_GUARD),
                "snapshot",
                "--world",
                str(world),
                "--output",
                str(snapshot),
            ],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"identity|link|race|changed|no-follow")

    def test_i3_ordinary_update_cannot_bypass_shared_lock(self) -> None:
        harness = self._friend_harness()
        runtime = harness.temp_path / "run"
        runtime.chmod(0o750)
        lock_path = runtime / "maintenance.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o660)
        self.addCleanup(os.close, descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        archive = harness.backup_dir / "afterlight-20260813-000000.tar.zst"
        environment = harness._valid_backup_environment(archive) | {
            "AFTERLIGHT_RUNTIME_DIR": str(runtime),
            "AFTERLIGHT_LOCK_OWNER_UID": str(os.getuid()),
            "AFTERLIGHT_LOCK_GROUP_GID": str(os.getgid()),
        }

        result = harness._run_operator("update", environment=environment)

        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"maintenance lock|operation lock")
        self.assertNotIn(("stop", "backup", "minecraft"), harness._compose_commands())

    def test_i4_symlinked_lock_never_truncates_victim(self) -> None:
        harness = self._quest_harness()
        victim = harness.temp_path / "victim"
        victim.write_text("do-not-truncate\n", encoding="utf-8")
        (harness.runtime_dir / "maintenance.lock").symlink_to(victim)

        result = harness._run(
            CURRENT_SHA,
            "--confirm",
            environment={
                "AFTERLIGHT_ACCEPTED_RECEIPT": "",
                "AFTERLIGHT_ACCEPTED_RECEIPT_SHA256": "",
            },
        )

        self.assertEqual(victim.read_text(encoding="utf-8"), "do-not-truncate\n")
        self.assertNotEqual(result.returncode, 0)

    def test_i5_unattested_checkout_is_rejected_before_gate(self) -> None:
        harness = self._quest_harness()

        result = harness._run(
            CURRENT_SHA,
            "--confirm",
            environment={
                "AFTERLIGHT_ACCEPTED_RECEIPT": "",
                "AFTERLIGHT_ACCEPTED_RECEIPT_SHA256": "",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("accepted release receipt", result.stderr.lower())
        self.assertFalse(harness.firewall_state.exists())

    def test_i5_real_receipt_verifier_binds_release_ci_assets_and_clean_checkout(self) -> None:
        repository = self.temp_path / "repository"
        repository.mkdir()
        (repository / "pack.toml").write_text("name = 'fixture'\n", encoding="utf-8")
        (repository / "index.toml").write_text("hash-format = 'sha256'\n", encoding="utf-8")
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        self._git(repository, "add", "pack.toml", "index.toml")
        self._git(repository, "commit", "-qm", "fixture")
        revision = self._git(repository, "rev-parse", "HEAD")

        accepted = self.temp_path / "accepted"
        public = accepted / "public"
        public.mkdir(parents=True)
        version = "1.2.3"
        packwiz = {
            "bootstrap": {"version": "v1", "size": 1, "sha256": "1" * 64},
            "installer": {"version": "v2", "size": 2, "sha256": "2" * 64},
        }
        server_state: dict[str, object] = {}

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                path, _, query = self.path.partition("?")
                if path == "/api/git/ref/tags/v1.2.3":
                    payload = {"object": {"type": "tag", "sha": "tag-object"}}
                elif path == "/api/git/tags/tag-object":
                    payload = {"object": {"sha": revision}}
                elif path == "/api/releases/tags/v1.2.3":
                    payload = {
                        "draft": False,
                        "tag_name": "v1.2.3",
                        "assets": server_state["assets"],
                    }
                elif path == "/api/actions/workflows/pack-ci.yml/runs":
                    parameters = dict(value.split("=", 1) for value in query.split("&"))
                    branch = parameters["branch"]
                    payload = {
                        "workflow_runs": [
                            {
                                "head_sha": revision,
                                "head_branch": branch,
                                "event": "push",
                                "conclusion": "success",
                            }
                        ]
                    }
                elif path == f"/raw/{revision}/pack.toml":
                    self._bytes((repository / "pack.toml").read_bytes())
                    return
                elif path == f"/raw/{revision}/index.toml":
                    self._bytes((repository / "index.toml").read_bytes())
                    return
                else:
                    self.send_error(404)
                    return
                self._bytes(json.dumps(payload).encode("utf-8"), "application/json")

            def _bytes(self, payload: bytes, content_type: str = "application/octet-stream") -> None:
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, _format: str, *_arguments: object) -> None:
                return

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(httpd.server_close)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(httpd.shutdown)
        base = f"http://127.0.0.1:{httpd.server_port}"
        pack_url = f"{base}/raw/{revision}/pack.toml"
        release_metadata = {
            "format": 3,
            "git_sha": revision,
            "version": version,
            "pack_url": pack_url,
            "packwiz": packwiz,
        }
        payloads = {
            "AFTERLIGHT-prism-instance.zip": b"prism",
            "AFTERLIGHT-curseforge.zip": b"curseforge",
            "AFTERLIGHT.mrpack": b"modrinth",
            "SHA256SUMS": b"fixture checksums\n",
            "release-metadata.json": (json.dumps(release_metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        }
        public_files = {}
        for name, payload in payloads.items():
            (public / name).write_bytes(payload)
            (public / name).chmod(0o600)
            public_files[name] = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        server_state["assets"] = [
            {
                "name": name,
                "size": record["size"],
                "digest": f"sha256:{record['sha256']}",
            }
            for name, record in public_files.items()
        ]
        receipt = {
            "format": 1,
            "git_sha": revision,
            "pack_url": pack_url,
            "packwiz": packwiz,
            "public_files": public_files,
            "version": version,
        }
        receipt_path = accepted / "gauntlet-receipt.json"
        receipt_payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        receipt_path.write_bytes(receipt_payload)
        receipt_path.chmod(0o600)
        command = [
            sys.executable,
            str(SAFETY_HELPER),
            "receipt-verify",
            "--repository",
            str(repository),
            "--receipt",
            str(receipt_path),
            "--receipt-sha256",
            hashlib.sha256(receipt_payload).hexdigest(),
            "--expected-sha",
            revision,
            "--receipt-owner-uid",
            str(os.getuid()),
            "--receipt-group-gid",
            str(os.getgid()),
        ]
        environment = os.environ | {
            "AFTERLIGHT_RAW_RELEASE_ROOT": f"{base}/raw",
            "AFTERLIGHT_GITHUB_API_ROOT": f"{base}/api",
        }
        accepted_result = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
        self.assertEqual(accepted_result.returncode, 0, accepted_result.stderr)

        (repository / "untracked").write_text("dirty\n", encoding="utf-8")
        dirty_result = subprocess.run(command, env=environment, capture_output=True, text=True, check=False)
        self.assertNotEqual(dirty_result.returncode, 0)
        self.assertIn("not clean", dirty_result.stderr.lower())

    def test_i5_live_verifier_binds_exact_mods_quests_log_and_revision(self) -> None:
        repository = self.temp_path / "live-repository"
        quests = repository / "config" / "ftbquests" / "quests"
        mods = repository / "mods"
        quests.mkdir(parents=True)
        mods.mkdir()
        (repository / "pack.toml").write_text("name = 'fixture'\n", encoding="utf-8")
        (repository / "index.toml").write_text("hash-format = 'sha256'\n", encoding="utf-8")
        (quests / "chapter.snbt").write_text("{id:'fixture'}\n", encoding="utf-8")
        (mods / "fixture.pw.toml").write_text('filename = "fixture.jar"\nside = "both"\n', encoding="utf-8")
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", "fixture")
        revision = self._git(repository, "rev-parse", "HEAD")
        data = self.temp_path / "live-data"
        shutil.copytree(quests, data / "config" / "ftbquests" / "quests")
        (data / "mods").mkdir(parents=True)
        (data / "mods" / "fixture.jar").write_bytes(b"jar")
        (data / "logs").mkdir()
        (data / "logs" / "latest.log").write_text(
            "Loaded 1 chapter groups, 2 chapters, 3 quests, 0 reward tables\n",
            encoding="utf-8",
        )
        (data / ".afterlight-pack-sha").write_text(f"{revision}\n", encoding="ascii")
        command = [
            sys.executable,
            str(SAFETY_HELPER),
            "live-verify",
            "--repository",
            str(repository),
            "--data",
            str(data),
            "--expected-sha",
            revision,
        ]
        valid = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        (data / "mods" / "unexpected.jar").write_bytes(b"unexpected")
        invalid = subprocess.run(command, capture_output=True, text=True, check=False)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("mod inventory", invalid.stderr.lower())

    def test_i6_marker_path_traversal_is_rejected(self) -> None:
        harness = self._quest_harness()
        harness.snapshot_root.chmod(0o700)
        (harness.snapshot_root / "recorded").mkdir(mode=0o700)
        marker = harness.quarantine_dir / "state"
        marker.write_text(
            json.dumps(
                {
                    "format": "afterlight.transaction.v2",
                    "transaction_id": "c" * 32,
                    "status": "pending",
                    "phase": "candidate-started",
                    "expected_sha": CURRENT_SHA,
                    "prior_sha": PRIOR_SHA,
                    "gate_comment": f"afterlight-quest-update-{CURRENT_SHA}-{'c' * 32}",
                    "snapshot_dir": f"{harness.snapshot_root}/recorded/..",
                    "snapshot_root": str(harness.snapshot_root),
                    "receipt_sha256": "a" * 64,
                    "containers": {
                        "minecraft": {"restart_disabled": False, "stopped": False},
                        "backup": {"restart_disabled": False, "stopped": False},
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        marker.chmod(0o640)
        result = subprocess.run(
            ["/bin/bash", str(QUARANTINE_GATE)],
            cwd=ROOT,
            env=harness.environment
            | {
                "AFTERLIGHT_QUARANTINE_GATE_ATTEMPTS": "1",
                "AFTERLIGHT_QUARANTINE_GATE_INTERVAL": "0",
                "AFTERLIGHT_SNAPSHOT_ROOT": str(harness.snapshot_root),
            },
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"canonical|malformed|unsafe")

    def test_i7_lock_runner_terminates_foreground_child_group(self) -> None:
        self.assertTrue(SAFETY_HELPER.is_file(), "missing controlled lock runner")
        runtime = self.temp_path / "run"
        runtime.mkdir()
        runtime.chmod(0o750)
        pid_path = self.temp_path / "child.pid"
        child = self.temp_path / "child.py"
        child.write_text(
            "import os,time,pathlib\n"
            f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()))\n"
            "time.sleep(120)\n",
            encoding="utf-8",
        )
        process = subprocess.Popen(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "lock-run",
                "--runtime-dir",
                str(runtime),
                "--owner-uid",
                str(os.getuid()),
                "--group-gid",
                str(os.getgid()),
                "--",
                sys.executable,
                str(child),
            ],
            start_new_session=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 5
        while not pid_path.exists() and time.monotonic() < deadline:
            time.sleep(0.02)
        self.assertTrue(pid_path.exists())
        child_pid = int(pid_path.read_text(encoding="utf-8"))

        process.send_signal(signal.SIGTERM)
        process.communicate(timeout=5)

        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)

    def test_i7_controlled_command_timeout_kills_and_reaps_child(self) -> None:
        pid_path = self.temp_path / "timed-child.pid"
        child = self.temp_path / "timed-child.py"
        child.write_text(
            "import os,time,pathlib\n"
            f"pathlib.Path({str(pid_path)!r}).write_text(str(os.getpid()))\n"
            "time.sleep(120)\n",
            encoding="utf-8",
        )
        started = time.monotonic()
        result = subprocess.run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "run-command",
                "--timeout",
                "0.2",
                "--",
                sys.executable,
                str(child),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        self.assertEqual(result.returncode, 124, result.stderr)
        self.assertLess(time.monotonic() - started, 3)
        child_pid = int(pid_path.read_text(encoding="utf-8"))
        with self.assertRaises(ProcessLookupError):
            os.kill(child_pid, 0)

    def test_m3_ingress_gate_reconstructs_rule_from_pending_authority(self) -> None:
        harness = quest_safe_tests.QuarantineGateTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        harness.firewall_state.unlink(missing_ok=True)
        result = subprocess.run(
            ["/bin/bash", str(INGRESS_GATE)],
            cwd=ROOT,
            env=harness.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(harness.firewall_state.is_file())
        self.assertIn(harness.transaction_id, harness.firewall_state.read_text(encoding="utf-8"))

    def test_m1_recovery_uses_reviewed_helper_not_inline_archive_commands(self) -> None:
        self.assertTrue(RECOVERY_HELPER.is_file())
        source = SERVER_README.read_text(encoding="utf-8")
        recovery = source.split("## Durable Quarantine Recovery", 1)[1]
        self.assertIn("afterlight-quarantine-recover.sh", recovery)
        self.assertNotRegex(recovery, r"(?m)^tar |^sha256sum |^mv /srv/afterlight")

    def test_m2_docs_call_snapshot_sensitive_and_define_retention(self) -> None:
        source = SERVER_README.read_text(encoding="utf-8")
        self.assertNotIn("privacy-safe canonical", source)
        self.assertRegex(source.lower(), r"sensitive root-only recovery data")
        self.assertRegex(source.lower(), r"retention")

    def test_m3_systemd_gate_fails_when_executable_is_missing(self) -> None:
        source = QUARANTINE_SERVICE.read_text(encoding="utf-8")
        self.assertNotIn("ConditionFileIsExecutable", source)
        self.assertIn("Requires=docker.service", source)
        self.assertIn("Before=afterlight-maintenance.service", source)
        ingress = INGRESS_SERVICE.read_text(encoding="utf-8")
        self.assertIn("Before=docker.service", ingress)
        self.assertIn("RequiredBy=docker.service", ingress)
        self.assertNotIn("ConditionFileIsExecutable", ingress)
        self.assertTrue(INGRESS_GATE.is_file())


if __name__ == "__main__":
    unittest.main()
