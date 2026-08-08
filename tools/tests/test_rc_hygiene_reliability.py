from __future__ import annotations

import hashlib
import importlib
import io
import json
import re
import struct
import sys
import tempfile
import unittest
import zipfile
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


def rewrite_zip_fixture(
    source: Path,
    target: Path,
    replacements: dict[str, bytes] | None = None,
    additions: dict[str, bytes] | None = None,
) -> None:
    replacements = replacements or {}
    additions = additions or {}
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, "w") as changed:
        for entry in original.infolist():
            if entry.is_dir():
                continue
            payload = replacements.get(entry.filename, original.read(entry.filename))
            changed.writestr(entry.filename, payload)
        for name, payload in additions.items():
            changed.writestr(name, payload)


def idas_compat_metadata(hygiene) -> dict:
    return {
        "filename": hygiene.IDAS_COMPAT_FILENAME,
        "side": "both",
        "download": {
            "url": hygiene.IDAS_COMPAT_URL,
            "hash-format": "sha512",
            "hash": hygiene.IDAS_COMPAT_SHA512,
        },
    }


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
    hygiene = hygiene_module()
    digest = "8428e54a802bb23013ff5d79c80592bec7b295351330ef4570458ac32f33fecd"
    return "\n".join(
        (
            "[08Aug2026 11:59:58.000] [modloading-worker-0/INFO] "
            f"[{hygiene.IDAS_COMPAT_LOGGER}]: {hygiene.IDAS_COMPAT_READY_MESSAGE}",
            *(
                "[08Aug2026 11:59:59.000] [Worker-Main-1/INFO] "
                f"[{hygiene.IDAS_COMPAT_LOGGER}]: {message}"
                for message in hygiene.IDAS_COMPAT_BOOT_SANITIZED_MESSAGES
            ),
            "[08Aug2026 12:00:00.000] [Server thread/INFO] "
            "[net.minecraft.server.dedicated.DedicatedServer/]: "
            'Done (12.345s)! For help, type "help"',
            "[08Aug2026 12:00:01.000] [Server thread/INFO] [KubeJS Server/]: "
            f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} 219 {nonce}",
            "[08Aug2026 12:00:01.500] [Server thread/INFO] [FTB Quests/]: "
            "Loaded 6 chapter groups, 41 chapters, 283 quests, 6 reward tables",
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


def insert_after_line(log_text: str, marker: str, added: str) -> str:
    lines = log_text.splitlines()
    index = next(index for index, line in enumerate(lines) if marker in line)
    lines.insert(index + 1, added)
    return "\n".join(lines) + "\n"


def move_line_after(log_text: str, moved_marker: str, destination_marker: str) -> str:
    lines = log_text.splitlines()
    moved_index = next(index for index, line in enumerate(lines) if moved_marker in line)
    moved = lines.pop(moved_index)
    destination_index = next(
        index for index, line in enumerate(lines) if destination_marker in line
    )
    lines.insert(destination_index + 1, moved)
    return "\n".join(lines) + "\n"


def duplicate_line(log_text: str, marker: str) -> str:
    lines = log_text.splitlines()
    index = next(index for index, line in enumerate(lines) if marker in line)
    lines.insert(index + 1, lines[index])
    return "\n".join(lines) + "\n"


def remove_line(log_text: str, marker: str) -> str:
    lines = log_text.splitlines()
    index = next(index for index, line in enumerate(lines) if marker in line)
    lines.pop(index)
    return "\n".join(lines) + "\n"


def swap_lines(log_text: str, first_marker: str, second_marker: str) -> str:
    lines = log_text.splitlines()
    first = next(index for index, line in enumerate(lines) if first_marker in line)
    second = next(index for index, line in enumerate(lines) if second_marker in line)
    lines[first], lines[second] = lines[second], lines[first]
    return "\n".join(lines) + "\n"


def _u2(value: int) -> bytes:
    return struct.pack(">H", value)


def _u4(value: int) -> bytes:
    return struct.pack(">I", value)


def mixin_class_bytes(
    *,
    value_targets: tuple[str, ...] = (),
    string_targets: tuple[str, ...] = (),
    pseudo: bool = True,
    scalar_string_target: bool = False,
) -> bytes:
    pool: list[bytes] = []

    def utf8(value: str) -> int:
        payload = value.encode("utf-8")
        pool.append(b"\x01" + _u2(len(payload)) + payload)
        return len(pool)

    def class_info(name_index: int) -> int:
        pool.append(b"\x07" + _u2(name_index))
        return len(pool)

    this_name = utf8("fixture/LevelsMixin")
    this_class = class_info(this_name)
    super_name = utf8("java/lang/Object")
    super_class = class_info(super_name)
    attribute_name = utf8("RuntimeInvisibleAnnotations")
    mixin_descriptor = utf8("Lorg/spongepowered/asm/mixin/Mixin;")
    pseudo_descriptor = utf8("Lorg/spongepowered/asm/mixin/Pseudo;")

    pairs: list[bytes] = []
    if value_targets:
        name_index = utf8("value")
        values = b"".join(b"c" + _u2(utf8(target)) for target in value_targets)
        pairs.append(_u2(name_index) + b"[" + _u2(len(value_targets)) + values)
    if string_targets:
        name_index = utf8("targets")
        target_indices = tuple(utf8(target) for target in string_targets)
        if scalar_string_target:
            element = b"s" + _u2(target_indices[0])
        else:
            values = b"".join(b"s" + _u2(index) for index in target_indices)
            element = b"[" + _u2(len(target_indices)) + values
        pairs.append(_u2(name_index) + element)

    mixin_annotation = (
        _u2(mixin_descriptor) + _u2(len(pairs)) + b"".join(pairs)
    )
    annotations = [mixin_annotation]
    if pseudo:
        annotations.append(_u2(pseudo_descriptor) + _u2(0))
    attribute = _u2(len(annotations)) + b"".join(annotations)
    return b"".join(
        (
            b"\xca\xfe\xba\xbe",
            _u2(0),
            _u2(65),
            _u2(len(pool) + 1),
            b"".join(pool),
            _u2(0x0021),
            _u2(this_class),
            _u2(super_class),
            _u2(0),
            _u2(0),
            _u2(0),
            _u2(1),
            _u2(attribute_name),
            _u4(len(attribute)),
            attribute,
        )
    )


def mixin_archive_bytes(
    class_payload: bytes,
    *,
    config_resource: str = "fixture.mixins.json",
    mixin_name: str = "LevelsMixin",
) -> bytes:
    output = io.BytesIO()
    config = json.dumps(
        {"required": True, "package": "fixture", "mixins": [mixin_name]},
        sort_keys=True,
    ).encode("utf-8")
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(
            "META-INF/neoforge.mods.toml",
            f'[[mixins]]\nconfig = "{config_resource}"\n',
        )
        archive.writestr(config_resource, config)
        archive.writestr(
            f"fixture/{mixin_name.replace('.', '/')}.class", class_payload
        )
    return output.getvalue()


def empty_mixin_scan() -> dict[str, object]:
    return {
        "archive_scopes": 0,
        "mixin_configs": 0,
        "common_mixins": 0,
        "annotation_clientlevel_mixins": 0,
        "direct_clientlevel_mixins": 0,
        "pseudo_clientlevel_candidates": [],
        "mixin_config_hashes": {},
    }


class StrictLogParserNegativeTests(unittest.TestCase):
    def test_valid_ansi_wrapped_header_is_parsed(self) -> None:
        hygiene = hygiene_module()
        records = hygiene.parse_log_records(
            "\x1b[31m[08Aug2026 12:00:00.000] [main/ERROR] "
            "[fixture.Logger/SOURCE]: exact failure\x1b[0m\n"
        )
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].thread, "main")
        self.assertEqual(records[0].level, "ERROR")
        self.assertEqual(records[0].logger, "fixture.Logger/SOURCE")
        self.assertEqual(records[0].message, "exact failure")

    def test_malformed_severe_headers_are_rejected(self) -> None:
        hygiene = hygiene_module()
        variants = (
            "[08Aug2026 12:00:00.000] [main/ERROR [fixture.Logger/]: hidden",
            "[08Aug2026 12:00:00.000] [main/FATAL] fixture.Logger/]: hidden",
            "[08Aug2026 12:00:00] [main/ERROR] [fixture.Logger/]: hidden",
            "\x1b[31m[08Aug2026 12:00:00.000] [main/ERROR "
            "[fixture.Logger/]: hidden\x1b[0m",
        )
        for line in variants:
            with self.subTest(line=line):
                with self.assertRaisesRegex(
                    hygiene.VerificationError, "malformed ERROR/FATAL"
                ):
                    hygiene.parse_log_records(line + "\n")

    def test_unattached_continuation_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with self.assertRaisesRegex(hygiene.VerificationError, "unattached log line"):
            hygiene.parse_log_records("java.lang.IllegalStateException: orphan\n")


