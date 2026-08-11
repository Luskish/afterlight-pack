import os
import hashlib
import re
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
    "test_client_install_failure_stops_before_acceptance",
    "test_failure_stops_before_copying_accepted_artifacts",
    "test_success_copies_exact_public_inventory_with_transcript",
    "test_cleanup_removes_only_the_temporary_worktree",
    "test_failed_worktree_add_cleans_only_its_owned_temporary_path",
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
            "#!/usr/bin/env bash\nset -eu\nprintf 'build-release %s %s\\n' \"$DIST_DIR\" \"$GIT_SHA\" >> \"$GAUNTLET_LOG\"\nmkdir -p \"$DIST_DIR\"\ncount_file=\"${GAUNTLET_BUILD_COUNT_FILE:?}\"\ncount=$(cat \"$count_file\")\ncount=$((count + 1))\nprintf '%s\\n' \"$count\" > \"$count_file\"\nprism=identical\nif [ \"$count\" -eq 2 ] && [ \"${GAUNTLET_SECOND_PRISM_DIFFERENT:-0}\" = 1 ]; then prism=different; fi\nprintf '%s\\n' \"$prism\" > \"$DIST_DIR/AFTERLIGHT-prism-instance.zip\"\nprintf 'mrpack\\n' > \"$DIST_DIR/AFTERLIGHT.mrpack\"\nprintf 'curseforge\\n' > \"$DIST_DIR/AFTERLIGHT-curseforge.zip\"\nprintf '{\\\"format\\\":3,\\\"git_sha\\\":\\\"%s\\\"}\\n' \"$GIT_SHA\" > \"$DIST_DIR/release-metadata.json\"\n(cd \"$DIST_DIR\" && shasum -a 256 AFTERLIGHT-curseforge.zip AFTERLIGHT-prism-instance.zip AFTERLIGHT.mrpack release-metadata.json > SHA256SUMS)\nif [ \"${GAUNTLET_EXTRA_FILE:-0}\" = 1 ]; then printf 'extra\\n' > \"$DIST_DIR/extra.txt\"; fi\nif [ \"${GAUNTLET_FRIENDS_DIRECTORY:-0}\" = 1 ]; then mkdir \"$DIST_DIR/friends-only\"; fi\nif [ \"${GAUNTLET_VERSIONED_NAME:-0}\" = 1 ]; then printf 'stale\\n' > \"$DIST_DIR/AFTERLIGHT-0.9.0-rc.1.mrpack\"; fi\nif [ \"${GAUNTLET_MISSING_CHECKSUMS:-0}\" = 1 ]; then rm \"$DIST_DIR/SHA256SUMS\"; fi\nif [ \"${GAUNTLET_MALFORMED_CHECKSUMS:-0}\" = 1 ]; then awk '{printf \"%s\\t%s\\n\", $1, $2}' \"$DIST_DIR/SHA256SUMS\" > \"$DIST_DIR/SHA256SUMS.tmp\"; mv \"$DIST_DIR/SHA256SUMS.tmp\" \"$DIST_DIR/SHA256SUMS\"; fi\nexit \"${GAUNTLET_BUILD_EXIT:-0}\"\n",
            executable=True,
        )
        self._write(
            self.root / "tools" / "client-install-test.sh",
            "#!/usr/bin/env bash\nprintf 'client-install %s\\n' \"$1\" >> \"$GAUNTLET_LOG\"\nexit \"${GAUNTLET_CLIENT_EXIT:-0}\"\n",
            executable=True,
        )
        self._write(self.root / "tools" / "sample.sh", "#!/usr/bin/env bash\nexit 0\n", executable=True)

    def _write_fake_commands(self):
        self._write(
            self.fake_bin / "git",
            "#!/usr/bin/env bash\nset -eu\nprintf 'git' >> \"$GAUNTLET_LOG\"\nfor argument in \"$@\"; do printf ' %s' \"$argument\" >> \"$GAUNTLET_LOG\"; done\nprintf '\\n' >> \"$GAUNTLET_LOG\"\nif [ \"$1\" = -C ] && [ \"$3 $4\" = 'worktree remove' ]; then [ \"${GAUNTLET_WORKTREE_REMOVE_FAIL:-0}\" = 1 ] && exit 1; rm -rf \"$6\"; exit 0; fi\ncase \"$1 ${2:-}\" in\n  'status --porcelain'*) if [ \"${GAUNTLET_DIRTY:-0}\" = 1 ] || { [ \"${GAUNTLET_TRACK_ENV:-0}\" = 1 ] && [ -e server/.env.gauntlet ]; }; then printf ' M server/.env.gauntlet\\n'; fi;;\n  'rev-parse HEAD') printf '%s\\n' \"$GAUNTLET_SHA\";;\n  'rev-parse --verify') [ \"${GAUNTLET_NONCOMMIT:-0}\" = 1 ] && exit 1; printf '%s\\n' \"$GAUNTLET_SHA\";;\n  'worktree add') destination=$4; mkdir -p \"$destination\"; if [ \"${GAUNTLET_WORKTREE_ADD_FAIL:-0}\" = 1 ]; then printf 'partial\\n' > \"$destination/partial.txt\"; exit 1; fi; cp -R \"$GAUNTLET_REPOSITORY/.\" \"$destination\";;\n  'ls-files '*) printf 'tools/sample.sh\\n';;\n  'diff --exit-code') exit \"${GAUNTLET_DIFF_EXIT:-0}\";;\nesac\nexit 0\n",
            executable=True,
        )
        self._write_fake_command("python3", "python3")
        self._write_fake_command("docker", "docker")
        self._write_fake_command("shellcheck", "shellcheck")
        self._write_fake_command("packwiz", "packwiz")
        self._write(
            self.fake_bin / "go",
            "#!/usr/bin/env bash\nprintf 'go version -m %s\\n' \"$3\" >> \"$GAUNTLET_LOG\"\nprintf '\\tpath\\tgithub.com/packwiz/packwiz\\n'\nif [ \"${GAUNTLET_PACKWIZ_OMIT_MOD_VERSION:-0}\" != 1 ]; then printf '\\tmod\\tgithub.com/packwiz/packwiz\\tv0.0.0-dfd8b68a4796\\n'; fi\nprintf '\\tbuild\\t-buildmode=exe\\n'\n",
            executable=True,
        )
        self._write(self.fake_bin / "java", "#!/usr/bin/env bash\nexit 1\n", executable=True)
        self._write(
            self.root / "fake java" / "bin" / "java",
            "#!/usr/bin/env bash\nprintf '%s\\n' \"${GAUNTLET_JAVA_VERSION:-openjdk version \\\"21.0.12\\\"}\" >&2\n",
            executable=True,
        )
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
                "GAUNTLET_FAKE_JAVA_HOME": str(self.root / "fake java"),
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

    def _normalized_log_lines(self):
        worktree_pattern = r"[^ ]*/afterlight-gauntlet\.[^/ ]+"
        return [
            re.sub(worktree_pattern, "<WORKTREE>", line.replace(str(self.root), "<REPO>"))
            for line in self._log_lines()
        ]

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

    def test_controller_output_guards_avoid_ambiguous_and_or_chains(self):
        source = GAUNTLET_SOURCE.read_text(encoding="utf-8")

        self.assertNotRegex(source, r"\]\s*&&\s*\[\s*!\s*-L\b.*\]\s*\|\|")

    def test_creates_detached_worktree_for_exact_sha(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(any(line.startswith("git worktree add --detach ") and line.endswith(f" {SHA}") for line in self._log_lines()))
        self.assertTrue(any("worktree remove --force" in line for line in self._log_lines()))

    def test_runs_tests_verify_boot_compose_shellcheck_and_two_builds_in_order(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._normalized_log_lines(), [
            "git status --porcelain --untracked-files=all",
            "git rev-parse HEAD",
            f"git rev-parse --verify {SHA}^{{commit}}",
            f"git worktree add --detach <WORKTREE> {SHA}",
            "python3 -m unittest discover -s tools/tests -p test_*.py -v",
            "verify-pack",
            "server-test",
            "docker compose --project-name afterlight-gauntlet --env-file <WORKTREE>/server/.env.gauntlet -f server/docker-compose.yml config --quiet",
            "git ls-files *.sh",
            "shellcheck -x tools/sample.sh",
            f"build-release <WORKTREE>/dist/.release-gauntlet-first {SHA}",
            f"build-release <WORKTREE>/dist/.release-gauntlet-second {SHA}",
            "cmp <WORKTREE>/dist/.release-gauntlet-first/AFTERLIGHT-prism-instance.zip <WORKTREE>/dist/.release-gauntlet-second/AFTERLIGHT-prism-instance.zip",
            "client-install <WORKTREE>/dist/.release-gauntlet-first/AFTERLIGHT-prism-instance.zip",
            "git diff --exit-code",
            "git status --porcelain --untracked-files=all",
            "go version -m <REPO>/fake-bin/packwiz",
            "git -C <REPO> worktree remove --force <WORKTREE>",
        ])

    def test_compares_two_prism_archives_byte_for_byte(self):
        result = self._run(GAUNTLET_SECOND_PRISM_DIFFERENT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(line.startswith("cmp ") for line in self._log_lines()))
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_client_install_failure_stops_before_acceptance(self):
        result = self._run(GAUNTLET_CLIENT_EXIT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(any(line.startswith("client-install ") for line in self._log_lines()))
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

    def test_success_copies_exact_public_inventory_with_transcript(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stderr)
        output = self.root / "dist" / "gauntlet" / SHA
        self.assertEqual(
            {path.name for path in (output / "public").iterdir()},
            {
                "AFTERLIGHT-curseforge.zip",
                "AFTERLIGHT-prism-instance.zip",
                "AFTERLIGHT.mrpack",
                "release-metadata.json",
                "SHA256SUMS",
            },
        )
        self.assertFalse((output / "friends-only").exists())
        transcript = (output / "gauntlet.txt").read_text(encoding="utf-8")
        expected_hashes = {
            "Prism": hashlib.sha256(b"identical\n").hexdigest(),
            "Pack": hashlib.sha256((self.root / "pack.toml").read_bytes()).hexdigest(),
            "Index": hashlib.sha256((self.root / "index.toml").read_bytes()).hexdigest(),
        }
        self.assertIn(f"SHA: {SHA}", transcript)
        self.assertRegex(transcript, r"(?m)^UTC start: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertRegex(transcript, r"(?m)^UTC finish: [0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$")
        self.assertIn('Java: openjdk version "21.0.12"', transcript)
        self.assertIn("Packwiz: github.com/packwiz/packwiz v0.0.0-dfd8b68a4796", transcript)
        self.assertIn("Pack version: 0.9.0-rc.1", transcript)
        self.assertIn("Minecraft version: 1.21.1", transcript)
        self.assertIn("NeoForge version: 21.1.248", transcript)
        for name, sha256 in expected_hashes.items():
            self.assertIn(f"{name} SHA-256: {sha256}", transcript)

    def test_rejects_noncanonical_build_inventory(self):
        cases = (
            {"GAUNTLET_EXTRA_FILE": "1"},
            {"GAUNTLET_FRIENDS_DIRECTORY": "1"},
            {"GAUNTLET_VERSIONED_NAME": "1"},
            {"GAUNTLET_MISSING_CHECKSUMS": "1"},
        )
        output = self.root / "dist" / "gauntlet" / SHA
        for environment in cases:
            with self.subTest(environment=environment):
                shutil.rmtree(output, ignore_errors=True)
                self.log_path.unlink(missing_ok=True)

                result = self._run(**environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(output.exists())

    def test_rejects_noncanonical_checksum_format(self):
        result = self._run(GAUNTLET_MALFORMED_CHECKSUMS="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public release checksums are malformed", result.stderr)
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_rejects_java_17_even_when_version_contains_21(self):
        result = self._run(GAUNTLET_JAVA_VERSION='openjdk version "17.0.21"')

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("GAUNTLET: ACCEPTED", result.stdout)
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_accepts_recognized_java_21_version_lines(self):
        output = self.root / "dist" / "gauntlet" / SHA
        for version in (
            'openjdk version "21.0.12" 2026-07-21 LTS',
            'java version "21"',
        ):
            with self.subTest(version=version):
                shutil.rmtree(output, ignore_errors=True)
                self.log_path.unlink(missing_ok=True)

                result = self._run(GAUNTLET_JAVA_VERSION=version)

                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("GAUNTLET: ACCEPTED", result.stdout)
                transcript = (output / "gauntlet.txt").read_text(encoding="utf-8")
                self.assertIn(f"Java: {version}", transcript)

    def test_rejects_malformed_java_version_lines(self):
        output = self.root / "dist" / "gauntlet" / SHA
        for version in (
            'not-java-output "21.0.12"',
            'openjdk version "21garbage"',
            "openjdk version 21.0.12",
            'openjdk version ""',
            'openjdk version "21."',
            'openjdk version "21.0.12" "extra"',
        ):
            with self.subTest(version=version):
                shutil.rmtree(output, ignore_errors=True)
                self.log_path.unlink(missing_ok=True)

                result = self._run(GAUNTLET_JAVA_VERSION=version)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("malformed or missing Java version", result.stderr)
                self.assertNotIn("GAUNTLET: ACCEPTED", result.stdout)
                self.assertFalse(output.exists())

    def test_rejects_packwiz_build_without_module_version(self):
        result = self._run(GAUNTLET_PACKWIZ_OMIT_MOD_VERSION="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("GAUNTLET: ACCEPTED", result.stdout)
        self.assertFalse((self.root / "dist" / "gauntlet" / SHA).exists())

    def test_cleanup_removes_only_the_temporary_worktree(self):
        sentinel = self.root / "dist" / "gauntlet" / "existing-output"
        sentinel.mkdir(parents=True)
        (sentinel / "keep.txt").write_text("keep\n", encoding="utf-8")

        result = self._run(GAUNTLET_BOOT_EXIT="1")

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((sentinel / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(list(self.worktree_root.iterdir()), [])

    def test_failed_worktree_add_cleans_only_its_owned_temporary_path(self):
        sentinel = self.root / "dist" / "gauntlet" / "existing-output"
        sentinel.mkdir(parents=True)
        (sentinel / "keep.txt").write_text("keep\n", encoding="utf-8")

        result = self._run(
            GAUNTLET_WORKTREE_ADD_FAIL="1",
            GAUNTLET_WORKTREE_REMOVE_FAIL="1",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((sentinel / "keep.txt").read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(list(self.worktree_root.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
