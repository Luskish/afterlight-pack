from __future__ import annotations

import argparse
import hashlib
import json
import importlib.util
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SAFETY_HELPER = ROOT / "server" / "afterlight-safety.py"
RECOVERY_HELPER = ROOT / "server" / "afterlight-quarantine-recover.sh"
CURRENT_SHA = "3" * 40
PRIOR_SHA = "2" * 40
CONTAINER_ID = "a" * 64
CONTAINER_START = "2026-08-13T12:00:00.000000000Z"


class Task9Rereview4Tests(unittest.TestCase):
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

    def _live_fixture(self) -> tuple[Path, Path, str, bytes]:
        repository = self.temp_path / "live-repository"
        quests = repository / "config" / "ftbquests" / "quests"
        mods = repository / "mods"
        tools = repository / "tools"
        quests.mkdir(parents=True)
        mods.mkdir()
        tools.mkdir()
        jar_payload = b"accepted server jar bytes\n"
        jar_hash = hashlib.sha512(jar_payload).hexdigest()
        (quests / "chapter.snbt").write_text("{id:'fixture'}\n", encoding="utf-8")
        (mods / "fixture.pw.toml").write_text(
            'name = "Fixture"\n'
            'filename = "fixture.jar"\n'
            'side = "both"\n\n'
            '[download]\n'
            'url = "https://example.invalid/fixture.jar"\n'
            'hash-format = "sha512"\n'
            f'hash = "{jar_hash}"\n',
            encoding="utf-8",
        )
        (tools / "server-mod-manifest-lock.json").write_text(
            json.dumps(
                {
                    "format": 1,
                    "files": [
                        {
                            "filename": "fixture.jar",
                            "hash": jar_hash,
                            "hash_format": "sha512",
                            "metadata_path": "mods/fixture.pw.toml",
                            "size": len(jar_payload),
                        }
                    ],
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
        data = self.temp_path / "live-data"
        shutil.copytree(quests, data / "config" / "ftbquests" / "quests")
        (data / "mods").mkdir(parents=True)
        (data / "mods" / "fixture.jar").write_bytes(jar_payload)
        marker = data / ".afterlight-pack-sha"
        marker.write_text(f"{revision}\n", encoding="ascii")
        marker.chmod(0o600)
        return repository, data, revision, jar_payload

    def _docker_environment(self, inspect_source: str | None = None) -> dict[str, str]:
        fake_bin = self.temp_path / "docker-bin"
        source = inspect_source or f"""
            #!/usr/bin/env python3
            import json
            import sys
            if sys.argv[1] == "inspect":
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
            if sys.argv[1] == "logs":
                print("Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables")
                raise SystemExit(0)
            raise SystemExit(90)
        """
        self._write_executable(fake_bin / "docker", source)
        return {"PATH": f"{fake_bin}:{os.environ['PATH']}"}

    def _live_verify(
        self,
        repository: Path,
        data: Path,
        revision: str,
        *,
        environment: dict[str, str],
    ) -> subprocess.CompletedProcess[str]:
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

    def _post_log_drift_result(
        self,
        *,
        second_id: str = CONTAINER_ID,
        second_running: bool = True,
        second_status: str = "running",
        second_start: str = CONTAINER_START,
    ) -> tuple[subprocess.CompletedProcess[str], int]:
        repository, data, revision, _ = self._live_fixture()
        counter = self.temp_path / "inspect-count"
        environment = self._docker_environment(
            f"""
            #!/usr/bin/env python3
            import json
            import os
            import pathlib
            import sys
            counter = pathlib.Path(os.environ["FAKE_DOCKER_COUNTER"])
            if sys.argv[1] == "inspect":
                count = int(counter.read_text()) if counter.exists() else 0
                counter.write_text(str(count + 1))
                if count == 0:
                    record = {{
                        "Id": "{CONTAINER_ID}",
                        "State": {{
                            "Running": True,
                            "Status": "running",
                            "StartedAt": "{CONTAINER_START}",
                            "Health": {{"Status": "healthy"}},
                        }},
                    }}
                else:
                    record = {{
                        "Id": "{second_id}",
                        "State": {{
                            "Running": {str(second_running)},
                            "Status": "{second_status}",
                            "StartedAt": "{second_start}",
                            "Health": {{"Status": "healthy"}},
                        }},
                    }}
                print(json.dumps([record]))
                raise SystemExit(0)
            if sys.argv[1] == "logs":
                print("Loaded 1 chapter groups, 2 chapters, 3 quests, 1 reward tables")
                raise SystemExit(0)
            raise SystemExit(90)
            """
        )
        environment["FAKE_DOCKER_COUNTER"] = str(counter)
        result = self._live_verify(
            repository,
            data,
            revision,
            environment=environment,
        )
        count = int(counter.read_text(encoding="utf-8"))
        return result, count

    def _state_fixture(self, prior_sha: str = PRIOR_SHA) -> tuple[Path, Path, Path, list[str]]:
        state = self.temp_path / "state"
        snapshots = self.temp_path / "snapshots"
        data = self.temp_path / "data"
        snapshots.mkdir(mode=0o700)
        data.mkdir(mode=0o700)
        marker = data / ".afterlight-pack-sha"
        marker.write_text(f"{prior_sha}\n", encoding="ascii")
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

    def _authority_create(
        self,
        snapshots: Path,
        data: Path,
        common: list[str],
        *,
        expected_sha: str,
        prior_sha: str,
        candidate_manifest: str,
        prior_manifest: str,
    ) -> subprocess.CompletedProcess[str]:
        return self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-create",
                *common,
                "--expected-sha",
                expected_sha,
                "--prior-sha",
                prior_sha,
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

    def test_i1_current_pack_authority_round_trips_with_explicit_bounds(self) -> None:
        revision = self._run(["git", "rev-parse", "HEAD"]).stdout.strip()
        manifest_result = self._run(
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
        self.assertEqual(manifest_result.returncode, 0, manifest_result.stderr)
        self.assertEqual(len(json.loads(manifest_result.stdout)), 159)
        state, snapshots, data, common = self._state_fixture(revision)
        created = self._authority_create(
            snapshots,
            data,
            common,
            expected_sha=revision,
            prior_sha=revision,
            candidate_manifest=manifest_result.stdout,
            prior_manifest=manifest_result.stdout,
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        self.assertGreater((state / "state").stat().st_size, 64 * 1024)
        status = self._run(
            [
                sys.executable,
                str(SAFETY_HELPER),
                "authority-status",
                *common,
                "--field",
                "transaction_id",
            ]
        )
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout.strip(), created.stdout.strip())

    def test_i1_manifest_record_bound_rejects_oversized_authority_before_write(self) -> None:
        state, snapshots, data, common = self._state_fixture()
        oversized_manifest = [
            {
                "filename": f"fixture-{index:04d}.jar",
                "hash_format": "sha1",
                "hash": f"{index:040x}",
                "size": 1,
            }
            for index in range(513)
        ]
        created = self._authority_create(
            snapshots,
            data,
            common,
            expected_sha=CURRENT_SHA,
            prior_sha=PRIOR_SHA,
            candidate_manifest=json.dumps(oversized_manifest),
            prior_manifest="[]",
        )
        self.assertNotEqual(created.returncode, 0)
        self.assertRegex(created.stderr.lower(), r"manifest.*(?:record|size|limit)")
        self.assertFalse((state / "state").exists())

    def test_i1_oversized_state_file_remains_fail_closed(self) -> None:
        state, snapshots, data, common = self._state_fixture()
        created = self._authority_create(
            snapshots,
            data,
            common,
            expected_sha=CURRENT_SHA,
            prior_sha=PRIOR_SHA,
            candidate_manifest="[]",
            prior_manifest="[]",
        )
        self.assertEqual(created.returncode, 0, created.stderr)
        with (state / "state").open("ab") as state_file:
            state_file.write(b" " * (2 * 1024 * 1024))
        status = self._run(
            [sys.executable, str(SAFETY_HELPER), "authority-status", *common]
        )
        self.assertNotEqual(status.returncode, 0)
        self.assertIn("size limit", status.stderr.lower())

    def test_i2_quest_semantic_hash_ignores_intentional_directory_ownership(self) -> None:
        expected = self.temp_path / "expected-quests"
        installed = self.temp_path / "installed-quests"
        for root in (expected, installed):
            (root / "chapter").mkdir(parents=True)
            (root / "chapter" / "quest.snbt").write_text(
                "{id:'same'}\n",
                encoding="utf-8",
            )
        spec = importlib.util.spec_from_file_location(
            "afterlight_safety_rereview4_i2",
            SAFETY_HELPER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        installed_directories = {
            (path.lstat().st_dev, path.lstat().st_ino)
            for path in (installed, *sorted(installed.rglob("*")))
            if path.is_dir()
        }
        original_stat = os.stat
        original_lstat = os.lstat
        original_fstat = os.fstat

        def replace_owner(metadata: os.stat_result) -> os.stat_result:
            if (metadata.st_dev, metadata.st_ino) not in installed_directories:
                return metadata
            values = list(metadata)
            values[4] = metadata.st_uid + 1000
            values[5] = metadata.st_gid + 1000
            return os.stat_result(values)

        def simulated_stat(*arguments, **keywords) -> os.stat_result:
            return replace_owner(original_stat(*arguments, **keywords))

        def simulated_lstat(*arguments, **keywords) -> os.stat_result:
            return replace_owner(original_lstat(*arguments, **keywords))

        def simulated_fstat(*arguments, **keywords) -> os.stat_result:
            return replace_owner(original_fstat(*arguments, **keywords))

        expected_hash = module.hash_tree(expected)
        with (
            mock.patch.object(module.os, "stat", simulated_stat),
            mock.patch.object(module.os, "lstat", simulated_lstat),
            mock.patch.object(module.os, "fstat", simulated_fstat),
        ):
            installed_hash = module.hash_tree(installed)
        self.assertEqual(installed_hash, expected_hash)

    def test_i3_live_mod_attestation_rejects_symlinked_mod_root(self) -> None:
        repository, data, revision, _ = self._live_fixture()
        mods = data / "mods"
        target = data / "mods-real"
        mods.rename(target)
        mods.symlink_to(target, target_is_directory=True)
        result = self._live_verify(
            repository,
            data,
            revision,
            environment=self._docker_environment(),
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"mod.*(?:root|directory|link|open)")

    def test_i3_live_mod_attestation_rejects_root_replacement_during_digest(self) -> None:
        repository, data, revision, jar_payload = self._live_fixture()
        replacement = data / "mods-replacement"
        replacement.mkdir()
        (replacement / "fixture.jar").write_bytes(jar_payload)
        displaced = data / "mods-displaced"
        spec = importlib.util.spec_from_file_location(
            "afterlight_safety_rereview4_i3",
            SAFETY_HELPER,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original_hash_new = module.hashlib.new
        swapped = False

        def replace_mod_root(name: str, *arguments: object, **keywords: object):
            nonlocal swapped
            if not swapped:
                (data / "mods").rename(displaced)
                replacement.rename(data / "mods")
                swapped = True
            return original_hash_new(name, *arguments, **keywords)

        arguments = argparse.Namespace(
            expected_sha=revision,
            repository=repository,
            data=data,
            data_owner_uid=os.getuid(),
            data_group_gid=os.getgid(),
            server_mod_manifest_json=None,
            container_id=CONTAINER_ID,
            started_at=CONTAINER_START,
        )
        with mock.patch.dict(os.environ, self._docker_environment(), clear=False):
            with mock.patch.object(module.hashlib, "new", replace_mod_root):
                with self.assertRaisesRegex(module.SafetyError, r"mod.*(?:root|identity|changed)"):
                    module.command_live_verify(arguments)

    def test_i4_live_log_evidence_rejects_container_restart_during_acquisition(self) -> None:
        result, inspect_count = self._post_log_drift_result(
            second_start="2026-08-13T12:05:00.000000000Z",
        )
        self.assertEqual(inspect_count, 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"container.*(?:start|identity|restart)")

    def test_i4_live_log_evidence_rejects_container_exit_during_acquisition(self) -> None:
        result, inspect_count = self._post_log_drift_result(
            second_running=False,
            second_status="exited",
        )
        self.assertEqual(inspect_count, 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"container.*(?:state|healthy|running|exit)")

    def test_i4_live_log_evidence_rejects_identity_drift_during_acquisition(self) -> None:
        result, inspect_count = self._post_log_drift_result(second_id="b" * 64)
        self.assertEqual(inspect_count, 2)
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr.lower(), r"container.*identity")

    def test_i5_recovery_start_bound_covers_both_operator_health_waits(self) -> None:
        source = RECOVERY_HELPER.read_text(encoding="utf-8")
        self.assertIn(
            'local timeout=$((COMMAND_TIMEOUT + 2 * HEALTH_TIMEOUT))',
            source,
        )
        self.assertIn(
            'run_bounded_with_timeout "$timeout" "$OPERATOR" start',
            source,
        )
        self.assertEqual(source.count("run_operator_start"), 3)
        self.assertNotIn('run_bounded "$OPERATOR" start', source)


if __name__ == "__main__":
    unittest.main()
