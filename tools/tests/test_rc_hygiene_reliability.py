from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def hygiene_module():
    return importlib.import_module("rc_hygiene")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def write_provenance_fixture(
    base: Path, side: str = "both"
) -> tuple[Path, Path, Path]:
    root = base / "pack"
    install = base / "install"
    (root / "mods").mkdir(parents=True)
    (install / "mods").mkdir(parents=True)

    jar_bytes = b"authenticated fixture jar"
    jar_hash = sha256_bytes(jar_bytes)
    metadata = (
        'name = "Fixture Mod"\n'
        'filename = "fixture.jar"\n'
        f'side = "{side}"\n\n'
        '[download]\n'
        'hash-format = "sha256"\n'
        f'hash = "{jar_hash}"\n'
    ).encode()
    metadata_path = root / "mods" / "fixture.pw.toml"
    metadata_path.write_bytes(metadata)

    index = (
        'hash-format = "sha256"\n\n'
        '[[files]]\n'
        'file = "mods/fixture.pw.toml"\n'
        f'hash = "{sha256_bytes(metadata)}"\n'
        'metafile = true\n'
    ).encode()
    (root / "index.toml").write_bytes(index)
    pack = (
        'name = "Fixture"\n'
        'pack-format = "packwiz:1.1.0"\n\n'
        '[index]\n'
        'file = "index.toml"\n'
        'hash-format = "sha256"\n'
        f'hash = "{sha256_bytes(index)}"\n'
    ).encode()
    (root / "pack.toml").write_bytes(pack)

    jar_path = install / "mods" / "fixture.jar"
    jar_path.write_bytes(jar_bytes)
    provenance = {
        "packFileHash": {"type": "sha256", "value": sha256_bytes(pack)},
        "indexFileHash": {"type": "sha256", "value": sha256_bytes(index)},
        "cachedFiles": {
            "mods/fixture.pw.toml": {
                "hash": {"type": "sha256", "value": sha256_bytes(metadata)},
                "linkedFileHash": {"type": "sha256", "value": jar_hash},
                "cachedLocation": "mods/fixture.jar",
                "optionValue": True,
            }
        },
        "cachedSide": "server",
    }
    (install / "packwiz.json").write_text(json.dumps(provenance), encoding="utf-8")
    return root, install, jar_path


def valid_boot_log(nonce: str) -> str:
    digest = "a" * 64
    return "\n".join(
        (
            "[08Aug2026 12:00:00.000] [Server thread/INFO] "
            "[net.minecraft.server.dedicated.DedicatedServer/]: "
            'Done (12.345s)! For help, type "help"',
            "[08Aug2026 12:00:01.000] [Server thread/INFO] [KubeJS Server/]: "
            f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} 219 {nonce}",
            "[08Aug2026 12:00:02.000] [Server thread/INFO] "
            "[net.minecraft.server.MinecraftServer/]: Stopping server",
            "[08Aug2026 12:00:02.100] [Server thread/INFO] "
            "[net.minecraft.server.MinecraftServer/]: Saving players",
            "[08Aug2026 12:00:02.200] [Server thread/INFO] "
            "[net.minecraft.server.MinecraftServer/]: Saving worlds",
            "[08Aug2026 12:00:03.000] [Server thread/INFO] "
            "[net.minecraft.server.MinecraftServer/]: "
            "ThreadedAnvilChunkStorage: All dimensions are saved",
        )
    )


