#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import tomllib
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Sequence


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LogRecord:
    level: str
    logger: str
    message: str
    text: str


@dataclass(frozen=True)
class LogAllowance:
    label: str
    level: str
    logger: str
    message: str
    count: int
    contexts: tuple[str, ...] = ()


RUNTIME_DIST_CLEANER_MESSAGE = (
    "Attempted to load class net/minecraft/client/multiplayer/ClientLevel "
    "for invalid dist DEDICATED_SERVER"
)
MOONLIGHT_FABRIC_MESSAGE = (
    "Fabric API detected! This is not a Fabric mod, so please don't report related "
    "issues to MoonlightLib or its dependent(s). This can usually happen when using "
    "Connector, or when using a mod that does NOT have a native Neoforge implementation. "
    "This can easily lead to poor compatibility and other bizarre issues. Proceed at "
    "your own risk. "
)
ITEMSTACK_AIR_MESSAGE = "Tried to load invalid item: 'Item must not be minecraft:air'"
JDT_WARNING_MESSAGE = (
    "Error white registering dispenser behavior for item justdirethings:fuel_canister: "
    "java.lang.IllegalStateException: Cannot get config value before config is loaded."
)
KALEIDOSCOPE_SUFFIX = (
    "[kaleidoscope_cookery:stockpot], falling back to default value: "
    "java.lang.IllegalStateException: Failed to parse either. First: Item array cannot "
    "be empty, at least one item must be defined; Second: Not a JSON object: []"
)
INCENDIUM_WARNING_MESSAGE = (
    "KubeRecipe.java#90: Failed to parse recipe "
    "'incendium:upgrade_elytra[minecraft:smithing_transform]'! Falling back to vanilla: "
    "Failed to read required component 'template: ingredient' - "
    "java.lang.IllegalStateException: Failed to parse either. First: Item array cannot "
    "be empty, at least one item must be defined; Second: Not a JSON object: []"
)
APOTHIC_WARNING_MESSAGE = (
    "Found data map file for non-existent data map type "
    "'apothic_enchanting:enchantment_info' on registry 'minecraft:enchantment'."
)

JDT_ARTIFACT_SHA256 = {
    "mods/just-dire-things.pw.toml": "6e5f7dd7091cc271fee66b0df62bde2250e8b52397b51dd911f79c088eb22d2f",
    "mods/supplementaries.pw.toml": "cdd3d67b510f20f386690a2cbdbe63fd1ae9c8a620861738b6b80b1fa5c996f9",
    "mods/moonlight.pw.toml": "e64737a18c934fe1fac2c4bf3ea1e997012d06ab67e2a06635def5968edb4474",
    "mods/kubejs.pw.toml": "01767bb677a9c4a8f318717c4c21bca7e7ef80995603403a551068a0e064e740",
}
JDT_CLASS_SHA256 = {
    (
        "mods/supplementaries.pw.toml",
        "net/mehvahdjukaar/supplementaries/common/block/dispenser/DispenserBehaviorsManager.class",
    ): "55d5096f83b294f4c6830bcde99b8e3c3a0f9d18f101c60cccc7c88828c2e70a",
    (
        "mods/supplementaries.pw.toml",
        "net/mehvahdjukaar/supplementaries/common/block/ModBlockProperties$Topping.class",
    ): "4637feea2f739e9169b3a615b705b0dfa2d65755c33e784bb00d1592caca041f",
    (
        "mods/just-dire-things.pw.toml",
        "com/direwolf20/justdirethings/common/items/FuelCanister.class",
    ): "ff6b13094a4b1cacd6a3a0dc155aee7e6cb4fa4fe1d948549858b9e6b8e55b28",
}
JDT_RUNTIME_SHA256 = {
    "libraries/net/neoforged/neoforge/21.1.248/neoforge-21.1.248-universal.jar": (
        "90a56f70425711b4e1a4b94ff0c2904ae9f6d74ca6478b3b2152ac794a07b8e5"
    ),
    "libraries/net/minecraft/server/1.21.1-20240808.144430/"
    "server-1.21.1-20240808.144430-srg.jar": (
        "26ca9c40d7e1681190b428583c38816852218e78df3f8bdb60a59a78503aec71"
    ),
}
JDT_CONFIG_SHA256 = "1585ad9a8fe3627f4858968de254f17dce69b73607940ca81e99d17a62289fe2"


