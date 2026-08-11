import hashlib
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path, PurePosixPath

from tools.release_artifacts import build_prism_archive, inspect_prism_archive
from tools.tests.release_fixtures import (
    rewrite_checksums,
    rewrite_metadata,
    write_empty_zip,
    write_public_release,
)


REQUIRED_PRISM_TESTS = {
    "test_same_inputs_produce_byte_identical_archives",
    "test_zip_entries_are_sorted_normalized_and_path_safe",
    "test_only_approved_installer_jars_are_allowed",
    "test_instance_uses_exact_pack_url_and_loader_versions",
    "test_inspection_rejects_wrong_bootstrap_digest",
    "test_inspection_rejects_wrong_installer_digest_or_size",
    "test_inspection_rejects_duplicate_or_parent_paths",
}

REQUIRED_RELEASE_POLICY_TESTS = {
    "test_public_launcher_archive_allows_mod_jars_but_rejects_secrets",
    "test_public_file_set_is_exactly_the_canonical_inventory",
    "test_metadata_binds_version_commit_pack_url_size_and_sha256",
    "test_checksums_are_sorted_and_cover_every_public_artifact",
    "test_repository_scan_rejects_tracked_jar_secret_and_u2014",
    "test_archive_scan_rejects_absolute_parent_duplicate_and_symlink_entries",
}

EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    ".minecraft/packwiz-installer.jar",
    "instance.cfg",
    "mmc-pack.json",
)

PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
MINECRAFT_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.248"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
RELEASE_VERSION = "0.9.0-rc.1"
RELEASE_GIT_SHA = "0123456789abcdef0123456789abcdef01234567"
BOOTSTRAP_VERSION = "0.0.3"
BOOTSTRAP_SIZE = 98989
BOOTSTRAP_SHA256 = (
    "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c"
)
INSTALLER_VERSION = "0.5.14"
INSTALLER_SIZE = 4378828
INSTALLER_SHA256 = (
    "c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598"
)
PUBLIC_RELEASE_FILES = {
    "AFTERLIGHT-curseforge.zip",
    "AFTERLIGHT-prism-instance.zip",
    "AFTERLIGHT.mrpack",
    "release-metadata.json",
    "SHA256SUMS",
}
PUBLIC_ARTIFACT_FILES = PUBLIC_RELEASE_FILES - {"release-metadata.json", "SHA256SUMS"}
REVIEWED_SKILL_SYMLINKS = {
    ".claude/skills/ftb-quests": "../../.agents/skills/ftb-quests",
    ".claude/skills/kubejs-modding": "../../.agents/skills/kubejs-modding",
    ".claude/skills/minecraft-modding": "../../.agents/skills/minecraft-modding",
    ".claude/skills/minecraft-modpack-authoring": (
        "../../.agents/skills/minecraft-modpack-authoring"
    ),
    ".claude/skills/modrinth-api": "../../.agents/skills/modrinth-api",
    ".claude/skills/neoforge-modding": "../../.agents/skills/neoforge-modding",
}
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RELEASE_TOOL = REPOSITORY_ROOT / "tools" / "release_artifacts.py"
BUILD_RELEASE = REPOSITORY_ROOT / "tools" / "build-release.sh"
PACK_CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "pack-ci.yml"


class PrismArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.bootstrap_bytes = b"temporary packwiz bootstrap fixture\n"
        self.bootstrap_path = self.root / "packwiz-installer-bootstrap.jar"
        self.bootstrap_path.write_bytes(self.bootstrap_bytes)
        self.bootstrap_sha256 = hashlib.sha256(self.bootstrap_bytes).hexdigest()
        self.installer_bytes = b"temporary packwiz installer fixture\n"
        self.installer_path = self.root / "packwiz-installer.jar"
        self.installer_path.write_bytes(self.installer_bytes)
        self.installer_sha256 = hashlib.sha256(self.installer_bytes).hexdigest()
        self.installer_size = len(self.installer_bytes)

    def _build(self, filename):
        return build_prism_archive(
            self.bootstrap_path,
            self.installer_path,
            self.root / filename,
            PACK_URL,
            MINECRAFT_VERSION,
            NEOFORGE_VERSION,
        )

    def _inspect(self, archive_path):
        return inspect_prism_archive(
            archive_path,
            PACK_URL,
            self.bootstrap_sha256,
            self.installer_sha256,
            self.installer_size,
        )

    def _normalized_info(self, name):
        info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
        info.create_system = 3
        info.external_attr = (stat.S_IFREG | 0o644) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        return info

    def _write_fixture_archive(self, archive_path, entries):
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for name, data in entries:
                archive.writestr(
                    self._normalized_info(name),
                    data,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )

    def _valid_entries(self):
        archive_path = self._build("valid.zip")
        with zipfile.ZipFile(archive_path) as archive:
            return [(info.filename, archive.read(info)) for info in archive.infolist()]

    def test_same_inputs_produce_byte_identical_archives(self):
        first = self._build("first.zip")
        second = self._build("second.zip")

        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_zip_entries_are_sorted_normalized_and_path_safe(self):
        archive_path = self._build("normalized.zip")

        with zipfile.ZipFile(archive_path) as archive:
            infos = archive.infolist()

        self.assertEqual(tuple(info.filename for info in infos), EXPECTED_PRISM_NAMES)
        self.assertEqual([info.filename for info in infos], sorted(EXPECTED_PRISM_NAMES))
        for info in infos:
            path = PurePosixPath(info.filename)
            self.assertFalse(path.is_absolute())
            self.assertNotIn("", path.parts)
            self.assertNotIn(".", path.parts)
            self.assertNotIn("..", path.parts)
            self.assertNotIn("\\", info.filename)
            self.assertEqual(info.date_time, FIXED_TIMESTAMP)
            self.assertEqual(info.create_system, 3)
            self.assertEqual(
                info.external_attr,
                (stat.S_IFREG | 0o644) << 16,
            )
            self.assertEqual(info.compress_type, zipfile.ZIP_DEFLATED)
            self.assertEqual(info.flag_bits, 0)

    def test_inspection_rejects_lower_dos_directory_flag(self):
        valid_path = self._build("valid-external-attr.zip")
        with zipfile.ZipFile(valid_path) as source:
            entries = [(info, source.read(info)) for info in source.infolist()]

        crafted_path = self.root / "dos-directory-flag.zip"
        with zipfile.ZipFile(
            crafted_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for info, data in entries:
                if info.filename == "instance.cfg":
                    info.external_attr |= 0x10
                archive.writestr(
                    info,
                    data,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )

        with self.assertRaisesRegex(ValueError, "external attributes"):
            self._inspect(crafted_path)

    def test_only_approved_installer_jars_are_allowed(self):
        archive_path = self._build("allowed.zip")
        summary = self._inspect(archive_path)
        self.assertEqual(summary["entry_count"], 4)
        self.assertEqual(
            summary["jar_entries"],
            [
                ".minecraft/packwiz-installer-bootstrap.jar",
                ".minecraft/packwiz-installer.jar",
            ],
        )

        entries = self._valid_entries()
        entries.append((".minecraft/mods/hidden.jar", b"hidden mod fixture\n"))
        malicious_path = self.root / "hidden-jar.zip"
        self._write_fixture_archive(malicious_path, entries)

        with self.assertRaisesRegex(ValueError, "JAR"):
            self._inspect(malicious_path)

    def test_instance_uses_exact_pack_url_and_loader_versions(self):
        archive_path = self._build("instance.zip")

        with zipfile.ZipFile(archive_path) as archive:
            instance_config = archive.read("instance.cfg").decode("utf-8")
            mmc_pack = json.loads(archive.read("mmc-pack.json"))

        self.assertEqual(
            instance_config,
            "InstanceType=OneSix\n"
            "name=AFTERLIGHT\n"
            "iconKey=default\n"
            "OverrideCommands=true\n"
            'PreLaunchCommand="$INST_JAVA" -jar '
            "packwiz-installer-bootstrap.jar "
            "--bootstrap-no-update "
            "--bootstrap-main-jar packwiz-installer.jar -g "
            "https://luskish.github.io/afterlight-pack/pack.toml\n",
        )
        self.assertEqual(
            mmc_pack,
            {
                "components": [
                    {
                        "important": True,
                        "uid": "net.minecraft",
                        "version": "1.21.1",
                    },
                    {"uid": "net.neoforged", "version": "21.1.248"},
                ],
                "formatVersion": 1,
            },
        )

    def test_inspection_rejects_wrong_bootstrap_digest(self):
        archive_path = self._build("wrong-digest.zip")

        with self.assertRaisesRegex(ValueError, "bootstrap SHA-256"):
            inspect_prism_archive(
                archive_path,
                PACK_URL,
                "0" * 64,
                self.installer_sha256,
                self.installer_size,
            )

    def test_inspection_rejects_wrong_installer_digest_or_size(self):
        archive_path = self._build("wrong-installer.zip")

        with self.assertRaisesRegex(ValueError, "installer SHA-256"):
            inspect_prism_archive(
                archive_path,
                PACK_URL,
                self.bootstrap_sha256,
                "0" * 64,
                self.installer_size,
            )

        with self.assertRaisesRegex(ValueError, "installer size"):
            inspect_prism_archive(
                archive_path,
                PACK_URL,
                self.bootstrap_sha256,
                self.installer_sha256,
                self.installer_size + 1,
            )

    def test_inspection_rejects_mutable_installer_command(self):
        entries = self._valid_entries()
        mutable_config = next(data for name, data in entries if name == "instance.cfg")
        mutable_config = mutable_config.replace(
            b" --bootstrap-no-update --bootstrap-main-jar packwiz-installer.jar -g",
            b"",
        )
        crafted_path = self.root / "mutable-command.zip"
        self._write_fixture_archive(
            crafted_path,
            [
                (name, mutable_config if name == "instance.cfg" else data)
                for name, data in entries
            ],
        )

        with self.assertRaisesRegex(ValueError, "exact Packwiz launch command"):
            self._inspect(crafted_path)

    def test_inspection_rejects_duplicate_or_parent_paths(self):
        entries = self._valid_entries()

        duplicate_path = self.root / "duplicate.zip"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            self._write_fixture_archive(
                duplicate_path,
                [*entries, ("instance.cfg", entries[1][1])],
            )
        with self.assertRaisesRegex(ValueError, "duplicate"):
            self._inspect(duplicate_path)

        parent_path = self.root / "parent.zip"
        self._write_fixture_archive(
            parent_path,
            [("../instance.cfg", entries[1][1]), *entries],
        )
        with self.assertRaisesRegex(ValueError, "parent traversal"):
            self._inspect(parent_path)


class ReleasePolicyTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.fixture_number = 0
        self.fake_bin = self.root / "fake-bin"
        self.fake_bin.mkdir()
        fake_curl = self.fake_bin / "curl"
        fake_curl.write_text("#!/usr/bin/env bash\nexit 97\n", encoding="utf-8")
        fake_curl.chmod(0o755)
        fake_packwiz = self.fake_bin / "packwiz"
        fake_packwiz.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_packwiz.chmod(0o755)

    def _run_tool(self, *arguments):
        return subprocess.run(
            [sys.executable, str(RELEASE_TOOL), *map(str, arguments)],
            cwd=REPOSITORY_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def _assert_tool_succeeds(self, result):
        self.assertEqual(
            result.returncode,
            0,
            msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
        )

    def _run_release_build(
        self, dist_directory, pack_url=None, environment_overrides=None
    ):
        environment = os.environ.copy()
        environment.update(
            {
                "DIST_DIR": str(dist_directory),
                "PATH_EXTRA": str(self.fake_bin),
            }
        )
        if pack_url is not None:
            environment["PACK_URL"] = pack_url
        else:
            environment.pop("PACK_URL", None)
        if environment_overrides:
            environment.update(environment_overrides)
        return subprocess.run(
            [str(BUILD_RELEASE)],
            cwd=REPOSITORY_ROOT,
            env=environment,
            check=False,
            capture_output=True,
            text=True,
        )

    def _new_repository(self, tracked_files=None, symlink=None, unreadable=None):
        self.fixture_number += 1
        repository = self.root / f"repository-{self.fixture_number}"
        repository.mkdir()
        subprocess.run(
            ["git", "init", "--quiet", str(repository)],
            check=True,
            capture_output=True,
            text=True,
        )

        tracked_paths = []
        for relative_path, data in (tracked_files or {}).items():
            path = repository / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            tracked_paths.append(relative_path)

        if symlink is not None:
            relative_path, target = symlink
            path = repository / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(target)
            tracked_paths.append(relative_path)

        if unreadable is not None:
            relative_path, data = unreadable
            path = repository / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            tracked_paths.append(relative_path)

        if tracked_paths:
            subprocess.run(
                ["git", "-C", str(repository), "add", "--", *tracked_paths],
                check=True,
                capture_output=True,
                text=True,
            )

        if unreadable is not None:
            unreadable_path = repository / unreadable[0]
            unreadable_path.chmod(0)
            self.addCleanup(unreadable_path.chmod, 0o600)

        return repository

    def _write_archive(self, name, entries):
        self.fixture_number += 1
        archive_path = self.root / f"{self.fixture_number}-{name}"
        with zipfile.ZipFile(
            archive_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for entry_name, data, external_attr in entries:
                info = zipfile.ZipInfo(entry_name, FIXED_TIMESTAMP)
                info.create_system = 3
                info.external_attr = external_attr
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(
                    info,
                    data,
                    compress_type=zipfile.ZIP_DEFLATED,
                    compresslevel=9,
                )
        return archive_path

    def _regular_entry(self, name, data=b"safe fixture\n"):
        return name, data, (stat.S_IFREG | 0o644) << 16

    def _modrinth_manifest_entry(
        self,
        *,
        minecraft=MINECRAFT_VERSION,
        neoforge=NEOFORGE_VERSION,
        loader="neoforge",
        version=RELEASE_VERSION,
    ):
        dependencies = {"minecraft": minecraft, loader: neoforge}
        manifest = {
            "formatVersion": 1,
            "game": "minecraft",
            "versionId": version,
            "name": "AFTERLIGHT",
            "files": [],
            "dependencies": dependencies,
        }
        return self._regular_entry(
            "modrinth.index.json",
            (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"),
        )

    def _curseforge_manifest_entry(
        self,
        *,
        minecraft=MINECRAFT_VERSION,
        neoforge=NEOFORGE_VERSION,
        loader="neoforge",
        version=RELEASE_VERSION,
    ):
        manifest = {
            "minecraft": {
                "version": minecraft,
                "modLoaders": [
                    {"id": f"{loader}-{neoforge}", "primary": True}
                ],
            },
            "manifestType": "minecraftModpack",
            "manifestVersion": 1,
            "name": "AFTERLIGHT",
            "version": version,
            "author": "Shane + ECHO",
            "projectID": 0,
            "files": [],
            "overrides": "overrides",
        }
        return self._regular_entry(
            "manifest.json",
            (json.dumps(manifest, sort_keys=True) + "\n").encode("utf-8"),
        )

    def _inspect_public_launcher(self, archive_path):
        return self._run_tool(
            "inspect-modrinth",
            "--archive",
            archive_path,
            "--version",
            RELEASE_VERSION,
        )

    def _inspect_curseforge(self, archive_path):
        return self._run_tool(
            "inspect-curseforge",
            "--archive",
            archive_path,
            "--version",
            RELEASE_VERSION,
        )

    def _write_release_inputs(self, directory, prism_bytes=b"p"):
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "AFTERLIGHT-prism-instance.zip").write_bytes(prism_bytes)
        (directory / "AFTERLIGHT.mrpack").write_bytes(b"public mrpack\n")
        (directory / "AFTERLIGHT-curseforge.zip").write_bytes(
            b"public curseforge\n"
        )

    def _write_metadata_fixture(self, directory):
        metadata = {
            "format": 3,
            "version": RELEASE_VERSION,
            "git_sha": RELEASE_GIT_SHA,
            "minecraft": MINECRAFT_VERSION,
            "neoforge": NEOFORGE_VERSION,
            "pack_url": PACK_URL,
            "packwiz": {
                "bootstrap": {
                    "version": BOOTSTRAP_VERSION,
                    "size": BOOTSTRAP_SIZE,
                    "sha256": BOOTSTRAP_SHA256,
                },
                "installer": {
                    "version": INSTALLER_VERSION,
                    "size": INSTALLER_SIZE,
                    "sha256": INSTALLER_SHA256,
                },
            },
            "public_artifacts": {
                artifact_name: {
                    "sha256": hashlib.sha256(
                        (directory / artifact_name).read_bytes()
                    ).hexdigest(),
                    "size": (directory / artifact_name).stat().st_size,
                }
                for artifact_name in sorted(PUBLIC_ARTIFACT_FILES)
            },
        }
        metadata_bytes = (json.dumps(metadata, sort_keys=True) + "\n").encode("utf-8")
        (directory / "release-metadata.json").write_bytes(metadata_bytes)
        return metadata_bytes

    def test_public_launcher_archive_allows_mod_jars_but_rejects_secrets(self):
        legitimate_archive = self._write_archive(
            "legitimate-mod-names.zip",
            [
                self._modrinth_manifest_entry(),
                self._regular_entry("overrides/mods/secretroomsmod.jar"),
                self._regular_entry("overrides/mods/tokenizer.jar"),
                self._regular_entry("overrides/mods/credentialed.jar"),
            ],
        )
        result = self._inspect_public_launcher(legitimate_archive)
        self._assert_tool_succeeds(result)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["classification"], "public")
        self.assertEqual(summary["embedded_jar_count"], 3)

        secret_paths = (
            "overrides/secret/settings.txt",
            "overrides/api-token.txt",
            "overrides/client_credential.json",
            "overrides/server.env",
            "overrides/.env.production",
            "overrides/rcon_password.txt",
        )
        for secret_path in secret_paths:
            with self.subTest(secret_path=secret_path):
                archive_path = self._write_archive(
                    "secret-path.zip",
                    [self._regular_entry(secret_path)],
                )
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("secret-bearing path", result.stderr)

    def test_archive_content_rejects_nonempty_credentials_under_neutral_paths(self):
        fixtures = (
            ("overrides/config/service.toml", b'api_key = "sk-live-fixture"\n'),
            ("overrides/config/client.json", b'{"token":"token-fixture-value"}\n'),
            ("overrides/config/login.cfg", b"password: hunter2-fixture\n"),
            ("overrides/config/runtime.ini", b"secret = actual-fixture-secret\n"),
            ("overrides/server.properties", b"rcon.password=fixture-rcon-value\n"),
        )
        for member_name, content in fixtures:
            with self.subTest(member_name=member_name):
                archive_path = self._write_archive(
                    "neutral-path-credential.zip",
                    [
                        self._modrinth_manifest_entry(),
                        self._regular_entry(member_name, content),
                    ],
                )
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("credential assignment", result.stderr)

    def test_archive_content_allows_words_and_empty_or_template_credentials(self):
        archive_path = self._write_archive(
            "credential-false-positives.zip",
            [
                self._modrinth_manifest_entry(),
                self._regular_entry(
                    "overrides/config/readme.txt",
                    b"Password recovery tokens are ordinary documentation words.\n",
                ),
                self._regular_entry(
                    "overrides/config/templates.toml",
                    b'password = ""\napi_key = "${API_KEY}"\nsecret = "CHANGEME"\n',
                ),
                self._regular_entry(
                    "overrides/config/defaults.json",
                    b'{"token":"<TOKEN>","rcon_password":null}\n',
                ),
            ],
        )

        result = self._inspect_public_launcher(archive_path)

        self._assert_tool_succeeds(result)

    def test_format_specific_launchers_require_expected_manifests(self):
        modrinth_archive = self._write_archive(
            "valid.mrpack",
            [
                self._modrinth_manifest_entry(),
                self._regular_entry("overrides/config/example.cfg"),
            ],
        )
        curseforge_archive = self._write_archive(
            "valid-curseforge.zip",
            [
                self._curseforge_manifest_entry(),
                self._regular_entry("overrides/config/example.cfg"),
            ],
        )

        for result, expected_format in (
            (self._inspect_public_launcher(modrinth_archive), "modrinth"),
            (self._inspect_curseforge(curseforge_archive), "curseforge"),
        ):
            with self.subTest(expected_format=expected_format):
                self._assert_tool_succeeds(result)
                summary = json.loads(result.stdout)
                self.assertEqual(summary["format"], expected_format)
                self.assertEqual(summary["minecraft"], MINECRAFT_VERSION)
                self.assertEqual(summary["neoforge"], NEOFORGE_VERSION)

    def test_format_specific_launchers_reject_empty_malformed_and_wrong_identity(self):
        empty_archive = self._write_archive("empty.zip", [])
        malformed_modrinth = self._write_archive(
            "malformed.mrpack",
            [self._regular_entry("modrinth.index.json", b"{not-json\n")],
        )
        malformed_curseforge = self._write_archive(
            "malformed-curseforge.zip",
            [self._regular_entry("manifest.json", b"{not-json\n")],
        )
        cases = (
            (self._inspect_public_launcher, empty_archive, "manifest"),
            (self._inspect_curseforge, empty_archive, "manifest"),
            (self._inspect_public_launcher, malformed_modrinth, "valid UTF-8 JSON"),
            (self._inspect_curseforge, malformed_curseforge, "valid UTF-8 JSON"),
        )
        for inspector, archive_path, expected_error in cases:
            with self.subTest(archive_path=archive_path, expected_error=expected_error):
                result = inspector(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

        identity_cases = (
            (
                self._inspect_public_launcher,
                self._modrinth_manifest_entry(loader="forge"),
                "NeoForge",
            ),
            (
                self._inspect_public_launcher,
                self._modrinth_manifest_entry(minecraft="1.20.1"),
                "Minecraft",
            ),
            (
                self._inspect_curseforge,
                self._curseforge_manifest_entry(loader="forge"),
                "NeoForge",
            ),
            (
                self._inspect_curseforge,
                self._curseforge_manifest_entry(neoforge="21.1.200"),
                "NeoForge",
            ),
        )
        for inspector, manifest_entry, expected_error in identity_cases:
            with self.subTest(expected_error=expected_error, manifest=manifest_entry[0]):
                archive_path = self._write_archive(
                    "wrong-launcher-identity.zip",
                    [manifest_entry],
                )
                result = inspector(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_final_public_release_verifier_accepts_exact_real_launcher_inventory(self):
        public = self.root / "verified-public"
        write_public_release(public, RELEASE_VERSION, RELEASE_GIT_SHA)

        result = self._run_tool(
            "verify-public-release",
            "--dist-dir",
            public,
            "--version",
            RELEASE_VERSION,
            "--git-sha",
            RELEASE_GIT_SHA,
        )

        self._assert_tool_succeeds(result)
        summary = json.loads(result.stdout)
        self.assertEqual(summary["version"], RELEASE_VERSION)
        self.assertEqual(summary["git_sha"], RELEASE_GIT_SHA)
        self.assertEqual(
            summary["formats"],
            {
                "AFTERLIGHT-curseforge.zip": "curseforge",
                "AFTERLIGHT-prism-instance.zip": "prism",
                "AFTERLIGHT.mrpack": "modrinth",
            },
        )

    def test_final_public_release_verifier_rejects_metadata_and_inventory_attacks(self):
        public = self.root / "attacked-public"
        cases = {
            "malformed-json": "valid UTF-8 JSON",
            "wrong-format": "format must be 3",
            "wrong-version": "version does not match",
            "wrong-sha": "SHA does not match",
            "extra": "inventory",
        }
        for case, expected_error in cases.items():
            with self.subTest(case=case):
                if public.exists():
                    for child in public.iterdir():
                        if child.is_dir() and not child.is_symlink():
                            child.rmdir()
                        else:
                            child.unlink()
                    public.rmdir()
                write_public_release(public, RELEASE_VERSION, RELEASE_GIT_SHA)
                metadata_path = public / "release-metadata.json"
                if case == "malformed-json":
                    metadata_path.write_text("{not-json\n", encoding="utf-8")
                elif case != "extra":
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    if case == "wrong-format":
                        metadata["format"] = 2
                    elif case == "wrong-version":
                        metadata["version"] = "9.9.9"
                    else:
                        metadata["git_sha"] = "f" * 40
                    metadata_path.write_text(
                        json.dumps(metadata, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                else:
                    (public / "extra.txt").write_text("extra\n", encoding="utf-8")
                if case != "extra":
                    rewrite_checksums(public)

                result = self._run_tool(
                    "verify-public-release",
                    "--dist-dir",
                    public,
                    "--version",
                    RELEASE_VERSION,
                    "--git-sha",
                    RELEASE_GIT_SHA,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_final_public_release_verifier_reinspects_self_consistent_replacements(self):
        public = self.root / "replaced-public"
        artifacts = {
            "AFTERLIGHT-curseforge.zip": "CurseForge manifest",
            "AFTERLIGHT-prism-instance.zip": "Prism archive",
            "AFTERLIGHT.mrpack": "Modrinth manifest",
        }
        for artifact_name, expected_error in artifacts.items():
            with self.subTest(artifact_name=artifact_name):
                if public.exists():
                    for child in public.iterdir():
                        child.unlink()
                    public.rmdir()
                write_public_release(public, RELEASE_VERSION, RELEASE_GIT_SHA)
                write_empty_zip(public / artifact_name)
                rewrite_metadata(public, RELEASE_VERSION, RELEASE_GIT_SHA)
                rewrite_checksums(public)

                result = self._run_tool(
                    "verify-public-release",
                    "--dist-dir",
                    public,
                    "--version",
                    RELEASE_VERSION,
                    "--git-sha",
                    RELEASE_GIT_SHA,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_public_launcher_archive_rejects_malformed_zip(self):
        malformed_archive = self.root / "malformed-launcher.zip"
        malformed_archive.write_bytes(b"not a ZIP archive\n")

        result = self._inspect_public_launcher(malformed_archive)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a zip file", result.stderr.lower())

    def test_public_file_set_is_exactly_the_canonical_inventory(self):
        dist_directory = self.root / "public-file-set"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)
        self._assert_tool_succeeds(result)

        covered_files = {
            line.split("  ", 1)[1]
            for line in (dist_directory / "SHA256SUMS").read_text(
                encoding="utf-8"
            ).splitlines()
        }
        self.assertEqual(
            {path.name for path in dist_directory.iterdir()},
            PUBLIC_RELEASE_FILES,
        )
        self.assertEqual(
            covered_files,
            PUBLIC_RELEASE_FILES - {"SHA256SUMS"},
        )

    def test_metadata_binds_version_commit_pack_url_size_and_sha256(self):
        dist_directory = self.root / "metadata"
        self._write_release_inputs(dist_directory, prism_bytes=b"p")

        result = self._run_tool(
            "write-metadata",
            "--dist-dir",
            dist_directory,
            "--version",
            RELEASE_VERSION,
            "--git-sha",
            RELEASE_GIT_SHA,
            "--minecraft",
            MINECRAFT_VERSION,
            "--neoforge",
            NEOFORGE_VERSION,
            "--pack-url",
            PACK_URL,
            "--bootstrap-version",
            BOOTSTRAP_VERSION,
            "--bootstrap-size",
            str(BOOTSTRAP_SIZE),
            "--bootstrap-sha256",
            BOOTSTRAP_SHA256,
            "--installer-version",
            INSTALLER_VERSION,
            "--installer-size",
            str(INSTALLER_SIZE),
            "--installer-sha256",
            INSTALLER_SHA256,
        )
        self._assert_tool_succeeds(result)

        expected = {
            "format": 3,
            "version": RELEASE_VERSION,
            "git_sha": RELEASE_GIT_SHA,
            "minecraft": MINECRAFT_VERSION,
            "neoforge": NEOFORGE_VERSION,
            "pack_url": PACK_URL,
            "packwiz": {
                "bootstrap": {
                    "version": BOOTSTRAP_VERSION,
                    "size": BOOTSTRAP_SIZE,
                    "sha256": BOOTSTRAP_SHA256,
                },
                "installer": {
                    "version": INSTALLER_VERSION,
                    "size": INSTALLER_SIZE,
                    "sha256": INSTALLER_SHA256,
                },
            },
            "public_artifacts": {
                artifact_name: {
                    "sha256": hashlib.sha256(
                        (dist_directory / artifact_name).read_bytes()
                    ).hexdigest(),
                    "size": (dist_directory / artifact_name).stat().st_size,
                }
                for artifact_name in sorted(PUBLIC_ARTIFACT_FILES)
            },
        }
        metadata_path = dist_directory / "release-metadata.json"
        self.assertEqual(json.loads(metadata_path.read_bytes()), expected)
        self.assertEqual(
            metadata_path.read_bytes(),
            (json.dumps(expected, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )

    def test_metadata_rejects_malformed_git_sha(self):
        malformed_values = (
            "0" * 39,
            "0" * 41,
            "g" * 40,
            "ABCDEF0123456789abcdef0123456789abcdef01",
        )
        for git_sha in malformed_values:
            with self.subTest(git_sha=git_sha):
                dist_directory = self.root / f"bad-sha-{len(git_sha)}-{git_sha[:1]}"
                self._write_release_inputs(dist_directory)
                result = self._run_tool(
                    "write-metadata",
                    "--dist-dir",
                    dist_directory,
                    "--version",
                    RELEASE_VERSION,
                    "--git-sha",
                    git_sha,
                    "--minecraft",
                    MINECRAFT_VERSION,
                    "--neoforge",
                    NEOFORGE_VERSION,
                    "--pack-url",
                    PACK_URL,
                    "--bootstrap-version",
                    BOOTSTRAP_VERSION,
                    "--bootstrap-size",
                    str(BOOTSTRAP_SIZE),
                    "--bootstrap-sha256",
                    BOOTSTRAP_SHA256,
                    "--installer-version",
                    INSTALLER_VERSION,
                    "--installer-size",
                    str(INSTALLER_SIZE),
                    "--installer-sha256",
                    INSTALLER_SHA256,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("40 lowercase hexadecimal", result.stderr)
                self.assertFalse((dist_directory / "release-metadata.json").exists())

    def test_checksums_are_sorted_and_cover_every_public_artifact(self):
        dist_directory = self.root / "checksums"
        prism_bytes = b"prism fixture\n"
        self._write_release_inputs(dist_directory, prism_bytes=prism_bytes)
        metadata_bytes = self._write_metadata_fixture(dist_directory)

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)
        self._assert_tool_succeeds(result)

        expected = "".join(
            f"{hashlib.sha256((dist_directory / artifact_name).read_bytes()).hexdigest()}  "
            f"{artifact_name}\n"
            for artifact_name in sorted(
                PUBLIC_RELEASE_FILES - {"SHA256SUMS"}
            )
        )
        checksum_path = dist_directory / "SHA256SUMS"
        self.assertEqual(checksum_path.read_text(encoding="utf-8"), expected)
        self.assertNotIn("SHA256SUMS", expected)

    def test_checksums_reject_noncanonical_inventory_entries(self):
        cases = (
            ("friends-only", "directory"),
            (f"AFTERLIGHT-{RELEASE_VERSION}.mrpack", "file"),
            (f"AFTERLIGHT-{RELEASE_VERSION}-curseforge.zip", "file"),
            ("stale-public-build.zip", "file"),
        )
        for entry_name, entry_kind in cases:
            with self.subTest(entry_name=entry_name):
                dist_directory = self.root / f"noncanonical-{entry_name}"
                self._write_release_inputs(dist_directory)
                self._write_metadata_fixture(dist_directory)
                entry_path = dist_directory / entry_name
                if entry_kind == "directory":
                    entry_path.mkdir()
                else:
                    entry_path.write_bytes(b"noncanonical\n")

                result = self._run_tool(
                    "write-checksums",
                    "--dist-dir",
                    dist_directory,
                )

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("release output", result.stderr)
                self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_checksums_reject_links_and_missing_public_artifacts(self):
        dist_directory = self.root / "linked-artifact"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)
        target = self.root / "outside.mrpack"
        target.write_bytes((dist_directory / "AFTERLIGHT.mrpack").read_bytes())
        (dist_directory / "AFTERLIGHT.mrpack").unlink()
        (dist_directory / "AFTERLIGHT.mrpack").symlink_to(target)

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not a regular file", result.stderr)
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

        dist_directory = self.root / "missing-artifact"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)
        (dist_directory / "AFTERLIGHT-curseforge.zip").unlink()

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn(
            "public artifact AFTERLIGHT-curseforge.zip is missing",
            result.stderr,
        )
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_checksums_reject_private_launcher_classification(self):
        dist_directory = self.root / "private-classification"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)
        metadata_path = dist_directory / "release-metadata.json"
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

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("public artifact classification", result.stderr)
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_checksums_reject_unclassified_release_output(self):
        dist_directory = self.root / "unclassified-output"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)
        (dist_directory / "stale-public-build.zip").write_bytes(b"stale\n")

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unclassified release output", result.stderr)
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_checksums_reject_replaced_prism(self):
        dist_directory = self.root / "replaced-prism"
        self._write_release_inputs(dist_directory, prism_bytes=b"original\n")
        self._write_metadata_fixture(dist_directory)
        (dist_directory / "AFTERLIGHT-prism-instance.zip").write_bytes(b"replaced\n")

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Prism SHA-256 mismatch", result.stderr)
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_checksums_reject_invalid_or_mismatched_prism_size(self):
        invalid_sizes = (0, -1, "1", True)
        for invalid_size in invalid_sizes:
            with self.subTest(invalid_size=invalid_size):
                dist_directory = self.root / f"invalid-size-{invalid_size!r}"
                self._write_release_inputs(dist_directory)
                self._write_metadata_fixture(dist_directory)
                metadata_path = dist_directory / "release-metadata.json"
                metadata = json.loads(metadata_path.read_bytes())
                metadata["public_artifacts"]["AFTERLIGHT-prism-instance.zip"][
                    "size"
                ] = invalid_size
                metadata_path.write_text(
                    json.dumps(metadata, sort_keys=True) + "\n",
                    encoding="utf-8",
                )

                result = self._run_tool(
                    "write-checksums",
                    "--dist-dir",
                    dist_directory,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("positive integer", result.stderr)
                self.assertFalse((dist_directory / "SHA256SUMS").exists())

        dist_directory = self.root / "mismatched-size"
        self._write_release_inputs(dist_directory)
        self._write_metadata_fixture(dist_directory)
        metadata_path = dist_directory / "release-metadata.json"
        metadata = json.loads(metadata_path.read_bytes())
        metadata["public_artifacts"]["AFTERLIGHT-prism-instance.zip"]["size"] = 2
        metadata_path.write_text(
            json.dumps(metadata, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        result = self._run_tool("write-checksums", "--dist-dir", dist_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Prism size mismatch", result.stderr)
        self.assertFalse((dist_directory / "SHA256SUMS").exists())

    def test_repository_scan_rejects_tracked_jar_secret_and_u2014(self):
        cases = (
            ("tracked JAR", {"mods/unsafe.jar": b"safe fixture\n"}),
            (
                "private-key header",
                {
                    "config/signing.txt": (
                        b"-----BEGIN OPENSSH " b"PRIVATE KEY-----\nfixture\n"
                    )
                },
            ),
            ("U+2014", {"docs/story.txt": b"before\xe2\x80\x94after\n"}),
        )
        for expected_error, tracked_files in cases:
            with self.subTest(expected_error=expected_error):
                repository = self._new_repository(tracked_files=tracked_files)
                result = self._run_tool(
                    "scan-repository",
                    "--root",
                    repository,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_repository_scan_rejects_private_runtime_paths(self):
        runtime_paths = (
            "dist/output.txt",
            "server-test/evidence.txt",
            "server/data/world.dat",
            "server/backups/world.tar",
        )
        for runtime_path in runtime_paths:
            with self.subTest(runtime_path=runtime_path):
                repository = self._new_repository(
                    tracked_files={runtime_path: b"safe fixture\n"}
                )
                result = self._run_tool(
                    "scan-repository",
                    "--root",
                    repository,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("tracked runtime path", result.stderr)

    def test_repository_scan_rejects_invalid_tracked_path_bytes(self):
        repository = self._new_repository()
        object_id = subprocess.run(
            ["git", "-C", str(repository), "hash-object", "-w", "--stdin"],
            input=b"safe fixture\n",
            check=True,
            capture_output=True,
        ).stdout.strip()
        subprocess.run(
            ["git", "-C", str(repository), "update-index", "-z", "--index-info"],
            input=b"100644 " + object_id + b"\tinvalid-\xff-name.txt\0",
            check=True,
            capture_output=True,
        )

        result = self._run_tool(
            "scan-repository",
            "--root",
            repository,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("tracked path is not valid UTF-8", result.stderr)

    def test_repository_scan_rejects_u2014_in_tracked_path_bytes(self):
        repository = self._new_repository(
            tracked_files={"docs/before\u2014after.txt": b"safe fixture\n"}
        )

        result = self._run_tool(
            "scan-repository",
            "--root",
            repository,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("U+2014 found in tracked path", result.stderr)

    def test_repository_scan_binds_each_path_to_exact_index_object(self):
        repository = self._new_repository(
            tracked_files={
                "safe.txt": b"safe fixture\n",
                "0:safe.txt": (
                    b"-----BEGIN OPENSSH " b"PRIVATE KEY-----\nfixture\n"
                ),
            }
        )

        result = self._run_tool(
            "scan-repository",
            "--root",
            repository,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private-key header", result.stderr)

    def test_repository_scan_reads_index_blobs_not_worktree_paths(self):
        symlink_repository = self._new_repository(
            symlink=("linked.txt", "untracked-target.txt")
        )
        (symlink_repository / "untracked-target.txt").write_bytes(
            b"-----BEGIN OPENSSH " b"PRIVATE KEY-----\nbefore\xe2\x80\x94after\n"
        )
        result = self._run_tool(
            "scan-repository",
            "--root",
            symlink_repository,
        )
        self._assert_tool_succeeds(result)

        changed_repository = self._new_repository(
            tracked_files={"changed.txt": b"safe index fixture\n"}
        )
        (changed_repository / "changed.txt").write_bytes(
            b"-----BEGIN RSA " b"PRIVATE KEY-----\nbefore\xe2\x80\x94after\n"
        )
        result = self._run_tool(
            "scan-repository",
            "--root",
            changed_repository,
        )
        self._assert_tool_succeeds(result)

        unreadable_repository = self._new_repository(
            unreadable=("locked.txt", b"safe fixture\n")
        )
        result = self._run_tool(
            "scan-repository",
            "--root",
            unreadable_repository,
        )
        self._assert_tool_succeeds(result)

        missing_repository = self._new_repository(
            tracked_files={"missing.txt": b"safe fixture\n"}
        )
        (missing_repository / "missing.txt").unlink()
        result = self._run_tool(
            "scan-repository",
            "--root",
            missing_repository,
        )
        self._assert_tool_succeeds(result)

    def test_repository_scan_preserves_reviewed_skill_symlinks(self):
        before = {}
        for relative_path, expected_target in REVIEWED_SKILL_SYMLINKS.items():
            path = REPOSITORY_ROOT / relative_path
            self.assertTrue(path.is_symlink(), msg=relative_path)
            self.assertEqual(os.readlink(path), expected_target)
            before[relative_path] = (path.lstat(), os.readlink(path))

            index_entry = subprocess.run(
                [
                    "git",
                    "-C",
                    str(REPOSITORY_ROOT),
                    "ls-files",
                    "-s",
                    "--",
                    relative_path,
                ],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertTrue(index_entry.startswith("120000 "), msg=index_entry)
            index_blob = subprocess.run(
                [
                    "git",
                    "-C",
                    str(REPOSITORY_ROOT),
                    "cat-file",
                    "blob",
                    f":{relative_path}",
                ],
                check=True,
                capture_output=True,
            ).stdout
            self.assertEqual(index_blob, expected_target.encode("utf-8"))

        result = self._run_tool(
            "scan-repository",
            "--root",
            REPOSITORY_ROOT,
        )
        self._assert_tool_succeeds(result)

        after = {
            relative_path: (path.lstat(), os.readlink(path))
            for relative_path in REVIEWED_SKILL_SYMLINKS
            for path in [REPOSITORY_ROOT / relative_path]
        }
        self.assertEqual(after, before)

    def test_repository_scan_ignores_untracked_policy_violations(self):
        untracked_cases = (
            ("mods/untracked.jar", b"safe fixture\n"),
            ("config/untracked-token.txt", b"safe fixture\n"),
            ("story.txt", b"before\xe2\x80\x94after\n"),
        )
        for relative_path, data in untracked_cases:
            with self.subTest(relative_path=relative_path):
                repository = self._new_repository(
                    tracked_files={"tracked.txt": b"safe fixture\n"}
                )
                untracked_path = repository / relative_path
                untracked_path.parent.mkdir(parents=True, exist_ok=True)
                untracked_path.write_bytes(data)
                result = self._run_tool(
                    "scan-repository",
                    "--root",
                    repository,
                )
                self._assert_tool_succeeds(result)

    def test_repository_scan_allows_nonsecret_marker_names(self):
        repository = self._new_repository(
            tracked_files={
                "server/.env.example": b"DATA_DIR=/safe/example\n",
                "tools/versions.env": b"VERSION=fixture\n",
                "docs/progression-token-recovery.md": b"safe documentation\n",
            }
        )

        result = self._run_tool(
            "scan-repository",
            "--root",
            repository,
        )
        self._assert_tool_succeeds(result)

    def test_archive_scan_rejects_absolute_parent_duplicate_and_symlink_entries(self):
        fixtures = []
        fixtures.append(
            (
                "absolute path",
                self._write_archive(
                    "absolute.zip",
                    [self._regular_entry("/absolute.txt")],
                ),
            )
        )
        fixtures.append(
            (
                "absolute path",
                self._write_archive(
                    "drive-absolute.zip",
                    [self._regular_entry("C:/absolute.txt")],
                ),
            )
        )
        fixtures.append(
            (
                "parent traversal",
                self._write_archive(
                    "parent.zip",
                    [self._regular_entry("../parent.txt")],
                ),
            )
        )

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            duplicate_archive = self._write_archive(
                "duplicate.zip",
                [
                    self._regular_entry("overrides/config.txt"),
                    self._regular_entry("overrides/config.txt"),
                ],
            )
        fixtures.append(("duplicate archive entry", duplicate_archive))

        symlink_archive = self._write_archive(
            "symlink.zip",
            [
                (
                    "overrides/link",
                    b"target.txt",
                    (stat.S_IFLNK | 0o777) << 16,
                )
            ],
        )
        fixtures.append(("symlink archive entry", symlink_archive))

        for expected_error, archive_path in fixtures:
            with self.subTest(expected_error=expected_error):
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)

    def test_archive_scan_rejects_encrypted_entries_and_private_key_headers(self):
        encrypted_archive = self._write_archive(
            "encrypted.zip",
            [self._regular_entry("overrides/config.txt")],
        )
        raw_archive = bytearray(encrypted_archive.read_bytes())
        for signature, flag_offset in ((b"PK\x03\x04", 6), (b"PK\x01\x02", 8)):
            position = raw_archive.find(signature)
            self.assertNotEqual(position, -1)
            flags_position = position + flag_offset
            flags = int.from_bytes(raw_archive[flags_position : flags_position + 2], "little")
            raw_archive[flags_position : flags_position + 2] = (flags | 1).to_bytes(
                2, "little"
            )
        encrypted_archive.write_bytes(raw_archive)

        result = self._inspect_public_launcher(encrypted_archive)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("encrypted archive entry", result.stderr)

        private_key_archive = self._write_archive(
            "private-key.zip",
            [
                self._regular_entry(
                    "overrides/config.txt",
                    b"-----BEGIN RSA " b"PRIVATE KEY-----\nfixture\n",
                )
            ],
        )
        result = self._inspect_public_launcher(private_key_archive)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private-key header", result.stderr)

    def test_archive_scan_rejects_local_only_encryption_flag(self):
        archive_path = self._write_archive(
            "local-only-encrypted.zip",
            [self._regular_entry("overrides/config.txt")],
        )
        raw_archive = bytearray(archive_path.read_bytes())
        position = raw_archive.find(b"PK\x03\x04")
        self.assertNotEqual(position, -1)
        flags_position = position + 6
        flags = int.from_bytes(raw_archive[flags_position : flags_position + 2], "little")
        raw_archive[flags_position : flags_position + 2] = (flags | 1).to_bytes(
            2, "little"
        )
        archive_path.write_bytes(raw_archive)

        result = self._inspect_public_launcher(archive_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("encrypted archive entry", result.stderr)

    def test_archive_scan_rejects_central_only_encryption_flag(self):
        archive_path = self._write_archive(
            "central-only-encrypted.zip",
            [self._regular_entry("overrides/config.txt")],
        )
        raw_archive = bytearray(archive_path.read_bytes())
        position = raw_archive.find(b"PK\x01\x02")
        self.assertNotEqual(position, -1)
        flags_position = position + 8
        flags = int.from_bytes(raw_archive[flags_position : flags_position + 2], "little")
        raw_archive[flags_position : flags_position + 2] = (flags | 1).to_bytes(
            2, "little"
        )
        archive_path.write_bytes(raw_archive)

        result = self._inspect_public_launcher(archive_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("encrypted archive entry", result.stderr)

    def test_archive_scan_rejects_non_encryption_flag_mismatch(self):
        archive_path = self._write_archive(
            "flag-mismatch.zip",
            [self._regular_entry("overrides/config.txt")],
        )
        raw_archive = bytearray(archive_path.read_bytes())
        position = raw_archive.find(b"PK\x03\x04")
        self.assertNotEqual(position, -1)
        flags_position = position + 6
        flags = int.from_bytes(raw_archive[flags_position : flags_position + 2], "little")
        raw_archive[flags_position : flags_position + 2] = (flags | (1 << 3)).to_bytes(
            2, "little"
        )
        archive_path.write_bytes(raw_archive)

        result = self._inspect_public_launcher(archive_path)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("local and central ZIP flags differ", result.stderr)

    def test_archive_scan_rejects_normalized_name_aliases(self):
        aliases = (
            ("overrides/item", "overrides/item/"),
            ("overrides/Config.txt", "overrides/config.txt"),
            ("overrides/caf\u00e9.txt", "overrides/cafe\u0301.txt"),
        )
        for first_name, second_name in aliases:
            with self.subTest(first_name=first_name, second_name=second_name):
                archive_path = self._write_archive(
                    "normalized-alias.zip",
                    [
                        self._regular_entry(first_name),
                        self._regular_entry(second_name),
                    ],
                )
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("duplicate archive entry", result.stderr)

    def test_archive_scan_rejects_windows_unsafe_path_components(self):
        unsafe_names = (
            "overrides/NUL",
            "overrides/CON.txt",
            "overrides/config:stream.txt",
            "overrides/trailing-dot.",
            "overrides/trailing-space ",
            "overrides/control-\x01.txt",
        )
        for unsafe_name in unsafe_names:
            with self.subTest(unsafe_name=unsafe_name):
                archive_path = self._write_archive(
                    "windows-unsafe.zip",
                    [
                        self._modrinth_manifest_entry(),
                        self._regular_entry(unsafe_name),
                    ],
                )
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Windows-unsafe archive entry", result.stderr)

    def test_archive_scan_rejects_windows_normalized_collisions(self):
        aliases = (
            ("overrides/Config.txt", "overrides/config.txt"),
            ("overrides/dir/Item.cfg", "OVERRIDES/DIR/item.cfg"),
        )
        for first_name, second_name in aliases:
            with self.subTest(first_name=first_name, second_name=second_name):
                archive_path = self._write_archive(
                    "windows-collision.zip",
                    [
                        self._modrinth_manifest_entry(),
                        self._regular_entry(first_name),
                        self._regular_entry(second_name),
                    ],
                )
                result = self._inspect_public_launcher(archive_path)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Windows-normalized archive collision", result.stderr)

    def test_release_build_rejects_symlink_output_without_touching_target(self):
        target_directory = self.root / "symlink-target"
        target_directory.mkdir()
        sentinel = target_directory / "AFTERLIGHT-prism-instance.zip"
        sentinel.write_bytes(b"sentinel\n")
        output_link = self.root / "release-output"
        output_link.symlink_to(target_directory, target_is_directory=True)

        result = self._run_release_build(output_link)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(sentinel.exists(), msg=result.stdout + result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"sentinel\n")
        self.assertEqual(
            {path.name for path in target_directory.iterdir()},
            {sentinel.name},
        )
        self.assertIn("symlink", result.stdout + result.stderr)

    def test_release_build_exports_before_writing_staged_prism(self):
        source = BUILD_RELEASE.read_text(encoding="utf-8")

        export_position = source.index(
            'DIST_DIR="$STAGING_DIR" ./tools/export.sh'
        )
        prism_position = source.index(
            'OUTPUT="$PRISM_ZIP" PACK_URL="$PACK_URL" ./tools/build-prism-instance.sh'
        )
        self.assertLess(export_position, prism_position)

    def test_release_build_failure_preserves_existing_output(self):
        output_directory = self.root / "existing-output"
        output_directory.mkdir()
        sentinel = output_directory / "AFTERLIGHT-prism-instance.zip"
        sentinel.write_bytes(b"existing release\n")

        result = self._run_release_build(output_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("download packwiz-installer-bootstrap", result.stderr)
        self.assertTrue(sentinel.exists(), msg=result.stdout + result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"existing release\n")
        self.assertEqual(
            {path.name for path in output_directory.iterdir()},
            {sentinel.name},
        )

    def test_release_build_accepts_existing_empty_output(self):
        output_directory = self.root / "existing-empty-output"
        output_directory.mkdir()

        result = self._run_release_build(output_directory)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("download packwiz-installer-bootstrap", result.stderr)
        self.assertNotIn("unbound variable", result.stderr)
        self.assertTrue(output_directory.is_dir())
        self.assertEqual(list(output_directory.iterdir()), [])

    def test_release_build_rejects_parent_basename(self):
        unsafe_parent = self.root / "unsafe-parent"
        unsafe_parent.mkdir()
        output_directory = unsafe_parent / "child" / ".."

        result = self._run_release_build(output_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("release output directory is unsafe", result.stderr)

    def test_release_build_preserves_unclassified_existing_content(self):
        output_directory = self.root / "existing-output-with-unrelated-content"
        gauntlet_directory = output_directory / "gauntlet"
        gauntlet_directory.mkdir(parents=True)
        sentinel = gauntlet_directory / "sentinel.txt"
        sentinel.write_bytes(b"must survive\n")

        result = self._run_release_build(output_directory)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unclassified release output entry", result.stderr)
        self.assertTrue(sentinel.exists(), msg=result.stdout + result.stderr)
        self.assertEqual(sentinel.read_bytes(), b"must survive\n")
        self.assertEqual(
            {path.name for path in output_directory.iterdir()},
            {gauntlet_directory.name},
        )

    def test_release_build_rejects_pack_url_override(self):
        output_directory = self.root / "custom-url-output"

        result = self._run_release_build(
            output_directory,
            pack_url="https://attacker.invalid/pack.toml",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("PACK_URL override is not allowed", result.stderr)
        self.assertFalse(output_directory.exists())

    def test_release_build_rejects_installer_pin_overrides(self):
        output_directory = self.root / "bootstrap-override-output"

        result = self._run_release_build(
            output_directory,
            environment_overrides={
                "PACKWIZ_BOOTSTRAP_VERSION": "9.9.9",
                "PACKWIZ_BOOTSTRAP_SHA256": "f" * 64,
                "PACKWIZ_INSTALLER_VERSION": "9.9.9",
                "PACKWIZ_INSTALLER_SHA256": "e" * 64,
                "PACKWIZ_INSTALLER_SIZE": "1",
            },
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("approved packwiz installer pins", result.stderr.lower())
        self.assertNotIn("download packwiz-installer-bootstrap", result.stderr)
        self.assertFalse(output_directory.exists())


class ReleaseWorkflowPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = PACK_CI_WORKFLOW.read_text(encoding="utf-8")

    def _step_block(self, step_name):
        marker = f"      - name: {step_name}\n"
        start = self.workflow.index(marker)
        next_step = self.workflow.find("\n      - ", start + len(marker))
        if next_step == -1:
            return self.workflow[start:]
        return self.workflow[start:next_step]

    def test_public_release_build_runs_only_on_trusted_events(self):
        build_step = self._step_block("Build release")
        self.assertIn(
            "if: github.event_name == 'push' || "
            "github.event_name == 'workflow_dispatch'",
            build_step,
        )
        self.assertEqual(build_step.count("./tools/build-release.sh"), 1)

    def test_pull_requests_keep_all_read_only_verification_steps(self):
        required_steps = (
            "Python tests",
            "Verify pack",
            "Headless server boot smoke test",
            "Render Docker Compose config",
            "ShellCheck",
            "Verify generated files are unchanged",
            "Verify worktree is clean",
        )
        for step_name in required_steps:
            with self.subTest(step_name=step_name):
                step_block = self._step_block(step_name)
                self.assertNotIn("github.event_name", step_block)


if __name__ == "__main__":
    unittest.main()