class MixinCorpusNegativeTests(unittest.TestCase):
    client_descriptor = "Lnet/minecraft/client/multiplayer/ClientLevel;"
    server_descriptor = "Lnet/minecraft/server/level/ServerLevel;"

    def test_mixin_annotation_parses_value_and_targets(self) -> None:
        hygiene = hygiene_module()
        value = mixin_class_bytes(
            value_targets=(self.server_descriptor, self.client_descriptor)
        )
        targets = mixin_class_bytes(
            string_targets=(
                "net.minecraft.server.level.ServerLevel",
                "net/minecraft/client/multiplayer/ClientLevel",
            )
        )
        self.assertEqual(
            hygiene._mixin_targets(value),
            (
                True,
                True,
                "value",
                (self.server_descriptor, self.client_descriptor),
            ),
        )
        self.assertEqual(
            hygiene._mixin_targets(targets),
            (
                True,
                True,
                "targets",
                (self.server_descriptor, self.client_descriptor),
            ),
        )

    def test_mixin_annotation_rejects_conflicting_or_malformed_targets(self) -> None:
        hygiene = hygiene_module()
        payloads = (
            mixin_class_bytes(
                value_targets=(self.client_descriptor,),
                string_targets=("net.minecraft.client.multiplayer.ClientLevel",),
            ),
            mixin_class_bytes(
                string_targets=("net.minecraft..multiplayer.ClientLevel",)
            ),
            mixin_class_bytes(
                string_targets=("net.minecraft.client.multiplayer.ClientLevel",),
                scalar_string_target=True,
            ),
        )
        for payload in payloads:
            with self.subTest(payload=hashlib.sha256(payload).hexdigest()):
                with self.assertRaises(hygiene.VerificationError):
                    hygiene._mixin_targets(payload)

    def test_duplicate_config_path_is_scoped_by_authenticated_artifact(self) -> None:
        hygiene = hygiene_module()
        scan = empty_mixin_scan()
        first = mixin_archive_bytes(
            mixin_class_bytes(value_targets=(self.server_descriptor,))
        )
        second = mixin_archive_bytes(
            mixin_class_bytes(
                string_targets=("net.minecraft.client.multiplayer.ClientLevel",)
            )
        )
        hygiene._scan_mixin_archive("mods/first.pw.toml", first, scan)
        hygiene._scan_mixin_archive("mods/second.pw.toml", second, scan)
        self.assertEqual(scan["archive_scopes"], 2)
        self.assertEqual(scan["mixin_configs"], 2)
        self.assertEqual(scan["common_mixins"], 2)
        self.assertEqual(scan["annotation_clientlevel_mixins"], 1)
        candidates = tuple(scan["pseudo_clientlevel_candidates"])
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0][0], "mods/second.pw.toml")
        self.assertEqual(candidates[0][-2], "targets")

    def test_conflicting_bytes_for_same_config_identity_are_rejected(self) -> None:
        hygiene = hygiene_module()
        scan = empty_mixin_scan()
        first = mixin_archive_bytes(
            mixin_class_bytes(value_targets=(self.server_descriptor,)),
            mixin_name="LevelsMixin",
        )
        second = mixin_archive_bytes(
            mixin_class_bytes(value_targets=(self.client_descriptor,)),
            mixin_name="ChangedLevelsMixin",
        )
        hygiene._scan_mixin_archive("mods/same.pw.toml", first, scan)
        with self.assertRaisesRegex(hygiene.VerificationError, "conflicting mixin config"):
            hygiene._scan_mixin_archive("mods/same.pw.toml", second, scan)

    def test_target_member_change_is_visible_when_counts_stay_constant(self) -> None:
        hygiene = hygiene_module()
        scans = []
        for label, payload in (
            (
                "value",
                mixin_class_bytes(value_targets=(self.client_descriptor,)),
            ),
            (
                "targets",
                mixin_class_bytes(
                    string_targets=("net.minecraft.client.multiplayer.ClientLevel",)
                ),
            ),
        ):
            scan = empty_mixin_scan()
            hygiene._scan_mixin_archive(
                f"mods/{label}.pw.toml", mixin_archive_bytes(payload), scan
            )
            scans.append(scan)
        self.assertEqual(scans[0]["mixin_configs"], scans[1]["mixin_configs"])
        self.assertEqual(scans[0]["common_mixins"], scans[1]["common_mixins"])
        self.assertNotEqual(
            tuple(scans[0]["pseudo_clientlevel_candidates"])[0][-2],
            tuple(scans[1]["pseudo_clientlevel_candidates"])[0][-2],
        )

    def test_real_corpus_processes_every_mixin_scope(self) -> None:
        hygiene = hygiene_module()
        evidence = hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")
        self.assertEqual(evidence["archive_scopes"], 305)
        self.assertEqual(evidence["mixin_configs"], 261)
        self.assertEqual(evidence["common_mixins"], 2286)
        self.assertEqual(evidence["annotation_clientlevel_mixins"], 3)
        self.assertEqual(len(evidence["pseudo_clientlevel_candidates"]), 3)
        terrablender = tuple(
            identity
            for identity in evidence["mixin_config_identities"]
            if identity[1] == "terrablender.mixins.json"
        )
        self.assertEqual(
            terrablender,
            (
                (
                    "mods/deep-aether.pw.toml!/META-INF/jarjar/"
                    "TerraBlender-neoforge-1.21.1-4.1.0.3.jar",
                    "terrablender.mixins.json",
                    "edfe250df79f5d242e7fbca0e9e09b4d72905c5e3124de5c319e25e34ceac2d8",
                ),
                (
                    "mods/terrablender.pw.toml",
                    "terrablender.mixins.json",
                    "f89948499252717c39dc1a04a188c96a79f38c038ab12bd5f6678ccf6fec205c",
                ),
            ),
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
            thread="main",
            continuations=(
                "\tat fixture.StableContext.load(StableContext.java:42)",
            ),
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
        with self.assertRaisesRegex(
            hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
        ):
            hygiene.validate_error_records(log_text, (self.allowance(),))

    def test_same_count_different_logger_is_rejected(self) -> None:
        hygiene = hygiene_module()
        substituted = self.allowed_error_log().replace(
            "fixture.Logger/SOURCE", "fixture.Unrelated/SUBSTITUTE"
        )
        with self.assertRaisesRegex(
            hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
        ):
            hygiene.validate_error_records(substituted, (self.allowance(),))

    def test_same_logger_and_message_with_changed_context_is_rejected(self) -> None:
        hygiene = hygiene_module()
        substituted = self.allowed_error_log().replace(
            "fixture.StableContext.load(StableContext.java:42)",
            "fixture.UnrelatedContext.run(UnrelatedContext.java:7)",
        )
        with self.assertRaisesRegex(
            hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
        ):
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
        with self.assertRaisesRegex(
            hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
        ):
            hygiene.validate_error_records(log_text, hygiene.project_error_allowances())

    def test_project_generic_allowances_cannot_consume_idas_air_errors(self) -> None:
        hygiene = hygiene_module()
        log_text = (
            "[08Aug2026 12:00:00.000] [Worker-Main-1/ERROR] "
            "[net.minecraft.world.item.ItemStack/]: "
            f"{hygiene.ITEMSTACK_AIR_MESSAGE}\n"
        )
        with self.assertRaisesRegex(
            hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
        ):
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
        self.assert_sable_debug_rejected(substituted, "provenance count mismatch")

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
        self.assert_sable_debug_rejected(
            substituted, r"application source .* context changed"
        )

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
        with self.assertRaisesRegex(hygiene.VerificationError, "quest audit"):
            hygiene.validate_boot_markers(valid_boot_log("stale"), "fresh", 0)

    def test_missing_clean_shutdown_is_rejected(self) -> None:
        hygiene = hygiene_module()
        log_text = valid_boot_log("fresh").replace(
            "ThreadedAnvilChunkStorage: All dimensions are saved", "shutdown omitted"
        )
        with self.assertRaisesRegex(hygiene.VerificationError, "all dimensions saved"):
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
                with self.assertRaisesRegex(
                    hygiene.VerificationError, "unmatched canonical ERROR/FATAL"
                ):
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
                thread = (
                    "Worker-Main-1"
                    if allowance.thread == "Worker-Main-N"
                    else allowance.thread
                )
                lines.append(
                    f"[08Aug2026 12:00:00.000] [{thread}/"
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

    def test_idas_compat_verifier_rejects_changed_source_commit(self) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / hygiene.IDAS_COMPAT_FILENAME
            with zipfile.ZipFile(source) as archive:
                provenance = json.loads(
                    archive.read("META-INF/afterlight-provenance.json")
                )
            provenance["sourceCommit"] = "0" * 40
            payload = json.dumps(provenance, sort_keys=True).encode("utf-8")
            rewrite_zip_fixture(
                source,
                target,
                {"META-INF/afterlight-provenance.json": payload},
            )
            resource_hashes = dict(hygiene.IDAS_COMPAT_RESOURCE_SHA256)
            resource_hashes["META-INF/afterlight-provenance.json"] = sha256_bytes(
                payload
            )
            with (
                mock.patch.object(
                    hygiene, "_read_toml", return_value=idas_compat_metadata(hygiene)
                ),
                mock.patch.object(hygiene, "resolve_source_jar", return_value=target),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_SHA256", sha256_bytes(target.read_bytes())
                ),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_RESOURCE_SHA256", resource_hashes
                ),
                self.assertRaisesRegex(
                    hygiene.VerificationError, "embedded source provenance"
                ),
            ):
                hygiene.verify_idas_compat_source_evidence(ROOT, ROOT / "server-test")

    def test_idas_compat_verifier_rejects_reviewed_allowlist_changes(self) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        mutations = (
            ("sourceSha256", "0" * 64),
            ("candidateCount", 3),
            ("auditDigest", "0" * 64),
        )
        with tempfile.TemporaryDirectory() as temporary:
            temporary_path = Path(temporary)
            for field, value in mutations:
                with self.subTest(field=field):
                    with zipfile.ZipFile(source) as archive:
                        provenance = json.loads(
                            archive.read("META-INF/afterlight-provenance.json")
                        )
                    provenance["reviewedTemplates"][
                        "idas:underground_camp/underground_camp1"
                    ][field] = value
                    payload = json.dumps(provenance, sort_keys=True).encode("utf-8")
                    target = temporary_path / f"changed-{field}.jar"
                    rewrite_zip_fixture(
                        source,
                        target,
                        {"META-INF/afterlight-provenance.json": payload},
                    )
                    resource_hashes = dict(hygiene.IDAS_COMPAT_RESOURCE_SHA256)
                    resource_hashes[
                        "META-INF/afterlight-provenance.json"
                    ] = sha256_bytes(payload)
                    with (
                        mock.patch.object(
                            hygiene,
                            "_read_toml",
                            return_value=idas_compat_metadata(hygiene),
                        ),
                        mock.patch.object(
                            hygiene, "resolve_source_jar", return_value=target
                        ),
                        mock.patch.object(
                            hygiene,
                            "IDAS_COMPAT_SHA256",
                            sha256_bytes(target.read_bytes()),
                        ),
                        mock.patch.object(
                            hygiene,
                            "IDAS_COMPAT_RESOURCE_SHA256",
                            resource_hashes,
                        ),
                        self.assertRaisesRegex(
                            hygiene.VerificationError,
                            "embedded source provenance",
                        ),
                    ):
                        hygiene.verify_idas_compat_source_evidence(
                            ROOT, ROOT / "server-test"
                        )

    def test_idas_compat_verifier_rejects_negative_test_hash_change(self) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / hygiene.IDAS_COMPAT_FILENAME
            with zipfile.ZipFile(source) as archive:
                provenance = json.loads(
                    archive.read("META-INF/afterlight-provenance.json")
                )
            provenance["negativeTestSources"][
                "ReviewedTemplateProvenanceTest.java"
            ] = "0" * 64
            payload = json.dumps(provenance, sort_keys=True).encode("utf-8")
            rewrite_zip_fixture(
                source,
                target,
                {"META-INF/afterlight-provenance.json": payload},
            )
            resource_hashes = dict(hygiene.IDAS_COMPAT_RESOURCE_SHA256)
            resource_hashes["META-INF/afterlight-provenance.json"] = sha256_bytes(
                payload
            )
            with (
                mock.patch.object(
                    hygiene, "_read_toml", return_value=idas_compat_metadata(hygiene)
                ),
                mock.patch.object(hygiene, "resolve_source_jar", return_value=target),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_SHA256", sha256_bytes(target.read_bytes())
                ),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_RESOURCE_SHA256", resource_hashes
                ),
                self.assertRaisesRegex(
                    hygiene.VerificationError, "embedded source provenance"
                ),
            ):
                hygiene.verify_idas_compat_source_evidence(ROOT, ROOT / "server-test")

    def test_idas_compat_verifier_rejects_extra_archive_payload(self) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / hygiene.IDAS_COMPAT_FILENAME
            rewrite_zip_fixture(
                source,
                target,
                additions={"data/idas/structures/forbidden.nbt": b"forbidden"},
            )
            with (
                mock.patch.object(
                    hygiene, "_read_toml", return_value=idas_compat_metadata(hygiene)
                ),
                mock.patch.object(hygiene, "resolve_source_jar", return_value=target),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_SHA256", sha256_bytes(target.read_bytes())
                ),
                self.assertRaisesRegex(
                    hygiene.VerificationError, "forbidden payloads"
                ),
            ):
                hygiene.verify_idas_compat_source_evidence(ROOT, ROOT / "server-test")

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
                        "targets",
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
            self.hygiene.VerificationError, "quest audit"
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
            self.hygiene.VerificationError, r"application source .* context changed"
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