LOG_HEADER = re.compile(
    r"^\[[^\]]+\] \[[^\]]+\/(?P<level>[A-Z]+)\] "
    r"\[(?P<logger>[^\]]+)\]: (?P<message>.*)$"
)


def _hash_bytes(payload: bytes, hash_format: str) -> str:
    normalized = hash_format.lower().replace("-", "")
    try:
        digest = hashlib.new(normalized)
    except ValueError as error:
        raise VerificationError(f"unsupported hash format {hash_format}") from error
    digest.update(payload)
    return digest.hexdigest()


def _hash_file(path: Path, hash_format: str) -> str:
    normalized = hash_format.lower().replace("-", "")
    try:
        digest = hashlib.new(normalized)
    except ValueError as error:
        raise VerificationError(f"unsupported hash format {hash_format}") from error
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise VerificationError(f"cannot read TOML {path}: {error}") from error


def _safe_relative_path(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise VerificationError(f"unsafe {label} path {value!r}")
    return path


def verify_manifest(root: Path | str) -> dict[str, str]:
    root_path = Path(root).resolve()
    pack_path = root_path / "pack.toml"
    pack_bytes = pack_path.read_bytes()
    pack = _read_toml(pack_path)
    index_config = pack.get("index")
    if not isinstance(index_config, dict):
        raise VerificationError("pack.toml has no index table")

    index_relative = _safe_relative_path(str(index_config.get("file", "")), "index")
    index_path = root_path.joinpath(*index_relative.parts)
    index_bytes = index_path.read_bytes()
    index_hash_format = str(index_config.get("hash-format", ""))
    expected_index_hash = str(index_config.get("hash", ""))
    actual_index_hash = _hash_bytes(index_bytes, index_hash_format)
    if actual_index_hash != expected_index_hash:
        raise VerificationError(
            f"index hash mismatch: expected {expected_index_hash}, got {actual_index_hash}"
        )

    index = _read_toml(index_path)
    file_hash_format = str(index.get("hash-format", ""))
    entries = index.get("files")
    if not isinstance(entries, list):
        raise VerificationError("index.toml has no files array")

    indexed_hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("index.toml contains a non-table file entry")
        relative_text = str(entry.get("file", ""))
        relative = _safe_relative_path(relative_text, "indexed file")
        if relative_text in indexed_hashes:
            raise VerificationError(f"duplicate index entry {relative_text}")
        target = root_path.joinpath(*relative.parts)
        if not target.is_file():
            raise VerificationError(f"indexed file is missing: {relative_text}")
        expected_hash = str(entry.get("hash", ""))
        actual_hash = _hash_file(target, file_hash_format)
        if actual_hash != expected_hash:
            raise VerificationError(
                f"indexed file hash mismatch for {relative_text}: expected {expected_hash}, got {actual_hash}"
            )
        indexed_hashes[relative_text] = expected_hash

    return {
        "pack_hash": _hash_bytes(pack_bytes, "sha256"),
        "index_hash": actual_index_hash,
        "index_hash_format": index_hash_format,
        "file_hash_format": file_hash_format,
        "indexed_hashes": indexed_hashes,
    }


def verify_install_provenance(root: Path | str, install: Path | str) -> dict:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    manifest = verify_manifest(root_path)
    provenance_path = install_path / "packwiz.json"
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read installer provenance {provenance_path}: {error}") from error

    expected_pack = provenance.get("packFileHash", {})
    if expected_pack != {"type": "sha256", "value": manifest["pack_hash"]}:
        raise VerificationError("installed pack provenance does not match current pack.toml")
    expected_index = provenance.get("indexFileHash", {})
    if expected_index != {
        "type": manifest["index_hash_format"],
        "value": manifest["index_hash"],
    }:
        raise VerificationError("installed index provenance does not match current index.toml")
    if provenance.get("cachedSide") != "server":
        raise VerificationError("installer provenance is not for server side")
    if not isinstance(provenance.get("cachedFiles"), dict):
        raise VerificationError("installer provenance has no cachedFiles map")
    return provenance


def _resolve_source_jar(
    root_path: Path,
    install_path: Path,
    metadata_relative: str,
    manifest: dict,
    provenance: dict,
) -> Path:
    metadata_posix = _safe_relative_path(metadata_relative, "metadata")
    if metadata_posix.suffixes[-2:] != [".pw", ".toml"]:
        raise VerificationError(f"source metadata must be an exact .pw.toml path: {metadata_relative}")
    metadata_path = root_path.joinpath(*metadata_posix.parts)
    indexed_hashes = manifest["indexed_hashes"]
    if metadata_relative not in indexed_hashes:
        raise VerificationError(f"source metadata is not indexed: {metadata_relative}")

    metadata = _read_toml(metadata_path)
    filename = str(metadata.get("filename", ""))
    if not filename or PurePosixPath(filename).name != filename:
        raise VerificationError(f"invalid source filename in {metadata_relative}")
    side = metadata.get("side")
    if side not in ("server", "both"):
        raise VerificationError(
            f"source metadata {metadata_relative} is not installed on the server side"
        )
    download = metadata.get("download")
    if not isinstance(download, dict):
        raise VerificationError(f"source metadata has no download table: {metadata_relative}")
    declared_hash_format = str(download.get("hash-format", ""))
    declared_hash = str(download.get("hash", ""))

    cached = provenance["cachedFiles"].get(metadata_relative)
    if not isinstance(cached, dict):
        raise VerificationError(f"installer provenance has no entry for {metadata_relative}")
    expected_metadata_hash = {
        "type": manifest["file_hash_format"],
        "value": indexed_hashes[metadata_relative],
    }
    if cached.get("hash") != expected_metadata_hash:
        raise VerificationError(f"stale installer metadata provenance for {metadata_relative}")
    if cached.get("linkedFileHash") != {
        "type": declared_hash_format,
        "value": declared_hash,
    }:
        raise VerificationError(f"stale installer artifact provenance for {metadata_relative}")
    if cached.get("optionValue") is not True:
        raise VerificationError(f"installer disabled source artifact {metadata_relative}")
    cached_location = str(cached.get("cachedLocation", ""))
    cached_posix = _safe_relative_path(cached_location, "cached artifact")
    if cached_posix.name != filename:
        raise VerificationError(
            f"cached artifact filename mismatch for {metadata_relative}: {cached_posix.name} != {filename}"
        )
    jar_path = install_path.joinpath(*cached_posix.parts)
    if not jar_path.is_file():
        raise VerificationError(f"source artifact is missing: {jar_path}")
    actual_hash = _hash_file(jar_path, declared_hash_format)
    if actual_hash != declared_hash:
        raise VerificationError(
            f"{filename} hash mismatch: expected {declared_hash}, got {actual_hash}"
        )
    return jar_path


def resolve_source_jars(
    root: Path | str, install: Path | str, metadata_relatives: Iterable[str]
) -> dict[str, Path]:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    manifest = verify_manifest(root_path)
    provenance = verify_install_provenance(root_path, install_path)
    return {
        metadata_relative: _resolve_source_jar(
            root_path,
            install_path,
            metadata_relative,
            manifest,
            provenance,
        )
        for metadata_relative in metadata_relatives
    }


def resolve_source_jar(
    root: Path | str, install: Path | str, metadata_relative: str
) -> Path:
    return resolve_source_jars(root, install, (metadata_relative,))[metadata_relative]


def parse_log_records(log_text: str) -> tuple[LogRecord, ...]:
    records: list[LogRecord] = []
    current_match: re.Match[str] | None = None
    current_lines: list[str] = []

    def finish_record() -> None:
        nonlocal current_match, current_lines
        if current_match is None:
            return
        records.append(
            LogRecord(
                level=current_match.group("level"),
                logger=current_match.group("logger"),
                message=current_match.group("message"),
                text="\n".join(current_lines),
            )
        )

    for line in log_text.splitlines():
        match = LOG_HEADER.match(line)
        if match:
            finish_record()
            current_match = match
            current_lines = [line]
        elif current_match is not None:
            current_lines.append(line)
    finish_record()
    return tuple(records)


def validate_error_records(
    log_text: str, allowances: Iterable[LogAllowance]
) -> Counter[str]:
    allowance_list = tuple(allowances)
    observed: Counter[str] = Counter()
    for record in parse_log_records(log_text):
        if record.level not in ("ERROR", "FATAL"):
            continue
        matches = [
            allowance
            for allowance in allowance_list
            if record.level == allowance.level
            and record.logger == allowance.logger
            and record.message == allowance.message
            and all(context in record.text for context in allowance.contexts)
        ]
        if len(matches) != 1:
            raise VerificationError(
                f"unmatched {record.level} record from {record.logger}: {record.message}"
            )
        observed[matches[0].label] += 1

    for allowance in allowance_list:
        actual = observed[allowance.label]
        if actual != allowance.count:
            raise VerificationError(
                f"{allowance.label} count mismatch: expected {allowance.count}, got {actual}"
            )
    return observed


def _validate_selected_records(
    records: Iterable[LogRecord],
    allowances: Iterable[LogAllowance],
    selected: Callable[[LogRecord], bool],
    category: str,
) -> Counter[str]:
    allowance_list = tuple(allowances)
    observed: Counter[str] = Counter()
    for record in records:
        if not selected(record):
            continue
        matches = [
            allowance
            for allowance in allowance_list
            if record.level == allowance.level
            and record.logger == allowance.logger
            and record.message == allowance.message
            and all(context in record.text for context in allowance.contexts)
        ]
        if len(matches) != 1:
            raise VerificationError(
                f"unmatched {category} record from {record.logger}: {record.message}"
            )
        observed[matches[0].label] += 1
    for allowance in allowance_list:
        actual = observed[allowance.label]
        if actual != allowance.count:
            raise VerificationError(
                f"{allowance.label} count mismatch: expected {allowance.count}, got {actual}"
            )
    return observed


def project_error_allowances() -> tuple[LogAllowance, ...]:
    return (
        LogAllowance(
            label="RuntimeDistCleaner client class errors",
            level="ERROR",
            logger="net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
            message=RUNTIME_DIST_CLEANER_MESSAGE,
            count=12,
        ),
        LogAllowance(
            label="Moonlight Fabric API detection error",
            level="ERROR",
            logger="Moonlight/",
            message=MOONLIGHT_FABRIC_MESSAGE,
            count=1,
            contexts=(
                "Mods that bundle Fabric API: [forgified-fabric-api-0.115.6+2.1.0+1.21.1.jar]",
            ),
        ),
        LogAllowance(
            label="Fabric overlay metadata error",
            level="ERROR",
            logger="net.minecraft.server.packs.AbstractPackResources/",
            message="Couldn't load fabric:overlays metadata",
            count=1,
            contexts=(
                "Unknown resource condition key: tectonic:config",
                "fabric_resource_conditions_api_v1$applyOverlayConditions",
                "tectonic@3.0.26/dev.worldgen.tectonic.platform.neoforge.TectonicNeoforge.registerEnabledPacks",
            ),
        ),
        LogAllowance(
            label="IDAS underground camp air ItemStack errors",
            level="ERROR",
            logger="net.minecraft.world.item.ItemStack/",
            message=ITEMSTACK_AIR_MESSAGE,
            count=2,
        ),
    )


def project_warning_allowances() -> tuple[LogAllowance, ...]:
    kaleidoscope = tuple(
        LogAllowance(
            label=f"Kaleidoscope carrier {food}_count_{count}",
            level="WARN",
            logger="KubeJS Server/",
            message=(
                "RecipeComponent.java#160: Failed to read component 'carrier: ingredient?' "
                f"from recipe kaleidoscope_cookery:stockpot/{food}_count_{count}"
                f"{KALEIDOSCOPE_SUFFIX}"
            ),
            count=1,
        )
        for food in ("shengjian_mantou", "dumpling", "zongzi")
        for count in range(1, 10)
    )
    malum = tuple(
        LogAllowance(
            label=f"EnderIO Malum inheritance {metal}",
            level="WARN",
            logger="net.minecraft.world.item.crafting.RecipeManager/",
            message=(
                "[EnderIO] Unable to inherit the cooking recipe with ID: "
                f"malum:{metal}_from_node_smelting. Reason: The result item is empty."
            ),
            count=1,
        )
        for metal in (
            "tin",
            "uranium",
            "copper",
            "silver",
            "zinc",
            "osmium",
            "nickel",
            "lead",
            "aluminum",
        )
    )
    return kaleidoscope + (
        LogAllowance(
            label="Incendium smithing fallback",
            level="WARN",
            logger="KubeJS Server/",
            message=INCENDIUM_WARNING_MESSAGE,
            count=1,
        ),
    ) + malum + (
        LogAllowance(
            label="Apothic Enchanting stale data map type",
            level="WARN",
            logger="net.neoforged.neoforge.registries.DataMapLoader/",
            message=APOTHIC_WARNING_MESSAGE,
            count=1,
        ),
        LogAllowance(
            label="Just Dire Things early pancake candidate scan",
            level="WARN",
            logger="Supplementaries/",
            message=JDT_WARNING_MESSAGE,
            count=1,
        ),
    )


def validate_known_residual_warnings(log_text: str) -> Counter[str]:
    def selected(record: LogRecord) -> bool:
        if record.level != "WARN":
            return False
        message = record.message
        return any(
            marker in message
            for marker in (
                "kaleidoscope_cookery:stockpot/",
                "incendium:upgrade_elytra",
                "[EnderIO] Unable to inherit the cooking recipe with ID: malum:",
                "apothic_enchanting:enchantment_info",
                "registering dispenser behavior for item",
                "Not all defined tags for registry ResourceKey[minecraft:root / minecraft:worldgen/biome] are present in data pack: idas:",
                "Couldn't load tag idas:",
            )
        )

    return _validate_selected_records(
        parse_log_records(log_text),
        project_warning_allowances(),
        selected,
        "known residual WARN",
    )


def verify_jdt_evidence(root: Path | str, install: Path | str) -> None:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    resolved = resolve_source_jars(
        root_path, install_path, JDT_ARTIFACT_SHA256.keys()
    )
    for metadata_relative, expected_hash in JDT_ARTIFACT_SHA256.items():
        jar_path = resolved[metadata_relative]
        actual_hash = _hash_file(jar_path, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT evidence artifact hash mismatch for {metadata_relative}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    for (metadata_relative, resource), expected_hash in JDT_CLASS_SHA256.items():
        try:
            with zipfile.ZipFile(resolved[metadata_relative]) as archive:
                payload = archive.read(resource)
        except (OSError, KeyError, zipfile.BadZipFile) as error:
            raise VerificationError(f"cannot read JDT evidence class {resource}: {error}") from error
        actual_hash = _hash_bytes(payload, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT evidence class hash mismatch for {resource}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    for relative, expected_hash in JDT_RUNTIME_SHA256.items():
        runtime_path = install_path / relative
        actual_hash = _hash_file(runtime_path, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT runtime hash mismatch for {relative}: expected {expected_hash}, got {actual_hash}"
            )

    for config_path in (
        root_path / "config" / "justdirethings-server.toml",
        install_path / "config" / "justdirethings-server.toml",
    ):
        actual_hash = _hash_file(config_path, "sha256")
        if actual_hash != JDT_CONFIG_SHA256:
            raise VerificationError(
                f"JDT config hash mismatch for {config_path}: "
                f"expected {JDT_CONFIG_SHA256}, got {actual_hash}"
            )


def verify_boot_run(
    root: Path | str, install: Path | str, nonce: str, status: int
) -> dict[str, Counter[str]]:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    verify_install_provenance(root_path, install_path)
    verify_jdt_evidence(root_path, install_path)
    log_path = install_path / "logs" / "latest.log"
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise VerificationError(f"cannot read authoritative current log {log_path}: {error}") from error
    validate_boot_markers(log_text, nonce, status)
    errors = validate_error_records(log_text, project_error_allowances())
    warnings = validate_known_residual_warnings(log_text)
    return {"errors": errors, "warnings": warnings}


def validate_boot_markers(log_text: str, nonce: str, status: int) -> None:
    if status != 0:
        raise VerificationError(f"server exit status {status} is not a graceful exit")
    records = parse_log_records(log_text)
    done = [
        record
        for record in records
        if record.level == "INFO"
        and record.logger == "net.minecraft.server.dedicated.DedicatedServer/"
        and re.fullmatch(r'Done \(\d+(?:\.\d+)?s\)! For help, type "help"', record.message)
    ]
    if len(done) != 1:
        raise VerificationError(
            f"expected one anchored DedicatedServer Done record, got {len(done)}"
        )

    audit_pattern = re.compile(
        rf"\[AFTERLIGHT QUEST ITEM AUDIT\] OK [0-9a-f]{{64}} 219 {re.escape(nonce)}"
    )
    audits = [
        record
        for record in records
        if record.level == "INFO"
        and record.logger == "KubeJS Server/"
        and audit_pattern.fullmatch(record.message)
    ]
    if len(audits) != 1:
        raise VerificationError(
            f"expected one fresh audit nonce record for {nonce}, got {len(audits)}"
        )

    shutdown_messages = (
        "Stopping server",
        "Saving players",
        "Saving worlds",
        "ThreadedAnvilChunkStorage: All dimensions are saved",
    )
    missing = [
        message
        for message in shutdown_messages
        if not any(
            record.level == "INFO"
            and record.logger == "net.minecraft.server.MinecraftServer/"
            and record.message == message
            for record in records
        )
    ]
    if missing:
        raise VerificationError(f"clean shutdown markers missing: {', '.join(missing)}")


FILTER_METADATA = {
    "pack": {
        "description": "AFTERLIGHT RC hygiene resource filter",
        "pack_format": 48,
    },
    "filter": {
        "block": [
            {
                "namespace": "^create_enchantment_industry$",
                "path": r"^data_maps/fluid/unit/experience\.json$",
            }
        ]
    },
}


def filter_matches(
    namespace_pattern: str, path_pattern: str, namespace: str, path: str
) -> bool:
    return bool(re.fullmatch(namespace_pattern, namespace)) and bool(
        re.fullmatch(path_pattern, path)
    )


def build_filter_archive() -> bytes:
    payload = (json.dumps(FILTER_METADATA, indent=2) + "\n").encode("utf-8")
    output = io.BytesIO()
    entry = zipfile.ZipInfo("pack.mcmeta", date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_STORED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    entry.extra = b""
    entry.comment = b""
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = b""
        archive.writestr(entry, payload)
    return output.getvalue()


def _cli_verify_manifest(args: argparse.Namespace) -> None:
    result = verify_manifest(Path(args.root))
    print(
        "MANIFEST: OK "
        f"pack={result['pack_hash']} index={result['index_hash']} "
        f"files={len(result['indexed_hashes'])}"
    )


def _cli_verify_provenance(args: argparse.Namespace) -> None:
    verify_install_provenance(Path(args.root), Path(args.install))
    print("PROVENANCE: OK")


def _cli_verify_boot(args: argparse.Namespace) -> None:
    result = verify_boot_run(
        Path(args.root), Path(args.install), args.nonce, args.status
    )
    print(
        "BOOT ORACLE: OK "
        f"errors={sum(result['errors'].values())} "
        f"known-warnings={sum(result['warnings'].values())}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AFTERLIGHT RC hygiene verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest = subparsers.add_parser("verify-manifest")
    manifest.add_argument("--root", default=".")
    manifest.set_defaults(handler=_cli_verify_manifest)
    provenance = subparsers.add_parser("verify-provenance")
    provenance.add_argument("--root", default=".")
    provenance.add_argument("--install", required=True)
    provenance.set_defaults(handler=_cli_verify_provenance)
    boot = subparsers.add_parser("verify-boot")
    boot.add_argument("--root", default=".")
    boot.add_argument("--install", required=True)
    boot.add_argument("--nonce", required=True)
    boot.add_argument("--status", required=True, type=int)
    boot.set_defaults(handler=_cli_verify_boot)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except VerificationError as error:
        print(f"RC HYGIENE: FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
