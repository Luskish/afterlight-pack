from __future__ import annotations

import hashlib
import importlib
import io
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
import warnings
import zipfile
from collections import Counter
from dataclasses import replace
from unittest import mock
from pathlib import Path
from urllib.parse import quote


tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
DEBUG_LOG = ROOT / "server-test" / "logs" / "debug.log"
LATEST_LOG = ROOT / "server-test" / "logs" / "latest.log"
BOOT_LOG = ROOT / "server-test" / "boot.log"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from live_install_support import requires_live_install
from tools.tests import test_afterlight_quests as quest_contracts


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
    base: Path, side: str = "both", download_hash_format: str = "sha256"
) -> tuple[Path, Path, Path]:
    root = base / "pack"
    install = base / "install"
    (root / "mods").mkdir(parents=True)
    (install / "mods").mkdir(parents=True)

    jar_bytes = b"authenticated fixture jar"
    jar_hash = hashlib.new(download_hash_format, jar_bytes).hexdigest()
    metadata = (
        'name = "Fixture Mod"\n'
        'filename = "fixture.jar"\n'
        f'side = "{side}"\n\n'
        '[download]\n'
        f'hash-format = "{download_hash_format}"\n'
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
        'name = "AFTERLIGHT"\n'
        'author = "Shane + ECHO"\n'
        'version = "test-fixture"\n'
        'pack-format = "packwiz:1.1.0"\n\n'
        '[index]\n'
        'file = "index.toml"\n'
        'hash-format = "sha256"\n'
        f'hash = "{sha256_bytes(index)}"\n\n'
        '[versions]\n'
        'minecraft = "1.21.1"\n'
        'neoforge = "21.1.248"\n'
    ).encode()
    (root / "pack.toml").write_bytes(pack)

    jar_path = install / "mods" / "fixture.jar"
    jar_path.write_bytes(jar_bytes)
    cached_record = (
        {"optionValue": True, "onlyOtherSide": True}
        if side == "client"
        else {
            "hash": {"type": "sha256", "value": sha256_bytes(metadata)},
            "linkedFileHash": {"type": download_hash_format, "value": jar_hash},
            "cachedLocation": "mods/fixture.jar",
            "optionValue": True,
        }
    )
    provenance = {
        "packFileHash": {"type": "sha256", "value": sha256_bytes(pack)},
        "indexFileHash": {"type": "sha256", "value": sha256_bytes(index)},
        "cachedFiles": {"mods/fixture.pw.toml": cached_record},
        "cachedSide": "server",
    }
    (install / "packwiz.json").write_text(json.dumps(provenance), encoding="utf-8")
    return root, install, jar_path


def write_manifest_entry_fixture(
    base: Path, relative: str, payload: bytes = b"fixture"
) -> Path:
    root = base / "pack"
    target = root / Path(relative)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    index = (
        'hash-format = "sha256"\n\n'
        '[[files]]\n'
        f'file = "{relative}"\n'
        f'hash = "{sha256_bytes(payload)}"\n'
    ).encode()
    (root / "index.toml").write_bytes(index)
    pack = (
        'name = "AFTERLIGHT"\n'
        'author = "Shane + ECHO"\n'
        'version = "test-fixture"\n'
        'pack-format = "packwiz:1.1.0"\n\n'
        '[index]\n'
        'file = "index.toml"\n'
        'hash-format = "sha256"\n'
        f'hash = "{sha256_bytes(index)}"\n\n'
        '[versions]\n'
        'minecraft = "1.21.1"\n'
        'neoforge = "21.1.248"\n'
    ).encode()
    (root / "pack.toml").write_bytes(pack)
    return root


def valid_boot_log(nonce: str) -> str:
    hygiene = hygiene_module()
    quest_digest, item_count = hygiene.quest_audit_expectation(ROOT)
    gate_digest, recipe_count = hygiene.gate_audit_expectation(ROOT)
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
            f"[AFTERLIGHT QUEST ITEM AUDIT] OK {quest_digest} {item_count} {nonce}",
            "[08Aug2026 12:00:01.250] [Server thread/INFO] [KubeJS Server/]: "
            f"[AFTERLIGHT GATE RECIPE AUDIT] OK {gate_digest} {recipe_count} {nonce}",
            "[08Aug2026 12:00:01.500] [Server thread/INFO] [FTB Quests/]: "
            "Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
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


def valid_gate_boot_log(nonce: str, *, gate_first: bool = True) -> str:
    hygiene = hygiene_module()
    quest_digest, item_count = hygiene.quest_audit_expectation(ROOT)
    gate_digest, recipe_count = hygiene.gate_audit_expectation(ROOT)
    gate = (
        "[08Aug2026 12:00:01.000] [Server thread/INFO] [KubeJS Server/]: "
        f"[AFTERLIGHT GATE RECIPE AUDIT] OK {gate_digest} {recipe_count} {nonce}"
    )
    quest = (
        "[08Aug2026 12:00:01.250] [Server thread/INFO] [KubeJS Server/]: "
        f"[AFTERLIGHT QUEST ITEM AUDIT] OK {quest_digest} {item_count} {nonce}"
    )
    audits = (gate, quest) if gate_first else (quest, gate)
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
            *audits,
            "[08Aug2026 12:00:01.500] [Server thread/INFO] [FTB Quests/]: "
            "Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
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


def replace_first_warning(log_text: str, replacement: str) -> str:
    lines = log_text.splitlines()
    index = next(index for index, line in enumerate(lines) if "/WARN]" in line)
    lines[index] = replacement
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


def shared_header_alias_archive_bytes(
    name: str, payload: bytes, copies: int
) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr(name, payload)
    original = output.getvalue()
    end_offset = original.rfind(b"PK\x05\x06")
    if end_offset < 0:
        raise AssertionError("fixture ZIP has no end-of-central-directory record")
    (
        signature,
        disk_number,
        central_directory_disk,
        disk_entries,
        total_entries,
        central_directory_size,
        central_directory_offset,
        comment_size,
    ) = struct.unpack_from("<4s4H2LH", original, end_offset)
    if disk_entries != 1 or total_entries != 1:
        raise AssertionError("fixture ZIP must begin with exactly one member")
    central_directory = original[
        central_directory_offset : central_directory_offset + central_directory_size
    ]
    comment = original[end_offset + 22 : end_offset + 22 + comment_size]
    end_record = struct.pack(
        "<4s4H2LH",
        signature,
        disk_number,
        central_directory_disk,
        copies,
        copies,
        central_directory_size * copies,
        central_directory_offset,
        comment_size,
    )
    return b"".join(
        (
            original[:central_directory_offset],
            central_directory * copies,
            end_record,
            comment,
        )
    )


