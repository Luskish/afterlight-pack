from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from tools.tests import test_friend_server as friend_server_tests
from tools.tests import test_quest_safe_update as quest_safe_tests


ROOT = Path(__file__).resolve().parents[2]
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
SERVER_OPERATOR = ROOT / "server" / "afterlight-server.sh"
SAFE_UPDATE = ROOT / "server" / "afterlight-quest-safe-update.sh"
RECOVERY_HELPER = ROOT / "server" / "afterlight-quarantine-recover.sh"
FINALIZER = ROOT / "server" / "afterlight-transaction-finalize.sh"
CONTRACT = ROOT / "server" / "afterlight-safety-contract.sh"
CURRENT_SHA = "3" * 40
PRIOR_SHA = "2" * 40
CONTAINER_ID = "a" * 64
CONTAINER_START = "2026-08-13T12:00:00.000000000Z"


class Task9Rereview3Tests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()

    def _run(
        self,
        arguments: list[str],
        *,
        environment: dict[str, str] | None = None,
        cwd: Path = ROOT,
        timeout: float = 30,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            arguments,
            cwd=cwd,
            env=os.environ | (environment or {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )

    def _write_executable(self, path: Path, source: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _git(self, repository: Path, *arguments: str) -> str:
        result = self._run(["git", "-C", str(repository), *arguments])
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _state_fixture(self) -> tuple[Path, Path, Path, list[str]]:
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
        return state, snapshots, data, common

    def _create_authority(
        self,
        snapshots: Path,
        data: Path,
        common: list[str],
        *,
        candidate_manifest: str = "[]",
        prior_manifest: str = "[]",
    ) -> str:
        result = self._run(
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
                "b" * 64,
                "--data-root",
                str(data),
                "--data-owner-uid",
                str(os.getuid()),
                "--data-group-gid",
                str(os.getgid()),
                "--candidate-server-mod-manifest-json",
                candidate_manifest,
                "--prior-server-mod-manifest-json",
                prior_manifest,
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip()

    def _status(self, common: list[str], field: str) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-status",
                *common,
                "--field",
                field,
            ]
        )

    def _manifest_commit(self, repository: Path, filename: str, payload: bytes) -> str:
        mods = repository / "mods"
        tools = repository / "tools"
        mods.mkdir(parents=True, exist_ok=True)
        tools.mkdir(parents=True, exist_ok=True)
        for path in mods.glob("*.pw.toml"):
            path.unlink()
        digest = hashlib.sha512(payload).hexdigest()
        metadata_path = f"mods/{filename}.pw.toml"
        (repository / metadata_path).write_text(
            "name = \"Fixture\"\n"
            f"filename = \"{filename}.jar\"\n"
            "side = \"both\"\n\n"
            "[download]\n"
            "url = \"https://example.invalid/fixture.jar\"\n"
            "hash-format = \"sha512\"\n"
            f"hash = \"{digest}\"\n",
            encoding="utf-8",
        )
        (tools / "server-mod-manifest-lock.json").write_text(
            json.dumps(
                {
                    "format": 1,
                    "files": [
                        {
                            "filename": f"{filename}.jar",
                            "hash": digest,
                            "hash_format": "sha512",
                            "metadata_path": metadata_path,
                            "size": len(payload),
                        }
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", filename)
        return self._git(repository, "rev-parse", "HEAD")

    def _live_fixture(self) -> tuple[Path, Path, str]:
        repository = self.temp_path / "live-repository"
        quests = repository / "config" / "ftbquests" / "quests"
        quests.mkdir(parents=True)
        (quests / "chapter.snbt").write_text("{id:'fixture'}\n", encoding="utf-8")
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        revision = self._manifest_commit(repository, "candidate", b"candidate jar\n")
        data = self.temp_path / "live-data"
        (data / "config" / "ftbquests").mkdir(parents=True)
        (data / "config" / "ftbquests" / "quests").symlink_to(quests, target_is_directory=True)
        # The real verifier rejects links, so replace the convenience link with a copied tree.
        (data / "config" / "ftbquests" / "quests").unlink()
        import shutil

        shutil.copytree(quests, data / "config" / "ftbquests" / "quests")
        (data / "mods").mkdir()
        (data / "mods" / "candidate.jar").write_bytes(b"candidate jar\n")
        (data / "logs").mkdir()
        host_log = data / "logs" / "latest.log"
        host_log.write_text(
            "Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables\n",
            encoding="utf-8",
        )
        future = time.time() + 3600
        os.utime(host_log, (future, future))
        marker = data / ".afterlight-pack-sha"
        marker.write_text(f"{revision}\n", encoding="ascii")
        marker.chmod(0o600)
        return repository, data, revision

    def _docker_fixture(self, source: str) -> dict[str, str]:
        fake_bin = self.temp_path / f"bin-{time.time_ns()}"
        self._write_executable(fake_bin / "docker", source)
        return {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

    def test_c1_ordinary_update_rejects_immutable_quest_change_before_docker(self) -> None:
        harness = friend_server_tests.FriendServerTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        marker = harness.data_dir / ".afterlight-pack-sha"
        marker.write_text(f"{PRIOR_SHA}\n", encoding="ascii")
        marker.chmod(0o600)
        git_log = harness.temp_path / "git.log"
        harness._write_executable(
            "git",
            r"""
            #!/usr/bin/env bash
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            if [ "$#" -eq 5 ] && [ "$1" = "-C" ] && [ "$3" = "rev-parse" ]; then
              printf '%s\n' "$FAKE_GIT_SHA"
              exit 0
            fi
            if [ "$#" -ge 5 ] && [ "$1" = "-C" ] && [ "$3" = "cat-file" ]; then
              exit 0
            fi
            if [ "$#" -ge 8 ] && [ "$1" = "-C" ] && [ "$3" = "diff" ]; then
              exit 1
            fi
            printf 'unexpected fake git command: %s\n' "$*" >&2
            exit 94
            """,
        )
        archive = harness.backup_dir / "afterlight-20260813-120000.tar.zst"
        result = harness._run_operator(
            "update",
            environment={
                **harness._valid_backup_environment(archive),
                "FAKE_GIT_LOG": str(git_log),
            },
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("quest-safe", result.stderr.lower())
        self.assertEqual(harness._docker_calls(), [])
        self.assertRegex(git_log.read_text(encoding="utf-8"), r"diff.*config/ftbquests/quests")

    def test_i1_checkout_intent_survives_crash_and_reconciles_prior_idempotently(self) -> None:
        repository = self.temp_path / "checkout-repository"
        repository.mkdir()
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        (repository / "record").write_text("prior\n", encoding="utf-8")
        self._git(repository, "add", ".")
        self._git(repository, "commit", "-qm", "prior")
        prior = self._git(repository, "rev-parse", "HEAD")
        (repository / "record").write_text("candidate\n", encoding="utf-8")
        self._git(repository, "commit", "-qam", "candidate")
        candidate = self._git(repository, "rev-parse", "HEAD")
        global PRIOR_SHA, CURRENT_SHA
        saved_prior, saved_current = PRIOR_SHA, CURRENT_SHA
        PRIOR_SHA, CURRENT_SHA = prior, candidate
        self.addCleanup(lambda: globals().update(PRIOR_SHA=saved_prior, CURRENT_SHA=saved_current))
        _, snapshots, data, common = self._state_fixture()
        transaction_id = self._create_authority(snapshots, data, common)
        intent = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-update",
                *common,
                "--transaction-id",
                transaction_id,
                "--phase",
                "rollback-checkout-prior",
                "--checkout-target-sha",
                prior,
            ]
        )
        self.assertEqual(intent.returncode, 0, intent.stderr)
        self.assertEqual(self._git(repository, "rev-parse", "HEAD"), candidate)
        reconcile = [
            sys.executable,
            str(SAFETY_HELPER),
            "checkout-reconcile",
            *common,
            "--repository",
            str(repository),
        ]
        first = self._run(reconcile)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(self._git(repository, "rev-parse", "HEAD"), prior)
        second = self._run(reconcile)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertEqual(self._status(common, "checkout_target_sha").stdout.strip(), prior)

    def test_i2_prior_and_candidate_manifests_bind_to_immutable_revisions(self) -> None:
        repository = self.temp_path / "manifest-repository"
        repository.mkdir()
        self._git(repository, "init", "-q")
        self._git(repository, "config", "user.name", "AFTERLIGHT Test")
        self._git(repository, "config", "user.email", "afterlight@example.invalid")
        prior = self._manifest_commit(repository, "prior", b"prior jar bytes\n")
        candidate = self._manifest_commit(repository, "candidate", b"candidate jar bytes differ\n")
        command = [sys.executable, str(SAFETY_HELPER), "server-mod-manifest", "--repository", str(repository)]
        prior_result = self._run([*command, "--revision", prior])
        candidate_result = self._run([*command, "--revision", candidate])
        self.assertEqual(prior_result.returncode, 0, prior_result.stderr)
        self.assertEqual(candidate_result.returncode, 0, candidate_result.stderr)
        prior_manifest = json.loads(prior_result.stdout)
        candidate_manifest = json.loads(candidate_result.stdout)
        self.assertEqual([record["filename"] for record in prior_manifest], ["prior.jar"])
        self.assertEqual([record["filename"] for record in candidate_manifest], ["candidate.jar"])
        self.assertNotEqual(prior_manifest, candidate_manifest)
        global PRIOR_SHA, CURRENT_SHA
        saved_prior, saved_current = PRIOR_SHA, CURRENT_SHA
        PRIOR_SHA, CURRENT_SHA = prior, candidate
        self.addCleanup(lambda: globals().update(PRIOR_SHA=saved_prior, CURRENT_SHA=saved_current))
        _, snapshots, data, common = self._state_fixture()
        transaction_id = self._create_authority(
            snapshots,
            data,
            common,
            candidate_manifest=json.dumps(candidate_manifest),
            prior_manifest=json.dumps(prior_manifest),
        )
        for release_sha, expected in ((candidate, candidate_manifest), (prior, prior_manifest)):
            selected = self._run(
                [
                    sys.executable,
                    str(SAFETY_HELPER),
                    "authority-server-mod-manifest",
                    *common,
                    "--release-sha",
                    release_sha,
                ]
            )
            self.assertEqual(selected.returncode, 0, selected.stderr)
            self.assertEqual(json.loads(selected.stdout), expected)
        self.assertEqual(self._status(common, "transaction_id").stdout.strip(), transaction_id)

    def test_i2_immutable_manifest_accepts_pack_managed_server_jar_names(self) -> None:
        revision = self._git(ROOT, "rev-parse", "HEAD")
        result = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "server-mod-manifest",
                "--repository",
                str(ROOT),
                "--revision",
                revision,
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        filenames = [record["filename"] for record in json.loads(result.stdout)]
        self.assertTrue(any("+" in filename or " " in filename for filename in filenames))

    def test_i2_transaction_selects_prior_manifest_during_automatic_rollback(self) -> None:
        harness = quest_safe_tests.QuestSafeUpdateTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        candidate_manifest = json.dumps(
            [
                {
                    "filename": "candidate.jar",
                    "hash_format": "sha256",
                    "hash": "c" * 64,
                    "size": 1,
                }
            ],
            separators=(",", ":"),
        )
        prior_manifest = json.dumps(
            [
                {
                    "filename": "prior.jar",
                    "hash_format": "sha256",
                    "hash": "d" * 64,
                    "size": 2,
                }
            ],
            separators=(",", ":"),
        )
        result = harness._run(
            quest_safe_tests.CURRENT_SHA,
            "--confirm",
            environment={
                "FAKE_CANDIDATE_SERVER_MOD_MANIFEST": candidate_manifest,
                "FAKE_PRIOR_SERVER_MOD_MANIFEST": prior_manifest,
                "FAKE_PROGRESS_FAIL_AT": "1",
            },
        )
        self.assertNotEqual(result.returncode, 0)
        rendered_events = "\n".join(harness._events())
        self.assertIn("candidate.jar", rendered_events)
        self.assertIn("prior.jar", rendered_events)
        self.assertIn("checkout-reconcile", rendered_events)

    def test_i1_i2_recovery_uses_durable_prior_checkout_and_manifest_selection(self) -> None:
        source = RECOVERY_HELPER.read_text(encoding="utf-8")
        self.assertIn("--checkout-target-sha \"$prior_sha\"", source)
        self.assertIn("checkout-reconcile --repository", source)
        self.assertIn("authority-server-mod-manifest --release-sha \"$prior_sha\"", source)
        self.assertIn("--server-mod-manifest-json \"$prior_server_mods\"", source)

    def test_i3_live_verify_uses_exact_container_logs_not_mutable_host_mtime(self) -> None:
        repository, data, revision = self._live_fixture()
        environment = self._docker_fixture(
            f"""
            #!/usr/bin/env python3
            import json
            import sys
            arguments = sys.argv[1:]
            if arguments[0] == "inspect":
                print(json.dumps([{{
                    "Id": "{CONTAINER_ID}",
                    "State": {{
                        "Running": True,
                        "Status": "running",
                        "StartedAt": "{CONTAINER_START}",
                        "Health": {{"Status": "healthy"}},
                    }},
                }}]))
                raise SystemExit(0)
            if arguments[0] == "logs":
                print("{CONTAINER_START} unrelated candidate output")
                raise SystemExit(0)
            raise SystemExit(90)
            """
        )
        result = self._run(
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
                CONTAINER_ID,
                "--started-at",
                CONTAINER_START,
                "--data-owner-uid",
                str(os.getuid()),
                "--data-group-gid",
                str(os.getgid()),
            ],
            environment=environment,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"container.*log|quest.*evidence")

    def test_i4_authority_deletion_requires_durable_cleanup_complete_phase(self) -> None:
        state, snapshots, data, common = self._state_fixture()
        transaction_id = self._create_authority(snapshots, data, common)
        premature = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-complete",
                *common,
                "--transaction-id",
                transaction_id,
            ]
        )
        self.assertNotEqual(premature.returncode, 0)
        self.assertTrue((state / "state").is_file())
        marked = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-update",
                *common,
                "--transaction-id",
                transaction_id,
                "--status",
                "terminal",
                "--phase",
                "cleanup-complete",
            ]
        )
        self.assertEqual(marked.returncode, 0, marked.stderr)
        completed = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-complete",
                *common,
                "--transaction-id",
                transaction_id,
            ]
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse((state / "state").exists())

    def _health_environment(self, mode: str) -> tuple[dict[str, str], Path]:
        counter = self.temp_path / f"health-{mode}.count"
        environment = self._docker_fixture(
            f"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import sys
            counter = pathlib.Path(os.environ["FAKE_HEALTH_COUNTER"])
            count = int(counter.read_text() if counter.exists() else "0") + 1
            counter.write_text(str(count))
            mode = os.environ["FAKE_HEALTH_MODE"]
            if mode == "transient" and count == 1:
                print("temporary inspect failure", file=sys.stderr)
                raise SystemExit(1)
            status = "starting"
            if mode == "delay" and count >= 2:
                status = "healthy"
            elif mode == "transient" and count >= 2:
                status = "healthy"
            elif mode == "unhealthy":
                status = "unhealthy"
            print(json.dumps([{{
                "Id": "{CONTAINER_ID}",
                "State": {{"Running": True, "Status": "running", "Health": {{"Status": status}}}},
            }}]))
            """
        )
        environment.update({"FAKE_HEALTH_COUNTER": str(counter), "FAKE_HEALTH_MODE": mode})
        return environment, counter

    def _health_wait(self, mode: str, timeout: str = "1") -> subprocess.CompletedProcess[str]:
        environment, _ = self._health_environment(mode)
        return self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "container-health-wait",
                "--container-id",
                CONTAINER_ID,
                "--timeout",
                timeout,
                "--poll-interval",
                "0",
            ],
            environment=environment,
        )

    def test_i5_shared_health_wait_accepts_delayed_health(self) -> None:
        result = self._health_wait("delay")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_i5_shared_health_wait_retries_transient_inspection(self) -> None:
        result = self._health_wait("transient")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_i5_shared_health_wait_rejects_unhealthy_container(self) -> None:
        result = self._health_wait("unhealthy")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unhealthy", result.stderr.lower())

    def test_i5_shared_health_wait_times_out_starting_container(self) -> None:
        result = self._health_wait("starting", timeout="0")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed out", result.stderr.lower())

    def test_i5_every_start_path_uses_one_shared_backup_wait(self) -> None:
        contract = CONTRACT.read_text(encoding="utf-8")
        self.assertIn("afterlight_wait_container_healthy", contract)
        for path in (SERVER_OPERATOR, SAFE_UPDATE, RECOVERY_HELPER):
            source = path.read_text(encoding="utf-8")
            self.assertIn("afterlight_wait_container_healthy", source)
        self.assertNotIn("wait_healthy()", SERVER_OPERATOR.read_text(encoding="utf-8"))
        self.assertNotIn("wait_healthy()", SAFE_UPDATE.read_text(encoding="utf-8"))

    def _firewall_environment(self, mode: str) -> dict[str, str]:
        state = self.temp_path / f"firewall-{mode}.state"
        environment = self._docker_fixture(
            r"""
            #!/usr/bin/env bash
            exit 90
            """
        )
        fake_bin = Path(environment["PATH"].split(":", 1)[0])
        self._write_executable(
            fake_bin / "iptables",
            r"""
            #!/usr/bin/env python3
            import os
            import pathlib
            import sys
            import time
            arguments = sys.argv[1:]
            mode = os.environ["FAKE_FIREWALL_MODE"]
            state = pathlib.Path(os.environ["FAKE_FIREWALL_FILE"])
            comment = os.environ["FAKE_GATE_COMMENT"]
            if mode == "timeout":
                time.sleep(2)
            if arguments[:3] == ["-w", "-S", "DOCKER-USER"]:
                if mode == "missing-chain":
                    print("iptables: No chain/target/match by that name.", file=sys.stderr)
                    raise SystemExit(1)
                if mode == "permission":
                    print("Permission denied", file=sys.stderr)
                    raise SystemExit(4)
                if mode == "backend":
                    print("backend unavailable", file=sys.stderr)
                    raise SystemExit(2)
                if mode == "present" and not state.exists():
                    print(
                        f"-A DOCKER-USER -p tcp -m tcp --dport 25565 -m conntrack --ctstate NEW "
                        f"-m comment --comment {comment} -j REJECT"
                    )
                raise SystemExit(0)
            if "-D" in arguments and mode == "present":
                state.write_text("deleted")
                raise SystemExit(0)
            raise SystemExit(90)
            """,
        )
        environment.update(
            {
                "FAKE_FIREWALL_MODE": mode,
                "FAKE_FIREWALL_FILE": str(state),
                "FAKE_GATE_COMMENT": f"afterlight-quest-update-{CURRENT_SHA}-{'1' * 32}",
            }
        )
        return environment

    def _remove_gate(self, mode: str) -> subprocess.CompletedProcess[str]:
        environment = self._firewall_environment(mode)
        return self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "firewall-gate-remove",
                "--comment",
                environment["FAKE_GATE_COMMENT"],
                "--timeout",
                "0.5",
            ],
            environment=environment,
        )

    def test_i6_present_or_exactly_absent_gate_removal_is_idempotent(self) -> None:
        present = self._remove_gate("present")
        absent = self._remove_gate("absent")
        self.assertEqual(present.returncode, 0, present.stderr)
        self.assertEqual(absent.returncode, 0, absent.stderr)

    def test_i6_missing_chain_is_not_treated_as_absence(self) -> None:
        result = self._remove_gate("missing-chain")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inspection failed", result.stderr.lower())

    def test_i6_permission_error_is_not_treated_as_absence(self) -> None:
        result = self._remove_gate("permission")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inspection failed", result.stderr.lower())

    def test_i6_backend_error_is_not_treated_as_absence(self) -> None:
        result = self._remove_gate("backend")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inspection failed", result.stderr.lower())

    def test_i6_timeout_is_not_treated_as_absence(self) -> None:
        result = self._remove_gate("timeout")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("timed out", result.stderr.lower())

    def test_i4_i6_terminal_cleanup_retains_authority_then_resumes(self) -> None:
        harness = friend_server_tests.FriendServerTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        marker = harness.data_dir / ".afterlight-pack-sha"
        marker.write_text(f"{PRIOR_SHA}\n", encoding="ascii")
        marker.chmod(0o600)
        common = [
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
                str(harness.snapshot_root),
                "--receipt-sha256",
                "b" * 64,
                "--data-root",
                str(harness.data_dir),
                "--data-owner-uid",
                str(os.getuid()),
                "--data-group-gid",
                str(os.getgid()),
                "--candidate-server-mod-manifest-json",
                "[]",
                "--prior-server-mod-manifest-json",
                "[]",
            ]
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        transaction_id = created.stdout.strip()
        terminal = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-update",
                *common,
                "--transaction-id",
                transaction_id,
                "--status",
                "terminal",
                "--phase",
                "transaction-verified",
            ]
        )
        self.assertEqual(terminal.returncode, 0, terminal.stderr)

        systemctl_state = harness.temp_path / "systemctl-failed-once"
        harness._write_executable(
            "docker",
            r"""
            #!/usr/bin/env bash
            set -u
            if [ "${1:-}" = compose ]; then
              shift
              while [ "$#" -gt 0 ]; do
                case "$1" in --project-name|--env-file|-f) shift 2 ;; *) break ;; esac
              done
              if [ "${1:-}" = ps ] && [ "${2:-}" = -aq ]; then
                printf '%s-id\n' "${3:?service}"
                exit 0
              fi
            elif [ "${1:-}" = update ] && [ "${2:-}" = --restart=unless-stopped ]; then
              exit 0
            elif [ "${1:-}" = inspect ] && [ "${2:-}" = --format ]; then
              printf 'unless-stopped\n'
              exit 0
            fi
            printf 'unexpected docker command: %s\n' "$*" >&2
            exit 90
            """,
        )
        harness._write_executable(
            "iptables",
            r"""
            #!/usr/bin/env bash
            if [ "$*" = "-w -S DOCKER-USER" ]; then exit 0; fi
            printf 'unexpected iptables command: %s\n' "$*" >&2
            exit 90
            """,
        )
        harness._write_executable(
            "systemctl",
            r"""
            #!/usr/bin/env bash
            set -u
            if [ "${1:-}" = reset-failed ]; then
              if [ ! -e "$FAKE_SYSTEMCTL_STATE" ]; then
                : > "$FAKE_SYSTEMCTL_STATE"
                printf 'injected systemd reconciliation failure\n' >&2
                exit 1
              fi
              exit 0
            fi
            case "$*" in
              "enable afterlight-quarantine-gate.service"|\
              "is-enabled --quiet afterlight-quarantine-gate.service"|\
              "enable --now afterlight-maintenance.timer"|\
              "is-enabled --quiet afterlight-maintenance.timer"|\
              "is-active --quiet afterlight-maintenance.timer") exit 0 ;;
            esac
            printf 'unexpected systemctl command: %s\n' "$*" >&2
            exit 90
            """,
        )
        environment = harness.environment | {
            "AFTERLIGHT_COMMAND_TIMEOUT": "2",
            "FAKE_SYSTEMCTL_STATE": str(systemctl_state),
        }
        command = ["/bin/bash", str(FINALIZER), "--transaction-id", transaction_id]
        first = self._run(command, environment=environment)
        self.assertNotEqual(first.returncode, 0)
        self.assertTrue((harness.quarantine_dir / "state").is_file())
        phase = self._run(
            [sys.executable, str(SAFETY_HELPER), "authority-status", *common, "--field", "phase"]
        )
        self.assertEqual(phase.returncode, 0, phase.stderr)
        self.assertEqual(phase.stdout.strip(), "cleanup-systemd")

        second = self._run(command, environment=environment)
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertFalse((harness.quarantine_dir / "state").exists())

    def test_m1_zero_identity_and_login_capable_account_are_rejected(self) -> None:
        harness = friend_server_tests.FriendServerTests(methodName="runTest")
        harness.setUp()
        self.addCleanup(harness.doCleanups)
        contents = harness.env_file.read_text(encoding="utf-8")
        contents = contents.replace(f"AFTERLIGHT_DATA_UID={os.getuid()}", "AFTERLIGHT_DATA_UID=0")
        contents = contents.replace(f"AFTERLIGHT_DATA_GID={os.getgid()}", "AFTERLIGHT_DATA_GID=0")
        harness.env_file.write_text(contents, encoding="utf-8")
        zero = harness._run_operator("doctor")
        self.assertNotEqual(zero.returncode, 0)
        self.assertRegex(zero.stderr.lower(), r"nonzero|unprivileged")

        fake_bin = self.temp_path / "identity-bin"
        self._write_executable(
            fake_bin / "getent",
            r"""
            #!/usr/bin/env bash
            printf '%s\n' "afterlight:x:1234:1234::/nonexistent:${FAKE_AFTERLIGHT_SHELL}"
            """,
        )
        command = [
            "/bin/bash",
            "-c",
            f"source {CONTRACT}; AFTERLIGHT_CONTRACT_MODE=production; afterlight_validate_data_identity 1234 1234",
        ]
        correct = self._run(
            command,
            environment={
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "FAKE_AFTERLIGHT_SHELL": "/usr/sbin/nologin",
            },
        )
        self.assertEqual(correct.returncode, 0, correct.stderr)
        login_capable = self._run(
            command,
            environment={
                "PATH": f"{fake_bin}:{os.environ['PATH']}",
                "FAKE_AFTERLIGHT_SHELL": "/bin/bash",
            },
        )
        self.assertNotEqual(login_capable.returncode, 0)
        self.assertIn("non-login", login_capable.stderr.lower())


if __name__ == "__main__":
    unittest.main()
