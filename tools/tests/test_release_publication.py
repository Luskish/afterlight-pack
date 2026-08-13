from __future__ import annotations

import hashlib
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
    write_gauntlet_receipt,
    write_packwiz_source,
    write_public_release,
    write_release_policy,
)


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SCRIPT = ROOT / "tools" / "publish-release.sh"
RELEASE_TOOL = ROOT / "tools" / "release_artifacts.py"
EVIDENCE_SHA = "89abcdef0123456789abcdef0123456789abcdef"
TAG_OBJECT = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
VERSION = "0.9.0-rc.2"


class ReleasePublicationTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        (self.root / "tools").mkdir()
        if PUBLICATION_SCRIPT.exists():
            destination = self.root / "tools" / "publish-release.sh"
            destination.write_bytes(PUBLICATION_SCRIPT.read_bytes())
            destination.chmod(destination.stat().st_mode | stat.S_IXUSR)
        (self.root / "tools" / "release_artifacts.py").write_bytes(
            RELEASE_TOOL.read_bytes()
        )
        write_release_policy(self.root / "tools" / "release-policy.env")

        self.real_git = shutil.which("git")
        self.assertIsNotNone(self.real_git)
        self.accepted_sha = write_packwiz_source(self.root, VERSION)
        self._write_artifacts(VERSION, self.accepted_sha)
        self._write_release_note(VERSION)
        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.curl_log = self.root / "curl.log"
        self.release_state = self.root / "release-state"
        self.create_request_capture = self.root / "create-request.json"
        self.publish_request_capture = self.root / "publish-request.json"
        self.tag_message_file = self.root / "tag-message.txt"
        self.tag_message_file.write_text(
            expected_tag_message(
                self.root / "dist" / "gauntlet" / self.accepted_sha,
                self.receipt_sha256,
            ),
            encoding="utf-8",
        )
        self._install_fakes()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GIT_LOG": str(self.git_log),
                "FAKE_CURL_LOG": str(self.curl_log),
                "FAKE_PUBLIC_ROOT": str(
                    self.root
                    / "dist"
                    / "gauntlet"
                    / self.accepted_sha
                    / "public"
                ),
                "FAKE_RELEASE_STATE": str(self.release_state),
                "FAKE_CREATE_REQUEST_CAPTURE": str(self.create_request_capture),
                "FAKE_PUBLISH_REQUEST_CAPTURE": str(self.publish_request_capture),
                "FAKE_REPLACEMENT_PATH": str(
                    self.root
                    / "dist"
                    / "gauntlet"
                    / self.accepted_sha
                    / "public"
                    / "AFTERLIGHT.mrpack"
                ),
                "FAKE_LOCAL_TAG_OBJECT": TAG_OBJECT,
                "FAKE_HEAD_SHA": EVIDENCE_SHA,
                "FAKE_REMOTE_DEV_SHA": EVIDENCE_SHA,
                "FAKE_REMOTE_MAIN_SHA": self.accepted_sha,
                "FAKE_CHANGED_PATHS": f"docs/releases/{VERSION}.md",
                "FAKE_ORIGIN_URL": "https://github.com/Luskish/afterlight-pack.git",
                "FAKE_SHA": self.accepted_sha,
                "FAKE_REAL_GIT": self.real_git,
                "FAKE_TAG_MESSAGE_FILE": str(self.tag_message_file),
            }
        )

    def _write_executable(self, name, source):
        path = self.fake_bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def _write_pack(self, version):
        pack_path = self.root / "pack.toml"
        pack_text = pack_path.read_text(encoding="utf-8")
        pack_text = pack_text.replace(
            f'version = "{VERSION}"',
            f'version = "{version}"',
            1,
        )
        pack_path.write_text(pack_text, encoding="utf-8")

    def _valid_automated_evidence(self):
        accepted = self.root / "dist" / "gauntlet" / self.accepted_sha
        public = accepted / "public"
        transcript_sha256 = hashlib.sha256(
            (accepted / "gauntlet.txt").read_bytes()
        ).hexdigest()
        lines = [
            f"- Accepted commit and annotated tag target: `{self.accepted_sha}`",
            f"- Local gauntlet receipt SHA-256: `{self.receipt_sha256}`",
            f"- Local gauntlet transcript SHA-256: `{transcript_sha256}`",
            "- Exact accepted `dev` CI URL: `https://example.invalid/dev/101`",
            "- Exact `main` CI URL: `https://example.invalid/main/202`",
            f"- GitHub Pages `pack.toml` SHA-256: `{hashlib.sha256((self.root / 'pack.toml').read_bytes()).hexdigest()}`",
            f"- GitHub Pages `index.toml` SHA-256: `{hashlib.sha256((self.root / 'index.toml').read_bytes()).hexdigest()}`",
            "- Signal source: `a3d95a74a56855a026f9f2786f1e925065a3b151`",
            "- Signal release JAR SHA-256: `81387eff5e6f5dad555a936d605c114af8fff1cf69778251cc3a7ec660f15947`",
            "- Signal release JAR SHA-512: `902d3f64ac6f2e3302da26daefa29cfd03e19f39d293daa81da7b04cb3f115d3e0ed933da189f2622bd1284e6a3292fd7a4ddc6f8c115e3e43d2123e56f7d74f`",
            "- Signal evidence CI: `https://github.com/Luskish/afterlight-signal/actions/runs/31588113497`",
            "",
            "## Public Artifacts",
            "",
        ]
        for name in sorted(
            (
                "AFTERLIGHT-curseforge.zip",
                "AFTERLIGHT-prism-instance.zip",
                "AFTERLIGHT.mrpack",
                "SHA256SUMS",
                "release-metadata.json",
            )
        ):
            path = public / name
            lines.append(
                f"- `{name}`: SHA-256 `{hashlib.sha256(path.read_bytes()).hexdigest()}`, "
                f"size `{path.stat().st_size}` bytes."
            )
        return "\n".join(lines)

    def _write_release_note(self, version, automated=None):
        if automated is None:
            automated = self._valid_automated_evidence()
        release_directory = self.root / "docs" / "releases"
        release_directory.mkdir(parents=True, exist_ok=True)
        (release_directory / f"{version}.md").write_text(
            f"# AFTERLIGHT {version}\n\n"
            "## Automated Evidence\n\n"
            f"{automated}\n\n"
            "## Known Boundaries\n\n"
            "- Manual checks remain separate.\n\n"
            "## Manual Acceptance\n\n"
            "- Player launch: NOT RUN\n",
            encoding="utf-8",
        )

    def _write_artifacts(self, version, git_sha):
        accepted = self.root / "dist" / "gauntlet" / git_sha
        public = accepted / "public"
        write_public_release(public, version, git_sha)
        (accepted / "gauntlet.txt").write_text(
            f"AFTERLIGHT release gauntlet\nSHA: {git_sha}\n",
            encoding="utf-8",
        )
        self.receipt_sha256 = write_gauntlet_receipt(accepted, version, git_sha)

    def _install_fakes(self):
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
              "branch --show-current") printf 'dev\n' ;;
              "rev-parse HEAD") printf '%s\n' "$FAKE_HEAD_SHA" ;;
              "status --porcelain")
                if [ "${FAKE_DIRTY:-0}" = 1 ]; then printf ' M tools/release-policy.env\n'; fi
                ;;
              "remote get-url") printf '%s\n' "$FAKE_ORIGIN_URL" ;;
              "merge-base --is-ancestor")
                [ "${FAKE_NOT_DESCENDANT:-0}" = 0 ]
                ;;
              "diff --name-only")
                if [ -n "${FAKE_CHANGED_PATHS:-}" ]; then
                  while IFS= read -r path; do printf '%s\0' "$path"; done <<< "$FAKE_CHANGED_PATHS"
                fi
                ;;
              "diff --quiet")
                [ "${FAKE_TOOLING_CHANGED:-0}" = 0 ]
                ;;
              "show "*) cat pack.toml ;;
              "cat-file -t") printf '%s\n' "${FAKE_TAG_TYPE:-tag}" ;;
              "rev-parse refs/tags/"*)
                case "${2:-}" in
                  *'^{}') printf '%s\n' "${FAKE_LOCAL_PEELED_SHA:-$FAKE_SHA}" ;;
                  *) printf '%s\n' "$FAKE_LOCAL_TAG_OBJECT" ;;
                esac
                ;;
              "ls-remote origin")
                case "${3:-}" in
                  refs/heads/dev) printf '%s\t%s\n' "$FAKE_REMOTE_DEV_SHA" "${3:-}" ;;
                  refs/heads/main) printf '%s\t%s\n' "$FAKE_REMOTE_MAIN_SHA" "${3:-}" ;;
                  *'^{}') printf '%s\t%s\n' "${FAKE_REMOTE_PEELED_SHA:-$FAKE_SHA}" "${3:-}" ;;
                  *) printf '%s\t%s\n' "${FAKE_REMOTE_TAG_OBJECT:-$FAKE_LOCAL_TAG_OBJECT}" "${3:-}" ;;
                esac
                ;;
              "for-each-ref --format=%(contents)") cat "$FAKE_TAG_MESSAGE_FILE" ;;
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
            asset_id_for_name() {
              case "$1" in
                AFTERLIGHT-curseforge.zip) printf '5001\n' ;;
                AFTERLIGHT-prism-instance.zip) printf '5002\n' ;;
                AFTERLIGHT.mrpack) printf '5003\n' ;;
                SHA256SUMS) printf '5004\n' ;;
                release-metadata.json) printf '5005\n' ;;
                *) printf '5999\n' ;;
              esac
            }
            asset_name_for_id() {
              case "$1" in
                5001) printf 'AFTERLIGHT-curseforge.zip\n' ;;
                5002) printf 'AFTERLIGHT-prism-instance.zip\n' ;;
                5003) printf 'AFTERLIGHT.mrpack\n' ;;
                5004) printf 'SHA256SUMS\n' ;;
                5005) printf 'release-metadata.json\n' ;;
                *) exit 97 ;;
              esac
            }
            asset_inventory() {
              names=${FAKE_ASSETS:-$'AFTERLIGHT-curseforge.zip\nAFTERLIGHT-prism-instance.zip\nAFTERLIGHT.mrpack\nSHA256SUMS\nrelease-metadata.json'}
              first=1
              while IFS= read -r name; do
                [ -n "$name" ] || continue
                id=$(asset_id_for_name "$name")
                size=$(wc -c < "$FAKE_PUBLIC_ROOT/$name" | tr -d ' ')
                if [ "$first" -eq 0 ]; then printf ','; fi
                printf '%s:%s:%s' "$name" "$id" "$size"
                first=0
              done <<< "$names"
              printf '\n'
            }
            if [ "${1:-}" = api ] && [[ " $* " == *" repos/Luskish/afterlight-pack/actions/workflows/pack-ci.yml "* ]]; then
              printf '777\t.github/workflows/pack-ci.yml\tactive\n'
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "run list" ]; then
              [ "${FAKE_GH_NO_CI:-0}" = 0 ] || exit 0
              case " $* " in
                *" --branch dev "*" --commit $FAKE_SHA "*) printf '101\n' ;;
                *" --branch main "*" --commit $FAKE_SHA "*) printf '202\n' ;;
                *" --branch dev "*" --commit $FAKE_HEAD_SHA "*) printf '303\n' ;;
                *) exit 93 ;;
              esac
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "run watch" ]; then
              [ "${FAKE_GH_WATCH_FAIL:-0}" = 0 ]
              exit
            fi
            if [ "${1:-} ${2:-}" = "run view" ]; then
              case "${3:-}" in
                101) printf '%s\tdev\tpush\tcompleted\tsuccess\thttps://example.invalid/dev/101\t%s\t%s\n' "$FAKE_SHA" "${FAKE_CI_WORKFLOW_ID:-777}" "${FAKE_CI_ATTEMPT:-1}" ;;
                202) printf '%s\tmain\tpush\tcompleted\tsuccess\thttps://example.invalid/main/202\t%s\t%s\n' "$FAKE_SHA" "${FAKE_CI_WORKFLOW_ID:-777}" "${FAKE_CI_ATTEMPT:-1}" ;;
                303) printf '%s\t%s\tpush\tcompleted\t%s\thttps://example.invalid/dev/303\t%s\t%s\n' "$FAKE_HEAD_SHA" "${FAKE_CI_BRANCH:-dev}" "${FAKE_CI_CONCLUSION:-success}" "${FAKE_CI_WORKFLOW_ID:-777}" "${FAKE_CI_ATTEMPT:-1}" ;;
                *) exit 94 ;;
              esac
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "release view" ]; then
              if [ ! -e "$FAKE_RELEASE_STATE" ]; then
                if [ "${FAKE_REPLACE_AFTER_VIEW:-0}" = 1 ]; then
                  printf 'post-validation replacement\n' > "$FAKE_REPLACEMENT_PATH"
                fi
                exit 1
              fi
              exit 0
            fi
            if [ "${1:-}" = api ]; then
              method=GET
              input=""
              endpoint=""
              previous=""
              for argument in "$@"; do
                if [ "$previous" = "--method" ]; then method=$argument; fi
                if [ "$previous" = "--input" ]; then input=$argument; fi
                previous=$argument
                case "$argument" in
                  repos/Luskish/afterlight-pack/releases|repos/Luskish/afterlight-pack/releases/4242|repos/Luskish/afterlight-pack/releases/assets/*|https://uploads.github.com/*) endpoint=$argument ;;
                esac
              done
              if [ "$method" = POST ] && [ "$endpoint" = repos/Luskish/afterlight-pack/releases ]; then
                printf 'draft\n' > "$FAKE_RELEASE_STATE"
                [ "${FAKE_CREATE_FAIL:-0}" = 0 ] || exit 24
                cp "$input" "$FAKE_CREATE_REQUEST_CAPTURE"
                if [ "${FAKE_CREATE_MALFORMED:-0}" = 1 ]; then
                  printf 'not-an-id\ttrue\tv0.9.0-rc.2\thttps://uploads.github.com/repos/Luskish/afterlight-pack/releases/4242/assets{?name,label}\n'
                  exit 0
                fi
                printf '4242\t%s\t%s\thttps://uploads.github.com/repos/Luskish/afterlight-pack/releases/4242/assets{?name,label}\n' \
                  "${FAKE_CREATED_DRAFT:-true}" "${FAKE_CREATED_TAG:-v0.9.0-rc.2}"
                exit 0
              fi
              if [ "$method" = POST ] && [[ "$endpoint" == https://uploads.github.com/* ]]; then
                [ "${FAKE_UPLOAD_FAIL:-0}" = 0 ] || exit 25
                name=${endpoint##*?name=}
                id=$(asset_id_for_name "$name")
                size=$(wc -c < "$input" | tr -d ' ')
                printf '%s\t%s\t%s\n' "$id" "$name" "$size"
                exit 0
              fi
              if [ "$method" = GET ] && [ "$endpoint" = repos/Luskish/afterlight-pack/releases/4242 ]; then
                state=$(cat "$FAKE_RELEASE_STATE")
                if [ "$state" = draft ]; then draft=true; else draft=false; fi
                published_at=""
                if [ "$state" = public ] && [ "${FAKE_EMPTY_PUBLISHED_AT:-0}" = 0 ]; then
                  published_at=2026-08-12T12:00:00Z
                fi
                printf '4242|%s|true|v0.9.0-rc.2|https://example.invalid/release|%s|' "$draft" "$published_at"
                asset_inventory
                exit 0
              fi
              if [ "$method" = GET ] && [[ "$endpoint" == repos/Luskish/afterlight-pack/releases/assets/* ]]; then
                id=${endpoint##*/}
                name=$(asset_name_for_id "$id")
                cp "$FAKE_PUBLIC_ROOT/$name" /dev/stdout
                if [ "${FAKE_AUTH_CORRUPT:-0}" = 1 ] && [ "$name" = AFTERLIGHT.mrpack ]; then
                  printf 'corrupt\n'
                fi
                exit 0
              fi
              if [ "$method" = PATCH ] && [ "$endpoint" = repos/Luskish/afterlight-pack/releases/4242 ]; then
                cp "$input" "$FAKE_PUBLISH_REQUEST_CAPTURE"
                printf 'public\n' > "$FAKE_RELEASE_STATE"
                [ "${FAKE_PUBLISH_FAIL:-0}" = 0 ] || exit 26
                exit 0
              fi
              if [ "$method" = DELETE ] && [ "$endpoint" = repos/Luskish/afterlight-pack/releases/4242 ]; then
                [ "${FAKE_DELETE_FAIL:-0}" = 0 ] || exit 23
                rm -f "$FAKE_RELEASE_STATE"
                exit 0
              fi
            fi
            printf 'unexpected fake gh command: %s\n' "$*" >&2
            exit 92
            """,
        )
        self._write_executable(
            "curl",
            r"""
            #!/usr/bin/env bash
            set -u
            printf '%s\n' "$*" >> "$FAKE_CURL_LOG"
            destination=""
            url=""
            previous=""
            for argument in "$@"; do
              if [ "$previous" = "-o" ]; then destination=$argument; fi
              previous=$argument
              case "$argument" in https://*) url=$argument ;; esac
            done
            name=${url##*/}
            cp "$FAKE_PUBLIC_ROOT/$name" "$destination"
            if [ "${FAKE_PUBLIC_CORRUPT:-0}" = 1 ] && [ "$name" = AFTERLIGHT.mrpack ]; then
              printf 'corrupt\n' >> "$destination"
            fi
            """,
        )

    def _run(
        self,
        version=VERSION,
        prerelease=True,
        receipt_sha256=None,
        environment=None,
    ):
        if receipt_sha256 is None:
            receipt_sha256 = self.receipt_sha256
        command = [
            str(self.root / "tools" / "publish-release.sh"),
            self.accepted_sha,
            version,
            receipt_sha256,
        ]
        if prerelease:
            command.append("--prerelease")
        command.append("--confirm")
        command_environment = self.environment.copy()
        if environment:
            command_environment.update(environment)
        return subprocess.run(
            command,
            cwd=self.root,
            env=command_environment,
            capture_output=True,
            text=True,
            check=False,
        )

    def _gh_calls(self):
        if not self.gh_log.exists():
            return []
        return self.gh_log.read_text(encoding="utf-8").splitlines()

    def _create_calls(self):
        return [
            call
            for call in self._gh_calls()
            if call.startswith("api --hostname github.com --method POST ")
            and " repos/Luskish/afterlight-pack/releases " in f" {call} "
        ]

    def _upload_calls(self):
        return [
            call
            for call in self._gh_calls()
            if call.startswith("api --method POST ")
            and " https://uploads.github.com/" in f" {call} "
        ]

    def _publish_calls(self):
        return [
            call
            for call in self._gh_calls()
            if " --method PATCH " in f" {call} "
            and " repos/Luskish/afterlight-pack/releases/4242 " in f" {call} "
        ]

    def _delete_calls(self):
        return [
            call
            for call in self._gh_calls()
            if " --method DELETE " in f" {call} "
            and " repos/Luskish/afterlight-pack/releases/4242 " in f" {call} "
        ]

    def test_publisher_avoids_ambiguous_and_or_guards(self):
        source = PUBLICATION_SCRIPT.read_text(encoding="utf-8")

        self.assertNotRegex(
            source,
            r"\]\s*&&\s*\[\s*!\s*-L\b.*\]\s*\|\|",
        )

    def test_signal_evidence_comes_from_trusted_release_policy(self):
        alternate_source = "7" * 40
        alternate_sha256 = "8" * 64
        alternate_sha512 = "9" * 128
        alternate_ci = (
            "https://github.com/Luskish/afterlight-signal/actions/runs/424242"
        )
        policy_path = self.root / "tools" / "release-policy.env"
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8")
            + f'RELEASE_SIGNAL_SOURCE_SHA="{alternate_source}"\n'
            + f'RELEASE_SIGNAL_JAR_SHA256="{alternate_sha256}"\n'
            + f'RELEASE_SIGNAL_JAR_SHA512="{alternate_sha512}"\n'
            + f'RELEASE_SIGNAL_EVIDENCE_CI_URL="{alternate_ci}"\n',
            encoding="utf-8",
        )
        automated = (
            self._valid_automated_evidence()
            .replace(
                "a3d95a74a56855a026f9f2786f1e925065a3b151",
                alternate_source,
            )
            .replace(
                "81387eff5e6f5dad555a936d605c114af8fff1cf69778251cc3a7ec660f15947",
                alternate_sha256,
            )
            .replace(
                "902d3f64ac6f2e3302da26daefa29cfd03e19f39d293daa81da7b04cb3f115d3e0ed933da189f2622bd1284e6a3292fd7a4ddc6f8c115e3e43d2123e56f7d74f",
                alternate_sha512,
            )
            .replace(
                "https://github.com/Luskish/afterlight-signal/actions/runs/31588113497",
                alternate_ci,
            )
        )
        self._write_release_note(VERSION, automated)

        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_malformed_signal_release_policy(self):
        policy_path = self.root / "tools" / "release-policy.env"
        policy_path.write_text(
            policy_path.read_text(encoding="utf-8")
            + 'RELEASE_SIGNAL_SOURCE_SHA="not-a-commit"\n'
            + 'RELEASE_SIGNAL_JAR_SHA256="not-a-digest"\n'
            + 'RELEASE_SIGNAL_JAR_SHA512="not-a-digest"\n'
            + 'RELEASE_SIGNAL_EVIDENCE_CI_URL="https://attacker.invalid/run"\n',
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Signal release policy", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_dirty_policy_before_sourcing_trusted_values(self):
        marker = self.root / "policy-sourced"
        policy_path = self.root / "tools" / "release-policy.env"
        policy_path.write_text(
            f'touch "{marker}"\n' + policy_path.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        result = self._run(environment={"FAKE_DIRTY": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(marker.exists())
        self.assertFalse(self._create_calls())

    def test_rejects_wrong_origin_or_changed_main_before_release(self):
        cases = (
            {"FAKE_ORIGIN_URL": "git@github.com:attacker/fork.git"},
            {"FAKE_REMOTE_MAIN_SHA": "f" * 40},
        )
        for environment in cases:
            with self.subTest(environment=environment):
                result = self._run(environment=environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)

    def test_disables_git_replace_objects_for_release_control(self):
        result = self._run(environment={"FAKE_REQUIRE_NO_REPLACE": "1"})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_success_attaches_exact_public_inventory(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(self._create_calls()), 1)
        create_call = self._create_calls()[0]
        create_request = json.loads(self.create_request_capture.read_text("utf-8"))
        self.assertEqual(create_request["tag_name"], "v0.9.0-rc.2")
        self.assertEqual(create_request["name"], "AFTERLIGHT 0.9.0-rc.2")
        self.assertTrue(create_request["draft"])
        self.assertTrue(create_request["prerelease"])
        self.assertNotIn("AFTERLIGHT-prism-instance.zip", create_call)
        upload_calls = self._upload_calls()
        self.assertEqual(len(upload_calls), 5)
        for name in (
            "AFTERLIGHT-prism-instance.zip",
            "AFTERLIGHT-curseforge.zip",
            "AFTERLIGHT.mrpack",
            "release-metadata.json",
            "SHA256SUMS",
        ):
            self.assertTrue(any(f"?name={name}" in call for call in upload_calls))
        authenticated_downloads = [
            call
            for call in self._gh_calls()
            if " repos/Luskish/afterlight-pack/releases/assets/" in f" {call} "
        ]
        self.assertEqual(len(authenticated_downloads), 5)
        self.assertEqual(len(self._publish_calls()), 1)
        self.assertEqual(
            json.loads(self.publish_request_capture.read_text("utf-8")),
            {"draft": False},
        )
        self.assertFalse(
            any(
                call.startswith(("release upload ", "release download ", "release edit "))
                for call in self._gh_calls()
            )
        )
        self.assertTrue(self.curl_log.exists())
        for call in self.curl_log.read_text(encoding="utf-8").splitlines():
            self.assertTrue(call.startswith("--disable "), call)
            self.assertIn("--proto =https", call)
            self.assertIn("--proto-redir =https", call)
        self.assertNotIn(f"AFTERLIGHT-{VERSION}", create_call)
        self.assertIn(
            "EVIDENCE_CI_URL=https://example.invalid/dev/303",
            result.stdout,
        )

    def test_draft_failure_preserves_owned_release_for_manual_inspection(self):
        for environment in (
            {"FAKE_UPLOAD_FAIL": "1"},
            {"FAKE_AUTH_CORRUPT": "1"},
        ):
            with self.subTest(environment=environment):
                result = self._run(environment=environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.release_state.read_text("utf-8"), "draft\n")
                self.assertFalse(self._delete_calls())
                self.assertFalse(self._publish_calls())
                self.assertIn("inspect release ID 4242", result.stderr)
                self.gh_log.unlink(missing_ok=True)
                self.release_state.unlink(missing_ok=True)

    def test_ambiguous_create_failure_never_deletes_unowned_release(self):
        result = self._run(environment={"FAKE_CREATE_FAIL": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.release_state.exists())
        self.assertIn("creation outcome is unknown", result.stderr)
        self.assertFalse(self._delete_calls())

    def test_malformed_create_response_never_targets_an_untrusted_release_id(self):
        result = self._run(environment={"FAKE_CREATE_MALFORMED": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unable to identify incomplete release", result.stderr)
        self.assertFalse(self._delete_calls())
        self.assertTrue(self.release_state.exists())

    def test_valid_created_id_is_preserved_before_metadata_checks(self):
        cases = (
            {"FAKE_CREATED_DRAFT": "false"},
            {"FAKE_CREATED_TAG": "v0.9.0-rc.2-wrong"},
        )
        for environment in cases:
            with self.subTest(environment=environment):
                self.gh_log.unlink(missing_ok=True)
                self.release_state.unlink(missing_ok=True)
                result = self._run(environment=environment)
                release_exists = self.release_state.exists()
                delete_calls = self._delete_calls()
                self.gh_log.unlink(missing_ok=True)
                self.release_state.unlink(missing_ok=True)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("inspect release ID 4242", result.stderr)
                self.assertFalse(delete_calls)
                self.assertTrue(release_exists)

    def test_public_byte_failure_preserves_the_published_release(self):
        result = self._run(environment={"FAKE_PUBLIC_CORRUPT": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self._publish_calls()), 1)
        self.assertFalse(self._delete_calls())
        self.assertEqual(self.release_state.read_text("utf-8"), "public\n")

    def test_published_release_requires_timestamp(self):
        result = self._run(environment={"FAKE_EMPTY_PUBLISHED_AT": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("publication timestamp", result.stderr)
        self.assertFalse(self._delete_calls())
        self.assertEqual(self.release_state.read_text("utf-8"), "public\n")

    def test_ambiguous_publish_failure_never_deletes_the_release(self):
        result = self._run(environment={"FAKE_PUBLISH_FAIL": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(len(self._publish_calls()), 1)
        self.assertFalse(self._delete_calls())
        self.assertEqual(self.release_state.read_text("utf-8"), "public\n")

    def test_publisher_never_issues_release_delete_requests(self):
        source = PUBLICATION_SCRIPT.read_text(encoding="utf-8")

        self.assertNotIn("--method DELETE", source)

    def test_rejects_pack_metadata_note_and_tag_identity_mismatches(self):
        cases = ("pack", "metadata-version", "metadata-sha", "note", "tag")
        for case in cases:
            with self.subTest(case=case):
                if case == "pack":
                    self._write_pack("9.9.9")
                elif case.startswith("metadata"):
                    metadata_path = (
                        self.root
                        / "dist"
                        / "gauntlet"
                        / self.accepted_sha
                        / "public"
                        / "release-metadata.json"
                    )
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    metadata["version" if case == "metadata-version" else "git_sha"] = (
                        "9.9.9" if case == "metadata-version" else "f" * 40
                    )
                    metadata_path.write_text(
                        json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8"
                    )
                elif case == "note":
                    self._write_release_note("0.9.0-rc.2", automated="# wrong")
                    note_path = self.root / "docs" / "releases" / "0.9.0-rc.2.md"
                    note_path.write_text(
                        note_path.read_text(encoding="utf-8").replace(
                            "# AFTERLIGHT 0.9.0-rc.2", "# AFTERLIGHT wrong"
                        ),
                        encoding="utf-8",
                    )
                result = self._run(
                    environment={"FAKE_LOCAL_PEELED_SHA": "f" * 40}
                    if case == "tag"
                    else None
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)
                self._write_pack(VERSION)
                self._write_release_note(VERSION)
                metadata_path = (
                    self.root
                    / "dist"
                    / "gauntlet"
                    / self.accepted_sha
                    / "public"
                    / "release-metadata.json"
                )
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["version"] = VERSION
                metadata["git_sha"] = self.accepted_sha
                metadata_path.write_text(
                    json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8"
                )
                rewrite_checksums(metadata_path.parent)

    def test_rejects_automated_not_run_but_allows_manual_not_run(self):
        self._write_release_note(VERSION, automated="- Gauntlet: NOT RUN")
        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("automated NOT RUN", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_pending_automated_evidence(self):
        self._write_release_note(VERSION, automated="- Gauntlet: PENDING PROMOTION")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("automated PENDING", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_missing_fabricated_or_unbound_automated_evidence(self):
        note_path = self.root / "docs" / "releases" / f"{VERSION}.md"
        cases = (
            (f"`{self.accepted_sha}`", f"`{'f' * 40}`"),
            (f"`{self.receipt_sha256}`", f"`{'e' * 64}`"),
            (
                "- Exact `main` CI URL: `https://example.invalid/main/202`\n",
                "",
            ),
            (
                "- GitHub Pages `pack.toml` SHA-256: `",
                "- GitHub Pages `pack.toml` SHA-256: `0",
            ),
            ("SHA-256 `", "SHA-256 `0"),
        )
        for original, replacement in cases:
            with self.subTest(original=original, replacement=replacement):
                self._write_release_note(VERSION)
                note = note_path.read_text(encoding="utf-8")
                self.assertIn(original, note)
                note_path.write_text(
                    note.replace(original, replacement, 1), encoding="utf-8"
                )

                result = self._run()

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("release evidence", result.stderr)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)

    def test_evidence_lines_outside_automated_section_do_not_count(self):
        expected_line = (
            f"- Accepted commit and annotated tag target: `{self.accepted_sha}`"
        )
        automated = self._valid_automated_evidence().replace(
            expected_line,
            "",
            1,
        )
        self._write_release_note(VERSION, automated=automated)
        note_path = self.root / "docs" / "releases" / f"{VERSION}.md"
        note_path.write_text(
            note_path.read_text(encoding="utf-8").replace(
                "- Player launch: NOT RUN",
                f"- Player launch: NOT RUN\n{expected_line}",
                1,
            ),
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release evidence", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_unaccepted_or_non_documentation_checkout(self):
        evidence_sha = "89abcdef0123456789abcdef0123456789abcdef"
        cases = {
            "accepted-without-evidence-child": {
                "FAKE_HEAD_SHA": self.accepted_sha,
                "FAKE_REMOTE_DEV_SHA": self.accepted_sha,
                "FAKE_CHANGED_PATHS": "",
            },
            "not-descendant": {
                "FAKE_HEAD_SHA": evidence_sha,
                "FAKE_REMOTE_DEV_SHA": evidence_sha,
                "FAKE_NOT_DESCENDANT": "1",
            },
            "remote-dev-mismatch": {
                "FAKE_HEAD_SHA": evidence_sha,
                "FAKE_REMOTE_DEV_SHA": "f" * 40,
            },
            "non-documentation-change": {
                "FAKE_HEAD_SHA": evidence_sha,
                "FAKE_REMOTE_DEV_SHA": evidence_sha,
                "FAKE_CHANGED_PATHS": "tools/publish-release.sh",
            },
            "accepted-tooling-change": {
                "FAKE_HEAD_SHA": evidence_sha,
                "FAKE_REMOTE_DEV_SHA": evidence_sha,
                "FAKE_CHANGED_PATHS": "docs/releases/0.9.0-rc.2.md",
                "FAKE_TOOLING_CHANGED": "1",
            },
        }
        for label, environment in cases.items():
            with self.subTest(label=label):
                result = self._run(environment=environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)

    def test_requires_exact_successful_dev_ci_for_current_head(self):
        evidence_sha = "89abcdef0123456789abcdef0123456789abcdef"
        result = self._run(
            environment={
                "FAKE_HEAD_SHA": evidence_sha,
                "FAKE_REMOTE_DEV_SHA": evidence_sha,
                "FAKE_CHANGED_PATHS": "docs/releases/0.9.0-rc.2.md",
                "FAKE_CI_CONCLUSION": "failure",
            }
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

    def test_requires_exact_ci_branch_workflow_and_attempt_identity(self):
        cases = (
            {"FAKE_CI_BRANCH": "main"},
            {"FAKE_CI_WORKFLOW_ID": "778"},
            {"FAKE_CI_ATTEMPT": "0"},
        )
        for environment in cases:
            with self.subTest(environment=environment):
                result = self._run(environment=environment)

                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)

    def test_rejects_public_inventory_changes(self):
        public = self.root / "dist" / "gauntlet" / self.accepted_sha / "public"
        cases = (
            public / "extra.txt",
            public / "friends-only",
            public / f"AFTERLIGHT-{VERSION}.mrpack",
        )
        for extra_path in cases:
            with self.subTest(extra_path=extra_path):
                if extra_path.name == "friends-only":
                    extra_path.mkdir()
                else:
                    extra_path.write_text("extra\n", encoding="utf-8")
                result = self._run()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self._create_calls())
                if extra_path.is_dir():
                    extra_path.rmdir()
                else:
                    extra_path.unlink()
                self.gh_log.unlink(missing_ok=True)

        outside = self.root / "outside.txt"
        outside.write_text("outside\n", encoding="utf-8")
        extra_link = public / "linked-extra.txt"
        extra_link.symlink_to(outside)
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

    def test_rejects_linked_artifact_and_missing_checksum(self):
        public = self.root / "dist" / "gauntlet" / self.accepted_sha / "public"
        mrpack = public / "AFTERLIGHT.mrpack"
        outside = self.root / "outside.mrpack"
        outside.write_bytes(mrpack.read_bytes())
        mrpack.unlink()
        mrpack.symlink_to(outside)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

        mrpack.unlink()
        mrpack.write_bytes(outside.read_bytes())
        self.gh_log.unlink(missing_ok=True)
        checksums = public / "SHA256SUMS"
        checksum_lines = checksums.read_text(encoding="utf-8").splitlines()
        checksums.write_text("\n".join(checksum_lines[1:]) + "\n", encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

    def test_rejects_noncanonical_checksum_format(self):
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
        self.assertFalse(self._create_calls())

    def test_revalidates_immediately_before_release_creation(self):
        result = self._run(environment={"FAKE_REPLACE_AFTER_VIEW": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

    def test_requires_exact_accepted_receipt_digest(self):
        for receipt_sha256 in ("f" * 64, "not-a-digest"):
            with self.subTest(receipt_sha256=receipt_sha256):
                result = self._run(receipt_sha256=receipt_sha256)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("receipt", result.stderr.lower())
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)

    def test_rejects_tag_message_receipt_or_public_hash_replacement(self):
        accepted = self.root / "dist" / "gauntlet" / self.accepted_sha
        original_message = self.tag_message_file.read_text(encoding="utf-8")
        public_hash_lines = original_message.splitlines()
        for index, line in enumerate(public_hash_lines):
            if line.startswith("Public-File-SHA256: "):
                digest = line.split()[1]
                replacement = ("0" if digest[0] != "0" else "1") + digest[1:]
                public_hash_lines[index] = line.replace(digest, replacement, 1)
                break
        changed_public_hash_message = "\n".join(public_hash_lines) + "\n"
        cases = {
            "receipt": original_message.replace(
                self.receipt_sha256,
                "f" * 64,
                1,
            ),
            "public-hash": changed_public_hash_message,
        }
        for case, replacement_message in cases.items():
            with self.subTest(case=case):
                self.tag_message_file.write_text(
                    replacement_message,
                    encoding="utf-8",
                )

                result = self._run()

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("tag message", result.stderr)
                self.assertFalse(self._create_calls())
                self.gh_log.unlink(missing_ok=True)
                self.tag_message_file.write_text(original_message, encoding="utf-8")

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
        self.tag_message_file.write_text(
            expected_tag_message(accepted, replacement_digest),
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt SHA-256", result.stderr)
        self.assertFalse(self._create_calls())

    def test_publication_verification_streams_artifact_hashing(self):
        site_directory = self.root / "python-site"
        site_directory.mkdir()
        (site_directory / "sitecustomize.py").write_text(
            "import pathlib\n"
            "def forbidden_read_bytes(self):\n"
            "    raise RuntimeError('Path.read_bytes is forbidden for release hashing')\n"
            "pathlib.Path.read_bytes = forbidden_read_bytes\n",
            encoding="utf-8",
        )

        result = self._run(environment={"PYTHONPATH": str(site_directory)})

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_rejects_lightweight_local_tag(self):
        result = self._run(environment={"FAKE_TAG_TYPE": "commit"})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("annotated tag", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_replaced_remote_tag_object_with_same_peeled_commit(self):
        result = self._run(environment={"FAKE_REMOTE_TAG_OBJECT": "b" * 40})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tag object IDs", result.stderr)
        self.assertFalse(self._create_calls())

    def test_rejects_private_launcher_metadata_classification(self):
        metadata_path = (
            self.root
            / "dist"
            / "gauntlet"
            / self.accepted_sha
            / "public"
            / "release-metadata.json"
        )
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["private_artifacts"] = [
            "AFTERLIGHT-curseforge.zip",
            "AFTERLIGHT.mrpack",
        ]
        metadata["public_artifacts"] = {
            "AFTERLIGHT-prism-instance.zip": metadata["public_artifacts"][
                "AFTERLIGHT-prism-instance.zip"
            ]
        }
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self._create_calls())

    def test_enforces_prerelease_mode_and_rejects_existing_release(self):
        result = self._run(prerelease=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("requires --prerelease", result.stderr)

        self.release_state.touch()
        result = self._run()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()
