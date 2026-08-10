import hashlib
import json
import stat
import tempfile
import unittest
import warnings
import zipfile
from pathlib import Path, PurePosixPath

from tools.release_artifacts import build_prism_archive, inspect_prism_archive


REQUIRED_PRISM_TESTS = {
    "test_same_inputs_produce_byte_identical_archives",
    "test_zip_entries_are_sorted_normalized_and_path_safe",
    "test_only_bootstrap_jar_is_allowed",
    "test_instance_uses_exact_pack_url_and_loader_versions",
    "test_inspection_rejects_wrong_bootstrap_digest",
    "test_inspection_rejects_duplicate_or_parent_paths",
}

EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    "instance.cfg",
    "mmc-pack.json",
)

PACK_URL = "https://luskish.github.io/afterlight-pack/pack.toml"
MINECRAFT_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.1.248"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


class PrismArtifactTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.bootstrap_bytes = b"temporary packwiz bootstrap fixture\n"
        self.bootstrap_path = self.root / "packwiz-installer-bootstrap.jar"
        self.bootstrap_path.write_bytes(self.bootstrap_bytes)
        self.bootstrap_sha256 = hashlib.sha256(self.bootstrap_bytes).hexdigest()

    def _build(self, filename):
        return build_prism_archive(
            self.bootstrap_path,
            self.root / filename,
            PACK_URL,
            MINECRAFT_VERSION,
            NEOFORGE_VERSION,
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
            inspect_prism_archive(crafted_path, PACK_URL, self.bootstrap_sha256)

    def test_only_bootstrap_jar_is_allowed(self):
        archive_path = self._build("allowed.zip")
        summary = inspect_prism_archive(
            archive_path,
            PACK_URL,
            self.bootstrap_sha256,
        )
        self.assertEqual(summary["entry_count"], 3)
        self.assertEqual(
            summary["jar_entries"],
            [".minecraft/packwiz-installer-bootstrap.jar"],
        )

        entries = self._valid_entries()
        entries.append((".minecraft/mods/hidden.jar", b"hidden mod fixture\n"))
        malicious_path = self.root / "hidden-jar.zip"
        self._write_fixture_archive(malicious_path, entries)

        with self.assertRaisesRegex(ValueError, "JAR"):
            inspect_prism_archive(malicious_path, PACK_URL, self.bootstrap_sha256)

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
            inspect_prism_archive(archive_path, PACK_URL, "0" * 64)

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
            inspect_prism_archive(duplicate_path, PACK_URL, self.bootstrap_sha256)

        parent_path = self.root / "parent.zip"
        self._write_fixture_archive(
            parent_path,
            [("../instance.cfg", entries[1][1]), *entries],
        )
        with self.assertRaisesRegex(ValueError, "parent traversal"):
            inspect_prism_archive(parent_path, PACK_URL, self.bootstrap_sha256)


if __name__ == "__main__":
    unittest.main()