def empty_mixin_scan() -> dict[str, object]:
    return {
        "archive_scopes": 0,
        "mixin_configs": 0,
        "common_mixins": 0,
        "server_mixins": 0,
        "annotation_clientlevel_mixins": 0,
        "direct_clientlevel_mixins": 0,
        "pseudo_clientlevel_candidates": [],
        "mixin_config_hashes": {},
        "mixin_corpus_entries": [],
        "client_target_candidates": [],
        "client_target_class_evidence": {},
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
                    hygiene.VerificationError, "malformed or relocated log header"
                ):
                    hygiene.parse_log_records(line + "\n")

    def test_relocated_headers_for_every_severity_are_rejected(self) -> None:
        hygiene = hygiene_module()
        prefix = (
            "[08Aug2026 11:59:59.000] [main/INFO] "
            "[fixture.Anchor/SOURCE]: anchor\n"
        )
        for severity in ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"):
            header = (
                "[08Aug2026 12:00:00.000] "
                f"[main/{severity}] [fixture.Hidden/SOURCE]: injected"
            )
            for relocated in (f" {header}", f"prefix {header}"):
                with self.subTest(severity=severity, relocated=relocated):
                    with self.assertRaisesRegex(
                        hygiene.VerificationError, "malformed or relocated log header"
                    ):
                        hygiene.parse_log_records(prefix + relocated + "\n")

    def test_interior_ansi_cannot_construct_a_header(self) -> None:
        hygiene = hygiene_module()
        variants = (
            "[08Aug2026 12:00:00.000] [main/ER\x1b[0mROR] "
            "[fixture.Hidden/SOURCE]: injected",
            "[08Aug2026 12:00:00.000] [ma\x1b[31min/WARN] "
            "[fixture.Hidden/SOURCE]: injected",
            "[08Aug2026 12:00:00.000] [main/FATAL] "
            "[fixture.Hid\x1b[0mden/SOURCE]: injected",
        )
        for line in variants:
            with self.subTest(line=line):
                with self.assertRaisesRegex(
                    hygiene.VerificationError, "unsupported interior ANSI"
                ):
                    hygiene.parse_log_records(line + "\n")

    def test_unattached_continuation_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with self.assertRaisesRegex(hygiene.VerificationError, "unattached log line"):
            hygiene.parse_log_records("java.lang.IllegalStateException: orphan\n")

    def test_compound_exception_classes_are_severe_without_prose_false_positives(
        self,
    ) -> None:
        hygiene = hygiene_module()
        severe_messages = (
            "java.lang.IllegalStateException: invalid state",
            "java.util.concurrent.CompletionException: failed future",
            "java.lang.NoClassDefFoundError: missing class",
            "example.mod.DeeplySpecificLoadException: failed mod",
        )
        for message in severe_messages:
            record = hygiene.LogRecord(
                "08Aug2026 12:00:00.000",
                "main",
                "INFO",
                "fixture/",
                message,
                (),
                "",
            )
            with self.subTest(message=message):
                self.assertEqual(
                    len(hygiene._severe_console_projection((record,))), 1
                )

        benign = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "main",
            "INFO",
            "fixture/",
            "Exception handling and error recovery documentation loaded",
            (),
            "",
        )
        self.assertEqual(hygiene._severe_console_projection((benign,)), ())

    def test_bare_exception_error_and_throwable_are_severe_at_info_and_warn(
        self,
    ) -> None:
        hygiene = hygiene_module()
        projections = (
            (
                "latest",
                hygiene.parse_log_records,
                "[08Aug2026 12:00:00.000] [main/{level}] "
                "[fixture/]: {message}\n",
            ),
            (
                "debug",
                hygiene.parse_log_records,
                "[08Aug2026 12:00:00.000] [main/{level}] "
                "[fixture/]: {message}\n",
            ),
            (
                "console",
                hygiene.parse_console_records,
                "[12:00:00.000] [main/{level}] [fixture/]: {message}\n",
            ),
        )
        for projection, parser, template in projections:
            for level in ("INFO", "WARN"):
                for message in (
                    "Exception: injected",
                    "Throwable: injected",
                    "Error: injected",
                ):
                    records = parser(template.format(level=level, message=message))
                    with self.subTest(
                        projection=projection, level=level, message=message
                    ):
                        self.assertEqual(
                            len(hygiene._severe_console_projection(records)), 1
                        )

        for benign_message in (
            "Exception handling and error recovery documentation loaded",
            "Recovered from an Error: retry succeeded",
        ):
            record = hygiene.LogRecord(
                "08Aug2026 12:00:00.000",
                "main",
                "INFO",
                "fixture/",
                benign_message,
                (),
                "",
            )
            with self.subTest(benign_message=benign_message):
                self.assertEqual(
                    hygiene._severe_console_projection((record,)), ()
                )

    def test_warning_path_projection_is_checkout_and_install_root_portable(self) -> None:
        hygiene = hygiene_module()
        first_workspace = Path("/Users/example/first-checkout")
        second_workspace = Path("/opt/build/relocated-checkout")
        first_install = first_workspace / "isolated-server"
        second_install = second_workspace / "different-install"

        def evidence(workspace: Path, install: Path) -> tuple[str, int, int]:
            records = hygiene.parse_log_records(
                "[08Aug2026 12:00:00.000] [main/WARN] [fixture/]: "
                f"source={workspace}/config/fixture.toml install={install}/mods/a.jar\n"
                f"continuation {install}/libraries/example.jar\n"
            )
            return hygiene.warning_multiset_evidence(
                records, workspace_root=workspace, install_root=install
            )

        self.assertEqual(
            evidence(first_workspace, first_install),
            evidence(second_workspace, second_install),
        )

    def test_warning_uri_encoded_roots_are_portable_without_decoding_unrelated_text(
        self,
    ) -> None:
        hygiene = hygiene_module()
        first_workspace = Path("/Users/example/AFTERLIGHT review")
        second_workspace = Path("/opt/build/relocated AFTERLIGHT review")
        first_install = first_workspace / "isolated server"
        second_install = second_workspace / "different install"

        def evidence(
            workspace: Path, install: Path, *, safe: str
        ) -> tuple[str, int, int]:
            encoded_workspace = quote(str(workspace), safe=safe)
            encoded_install = quote(str(install), safe=safe)
            records = hygiene.parse_log_records(
                "[08Aug2026 12:00:00.000] [main/WARN] [fixture/]: "
                f"source={encoded_workspace}/config/fixture.toml "
                f"install={encoded_install}/mods/a.jar\n"
                f"continuation {encoded_install}/libraries/example.jar\n"
            )
            return hygiene.warning_multiset_evidence(
                records, workspace_root=workspace, install_root=install
            )

        for safe in ("/:", ""):
            with self.subTest(safe=safe):
                self.assertEqual(
                    evidence(first_workspace, first_install, safe=safe),
                    evidence(second_workspace, second_install, safe=safe),
                )

        unrelated = "note=AFTERLIGHT%20review and /tmp/unrelated%20path"
        self.assertEqual(
            hygiene._normalize_absolute_roots(
                unrelated,
                workspace_root=first_workspace,
                install_root=first_install,
            ),
            unrelated,
        )

    def test_supplementaries_way_sign_worker_threads_are_portable_and_narrow(
        self,
    ) -> None:
        hygiene = hygiene_module()
        message = (
            "Could not find Sign for wood cataclysm:chorus. Does this block even "
            "exist? It should! Skipping way sign recipe generation"
        )

        def record(thread: str, logger: str = "Supplementaries/", text: str = message):
            return hygiene.LogRecord(
                "08Aug2026 12:00:00.000",
                thread,
                "WARN",
                logger,
                text,
                (),
                "",
            )

        local = hygiene.canonical_record_fingerprint(record("pool-14-thread-1"))
        ci = hygiene.canonical_record_fingerprint(record("pool-5-thread-1"))
        self.assertEqual(local, ci)
        self.assertNotEqual(
            local,
            hygiene.canonical_record_fingerprint(record("main")),
        )
        self.assertNotEqual(
            local,
            hygiene.canonical_record_fingerprint(record("pool-14-thread-999")),
        )
        self.assertNotEqual(
            local,
            hygiene.canonical_record_fingerprint(
                record("pool-5-thread-1", logger="fixture/")
            ),
        )
        self.assertNotEqual(
            local,
            hygiene.canonical_record_fingerprint(
                record("pool-5-thread-1", text="unreviewed warning")
            ),
        )

    def test_lan_pinger_route_warning_is_zero_or_one_exact_record(self) -> None:
        hygiene = hygiene_module()
        stable = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "main",
            "WARN",
            "fixture/",
            "stable reviewed warning",
            (),
            "",
        )
        optional = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "LanServerPinger #1",
            "WARN",
            "net.minecraft.client.server.LanServerPinger/",
            "LanServerPinger: No route to host",
            (),
            "",
        )
        digest, total, unique = hygiene.warning_multiset_evidence((stable,))
        with (
            mock.patch.object(hygiene, "REVIEWED_WARNING_MULTISET_SHA256", digest),
            mock.patch.object(hygiene, "REVIEWED_WARNING_TOTAL", total),
            mock.patch.object(hygiene, "REVIEWED_WARNING_UNIQUE", unique),
        ):
            hygiene._validate_reviewed_warning_multiset((stable,), "fixture")
            hygiene._validate_reviewed_warning_multiset(
                (stable, optional), "fixture"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "optional environmental WARN"
            ):
                hygiene._validate_reviewed_warning_multiset(
                    (stable, optional, optional), "fixture"
                )
            mutations = (
                replace(optional, thread="main"),
                replace(optional, thread="LanServerPinger #2"),
                replace(optional, message="LanServerPinger: changed"),
                replace(optional, continuations=("Caused by: fixture.Hidden",)),
            )
            for changed in mutations:
                with self.subTest(changed=changed), self.assertRaises(
                    hygiene.VerificationError
                ):
                    hygiene._validate_reviewed_warning_multiset(
                        (stable, changed), "fixture"
                    )

    def test_spark_world_statistics_timeout_is_zero_or_one_exact_record(self) -> None:
        hygiene = hygiene_module()
        stable = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "main",
            "WARN",
            "fixture/",
            "stable reviewed warning",
            (),
            "",
        )
        optional = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "spark-async-sampler-worker-thread",
            "WARN",
            "spark/",
            "Timed out waiting for world statistics",
            (),
            "",
        )
        digest, total, unique = hygiene.warning_multiset_evidence((stable,))
        with (
            mock.patch.object(hygiene, "REVIEWED_WARNING_MULTISET_SHA256", digest),
            mock.patch.object(hygiene, "REVIEWED_WARNING_TOTAL", total),
            mock.patch.object(hygiene, "REVIEWED_WARNING_UNIQUE", unique),
        ):
            hygiene._validate_reviewed_warning_multiset((stable,), "fixture")
            hygiene._validate_reviewed_warning_multiset(
                (stable, optional), "fixture"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "optional environmental WARN"
            ):
                hygiene._validate_reviewed_warning_multiset(
                    (stable, optional, optional), "fixture"
                )
            mutations = (
                replace(optional, thread="main"),
                replace(optional, logger="fixture/"),
                replace(optional, message="Timed out waiting for changed statistics"),
                replace(optional, continuations=("Caused by: fixture.Hidden",)),
            )
            for changed in mutations:
                with self.subTest(changed=changed), self.assertRaises(
                    hygiene.VerificationError
                ):
                    hygiene._validate_reviewed_warning_multiset(
                        (stable, changed), "fixture"
                    )

    def test_distinct_optional_environment_warnings_have_independent_quotas(
        self,
    ) -> None:
        hygiene = hygiene_module()
        stable = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "main",
            "WARN",
            "fixture/",
            "stable reviewed warning",
            (),
            "",
        )
        lan = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "LanServerPinger #1",
            "WARN",
            "net.minecraft.client.server.LanServerPinger/",
            "LanServerPinger: No route to host",
            (),
            "",
        )
        spark = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "spark-async-sampler-worker-thread",
            "WARN",
            "spark/",
            "Timed out waiting for world statistics",
            (),
            "",
        )
        digest, total, unique = hygiene.warning_multiset_evidence((stable,))
        with (
            mock.patch.object(hygiene, "REVIEWED_WARNING_MULTISET_SHA256", digest),
            mock.patch.object(hygiene, "REVIEWED_WARNING_TOTAL", total),
            mock.patch.object(hygiene, "REVIEWED_WARNING_UNIQUE", unique),
        ):
            hygiene._validate_reviewed_warning_multiset(
                (stable, lan, spark), "fixture"
            )

    def test_warning_multiset_failure_preserves_log_label(self) -> None:
        hygiene = hygiene_module()
        stable = hygiene.LogRecord(
            "08Aug2026 12:00:00.000",
            "main",
            "WARN",
            "fixture/",
            "stable reviewed warning",
            (),
            "",
        )
        unknown = replace(stable, message="unreviewed warning")
        digest, total, unique = hygiene.warning_multiset_evidence((stable,))
        with (
            mock.patch.object(hygiene, "REVIEWED_WARNING_MULTISET_SHA256", digest),
            mock.patch.object(hygiene, "REVIEWED_WARNING_TOTAL", total),
            mock.patch.object(hygiene, "REVIEWED_WARNING_UNIQUE", unique),
            self.assertRaisesRegex(
                hygiene.VerificationError,
                r"^fixture complete WARN fingerprint multiset changed",
            ),
        ):
            hygiene._validate_reviewed_warning_multiset(
                (stable, unknown), "fixture"
            )

    def test_mixin_synthetic_rename_session_id_is_the_only_normalized_field(
        self,
    ) -> None:
        hygiene = hygiene_module()
        template = (
            "Renaming synthetic method lambda$getStacks$0()Ljava/lang/"
            "IllegalStateException; to {session}$fabric$lambda$getStacks$0$0 "
            "in fixture.mixins.json:FixtureMixin from mod fixture"
        )

        def record(session: str, suffix: str = "FixtureMixin"):
            return hygiene.LogRecord(
                "08Aug2026 12:00:00.000",
                "main",
                "DEBUG",
                "mixin/",
                template.format(session=session).replace("FixtureMixin", suffix),
                (),
                "fixture",
            )

        first = hygiene.canonical_record_tuple(record("md0f210e"))
        second = hygiene.canonical_record_tuple(record("md6e4466"))
        self.assertEqual(first, second)
        self.assertNotEqual(
            first,
            hygiene.canonical_record_tuple(
                record("md6e4466", suffix="SubstitutedMixin")
            ),
        )
        self.assertNotEqual(
            first,
            hygiene.canonical_record_tuple(record("prefix6e4466")),
        )


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

    def test_server_listed_clientlevel_mixin_is_scanned(self) -> None:
        hygiene = hygiene_module()
        output = io.BytesIO()
        config = json.dumps(
            {
                "required": True,
                "package": "fixture",
                "server": ["ServerLevelsMixin"],
            },
            sort_keys=True,
        ).encode("utf-8")
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(
                "META-INF/neoforge.mods.toml",
                '[[mixins]]\nconfig = "fixture.mixins.json"\n',
            )
            archive.writestr("fixture.mixins.json", config)
            archive.writestr(
                "fixture/ServerLevelsMixin.class",
                mixin_class_bytes(value_targets=(self.client_descriptor,)),
            )
        scan = empty_mixin_scan()
        hygiene._scan_mixin_archive("mods/server.pw.toml", output.getvalue(), scan)
        self.assertEqual(scan["server_mixins"], 1)
        self.assertEqual(scan["annotation_clientlevel_mixins"], 1)

    def test_common_client_targets_are_derived_across_platform_and_mod_packages(
        self,
    ) -> None:
        hygiene = hygiene_module()
        targets = (
            "Lnet/minecraft/client/multiplayer/ClientLevel;",
            "Lnet/neoforged/neoforge/client/ClientHooks;",
            "Lnet/caffeinemc/mods/sodium/client/render/chunk/BlockRenderer;",
            "Lcom/simibubi/create/CreateClient;",
            "Lfixture/client/render/ModSpecificRenderer;",
            "Ldev/emi/emi/screen/RecipeScreen;",
            "Lnet/createmod/catnip/gui/AbstractSimiScreen;",
            "Ldev/lopyluna/dndesires/compat/jei/category/DragonBreathingCategory;",
            "Ldev/lopyluna/dndesires/compat/jei/category/FreezingCategory;",
            "Ldev/lopyluna/dndesires/compat/jei/category/SandingCategory;",
            "Lnet/dakotapride/garnished/registry/JEI/DyeBlowingFanCategory;",
            "Lnet/dakotapride/garnished/registry/JEI/FreezingFanCategory;",
            "Lcom/simibubi/create/compat/jei/category/CreateRecipeCategory;",
            "Lmezz/jei/gui/bookmarks/BookmarkList;",
            "Lmezz/jei/gui/overlay/bookmarks/BookmarkOverlay;",
            "Lmezz/jei/library/plugins/vanilla/ingredients/ItemStackListFactory;",
        )
        output = io.BytesIO()
        config = json.dumps(
            {"required": True, "package": "fixture", "mixins": ["ClientTargetsMixin"]},
            sort_keys=True,
        ).encode("utf-8")
        class_payload = mixin_class_bytes(value_targets=targets)
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr(
                "META-INF/neoforge.mods.toml",
                '[[mixins]]\nconfig = "fixture.mixins.json"\n',
            )
            archive.writestr("fixture.mixins.json", config)
            archive.writestr("fixture/ClientTargetsMixin.class", class_payload)
            archive.writestr("fixture/client/render/ModSpecificRenderer.class", b"client")
        scan = empty_mixin_scan()
        hygiene._scan_mixin_archive("mods/client-targets.pw.toml", output.getvalue(), scan)
        candidates = hygiene._finalize_client_target_inventory(scan)
        self.assertEqual(len(candidates), len(targets))
        self.assertEqual(tuple(candidate[-2] for candidate in candidates), targets)
        self.assertTrue(all(candidate[-1] for candidate in candidates))

    def test_corpus_entry_binds_position_class_hash_form_and_targets(self) -> None:
        hygiene = hygiene_module()
        payload = mixin_class_bytes(
            string_targets=("net.minecraft.server.level.ServerLevel",)
        )
        scan = empty_mixin_scan()
        hygiene._scan_mixin_archive(
            "mods/fixture.pw.toml", mixin_archive_bytes(payload), scan
        )
        entries = scan["mixin_corpus_entries"]
        self.assertEqual(len(entries), 3)
        mixin_entry = next(entry for entry in entries if entry[0] == "mixin")
        self.assertEqual(mixin_entry[1], "mods/fixture.pw.toml")
        self.assertEqual(mixin_entry[3], "mixins")
        self.assertEqual(mixin_entry[4], 0)
        self.assertEqual(mixin_entry[5], "LevelsMixin")
        self.assertEqual(mixin_entry[7], sha256_bytes(payload))
        self.assertEqual(mixin_entry[10], "targets")
        self.assertEqual(
            mixin_entry[11], ("Lnet/minecraft/server/level/ServerLevel;",)
        )

    def test_duplicate_config_and_class_members_are_rejected(self) -> None:
        hygiene = hygiene_module()
        output = io.BytesIO()
        first_config = json.dumps(
            {"package": "fixture", "mixins": ["LevelsMixin"]}, sort_keys=True
        ).encode("utf-8")
        second_config = json.dumps(
            {"package": "fixture", "server": ["LevelsMixin"]}, sort_keys=True
        ).encode("utf-8")
        first_class = mixin_class_bytes(value_targets=(self.server_descriptor,))
        second_class = mixin_class_bytes(value_targets=(self.client_descriptor,))
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr(
                    "META-INF/neoforge.mods.toml",
                    '[[mixins]]\nconfig = "fixture.mixins.json"\n',
                )
                archive.writestr("fixture.mixins.json", first_config)
                archive.writestr("fixture.mixins.json", second_config)
                archive.writestr("fixture/LevelsMixin.class", first_class)
                archive.writestr("fixture/LevelsMixin.class", second_class)
        with self.assertRaisesRegex(hygiene.VerificationError, "duplicate ZIP member"):
            hygiene._scan_mixin_archive(
                "mods/duplicate.pw.toml", output.getvalue(), empty_mixin_scan()
            )

    def test_duplicate_members_in_nested_archive_are_rejected(self) -> None:
        hygiene = hygiene_module()
        nested = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(nested, "w") as archive:
                archive.writestr("duplicate.txt", b"first")
                archive.writestr("duplicate.txt", b"second")
        outer = io.BytesIO()
        with zipfile.ZipFile(outer, "w") as archive:
            archive.writestr("META-INF/jarjar/nested.jar", nested.getvalue())
        with self.assertRaisesRegex(hygiene.VerificationError, "duplicate ZIP member"):
            hygiene._scan_mixin_archive(
                "mods/outer.pw.toml", outer.getvalue(), empty_mixin_scan()
            )

    def test_reviewed_shared_header_duplicate_uses_canonical_member(self) -> None:
        hygiene = hygiene_module()
        label = "mods/reviewed-alias.pw.toml"
        name = "META-INF/LICENSE.txt"
        payload = b"reviewed shared-header payload\n"
        archive_payload = shared_header_alias_archive_bytes(name, payload, 6)
        original_read = zipfile.ZipFile.read

        def strict_read(
            archive: zipfile.ZipFile,
            member: str | zipfile.ZipInfo,
            pwd: bytes | None = None,
        ) -> bytes:
            if isinstance(member, zipfile.ZipInfo):
                aliases = tuple(
                    info
                    for info in archive.infolist()
                    if info.filename == member.filename
                )
                end_offset = getattr(member, "_end_offset", None)
                if len(aliases) > 1 and (
                    end_offset is None or end_offset <= member.header_offset
                ):
                    raise zipfile.BadZipFile(
                        f"Overlapped entries: {member.filename!r} (possible zip bomb)"
                    )
            return original_read(archive, member, pwd)

        reviewed = {(label, name): (6, sha256_bytes(payload))}
        scan = empty_mixin_scan()
        with (
            mock.patch.object(hygiene, "REVIEWED_DUPLICATE_ZIP_MEMBERS", reviewed),
            mock.patch.object(zipfile.ZipFile, "read", strict_read),
        ):
            hygiene._scan_mixin_archive(label, archive_payload, scan)
        self.assertEqual(scan["archive_scopes"], 1)

    def test_reviewed_shared_header_duplicate_rejects_metadata_drift(self) -> None:
        hygiene = hygiene_module()
        label = "mods/reviewed-alias.pw.toml"
        name = "META-INF/LICENSE.txt"
        payload = b"reviewed shared-header payload\n"
        archive_payload = bytearray(
            shared_header_alias_archive_bytes(name, payload, 6)
        )
        end_offset = archive_payload.rfind(b"PK\x05\x06")
        end_record = struct.unpack_from("<4s4H2LH", archive_payload, end_offset)
        central_directory_size = end_record[5]
        central_directory_offset = end_record[6]
        member_size = central_directory_size // 6
        external_attributes_offset = central_directory_offset + member_size + 38
        external_attributes = struct.unpack_from(
            "<L", archive_payload, external_attributes_offset
        )[0]
        struct.pack_into(
            "<L",
            archive_payload,
            external_attributes_offset,
            external_attributes ^ 1,
        )

        reviewed = {(label, name): (6, sha256_bytes(payload))}
        with (
            mock.patch.object(hygiene, "REVIEWED_DUPLICATE_ZIP_MEMBERS", reviewed),
            self.assertRaisesRegex(hygiene.VerificationError, "metadata"),
        ):
            hygiene._scan_mixin_archive(
                label, bytes(archive_payload), empty_mixin_scan()
            )

    @requires_live_install(ROOT)
    def test_real_corpus_processes_every_mixin_scope(self) -> None:
        hygiene = hygiene_module()
        evidence = hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")
        self.assertEqual(evidence["archive_scopes"], 305)
        self.assertEqual(evidence["mixin_configs"], 261)
        self.assertEqual(evidence["common_mixins"], 2286)
        self.assertEqual(evidence["server_mixins"], 5)
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

    @requires_live_install(ROOT)
    def test_sable_dedicated_verifier_accepts_current_named_context(self) -> None:
        hygiene = hygiene_module()
        records = hygiene.parse_log_records(
            DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        )
        indices = hygiene._validate_sable_debug_records(
            records, hygiene.project_sable_error_requirement()
        )
        self.assertEqual(len(indices), 12)

    @requires_live_install(ROOT)
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

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_added_substitute_context(self) -> None:
        hygiene = hygiene_module()
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = add_unrelated_record_context(
            debug_text,
            "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
            hygiene.RUNTIME_DIST_CLEANER_MESSAGE,
        )
        self.assert_sable_debug_rejected(substituted, "provenance count mismatch")

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_named_prepare_source_substitution(self) -> None:
        hygiene = hygiene_module()
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "sable.mixins.json:entity.entity_aabb_lookup.LevelsMixin from mod sable",
            "substitute.mixins.json:other.LevelsMixin from mod substitute",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "prepare source context")

    @requires_live_install(ROOT)
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

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_changed_normalized_stack_source(self) -> None:
        debug_text = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        substituted = debug_text.replace(
            "RuntimeDistCleaner.processClassWithFlags(RuntimeDistCleaner.java:60)",
            "RuntimeDistCleaner.processClassWithFlags(RuntimeDistCleaner.java:61)",
            1,
        )
        self.assert_sable_debug_rejected(substituted, "normalized stack hash changed")

    @requires_live_install(ROOT)
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

    @requires_live_install(ROOT)
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
    def test_safe_relative_path_rejects_noncanonical_spelling(self) -> None:
        hygiene = hygiene_module()
        for value in (
            "config//fixture.json",
            "config/./fixture.json",
            "config/fixture.json/",
        ):
            with self.subTest(value=value), self.assertRaisesRegex(
                hygiene.VerificationError, "noncanonical"
            ):
                hygiene._safe_relative_path(value, "fixture")

    def test_manifest_rejects_pack_identity_runtime_and_index_path_drift(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            mutations = (
                ('name = "AFTERLIGHT"', 'name = "Counterfeit"', "pack name"),
                (
                    'author = "Shane + ECHO"',
                    'author = "Unknown"',
                    "pack author",
                ),
                (
                    'version = "test-fixture"',
                    'version = ""',
                    "pack version",
                ),
                (
                    'pack-format = "packwiz:1.1.0"',
                    'pack-format = "packwiz:1.0.0"',
                    "pack format",
                ),
                (
                    'minecraft = "1.21.1"',
                    'minecraft = "1.21"',
                    "Minecraft version",
                ),
                (
                    'neoforge = "21.1.248"',
                    'neoforge = "21.1.247"',
                    "NeoForge version",
                ),
            )
            for index, (original, replacement, message) in enumerate(mutations):
                with self.subTest(replacement=replacement):
                    root = write_manifest_entry_fixture(
                        base / str(index), "config/fixture.json"
                    )
                    pack_path = root / "pack.toml"
                    pack_path.write_text(
                        pack_path.read_text(encoding="utf-8").replace(
                            original, replacement, 1
                        ),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(hygiene.VerificationError, message):
                        hygiene.verify_manifest(root)

            root = write_manifest_entry_fixture(
                base / "index-path", "config/fixture.json"
            )
            (root / "nested").mkdir()
            (root / "nested" / "renamed-index.toml").write_bytes(
                (root / "index.toml").read_bytes()
            )
            pack_path = root / "pack.toml"
            pack_path.write_text(
                pack_path.read_text(encoding="utf-8").replace(
                    'file = "index.toml"',
                    'file = "nested/renamed-index.toml"',
                    1,
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(hygiene.VerificationError, "index file"):
                hygiene.verify_manifest(root)

    def test_manifest_index_drift_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, _, _ = write_provenance_fixture(Path(temporary))
            (root / "index.toml").write_text("hash-format = \"sha256\"\n", encoding="utf-8")
            with self.assertRaisesRegex(hygiene.VerificationError, "index hash"):
                hygiene.verify_manifest(root)

    def test_manifest_rejects_hash_format_downgrades(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            pack_root = write_manifest_entry_fixture(
                base / "pack-format", "config/fixture.json"
            )
            index_bytes = (pack_root / "index.toml").read_bytes()
            (pack_root / "pack.toml").write_text(
                'name = "AFTERLIGHT"\n'
                'author = "Shane + ECHO"\n'
                'version = "test-fixture"\n'
                'pack-format = "packwiz:1.1.0"\n\n'
                '[index]\n'
                'file = "index.toml"\n'
                'hash-format = "sha1"\n'
                f'hash = "{hashlib.sha1(index_bytes).hexdigest()}"\n\n'
                '[versions]\n'
                'minecraft = "1.21.1"\n'
                'neoforge = "21.1.248"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "pack.toml index hash-format"
            ):
                hygiene.verify_manifest(pack_root)

            index_root = write_manifest_entry_fixture(
                base / "index-format", "config/fixture.json"
            )
            payload = (index_root / "config" / "fixture.json").read_bytes()
            downgraded_index = (
                'hash-format = "sha1"\n\n'
                '[[files]]\n'
                'file = "config/fixture.json"\n'
                f'hash = "{hashlib.sha1(payload).hexdigest()}"\n'
            ).encode()
            (index_root / "index.toml").write_bytes(downgraded_index)
            (index_root / "pack.toml").write_text(
                'name = "AFTERLIGHT"\n'
                'author = "Shane + ECHO"\n'
                'version = "test-fixture"\n'
                'pack-format = "packwiz:1.1.0"\n\n'
                '[index]\n'
                'file = "index.toml"\n'
                'hash-format = "sha256"\n'
                f'hash = "{sha256_bytes(downgraded_index)}"\n\n'
                '[versions]\n'
                'minecraft = "1.21.1"\n'
                'neoforge = "21.1.248"\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "index.toml hash-format"
            ):
                hygiene.verify_manifest(index_root)

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

    @requires_live_install(ROOT)
    def test_missing_cached_pack_file_is_rejected(self) -> None:
        hygiene = hygiene_module()
        provenance = json.loads(
            (ROOT / "server-test" / "packwiz.json").read_text(encoding="utf-8")
        )
        removed = provenance["cachedFiles"].pop(
            "kubejs/server_scripts/afterlight/gate_draconic.js"
        )
        self.assertIsNotNone(removed)
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            (install / "packwiz.json").write_text(
                json.dumps(provenance), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "cachedFiles payload"
            ):
                hygiene.verify_install_provenance(ROOT, install)

    def test_extra_cached_pack_file_is_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, _ = write_provenance_fixture(Path(temporary))
            provenance_path = install / "packwiz.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["cachedFiles"]["config/extra-secret.txt"] = {
                "hash": {"type": "sha256", "value": "0" * 64},
                "cachedLocation": "config/extra-secret.txt",
                "optionValue": True,
            }
            provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
            with self.assertRaisesRegex(
                hygiene.VerificationError, "cachedFiles payload"
            ):
                hygiene.verify_install_provenance(root, install)

    def test_changed_installed_pack_file_is_rejected_by_provenance(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, jar_path = write_provenance_fixture(Path(temporary))
            jar_path.write_bytes(b"changed installed content")
            with self.assertRaisesRegex(
                hygiene.VerificationError, "installed file hash mismatch"
            ):
                hygiene.verify_install_provenance(root, install)

    def test_repository_and_installed_hardlinks_are_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, install, jar_path = write_provenance_fixture(base / "repo")
            metadata_path = root / "mods" / "fixture.pw.toml"
            os.link(metadata_path, base / "metadata-hardlink.pw.toml")
            with self.assertRaisesRegex(hygiene.VerificationError, "hardlink"):
                hygiene.verify_manifest(root)

            root, install, jar_path = write_provenance_fixture(base / "install")
            os.link(jar_path, base / "artifact-hardlink.jar")
            with self.assertRaisesRegex(hygiene.VerificationError, "hardlink"):
                hygiene.verify_install_provenance(root, install)

    def test_installed_shipping_inventory_rejects_extra_and_client_files(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, install, _ = write_provenance_fixture(base / "extra")
            (install / "config").mkdir()
            (install / "config" / "unexpected.json").write_text(
                "{}", encoding="utf-8"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "physical shipping inventory"
            ):
                hygiene.verify_install_provenance(root, install)

            root, install, _ = write_provenance_fixture(
                base / "client", side="client"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "client-only artifact"
            ):
                hygiene.verify_install_provenance(root, install)

    def test_duplicate_cached_locations_are_rejected(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root, install, _ = write_provenance_fixture(Path(temporary))
            metadata = (root / "mods" / "fixture.pw.toml").read_bytes()
            duplicate_relative = "mods/duplicate.pw.toml"
            (root / duplicate_relative).write_bytes(metadata)
            index = (
                'hash-format = "sha256"\n\n'
                '[[files]]\n'
                'file = "mods/duplicate.pw.toml"\n'
                f'hash = "{sha256_bytes(metadata)}"\n'
                'metafile = true\n\n'
                '[[files]]\n'
                'file = "mods/fixture.pw.toml"\n'
                f'hash = "{sha256_bytes(metadata)}"\n'
                'metafile = true\n'
            ).encode()
            (root / "index.toml").write_bytes(index)
            pack = (
                'name = "AFTERLIGHT"\n'
                'author = "Shane + ECHO"\n'
                'version = "test-fixture"\n'
                'pack-format = "packwiz:1.1.0"\n\n'
                '[index]\n'
                'file = "index.toml"\n'
                'hash-format = "sha256"\n'
                f'hash = "{sha256_bytes(index)}"\n\n'
                '[versions]\n'
                'minecraft = "1.21.1"\n'
                'neoforge = "21.1.248"\n'
            ).encode()
            (root / "pack.toml").write_bytes(pack)
            provenance_path = install / "packwiz.json"
            provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
            provenance["packFileHash"]["value"] = sha256_bytes(pack)
            provenance["indexFileHash"]["value"] = sha256_bytes(index)
            provenance["cachedFiles"][duplicate_relative] = dict(
                provenance["cachedFiles"]["mods/fixture.pw.toml"]
            )
            provenance_path.write_text(json.dumps(provenance), encoding="utf-8")
            with self.assertRaisesRegex(
                hygiene.VerificationError, "duplicate cachedLocation"
            ):
                hygiene.verify_install_provenance(root, install)

    def test_reviewed_server_artifact_inventory_rejects_weak_hash_substitution(
        self,
    ) -> None:
        hygiene = hygiene_module()
        guard = getattr(hygiene, "verify_reviewed_server_artifact_inventory", None)
        self.assertIsNotNone(guard)
        if guard is None:
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, install, jar_path = write_provenance_fixture(
                Path(temporary), download_hash_format="sha1"
            )
            baseline = hygiene.verify_install_provenance(root, install)
            self.assertIn("afterlightServerArtifacts", baseline)
            expected = baseline["afterlightServerArtifacts"]
            original_hash_file = hygiene._hash_file
            jar_path.write_bytes(b"one-for-one substituted fixture jar")

            def weak_hash_collision(path: Path, hash_format: str) -> str:
                if path.resolve() == jar_path.resolve() and hash_format == "sha1":
                    return baseline["cachedFiles"]["mods/fixture.pw.toml"][
                        "linkedFileHash"
                    ]["value"]
                return original_hash_file(path, hash_format)

            with mock.patch.object(hygiene, "_hash_file", weak_hash_collision):
                changed = hygiene.verify_install_provenance(root, install)
            with self.assertRaisesRegex(
                hygiene.VerificationError, "server artifact inventory"
            ):
                guard(
                    changed,
                    expected_count=expected["count"],
                    expected_digest=expected["digest"],
                )

    def test_duplicate_ae2_metadata_is_removed(self) -> None:
        self.assertTrue((ROOT / "mods" / "ae2.pw.toml").is_file())
        self.assertFalse((ROOT / "mods" / "applied-energistics-2.pw.toml").exists())

    def test_installed_pack_file_and_parent_symlinks_are_rejected(self) -> None:
        hygiene = hygiene_module()
        jar_bytes = b"authenticated fixture jar"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            root, install, jar_path = write_provenance_fixture(base / "file-link")
            external_jar = base / "external.jar"
            external_jar.write_bytes(jar_bytes)
            jar_path.unlink()
            jar_path.symlink_to(external_jar)
            with self.assertRaisesRegex(hygiene.VerificationError, "symlink"):
                hygiene.verify_install_provenance(root, install)

    def test_symlink_install_root_and_existing_ancestor_are_rejected_first(self) -> None:
        hygiene = hygiene_module()
        jar_bytes = b"authenticated fixture jar"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            root, install, _ = write_provenance_fixture(base / "fixture")
            direct_link = base / "install-link"
            direct_link.symlink_to(install, target_is_directory=True)
            ancestor_link = base / "ancestor-link"
            ancestor_link.symlink_to(install.parent, target_is_directory=True)
            nested_link = ancestor_link / install.name

            for candidate in (direct_link, nested_link):
                for verifier in (
                    lambda: hygiene.verify_install_provenance(root, candidate),
                    lambda: hygiene.resolve_source_jars(
                        root, candidate, ("mods/fixture.pw.toml",)
                    ),
                    lambda: hygiene.verify_sable_source_evidence(root, candidate),
                    lambda: hygiene.verify_idas_compat_source_evidence(root, candidate),
                    lambda: hygiene.verify_jdt_evidence(root, candidate),
                    lambda: hygiene.verify_boot_run(root, candidate, "nonce", 0),
                    lambda: hygiene.verify_installed_quest_audit(
                        root, candidate, "nonce"
                    ),
                ):
                    with self.subTest(candidate=candidate, verifier=verifier), self.assertRaisesRegex(
                        hygiene.VerificationError, "symlink"
                    ):
                        verifier()

            root, install, jar_path = write_provenance_fixture(base / "parent-link")
            external_mods = base / "external-mods"
            external_mods.mkdir()
            (external_mods / "fixture.jar").write_bytes(jar_bytes)
            jar_path.unlink()
            (install / "mods").rmdir()
            (install / "mods").symlink_to(external_mods, target_is_directory=True)
            with self.assertRaisesRegex(hygiene.VerificationError, "symlink"):
                hygiene.verify_install_provenance(root, install)

    def test_shipping_policy_rejects_forbidden_and_root_leakage(self) -> None:
        hygiene = hygiene_module()
        forbidden = (
            "server-test/credentials.txt",
            "config/Server-Test/allowed.toml",
            "dist/export.zip",
            "docs/guide.txt",
            "tools/check.py",
            ".Git/config",
            ".superpowers/report.md",
            "config/private/Client-Token.json",
            "config/private/CREDENTIALS.txt",
            "mods/forbidden.JAR",
            "kubejs/data/structure.NBT",
            "README.md",
        )
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for index, relative in enumerate(forbidden):
                with self.subTest(relative=relative):
                    root = write_manifest_entry_fixture(
                        base / str(index), relative
                    )
                    with self.assertRaisesRegex(
                        hygiene.VerificationError, "shipping policy"
                    ):
                        hygiene.verify_manifest(root)

    def test_manifest_rejects_indexed_file_and_parent_symlinks(self) -> None:
        hygiene = hygiene_module()
        payload = b"external secret"
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            file_root = write_manifest_entry_fixture(
                base / "file-link", "config/payload.json", payload
            )
            external_file = base / "external-payload.json"
            external_file.write_bytes(payload)
            indexed_file = file_root / "config" / "payload.json"
            indexed_file.unlink()
            indexed_file.symlink_to(external_file)
            with self.assertRaisesRegex(hygiene.VerificationError, "symlink"):
                hygiene.verify_manifest(file_root)

            parent_root = write_manifest_entry_fixture(
                base / "parent-link", "config/linked/payload.json", payload
            )
            external_directory = base / "external-config"
            external_directory.mkdir()
            (external_directory / "payload.json").write_bytes(payload)
            linked_directory = parent_root / "config" / "linked"
            (linked_directory / "payload.json").unlink()
            linked_directory.rmdir()
            linked_directory.symlink_to(external_directory, target_is_directory=True)
            with self.assertRaisesRegex(hygiene.VerificationError, "symlink"):
                hygiene.verify_manifest(parent_root)

    def test_current_manifest_has_exact_reviewed_shipping_roots(self) -> None:
        hygiene = hygiene_module()
        manifest = hygiene.verify_manifest(ROOT)
        indexed = manifest["indexed_hashes"]
        self.assertEqual(len(indexed), 305)
        self.assertEqual(
            {relative.split("/", 1)[0] for relative in indexed},
            {"config", "global_packs", "kubejs", "mods"},
        )

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

    @requires_live_install(ROOT)
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
                    hygiene, "IDAS_COMPAT_SIZE", target.stat().st_size
                ),
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

    @requires_live_install(ROOT)
    def test_idas_compat_verifier_rejects_reviewed_allowlist_changes(self) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        mutations = (
            ("sourceSha256", "0" * 64),
            ("sourceLength", 1239),
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
                            hygiene, "IDAS_COMPAT_SIZE", target.stat().st_size
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

    @requires_live_install(ROOT)
    def test_idas_compat_verifier_rejects_source_tree_or_release_provenance_change(
        self,
    ) -> None:
        hygiene = hygiene_module()
        source = hygiene.resolve_source_jar(
            ROOT, ROOT / "server-test", hygiene.IDAS_COMPAT_METADATA
        )
        with tempfile.TemporaryDirectory() as temporary:
            for field, value in (
                ("sourceTreeSha256", "0" * 64),
                ("sourceTreeDigestSchema", 1),
                ("releaseBuild", False),
            ):
                with self.subTest(field=field):
                    with zipfile.ZipFile(source) as archive:
                        provenance = json.loads(
                            archive.read("META-INF/afterlight-provenance.json")
                        )
                    provenance[field] = value
                    payload = json.dumps(provenance, sort_keys=True).encode("utf-8")
                    target = Path(temporary) / f"changed-{field}.jar"
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
                            "IDAS_COMPAT_SIZE",
                            target.stat().st_size,
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

    @requires_live_install(ROOT)
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
                    hygiene, "IDAS_COMPAT_SIZE", target.stat().st_size
                ),
                mock.patch.object(
                    hygiene, "IDAS_COMPAT_SHA256", sha256_bytes(target.read_bytes())
                ),
                self.assertRaisesRegex(
                    hygiene.VerificationError, "forbidden payloads"
                ),
            ):
                hygiene.verify_idas_compat_source_evidence(ROOT, ROOT / "server-test")

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_authenticated_artifact_hash_change(self) -> None:
        hygiene = hygiene_module()
        original_hash_file = hygiene._hash_file

        def changed_hash(path: Path, hash_format: str) -> str:
            if path.name == "sable-neoforge-1.21.1-2.0.3.jar" and hash_format == "sha256":
                return "0" * 64
            return original_hash_file(path, hash_format)

        with mock.patch.object(hygiene, "_hash_file", side_effect=changed_hash):
            with self.assertRaisesRegex(
                hygiene.VerificationError, "server artifact inventory"
            ):
                hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")

    @requires_live_install(ROOT)
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

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_one_for_one_corpus_substitution(self) -> None:
        hygiene = hygiene_module()
        original_scan = hygiene._scan_mixin_archive
        changed = False

        def changed_scan(label, payload, result, nested_queue=None):
            nonlocal changed
            original_scan(label, payload, result, nested_queue)
            entries = result.get("mixin_corpus_entries", [])
            if not changed and entries:
                first = entries[0]
                entries[0] = (*first[:-1], "substituted")
                changed = True

        with (
            mock.patch.object(hygiene, "_scan_mixin_archive", changed_scan),
            self.assertRaisesRegex(
                hygiene.VerificationError, "mixin corpus digest"
            ),
        ):
            hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")

    @requires_live_install(ROOT)
    def test_sable_verifier_rejects_new_common_server_client_target(self) -> None:
        hygiene = hygiene_module()
        original_scan = hygiene._scan_mixin_archive
        injected = False

        def changed_scan(label, payload, result, nested_queue=None):
            nonlocal injected
            original_scan(label, payload, result, nested_queue)
            if not injected:
                result.setdefault("client_target_candidates", []).append(
                    (
                        "mods/substituted.pw.toml",
                        "substituted.mixins.json",
                        "mixins",
                        0,
                        "SubstitutedMixin",
                        "substituted/SubstitutedMixin.class",
                        "0" * 64,
                        "targets",
                        ("Lnet/minecraft/client/Minecraft;",),
                        "minecraft-client-package",
                        "Lnet/minecraft/client/Minecraft;",
                    )
                )
                injected = True

        with (
            mock.patch.object(hygiene, "_scan_mixin_archive", changed_scan),
            self.assertRaisesRegex(
                hygiene.VerificationError, "client target inventory"
            ),
        ):
            hygiene.verify_sable_source_evidence(ROOT, ROOT / "server-test")


@requires_live_install(ROOT)
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
        quest_line = next(
            line
            for line in self.debug.splitlines()
            if "[AFTERLIGHT QUEST ITEM AUDIT] OK " in line
        )
        stale_quest_line = quest_line.replace(self.nonce, "stale-nonce", 1)
        stale = self.debug.replace(quest_line, stale_quest_line, 1)
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
        expected_digest = self.hygiene.IDAS_COMPAT_REVIEWED_TEMPLATES[
            "idas:underground_camp/underground_camp1"
        ]["auditDigest"]
        changed = self.hygiene.IDAS_COMPAT_CAMP_MESSAGE.replace(
            expected_digest,
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


@requires_live_install(ROOT)
class CanonicalBootOracleNegativeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.hygiene = hygiene_module()
        self.latest = LATEST_LOG.read_text(encoding="utf-8", errors="replace")
        self.debug = DEBUG_LOG.read_text(encoding="utf-8", errors="replace")
        self.boot = BOOT_LOG.read_text(encoding="utf-8", errors="replace")
        self.nonce = (ROOT / "server-test" / "afterlight-audit-nonce.txt").read_text(
            encoding="utf-8"
        ).strip()
        self.status = int(
            (ROOT / "server-test" / "afterlight-server-exit-status.txt")
            .read_text(encoding="utf-8")
            .strip()
        )

    def copy_seal_corpus(self, source_root: Path, destination_root: Path) -> None:
        relative_paths = {
            Path(relative.split("!", 1)[0])
            for relative, _line in self.hygiene.EXPECTED_SEAL_OCCURRENCES
        }
        for relative in sorted(relative_paths):
            source = source_root / relative
            destination = destination_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

    def verify_pair(self, latest: str, debug: str, boot: str | None = None):
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            self.copy_seal_corpus(ROOT / "server-test", install)
            (install / "logs").mkdir(parents=True)
            gate_audit = install / self.hygiene.GATE_AUDIT_RELATIVE
            gate_audit.parent.mkdir(parents=True, exist_ok=True)
            gate_audit.write_bytes(
                self.hygiene.render_installed_gate_audit(ROOT, self.nonce)
            )
            (install / "logs" / "latest.log").write_text(latest, encoding="utf-8")
            (install / "logs" / "debug.log").write_text(debug, encoding="utf-8")
            (install / "boot.log").write_text(
                self.boot if boot is None else boot, encoding="utf-8"
            )
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

    def verify_bytes(self, latest: bytes, debug: bytes, boot: bytes):
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            self.copy_seal_corpus(ROOT / "server-test", install)
            (install / "logs").mkdir()
            gate_audit = install / self.hygiene.GATE_AUDIT_RELATIVE
            gate_audit.parent.mkdir(parents=True, exist_ok=True)
            gate_audit.write_bytes(
                self.hygiene.render_installed_gate_audit(ROOT, self.nonce)
            )
            (install / "logs" / "latest.log").write_bytes(latest)
            (install / "logs" / "debug.log").write_bytes(debug)
            (install / "boot.log").write_bytes(boot)
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

    def inject_after_ignored_info(self, log_text: str, added: str) -> str:
        return insert_after_line(log_text, "ModLauncher running: args", added)

    def test_current_log_pair_is_accepted(self) -> None:
        result = self.verify_pair(self.latest, self.debug)
        self.assertEqual(sum(result["errors"].values()), 14)
        self.assertEqual(sum(result["warnings"].values()), 39)

    def test_optional_lan_warning_presence_must_agree_across_logs(self) -> None:
        def remove_optional_warning(log_text: str) -> str:
            lines = log_text.splitlines(keepends=True)
            matches = tuple(
                line for line in lines if "LanServerPinger: No route to host" in line
            )
            self.assertLessEqual(len(matches), 1)
            return "".join(line for line in lines if line not in matches)

        without_latest = remove_optional_warning(self.latest)
        without_debug = remove_optional_warning(self.debug)
        optional_warning = (
            "[08Aug2026 12:00:00.000] [LanServerPinger #1/WARN] "
            "[net.minecraft.client.server.LanServerPinger/]: "
            "LanServerPinger: No route to host"
        )
        with_latest = self.inject_after_ignored_info(
            without_latest, optional_warning
        )
        with_debug = self.inject_after_ignored_info(without_debug, optional_warning)

        def validate_pair(latest: str, debug: str) -> None:
            self.hygiene._validate_canonical_log_pair(
                self.hygiene.parse_log_records(latest),
                self.hygiene.parse_log_records(debug),
                workspace_root=ROOT,
                install_root=ROOT / "server-test",
            )

        validate_pair(without_latest, without_debug)
        validate_pair(with_latest, with_debug)
        for latest, debug in (
            (with_latest, without_debug),
            (without_latest, with_debug),
        ):
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "optional environmental WARN presence differs",
            ):
                validate_pair(latest, debug)

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

    def test_relocated_severe_headers_fail_in_each_log_projection(self) -> None:
        header = (
            " [08Aug2026 12:00:00.000] [main/ERROR] "
            "[fixture.Hidden/SOURCE]: injected"
        )
        latest_changed = self.inject_after_ignored_info(self.latest, header)
        debug_changed = self.inject_after_ignored_info(self.debug, header)
        variants = (
            (latest_changed, debug_changed),
            (latest_changed, self.debug),
            (self.latest, debug_changed),
        )
        for latest, debug in variants:
            with self.subTest(
                latest_changed=latest is latest_changed,
                debug_changed=debug is debug_changed,
            ):
                self.assert_pair_rejected(latest, debug)

    def test_console_rejects_malformed_or_relocated_headers_for_every_level(self) -> None:
        parser = getattr(self.hygiene, "parse_console_records", None)
        self.assertIsNotNone(parser)
        if parser is None:
            return
        for level in ("TRACE", "DEBUG", "INFO", "WARN", "ERROR", "FATAL"):
            variants = (
                f" [12:00:00.000] [main/{level}] [fixture/Test]: relocated\n",
                f"[12:00:00.000] [main/{level} [fixture/Test]: malformed\n",
                f"\x1b[31m[12:00:00.000] [main/{level} [fixture/Test]: ansi\x1b[0m\n",
            )
            for text in variants:
                with self.subTest(level=level, text=text), self.assertRaises(
                    self.hygiene.VerificationError
                ):
                    parser(text)

    def test_strict_utf8_rejects_invalid_bytes_inside_authoritative_logs(self) -> None:
        payloads = {
            "latest": self.latest.encode("utf-8"),
            "debug": self.debug.encode("utf-8"),
            "boot": self.boot.encode("utf-8"),
        }
        for label in payloads:
            changed = dict(payloads)
            marker = b"/ERROR]"
            self.assertIn(marker, changed[label])
            changed[label] = changed[label].replace(marker, marker + b"\xff", 1)
            with self.subTest(label=label), self.assertRaisesRegex(
                self.hygiene.VerificationError, "UTF-8"
            ):
                self.verify_bytes(
                    changed["latest"], changed["debug"], changed["boot"]
                )

    def test_console_only_severe_record_is_rejected(self) -> None:
        injected = (
            "\n[12:00:00.000] [main/ERROR] "
            "[fixture.Hidden/SOURCE]: console-only exception\n"
        )
        with self.assertRaisesRegex(
            self.hygiene.VerificationError, "console severe"
        ):
            self.verify_pair(self.latest, self.debug, self.boot + injected)

    def test_compound_exception_is_rejected_when_latest_debug_or_console_only(
        self,
    ) -> None:
        latest_header = (
            "[08Aug2026 12:00:00.000] [main/INFO] [fixture.Hidden/]: "
            "java.lang.IllegalStateException: injected"
        )
        console_header = (
            "[12:00:00.000] [main/INFO] [fixture.Hidden/]: "
            "java.lang.IllegalStateException: injected"
        )
        variants = (
            (
                self.inject_after_ignored_info(self.latest, latest_header),
                self.debug,
                self.boot,
            ),
            (
                self.latest,
                self.inject_after_ignored_info(self.debug, latest_header),
                self.boot,
            ),
            (self.latest, self.debug, self.boot + "\n" + console_header + "\n"),
        )
        for latest, debug, boot in variants:
            with self.subTest(
                latest_changed=latest is not self.latest,
                debug_changed=debug is not self.debug,
                boot_changed=boot is not self.boot,
            ), self.assertRaises(self.hygiene.VerificationError):
                self.verify_pair(latest, debug, boot)

    def test_bare_severe_class_names_are_rejected_in_every_log_projection(
        self,
    ) -> None:
        for bare_name in ("Exception", "Throwable", "Error"):
            latest_header = (
                "[08Aug2026 12:00:00.000] [main/INFO] [fixture.Hidden/]: "
                f"{bare_name}: injected"
            )
            console_header = (
                "[12:00:00.000] [main/INFO] [fixture.Hidden/]: "
                f"{bare_name}: injected"
            )
            variants = (
                (
                    self.inject_after_ignored_info(self.latest, latest_header),
                    self.debug,
                    self.boot,
                ),
                (
                    self.latest,
                    self.inject_after_ignored_info(self.debug, latest_header),
                    self.boot,
                ),
                (self.latest, self.debug, self.boot + "\n" + console_header + "\n"),
            )
            for projection, (latest, debug, boot) in enumerate(variants):
                with self.subTest(
                    bare_name=bare_name, projection=projection
                ), self.assertRaises(self.hygiene.VerificationError):
                    self.verify_pair(latest, debug, boot)

    def test_warning_multiset_is_portable_across_relocated_checkout_and_install(
        self,
    ) -> None:
        old_workspace = str(ROOT)
        audit_expectation = self.hygiene.quest_audit_expectation(ROOT)
        with tempfile.TemporaryDirectory() as temporary:
            workspace = Path(temporary).resolve() / "AFTERLIGHT review"
            install = workspace / "isolated runtime"
            encoded_workspace = quote(str(workspace), safe="/:")
            encoded_install = quote(str(install), safe="/:")
            rewritten_latest = self.latest.replace(
                f"{old_workspace}/server-test", encoded_install
            ).replace(old_workspace, encoded_workspace)
            rewritten_debug = self.debug.replace(
                f"{old_workspace}/server-test", encoded_install
            ).replace(old_workspace, encoded_workspace)
            rewritten_boot = self.boot.replace(
                f"{old_workspace}/server-test", encoded_install
            ).replace(old_workspace, encoded_workspace)
            self.copy_seal_corpus(ROOT, workspace)
            self.copy_seal_corpus(ROOT / "server-test", install)
            gate_source = workspace / self.hygiene.GATE_AUDIT_RELATIVE
            gate_source.parent.mkdir(parents=True, exist_ok=True)
            gate_source.write_bytes(
                (ROOT / self.hygiene.GATE_AUDIT_RELATIVE).read_bytes()
            )
            installed_gate = install / self.hygiene.GATE_AUDIT_RELATIVE
            installed_gate.parent.mkdir(parents=True, exist_ok=True)
            installed_gate.write_bytes(
                self.hygiene.render_installed_gate_audit(workspace, self.nonce)
            )
            (install / "logs").mkdir(parents=True)
            (install / "logs" / "latest.log").write_text(
                rewritten_latest, encoding="utf-8"
            )
            (install / "logs" / "debug.log").write_text(
                rewritten_debug, encoding="utf-8"
            )
            (install / "boot.log").write_text(rewritten_boot, encoding="utf-8")
            with (
                mock.patch.object(self.hygiene, "verify_install_provenance"),
                mock.patch.object(self.hygiene, "verify_jdt_evidence"),
                mock.patch.object(self.hygiene, "verify_sable_source_evidence"),
                mock.patch.object(
                    self.hygiene, "verify_idas_compat_source_evidence"
                ),
                mock.patch.object(
                    self.hygiene,
                    "quest_audit_expectation",
                    return_value=audit_expectation,
                ),
            ):
                result = self.hygiene.verify_boot_run(
                    workspace, install, self.nonce, self.status
                )
        self.assertEqual(result["warning_records"], self.hygiene.REVIEWED_WARNING_TOTAL)

    def test_complete_warning_fingerprint_corpus_rejects_all_mutations(self) -> None:
        unknown = (
            "[08Aug2026 12:00:00.000] [main/WARN] "
            "[fixture.Hidden/SOURCE]: injected"
        )
        first_warning = next(
            line for line in self.latest.splitlines() if "/WARN]" in line
        )
        debug_first_warning = next(
            line for line in self.debug.splitlines() if "/WARN]" in line
        )
        changed_thread_latest = self.latest.replace(
            first_warning,
            re.sub(r"\[[^\]]+/WARN\]", "[Relocated-Worker/WARN]", first_warning),
            1,
        )
        changed_thread_debug = self.debug.replace(
            debug_first_warning,
            re.sub(
                r"\[[^\]]+/WARN\]",
                "[Relocated-Worker/WARN]",
                debug_first_warning,
            ),
            1,
        )
        replacement = (
            "[08Aug2026 12:00:00.000] [main/WARN] "
            "[fixture.Substitute/SOURCE]: same count substitution"
        )
        version_marker = "Failed to process update information"
        mutations = (
            (
                self.inject_after_ignored_info(self.latest, unknown),
                self.inject_after_ignored_info(self.debug, unknown),
            ),
            (self.inject_after_ignored_info(self.latest, unknown), self.debug),
            (self.latest, self.inject_after_ignored_info(self.debug, unknown)),
            (
                self.latest.replace(first_warning + "\n", "", 1),
                self.debug.replace(debug_first_warning + "\n", "", 1),
            ),
            (changed_thread_latest, changed_thread_debug),
            (
                insert_after_line(
                    self.latest, version_marker, "Caused by: fixture.ChangedWarning"
                ),
                insert_after_line(
                    self.debug, version_marker, "Caused by: fixture.ChangedWarning"
                ),
            ),
            (
                replace_first_warning(self.latest, replacement),
                replace_first_warning(self.debug, replacement),
            ),
        )
        for index, (latest, debug) in enumerate(mutations):
            with self.subTest(index=index):
                self.assert_pair_rejected(latest, debug)

    def test_warning_volatile_normalization_is_explicit_and_narrow(self) -> None:
        record = self.hygiene.LogRecord
        jar_message = (
            "Attempted to select a dependency jar for JarJar which was passed in as "
            "source: architectury. Using Mod File: "
            "/Users/example/project/server-test/mods/architectury.jar"
        )
        ci_message = jar_message.replace(
            "/Users/example/project", "/home/runner/work/afterlight"
        )
        local = record(
            "08Aug2026 12:00:00.000",
            "main",
            "WARN",
            "net.neoforged.jarjar.selection.JarSelector/",
            jar_message,
            (),
            "",
        )
        ci = record(
            "08Aug2026 12:00:01.000",
            "main",
            "WARN",
            "net.neoforged.jarjar.selection.JarSelector/",
            ci_message,
            (),
            "",
        )
        self.assertEqual(
            self.hygiene.canonical_record_fingerprint(
                local,
                workspace_root="/Users/example/project",
                install_root="/Users/example/project/server-test",
            ),
            self.hygiene.canonical_record_fingerprint(
                ci,
                workspace_root="/home/runner/work/afterlight",
                install_root="/home/runner/work/afterlight/server-test",
            ),
        )

        yungs_message = (
            "Discarding @Unique public method getEnhancedJunctionIterator in "
            "yungsapi.mixins.json:BeardifierMixin from mod yungsapi because it "
            "already exists in net.minecraft.world.level.levelgen.Beardifier"
        )
        workers = tuple(
            record(
                "08Aug2026 12:00:00.000",
                thread,
                "WARN",
                "mixin/",
                yungs_message,
                (),
                "",
            )
            for thread in ("Worker-Main-5", "Worker-Main-19")
        )
        self.assertEqual(
            self.hygiene.canonical_record_fingerprint(workers[0]),
            self.hygiene.canonical_record_fingerprint(workers[1]),
        )
        unrelated = record(
            "08Aug2026 12:00:00.000",
            "Worker-Main-19",
            "WARN",
            "mixin/",
            "unreviewed warning",
            (),
            "",
        )
        self.assertNotEqual(
            self.hygiene.canonical_record_fingerprint(workers[0]),
            self.hygiene.canonical_record_fingerprint(unrelated),
        )

        lambda_records = tuple(
            record(
                "08Aug2026 12:00:00.000",
                "Server thread",
                "WARN",
                "com.yanny.aci.manager.ManagedRegistry/",
                "Missing trade item listings for fixture.Trade$$Lambda/0x"
                f"{address}",
                (),
                "",
            )
            for address in ("00000070074cc500", "000000e8074e3538")
        )
        self.assertEqual(
            self.hygiene.canonical_record_fingerprint(lambda_records[0]),
            self.hygiene.canonical_record_fingerprint(lambda_records[1]),
        )

        modernfix_records = tuple(
            record(
                "08Aug2026 12:00:00.000",
                "main",
                "WARN",
                "ModernFix/",
                f"Initial datapack load took {seconds} s",
                (),
                "",
            )
            for seconds in ("6.126", "6.975")
        )
        self.assertEqual(
            self.hygiene.canonical_record_fingerprint(modernfix_records[0]),
            self.hygiene.canonical_record_fingerprint(modernfix_records[1]),
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

    def test_modernfix_dedicated_timing_normalization_is_explicit(self) -> None:
        records = tuple(
            self.hygiene.LogRecord(
                "08Aug2026 12:00:00.000",
                "Server thread",
                "WARN",
                "ModernFix/",
                f"Dedicated server took {seconds} seconds to load",
                (),
                "",
            )
            for seconds in ("64.226", "68.709")
        )
        self.assertEqual(
            self.hygiene.canonical_record_fingerprint(records[0]),
            self.hygiene.canonical_record_fingerprint(records[1]),
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
                "be3d18091a1e0cc0e81f2ace182b104da15e70170c7bd4e7a4354156ba13f7b2",
                237,
            ),
        )

    def test_quest_digest_and_items_are_recomputed_from_source(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "config", root / "config")
            shutil.copytree(ROOT / "mods", root / "mods")
            shutil.copytree(
                ROOT / "kubejs" / "startup_scripts",
                root / "kubejs" / "startup_scripts",
            )
            script_dir = root / "kubejs" / "server_scripts" / "afterlight"
            script_dir.mkdir(parents=True)
            source = (
                ROOT
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "generated_quest_item_audit.js"
            ).read_text(encoding="utf-8")
            script_path = script_dir / "generated_quest_item_audit.js"
            digest = re.search(
                r"AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST = '([0-9a-f]{64})'", source
            ).group(1)
            for label, changed in (
                ("digest", source.replace(digest, "f" * 64, 1)),
                (
                    "items",
                    source.replace(
                        '  "ae2:1k_crafting_storage",\n', "", 1
                    ),
                ),
                (
                    "same_count_substitution",
                    source.replace(
                        '  "ae2:1k_crafting_storage",\n',
                        '  "minecraft:stone",\n',
                        1,
                    ),
                ),
            ):
                with self.subTest(label=label):
                    script_path.write_text(changed, encoding="utf-8")
                    with self.assertRaisesRegex(
                        hygiene.VerificationError, "deterministic builder output"
                    ):
                        hygiene.quest_audit_expectation(root)

    def test_complete_generated_quest_audit_script_matches_builder_bytes(self) -> None:
        hygiene = hygiene_module()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "config", root / "config")
            shutil.copytree(ROOT / "mods", root / "mods")
            shutil.copytree(
                ROOT / "kubejs" / "startup_scripts",
                root / "kubejs" / "startup_scripts",
            )
            script_dir = root / "kubejs" / "server_scripts" / "afterlight"
            script_dir.mkdir(parents=True)
            source = (
                ROOT
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "generated_quest_item_audit.js"
            ).read_text(encoding="utf-8")
            changed = source.replace("!Item.exists(id)", "false", 1)
            self.assertNotEqual(source, changed)
            (script_dir / "generated_quest_item_audit.js").write_text(
                changed, encoding="utf-8"
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "builder output"
            ):
                hygiene.quest_audit_expectation(root)

    def test_installed_quest_audit_rejects_post_nonce_bypass(self) -> None:
        hygiene = hygiene_module()
        verifier = getattr(hygiene, "verify_installed_quest_audit", None)
        self.assertIsNotNone(verifier)
        if verifier is None:
            return
        nonce = "fixture-nonce"
        relative = Path(
            "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
        )
        expected = (ROOT / relative).read_text(encoding="utf-8").replace(
            "__AFTERLIGHT_BOOT_NONCE__", nonce
        )
        with tempfile.TemporaryDirectory() as temporary:
            install = Path(temporary)
            target = install / relative
            target.parent.mkdir(parents=True)
            target.write_text(
                expected.replace("!Item.exists(id)", "false", 1),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                hygiene.VerificationError, "installed quest audit"
            ):
                verifier(ROOT, install, nonce)

    def test_zero_and_mutated_quest_digests_are_rejected(self) -> None:
        digest, _ = self.hygiene.quest_audit_expectation(ROOT)
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
            "[AFTERLIGHT GATE RECIPE AUDIT] OK ",
            "FTB Quests/]: Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
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
                "FTB Quests/]: Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
            ),
            ("MinecraftServer/]: Saving players", "MinecraftServer/]: Saving worlds"),
        )
        for first, second in pairs:
            with self.subTest(first=first, second=second):
                self.assert_pair_rejected(
                    swap_lines(self.latest, first, second),
                    swap_lines(self.debug, first, second),
                )


class GateRecipeAuditNegativeTests(unittest.TestCase):
    RELATIVE = Path("kubejs/server_scripts/afterlight/gate_recipe_audit.js")

    def setUp(self) -> None:
        self.hygiene = hygiene_module()

    def require_gate_api(self) -> bool:
        functions = (
            "gate_audit_expectation",
            "render_installed_gate_audit",
            "verify_installed_gate_audit",
        )
        available = all(callable(getattr(self.hygiene, name, None)) for name in functions)
        self.assertTrue(available, "Gate audit authentication interfaces are missing")
        return available

    def copy_gate_source(self, base: Path) -> tuple[Path, Path]:
        root = base / "pack"
        install = base / "install"
        source = root / self.RELATIVE
        source.parent.mkdir(parents=True)
        source.write_bytes((ROOT / self.RELATIVE).read_bytes())
        (install / self.RELATIVE).parent.mkdir(parents=True)
        return root, install

    def write_installed(self, root: Path, install: Path, nonce: str) -> Path:
        target = install / self.RELATIVE
        target.write_bytes(self.hygiene.render_installed_gate_audit(root, nonce))
        return target

    def assert_marker_rejected(self, latest: str, debug: str, nonce: str) -> None:
        rejected = 0
        for log_text in (latest, debug):
            try:
                self.hygiene.validate_boot_markers(log_text, nonce, 0, ROOT)
            except self.hygiene.VerificationError:
                rejected += 1
        self.assertGreater(rejected, 0)

    def test_source_contract_and_rendered_bytes_are_authenticated(self) -> None:
        if not self.require_gate_api():
            return
        digest, count = self.hygiene.gate_audit_expectation(ROOT)
        self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertEqual(count, 11)
        source = (ROOT / self.RELATIVE).read_bytes()
        self.assertEqual(digest, hashlib.sha256(source).hexdigest())
        rendered = self.hygiene.render_installed_gate_audit(ROOT, "fresh-nonce")
        self.assertNotIn(b"__AFTERLIGHT_GATE_AUDIT_SHA256__", rendered)
        self.assertNotIn(b"__AFTERLIGHT_GATE_BOOT_NONCE__", rendered)
        self.assertEqual(rendered.count(digest.encode()), 1)
        self.assertEqual(rendered.count(b"fresh-nonce"), 1)

    def test_missing_and_repeated_placeholders_are_rejected(self) -> None:
        if not self.require_gate_api():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, _install = self.copy_gate_source(Path(temporary))
            source_path = root / self.RELATIVE
            original = source_path.read_text(encoding="utf-8")
            for placeholder in (
                "__AFTERLIGHT_GATE_AUDIT_SHA256__",
                "__AFTERLIGHT_GATE_BOOT_NONCE__",
            ):
                for label, changed in (
                    ("missing", original.replace(placeholder, "", 1)),
                    ("repeated", original + f"\n// {placeholder}\n"),
                ):
                    with self.subTest(placeholder=placeholder, mutation=label):
                        source_path.write_text(changed, encoding="utf-8")
                        with self.assertRaisesRegex(
                            self.hygiene.VerificationError, "placeholder"
                        ):
                            self.hygiene.render_installed_gate_audit(root, "fresh")
                source_path.write_text(original, encoding="utf-8")

    def test_source_mutation_after_render_is_rejected(self) -> None:
        if not self.require_gate_api():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, install = self.copy_gate_source(Path(temporary))
            self.write_installed(root, install, "fresh")
            source_path = root / self.RELATIVE
            source_path.write_bytes(source_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                self.hygiene.VerificationError, "installed Gate audit"
            ):
                self.hygiene.verify_installed_gate_audit(root, install, "fresh")

    def test_installed_mutation_before_and_after_substitution_is_rejected(self) -> None:
        if not self.require_gate_api():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, install = self.copy_gate_source(Path(temporary))
            source = (root / self.RELATIVE).read_bytes()
            digest = hashlib.sha256(source).hexdigest().encode()
            nonce = b"fresh"
            pre_substitution = source.replace(b"Item.exists", b"Item.missing", 1)
            pre_substitution = pre_substitution.replace(
                b"__AFTERLIGHT_GATE_AUDIT_SHA256__", digest, 1
            ).replace(b"__AFTERLIGHT_GATE_BOOT_NONCE__", nonce, 1)
            target = install / self.RELATIVE
            target.write_bytes(pre_substitution)
            with self.assertRaisesRegex(
                self.hygiene.VerificationError, "installed Gate audit"
            ):
                self.hygiene.verify_installed_gate_audit(root, install, "fresh")

            target.write_bytes(
                self.hygiene.render_installed_gate_audit(root, "fresh")
                + b"\n"
            )
            with self.assertRaisesRegex(
                self.hygiene.VerificationError, "installed Gate audit"
            ):
                self.hygiene.verify_installed_gate_audit(root, install, "fresh")

    def test_install_rejects_mutated_raw_bytes_without_overwrite(self) -> None:
        if not self.require_gate_api():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, install = self.copy_gate_source(Path(temporary))
            source = (root / self.RELATIVE).read_bytes()
            mutated = source.replace(b"Item.exists", b"Item.missing", 1)
            self.assertNotEqual(mutated, source)
            target = install / self.RELATIVE
            target.write_bytes(mutated)

            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "installed Gate audit pre-substitution bytes differ from root source",
            ):
                self.hygiene._install_rendered_gate_audit(root, install, "fresh")

            self.assertEqual(target.read_bytes(), mutated)

    def test_stale_installed_digest_and_nonce_are_rejected(self) -> None:
        if not self.require_gate_api():
            return
        with tempfile.TemporaryDirectory() as temporary:
            root, install = self.copy_gate_source(Path(temporary))
            target = self.write_installed(root, install, "fresh")
            rendered = target.read_bytes()
            digest, _count = self.hygiene.gate_audit_expectation(root)
            for label, changed in (
                ("digest", rendered.replace(digest.encode(), b"0" * 64, 1)),
                ("nonce", rendered.replace(b"fresh", b"stale", 1)),
            ):
                with self.subTest(label=label):
                    target.write_bytes(changed)
                    with self.assertRaisesRegex(
                        self.hygiene.VerificationError, "installed Gate audit"
                    ):
                        self.hygiene.verify_installed_gate_audit(
                            root, install, "fresh"
                        )

    def test_valid_markers_allow_gate_and_quest_in_either_order(self) -> None:
        if not self.require_gate_api():
            return
        for gate_first in (True, False):
            with self.subTest(gate_first=gate_first):
                try:
                    projection = self.hygiene.validate_boot_markers(
                        valid_gate_boot_log("fresh", gate_first=gate_first),
                        "fresh",
                        0,
                        ROOT,
                    )
                except self.hygiene.VerificationError as error:
                    self.fail(str(error))
                labels = tuple(label for label, _record in projection)
                self.assertIn("Gate audit", labels)
                self.assertIn("quest audit", labels)

    def test_stale_digest_and_nonce_markers_are_rejected(self) -> None:
        if not self.require_gate_api():
            return
        valid = valid_gate_boot_log("fresh")
        digest, _count = self.hygiene.gate_audit_expectation(ROOT)
        for label, changed in (
            ("digest", valid.replace(digest, "0" * 64, 1)),
            ("nonce", valid.replace("fresh", "stale", 1)),
        ):
            with self.subTest(label=label):
                self.assert_marker_rejected(changed, changed, "fresh")

    def test_duplicate_and_one_log_only_markers_are_rejected(self) -> None:
        if not self.require_gate_api():
            return
        marker = "[AFTERLIGHT GATE RECIPE AUDIT] OK "
        valid = valid_gate_boot_log("fresh")
        duplicate = duplicate_line(valid, marker)
        missing = remove_line(valid, marker)
        self.assert_marker_rejected(duplicate, duplicate, "fresh")
        self.assert_marker_rejected(valid, missing, "fresh")
        self.assert_marker_rejected(missing, valid, "fresh")

    def test_gate_marker_rejects_every_outside_window_position(self) -> None:
        if not self.require_gate_api():
            return
        marker = "[AFTERLIGHT GATE RECIPE AUDIT] OK "
        done = "DedicatedServer/]: Done ("
        ftb = "FTB Quests/]: Loaded 6 chapter groups"
        valid = valid_gate_boot_log("fresh")
        lines = valid.splitlines()
        marker_index = next(index for index, line in enumerate(lines) if marker in line)
        marker_line = lines.pop(marker_index)
        done_index = next(index for index, line in enumerate(lines) if done in line)
        before_done = lines.copy()
        before_done.insert(done_index, marker_line)
        ftb_index = next(index for index, line in enumerate(lines) if ftb in line)
        after_ftb = lines.copy()
        after_ftb.insert(ftb_index + 1, marker_line)
        for label, changed_lines in (
            ("before Done", before_done),
            ("after FTB", after_ftb),
        ):
            with self.subTest(position=label):
                changed = "\n".join(changed_lines) + "\n"
                self.assert_marker_rejected(changed, changed, "fresh")


class GateRecipeAdversarialTests(unittest.TestCase):
    RELATIVE = Path("kubejs/server_scripts/afterlight/gate_recipe_audit.js")
    EXPECTED_HELPERS = (
        "afterlightRecipe",
        "afterlightMechanicalInput",
        "afterlightCraftingInput",
        "afterlightAssertMatch",
        "afterlightAssertNoMatch",
        "afterlightAssertOnlySealRemainder",
    )
    EXECUTABLE_CONTRACTS = {
        "deletion": (
            "let deletedPattern = spec.pattern.slice()",
            "afterlightAssertNoMatch( recipe, afterlightMechanicalInput(deletedPattern, spec.keys),",
        ),
        "replacement": (
            "let replacedPattern = spec.pattern.slice()",
            "replacementKeys.X = 'minecraft:barrier'",
            "afterlightAssertNoMatch( recipe, afterlightMechanicalInput(replacedPattern, replacementKeys),",
        ),
        "schematic": (
            "wrongSchematics.filter(candidate => candidate !== spec.keys.S).forEach(candidate => {",
            "changedKeys.S = candidate",
            "afterlightMechanicalInput(spec.pattern, changedKeys), `${spec.id} wrong schematic ${candidate}`",
        ),
        "gate-specials": (
            "if (spec.wrongSpecialItems) {",
            "Object.keys(spec.wrongSpecialItems).forEach(key => {",
            "changedKeys[key] = spec.wrongSpecialItems[key]",
            "key === 'B' ? 'wrong blueprint' : 'wrong unique component'",
        ),
        "transforms": (
            "for (let turn = 1; turn <= 3; turn++) {",
            "rotatedRow += rotatedPattern[row][column]",
            "afterlightMechanicalInput(rotatedPattern, spec.keys), `${spec.id} rotated ${turn * 90} degrees`",
        ),
        "producer-cardinality": (
            "server.getRecipeManager().getRecipes().forEach(holder => {",
            "if (producerIds[output].length !== expectedProducerCount[output]) {",
            "producerIds[AFTERLIGHT.STABILIZER].join('|') !== approvedStabilizers.join('|')",
        ),
        "seal-slot": (
            "for (let wrongSlot = 0; wrongSlot < 9; wrongSlot++) {",
            "if (wrongSlot === 7) continue",
            "afterlightCraftingInput(wrongSlotPattern, spec.keys), `${spec.id} wrong Seal slot ${wrongSlot}`",
        ),
        "stack-size": (
            "if (Item.of(draconicRecipes[0].keys.Z).getMaxStackSize() !== 1) {",
            "throw new Error('Seal maximum stack size changed')",
        ),
        "count-two": (
            "afterlightAssertMatch( recipe, countTwoInput, `${spec.id} unsupported count-two KeepAction characterization`",
            "if (mergedCount !== 3) throw new Error(`${spec.id} unsupported count-two KeepAction merge changed to ${mergedCount}`)",
        ),
    }
    EXPECTED_SEAL_OCCURRENCES = Counter(
        (
            (
                "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
                "snbt:$.icon.id=kubejs:ascendancy_seal",
            ),
            (
                "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
                "snbt:$.quests[].rewards[].item.id=kubejs:ascendancy_seal",
            ),
            (
                "config/ftbquests/quests/chapters/BFF4AF7B0C73F058.snbt",
                "snbt:$.quests[].tasks[].item.id=kubejs:ascendancy_seal",
            ),
            (
                "kubejs/assets/kubejs/lang/en_us.json",
                '"item.kubejs.ascendancy_seal": "Ascendancy Seal",',
            ),
            (
                "kubejs/server_scripts/afterlight/_constants.js",
                "SEAL: 'kubejs:ascendancy_seal',",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_draconic.js",
                "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "C: 'minecraft:diamond', Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "C: 'minecraft:ender_eye', Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "I: 'minecraft:iron_ingot', R: 'minecraft:redstone', Z: AFTERLIGHT.SEAL",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "countTwoKeys.Z = Item.of(AFTERLIGHT.SEAL, 2)",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 2) {",
            ),
            (
                "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
                "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 1) {",
            ),
            (
                "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
                '"kubejs:ascendancy_seal",',
            ),
            (
                "kubejs/startup_scripts/afterlight/registry.js",
                "event.create('ascendancy_seal')",
            ),
        )
    )
    UNAUTHORIZED_SEAL_SOURCES = (
        (
            "recipe",
            Path("kubejs/server_scripts/afterlight/unauthorized_recipe.js"),
            "ServerEvents.recipes(event => {\n"
            "  event.shapeless('kubejs:ascendancy_seal', ['minecraft:dirt'])\n"
            "})\n",
        ),
        (
            "loot",
            Path("global_packs/required_data/afterlight/data/afterlight/loot_table/unauthorized.json"),
            '{"pools":[{"entries":[{"type":"minecraft:item","name":"kubejs:ascendancy_seal"}]}]}\n',
        ),
        (
            "trade",
            Path("kubejs/server_scripts/afterlight/unauthorized_trade.js"),
            "MoreJSEvents.villagerTrades(event => {\n"
            "  event.addTrade('minecraft:librarian', 1, 'minecraft:dirt', 'kubejs:ascendancy_seal')\n"
            "})\n",
        ),
        (
            "grant",
            Path("kubejs/server_scripts/afterlight/unauthorized_grant.js"),
            "PlayerEvents.loggedIn(event => {\n"
            "  event.player.give('kubejs:ascendancy_seal')\n"
            "})\n",
        ),
        (
            "quest-reward",
            Path("config/ftbquests/quests/chapters/0000000000000000.snbt"),
            '{ id: "0000000000000000" rewards: [{ type: "item" item: { id: "kubejs:ascendancy_seal" } }] }\n',
        ),
        (
            "generated-data",
            Path("kubejs/data/afterlight/recipe/unauthorized.json"),
            '{"type":"minecraft:crafting_shapeless","result":{"id":"kubejs:ascendancy_seal"}}\n',
        ),
    )

    def setUp(self) -> None:
        self.hygiene = hygiene_module()
        self.source = (ROOT / self.RELATIVE).read_text(encoding="utf-8")

    def copy_seal_corpus(self, base: Path) -> tuple[Path, Path]:
        root = base / "pack"
        install = base / "install"
        for root_name in ("config", "global_packs", "kubejs"):
            shutil.copytree(ROOT / root_name, root / root_name)
            shutil.copytree(ROOT / root_name, install / root_name)
        return root, install

    def executable_source(self, source: str) -> str:
        without_blocks = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
        without_comments = re.sub(r"(?m)^\s*//.*$", "", without_blocks)
        return re.sub(r"\s+", " ", without_comments).strip()

    def assert_executable_contract(self, source: str) -> None:
        executable = self.executable_source(source)
        self.assertNotIn("if (false)", executable)
        self.assertNotIn("if (0)", executable)
        invalid = []
        for category, snippets in self.EXECUTABLE_CONTRACTS.items():
            for snippet in snippets:
                count = executable.count(snippet)
                if count != 1:
                    invalid.append((category, snippet, count))
        self.assertEqual(
            invalid,
            [],
            "missing or duplicated executable adversarial contracts",
        )

    def test_adversarial_assertions_extend_the_same_listener_and_marker(self) -> None:
        self.assertEqual(self.source.count("ServerEvents.loaded("), 1)
        self.assertEqual(self.source.count("[AFTERLIGHT GATE RECIPE AUDIT] OK"), 1)
        self.assertEqual(
            tuple(re.findall(r"\bfunction\s+(\w+)\(", self.source)),
            self.EXPECTED_HELPERS,
        )
        self.assert_executable_contract(self.source)
        executable = self.executable_source(self.source)
        marker = executable.index("[AFTERLIGHT GATE RECIPE AUDIT] OK")
        for snippets in self.EXECUTABLE_CONTRACTS.values():
            for snippet in snippets:
                self.assertLess(executable.index(snippet), marker)

    def test_each_adversarial_executable_contract_detects_removal_or_noop(self) -> None:
        executable = self.executable_source(self.source)
        self.assert_executable_contract(executable)
        for category, snippets in self.EXECUTABLE_CONTRACTS.items():
            for target in snippets:
                self.assertEqual(executable.count(target), 1, category)
                for mutation, replacement in (
                    ("removed", ""),
                    ("no-op", "void 0"),
                ):
                    with self.subTest(
                        category=category,
                        target=target,
                        mutation=mutation,
                    ):
                        changed = executable.replace(target, replacement, 1)
                        with self.assertRaises(AssertionError):
                            self.assert_executable_contract(changed)

    def test_repository_and_installed_seal_source_scans_fail_closed(self) -> None:
        verifier = getattr(self.hygiene, "verify_seal_sources", None)
        self.assertTrue(callable(verifier), "Seal source verifier is missing")
        with tempfile.TemporaryDirectory() as temporary:
            root, install = self.copy_seal_corpus(Path(temporary))
            result = verifier(root, install)
            expected = self.EXPECTED_SEAL_OCCURRENCES
            self.assertEqual(Counter(result["root"]), expected)
            self.assertEqual(Counter(result["install"]), expected)

            act_four = install / "config/ftbquests/quests/chapters/245BADE04399406C.snbt"
            act_four_text = act_four.read_text(encoding="utf-8")
            misplaced = act_four_text.replace(
                'icon: { id: "kubejs:ascendancy_seal" }',
                'seal_probe: { id: "kubejs:ascendancy_seal" }',
                1,
            )
            self.assertNotEqual(misplaced, act_four_text)
            act_four.write_text(misplaced, encoding="utf-8")
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "Seal source corpus",
            ):
                verifier(root, install)
            act_four.write_text(act_four_text, encoding="utf-8")

            reward_header = (
                '\t\t\trewards: [\n'
                '\t\t\t\t{\n'
                '\t\t\t\t\tid: "DF14A45FDAFFC3A0"'
            )
            misplaced_reward = act_four_text.replace(
                reward_header,
                reward_header.replace("rewards", "seal_probe"),
                1,
            )
            self.assertNotEqual(misplaced_reward, act_four_text)
            act_four.write_text(misplaced_reward, encoding="utf-8")
            with self.assertRaisesRegex(
                self.hygiene.VerificationError,
                "Seal source corpus",
            ):
                verifier(root, install)
            act_four.write_text(act_four_text, encoding="utf-8")

            normalized = act_four_text.replace(
                'icon: { id: "kubejs:ascendancy_seal" }',
                'icon: {\n\t\tid: "kubejs:ascendancy_seal"\n\t}',
                1,
            ).replace(
                'item: { count: 1, id: "kubejs:ascendancy_seal" }',
                'item: {\n\t\t\t\t\tcount: 1\n\t\t\t\t\tid: "kubejs:ascendancy_seal"\n\t\t\t\t}',
                1,
            )
            self.assertNotEqual(normalized, act_four_text)
            act_four.write_text(normalized, encoding="utf-8")
            postgame = install / "config/ftbquests/quests/chapters/BFF4AF7B0C73F058.snbt"
            postgame_text = postgame.read_text(encoding="utf-8")
            normalized_postgame = postgame_text.replace(
                'item: { count: 1, id: "kubejs:ascendancy_seal" }',
                'item: {\n\t\t\t\tcount: 1\n\t\t\t\tid: "kubejs:ascendancy_seal"\n\t\t\t}',
                1,
            )
            self.assertNotEqual(normalized_postgame, postgame_text)
            postgame.write_text(normalized_postgame, encoding="utf-8")
            normalized_result = verifier(root, install)
            self.assertEqual(Counter(normalized_result["root"]), expected)
            self.assertEqual(Counter(normalized_result["install"]), expected)

            for source_class, relative, payload in self.UNAUTHORIZED_SEAL_SOURCES:
                for location, corpus_root in (("root", root), ("install", install)):
                    with self.subTest(source_class=source_class, location=location):
                        unauthorized = corpus_root / relative
                        unauthorized.parent.mkdir(parents=True, exist_ok=True)
                        unauthorized.write_text(payload, encoding="utf-8")
                        with self.assertRaisesRegex(
                            self.hygiene.VerificationError,
                            "Seal source corpus",
                        ):
                            verifier(root, install)
                        unauthorized.unlink()

    def test_boot_oracle_binds_exact_finale_totals_and_seal_scan(self) -> None:
        current = valid_gate_boot_log("fresh").replace(
            "Loaded 6 chapter groups, 45 chapters, 307 quests, 6 reward tables",
            "Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
        )
        try:
            projection = self.hygiene.validate_boot_markers(current, "fresh", 0, ROOT)
        except self.hygiene.VerificationError as error:
            self.fail(str(error))
        self.assertIn("FTB Quests load", {label for label, _record in projection})
        stale = current.replace(
            "Loaded 6 chapter groups, 46 chapters, 313 quests, 6 reward tables",
            "Loaded 6 chapter groups, 45 chapters, 307 quests, 6 reward tables",
        )
        with self.assertRaisesRegex(
            self.hygiene.VerificationError,
            "FTB Quests load",
        ):
            self.hygiene.validate_boot_markers(stale, "fresh", 0, ROOT)
        rc_source = (ROOT / "tools" / "rc_hygiene.py").read_text(encoding="utf-8")
        server_source = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn("verify_seal_sources(root_path, install_path)", rc_source)
        self.assertIn("verify-seal-sources --root . --install \"$DIR\"", server_source)


