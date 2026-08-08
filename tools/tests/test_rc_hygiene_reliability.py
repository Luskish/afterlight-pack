from __future__ import annotations

import hashlib
import importlib
import json
import re
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
DEBUG_LOG = ROOT / "server-test" / "logs" / "debug.log"
LATEST_LOG = ROOT / "server-test" / "logs" / "latest.log"
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


def relocate_record(
    log_text: str, logger: str, message: str, change_thread: bool = True
) -> str:
    lines = log_text.splitlines()
    record_index = next(
        index
        for index, line in enumerate(lines)
        if f"[{logger}]: {message}" in line
    )
    moved = lines.pop(record_index)
    if change_thread:
        moved = re.sub(
            r"\[[^\]]+/ERROR\]", "[Unrelated-Worker/ERROR]", moved, count=1
        )
    done_index = next(
        index
        for index, line in enumerate(lines)
        if "[net.minecraft.server.dedicated.DedicatedServer/]: Done (" in line
    )
    lines.insert(done_index + 1, moved)
    return "\n".join(lines) + "\n"


def add_unrelated_record_context(log_text: str, logger: str, message: str) -> str:
    lines = log_text.splitlines()
    record_index = next(
        index
        for index, line in enumerate(lines)
        if f"[{logger}]: {message}" in line
    )
    lines.insert(record_index + 1, "\tat unrelated.Substitute.run(Substitute.java:7)")
    return "\n".join(lines) + "\n"


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

    def assert_sable_debug_rejected(self, debug_text: str, pattern: str) -> None:
        hygiene = hygiene_module()
        records = hygiene.parse_log_records(debug_text)
        with self.assertRaisesRegex(hygiene.VerificationError, pattern):
            hygiene._validate_sable_debug_records(
                records, hygiene.project_sable_error_requirement()
            )

    def test_project_generic_allowances_cannot_consume_sable_records(self) -> None:
        hygiene = hygiene_module()
        requirement = hygiene.project_sable_error_requirement()
        self.assertFalse(
            any(
                allowance.logger == requirement.logger
                and allowance.message == requirement.message
                for allowance in hygiene.project_error_allowances()
            )
        )
        log_text = (
            "[08Aug2026 12:00:00.000] [main/ERROR] "
            f"[{requirement.logger}]: {requirement.message}\n"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
            hygiene.validate_error_records(log_text, hygiene.project_error_allowances())

    def test_project_generic_allowances_cannot_consume_idas_air_errors(self) -> None:
        hygiene = hygiene_module()
        log_text = (
            "[08Aug2026 12:00:00.000] [Worker-Main-1/ERROR] "
            "[net.minecraft.world.item.ItemStack/]: "
            f"{hygiene.ITEMSTACK_AIR_MESSAGE}\n"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "unmatched ERROR"):
            hygiene.validate_error_records(log_text, hygiene.project_error_allowances())

    def test_sable_dedicated_verifier_accepts_current_named_context(self) -> None:
        hygiene = hygiene_module()
        records = hygiene.parse_log_records(
            DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        )
        indices = hygiene._validate_sable_debug_records(
            records, hygiene.project_sable_error_requirement()
        )
        self.assertEqual(len(indices), 12)

    def test_sable_verifier_rejects_same_count_relocation(self) -> None:
        hygiene = hygiene_module()
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        relocated = relocate_record(
            debug_text,
            "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
            hygiene.RUNTIME_DIST_CLEANER_MESSAGE,
            change_thread=False,
        )
        self.assert_sable_debug_rejected(relocated, "RuntimeDistCleaner")

    def test_sable_verifier_rejects_added_substitute_context(self) -> None:
        hygiene = hygiene_module()
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = add_unrelated_record_context(
            debug_text,
            "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
            hygiene.RUNTIME_DIST_CLEANER_MESSAGE,
        )
        self.assert_sable_debug_rejected(substituted, "continuation context")

    def test_sable_verifier_rejects_named_prepare_source_substitution(self) -> None:
        hygiene = hygiene_module()
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "sable.mixins.json:entity.entity_aabb_lookup.LevelsMixin from mod sable",
            "substitute.mixins.json:other.LevelsMixin from mod substitute",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "prepare source context")

    def test_sable_verifier_rejects_application_source_substitution(self) -> None:
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "Mixing plot.LevelsMixin from sable.mixins.json into "
            "net.minecraft.server.level.ServerLevel",
            "Mixing substitute.LevelsMixin from substitute.mixins.json into "
            "net.minecraft.server.level.ServerLevel",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "application source context")

    def test_sable_verifier_rejects_changed_normalized_stack_source(self) -> None:
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "RuntimeDistCleaner.processClassWithFlags(RuntimeDistCleaner.java:60)",
            "RuntimeDistCleaner.processClassWithFlags(RuntimeDistCleaner.java:61)",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "normalized stack hash changed")

    def test_sable_verifier_rejects_named_window_relocation(self) -> None:
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        anchor = (
            "[main/TRACE] [mixin/]: Added class metadata for "
            "dev/ryanhcode/sable/api/command/SubLevelArgumentType$Info to metadata cache"
        )
        lines = debug_text.splitlines()
        anchor_index = next(index for index, line in enumerate(lines) if anchor in line)
        moved = lines.pop(anchor_index)
        p2_anchor = next(
            index
            for index, line in enumerate(lines)
            if "SubLevelEntityCollision$FirstCollisionInfo to metadata cache" in line
        )
        lines.insert(p2_anchor, moved)
        self.assert_sable_debug_rejected("\n".join(lines) + "\n", "P1 source window")

    def test_sable_verifier_rejects_missing_first_p3_named_anchor(self) -> None:
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "ServerConnectionListenerMixin$1 to metadata cache",
            "ServerConnectionListenerMixin$changed to metadata cache",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "P3 first start")

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

    def test_sable_verifier_rejects_authenticated_artifact_hash_change(self) -> None:
        hygiene = hygiene_module()
        original_hash_file = hygiene._hash_file

        def changed_hash(path: Path, hash_format: str) -> str:
            if path.name == "sable-neoforge-1.21.1-2.0.3.jar" and hash_format == "sha256":
                return "0" * 64
            return original_hash_file(path, hash_format)

        with mock.patch.object(hygiene, "_hash_file", side_effect=changed_hash):
            with self.assertRaisesRegex(hygiene.VerificationError, "Sable artifact hash"):
                hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")

    def test_sable_verifier_rejects_fourth_pseudo_clientlevel_candidate(self) -> None:
        hygiene = hygiene_module()
        original_scan = hygiene._scan_mixin_archive
        injected = False

        def changed_scan(label, payload, result, nested_queue=None):
            nonlocal injected
            original_scan(label, payload, result, nested_queue)
            if label == hygiene.SABLE_METADATA and not injected:
                result["pseudo_clientlevel_candidates"].append(
                    (
                        "mods/substitute.pw.toml",
                        "substitute.mixins.json",
                        "substitute.LevelsMixin",
                        "substitute/LevelsMixin.class",
                        "0" * 64,
                        (
                            "Lnet/minecraft/server/level/ServerLevel;",
                            "Lnet/minecraft/client/multiplayer/ClientLevel;",
                        ),
                    )
                )
                injected = True

        with mock.patch.object(
            hygiene, "_scan_mixin_archive", side_effect=changed_scan
        ):
            with self.assertRaisesRegex(
                hygiene.VerificationError, "@Pseudo ClientLevel candidate set"
            ):
                hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")


class CurrentBootProjectionNegativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hygiene = hygiene_module()
        self.latest = LATEST_LOG.read_text(encoding="utf-8", errors="replace")
        self.debug = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        self.nonce = (ROOT / "server-test" / "afterlight-audit-nonce.txt").read_text(
            encoding="utf-8"
        ).strip()
        self.status = int(
            (ROOT / "server-test" / "afterlight-server-exit-status.txt")
            .read_text(encoding="utf-8")
            .strip()
        )

    def verify(self, latest: str, debug: str) -> None:
        self.hygiene.verify_sable_runtime_dist_cleaner_evidence(
            ROOT,
            ROOT / "server-test",
            latest,
            debug,
            self.nonce,
            self.status,
        )

    def test_sable_verifier_rejects_stale_debug_log_nonce(self) -> None:
        stale = self.debug.replace(self.nonce, "stale-nonce", 1)
        with self.assertRaisesRegex(
            self.hygiene.VerificationError, "fresh audit nonce"
        ):
            self.verify(self.latest, stale)

    def test_sable_verifier_rejects_same_count_source_substitution(self) -> None:
        substituted = self.debug.replace(
            "Mixing water_occlusion.LevelsMixin from sable.mixins.json into "
            "net.minecraft.server.level.ServerLevel",
            "Mixing substitute.LevelsMixin from substitute.mixins.json into "
            "net.minecraft.server.level.ServerLevel",
            1,
        )
        with self.assertRaisesRegex(
            self.hygiene.VerificationError, "application source context"
        ):
            self.verify(self.latest, substituted)

    def test_idas_compat_verifier_rejects_same_count_audit_substitution(self) -> None:
        changed = self.hygiene.IDAS_COMPAT_CAMP_MESSAGE.replace(
            "772fe478261727163979ddd04ae3d69220c35b02c09c7046974f96d99d5b0b06",
            "0" * 64,
        )
        latest = self.latest.replace(self.hygiene.IDAS_COMPAT_CAMP_MESSAGE, changed, 1)
        debug = self.debug.replace(self.hygiene.IDAS_COMPAT_CAMP_MESSAGE, changed, 1)
        with self.assertRaisesRegex(
            self.hygiene.VerificationError, "SANITIZED audit sequence changed"
        ):
            self.hygiene.verify_idas_compat_runtime_evidence(
                ROOT, ROOT / "server-test", latest, debug
            )

    def test_idas_compat_verifier_rejects_any_generic_air_error(self) -> None:
        injected = (
            "[08Aug2026 12:00:00.000] [Worker-Main-1/ERROR] "
            "[net.minecraft.world.item.ItemStack/]: "
            f"{self.hygiene.ITEMSTACK_AIR_MESSAGE}\n"
        )
        with self.assertRaisesRegex(
            self.hygiene.VerificationError, "generic ItemStack air ERROR"
        ):
            self.hygiene.verify_idas_compat_runtime_evidence(
                ROOT,
                ROOT / "server-test",
                self.latest + injected,
                self.debug + injected,
            )


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
