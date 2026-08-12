from __future__ import annotations

import json
import os
import shutil
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
    write_packwiz_source,
    write_empty_zip,
    write_public_release,
    write_release_policy,
)


ROOT = Path(__file__).resolve().parents[2]
PROMOTION_SCRIPT = ROOT / "tools" / "promote-release.sh"
RELEASE_TOOL = ROOT / "tools" / "release_artifacts.py"
VERSION = "0.9.0-rc.1"
PRODUCTION_PUSH_URL = "https://github.com/Luskish/afterlight-pack.git"


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

        self.real_git = shutil.which("git")
        self.assertIsNotNone(self.real_git)
        self.accepted_sha = write_packwiz_source(self.root, VERSION)
        accepted = self.root / "dist" / "gauntlet" / self.accepted_sha
        public = accepted / "public"
        write_public_release(public, VERSION, self.accepted_sha)
        (accepted / "gauntlet.txt").write_text(
            f"AFTERLIGHT release gauntlet\nSHA: {self.accepted_sha}\n",
            encoding="utf-8",
        )
        self.receipt_sha256 = write_gauntlet_receipt(
            accepted,
            VERSION,
            self.accepted_sha,
        )

        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.curl_log = self.root / "curl.log"
        self.client_log = self.root / "client.log"
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
                "FAKE_CURL_LOG": str(self.curl_log),
                "FAKE_CLIENT_LOG": str(self.client_log),
                "FAKE_HEAD_SHA": self.accepted_sha,
                "FAKE_REAL_GIT": self.real_git,
                "FAKE_PACK_FILE": str(self.root / "pack.toml"),
                "FAKE_INDEX_FILE": str(self.root / "index.toml"),
                "FAKE_ORIGIN_URL": "https://github.com/Luskish/afterlight-pack.git",
                "FAKE_PUSH_URL": "https://github.com/Luskish/afterlight-pack.git",
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
            if [ "${FAKE_REQUIRE_NO_REPLACE:-0}" = 1 ] && [ "${GIT_NO_REPLACE_OBJECTS:-}" != 1 ]; then exit 96; fi
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            if [ "${1:-}" = "-C" ]; then
              exec "$FAKE_REAL_GIT" "$@"
            fi
            case "${1:-} ${2:-}" in
              "branch --show-current") cat "$FAKE_BRANCH_FILE" ;;
              "rev-parse HEAD") printf '%s\n' "$FAKE_HEAD_SHA" ;;
              "status --porcelain")
                if [ "${FAKE_DIRTY:-0}" = 1 ]; then printf ' M tools/release-policy.env\n'; fi
                ;;
              "remote get-url")
                if [ "${3:-}" = "--push" ]; then
                  printf '%s\n' "$FAKE_PUSH_URL"
                else
                  printf '%s\n' "$FAKE_ORIGIN_URL"
                fi
                ;;
              "tag --list") ;;
              "ls-remote --exit-code") exit 2 ;;
              push*) ;;
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
            if [ "${1:-}" = api ] && [[ " $* " == *" repos/Luskish/afterlight-pack/actions/workflows/pack-ci.yml "* ]]; then
              printf '777\t.github/workflows/pack-ci.yml\tactive\n'
              exit 0
            fi
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
                101) printf '%s\t%s\tpush\tcompleted\tsuccess\thttps://example.invalid/dev/101\t%s\t%s\n' "$FAKE_HEAD_SHA" "${FAKE_CI_BRANCH:-dev}" "${FAKE_CI_WORKFLOW_ID:-777}" "${FAKE_CI_ATTEMPT:-1}" ;;
                202) printf '%s\t%s\tpush\tcompleted\tsuccess\thttps://example.invalid/main/202\t%s\t%s\n' "$FAKE_HEAD_SHA" "${FAKE_CI_BRANCH_MAIN:-main}" "${FAKE_CI_WORKFLOW_ID:-777}" "${FAKE_CI_ATTEMPT:-1}" ;;
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
            printf '%s\n' "$*" >> "$FAKE_CURL_LOG"
            case "$*" in
              *pack.toml*)
                if [ "${FAKE_BARE_STALE:-0}" = 1 ] && [[ "$*" != *\?* ]]; then
                  printf 'stale pack\n'
                else
                  cat "$FAKE_PACK_FILE"
                fi
                ;;
              *index.toml*)
                if [ "${FAKE_BARE_STALE:-0}" = 1 ] && [[ "$*" != *\?* ]]; then
                  printf 'stale index\n'
                else
                  cat "$FAKE_INDEX_FILE"
                fi
                ;;
              *) exit 95 ;;
            esac
            """,
        )
        client_install = self.root / "tools" / "client-install-test.sh"
        client_install.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"$*\" >> \"$FAKE_CLIENT_LOG\"\n"
            "if [ \"${2:-}\" = local ]; then\n"
            "  printf 'Client mod-set SHA-256: %s\\n' \"${FAKE_LOCAL_MODSET_SHA256:-1111111111111111111111111111111111111111111111111111111111111111}\"\n"
            "  printf 'Client payload SHA-256: %s\\n' \"${FAKE_LOCAL_PAYLOAD_SHA256:-2222222222222222222222222222222222222222222222222222222222222222}\"\n"
            "fi\n"
            "if [ \"${2:-}\" = production ] && [ \"${3:-}\" != \"${FAKE_LOCAL_MODSET_SHA256:-1111111111111111111111111111111111111111111111111111111111111111}\" ]; then exit 18; fi\n"
            "if [ \"${2:-}\" = production ] && [ \"${4:-}\" != \"${FAKE_LOCAL_PAYLOAD_SHA256:-2222222222222222222222222222222222222222222222222222222222222222}\" ]; then exit 19; fi\n"
            "exit \"${FAKE_CLIENT_EXIT:-0}\"\n",
            encoding="utf-8",
        )
        client_install.chmod(client_install.stat().st_mode | stat.S_IXUSR)
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
                self.accepted_sha,
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

    def _push_calls(self) -> list[str]:
        return [call for call in self._git_calls() if call.startswith("push ")]

    def test_failed_dev_ci_stops_before_main_and_tag(self) -> None:
        result = self._run(environment={"FAKE_GH_FAIL_WATCH_ID": "101"})

        self.assertNotEqual(result.returncode, 0)
        calls = self._git_calls()
        self.assertIn(
            f"push {PRODUCTION_PUSH_URL} HEAD:refs/heads/dev",
            calls,
        )
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
        self.assertFalse(self._push_calls())

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
        self.assertFalse(self._push_calls())

    def test_rejects_nonproduction_origin_before_push(self) -> None:
        result = self._run(
            environment={"FAKE_ORIGIN_URL": "https://github.com/attacker/fork.git"}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production repository", result.stderr)
        self.assertFalse(self._push_calls())

    def test_rejects_nonproduction_push_url_before_push(self) -> None:
        result = self._run(
            environment={"FAKE_PUSH_URL": "ssh://git@attacker.invalid/fork.git"}
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("production repository", result.stderr)
        self.assertFalse(self._push_calls())

    def test_rejects_multiple_push_urls_before_push(self) -> None:
        result = self._run(
            environment={
                "FAKE_PUSH_URL": (
                    "https://github.com/Luskish/afterlight-pack.git\n"
                    "ssh://git@attacker.invalid/fork.git"
                )
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exactly one production repository URL", result.stderr)
        self.assertFalse(self._push_calls())

    def test_success_pushes_directly_to_the_validated_production_url(self) -> None:
        production_url = "ssh://git@github.com/Luskish/afterlight-pack.git"

        result = self._run(environment={"FAKE_PUSH_URL": production_url})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        calls = self._git_calls()
        self.assertIn(
            f"push {production_url} HEAD:refs/heads/dev",
            calls,
        )
        self.assertIn(
            f"push {production_url} HEAD:refs/heads/main",
            calls,
        )
        self.assertIn(
            f"push {production_url} refs/tags/v{VERSION}:refs/tags/v{VERSION}",
            calls,
        )
        self.assertFalse(any(call.startswith("push origin") for call in calls))

    def test_disables_git_replace_objects_for_release_control(self) -> None:
        result = self._run(environment={"FAKE_REQUIRE_NO_REPLACE": "1"})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_noncanonical_public_inventory_before_push(self) -> None:
        public = self.root / "dist" / "gauntlet" / self.accepted_sha / "public"
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
                self.assertFalse(self._push_calls())
                if path.is_dir():
                    path.rmdir()
                else:
                    path.unlink()
                self.git_log.unlink(missing_ok=True)

    def test_rejects_missing_checksum_before_push(self) -> None:
        checksum_path = (
            self.root
            / "dist"
            / "gauntlet"
            / self.accepted_sha
            / "public"
            / "SHA256SUMS"
        )
        checksum_lines = checksum_path.read_text(encoding="utf-8").splitlines()
        checksum_path.write_text("\n".join(checksum_lines[1:]) + "\n", encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._push_calls())

    def test_rejects_noncanonical_checksum_format_before_push(self) -> None:
        checksum_path = (
            self.root
            / "dist"
            / "gauntlet"
            / self.accepted_sha
            / "public"
            / "SHA256SUMS"
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
        self.assertFalse(self._push_calls())

    def test_rejects_malformed_metadata_before_push_or_tag(self) -> None:
        public = self.root / "dist" / "gauntlet" / self.accepted_sha / "public"
        (public / "release-metadata.json").write_text(
            "{not-json\n", encoding="utf-8"
        )
        rewrite_checksums(public)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("valid UTF-8 JSON", result.stderr)
        self.assertFalse(self._push_calls())
        self.assertFalse(any(call.startswith("tag -a ") for call in self._git_calls()))

    def test_rejects_self_consistent_post_gauntlet_archive_replacement(self) -> None:
        public = self.root / "dist" / "gauntlet" / self.accepted_sha / "public"
        write_empty_zip(public / "AFTERLIGHT.mrpack")
        rewrite_metadata(public, VERSION, self.accepted_sha)
        rewrite_checksums(public)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Modrinth manifest", result.stderr)
        self.assertFalse(self._push_calls())
        self.assertFalse(any(call.startswith("tag -a ") for call in self._git_calls()))

    def test_requires_exact_accepted_receipt_digest_before_push(self) -> None:
        for receipt_sha256 in ("f" * 64, "not-a-digest"):
            with self.subTest(receipt_sha256=receipt_sha256):
                result = self._run(receipt_sha256=receipt_sha256)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("receipt", result.stderr.lower())
                self.assertFalse(self._push_calls())
                self.git_log.unlink(missing_ok=True)

        result = subprocess.run(
            [
                str(self.root / "tools" / "promote-release.sh"),
                self.accepted_sha,
                "--confirm",
            ],
            cwd=self.root,
            env=self.environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECEIPT_SHA256", result.stderr)
        self.assertFalse(self._push_calls())

    def test_rejects_self_consistent_receipt_replacement_before_push(self) -> None:
        accepted = self.root / "dist" / "gauntlet" / self.accepted_sha
        public = accepted / "public"
        metadata_path = public / "release-metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata_path.write_text(
            json.dumps(metadata, separators=(",", ":"), sort_keys=True) + "\n",
            encoding="utf-8",
        )
        rewrite_checksums(public)
        replacement_digest = write_gauntlet_receipt(
            accepted,
            VERSION,
            self.accepted_sha,
        )
        self.assertNotEqual(replacement_digest, self.receipt_sha256)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt SHA-256", result.stderr)
        self.assertFalse(self._push_calls())

    def test_success_requires_exact_push_runs_pages_parity_and_then_tags(self) -> None:
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        git_calls = self._git_calls()
        dev_push = f"push {PRODUCTION_PUSH_URL} HEAD:refs/heads/dev"
        main_push = f"push {PRODUCTION_PUSH_URL} HEAD:refs/heads/main"
        tag_push = (
            f"push {PRODUCTION_PUSH_URL} "
            f"refs/tags/v{VERSION}:refs/tags/v{VERSION}"
        )
        self.assertLess(git_calls.index(dev_push), git_calls.index("switch main"))
        tag_call = next(
            call
            for call in git_calls
            if call.startswith(f"tag -a v{VERSION} {self.accepted_sha} -F ")
        )
        self.assertLess(git_calls.index(main_push), git_calls.index(tag_call))
        self.assertIn(tag_push, git_calls)
        self.assertEqual(
            self.tag_message_file.read_text(encoding="utf-8"),
            expected_tag_message(
                self.root / "dist" / "gauntlet" / self.accepted_sha,
                self.receipt_sha256,
            ),
        )
        gh_calls = "\n".join(self._gh_calls())
        self.assertIn(f"run list --repo Luskish/afterlight-pack --workflow pack-ci.yml --branch dev --event push --commit {self.accepted_sha}", gh_calls)
        self.assertIn(f"run list --repo Luskish/afterlight-pack --workflow pack-ci.yml --branch main --event push --commit {self.accepted_sha}", gh_calls)
        self.assertIn("DEV_CI_URL=https://example.invalid/dev/101", result.stdout)
        self.assertIn("MAIN_CI_URL=https://example.invalid/main/202", result.stdout)
        self.assertIn("PAGES_PACK_SHA=", result.stdout)
        self.assertIn("PAGES_INDEX_SHA=", result.stdout)
        curl_calls = self.curl_log.read_text(encoding="utf-8")
        self.assertIn("https://luskish.github.io/afterlight-pack/pack.toml", curl_calls)
        self.assertIn("https://luskish.github.io/afterlight-pack/index.toml", curl_calls)
        for call in curl_calls.splitlines():
            self.assertTrue(call.startswith("--disable "), call)
            self.assertIn("--proto =https", call)
            self.assertIn("--proto-redir =https", call)
            self.assertIn("--tlsv1.2", call)
        self.assertEqual(
            self.client_log.read_text(encoding="utf-8").splitlines(),
            [
                f"dist/gauntlet/{self.accepted_sha}/public/AFTERLIGHT-prism-instance.zip local",
                f"dist/gauntlet/{self.accepted_sha}/public/AFTERLIGHT-prism-instance.zip production "
                + "1" * 64
                + " "
                + "2" * 64,
            ],
        )
        bare_calls = [
            call
            for call in curl_calls.splitlines()
            if "?" not in call and "github.io/afterlight-pack" in call
        ]
        self.assertTrue(bare_calls)
        self.assertGreaterEqual(len(bare_calls), 4)
        self.assertTrue(all("Cache-Control" not in call for call in bare_calls))

    def test_stale_bare_pages_stops_before_client_install_and_tag(self) -> None:
        result = self._run(environment={"FAKE_BARE_STALE": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("GitHub Pages", result.stderr)
        self.assertFalse(self.client_log.exists())
        self.assertFalse(
            any(call.startswith("tag -a ") for call in self._git_calls())
        )

    def test_failed_production_client_install_stops_before_tag(self) -> None:
        result = self._run(environment={"FAKE_CLIENT_EXIT": "17"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            f"push {PRODUCTION_PUSH_URL} HEAD:refs/heads/main",
            self._git_calls(),
        )
        self.assertFalse(
            any(call.startswith("tag -a ") for call in self._git_calls())
        )

    def test_rejects_mismatched_ci_branch_workflow_or_attempt(self) -> None:
        cases = (
            {"FAKE_CI_BRANCH": "main"},
            {"FAKE_CI_WORKFLOW_ID": "778"},
            {"FAKE_CI_ATTEMPT": "0"},
        )
        for environment in cases:
            with self.subTest(environment=environment):
                result = self._run(environment=environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(
                    any(call.startswith("tag -a ") for call in self._git_calls())
                )
                self.gh_log.unlink(missing_ok=True)
                self.git_log.unlink(missing_ok=True)
                self.branch_file.write_text("dev\n", encoding="utf-8")

    def test_release_docs_use_fail_closed_promoter_before_publication(self) -> None:
        releasing = (ROOT / "docs" / "RELEASING.md").read_text(encoding="utf-8")
        release_notes = (ROOT / "docs" / "releases" / "1.0.0-rc.1.md").read_text(
            encoding="utf-8"
        )
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
        self.assertIn(
            "Populate every prepublication automated evidence field",
            releasing,
        )
        self.assertIn("must contain no automated `NOT RUN`", releasing)
        self.assertIn("must contain no automated `PENDING`", releasing)
        self.assertIn("bare and cache-busted", releasing)
        self.assertIn("clean install directly from the public Pages URL", releasing)
        self.assertIn("mod sets and payloads to be byte-identical", releasing)
        self.assertIn("draft GitHub release", releasing)
        self.assertIn("authenticated downloads", releasing)
        self.assertIn("unauthenticated downloads", releasing)
        self.assertIn("pushed descendant of the accepted SHA", releasing)
        self.assertIn(
            'tools/publish-release.sh "$SHA" "$VERSION" "$RECEIPT_SHA256"',
            releasing,
        )
        automated = release_notes.split("## Automated Evidence", 1)[1].split(
            "## Known Boundaries", 1
        )[0]
        self.assertNotIn("Public prerelease URL", automated)
        self.assertNotIn("publication timestamp", automated.casefold())
        self.assertIn("## Postpublication Evidence", release_notes)
        self.assertNotIn("refs/tags/v0.9.0-rc.1^{}", releasing)
        self.assertIn('"tag_name": tag', publisher)
        self.assertIn('"repos/$REPOSITORY/releases/$RELEASE_ID"', publisher)
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