class BootOracleNegativeTests(unittest.TestCase):
    def allowance(self):
        hygiene = hygiene_module()
        return hygiene.LogAllowance(
            label="source-bound fixture",
            level="ERROR",
            logger="fixture.Logger/SOURCE",
            message="Known failure in fixture: resource/example.json",
            count=1,
            contexts=("at fixture.StableContext.load(StableContext.java:42)",),
        )

    def allowed_error_log(self) -> str:
        return (
            "[08Aug2026 12:00:00.000] [main/ERROR] [fixture.Logger/SOURCE]: "
            "Known failure in fixture: resource/example.json\n"
            "\tat fixture.StableContext.load(StableContext.java:42)\n"
        )

    def test_unknown_error_record_is_rejected(self) -> None:
        hygiene = hygiene_module()
        log_text = self.allowed_error_log() + (
            "[08Aug2026 12:00:01.000] [main/ERROR] [fixture.Unknown/NEW]: "
            "Release-blocking failure\n"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
            hygiene.validate_error_records(log_text, (self.allowance(),))

    def test_same_count_different_logger_is_rejected(self) -> None:
        hygiene = hygiene_module()
        substituted = self.allowed_error_log().replace(
            "fixture.Logger/SOURCE", "fixture.Unrelated/SUBSTITUTE"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
            hygiene.validate_error_records(substituted, (self.allowance(),))

    def test_same_logger_and_message_with_changed_context_is_rejected(self) -> None:
        hygiene = hygiene_module()
        substituted = self.allowed_error_log().replace(
            "fixture.StableContext.load(StableContext.java:42)",
            "fixture.UnrelatedContext.run(UnrelatedContext.java:7)",
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
            hygiene.validate_error_records(substituted, (self.allowance(),))

    def test_fake_done_logger_is_rejected(self) -> None:
        hygiene = hygiene_module()
        log_text = valid_boot_log("fresh").replace(
            "net.minecraft.server.dedicated.DedicatedServer/",
            "example.NotAServer/",
            1,
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "DedicatedServer Done"):
            hygiene.validate_boot_markers(log_text, "fresh", 0)

    def test_stale_nonce_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with self.assertRaisesRegex(hygiene.VerificationError, "fresh audit nonce"):
            hygiene.validate_boot_markers(valid_boot_log("stale"), "fresh", 0)

    def test_missing_clean_shutdown_is_rejected(self) -> None:
        hygiene = hygiene_module()
        log_text = valid_boot_log("fresh").replace(
            "ThreadedAnvilChunkStorage: All dimensions are saved", "shutdown omitted"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "clean shutdown"):
            hygiene.validate_boot_markers(log_text, "fresh", 0)

    def test_nonzero_server_status_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with self.assertRaisesRegex(hygiene.VerificationError, "server exit status 124"):
            hygiene.validate_boot_markers(valid_boot_log("fresh"), "fresh", 124)

    def test_every_cei_registry_error_variant_is_rejected(self) -> None:
        hygiene = hygiene_module()
        for fluid_id in (
            "enderio:xpjuice",
            "enderio:xp_juice",
            "enderio:fluid_xp_juice_still",
        ):
            with self.subTest(fluid_id=fluid_id):
                log_text = (
                    "[08Aug2026 12:00:00.000] [main/ERROR] "
                    "[net.neoforged.neoforge.registries.DataMapLoader/]: "
                    f"Object with ID {fluid_id} specified in data map for registry "
                    "minecraft:fluid doesn't exist\n"
                )
                with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
                    hygiene.validate_error_records(
                        log_text, hygiene.project_error_allowances()
                    )

    def test_idas_missing_tag_warning_is_rejected(self) -> None:
        hygiene = hygiene_module()
        log_text = (
            "[08Aug2026 12:00:00.000] [main/WARN] "
            "[net.minecraft.core.MappedRegistry/]: Not all defined tags for registry "
            "ResourceKey[minecraft:root / minecraft:worldgen/biome] are present in data "
            "pack: idas:has_structure/bygredwood_biomes\n"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched known residual WARN"):
            hygiene.validate_known_residual_warnings(log_text)

    def test_jdt_allowance_rejects_any_identity_or_count_change(self) -> None:
        hygiene = hygiene_module()
        lines = []
        for allowance in hygiene.project_warning_allowances():
            for _ in range(allowance.count):
                lines.append(
                    "[08Aug2026 12:00:00.000] [main/"
                    f"{allowance.level}] [{allowance.logger}]: {allowance.message}"
                )
        valid_log = "\n".join(lines) + "\n"
        hygiene.validate_known_residual_warnings(valid_log)
        mutations = (
            ("Supplementaries/", "SubstitutedLogger/"),
            ("justdirethings:fuel_canister", "justdirethings:changed_item"),
            ("Cannot get config value before config is loaded.", "Changed exception"),
        )
        for original, replacement in mutations:
            with self.subTest(replacement=replacement):
                with self.assertRaises(hygiene.VerificationError):
                    hygiene.validate_known_residual_warnings(
                        valid_log.replace(original, replacement, 1)
                    )
        jdt_line = next(line for line in lines if "fuel_canister" in line)
        with self.assertRaisesRegex(hygiene.VerificationError, "count mismatch"):
            hygiene.validate_known_residual_warnings(
                valid_log.replace(jdt_line + "\n", "", 1)
            )
        with self.assertRaisesRegex(hygiene.VerificationError, "count mismatch"):
            hygiene.validate_known_residual_warnings(valid_log + jdt_line + "\n")


class ManifestAndProvenanceNegativeTests(unittest.TestCase):
    def test_manifest_index_drift_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = write_provenance_fixture(Path(temporary))
            (root / "index.toml").write_text("hash-format = \"sha256\"\n", encoding="utf-8")
            with self.assertRaisesRegex(hygiene.VerificationError, "index hash"):
                hygiene.verify_manifest(root)

    def test_modified_source_jar_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, jar_path = write_provenance_fixture(Path(temporary))
            jar_path.write_bytes(jar_path.read_bytes() + b"tampered")
            with self.assertRaisesRegex(hygiene.VerificationError, "fixture.jar hash"):
                hygiene.resolve_source_jar(root, install, "mods/fixture.pw.toml")

    def test_stale_installer_provenance_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, _ = write_provenance_fixture(Path(temporary))
            with (root / "pack.toml").open("ab") as pack_file:
                pack_file.write(b"\n")
            with self.assertRaisesRegex(hygiene.VerificationError, "installed pack provenance"):
                hygiene.verify_install_provenance(root, install)

    def test_metadata_fragment_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, _ = write_provenance_fixture(Path(temporary))
            with self.assertRaisesRegex(hygiene.VerificationError, "exact .pw.toml path"):
                hygiene.resolve_source_jar(root, install, "fixture")

    def test_client_side_source_is_rejected_for_server_fixture(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, _ = write_provenance_fixture(
                Path(temporary), side="client"
            )
            with self.assertRaisesRegex(hygiene.VerificationError, "not installed on the server side"):
                hygiene.resolve_source_jar(root, install, "mods/fixture.pw.toml")


class FilterAndHarnessNegativeTests(unittest.TestCase):
    def test_filter_patterns_reject_namespace_and_path_near_matches(self) -> None:
        hygiene = hygiene_module()
        namespace_pattern = "^create_enchantment_industry$"
        path_pattern = "^data_maps/fluid/unit/experience\\.json$"
        self.assertTrue(
            hygiene.filter_matches(
                namespace_pattern,
                path_pattern,
                "create_enchantment_industry",
                "data_maps/fluid/unit/experience.json",
            )
        )
        for namespace, path in (
            (
                "prefix_create_enchantment_industry_suffix",
                "data_maps/fluid/unit/experience.json",
            ),
            (
                "create_enchantment_industry",
                "prefix/data_maps/fluid/unit/experience.json",
            ),
            (
                "create_enchantment_industry",
                "data_maps/fluid/unit/experience.json.backup",
            ),
        ):
            with self.subTest(namespace=namespace, path=path):
                self.assertFalse(
                    hygiene.filter_matches(
                        namespace_pattern, path_pattern, namespace, path
                    )
                )

    def test_filter_archive_matches_deterministic_generator_bytes(self) -> None:
        hygiene = hygiene_module()
        archive_path = ROOT / "kubejs" / "data" / "afterlight_rc_hygiene.zip"
        self.assertEqual(archive_path.read_bytes(), hygiene.build_filter_archive())

    def test_server_harness_pins_bootstrap_and_preserves_process_truth(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn(
            "releases/download/v0.0.3/packwiz-installer-bootstrap.jar", script
        )
        self.assertIn(
            "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c",
            script,
        )
        self.assertIn("packwiz serve --refresh=false", script)
        self.assertIn("python3 tools/rc_hygiene.py verify-manifest", script)
        self.assertIn("afterlight-server-exit-status.txt", script)
        self.assertRegex(script, re.compile(r"SERVER_STATUS=\$\?"))
        self.assertIn("ACTUAL_BOOTSTRAP_SHA256", script)
        self.assertIn("assert_manifest_unchanged", script)
        self.assertGreaterEqual(script.count("assert_manifest_unchanged"), 5)
        self.assertNotIn("packwiz refresh", script)
        self.assertNotIn("|| true", script)
        run_lines = [line for line in script.splitlines() if "./run.sh nogui" in line]
        self.assertEqual(len(run_lines), 1)
        self.assertNotIn("|| true", run_lines[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