class FilterAndHarnessNegativeTests(unittest.TestCase):
    def test_live_runtime_gate_skips_precisely_or_fails_when_required(self) -> None:
        support = importlib.import_module("live_install_support")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            decision = support.live_install_decision(root, require=False)
            self.assertFalse(decision.ready)
            self.assertIn("fresh authenticated server-test install", decision.reason)
            with self.assertRaisesRegex(
                RuntimeError, "AFTERLIGHT_REQUIRE_LIVE_TESTS=1"
            ):
                support.live_install_decision(root, require=True)

    def test_quest_audit_cli_reports_only_quest_result(self) -> None:
        hygiene = hygiene_module()
        arguments = hygiene.argparse.Namespace(
            root=".", install="server-test", nonce="fixture"
        )
        output = io.StringIO()
        with (
            mock.patch.object(
                hygiene, "verify_installed_quest_audit", return_value="a" * 64
            ),
            mock.patch("sys.stdout", output),
        ):
            hygiene._cli_verify_quest_audit(arguments)
        self.assertEqual(
            output.getvalue(), f"QUEST AUDIT BYTES: OK sha256={'a' * 64}\n"
        )

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
            "releases/download/v${PACKWIZ_BOOTSTRAP_VERSION}/"
            "packwiz-installer-bootstrap.jar",
            script,
        )
        versions = (ROOT / "tools" / "versions.env").read_text(encoding="utf-8")
        self.assertIn(
            "PACKWIZ_BOOTSTRAP_SHA256=${PACKWIZ_BOOTSTRAP_SHA256:-"
            "a8fbb24dc604278e97f4688e82d3d91a318b98efc08d5dbfcbcbcab6443d116c}",
            versions,
        )
        self.assertIn("packwiz serve --refresh=false", script)
        self.assertIn("python3 tools/rc_hygiene.py verify-manifest", script)
        self.assertIn("afterlight-server-exit-status.txt", script)
        self.assertRegex(script, re.compile(r"SERVER_STATUS=\$\?"))
        self.assertIn("ACTUAL_BOOTSTRAP_SHA256", script)
        self.assertNotIn("releases/latest", script)
        self.assertIn("--bootstrap-no-update", script)
        self.assertIn("--bootstrap-main-jar", script)
        self.assertIn("packwiz-installer.jar", script)
        self.assertIn("assert_manifest_unchanged", script)
        self.assertGreaterEqual(script.count("assert_manifest_unchanged"), 5)
        self.assertNotIn("packwiz refresh", script)
        self.assertNotIn("|| true", script)
        self.assertIn("AFTERLIGHT_REQUIRE_LIVE_TESTS=1", script)
        self.assertIn("AFTERLIGHT_LIVE_RUN_ID", script)
        self.assertIn("afterlight-live-tests-ready.txt", script)
        self.assertIn("os.setsid()", script)
        self.assertIn(
            'os.execv(sys.argv[2], [sys.argv[2], sys.argv[3], "./run.sh", "nogui"])',
            script,
        )

    def test_server_harness_requires_a_working_java_21_runtime(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn(
            'if JAVA_CANDIDATE=$(command -v java 2>/dev/null); then', script
        )
        self.assertIn('JAVA="$JAVA_CANDIDATE"', script)
        self.assertIn("need a working Java 21 runtime", script)

    def test_server_harness_rejects_unowned_port_and_dead_serve_process(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn('socket.bind(("127.0.0.1", port))', script)
        self.assertIn('kill -0 "$SERVE_PID"', script)
        self.assertIn("packwiz serve exited before readiness", script)

    def test_neoforge_installer_is_authenticated_before_cache_publish(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        temp_checksum_line = 'shasum -a 256 "$NEOFORGE_INSTALLER_TMP"'
        cache_publish_line = 'mv "$NEOFORGE_INSTALLER_TMP"'
        self.assertIn(temp_checksum_line, script)
        self.assertIn(cache_publish_line, script)
        temp_checksum = script.index(temp_checksum_line)
        cache_publish = script.index(cache_publish_line)
        self.assertLess(temp_checksum, cache_publish)

    def test_ci_failure_evidence_is_run_unique_and_complete(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn('EVIDENCE_DIR="$DIR/evidence/$RUN_ID"', script)
        self.assertIn("afterlight-run-marker.txt", script)
        for relative in (
            "installer.log",
            "packwiz-install.log",
            "boot.log",
            "logs/latest.log",
            "logs/debug.log",
            "afterlight-audit-nonce.txt",
            "afterlight-server-exit-status.txt",
            "packwiz.json",
        ):
            with self.subTest(relative=relative):
                self.assertIn(relative, script)
        workflow = (ROOT / ".github" / "workflows" / "pack-ci.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("server-test/evidence/", workflow)
        self.assertNotIn("server-test/boot.log\n", workflow)

    def test_ci_and_neoforge_installer_executables_are_immutable(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "pack-ci.yml").read_text(
            encoding="utf-8"
        )
        uses = re.findall(
            r"^\s*- uses: ([^\s]+)(?:\s+#.*)?$", workflow, flags=re.MULTILINE
        )
        expected_actions = {
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-java@b6effb05e454b25005698d916606bdc6ffcbf961",
            "actions/setup-go@b7ad1dad31e06c5925ef5d2fc7ad053ef454303e",
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        }
        self.assertEqual(set(uses), expected_actions)
        for action in uses:
            with self.subTest(action=action):
                self.assertRegex(action, r"^[^@]+@[0-9a-f]{40}$")
        self.assertNotIn("go-version: stable", workflow)
        self.assertIn('go-version: "1.26.5"', workflow)

        versions = (ROOT / "tools" / "versions.env").read_text(encoding="utf-8")
        self.assertRegex(
            versions,
            r"NEOFORGE_INSTALLER_SHA256=\$\{NEOFORGE_INSTALLER_SHA256:-[0-9a-f]{64}\}",
        )
        self.assertIn(
            "PACKWIZ_INSTALLER_VERSION=${PACKWIZ_INSTALLER_VERSION:-0.5.14}",
            versions,
        )
        self.assertIn(
            "PACKWIZ_INSTALLER_SHA256=${PACKWIZ_INSTALLER_SHA256:-"
            "c9f646908d340d84773948a9a7d98bc1dae250d35e1016dc6e2b8459760b5598}",
            versions,
        )
        self.assertIn(
            "PACKWIZ_INSTALLER_SIZE=${PACKWIZ_INSTALLER_SIZE:-4378828}",
            versions,
        )
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn("NEOFORGE_INSTALLER_CACHE", script)
        self.assertIn("ACTUAL_NEOFORGE_SHA256", script)
        checksum_index = script.index("ACTUAL_NEOFORGE_SHA256")
        execute_index = script.index("-jar neoforge-installer.jar")
        self.assertLess(checksum_index, execute_index)
        self.assertIn("NEOFORGE_INSTALLER_SHA256 mismatch", script)

    def test_packwiz_main_installer_is_authenticated_before_cache_publish(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn(
            "releases/download/v${PACKWIZ_INSTALLER_VERSION}/packwiz-installer.jar",
            script,
        )
        self.assertIn('wc -c < "$PACKWIZ_INSTALLER_TMP"', script)
        self.assertIn('shasum -a 256 "$PACKWIZ_INSTALLER_TMP"', script)
        self.assertIn('mv "$PACKWIZ_INSTALLER_TMP" "$PACKWIZ_INSTALLER_CACHE"', script)
        self.assertLess(
            script.index('wc -c < "$PACKWIZ_INSTALLER_TMP"'),
            script.index('mv "$PACKWIZ_INSTALLER_TMP" "$PACKWIZ_INSTALLER_CACHE"'),
        )
        self.assertLess(
            script.index('shasum -a 256 "$PACKWIZ_INSTALLER_TMP"'),
            script.index('mv "$PACKWIZ_INSTALLER_TMP" "$PACKWIZ_INSTALLER_CACHE"'),
        )
        self.assertNotIn("api.github.com/repos/comp500/packwiz-installer/releases/latest", script)

    def test_server_harness_tracks_and_terminates_the_server_process_group(self) -> None:
        script = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn('SERVER_PID=""', script)
        self.assertIn('kill -TERM -- "-$SERVER_PID"', script)
        self.assertIn('wait "$SERVER_PID"', script)
        self.assertIn("os.setsid()", script)


class ServerHarnessIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name) / "repo"
        self.fake_bin = self.root / "fake-bin"
        self.java_home = self.root / "fake-jdk"
        (self.root / "tools").mkdir(parents=True)
        self.fake_bin.mkdir()
        (self.java_home / "bin").mkdir(parents=True)
        shutil.copy2(ROOT / "tools" / "server-test.sh", self.root / "tools")
        (self.root / "tools" / "versions.env").write_text(
            "MC_VERSION=1.21.1\n"
            "NEOFORGE_VERSION=21.1.248\n"
            "NEOFORGE_INSTALLER_SHA256=${NEOFORGE_INSTALLER_SHA256:-"
            + sha256_bytes(b"expected installer")
            + "}\n"
            "PACKWIZ_BOOTSTRAP_VERSION=${PACKWIZ_BOOTSTRAP_VERSION:-0.0.3}\n"
            "PACKWIZ_BOOTSTRAP_SHA256=${PACKWIZ_BOOTSTRAP_SHA256:-"
            + sha256_bytes(b"bootstrap bytes")
            + "}\n"
            "PACKWIZ_INSTALLER_VERSION=${PACKWIZ_INSTALLER_VERSION:-0.5.14}\n"
            "PACKWIZ_INSTALLER_SHA256=${PACKWIZ_INSTALLER_SHA256:-"
            + sha256_bytes(b"expected packwiz installer")
            + "}\n"
            "PACKWIZ_INSTALLER_SIZE=${PACKWIZ_INSTALLER_SIZE:-27}\n"
            "JAVA_HOME=${JAVA_HOME:-/missing}\n"
            "PATH_EXTRA=${PATH_EXTRA:-/missing}\n",
            encoding="utf-8",
        )
        (self.root / "pack.toml").write_text("pack\n", encoding="utf-8")
        (self.root / "index.toml").write_text("index\n", encoding="utf-8")
        self._write_executable(
            self.root / "tools" / "rc_hygiene.py",
            "#!/usr/bin/env python3\nraise SystemExit(0)\n",
        )
        self._write_java(21)
        self._write_executable(
            self.fake_bin / "gtimeout", "#!/bin/sh\nexit 99\n"
        )
        self._write_packwiz("serve")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_executable(self, path: Path, source: str) -> None:
        path.write_text(source, encoding="utf-8")
        path.chmod(0o755)

    def _write_java(self, major: int) -> None:
        self._write_executable(
            self.java_home / "bin" / "java",
            textwrap.dedent(
                f"""\
                #!/bin/sh
                if [ "$1" = "-version" ]; then
                  echo 'openjdk version "{major}.0.1"' >&2
                  exit 0
                fi
                if [ "$1" = "-XshowSettings:properties" ]; then
                  echo '    java.home = {self.java_home}' >&2
                  exit 0
                fi
                echo invoked >> "{self.root / 'java-invocations.txt'}"
                exit 97
                """
            ),
        )

    def _write_installer_java(
        self, run_source: str = "#!/bin/sh\nexit 0\n", *, create_audit: bool = False
    ) -> None:
        self._write_executable(
            self.java_home / "bin" / "java",
            textwrap.dedent(
                f"""\
                #!/usr/bin/env python3
                import os
                from pathlib import Path
                import sys

                if sys.argv[1:] == ["-version"]:
                    print('openjdk version "21.0.1"', file=sys.stderr)
                    raise SystemExit(0)
                if sys.argv[1:2] == ["-XshowSettings:properties"]:
                    print("    java.home = {self.java_home}", file=sys.stderr)
                    raise SystemExit(0)
                with Path({str(self.root / 'java-arguments.txt')!r}).open("a", encoding="utf-8") as target:
                    target.write(" ".join(sys.argv[1:]) + "\\n")
                if sys.argv[1:3] == ["-jar", "neoforge-installer.jar"]:
                    run_path = Path({str(self.root / 'server-test' / 'run.sh')!r})
                    run_path.write_text({run_source!r}, encoding="utf-8")
                    run_path.chmod(0o755)
                    raise SystemExit(0)
                if sys.argv[1:3] == ["-jar", "packwiz-installer-bootstrap.jar"]:
                    if {create_audit!r}:
                        audit = Path({str(self.root / 'server-test/kubejs/server_scripts/afterlight/generated_quest_item_audit.js')!r})
                        audit.parent.mkdir(parents=True, exist_ok=True)
                        audit.write_text("__AFTERLIGHT_BOOT_NONCE__\\n", encoding="utf-8")
                        gate_audit = Path({str(self.root / 'server-test/kubejs/server_scripts/afterlight/gate_recipe_audit.js')!r})
                        gate_audit.write_text("Gate audit fixture\\n", encoding="utf-8")
                    raise SystemExit(0)
                raise SystemExit(97)
                """
            ),
        )

    def _write_authenticated_curl(self, packwiz_payload: bytes = b"expected packwiz installer") -> None:
        self._write_executable(
            self.fake_bin / "curl",
            textwrap.dedent(
                f"""\
                #!/bin/sh
                output=""
                previous=""
                for argument in "$@"; do
                  if [ "$previous" = "-o" ]; then output="$argument"; fi
                  previous="$argument"
                done
                printf '%s\n' "$*" >> "{self.root / 'curl-arguments.txt'}"
                case "$*" in
                  *maven.neoforged.net*) printf 'expected installer' > "$output" ;;
                  *packwiz-installer-bootstrap*) printf 'bootstrap bytes' > "$output" ;;
                  *packwiz/packwiz-installer/releases/download*) printf {packwiz_payload.decode('ascii')!r} > "$output" ;;
                  *) exec /usr/bin/curl "$@" ;;
                esac
                """
            ),
        )

    def _write_packwiz(self, mode: str) -> None:
        source = textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import http.server
            import os
            from pathlib import Path
            import socketserver
            import sys

            if {mode!r} == "dead":
                raise SystemExit(23)
            port = int(sys.argv[sys.argv.index("--port") + 1])
            Path({str(self.root / 'serve.pid')!r}).write_text(str(os.getpid()))
            os.chdir({str(self.root)!r})
            class Handler(http.server.SimpleHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass
                def do_GET(self):
                    if {mode!r} == "hold":
                        self.send_error(404)
                        return
                    super().do_GET()
            socketserver.TCPServer.allow_reuse_address = True
            with socketserver.TCPServer(("127.0.0.1", port), Handler) as server:
                server.serve_forever()
            """
        )
        self._write_executable(self.fake_bin / "packwiz", source)

    def _environment(
        self, port: int, overrides: dict[str, str] | None = None
    ) -> dict[str, str]:
        environment = os.environ.copy()
        environment.update(
            {
                "JAVA_HOME": str(self.java_home),
                "PATH_EXTRA": str(self.fake_bin),
                "SERVE_PORT": str(port),
                "AFTERLIGHT_CACHE_DIR": str(self.root / "cache"),
                "NEOFORGE_INSTALLER_SHA256": sha256_bytes(b"expected installer"),
                "PACKWIZ_BOOTSTRAP_SHA256": sha256_bytes(b"bootstrap bytes"),
                "PACKWIZ_INSTALLER_VERSION": "0.5.14",
                "PACKWIZ_INSTALLER_SHA256": sha256_bytes(
                    b"expected packwiz installer"
                ),
                "PACKWIZ_INSTALLER_SIZE": str(len(b"expected packwiz installer")),
            }
        )
        environment.update(overrides or {})
        return environment

    def _free_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            listener.bind(("127.0.0.1", 0))
            return int(listener.getsockname()[1])

    def _run(
        self,
        port: int,
        timeout: float = 20,
        overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", "tools/server-test.sh"],
            cwd=self.root,
            env=self._environment(port, overrides),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            check=False,
        )

    def _assert_port_released(self, port: int) -> None:
        deadline = time.monotonic() + 3
        while True:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    probe.bind(("127.0.0.1", port))
                break
            except OSError:
                if time.monotonic() >= deadline:
                    self.fail(f"serve port {port} was not released by trap cleanup")
                time.sleep(0.05)
        pid_path = self.root / "serve.pid"
        if pid_path.is_file():
            serve_pid = int(pid_path.read_text(encoding="utf-8"))
            with self.assertRaises(ProcessLookupError):
                os.kill(serve_pid, 0)

    def _wait_for_path(self, path: Path, timeout: float = 8) -> None:
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for {path}")
            time.sleep(0.05)

    def _wait_for_process_path(
        self, process: subprocess.Popen[str], path: Path, timeout: float = 8
    ) -> None:
        deadline = time.monotonic() + timeout
        while not path.exists():
            if process.poll() is not None:
                output, _ = process.communicate()
                self.fail(
                    f"process exited {process.returncode} before creating {path}: {output}"
                )
            if time.monotonic() >= deadline:
                self.fail(f"timed out waiting for {path}")
            time.sleep(0.05)

    def _assert_process_terminated(self, pid: int, timeout: float = 3) -> None:
        deadline = time.monotonic() + timeout
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            if time.monotonic() >= deadline:
                self.fail(f"process {pid} survived process-group cleanup")
            time.sleep(0.05)

    def test_wrong_java_preserves_prior_local_evidence(self) -> None:
        self._write_java(17)
        prior = self.root / "server-test" / "boot.log"
        prior.parent.mkdir()
        prior.write_text("prior boot evidence\n", encoding="utf-8")
        result = self._run(self._free_port())
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("need a working Java 21 runtime", result.stdout)
        self.assertEqual(prior.read_text(encoding="utf-8"), "prior boot evidence\n")

    def test_symlink_install_root_is_rejected_before_any_write(self) -> None:
        external = self.root / "external-install"
        external.mkdir()
        sentinel = external / "sentinel.txt"
        sentinel.write_text("must remain untouched\n", encoding="utf-8")
        (self.root / "server-test").symlink_to(external, target_is_directory=True)
        result = self._run(self._free_port())
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("symlink", result.stdout)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain untouched\n")
        self.assertEqual(sorted(path.name for path in external.iterdir()), ["sentinel.txt"])

    def test_symlink_evidence_root_is_rejected_before_any_external_write(self) -> None:
        install = self.root / "server-test"
        install.mkdir()
        external = self.root / "external-evidence"
        external.mkdir()
        sentinel = external / "sentinel.txt"
        sentinel.write_text("must remain untouched\n", encoding="utf-8")
        (install / "evidence").symlink_to(external, target_is_directory=True)

        result = self._run(self._free_port())

        self.assertEqual(result.returncode, 9, result.stdout)
        self.assertIn("symlink", result.stdout)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "must remain untouched\n")
        self.assertEqual(sorted(path.name for path in external.iterdir()), ["sentinel.txt"])

    def test_sigint_and_sigterm_terminate_packwiz_and_preserve_prior_evidence(
        self,
    ) -> None:
        for signal_number in (2, 15):
            with self.subTest(signal=signal_number):
                (self.root / "serve.pid").unlink(missing_ok=True)
                self._write_packwiz("hold")
                port = self._free_port()
                prior = self.root / "server-test" / "boot.log"
                prior.parent.mkdir(exist_ok=True)
                prior.write_text("prior signal evidence\n", encoding="utf-8")
                process = subprocess.Popen(
                    ["bash", "tools/server-test.sh"],
                    cwd=self.root,
                    env=self._environment(port),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                try:
                    self._wait_for_path(self.root / "serve.pid")
                    os.kill(process.pid, signal_number)
                    output, _ = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 130, output)
                    self.assertEqual(
                        prior.read_text(encoding="utf-8"),
                        "prior signal evidence\n",
                    )
                    self.assertEqual(
                        list((self.root / "cache").glob("*.tmp.*"))
                        if (self.root / "cache").exists()
                        else [],
                        [],
                    )
                    self._assert_port_released(port)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)

    def test_sigint_and_sigterm_terminate_server_process_group_and_free_port(
        self,
    ) -> None:
        for signal_number in (2, 15):
            with self.subTest(signal=signal_number):
                (self.root / "server.pid").unlink(missing_ok=True)
                (self.root / "server.ppid").unlink(missing_ok=True)
                (self.root / "server.pgrp").unlink(missing_ok=True)
                (self.root / "timeout.pid").unlink(missing_ok=True)
                (self.root / "serve.pid").unlink(missing_ok=True)
                server_port = self._free_port()
                run_script = textwrap.dedent(
                    f"""\
                    #!/bin/sh
                    exec {sys.executable} -c "import os,socket,time; from pathlib import Path; s=socket.socket(); s.bind(('127.0.0.1', {server_port})); s.listen(); Path({str(self.root / 'server.pid')!r}).write_text(str(os.getpid())); Path({str(self.root / 'server.ppid')!r}).write_text(str(os.getppid())); Path({str(self.root / 'server.pgrp')!r}).write_text(str(os.getpgrp())); time.sleep(60)"
                    """
                )
                self._prepare_packwiz_installer_stage(
                    run_script, create_audit=True
                )
                self._write_executable(
                    self.fake_bin / "gtimeout",
                    "#!/bin/sh\n"
                    f"echo $$ > {str(self.root / 'timeout.pid')!r}\n"
                    "shift\n\"$@\" &\nchild=$!\nwait \"$child\"\n",
                )
                serve_port = self._free_port()
                process = subprocess.Popen(
                    ["bash", "tools/server-test.sh"],
                    cwd=self.root,
                    env=self._environment(
                        serve_port, {"SERVER_PORT": str(server_port)}
                    ),
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )
                child_pid = None
                timeout_pid = None
                try:
                    self._wait_for_process_path(
                        process, self.root / "server.pid", timeout=12
                    )
                    self._wait_for_process_path(
                        process, self.root / "timeout.pid", timeout=12
                    )
                    child_pid = int(
                        (self.root / "server.pid").read_text(encoding="utf-8")
                    )
                    timeout_pid = int(
                        (self.root / "timeout.pid").read_text(encoding="utf-8")
                    )
                    os.kill(process.pid, signal_number)
                    output, _ = process.communicate(timeout=10)
                    self.assertEqual(process.returncode, 130, output)
                    self.assertNotEqual(timeout_pid, child_pid)
                    self.assertEqual(
                        int((self.root / "server.ppid").read_text(encoding="utf-8")),
                        timeout_pid,
                    )
                    self.assertEqual(
                        int((self.root / "server.pgrp").read_text(encoding="utf-8")),
                        timeout_pid,
                    )
                    self._assert_process_terminated(timeout_pid)
                    self._assert_process_terminated(child_pid)
                    self._assert_port_released(server_port)
                    self._assert_port_released(serve_port)
                finally:
                    if process.poll() is None:
                        process.kill()
                        process.wait(timeout=5)
                    if child_pid is not None:
                        try:
                            os.kill(child_pid, 9)
                        except ProcessLookupError:
                            pass
                    if timeout_pid is not None and timeout_pid != child_pid:
                        try:
                            os.kill(timeout_pid, 9)
                        except ProcessLookupError:
                            pass

    def test_occupied_404_port_preserves_prior_boot_log(self) -> None:
        port = self._free_port()
        server = subprocess.Popen(
            [
                sys.executable,
                "-c",
                "import http.server,socketserver; "
                f"socketserver.TCPServer(('127.0.0.1',{port}),http.server.SimpleHTTPRequestHandler).serve_forever()",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            time.sleep(0.15)
            prior = self.root / "server-test" / "boot.log"
            prior.parent.mkdir()
            prior.write_text("prior 404 evidence\n", encoding="utf-8")
            result = self._run(port)
            self.assertEqual(result.returncode, 4, result.stdout)
            self.assertIn("port", result.stdout)
            self.assertEqual(prior.read_text(encoding="utf-8"), "prior 404 evidence\n")
        finally:
            server.terminate()
            server.wait(timeout=5)

    def test_dead_packwiz_serve_fails_without_readiness_false_positive(self) -> None:
        self._write_packwiz("dead")
        port = self._free_port()
        result = self._run(port)
        self.assertEqual(result.returncode, 4, result.stdout)
        self.assertIn("exited before readiness", result.stdout)
        self._assert_port_released(port)

    def test_corrupt_cached_installer_is_removed_without_execution(self) -> None:
        port = self._free_port()
        cache = self.root / "cache" / "neoforge-21.1.248-installer.jar"
        cache.parent.mkdir()
        cache.write_bytes(b"corrupt cached installer")
        result = self._run(port)
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("NEOFORGE_INSTALLER_SHA256 mismatch", result.stdout)
        self.assertFalse(cache.exists())
        self.assertFalse((self.root / "java-invocations.txt").exists())
        self._assert_port_released(port)

    def test_corrupt_download_is_never_published_and_trap_cleans_serve(self) -> None:
        curl = textwrap.dedent(
            """\
            #!/bin/sh
            output=""
            previous=""
            for argument in "$@"; do
              if [ "$previous" = "-o" ]; then output="$argument"; fi
              previous="$argument"
            done
            case "$*" in
              *maven.neoforged.net*) printf 'corrupt temp installer' > "$output"; exit 0 ;;
            esac
            exec /usr/bin/curl "$@"
            """
        )
        self._write_executable(self.fake_bin / "curl", curl)
        port = self._free_port()
        result = self._run(port)
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("NEOFORGE_INSTALLER_SHA256 mismatch", result.stdout)
        cache = self.root / "cache" / "neoforge-21.1.248-installer.jar"
        self.assertFalse(cache.exists())
        self.assertEqual(list(cache.parent.glob("*.tmp.*")), [])
        self.assertFalse((self.root / "java-invocations.txt").exists())
        self._assert_port_released(port)

    def _prepare_packwiz_installer_stage(
        self, run_source: str = "#!/bin/sh\nexit 0\n", *, create_audit: bool = False
    ) -> None:
        self._write_installer_java(run_source, create_audit=create_audit)
        self._write_authenticated_curl()
        neoforge_cache = self.root / "cache" / "neoforge-21.1.248-installer.jar"
        neoforge_cache.parent.mkdir(parents=True, exist_ok=True)
        neoforge_cache.write_bytes(b"expected installer")

    def test_packwiz_installer_uses_immutable_download_and_exact_bootstrap_argv(
        self,
    ) -> None:
        self._prepare_packwiz_installer_stage()
        port = self._free_port()
        result = self._run(port)
        self.assertEqual(result.returncode, 7, result.stdout)
        self.assertIn("generated quest item audit script missing", result.stdout)
        curl_arguments = (self.root / "curl-arguments.txt").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            "https://github.com/packwiz/packwiz-installer/releases/download/"
            "v0.5.14/packwiz-installer.jar",
            curl_arguments,
        )
        self.assertNotIn("releases/latest", curl_arguments)
        java_arguments = (self.root / "java-arguments.txt").read_text(
            encoding="utf-8"
        ).splitlines()
        bootstrap = next(
            line
            for line in java_arguments
            if line.startswith("-jar packwiz-installer-bootstrap.jar")
        )
        self.assertEqual(
            bootstrap,
            "-jar packwiz-installer-bootstrap.jar --bootstrap-no-update "
            "--bootstrap-main-jar packwiz-installer.jar -g -s server "
            f"http://localhost:{port}/pack.toml",
        )
        self._assert_port_released(port)

    def test_corrupt_cached_packwiz_installer_is_removed_before_bootstrap(self) -> None:
        self._prepare_packwiz_installer_stage()
        cache = self.root / "cache" / "packwiz-installer-0.5.14.jar"
        cache.write_bytes(b"corrupt cached packwiz installer")
        port = self._free_port()
        result = self._run(port)
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("PACKWIZ_INSTALLER", result.stdout)
        self.assertFalse(cache.exists())
        arguments = (self.root / "java-arguments.txt").read_text(encoding="utf-8")
        self.assertNotIn("packwiz-installer-bootstrap.jar", arguments)
        self._assert_port_released(port)

    def test_packwiz_installer_rejects_wrong_size_and_wrong_hash(self) -> None:
        cases = (
            (
                {"PACKWIZ_INSTALLER_SIZE": "28"},
                "size mismatch",
            ),
            (
                {"PACKWIZ_INSTALLER_SHA256": "0" * 64},
                "SHA-256 mismatch",
            ),
        )
        for overrides, message in cases:
            with self.subTest(message=message):
                self._prepare_packwiz_installer_stage()
                cache = self.root / "cache" / "packwiz-installer-0.5.14.jar"
                cache.write_bytes(b"expected packwiz installer")
                result = self._run(self._free_port(), overrides=overrides)
                self.assertEqual(result.returncode, 3, result.stdout)
                self.assertIn(message, result.stdout)
                self.assertFalse(cache.exists())

    def test_corrupt_packwiz_download_is_not_published(self) -> None:
        self._prepare_packwiz_installer_stage()
        self._write_authenticated_curl(b"corrupt packwiz download")
        cache = self.root / "cache" / "packwiz-installer-0.5.14.jar"
        result = self._run(self._free_port())
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("PACKWIZ_INSTALLER", result.stdout)
        self.assertFalse(cache.exists())
        self.assertEqual(list(cache.parent.glob("*.tmp.*")), [])

    def test_missing_packwiz_main_jar_fails_before_bootstrap_execution(self) -> None:
        self._prepare_packwiz_installer_stage()
        self._write_executable(
            self.fake_bin / "cp",
            textwrap.dedent(
                """\
                #!/bin/sh
                case "$1" in
                  *packwiz-installer-0.5.14.jar) exit 0 ;;
                esac
                exec /bin/cp "$@"
                """
            ),
        )
        result = self._run(self._free_port())
        self.assertEqual(result.returncode, 3, result.stdout)
        self.assertIn("packwiz-installer.jar missing", result.stdout)
        arguments = (self.root / "java-arguments.txt").read_text(encoding="utf-8")
        self.assertNotIn("packwiz-installer-bootstrap.jar", arguments)


if __name__ == "__main__":
    unittest.main(verbosity=2)
