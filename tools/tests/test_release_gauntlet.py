import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


REQUIRED_GAUNTLET_TESTS = {
    "test_rejects_dirty_tree_noncommit_and_nonhead_sha",
    "test_creates_detached_worktree_for_exact_sha",
    "test_runs_tests_verify_boot_compose_shellcheck_and_two_builds_in_order",
    "test_compares_two_prism_archives_byte_for_byte",
    "test_failure_stops_before_copying_accepted_artifacts",
    "test_success_copies_public_and_private_outputs_with_transcript",
    "test_cleanup_removes_only_the_temporary_worktree",
}


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
GAUNTLET_SOURCE = REPOSITORY_ROOT / "tools" / "release-gauntlet.sh"
SHA = "0123456789abcdef0123456789abcdef01234567"


class ReleaseGauntletTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name) / "repository"
        self.root.mkdir()
        self.worktree_root = self.root.parent / "worktrees"
        self.log_path = self.root / "commands.log"
        self.fake_bin = self.root / "fake-bin"
        self.fake_bin.mkdir()
        self._write_fixture_repository()
        self._write_fake_commands()

    def _write(self, path, contents, executable=False):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
        if executable:
            path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _write_fixture_repository(self):
        (self.root / "tools").mkdir()
        shutil.copy2(GAUNTLET_SOURCE, self.root / "tools" / "release-gauntlet.sh")
        (self.root / "tools" / "release-gauntlet.sh").chmod(0o755)
        self._write(
            self.root / "pack.toml",
            "version = \"0.9.0-rc.1\"\n\n[versions]\nminecraft = \"1.21.1\"\nneoforge = \"21.1.248\"\n",
        )
        self._write(self.root / "index.toml", "hash-format = \"sha256\"\n")
        self._write(self.root / "tools" / "versions.env", "PATH_EXTRA=\nJAVA_HOME=${GAUNTLET_FAKE_JAVA_HOME:?}\n")
        self._write(self.root / "server" / ".env.example", "DATA_DIR=/tmp/data\nBACKUP_DIR=/tmp/backups\nSECRETS_DIR=/tmp/secrets\n")
        self._write(self.root / "server" / "docker-compose.yml", "services: {}\n")
        self._write(
            self.root / "tools" / "verify-pack.sh",
            "#!/usr/bin/env bash\nprintf '%s\\n' 'verify-pack' >> \"$GAUNTLET_LOG\"\nexit \"${GAUNTLET_VERIFY_EXIT:-0}\"\n",
            executable=True,
        )
        self._write(
            self.root / "tools" / "server-test.sh",
            "#!/usr/bin/env bash\nprintf '%s\\n' 'server-test' >> \"$GAUNTLET_LOG\"\nexit \"${GAUNTLET_BOOT_EXIT:-0}\"\n",
            executable=True,
        )
        self._write(
            self.root / "tools" / "build-release.sh",
            "#!/usr/bin/env bash\nset -eu\nprintf 'build-release %s %s\\n' \"$DIST_DIR\" \"$GIT_SHA\" >> \"$GAUNTLET_LOG\"\nmkdir -p \"$DIST_DIR\"\ncount_file=\"${GAUNTLET_BUILD_COUNT_FILE:?}\"\ncount=$(cat \"$count_file\")\ncount=$((count + 1))\nprintf '%s\\n' \"$count\" > \"$count_file\"\nprism=identical\nif [ \"$count\" -eq 2 ] && [ \"${GAUNTLET_SECOND_PRISM_DIFFERENT:-0}\" = 1 ]; then prism=different; fi\nprintf '%s\\n' \"$prism\" > \"$DIST_DIR/AFTERLIGHT-prism-instance.zip\"\nprintf '{\\\"sha\\\":\\\"%s\\\"}\\n' \"$GIT_SHA\" > \"$DIST_DIR/release-metadata.json\"\nprintf 'checksum\\n' > \"$DIST_DIR/SHA256SUMS\"\nprintf 'mrpack\\n' > \"$DIST_DIR/AFTERLIGHT-0.9.0-rc.1.mrpack\"\nprintf 'curseforge\\n' > \"$DIST_DIR/AFTERLIGHT-0.9.0-rc.1-curseforge.zip\"\nexit \"${GAUNTLET_BUILD_EXIT:-0}\"\n",
            executable=True,
        )
        self._write(self.root / "tools" / "sample.sh", "#!/usr/bin/env bash\nexit 0\n", executable=True)

    def _write_fake_commands(self):
        self._write(
            self.fake_bin / "git",
            "#!/usr/bin/env bash\nset -eu\nprintf 'git' >> \"$GAUNTLET_LOG\"\nfor argument in \"$@\"; do printf ' %s' \"$argument\" >> \"$GAUNTLET_LOG\"; done\nprintf '\\n' >> \"$GAUNTLET_LOG\"\nif [ \"$1\" = -C ] && [ \"$3 $4\" = 'worktree remove' ]; then rm -rf \"$6\"; exit 0; fi\ncase \"$1 ${2:-}\" in\n  'status --porcelain'*) if [ \"${GAUNTLET_DIRTY:-0}\" = 1 ] || { [ \"${GAUNTLET_TRACK_ENV:-0}\" = 1 ] && [ -e server/.env.gauntlet ]; }; then printf ' M server/.env.gauntlet\\n'; fi;;\n  'rev-parse HEAD') printf '%s\\n' \"$GAUNTLET_SHA\";;\n  'rev-parse --verify') [ \"${GAUNTLET_NONCOMMIT:-0}\" = 1 ] && exit 1; printf '%s\\n' \"$GAUNTLET_SHA\";;\n  'worktree add') destination=$4; mkdir -p \"$destination\"; cp -R \"$GAUNTLET_REPOSITORY/.\" \"$destination\";;\n  'ls-files '*) printf 'tools/sample.sh\\n';;\n  'diff --exit-code') exit \"${GAUNTLET_DIFF_EXIT:-0}\";;\nesac\nexit 0\n",
            executable=True,
        )
        self._write_fake_command("python3", "python3")
        self._write_fake_command("docker", "docker")
        self._write_fake_command("shellcheck", "shellcheck")
        self._write_fake_command("packwiz", "packwiz")
        self._write(
            self.fake_bin / "go",
            "#!/usr/bin/env bash\nprintf 'go version -m %s\\n' \"$3\" >> \"$GAUNTLET_LOG\"\nprintf '\\tpath\\tgithub.com/packwiz/packwiz\\n\\tmod\\tgithub.com/packwiz/packwiz\\tv0.0.0-dfd8b68a4796\\n'\n",
            executable=True,
        )
        self._write(self.fake_bin / "java", "#!/usr/bin/env bash\nexit 1\n", executable=True)
        self._write(self.root / "fake-java" / "bin" / "java", "#!/usr/bin/env bash\nprintf '%s\\n' 'openjdk version \"21.0.12\"' >&2\n", executable=True)
        self._write(
            self.fake_bin / "cmp",
            "#!/usr/bin/env bash\nprintf 'cmp %s %s\\n' \"$1\" \"$2\" >> \"$GAUNTLET_LOG\"\n/usr/bin/cmp \"$@\"\n",
            executable=True,
        )

    def _write_fake_command(self, name, canonical_name):
        self._write(
            self.fake_bin / name,
            "#!/usr/bin/env bash\nprintf '" + canonical_name + "' >> \"$GAUNTLET_LOG\"\nfor argument in \"$@\"; do printf ' %s' \"$argument\" >> \"$GAUNTLET_LOG\"; done\nprintf '\\n' >> \"$GAUNTLET_LOG\"\nexit 0\n",
            executable=True,
        )

    def _run(self, sha=SHA, **overrides):
        environment = os.environ.copy()
        for name in (
            "AFTERLIGHT_GAUNTLET_INNER",
            "GAUNTLET_ENV",
            "GAUNTLET_OUTPUT_DIR",
            "GAUNTLET_STARTED_AT",
        ):
            environment.pop(name, None)
        environment.update(
            {
                "PATH": f"{self.fake_bin}:{environment['PATH']}",
                "GAUNTLET_LOG": str(self.log_path),
                "GAUNTLET_REPOSITORY": str(self.root),
                "GAUNTLET_SHA": SHA,
                "GAUNTLET_BUILD_COUNT_FILE": str(self.root / "build-count"),
                "TMPDIR": str(self.worktree_root),
                "GAUNTLET_FAKE_JAVA_HOME": str(self.root / "fake-java"),
            }
        )
        environment.update(overrides)
        self.worktree_root.mkdir(exist_ok=True)
        (self.root / "build-count").write_text("0\n", encoding="utf-8")
        return subprocess.run(
            [str(self.root / "tools" / "release-gauntlet.sh"), sha],
            cwd=self.root,
            env=environment,
            capture_output=True,
            text=True,
        )

    def _log_lines(self):
        if not self.log_path.exists():
            return []
        return self.log_path.read_text(encoding="utf-8").splitlines()

    def test_rejects_dirty_tree_noncommit_and_nonhead_sha(self):
        for sha, environment in (
            (SHA, {"GAUNTLET_DIRTY": "1"}),
            (SHA, {"GAUNTLET_NONCOMMIT": "1"}),
            ("f" * 40, {}),
            ("not-a-sha", {}),
        ):
            with self.subTest(sha=sha, environment=environment):
                result = self._run(sha, **environment)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(any("worktree add" in line for line in self._log_lines()))
                self.log_path.unlink(missing_ok=True)

    def test_creates_detached_worktree_for_exact_sha(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(line.startswith("git worktree add --detach ") and line.endswith(f" {SHA}") for line in self._log_lines()))
        self.assertTrue(any("worktree remove --force" in line for line in self._log_lines()))

    def test_runs_tests_verify_boot_compose_shellcheck_and_two_builds_in_order(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        lines = self._log_lines()
        expected_prefixes = [
            "python3 -m unittest discover -s tools/tests -p test_*.py -v",
            "verify-pack",
            "server-test",
            "docker compose --project-name afterlight-gauntlet",
            "shellcheck -x tools/sample.sh",
            "build-release ",
            "build-release ",
            "cmp ",
            "git diff --exit-code",
            "git status --porcelain --untracked-files=all",
            "go version -m ",
        ]
        positions = []
        start = 0
        for prefix in expected_prefixes:
            for position in range(start, len(lines)):
                if lines[position].startswith(prefix):
                    positions.append(position)
                    start = position + 1
                    break
            else:
                self.fail(f"missing command prefix: {prefix}; log: {lines}")
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(len(lines), 17, lines)

    def test_compares_two_prism_archives_byte_for_byte(self):
        result = self._run(GAUNTLET_SECOND_PRISM_DIFFERENT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(line.startswith("cmp ") for line in self._log_lines()))
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_failure_stops_before_copying_accepted_artifacts(self):
        result = self._run(GAUNTLET_BOOT_EXIT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("server-test", self._log_lines())
        self.assertFalse(any(line.startswith("docker compose") for line in self._log_lines()))
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_removes_temporary_compose_environment_before_clean_check(self):
        result = self._run(GAUNTLET_TRACK_ENV="1")

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_success_copies_public_and_private_outputs_with_transcript(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "dist" / "gauntlet" / SHA
        self.assertEqual(
            {path.name for path in (output / "public").iterdir()},
            {"AFTERLIGHT-prism-instance.zip", "release-metadata.json", "SHA256SUMS"},
        )
        self.assertEqual(
            {path.name for path in (output / "friends-only").iterdir()},
            {"AFTERLIGHT-0.9.0-rc.1.mrpack", "AFTERLIGHT-0.9.0-rc.1-curseforge.zip"},
        )
        transcript = (output / "gauntlet.txt").read_text(encoding="utf-8")
        self.assertIn(f"SHA: {SHA}", transcript)
        self.assertIn("Prism SHA-256:", transcript)
        self.assertIn("Pack SHA-256:", transcript)
        self.assertIn("Index SHA-256:", transcript)
        self.assertRegex(transcript, r"UTC start: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z")
        self.assertRegex(transcript, r"UTC finish: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9:]+Z")
        self.assertRegex(transcript, r"Java: .+")
        self.assertRegex(transcript, r"Packwiz: github.com/packwiz/packwiz v\S*dfd8b68a4796\S*")
        self.assertEqual(len(__import__("re").findall(r"(?m)^.* SHA-256: [0-9a-f]{64}$", transcript)), 3)

    def test_cleanup_removes_only_the_temporary_worktree(self):
        sentinel = self.root / "dist" / "gauntlet" / "existing-output"
        sentinel.mkdir(parents=True)
        (sentinel / "keep.txt").write_text("keep\n", encoding="utf-8")

        result = self._run(GAUNTLET_BOOT_EXIT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((sentinel / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(list(self.worktree_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
