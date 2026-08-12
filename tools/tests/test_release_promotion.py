from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.tests.release_fixtures import (
    expected_tag_message,
    rewrite_checksums,
    rewrite_metadata,
    write_gauntlet_receipt,
    write_empty_zip,
    write_public_release,
    write_release_policy,
)


ROOT = Path(__file__).resolve().parents[2]
PROMOTION_SCRIPT = ROOT / "tools" / "promote-release.sh"
RELEASE_TOOL = ROOT / "tools" / "release_artifacts.py"
SHA = "0123456789abcdef0123456789abcdef01234567"
VERSION = "0.9.0-rc.1"


class ReleasePromotionTests(unittest.TestCase):
    maxDiff = None

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.root = Path(self.temporary_directory.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        (self.root / "tools").mkdir()
        if PROMOTION_SCRIPT.exists():
            destination = self.root / "tools" / "promote-release.sh"
            destination.write_bytes(PROMOTION_SCRIPT.read_bytes())
            destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
        (self.root / "tools" / "release_artifacts.py").write_bytes(
            RELEASE_TOOL.read_bytes()
        )
        write_release_policy(self.root / "tools" / "release-policy.env")

        (self.root / "pack.toml").write_text(
            f'version = "{VERSION}"\n', encoding="utf-8"
        )
        (self.root / "index.toml").write_text("index fixture\n", encoding="utf-8")
        accepted = self.root / "dist" / "gauntlet" / SHA
        public = accepted / "public"
        write_public_release(public, VERSION, SHA)
        (accepted / "gauntlet.txt").write_text(
            f"AFTERLIGHT release gauntlet\nSHA: {SHA}\n", encoding="utf-8"
        )
        self.receipt_sha256 = write_gauntlet_receipt(accepted, VERSION, SHA)

        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.branch_file = self.root / "branch"
        self.branch_file.write_text("dev\n", encoding="utf-8")
        self.tag_message_file = self.root / "tag-message.txt"
        self._install_fakes()

        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "FAKE_BRANCH_FILE": str(self.branch_file),
                "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GIT_LOG": str(self.git_log),
                "FAKE_HEAD_SHA": SHA,
                "FAKE_PACK_FILE": str(self.root / "pack.toml"),
                "FAKE_INDEX_FILE": str(self.root / "index.toml"),
                "FAKE_TAG_MESSAGE_FILE": str(self.tag_message_file),
                "AFTERLIGHT_CI_POLL_ATTEMPTS": "2",
                "AFTERLIGHT_CI_POLL_SECONDS": "0",
                "AFTERLIGHT_PAGES_POLL_ATTEMPTS": "2",
                "AFTERLIGHT_PAGES_POLL_SECONDS": "0",
            }
        )

    @staticmethod
    def _sha256(path: Path) -> str:
        result = subprocess.run(
            ["shasum", "-a", "256", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.split()[0]

    def _write_executable(self, name: str, source: str) -> None:
        path = self.fake_bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR)

    def _install_fakes(self) -> None:
        self._write_executable(
            "git",
            r"""
            #!/usr/bin/env bash
            set -u
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            case "${1:-} ${2:-}" in
              "branch --show-current") cat "$FAKE_BRANCH_FILE" ;;
              "rev-parse HEAD") printf '%s\n' "$FAKE_HEAD_SHA" ;;
              "status --porcelain")
                if [ "${FAKE_DIRTY:-0}" = 1 ]; then printf ' M tools/release-policy.env\n'; fi
                ;;
              "tag --list") ;;
              "ls-remote --exit-code") exit 2 ;;
              "push origin") ;;
              "switch main") printf 'main\n' > "$FAKE_BRANCH_FILE" ;;
              "switch dev") printf 'dev\n' > "$FAKE_BRANCH_FILE" ;;
              "merge --ff-only") ;;
              "tag -a")
                previous=""
                for argument in "$@"; do
                  if [ "$previous" = "-F" ]; then cat "$argument" > "$FAKE_TAG_MESSAGE_FILE"; fi
                  previous=$argument
                done
                ;;
              *) printf 'unexpected fake git command: %s\n' "$*" >&2; exit 91 ;;
            esac
            """,
        )
        self._write_executable(
            "gh",
            r"""
            #!/usr/bin/env bash
            set -u
            printf '%s\n' "$*" >> "$FAKE_GH_LOG"
            if [ "${1:-} ${2:-}" = "run list" ]; then
              [ "${FAKE_GH_NO_RUNS:-0}" = 0 ] || exit 0
              case " $* " in
                *" --branch dev "*) printf '101\n' ;;
                *" --branch main "*) printf '202\n' ;;
                *) exit 92 ;;
              esac
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "run watch" ]; then
              if [ "${FAKE_GH_FAIL_WATCH_ID:-}" = "${3:-}" ]; then
                exit 7
              fi
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "run view" ]; then
              case "${3:-}" in
                101) printf '%s\tpush\tcompleted\tsuccess\thttps://example.invalid/dev/101\n' "$FAKE_HEAD_SHA" ;;
                202) printf '%s\tpush\tcompleted\tsuccess\thttps://example.invalid/main/202\n' "$FAKE_HEAD_SHA" ;;
                *) exit 93 ;;
              esac
              exit 0
            fi
            printf 'unexpected fake gh command: %s\n' "$*" >&2
            exit 94
            """,
        )
        self._write_executable(
            "curl",
            r"""
            #!/usr/bin/env bash
            case "$*" in
              *pack.toml*) cat "$FAKE_PACK_FILE" ;;
              *index.toml*) cat "$FAKE_INDEX_FILE" ;;
              *) exit 95 ;;
            esac
            """,
        )
        self._write_executable("sleep", "#!/usr/bin/env bash\nexit 0\n")

    def _run(
        self,
        *,
        receipt_sha256: str | None = None,
        environment: dict[str, str] | None = None,
    ):
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        if receipt_sha256 is None:
            receipt_sha256 = self.receipt_sha256
        return subprocess.run(
            [
                str(self.root / "tools" / "promote-release.sh"),
                SHA,
                receipt_sha256,
                "--confirm",
            ],
            cwd=self.root,
            env=command_environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def _git_calls(self) -> list[str]:
        if not self.git_log.exists():
            return []
        return self.git_log.read_text(encoding="utf-8").splitlines()

    def _gh_calls(self) -> list[str]:
        if not self.gh_log.exists():
            return []
        return self.gh_log.read_text(encoding="utf-8").splitlines()

    def test_failed_dev_ci_stops_before_main_and_tag(self) -> None:
        result = self._run(environment={"FAKE_GH_FAIL_WATCH_ID": "101"})

        self.assertNotEqual(result.returncode, 0)
        calls = self._git_calls()
        self.assertIn("push origin dev", calls)
        self.assertNotIn("switch main", calls)
        self.assertNotIn("switch dev", calls)
        self.assertEqual(self.branch_file.read_text(encoding="utf-8"), "dev\n")
        self.assertFalse(any(call.startswith("tag -a ") for call in calls))

    def test_failure_after_script_switches_main_restores_dev(self) -> None:
        result = self._run(environment={"FAKE_GH_FAIL_WATCH_ID": "202"})

        self.assertNotEqual(result.returncode, 0)
        calls = self._git_calls()
        self.assertEqual(calls.count("switch main"), 1)
        self.assertEqual(calls.count("switch dev"), 1)
        self.assertEqual(self.branch_file.read_text(encoding="utf-8"), "dev\n")
        self.assertFalse(any(call.startswith("tag -a ") for call in calls))

    def test_missing_exact_dev_ci_run_stops_before_main(self) -> None:
        result = self._run(environment={"FAKE_GH_NO_RUNS": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exact push CI run", result.stderr)
        self.assertNotIn("switch main", self._git_calls())

    def test_noncanonical_poll_count_is_rejected_before_push(self) -> None:
        result = self._run(environment={"AFTERLIGHT_CI_POLL_ATTEMPTS": "08"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("positive integer", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())

    def test_rejects_dirty_policy_before_sourcing_trusted_values(self) -> None:
        marker = self.root / "policy-sourced"
        policy_path = self.root / "tools" / "release-policy.env"
        policy_path.write_text(
            f'touch "{marker}"\n' + policy_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = self._run(environment={"FAKE_DIRTY": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertNotIn("push origin dev", self._git_calls())

    def test_rejects_noncanonical_public_inventory_before_push(self) -> None:
        public = self.root / "dist" / "gauntlet" / SHA / "public"
        cases = (
            public / "extra.txt",
            public / "friends-only",
            public / f"AFTERLIGHT-{VERSION}.mrpack",
        )
        for path in cases:
            with self.subTest(path=path):
                if path.name == "friends-only":
                    path.mkdir()
                else:
                    path.write_text("noncanonical\n", encoding="utf-8")

                result = self._run()

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("inventory", result.stderr)
                self.assertNotIn("push origin dev", self._git_calls())
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                self.git_log.unlink(missing_ok=True)

    def test_rejects_missing_checksum_before_push(self) -> None:
        checksum_path = (
            self.root / "dist" / "gauntlet" / SHA / "public" / "SHA256SUMS"
        )
        checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
        checksum_path.write_text("\n".join(checksum_lines[1:]) + "\n", encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("push origin dev", self._git_calls())

    def test_rejects_noncanonical_checksum_format_before_push(self) -> None:
        checksum_path = (
            self.root / "dist" / "gauntlet" / SHA / "public" / "SHA256SUMS"
        )
        checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
        checksum_path.write_text(
            "\n".join(line.replace("  ", "\t", 1) for line in checksum_lines)
            + "\n",
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("checksums are malformed", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())

    def test_rejects_malformed_metadata_before_push_or_tag(self) -> None:
        public = self.root / "dist" / "gauntlet" / SHA / "public"
        (public / "release-metadata.json").write_text(
            "{not-json\n", encoding="utf-8"
        )
        rewrite_checksums(public)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid UTF-8 JSON", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())
        self.assertFalse(any(call.startswith("tag -a ") for call in self._git_calls()))

    def test_rejects_self_consistent_post_gauntlet_archive_replacement(self) -> None:
        public = self.root / "dist" / "gauntlet" / SHA / "public"
        write_empty_zip(public / "AFTERLIGHT.mrpack")
        rewrite_metadata(public, VERSION, SHA)
        rewrite_checksums(public)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Modrinth manifest", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())
        self.assertFalse(any(call.startswith("tag -a ") for call in self._git_calls()))

    def test_requires_exact_accepted_receipt_digest_before_push(self) -> None:
        for receipt_sha256 in ("f" * 64, "not-a-digest"):
            with self.subTest(receipt_sha256=receipt_sha256):
                result = self._run(receipt_sha256=receipt_sha256)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("receipt", result.stderr.lower())
                self.assertNotIn("push origin dev", self._git_calls())
                self.git_log.unlink(missing_ok=True)

        result = subprocess.run(
            [str(self.root / "tools" / "promote-release.sh"), SHA, "--confirm"],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECEIPT_SHA256", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())

    def test_rejects_self_consistent_receipt_replacement_before_push(self) -> None:
        accepted = self.root / "dist" / "gauntlet" / SHA
        public = accepted / "public"
        metadata_path = public / "release-metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata_path.write_text(
            json.dumps(metadata, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rewrite_checksums(public)
        replacement_digest = write_gauntlet_receipt(accepted, VERSION, SHA)
        self.assertNotEqual(replacement_digest, self.receipt_sha256)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt SHA-256", result.stderr)
        self.assertNotIn("push origin dev", self._git_calls())

    def test_success_requires_exact_push_runs_pages_parity_and_then_tags(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git_calls = self._git_calls()
        self.assertLess(git_calls.index("push origin dev"), git_calls.index("switch main"))
        tag_call = next(call for call in git_calls if call.startswith(f"tag -a v{VERSION} {SHA} -F "))
        self.assertLess(git_calls.index("push origin main"), git_calls.index(tag_call))
        self.assertIn(f"push origin v{VERSION}", git_calls)
        self.assertEqual(
            self.tag_message_file.read_text(encoding="utf-8"),
            expected_tag_message(
                self.root / "dist" / "gauntlet" / SHA,
                self.receipt_sha256,
            ),
        )
        gh_calls = "\n".join(self._gh_calls())
        self.assertIn(f"run list --repo Luskish/afterlight-pack --workflow pack-ci --branch dev --event push --commit {SHA}", gh_calls)
        self.assertIn(f"run list --repo Luskish/afterlight-pack --workflow pack-ci --branch main --event push --commit {SHA}", gh_calls)
        self.assertIn("DEV_CI_URL=https://example.invalid/dev/101", result.stdout)
        self.assertIn("MAIN_CI_URL=https://example.invalid/main/202", result.stdout)
        self.assertIn("PAGES_PACK_SHA=", result.stdout)
        self.assertIn("PAGES_INDEX_SHA=", result.stdout)

    def test_release_docs_use_fail_closed_promoter_before_publication(self) -> None:
        releasing = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
        verifier = (ROOT / "tools" / "verify-pack.sh").read_text(encoding="utf-8")
        publisher = (ROOT / "tools" / "publish-release.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn(
            'tools/promote-release.sh "$SHA" "$RECEIPT_SHA256" --confirm',
            releasing,
        )
        self.assertIn('TAG="v$VERSION"', releasing)
        self.assertIn('RELEASE_DOC="docs/releases/$VERSION.md"', releasing)
        self.assertIn("Populate every automated evidence field", releasing)
        self.assertIn("must contain no automated `NOT RUN`", releasing)
        self.assertIn(
            'tools/publish-release.sh "$SHA" "$VERSION" "$RECEIPT_SHA256"',
            releasing,
        )
        self.assertNotIn("refs/tags/v0.9.0-rc.1^{}", releasing)
        self.assertIn("--verify-tag", publisher)
        self.assertIn("tools/promote-release.sh", verifier)
        self.assertIn("tools/publish-release.sh", verifier)

    def test_handoff_active_hard_rules_use_exact_public_inventory(self) -> None:
        handoff = (ROOT / "docs" / "HANDOFF.md").read_text(encoding="utf-8")
        hard_rules = handoff.split(
            "## Hard rules the prompts assume (also in AGENTS.md)",
            1,
        )[1].split("## If returning to Claude instead of Codex", 1)[0]

        self.assertIn("2026-08-11", hard_rules)
        for public_name in (
            "AFTERLIGHT-prism-instance.zip",
            "AFTERLIGHT-curseforge.zip",
            "AFTERLIGHT.mrpack",
            "SHA256SUMS",
            "release-metadata.json",
        ):
            self.assertIn(public_name, hard_rules)
        self.assertNotIn("friends-only", hard_rules.casefold())


class PromotionArgumentHygieneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        temporary_root = Path(self.temporary_directory.name)
        self.root = temporary_root / "checkout"
        self.remote = temporary_root / "origin.git"
        self.root.mkdir()
        (self.root / "tools").mkdir()
        destination = self.root / "tools" / "promote-release.sh"
        destination.write_bytes(PROMOTION_SCRIPT.read_bytes())
        destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
        (self.root / "tracked.txt").write_text("dev fixture\n", encoding="utf-8")

        self._run_git("init", "--quiet")
        self._run_git("config", "user.name", "Release Test")
        self._run_git("config", "user.email", "release-test@example.invalid")
        self._run_git("add", "tools/promote-release.sh", "tracked.txt")
        self._run_git("commit", "--quiet", "-m", "dev fixture")
        self._run_git("branch", "-M", "dev")
        self._run_git("switch", "--quiet", "-c", "main")
        (self.root / "tracked.txt").write_text("main fixture\n", encoding="utf-8")
        self._run_git("add", "tracked.txt")
        self._run_git("commit", "--quiet", "-m", "main fixture")
        self._run_git("switch", "--quiet", "dev")

        subprocess.run(
            ["git", "init", "--quiet", "--bare", str(self.remote)],
            check=True,
            capture_output=True,
            text=True,
        )
        self._run_git("remote", "add", "origin", str(self.remote))
        self._run_git("push", "--quiet", "-u", "origin", "dev", "main")
        self.receipt_sha256 = "a" * 64

    def _run_git(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        )

    def _repository_snapshot(self) -> dict[str, str]:
        return {
            "branch": self._run_git("branch", "--show-current").stdout,
            "head": self._run_git("rev-parse", "HEAD").stdout,
            "index": self._run_git("ls-files", "--stage").stdout,
            "worktree": self._run_git(
                "status",
                "--porcelain=v1",
                "--untracked-files=all",
            ).stdout,
            "local_refs": self._run_git(
                "for-each-ref",
                "--format=%(refname) %(objectname)",
            ).stdout,
            "remote_config": self._run_git("remote", "-v").stdout,
            "remote_refs": subprocess.run(
                [
                    "git",
                    f"--git-dir={self.remote}",
                    "for-each-ref",
                    "--format=%(refname) %(objectname)",
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout,
        }

    def _run_invalid(self, arguments: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(self.root / "tools" / "promote-release.sh"), *arguments],
            cwd=self.root,
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            check=False,
        )

    def test_invalid_calls_preserve_exact_repository_state_from_main_and_dev(self) -> None:
        for branch in ("main", "dev"):
            self._run_git("switch", "--quiet", branch)
            branch_sha = self._run_git("rev-parse", "HEAD").stdout.strip()
            invalid_calls = (
                ("omitted", []),
                ("unconfirmed", [branch_sha, self.receipt_sha256]),
                ("reordered", [branch_sha, "--confirm", self.receipt_sha256]),
                ("malformed-sha", ["not-a-sha", self.receipt_sha256, "--confirm"]),
                ("malformed-receipt", [branch_sha, "not-a-digest", "--confirm"]),
                ("extra", [branch_sha, self.receipt_sha256, "--confirm", "extra"]),
            )
            if branch == "main":
                invalid_calls = (
                    *invalid_calls,
                    ("wrong-starting-branch", [branch_sha, self.receipt_sha256, "--confirm"]),
                )
            for label, arguments in invalid_calls:
                with self.subTest(branch=branch, label=label):
                    self._run_git("switch", "--quiet", branch)
                    before = self._repository_snapshot()

                    result = self._run_invalid(arguments)

                    self.assertNotEqual(result.returncode, 0)
                    self.assertEqual(self._repository_snapshot(), before)


if __name__ == "__main__":
    unittest.main()