class CanonicalBootOracleNegativeTests(unittest.TestCase):
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

    def verify_pair(self, latest: str, debug: str):
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            (install / "logs").mkdir()
            (install / "logs" / "latest.log").write_text(latest, encoding="utf-8")
            (install / "logs" / "debug.log").write_text(debug, encoding="utf-8")
            with (
                mock.patch.object(self.hygiene, "verify_install_provenance"),
                mock.patch.object(self.hygiene, "verify_jdt_evidence"),
                mock.patch.object(self.hygiene, "verify_sable_source_evidence"),
                mock.patch.object(
                    self.hygiene, "verify_idas_compat_source_evidence"
                ),
            ):
                return self.hygiene.verify_boot_run(
                    ROOT, install, self.nonce, self.status
                )

    def assert_pair_rejected(self, latest: str, debug: str) -> None:
        with self.assertRaises(self.hygiene.VerificationError):
            self.verify_pair(latest, debug)

    def test_current_log_pair_is_accepted(self) -> None:
        result = self.verify_pair(self.latest, self.debug)
        self.assertEqual(sum(result["errors"].values()), 14)
        self.assertEqual(sum(result["warnings"].values()), 39)

    def test_malformed_error_and_fatal_headers_in_both_logs_are_rejected(self) -> None:
        variants = (
            "[08Aug2026 12:00:00.000] [main/ERROR [fixture.Hidden/]: injected",
            "[08Aug2026 12:00:00.000] [main/FATAL] fixture.Hidden/]: injected",
            "\x1b[31m[08Aug2026 12:00:00.000] [main/ERROR "
            "[fixture.Hidden/]: injected\x1b[0m",
        )
        for line in variants:
            with self.subTest(line=line):
                self.assert_pair_rejected(
                    self.latest + line + "\n", self.debug + line + "\n"
                )

    def test_latest_only_sable_thread_relocation_is_rejected(self) -> None:
        original = (
            "[main/ERROR] "
            "[net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM]: "
            f"{self.hygiene.RUNTIME_DIST_CLEANER_MESSAGE}"
        )
        changed = original.replace("[main/ERROR]", "[Unrelated-Worker/ERROR]")
        self.assert_pair_rejected(
            self.latest.replace(original, changed, 1), self.debug
        )

    def test_cross_log_error_continuation_disagreement_is_rejected(self) -> None:
        marker = (
            " Mods that bundle Fabric API: "
            "[forgified-fabric-api-0.115.6+2.1.0+1.21.1.jar]"
        )
        changed_debug = insert_after_line(
            self.debug, marker, "Caused by: fixture.RelocatedCause"
        )
        self.assert_pair_rejected(self.latest, changed_debug)

    def test_added_error_cause_in_both_logs_is_rejected(self) -> None:
        marker = (
            " Mods that bundle Fabric API: "
            "[forgified-fabric-api-0.115.6+2.1.0+1.21.1.jar]"
        )
        latest = insert_after_line(self.latest, marker, "Caused by: fixture.AddedCause")
        debug = insert_after_line(self.debug, marker, "Caused by: fixture.AddedCause")
        self.assert_pair_rejected(latest, debug)

    def test_non_anchor_error_frame_mutation_in_both_logs_is_rejected(self) -> None:
        original = "DataResult$Error.getOrThrow(DataResult.java:287)"
        replacement = "DataResult$Error.getOrThrow(DataResult.java:288)"
        self.assertIn(original, self.latest)
        self.assert_pair_rejected(
            self.latest.replace(original, replacement, 1),
            self.debug.replace(original, replacement, 1),
        )

    def test_warning_continuation_mutation_in_both_logs_is_rejected(self) -> None:
        marker = self.hygiene.JDT_WARNING_MESSAGE
        latest = insert_after_line(
            self.latest, marker, "Caused by: fixture.UnreviewedWarningCause"
        )
        debug = insert_after_line(
            self.debug, marker, "Caused by: fixture.UnreviewedWarningCause"
        )
        self.assert_pair_rejected(latest, debug)

    def test_warning_cross_log_disagreement_is_rejected(self) -> None:
        changed_debug = self.debug.replace(
            "justdirethings:fuel_canister",
            "justdirethings:relocated_canister",
            1,
        )
        self.assert_pair_rejected(self.latest, changed_debug)

    def test_quest_digest_is_derived_from_generated_script(self) -> None:
        self.assertEqual(
            self.hygiene.quest_audit_expectation(ROOT),
            (
                "8428e54a802bb23013ff5d79c80592bec7b295351330ef4570458ac32f33fecd",
                219,
            ),
        )

    def test_zero_and_mutated_quest_digests_are_rejected(self) -> None:
        digest = (
            "8428e54a802bb23013ff5d79c80592bec7b295351330ef4570458ac32f33fecd"
        )
        for replacement in ("0" * 64, "1" + digest[1:]):
            with self.subTest(replacement=replacement):
                self.assert_pair_rejected(
                    self.latest.replace(digest, replacement, 1),
                    self.debug.replace(digest, replacement, 1),
                )

    def test_done_after_shutdown_is_rejected(self) -> None:
        destination = "ThreadedAnvilChunkStorage: All dimensions are saved"
        self.assert_pair_rejected(
            move_line_after(self.latest, "DedicatedServer/]: Done (", destination),
            move_line_after(self.debug, "DedicatedServer/]: Done (", destination),
        )

    def test_duplicate_final_save_marker_is_rejected(self) -> None:
        marker = "ThreadedAnvilChunkStorage: All dimensions are saved"
        self.assert_pair_rejected(
            duplicate_line(self.latest, marker), duplicate_line(self.debug, marker)
        )

    def test_missing_and_duplicate_state_markers_are_rejected(self) -> None:
        markers = (
            self.hygiene.IDAS_COMPAT_READY_MESSAGE,
            *self.hygiene.IDAS_COMPAT_BOOT_SANITIZED_MESSAGES,
            "DedicatedServer/]: Done (",
            "[AFTERLIGHT QUEST ITEM AUDIT] OK ",
            "FTB Quests/]: Loaded 6 chapter groups, 41 chapters, 283 quests, 6 reward tables",
            "MinecraftServer/]: Stopping server",
            "MinecraftServer/]: Saving players",
            "MinecraftServer/]: Saving worlds",
            "ThreadedAnvilChunkStorage: All dimensions are saved",
        )
        for marker in markers:
            with self.subTest(marker=marker, mutation="missing"):
                self.assert_pair_rejected(
                    remove_line(self.latest, marker), remove_line(self.debug, marker)
                )
            with self.subTest(marker=marker, mutation="duplicate"):
                self.assert_pair_rejected(
                    duplicate_line(self.latest, marker),
                    duplicate_line(self.debug, marker),
                )

    def test_reordered_state_markers_are_rejected(self) -> None:
        pairs = (
            (
                self.hygiene.IDAS_COMPAT_BOOT_SANITIZED_MESSAGES[0],
                self.hygiene.IDAS_COMPAT_BOOT_SANITIZED_MESSAGES[1],
            ),
            ("DedicatedServer/]: Done (", "[AFTERLIGHT QUEST ITEM AUDIT] OK "),
            (
                "[AFTERLIGHT QUEST ITEM AUDIT] OK ",
                "FTB Quests/]: Loaded 6 chapter groups, 41 chapters, 283 quests, 6 reward tables",
            ),
            ("MinecraftServer/]: Saving players", "MinecraftServer/]: Saving worlds"),
        )
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assert_pair_rejected(
                    swap_lines(self.latest, first, second),
                    swap_lines(self.debug, first, second),
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
