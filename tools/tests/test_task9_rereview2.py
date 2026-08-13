from __future__ import annotations

import fcntl
import hashlib
import http.server
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools.tests import test_friend_server as friend_server_tests


ROOT = Path(__file__).resolve().parents[2]
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
PROGRESS_GUARD = ROOT / "server" / "afterlight-progress-guard.py"
SERVER_OPERATOR = ROOT / "server" / "afterlight-server.sh"
RECOVERY_HELPER = ROOT / "server" / "afterlight-quarantine-recover.sh"
RETENTION_HELPER = ROOT / "server" / "afterlight-snapshot-retention.sh"
COMPOSE_FILE = ROOT / "server" / "docker-compose.yml"
TRANSACTION_COMPOSE_FILE = ROOT / "server" / "docker-compose.transaction.yml"
MAINTENANCE_SERVICE = ROOT / "server" / "systemd" / "afterlight-maintenance.service"
INGRESS_SERVICE = ROOT / "server" / "systemd" / "afterlight-ingress-boot-gate.service"
POLICY_FILE = ROOT / "tools" / "release-policy.env"
CURRENT_SHA = "1" * 40
PRIOR_SHA = "2" * 40


class Task9Rereview2Tests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()

    def _run(self, arguments: list[str], *, environment: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=ROOT,
            env=os.environ | (environment or {}),
            capture_output=True,
            text=True,
            check=False,
        )

    def _git(self, repository: Path, *arguments: str) -> str:
        result = self._run(["git", "-C", str(repository), *arguments])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _compose_model(self) -> dict[str, object]:
        for name in ("data", "backups", "secrets"):
            (self.temp_path / name).mkdir()
        result = self._run(
            [
                "docker",
                "compose",
                "--project-name",
                "afterlight-rereview2",
                "-f",
                str(COMPOSE_FILE),
                "-f",
                str(TRANSACTION_COMPOSE_FILE),
                "config",
                "--format",
                "json",
            ],
            environment={
                "DATA_DIR": str(self.temp_path / "data"),
                "BACKUP_DIR": str(self.temp_path / "backups"),
                "SECRETS_DIR": str(self.temp_path / "secrets"),
                "AFTERLIGHT_DATA_UID": "1000",
                "AFTERLIGHT_DATA_GID": "1000",
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def _live_fixture(self, *, installed_jar: bytes, log_text: str) -> tuple[Path, Path, str]:
        repository = self.temp_path / f"repository-{time.time_ns()}"
        quests = repository / "config" / "ftbquests" / "quests"
        mods = repository / "mods"
        tools = repository / "tools"
        quests.mkdir(parents=True)
        mods.mkdir()
        tools.mkdir()
        expected_jar = b"accepted server jar bytes\n"
        expected_sha256 = hashlib.sha256(expected_jar).hexdigest()
        expected_sha512 = hashlib.sha512(expected_jar).hexdigest()
        (repository / "pack.toml").write_text("name = 'fixture'\n", encoding="utf-8")
        (repository / "index.toml").write_text("hash-format = 'sha256'\n", encoding="utf-8")
        (quests / "chapter.snbt").write_text("{id:'fixture'}\n", encoding="utf-8")
        (mods / "fixture.pw.toml").write_text(
            "name = \"Fixture\"\n"
            "filename = \"fixture.jar\"\n"
            "side = \"both\"\n\n"
            "[download]\n"
            "url = \"https://example.invalid/fixture.jar\"\n"
            "hash-format = \"sha512\"\n"
            f"hash = \"{expected_sha512}\"\n",
            encoding="utf-8",
        )
        (tools / "server-mod-manifest-lock.json").write_text(
            json.dumps(
                {
                    "format": 1,
                    "files": [
                        {
                            "filename": "fixture.jar",
                            "hash": expected_sha512,
                            "hash_format": "sha512",
                            "metadata_path": "mods/fixture.pw.toml",
                            "size": len(expected_jar),
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", "fixture")
        revision = self._git(repository, "rev-parse", "HEAD")

        data = self.temp_path / f"data-{time.time_ns()}"
        shutil.copytree(quests, data / "config" / "ftbquests" / "quests")
        (data / "mods").mkdir(parents=True)
        (data / "mods" / "fixture.jar").write_bytes(installed_jar)
        (data / "logs").mkdir()
        (data / "logs" / "latest.log").write_text(log_text, encoding="utf-8")
        marker = data / ".afterlight-pack-sha"
        marker.write_text(f"{revision}\n", encoding="ascii")
        marker.chmod(0o600)
        return repository, data, revision

    def _live_verify(self, repository: Path, data: Path, revision: str) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "live-verify",
                "--repository",
                str(repository),
                "--data",
                str(data),
                "--expected-sha",
                revision,
                "--container-id",
                "a" * 64,
                "--started-at",
                "2000-01-01T00:00:00Z",
                "--data-owner-uid",
                str(os.getuid()),
                "--data-group-gid",
                str(os.getgid()),
            ]
        )

    def test_c1_compose_binds_every_published_port_to_ipv4(self) -> None:
        model = self._compose_model()
        ports = model["services"]["minecraft"]["ports"]
        self.assertEqual({record["host_ip"] for record in ports}, {"0.0.0.0"})
        self.assertEqual(
            {(record["published"], record["protocol"]) for record in ports},
            {("25565", "tcp"), ("24454", "udp")},
        )

    def test_i1_receipt_uses_policy_file_url_contract(self) -> None:
        policy_url = next(
            line.split("=", 1)[1]
            for line in POLICY_FILE.read_text(encoding="utf-8").splitlines()
            if line.startswith("RELEASE_PACK_URL=")
        )
        self.assertEqual(policy_url, "https://luskish.github.io/afterlight-pack/pack.toml")

        repository = self.temp_path / "accepted-repository"
        (repository / "tools").mkdir(parents=True)
        (repository / "pack.toml").write_text("name = 'fixture'\n", encoding="utf-8")
        (repository / "index.toml").write_text("hash-format = 'sha256'\n", encoding="utf-8")
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")

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
            def do_GET(handler_self) -> None:
                path, _, query = handler_self.path.partition("?")
                if path == "/api/git/ref/tags/v1.2.3":
                    handler_self._json({"object": {"type": "tag", "sha": "tag-object"}})
                elif path == "/api/git/tags/tag-object":
                    handler_self._json({"object": {"sha": server_state["revision"]}})
                elif path == "/api/releases/tags/v1.2.3":
                    handler_self._json(
                        {"draft": False, "tag_name": "v1.2.3", "assets": server_state["assets"]}
                    )
                elif path == "/api/actions/workflows/pack-ci.yml/runs":
                    parameters = dict(value.split("=", 1) for value in query.split("&"))
                    handler_self._json(
                        {
                            "workflow_runs": [
                                {
                                    "head_sha": server_state["revision"],
                                    "head_branch": parameters["branch"],
                                    "event": "push",
                                    "conclusion": "success",
                                }
                            ]
                        }
                    )
                elif path == "/policy/pack.toml":
                    handler_self._bytes((repository / "pack.toml").read_bytes())
                elif path == "/policy/index.toml":
                    handler_self._bytes((repository / "index.toml").read_bytes())
                else:
                    handler_self.send_error(404)

            def _json(handler_self, value: object) -> None:
                handler_self._bytes(json.dumps(value).encode("utf-8"), "application/json")

            def _bytes(handler_self, payload: bytes, content_type: str = "application/octet-stream") -> None:
                handler_self.send_response(200)
                handler_self.send_header("Content-Type", content_type)
                handler_self.send_header("Content-Length", str(len(payload)))
                handler_self.end_headers()
                handler_self.wfile.write(payload)

            def log_message(self, _format: str, *_arguments: object) -> None:
                return

        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.addCleanup(httpd.server_close)
        thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(httpd.shutdown)
        base = f"http://127.0.0.1:{httpd.server_port}"
        fixture_policy_url = f"{base}/policy/pack.toml"
        (repository / "tools" / "release-policy.env").write_text(
            f"RELEASE_PACK_URL={fixture_policy_url}\n",
            encoding="utf-8",
        )
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", "fixture")
        revision = self._git(repository, "rev-parse", "HEAD")
        server_state["revision"] = revision

        release_metadata = {
            "format": 3,
            "git_sha": revision,
            "version": version,
            "pack_url": fixture_policy_url,
            "packwiz": packwiz,
        }
        payloads = {
            "AFTERLIGHT-prism-instance.zip": b"prism",
            "AFTERLIGHT-curseforge.zip": b"curseforge",
            "AFTERLIGHT.mrpack": b"modrinth",
            "SHA256SUMS": b"fixture checksums\n",
            "release-metadata.json": (json.dumps(release_metadata, indent=2, sort_keys=True) + "\n").encode(),
        }
        public_files = {}
        for name, payload in payloads.items():
            path = public / name
            path.write_bytes(payload)
            path.chmod(0o600)
            public_files[name] = {"size": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
        server_state["assets"] = [
            {"name": name, "size": record["size"], "digest": f"sha256:{record['sha256']}"}
            for name, record in public_files.items()
        ]
        receipt = {
            "format": 1,
            "git_sha": revision,
            "pack_url": fixture_policy_url,
            "packwiz": packwiz,
            "public_files": public_files,
            "version": version,
        }
        receipt_payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
        receipt_path = accepted / "gauntlet-receipt.json"
        receipt_path.write_bytes(receipt_payload)
        receipt_path.chmod(0o600)
        result = self._run(
            [
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
            ],
            environment={"AFTERLIGHT_GITHUB_API_ROOT": f"{base}/api"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_i2_existing_lock_is_never_chmoded_by_the_caller(self) -> None:
        runtime = self.temp_path / "runtime"
        runtime.mkdir(mode=0o700)
        lock = runtime / "maintenance.lock"
        lock.write_bytes(b"")
        lock.chmod(0o600)
        spec = importlib.util.spec_from_file_location("afterlight_safety_lock", SAFETY_HELPER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        arguments = SimpleNamespace(
            runtime_dir=runtime,
            runtime_mode=0o700,
            lock_mode=0o600,
            owner_uid=os.getuid(),
            group_gid=os.getgid(),
        )
        with mock.patch.object(module.os, "fchmod", side_effect=PermissionError("not owner")):
            descriptor = module.secure_lock_descriptor(arguments)
        os.close(descriptor)
        self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o600)

    def test_i2_production_identity_is_root_control_and_explicit_runtime_uid(self) -> None:
        readme = (ROOT / "server" / "README.md").read_text(encoding="utf-8")
        compose = COMPOSE_FILE.read_text(encoding="utf-8")
        update = (ROOT / "server" / "afterlight-quest-safe-update.sh").read_text(encoding="utf-8")
        self.assertIn("root-only host control plane", readme.lower())
        self.assertIn("AFTERLIGHT_DATA_UID", compose)
        self.assertIn("AFTERLIGHT_DATA_GID", compose)
        self.assertNotIn("DATA_OWNER_UID=$(path_uid", update)
        self.assertNotIn("SNAPSHOT_OWNER_UID=${AFTERLIGHT_SNAPSHOT_OWNER_UID", update)

    def test_i3_only_root_ingress_unit_manages_runtime_directory(self) -> None:
        maintenance = MAINTENANCE_SERVICE.read_text(encoding="utf-8")
        ingress = INGRESS_SERVICE.read_text(encoding="utf-8")
        self.assertIn("User=root", maintenance)
        self.assertIn("Group=root", maintenance)
        self.assertNotIn("RuntimeDirectory=afterlight", maintenance)
        self.assertIn("User=root", ingress)
        self.assertIn("RuntimeDirectory=afterlight", ingress)

    def test_i4_environment_alone_cannot_forge_inherited_lock(self) -> None:
        harness = friend_server_tests.FriendServerTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        lock_path = harness.runtime_dir / "maintenance.lock"
        descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o660)
        self.addCleanup(os.close, descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = harness._run_operator(
            "stop",
            environment=harness.environment | {"AFTERLIGHT_LOCK_HELD": "1"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(("stop", "backup", "minecraft"), harness._compose_commands())

    def test_i5_backup_has_meaningful_rendered_healthcheck(self) -> None:
        model = self._compose_model()
        healthcheck = model["services"]["backup"].get("healthcheck")
        self.assertIsInstance(healthcheck, dict)
        rendered = " ".join(healthcheck["test"])
        self.assertIn("mc-monitor", rendered)
        self.assertIn("/data", rendered)
        self.assertIn("/backups", rendered)
        self.assertEqual(model["services"]["backup"]["restart"], "no")

    def test_i6_production_paths_are_canonical_and_test_root_is_explicit(self) -> None:
        contract = ROOT / "server" / "afterlight-safety-contract.sh"
        self.assertTrue(contract.is_file())
        source = contract.read_text(encoding="utf-8")
        for path in (
            "/run/afterlight",
            "/var/lib/afterlight/quest-update-quarantine",
            "/var/lib/afterlight/quest-update-snapshots",
            "/srv/afterlight/data",
            "/srv/afterlight/backups",
            "/etc/afterlight/secrets",
        ):
            self.assertIn(path, source)
        self.assertIn("AFTERLIGHT_SAFETY_TEST_ROOT", source)
        self.assertIn(".afterlight-safety-test-contract", source)
        for script in (
            "afterlight-server.sh",
            "afterlight-maintenance.sh",
            "afterlight-quest-safe-update.sh",
            "afterlight-ingress-boot-gate.sh",
            "afterlight-quarantine-gate.sh",
            "afterlight-quarantine-recover.sh",
        ):
            script_source = (ROOT / "server" / script).read_text(encoding="utf-8")
            self.assertIn("afterlight-safety-contract.sh", script_source)

    def test_i7_world_descriptor_must_match_checked_root_identity(self) -> None:
        world = self.temp_path / "world"
        (world / "ftbquests").mkdir(parents=True)
        (world / "ftbteams").mkdir()
        (world / "ftbquests" / "progress.snbt").write_text("{completed:[1L]}", encoding="utf-8")
        (world / "ftbteams" / "team.json").write_text('{"members":["fixture"]}', encoding="utf-8")
        spec = importlib.util.spec_from_file_location("afterlight_progress_guard_race", PROGRESS_GUARD)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        self.addCleanup(sys.modules.pop, spec.name, None)
        spec.loader.exec_module(module)
        original = module.checked_root
        swapped = False

        def swap_after_check(path: Path, label: str):
            nonlocal swapped
            result = original(path, label)
            if label == "world" and not swapped:
                replaced = self.temp_path / "replaced-world"
                path.rename(replaced)
                shutil.copytree(replaced, path)
                swapped = True
            return result

        module.checked_root = swap_after_check
        with self.assertRaisesRegex(module.GuardError, r"identity|changed|replacement"):
            module.collect_state(world)

    def test_i8_tampered_same_name_mod_is_rejected(self) -> None:
        repository, data, revision = self._live_fixture(
            installed_jar=b"tampered bytes with same filename\n",
            log_text="Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables\n",
        )
        result = self._live_verify(repository, data, revision)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"mod.*(?:digest|size|identity)")

    def test_i8_severity_first_ftb_error_is_rejected(self) -> None:
        repository, data, revision = self._live_fixture(
            installed_jar=b"accepted server jar bytes\n",
            log_text=(
                "[Server thread/ERROR] [FTB Quests/]: Failed to load fixture\n"
                "Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables\n"
            ),
        )
        result = self._live_verify(repository, data, revision)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ftb quests", result.stderr.lower())

    def test_i8_zero_quest_load_is_rejected(self) -> None:
        repository, data, revision = self._live_fixture(
            installed_jar=b"accepted server jar bytes\n",
            log_text="Loaded 0 chapter groups, 0 chapters, 0 quests, 0 reward tables\n",
        )
        result = self._live_verify(repository, data, revision)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"positive|zero|quest")

    def test_i8_log_must_belong_to_the_candidate_start(self) -> None:
        repository, data, revision = self._live_fixture(
            installed_jar=b"accepted server jar bytes\n",
            log_text="Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables\n",
        )
        old_epoch = time.time() - 3600
        os.utime(data / "logs" / "latest.log", (old_epoch, old_epoch))
        spec = importlib.util.spec_from_file_location("afterlight_safety_live_log", SAFETY_HELPER)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        arguments = SimpleNamespace(
            repository=repository,
            data=data,
            expected_sha=revision,
            container_id="a" * 64,
            started_at="2100-01-01T00:00:00Z",
            data_owner_uid=os.getuid(),
            data_group_gid=os.getgid(),
            server_mod_manifest_json=None,
        )
        with self.assertRaisesRegex(module.SafetyError, r"candidate|start|log"):
            module.command_live_verify(arguments)

    def test_i9_archive_activation_resumes_partial_rename_and_is_idempotent(self) -> None:
        snapshot_root = self.temp_path / "snapshots"
        source = self.temp_path / "prior"
        parent = self.temp_path / "live"
        snapshot_root.mkdir(mode=0o700)
        source.mkdir(mode=0o700)
        parent.mkdir(mode=0o700)
        (source / "marker").write_text("prior\n", encoding="utf-8")
        current = parent / "data"
        current.mkdir(mode=0o700)
        (current / "marker").write_text("candidate\n", encoding="utf-8")
        archive = snapshot_root / "full-backup.tar.gz"
        receipt = snapshot_root / "backup-preflight.json"
        common = [
            "--owner-uid",
            str(os.getuid()),
            "--group-gid",
            str(os.getgid()),
        ]
        created = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "archive-create",
                "--source",
                str(source),
                "--archive",
                str(archive),
                "--receipt",
                str(receipt),
                *common,
            ]
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        staging = parent / ".data.restore"
        rescue = parent / "data.rescue"
        extracted = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "archive-restore",
                "--archive",
                str(archive),
                "--receipt",
                str(receipt),
                "--destination",
                str(staging),
                *common,
            ]
        )
        self.assertEqual(extracted.returncode, 0, extracted.stderr)
        current.rename(rescue)
        activation = [
            sys.executable,
            str(SAFETY_HELPER),
            "archive-restore",
            "--archive",
            str(archive),
            "--receipt",
            str(receipt),
            "--destination",
            str(staging),
            "--activate-current",
            str(current),
            "--rescue",
            str(rescue),
            "--resume",
            *common,
        ]
        first = self._run(activation)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual((current / "marker").read_text(encoding="utf-8"), "prior\n")
        self.assertEqual((rescue / "marker").read_text(encoding="utf-8"), "candidate\n")
        second = self._run(activation)
        self.assertEqual(second.returncode, 0, second.stderr)

    def test_i9_no_snapshot_recovery_has_reviewed_phase_guard(self) -> None:
        source = RECOVERY_HELPER.read_text(encoding="utf-8")
        self.assertIn("recovery-original-verify", source)
        self.assertIn("no authenticated snapshot", source.lower())
        self.assertNotIn("Transaction has no authenticated recovery snapshot", source)

    def test_i9_no_snapshot_authority_accepts_only_unchanged_pre_mutation_data(self) -> None:
        state = self.temp_path / "state"
        snapshots = self.temp_path / "snapshots"
        data = self.temp_path / "data"
        snapshots.mkdir(mode=0o700)
        data.mkdir(mode=0o700)
        marker = data / ".afterlight-pack-sha"
        marker.write_text(f"{PRIOR_SHA}\n", encoding="ascii")
        marker.chmod(0o600)
        common = [
            "--state-dir",
            str(state),
            "--state-dir-mode",
            "700",
            "--state-file-mode",
            "600",
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
            str(snapshots),
        ]
        created = self._run(
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
                str(snapshots),
                "--receipt-sha256",
                "a" * 64,
                "--data-root",
                str(data),
                "--data-owner-uid",
                str(os.getuid()),
                "--data-group-gid",
                str(os.getgid()),
                "--server-mod-manifest-json",
                "[]",
            ]
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        transaction_id = created.stdout.strip()
        verify = [
            sys.executable,
            str(SAFETY_HELPER),
            "recovery-original-verify",
            *common,
            "--transaction-id",
            transaction_id,
            "--data",
            str(data),
            "--data-owner-uid",
            str(os.getuid()),
            "--data-group-gid",
            str(os.getgid()),
        ]
        unchanged = self._run(verify)
        self.assertEqual(unchanged.returncode, 0, unchanged.stderr)
        mutated = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-update",
                *common,
                "--transaction-id",
                transaction_id,
                "--data-mutated",
                "true",
            ]
        )
        self.assertEqual(mutated.returncode, 0, mutated.stderr)
        rejected = self._run(verify)
        self.assertNotEqual(rejected.returncode, 0)
        self.assertIn("mutation", rejected.stderr.lower())

    def test_m1_root_retention_action_uses_authenticated_shared_lock(self) -> None:
        self.assertTrue(RETENTION_HELPER.is_file())
        source = RETENTION_HELPER.read_text(encoding="utf-8")
        contract = (ROOT / "server" / "afterlight-safety-contract.sh").read_text(encoding="utf-8")
        self.assertIn("afterlight_verify_or_reexec_lock", source)
        self.assertIn("lock-verify", contract)
        self.assertIn("snapshot-prune", source)
        self.assertIn("7", source)
        self.assertNotIn("AFTERLIGHT_LOCK_HELD", source)

    def test_m1_prune_removes_only_old_successful_snapshots(self) -> None:
        root = self.temp_path / "snapshots"
        root.mkdir(mode=0o700)
        common = [
            "--owner-uid",
            str(os.getuid()),
            "--group-gid",
            str(os.getgid()),
        ]
        snapshots: dict[str, Path] = {}
        for label in ("old", "recent", "incomplete"):
            created = self._run(
                [
                    sys.executable,
                    str(SAFETY_HELPER),
                    "snapshot-create",
                    "--snapshot-root",
                    str(root),
                    "--name",
                    f"quest-update-{label}",
                    *common,
                ]
            )
            self.assertEqual(created.returncode, 0, created.stderr)
            snapshots[label] = Path(created.stdout.strip())
            (snapshots[label] / "progress" / "record").write_text(label, encoding="utf-8")
        for label, completed_at, transaction_id in (
            ("old", "1", "a" * 32),
            ("recent", "200", "b" * 32),
        ):
            completed = self._run(
                [
                    sys.executable,
                    str(SAFETY_HELPER),
                    "snapshot-complete",
                    "--snapshot",
                    str(snapshots[label]),
                    "--transaction-id",
                    transaction_id,
                    "--completed-at",
                    completed_at,
                    *common,
                ]
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
        pruned = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "snapshot-prune",
                "--snapshot-root",
                str(root),
                "--older-than",
                "100",
                *common,
            ]
        )
        self.assertEqual(pruned.returncode, 0, pruned.stderr)
        self.assertFalse(snapshots["old"].exists())
        self.assertTrue(snapshots["recent"].is_dir())
        self.assertTrue(snapshots["incomplete"].is_dir())


if __name__ == "__main__":
    unittest.main()
