from __future__ import annotations

import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROMOTION_SCRIPT = ROOT / "tools" / "promote-release.sh"
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

        (self.root / "pack.toml").write_text(
            f'version = "{VERSION}"\n', encoding="utf-8"
        )
        (self.root / "index.toml").write_text("index fixture\n", encoding="utf-8")
        accepted = self.root / "dist" / "gauntlet" / SHA
        public = accepted / "public"
        private = accepted / "friends-only"
        public.mkdir(parents=True)
        private.mkdir()
        (public / "AFTERLIGHT-prism-instance.zip").write_bytes(b"prism\n")
        (public / "release-metadata.json").write_bytes(b"metadata\n")
        prism_hash = self._sha256(public / "AFTERLIGHT-prism-instance.zip")
        metadata_hash = self._sha256(public / "release-metadata.json")
        (public / "SHA256SUMS").write_text(
            f"{prism_hash}  AFTERLIGHT-prism-instance.zip\n"
            f"{metadata_hash}  release-metadata.json\n",
            encoding="utf-8",
        )
        (private / f"AFTERLIGHT-{VERSION}.mrpack").write_bytes(b"mrpack\n")
        (private / f"AFTERLIGHT-{VERSION}-curseforge.zip").write_bytes(
            b"curseforge\n"
        )
        (accepted / "gauntlet.txt").write_text(
            f"AFTERLIGHT release gauntlet\nSHA: {SHA}\n", encoding="utf-8"
        )

        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.branch_file = self.root / "branch"
        self.branch_file.write_text("dev\n", encoding="utf-8")
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
              "status --porcelain") ;;
              "tag --list") ;;
              "ls-remote --exit-code") exit 2 ;;
              "push origin") ;;
              "switch main") printf 'main\n' > "$FAKE_BRANCH_FILE" ;;
              "switch dev") printf 'dev\n' > "$FAKE_BRANCH_FILE" ;;
              "merge --ff-only") ;;
              "tag -a") ;;
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

    def _run(self, *, environment: dict[str, str] | None = None):
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            [str(self.root / "tools" / "promote-release.sh"), SHA, "--confirm"],
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

    def test_success_requires_exact_push_runs_pages_parity_and_then_tags(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git_calls = self._git_calls()
        self.assertLess(git_calls.index("push origin dev"), git_calls.index("switch main"))
        self.assertLess(git_calls.index("push origin main"), git_calls.index(f"tag -a v{VERSION} {SHA} -m AFTERLIGHT {VERSION}"))
        self.assertIn(f"push origin v{VERSION}", git_calls)
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

        self.assertIn('tools/promote-release.sh "$SHA" --confirm', releasing)
        self.assertIn("Populate every automated evidence field", releasing)
        self.assertIn("must contain no automated `NOT RUN`", releasing)
        self.assertIn("--verify-tag", releasing)
        self.assertIn('refs/tags/v0.9.0-rc.1^{}', releasing)
        self.assertIn("tools/promote-release.sh", verifier)


if __name__ == "__main__":
    unittest.main()
