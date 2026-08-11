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
    write_gauntlet_receipt,
    write_public_release,
    write_release_policy,
)


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SCRIPT = ROOT / "tools" / "publish-release.sh"
RELEASE_TOOL = ROOT / "tools" / "release_artifacts.py"
SHA = "0123456789abcdef0123456789abcdef01234567"
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

        self._write_pack(VERSION)
        self._write_release_note(VERSION)
        self._write_artifacts(VERSION, SHA)
        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.release_state = self.root / "release-state"
        self.tag_message_file = self.root / "tag-message.txt"
        self.tag_message_file.write_text(
            expected_tag_message(
                self.root / "dist" / "gauntlet" / SHA,
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
                "FAKE_RELEASE_STATE": str(self.release_state),
                "FAKE_REPLACEMENT_PATH": str(
                    self.root
                    / "dist"
                    / "gauntlet"
                    / SHA
                    / "public"
                    / "AFTERLIGHT.mrpack"
                ),
                "FAKE_LOCAL_TAG_OBJECT": TAG_OBJECT,
                "FAKE_SHA": SHA,
                "FAKE_TAG_MESSAGE_FILE": str(self.tag_message_file),
            }
        )

    def _write_executable(self, name, source):
        path = self.fake_bin / name
        path.write_text(textwrap.dedent(source).lstrip(), encoding="utf-8")
        path.chmod(0o755)

    def _write_pack(self, version):
        (self.root / "pack.toml").write_text(
            f'version = "{version}"\n', encoding="utf-8"
        )

    def _write_release_note(self, version, automated="- Gauntlet: PASS"):
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
        accepted = self.root / "dist" / "gauntlet" / SHA
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
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            case "${1:-} ${2:-}" in
              "branch --show-current") printf 'dev\n' ;;
              "rev-parse HEAD") printf '%s\n' "$FAKE_SHA" ;;
              "status --porcelain")
                if [ "${FAKE_DIRTY:-0}" = 1 ]; then printf ' M tools/release-policy.env\n'; fi
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
            if [ "${1:-} ${2:-}" = "release view" ]; then
              if [ ! -e "$FAKE_RELEASE_STATE" ]; then
                if [ "${FAKE_REPLACE_AFTER_VIEW:-0}" = 1 ]; then
                  printf 'post-validation replacement\n' > "$FAKE_REPLACEMENT_PATH"
                fi
                exit 1
              fi
              if [[ " $* " == *" --json assets "* ]]; then
                if [ -n "${FAKE_ASSETS:-}" ]; then
                  printf '%s\n' "$FAKE_ASSETS"
                else
                  printf '%s\n' AFTERLIGHT-curseforge.zip AFTERLIGHT-prism-instance.zip AFTERLIGHT.mrpack SHA256SUMS release-metadata.json
                fi
              fi
              exit 0
            fi
            if [ "${1:-} ${2:-}" = "release create" ]; then
              : > "$FAKE_RELEASE_STATE"
              exit 0
            fi
            printf 'unexpected fake gh command: %s\n' "$*" >&2
            exit 92
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
            SHA,
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

    def test_publisher_avoids_ambiguous_and_or_guards(self):
        source = PUBLICATION_SCRIPT.read_text(encoding="utf-8")

        self.assertNotRegex(
            source,
            r"\]\s*&&\s*\[\s*!\s*-L\b.*\]\s*\|\|",
        )

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
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_success_attaches_exact_public_inventory(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        create_call = next(
            call for call in self._gh_calls() if call.startswith("release create ")
        )
        self.assertIn("v0.9.0-rc.2 --verify-tag --prerelease", create_call)
        self.assertIn("AFTERLIGHT-prism-instance.zip", create_call)
        self.assertIn("AFTERLIGHT-curseforge.zip", create_call)
        self.assertIn("AFTERLIGHT.mrpack", create_call)
        self.assertIn("release-metadata.json", create_call)
        self.assertIn("SHA256SUMS", create_call)
        self.assertNotIn(f"AFTERLIGHT-{VERSION}", create_call)

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
                        / SHA
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
                self.assertFalse(
                    any(call.startswith("release create ") for call in self._gh_calls())
                )
                self.gh_log.unlink(missing_ok=True)
                self._write_pack(VERSION)
                self._write_release_note(VERSION)
                metadata_path = (
                    self.root
                    / "dist"
                    / "gauntlet"
                    / SHA
                    / "public"
                    / "release-metadata.json"
                )
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                metadata["version"] = VERSION
                metadata["git_sha"] = SHA
                metadata_path.write_text(
                    json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8"
                )
                rewrite_checksums(metadata_path.parent)

    def test_rejects_automated_not_run_but_allows_manual_not_run(self):
        self._write_release_note(VERSION, automated="- Gauntlet: NOT RUN")
        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("automated NOT RUN", result.stderr)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_public_inventory_changes(self):
        public = self.root / "dist" / "gauntlet" / SHA / "public"
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
                self.assertFalse(
                    any(call.startswith("release create ") for call in self._gh_calls())
                )
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
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_linked_artifact_and_missing_checksum(self):
        public = self.root / "dist" / "gauntlet" / SHA / "public"
        mrpack = public / "AFTERLIGHT.mrpack"
        outside = self.root / "outside.mrpack"
        outside.write_bytes(mrpack.read_bytes())
        mrpack.unlink()
        mrpack.symlink_to(outside)

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

        mrpack.unlink()
        mrpack.write_bytes(outside.read_bytes())
        self.gh_log.unlink(missing_ok=True)
        checksums = public / "SHA256SUMS"
        checksum_lines = checksums.read_text(encoding="utf-8").splitlines()
        checksums.write_text("\n".join(checksum_lines[1:]) + "\n", encoding="utf-8")

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_noncanonical_checksum_format(self):
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
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_revalidates_immediately_before_release_creation(self):
        result = self._run(environment={"FAKE_REPLACE_AFTER_VIEW": "1"})

        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_requires_exact_accepted_receipt_digest(self):
        for receipt_sha256 in ("f" * 64, "not-a-digest"):
            with self.subTest(receipt_sha256=receipt_sha256):
                result = self._run(receipt_sha256=receipt_sha256)

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("receipt", result.stderr.lower())
                self.assertFalse(
                    any(call.startswith("release create ") for call in self._gh_calls())
                )
                self.gh_log.unlink(missing_ok=True)

    def test_rejects_tag_message_receipt_or_public_hash_replacement(self):
        accepted = self.root / "dist" / "gauntlet" / SHA
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
                self.assertFalse(
                    any(call.startswith("release create ") for call in self._gh_calls())
                )
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
        replacement_digest = write_gauntlet_receipt(accepted, VERSION, SHA)
        self.assertNotEqual(replacement_digest, self.receipt_sha256)
        self.tag_message_file.write_text(
            expected_tag_message(accepted, replacement_digest),
            encoding="utf-8",
        )

        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("receipt SHA-256", result.stderr)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

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
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_replaced_remote_tag_object_with_same_peeled_commit(self):
        result = self._run(environment={"FAKE_REMOTE_TAG_OBJECT": "b" * 40})

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tag object IDs", result.stderr)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_private_launcher_metadata_classification(self):
        metadata_path = (
            self.root
            / "dist"
            / "gauntlet"
            / SHA
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
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

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
