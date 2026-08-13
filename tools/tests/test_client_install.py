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
        self.pack_root = self.root / "pack"
        self.metadata = self.pack_root / "mods"
        self.instance = self.root / "instance"
        self.mods = self.instance / "mods"
        self.metadata.mkdir(parents=True)
        self.mods.mkdir(parents=True)

    def _write_metadata(self, stem, filename, side, jar_bytes=None):
        if jar_bytes is None:
            jar_bytes = f"{stem} fixture\n".encode("utf-8")
        source = textwrap.dedent(
            f"""\
            name = "{stem}"
            filename = "{filename}"
            side = "{side}"

            [download]
            url = "https://example.invalid/{filename}"
            hash-format = "sha256"
            hash = "{hashlib.sha256(jar_bytes).hexdigest()}"
            """
        )
        (self.metadata / f"{stem}.pw.toml").write_text(source, encoding="utf-8")

    def _write_pack_index(self, authored_bytes=b"enabled=true\n"):
        authored_path = self.pack_root / "config" / "fixture.cfg"
        authored_path.parent.mkdir(parents=True, exist_ok=True)
        authored_path.write_bytes(authored_bytes)
        records = []
        for path in [authored_path, *sorted(self.metadata.glob("*.pw.toml"))]:
            relative_path = path.relative_to(self.pack_root).as_posix()
            lines = [
                "[[files]]",
                f'file = "{relative_path}"',
                f'hash = "{hashlib.sha256(path.read_bytes()).hexdigest()}"',
            ]
            if relative_path.endswith(".pw.toml"):
                lines.append("metafile = true")
            records.extend([*lines, ""])
        index_bytes = ('hash-format = "sha256"\n\n' + "\n".join(records)).encode(
            "utf-8"
        )
        (self.pack_root / "index.toml").write_bytes(index_bytes)
        (self.pack_root / "pack.toml").write_text(
            textwrap.dedent(
                f"""\
                name = "AFTERLIGHT"
                version = "fixture"

                [index]
                file = "index.toml"
                hash-format = "sha256"
                hash = "{hashlib.sha256(index_bytes).hexdigest()}"
                """
            ),
            encoding="utf-8",
        )

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

    def test_validate_client_install_binds_every_packwiz_payload_file(self):
        client_bytes = b"client fixture\n"
        self._write_metadata("client", "client.jar", "client", client_bytes)
        self._write_metadata("server", "server.jar", "server")
        self._write_pack_index()
        (self.mods / "client.jar").write_bytes(client_bytes)
        installed_config = self.instance / "config" / "fixture.cfg"
        installed_config.parent.mkdir(parents=True)
        installed_config.write_bytes(b"enabled=true\n")

        summary = validate_client_install(
            self.instance,
            self.metadata,
            self.pack_root,
        )

        payload_lines = []
        for relative_path in ("config/fixture.cfg", "mods/client.jar"):
            path = self.instance / relative_path
            payload_lines.append(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative_path}\n"
            )
        expected_payload = hashlib.sha256(
            "".join(payload_lines).encode("utf-8")
        ).hexdigest()
        self.assertEqual(summary["payload_file_count"], 2)
        self.assertEqual(summary["payload_sha256"], expected_payload)

        installed_config.write_bytes(b"enabled=false\n")
        with self.assertRaisesRegex(ValueError, "installed payload hash mismatch"):
            validate_client_install(self.instance, self.metadata, self.pack_root)

        installed_config.unlink()
        with self.assertRaisesRegex(ValueError, "missing installed payload"):
            validate_client_install(self.instance, self.metadata, self.pack_root)

    def test_validate_client_install_rejects_unexpected_payload_files(self):
        client_bytes = b"client fixture\n"
        self._write_metadata("client", "client.jar", "client", client_bytes)
        self._write_pack_index()
        (self.mods / "client.jar").write_bytes(client_bytes)
        installed_config = self.instance / "config" / "fixture.cfg"
        installed_config.parent.mkdir(parents=True)
        installed_config.write_bytes(b"enabled=true\n")
        unexpected_script = self.instance / "kubejs" / "startup_scripts" / "extra.js"
        unexpected_script.parent.mkdir(parents=True)
        unexpected_script.write_bytes(b"unexpected production payload\n")

        with self.assertRaisesRegex(ValueError, "unexpected installed file"):
            validate_client_install(self.instance, self.metadata, self.pack_root)

    def test_current_repository_inventory_is_release_sized(self):
        client_required, server_only = expected_mod_inventory(
            REPOSITORY_ROOT / "mods"
        )

        smartbrainlib = "SmartBrainLib-neoforge-1.21.1-1.16.11.jar"
        luckperms = "LuckPerms-NeoForge-5.4.140.jar"
        controlling = "Controlling-neoforge-1.21.1-19.0.5.jar"
        searchables = "Searchables-neoforge-1.21.1-1.0.2.jar"
        ftb_ultimine = "ftb-ultimine-neoforge-2101.1.15.jar"
        lootr = "lootr-neoforge-1.21.1-1.11.38.123.jar"
        afterlight_signal = "afterlight-signal-0.2.1+1.21.1.jar"
        veinminer = "veinminer-neoforge-2.11.2+1.21.1.jar"
        veinminer_hotkey = "veinminer-client-neoforge-2.11.2+1.21.1.jar"
        self.assertIn(smartbrainlib, client_required)
        self.assertNotIn(smartbrainlib, server_only)
        self.assertNotIn(luckperms, server_only)
        self.assertIn(controlling, client_required)
        self.assertIn(searchables, client_required)
        self.assertIn(ftb_ultimine, client_required)
        self.assertIn(lootr, client_required)
        self.assertIn(afterlight_signal, client_required)
        self.assertNotIn(veinminer, client_required)
        self.assertNotIn(veinminer_hotkey, client_required)
        self.assertEqual(len(client_required), 156)
        self.assertEqual(len(server_only), 13)


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

    def test_harness_has_explicit_production_pages_mode(self):
        self.assertIn('INSTALL_MODE=${2:-local}', self.source)
        self.assertIn('EXPECTED_MODSET_SHA256=${3:-}', self.source)
        self.assertIn('EXPECTED_PAYLOAD_SHA256=${4:-}', self.source)
        self.assertIn('"$INSTALL_MODE" = production', self.source)
        self.assertIn('INSTALL_PACK_URL="$PACK_URL"', self.source)
        self.assertIn('INSTALL_PACK_URL="$LOCAL_PACK_URL"', self.source)
        self.assertIn('-g "$INSTALL_PACK_URL"', self.source)
        self.assertIn('"$FIRST_MODSET_SHA256" = "$EXPECTED_MODSET_SHA256"', self.source)
        self.assertIn('"$SECOND_MODSET_SHA256" = "$EXPECTED_MODSET_SHA256"', self.source)
        self.assertIn('"$SECOND_PAYLOAD_SHA256" = "$EXPECTED_PAYLOAD_SHA256"', self.source)
        self.assertIn('--pack-root .', self.source)
        self.assertIn("usage:", self.source)

    def test_harness_owns_cleanup_java_and_idempotence_checks(self):
        self.assertIn("cleanup()", self.source)
        self.assertIn("trap cleanup EXIT", self.source)
        self.assertIn("need a working Java 21 runtime", self.source)
        self.assertIn("FIRST_MODSET_SHA256", self.source)
        self.assertIn("SECOND_MODSET_SHA256", self.source)
        self.assertIn("FIRST_PAYLOAD_SHA256", self.source)
        self.assertIn("SECOND_PAYLOAD_SHA256", self.source)
        self.assertIn('[ "$FIRST_CLIENT_COUNT" = 156 ]', self.source)
        self.assertIn("CLIENT INSTALL: OK", self.source)

    def test_harness_avoids_ambiguous_and_or_guards(self):
        self.assertNotRegex(
            self.source,
            r"\]\s*&&\s*\[\s*!\s*-L\b.*\]\s*\|\|",
        )


if __name__ == "__main__":
    unittest.main()
