from __future__ import annotations

import hashlib
import json
import os
import stat
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PUBLICATION_SCRIPT = ROOT / "tools" / "publish-release.sh"
SHA = "0123456789abcdef0123456789abcdef01234567"
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

        self._write_pack(VERSION)
        self._write_release_note(VERSION)
        self._write_artifacts(VERSION, SHA)
        self.git_log = self.root / "git.log"
        self.gh_log = self.root / "gh.log"
        self.release_state = self.root / "release-state"
        self._install_fakes()
        self.environment = os.environ.copy()
        self.environment.update(
            {
                "PATH": f"{self.fake_bin}:{self.environment['PATH']}",
                "FAKE_GH_LOG": str(self.gh_log),
                "FAKE_GIT_LOG": str(self.git_log),
                "FAKE_RELEASE_STATE": str(self.release_state),
                "FAKE_SHA": SHA,
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
        private = accepted / "friends-only"
        public.mkdir(parents=True)
        private.mkdir()
        prism = public / "AFTERLIGHT-prism-instance.zip"
        prism.write_bytes(b"prism fixture\n")
        metadata = {
            "format": 2,
            "version": version,
            "git_sha": git_sha,
            "private_artifacts": sorted(
                (
                    f"AFTERLIGHT-{version}-curseforge.zip",
                    f"AFTERLIGHT-{version}.mrpack",
                )
            ),
            "public_artifacts": {
                prism.name: {
                    "sha256": hashlib.sha256(prism.read_bytes()).hexdigest(),
                    "size": prism.stat().st_size,
                }
            },
        }
        metadata_path = public / "release-metadata.json"
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8"
        )
        checksum_lines = []
        for path in sorted((prism, metadata_path)):
            checksum_lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            )
        (public / "SHA256SUMS").write_text(
            "".join(checksum_lines), encoding="utf-8"
        )
        (private / f"AFTERLIGHT-{version}.mrpack").write_bytes(b"mrpack\n")
        (private / f"AFTERLIGHT-{version}-curseforge.zip").write_bytes(
            b"curseforge\n"
        )

    def _install_fakes(self):
        self._write_executable(
            "git",
            r"""
            #!/usr/bin/env bash
            set -u
            printf '%s\n' "$*" >> "$FAKE_GIT_LOG"
            case "${1:-} ${2:-}" in
              "branch --show-current") printf 'dev\n' ;;
              "show "*) cat pack.toml ;;
              "rev-parse refs/tags/"*) printf '%s\n' "${FAKE_TAG_SHA:-$FAKE_SHA}" ;;
              "ls-remote origin") printf '%s\t%s\n' "${FAKE_TAG_SHA:-$FAKE_SHA}" "${3:-}" ;;
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
              if [ ! -e "$FAKE_RELEASE_STATE" ]; then exit 1; fi
              if [[ " $* " == *" --json assets "* ]]; then
                if [ -n "${FAKE_ASSETS:-}" ]; then
                  printf '%s\n' "$FAKE_ASSETS"
                else
                  printf '%s\n' AFTERLIGHT-prism-instance.zip SHA256SUMS release-metadata.json
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

    def _run(self, version=VERSION, prerelease=True, environment=None):
        command = [
            str(self.root / "tools" / "publish-release.sh"),
            SHA,
            version,
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

    def test_success_creates_prerelease_with_only_public_assets(self):
        result = self._run()

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        create_call = next(
            call for call in self._gh_calls() if call.startswith("release create ")
        )
        self.assertIn("v0.9.0-rc.2 --verify-tag --prerelease", create_call)
        self.assertIn("AFTERLIGHT-prism-instance.zip", create_call)
        self.assertIn("release-metadata.json", create_call)
        self.assertIn("SHA256SUMS", create_call)
        self.assertNotIn("mrpack", create_call)
        self.assertNotIn("curseforge", create_call)

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
                    environment={"FAKE_TAG_SHA": "f" * 40} if case == "tag" else None
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

    def test_rejects_automated_not_run_but_allows_manual_not_run(self):
        self._write_release_note(VERSION, automated="- Gauntlet: NOT RUN")
        result = self._run()

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("automated NOT RUN", result.stderr)
        self.assertFalse(
            any(call.startswith("release create ") for call in self._gh_calls())
        )

    def test_rejects_public_or_private_inventory_changes(self):
        public = self.root / "dist" / "gauntlet" / SHA / "public"
        private = self.root / "dist" / "gauntlet" / SHA / "friends-only"
        cases = (
            public / "extra.txt",
            private / "extra.txt",
        )
        for extra_path in cases:
            with self.subTest(extra_path=extra_path):
                extra_path.write_text("extra\n", encoding="utf-8")
                result = self._run()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(
                    any(call.startswith("release create ") for call in self._gh_calls())
                )
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
