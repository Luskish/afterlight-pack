import hashlib
import tempfile
import textwrap
import unittest
from pathlib import Path

from tools.client_install_support import (
    expected_mod_inventory,
    validate_client_install,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CLIENT_SCRIPT = REPOSITORY_ROOT / "tools" / "client-install-test.sh"


class ClientInventoryTests(unittest.TestCase):
    def setUp(self):
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.root = Path(temporary_directory.name)
        self.metadata = self.root / "metadata"
        self.instance = self.root / "instance"
        self.mods = self.instance / "mods"
        self.metadata.mkdir()
        self.mods.mkdir(parents=True)

    def _write_metadata(self, stem, filename, side):
        source = textwrap.dedent(
            f"""\
            name = "{stem}"
            filename = "{filename}"
            side = "{side}"

            [download]
            url = "https://example.invalid/{filename}"
            hash-format = "sha256"
            hash = "{'0' * 64}"
            """
        )
        (self.metadata / f"{stem}.pw.toml").write_text(source, encoding="utf-8")

    def test_inventory_classifies_client_both_and_server_sides(self):
        self._write_metadata("client", "client.jar", "client")
        self._write_metadata("shared", "shared.jar", "both")
        self._write_metadata("server", "server.jar", "server")

        client_required, server_only = expected_mod_inventory(self.metadata)

        self.assertEqual(client_required, {"client.jar", "shared.jar"})
        self.assertEqual(server_only, {"server.jar"})

    def test_inventory_rejects_missing_side_duplicate_and_nonjar_filename(self):
        (self.metadata / "missing.pw.toml").write_text(
            'name = "missing"\nfilename = "missing.jar"\n', encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "deliberate side"):
            expected_mod_inventory(self.metadata)

        (self.metadata / "missing.pw.toml").unlink()
        self._write_metadata("first", "duplicate.jar", "both")
        self._write_metadata("second", "duplicate.jar", "client")
        with self.assertRaisesRegex(ValueError, "duplicate mod filename"):
            expected_mod_inventory(self.metadata)

        (self.metadata / "second.pw.toml").unlink()
        self._write_metadata("not_jar", "readme.txt", "client")
        with self.assertRaisesRegex(ValueError, "must end with .jar"):
            expected_mod_inventory(self.metadata)

    def test_validate_client_install_reports_exact_counts_and_digest(self):
        self._write_metadata("client", "client.jar", "client")
        self._write_metadata("shared", "shared.jar", "both")
        self._write_metadata("server", "server.jar", "server")
        (self.mods / "client.jar").write_bytes(b"client fixture\n")
        (self.mods / "shared.jar").write_bytes(b"shared fixture\n")

        summary = validate_client_install(self.instance, self.metadata)

        lines = []
        for filename in ("client.jar", "shared.jar"):
            digest = hashlib.sha256((self.mods / filename).read_bytes()).hexdigest()
            lines.append(f"{digest}  {filename}\n")
        expected_digest = hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()
        self.assertEqual(
            summary,
            {
                "client_mod_count": 2,
                "server_only_count": 1,
                "modset_sha256": expected_digest,
            },
        )

    def test_validate_client_install_rejects_missing_unexpected_and_server_jar(self):
        self._write_metadata("client", "client.jar", "client")
        self._write_metadata("server", "server.jar", "server")

        with self.assertRaisesRegex(ValueError, "missing client mod"):
            validate_client_install(self.instance, self.metadata)

        (self.mods / "client.jar").write_bytes(b"client\n")
        (self.mods / "unexpected.jar").write_bytes(b"unexpected\n")
        with self.assertRaisesRegex(ValueError, "unexpected client mod"):
            validate_client_install(self.instance, self.metadata)

        (self.mods / "unexpected.jar").unlink()
        (self.mods / "server.jar").write_bytes(b"server\n")
        with self.assertRaisesRegex(ValueError, "server-only mod"):
            validate_client_install(self.instance, self.metadata)

    def test_current_repository_inventory_is_release_sized(self):
        client_required, server_only = expected_mod_inventory(
            REPOSITORY_ROOT / "mods"
        )

        self.assertEqual(len(client_required), 152)
        self.assertEqual(len(server_only), 15)


class ClientHarnessContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = CLIENT_SCRIPT.read_text(encoding="utf-8")

    def test_harness_uses_released_pinned_installers_twice(self):
        self.assertIn("AFTERLIGHT-prism-instance.zip", self.source)
        self.assertIn("packwiz-installer-bootstrap.jar", self.source)
        self.assertIn("packwiz-installer.jar", self.source)
        self.assertIn("--bootstrap-no-update", self.source)
        self.assertIn("--bootstrap-main-jar packwiz-installer.jar", self.source)
        self.assertNotIn("releases/latest", self.source)
        self.assertEqual(self.source.count("run_installer"), 3)

    def test_harness_owns_cleanup_java_and_idempotence_checks(self):
        self.assertIn("cleanup()", self.source)
        self.assertIn("trap cleanup EXIT", self.source)
        self.assertIn("need a working Java 21 runtime", self.source)
        self.assertIn("FIRST_MODSET_SHA256", self.source)
        self.assertIn("SECOND_MODSET_SHA256", self.source)
        self.assertIn("CLIENT INSTALL: OK", self.source)

    def test_harness_avoids_ambiguous_and_or_guards(self):
        self.assertNotRegex(
            self.source,
            r"\]\s*&&\s*\[\s*!\s*-L\b.*\]\s*\|\|",
        )


if __name__ == "__main__":
    unittest.main()
