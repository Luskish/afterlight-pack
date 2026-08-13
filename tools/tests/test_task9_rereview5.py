from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

from tools.tests import test_task9_rereview4 as rereview4_tests


ROOT = Path(__file__).resolve().parents[2]
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
RECOVERY_HELPER = ROOT / "server" / "afterlight-quarantine-recover.sh"
PRIOR_SHA = "2" * 40


class Task9Rereview5Tests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.temp_path = Path(self.temporary_directory.name).resolve()

    def _load_safety(self, suffix: str):
        spec = importlib.util.spec_from_file_location(
            f"afterlight_safety_rereview5_{suffix}",
            SAFETY_HELPER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _write_executable(self, path: Path, source: str) -> None:
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _quest_trees(self) -> tuple[Path, Path]:
        repository = self.temp_path / "repository-quests"
        runtime = self.temp_path / "runtime-quests"
        (repository / "chapter").mkdir(parents=True)
        (repository / "chapter" / "quest.snbt").write_text(
            "{id:'same'}\n",
            encoding="utf-8",
        )
        shutil.copytree(repository, runtime)
        return repository, runtime

    def _tree_inodes(self, root: Path) -> set[tuple[int, int]]:
        return {
            (path.lstat().st_dev, path.lstat().st_ino)
            for path in (root, *sorted(root.rglob("*")))
        }

    @contextmanager
    def _simulated_ownership(
        self,
        module,
        owners: dict[tuple[int, int], tuple[int, int]],
    ):
        real_stat = os.stat
        real_lstat = os.lstat
        real_fstat = os.fstat

        def replace(metadata: os.stat_result) -> os.stat_result:
            owner = owners.get((metadata.st_dev, metadata.st_ino))
            if owner is None:
                return metadata
            values = list(metadata)
            values[4], values[5] = owner
            return os.stat_result(values)

        def simulated_stat(*arguments, **keywords):
            return replace(real_stat(*arguments, **keywords))

        def simulated_lstat(*arguments, **keywords):
            return replace(real_lstat(*arguments, **keywords))

        def simulated_fstat(*arguments, **keywords):
            return replace(real_fstat(*arguments, **keywords))

        with (
            mock.patch.object(module.os, "stat", simulated_stat),
            mock.patch.object(module.os, "lstat", simulated_lstat),
            mock.patch.object(module.os, "fstat", simulated_fstat),
        ):
            yield

    def test_i1_semantic_quest_equality_allows_distinct_valid_side_owners(self) -> None:
        repository, runtime = self._quest_trees()
        module = self._load_safety("i1_distinct_owners")
        runtime_uid = os.getuid() + 1000
        runtime_gid = os.getgid() + 1000
        owners = {
            inode: (runtime_uid, runtime_gid)
            for inode in self._tree_inodes(runtime)
        }

        repository_digest = module.hash_tree(repository)
        with self._simulated_ownership(module, owners):
            runtime_digest = module.hash_tree(
                runtime,
                owner_uid=runtime_uid,
                group_gid=runtime_gid,
            )

        self.assertEqual(runtime_digest, repository_digest)

    def test_i1_runtime_quest_directory_requires_runtime_owner(self) -> None:
        _, runtime = self._quest_trees()
        module = self._load_safety("i1_directory_owner")
        runtime_uid = os.getuid() + 1000
        runtime_gid = os.getgid() + 1000
        owners = {
            inode: (runtime_uid, runtime_gid)
            for inode in self._tree_inodes(runtime)
        }
        directory = runtime / "chapter"
        owners[(directory.lstat().st_dev, directory.lstat().st_ino)] = (
            runtime_uid + 1,
            runtime_gid,
        )

        with self._simulated_ownership(module, owners):
            with self.assertRaisesRegex(module.SafetyError, r"tree.*owner|owner.*tree"):
                module.hash_tree(
                    runtime,
                    owner_uid=runtime_uid,
                    group_gid=runtime_gid,
                )

    def test_i1_runtime_quest_file_requires_runtime_owner(self) -> None:
        _, runtime = self._quest_trees()
        module = self._load_safety("i1_file_owner")
        runtime_uid = os.getuid() + 1000
        runtime_gid = os.getgid() + 1000
        owners = {
            inode: (runtime_uid, runtime_gid)
            for inode in self._tree_inodes(runtime)
        }
        quest = runtime / "chapter" / "quest.snbt"
        owners[(quest.lstat().st_dev, quest.lstat().st_ino)] = (
            runtime_uid + 1,
            runtime_gid,
        )

        with self._simulated_ownership(module, owners):
            with self.assertRaisesRegex(module.SafetyError, r"tree.*owner|owner.*tree"):
                module.hash_tree(
                    runtime,
                    owner_uid=runtime_uid,
                    group_gid=runtime_gid,
                )

    def test_i1_quest_file_same_name_replacement_is_rejected(self) -> None:
        _, runtime = self._quest_trees()
        module = self._load_safety("i1_file_replacement")
        victim = runtime / "chapter" / "quest.snbt"
        displaced = self.temp_path / "displaced.snbt"
        replacement = self.temp_path / "replacement.snbt"
        replacement.write_bytes(victim.read_bytes())
        victim_metadata = victim.stat()
        parent_metadata = victim.parent.stat()
        replacement.chmod(stat.S_IMODE(victim_metadata.st_mode))
        os.utime(
            replacement,
            ns=(victim_metadata.st_atime_ns, victim_metadata.st_mtime_ns),
        )
        real_digest = module.file_digest_from_fd
        replaced = False

        def digest_then_replace(descriptor: int) -> str:
            nonlocal replaced
            digest = real_digest(descriptor)
            if not replaced:
                replaced = True
                victim.rename(displaced)
                replacement.rename(victim)
                os.utime(
                    victim,
                    ns=(victim_metadata.st_atime_ns, victim_metadata.st_mtime_ns),
                )
                os.utime(
                    victim.parent,
                    ns=(parent_metadata.st_atime_ns, parent_metadata.st_mtime_ns),
                )
            return digest

        with mock.patch.object(module, "file_digest_from_fd", digest_then_replace):
            with self.assertRaisesRegex(module.SafetyError, r"tree.*(?:path|identity|changed)"):
                module.hash_tree(
                    runtime,
                    owner_uid=os.getuid(),
                    group_gid=os.getgid(),
                )

    def test_i1_quest_root_same_name_replacement_is_rejected(self) -> None:
        _, runtime = self._quest_trees()
        module = self._load_safety("i1_root_replacement")
        displaced = self.temp_path / "runtime-displaced"
        replacement = self.temp_path / "runtime-replacement"
        shutil.copytree(runtime, replacement)
        parent_metadata = runtime.parent.stat()
        real_digest = module.file_digest_from_fd
        replaced = False

        def digest_then_replace(descriptor: int) -> str:
            nonlocal replaced
            digest = real_digest(descriptor)
            if not replaced:
                replaced = True
                runtime.rename(displaced)
                replacement.rename(runtime)
                os.utime(
                    runtime.parent,
                    ns=(parent_metadata.st_atime_ns, parent_metadata.st_mtime_ns),
                )
            return digest

        with mock.patch.object(module, "file_digest_from_fd", digest_then_replace):
            with self.assertRaisesRegex(module.SafetyError, r"tree.*(?:root|path|identity|changed)"):
                module.hash_tree(
                    runtime,
                    owner_uid=os.getuid(),
                    group_gid=os.getgid(),
                )

    def test_i2_live_mod_same_name_replacement_is_rejected(self) -> None:
        fixture = rereview4_tests.Task9Rereview4Tests(
            methodName="test_i3_live_mod_attestation_rejects_symlinked_mod_root"
        )
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        repository, data, revision, jar_payload = fixture._live_fixture()
        module = self._load_safety("i2_jar_replacement")
        victim = data / "mods" / "fixture.jar"
        displaced = fixture.temp_path / "fixture-displaced.jar"
        replacement = fixture.temp_path / "fixture-replacement.jar"
        replacement.write_bytes(jar_payload)
        victim_metadata = victim.stat()
        mods_metadata = victim.parent.stat()
        replacement.chmod(stat.S_IMODE(victim_metadata.st_mode))
        os.utime(
            replacement,
            ns=(victim_metadata.st_atime_ns, victim_metadata.st_mtime_ns),
        )
        original_hash_new = module.hashlib.new
        replaced = False

        class ReplacingDigest:
            def __init__(self, algorithm: str) -> None:
                self.digest = original_hash_new(algorithm)

            def update(self, payload: bytes) -> None:
                nonlocal replaced
                self.digest.update(payload)
                if not replaced:
                    replaced = True
                    victim.rename(displaced)
                    replacement.rename(victim)
                    os.utime(
                        victim,
                        ns=(victim_metadata.st_atime_ns, victim_metadata.st_mtime_ns),
                    )
                    os.utime(
                        victim.parent,
                        ns=(mods_metadata.st_atime_ns, mods_metadata.st_mtime_ns),
                    )

            def hexdigest(self) -> str:
                return self.digest.hexdigest()

        arguments = argparse.Namespace(
            expected_sha=revision,
            repository=repository,
            data=data,
            data_owner_uid=os.getuid(),
            data_group_gid=os.getgid(),
            server_mod_manifest_json=None,
            container_id=rereview4_tests.CONTAINER_ID,
            started_at=rereview4_tests.CONTAINER_START,
        )
        with mock.patch.dict(os.environ, fixture._docker_environment(), clear=False):
            with mock.patch.object(
                module.hashlib,
                "new",
                lambda algorithm: ReplacingDigest(algorithm),
            ):
                with self.assertRaisesRegex(
                    module.SafetyError,
                    r"mod.*(?:path|identity|changed|inventory)",
                ):
                    module.command_live_verify(arguments)

    def test_i3_recovery_outer_timeout_covers_executed_worst_case_budget(self) -> None:
        test_root = self.temp_path / "recovery"
        test_root.mkdir(mode=0o700)
        marker = test_root / ".afterlight-safety-test-contract"
        marker.write_text("AFTERLIGHT SAFETY TEST CONTRACT v1\n", encoding="utf-8")
        marker.chmod(0o600)
        for name in ("run", "quarantine", "snapshots", "data", "backups", "secrets"):
            (test_root / name).mkdir(mode=0o700)
        data_uid = os.getuid() if os.getuid() != 0 else 12345
        data_gid = os.getgid() if os.getgid() != 0 else 12345
        if os.geteuid() == 0:
            os.chown(test_root / "data", data_uid, data_gid)
        snapshot = test_root / "snapshots" / "transaction"
        (snapshot / "progress").mkdir(parents=True)
        (test_root / "server.env").write_text(
            f"DATA_DIR={test_root / 'data'}\n"
            f"AFTERLIGHT_DATA_UID={data_uid}\n"
            f"AFTERLIGHT_DATA_GID={data_gid}\n",
            encoding="utf-8",
        )
        event_log = test_root / "budget-events.jsonl"
        fake_helper = test_root / "fake-safety.py"
        self._write_executable(
            fake_helper,
            f"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import sys

            PRIOR_SHA = {PRIOR_SHA!r}
            SNAPSHOT = {str(snapshot)!r}
            MINECRAFT_ID = {'a' * 64!r}
            BACKUP_ID = {'b' * 64!r}
            STARTED_AT = "2026-08-13T12:00:00.000000000Z"
            log_path = pathlib.Path(os.environ["AFTERLIGHT_BUDGET_EVENT_LOG"])

            def record(payload):
                with log_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\\n")

            arguments = sys.argv[1:]
            command = arguments[0]
            if command == "lock-run":
                timeout = arguments[arguments.index("--timeout") + 1]
                grace = arguments[arguments.index("--termination-grace") + 1]
                child = arguments[arguments.index("--") + 1:]
                record({{"kind": "outer", "timeout": float(timeout), "grace": float(grace)}})
                descriptor = os.open("/dev/null", os.O_RDONLY)
                os.dup2(descriptor, 9)
                os.set_inheritable(9, True)
                environment = os.environ.copy()
                environment["AFTERLIGHT_LOCK_FD"] = "9"
                os.execvpe(child[0], child, environment)
            if command == "lock-verify":
                raise SystemExit(0)
            if command == "container-health-wait":
                timeout = arguments[arguments.index("--timeout") + 1]
                record({{"kind": "health", "timeout": float(timeout)}})
                raise SystemExit(0)
            if command != "run-command":
                raise SystemExit(90)
            timeout = arguments[arguments.index("--timeout") + 1]
            child = arguments[arguments.index("--") + 1:]
            record({{"kind": "bounded", "timeout": float(timeout), "command": child}})
            if child[0] == str(pathlib.Path(__file__).resolve()):
                nested = child[1]
                if nested == "authority-status":
                    field = child[child.index("--field") + 1]
                    values = {{
                        "transaction_id": "transaction",
                        "status": "quarantine",
                        "prior_sha": PRIOR_SHA,
                        "expected_sha": "3" * 40,
                        "snapshot_dir": SNAPSHOT,
                        "data_mutated": "True",
                    }}
                    print(values[field])
                elif nested == "authority-server-mod-manifest":
                    print("[]")
                elif nested == "release-marker-read":
                    print(PRIOR_SHA)
                raise SystemExit(0)
            if child[:2] == ["docker", "compose"] and "ps" in child:
                print(MINECRAFT_ID if child[-1] == "minecraft" else BACKUP_ID)
            elif child[:2] == ["docker", "inspect"]:
                print(STARTED_AT)
            raise SystemExit(0)
            """,
        )
        environment = {
            "AFTERLIGHT_SAFETY_TEST_ROOT": str(test_root),
            "AFTERLIGHT_SAFETY_HELPER": str(fake_helper),
            "AFTERLIGHT_OPERATOR": str(fake_helper),
            "AFTERLIGHT_PROGRESS_GUARD": str(fake_helper),
            "AFTERLIGHT_TRANSACTION_FINALIZER": str(fake_helper),
            "AFTERLIGHT_BUDGET_EVENT_LOG": str(event_log),
        }
        result = subprocess.run(
            ["/bin/bash", str(RECOVERY_HELPER), "--confirm"],
            cwd=ROOT,
            env=os.environ | environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        events = [json.loads(line) for line in event_log.read_text().splitlines()]
        outer = [event for event in events if event["kind"] == "outer"]
        bounded = [event for event in events if event["kind"] == "bounded"]
        health = [event for event in events if event["kind"] == "health"]
        self.assertEqual(len(outer), 1)
        self.assertEqual(len(bounded), 28)
        self.assertEqual(len(health), 2)
        self.assertEqual(sum(event["timeout"] == 1800 for event in bounded), 2)
        self.assertEqual(sum(event["timeout"] == 600 for event in bounded), 26)
        executed_budget = sum(event["timeout"] for event in bounded + health)
        self.assertEqual(outer[0]["timeout"], executed_budget + 5)
        self.assertEqual(outer[0]["grace"], 300)


if __name__ == "__main__":
    unittest.main()
