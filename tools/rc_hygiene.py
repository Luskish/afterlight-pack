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
    thread: str
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


@dataclass(frozen=True)
class DedicatedErrorEvidence:
    label: str
    latest_record_indices: tuple[int, ...]
    debug_record_indices: tuple[int, ...]


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

SABLE_METADATA = "mods/sable.pw.toml"
SABLE_ARTIFACT_SHA256 = "da6c3b66238586603d1dcaa2afb012d36815fbce0a2d5938fbb2936701d42279"
SABLE_MIXIN_CONFIG = "sable.mixins.json"
SABLE_MIXIN_CONFIG_SHA256 = "02dd86d2bd0ed6bef4841b1ae4ac8579edeb33fe0134f2060191b49102c4878d"
SABLE_MIXIN_CLASSES = {
    "entity.entity_aabb_lookup.LevelsMixin": (
        40,
        "dev/ryanhcode/sable/mixin/entity/entity_aabb_lookup/LevelsMixin.class",
        "0b6d6e637410852d131f2178c53a454bdd506555e509c5aea2ce3127d01070c0",
    ),
    "plot.LevelsMixin": (
        100,
        "dev/ryanhcode/sable/mixin/plot/LevelsMixin.class",
        "660410f918f5676d49e734028cb2e74967a622746cc7c7f22ff805016c476bda",
    ),
    "water_occlusion.LevelsMixin": (
        132,
        "dev/ryanhcode/sable/mixin/water_occlusion/LevelsMixin.class",
        "f5cecf91372f08ef0b5b9bc36f609b6f2df726dc3612731d9e0a5a56460b647c",
    ),
}
SABLE_ENABLED_METADATA_COUNT = 158
SABLE_TOP_LEVEL_ARTIFACT_COUNT = 157
SABLE_ARCHIVE_SCOPE_COUNT = 305
SABLE_MIXIN_CONFIG_COUNT = 255
SABLE_COMMON_MIXIN_COUNT = 2258
SABLE_DIRECT_CLIENTLEVEL_MIXIN_COUNT = 10
SABLE_STACK_SHA256 = {
    "prepare": "87df768dd4921f00d5b8c13e02beeb365885f0708d0216a58dfc961ba443192d",
    "validate": "40c05a51c8a02d94692457d73ec3414e456a22dccdc04cbc59d308e8abd29f87",
    "validate_changes": "c1e2e1e8d01e33eebbc20cd18f868bbe28447ccecaa6958f3a527377750320ec",
}
SABLE_RUNTIME_SHA256 = {
    "libraries/net/neoforged/fancymodloader/loader/4.0.43/loader-4.0.43.jar": (
        "ba406038d0ce8242391bb23b9974648748d217b67332c0db620fcabf50edbc37"
    ),
    "libraries/net/fabricmc/sponge-mixin/0.15.2+mixin.0.8.7/"
    "sponge-mixin-0.15.2+mixin.0.8.7.jar": (
        "1d45cfe3ae4a2eab38dc74276803748cf799088986260d6d912e50ddb35d15c5"
    ),
}

IDAS_COMPAT_METADATA = "mods/afterlight-idas-compat.pw.toml"
IDAS_COMPAT_FILENAME = "afterlight_idas_compat-0.1.0+1.21.1.jar"
IDAS_COMPAT_URL = (
    "https://github.com/Luskish/afterlight-idas-compat/releases/download/"
    "v0.1.0/afterlight_idas_compat-0.1.0%2B1.21.1.jar"
)
IDAS_COMPAT_SHA512 = (
    "26a490e6f4e2bde870ada10325dc8f7cad2774b96fa1c35e11a709010de50d126"
    "e0ffb33853a8b5f8fcfa1ced28e2d377b7603ddae056c634e959b760be82c54"
)
IDAS_COMPAT_SHA256 = "458bbaeb5d93923d24b18d69ed7f60dbf3bab9854d50a02671f6ecb7a0338b1b"
IDAS_COMPAT_RESOURCE_SHA256 = {
    "META-INF/neoforge.mods.toml": (
        "ad87e101ddc5672ec917a9431192f0087c30a77270f967970ce586a0aa260bfc"
    ),
    "afterlight_idas_compat.mixins.json": (
        "f1ea036959fde1aed3d5626343b11b328bad56d2174795b8cd9c065e2812fece"
    ),
    "dev/afterlight/idascompat/AfterlightIdasCompat.class": (
        "092d27ea4f2020ad8bc7296101cfd86356637f8ba44420ef5eba3308a387ffb3"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier.class": (
        "bc541ecb87883de9d06da89938048437bbaba1ec9a20d48496454e2ffe6966ce"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer.class": (
        "aa5b7326570380a66f326fb3add930a6466f81cb3c24e25e6e8501e652c5b01e"
    ),
    "dev/afterlight/idascompat/mixin/StructureTemplateAccessor.class": (
        "eeaef3dd31492cabec8db1d8dec79cd5aa0777c4ec4e048a4794fcf4b1361a86"
    ),
    "dev/afterlight/idascompat/mixin/StructureTemplateManagerMixin.class": (
        "15c6edee0810c86656a5d971724c163fdac498fba5699782b4a75cdea7f9d436"
    ),
}
IDAS_COMPAT_LOGGER = "afterlight_idas_compat/STRUCTURE_SANITIZER/"
IDAS_COMPAT_READY_MESSAGE = (
    "AFTERLIGHT_IDAS_COMPAT_READY idas_version=1.13.7+1.21.1-neoforge "
    "artifact_sha256=7f5031dd90ae0b32d7fe5c6c47c877cac1eb95a178bc78d196cb24c17ce82522 "
    "known_compounds=1684 known_templates=100"
)
IDAS_COMPAT_CAMP_MESSAGE = (
    "AFTERLIGHT_IDAS_SANITIZED template=idas:underground_camp/underground_camp1 "
    "replacements=2 "
    "digest=772fe478261727163979ddd04ae3d69220c35b02c09c7046974f96d99d5b0b06"
)
IDAS_COMPAT_BOOT_SANITIZED_MESSAGES = (
    "AFTERLIGHT_IDAS_SANITIZED template=idas:underground_camp/underground_camp_deep1 "
    "replacements=1 "
    "digest=79fe677f9e4c30ea95806383468977e42b46e79dd2f47a7748d089ceacec29b5",
    IDAS_COMPAT_CAMP_MESSAGE,
    "AFTERLIGHT_IDAS_SANITIZED template=idas:tudor_pub/tudor_pub replacements=8 "
    "digest=9e9afaf0cdd2470ef45319d2f18f7205d1939a3165f57daa6c2927f9633fd9d1",
    "AFTERLIGHT_IDAS_SANITIZED template=idas:tudor_pub/tudor_pub_bottom replacements=9 "
    "digest=4dfd6abd605d244e35aa8be0235746a2e48cbf3e9d5e133553810750c2af0cc0",
)


LOG_HEADER = re.compile(
    r"^\[[^\]]+\] \[(?P<thread>[^\]]+)\/(?P<level>[A-Z]+)\] "
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


def _enabled_server_metadata(
    root_path: Path, manifest: dict, provenance: dict
) -> tuple[str, ...]:
    enabled: list[str] = []
    for relative in sorted(manifest["indexed_hashes"]):
        if not relative.endswith(".pw.toml"):
            continue
        metadata = _read_toml(root_path / relative)
        if metadata.get("side") not in ("server", "both"):
            continue
        cached = provenance["cachedFiles"].get(relative)
        if isinstance(cached, dict) and cached.get("optionValue") is True:
            enabled.append(relative)
    return tuple(enabled)


class _ClassReader:
    def __init__(self, payload: bytes):
        self.payload = memoryview(payload)
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if size < 0 or end > len(self.payload):
            raise VerificationError("truncated class file")
        value = self.payload[self.offset:end].tobytes()
        self.offset = end
        return value

    def u1(self) -> int:
        return int.from_bytes(self.read(1), "big")

    def u2(self) -> int:
        return int.from_bytes(self.read(2), "big")

    def u4(self) -> int:
        return int.from_bytes(self.read(4), "big")


def _class_utf8(pool: Sequence[object | None], index: int) -> str:
    if not 0 < index < len(pool) or not isinstance(pool[index], str):
        raise VerificationError(f"invalid class UTF-8 constant index {index}")
    return pool[index]


def _annotation_value(reader: _ClassReader, pool: Sequence[object | None]):
    tag = chr(reader.u1())
    if tag in "BCDFIJSZ":
        return (tag, reader.u2())
    if tag == "s":
        return _class_utf8(pool, reader.u2())
    if tag == "e":
        return ("enum", _class_utf8(pool, reader.u2()), _class_utf8(pool, reader.u2()))
    if tag == "c":
        return ("class", _class_utf8(pool, reader.u2()))
    if tag == "@":
        return _annotation(reader, pool)
    if tag == "[":
        return tuple(_annotation_value(reader, pool) for _ in range(reader.u2()))
    raise VerificationError(f"unsupported annotation value tag {tag!r}")


def _annotation(
    reader: _ClassReader, pool: Sequence[object | None]
) -> tuple[str, dict[str, object]]:
    descriptor = _class_utf8(pool, reader.u2())
    values = {
        _class_utf8(pool, reader.u2()): _annotation_value(reader, pool)
        for _ in range(reader.u2())
    }
    return descriptor, values


def _skip_class_attributes(reader: _ClassReader) -> None:
    for _ in range(reader.u2()):
        reader.read(6)
        for _ in range(reader.u2()):
            reader.read(2)
            reader.read(reader.u4())


def _class_annotations(payload: bytes) -> dict[str, dict[str, object]]:
    reader = _ClassReader(payload)
    if reader.u4() != 0xCAFEBABE:
        raise VerificationError("invalid class file magic")
    reader.read(4)
    pool_count = reader.u2()
    pool: list[object | None] = [None] * pool_count
    index = 1
    while index < pool_count:
        tag = reader.u1()
        if tag == 1:
            try:
                pool[index] = reader.read(reader.u2()).decode("utf-8")
            except UnicodeDecodeError as error:
                raise VerificationError("invalid class UTF-8 constant") from error
        elif tag in (3, 4):
            reader.read(4)
        elif tag in (5, 6):
            reader.read(8)
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            reader.read(2)
        elif tag in (9, 10, 11, 12, 17, 18):
            reader.read(4)
        elif tag == 15:
            reader.read(3)
        else:
            raise VerificationError(f"unsupported class constant tag {tag}")
        index += 1

    reader.read(6)
    reader.read(2 * reader.u2())
    _skip_class_attributes(reader)
    _skip_class_attributes(reader)
    annotations: dict[str, dict[str, object]] = {}
    for _ in range(reader.u2()):
        name = _class_utf8(pool, reader.u2())
        attribute = _ClassReader(reader.read(reader.u4()))
        if name not in ("RuntimeVisibleAnnotations", "RuntimeInvisibleAnnotations"):
            continue
        for _ in range(attribute.u2()):
            descriptor, values = _annotation(attribute, pool)
            annotations[descriptor] = values
        if attribute.offset != len(attribute.payload):
            raise VerificationError(f"unparsed class annotation bytes in {name}")
    return annotations


def _mixin_targets(payload: bytes) -> tuple[bool, bool, tuple[str, ...]]:
    annotations = _class_annotations(payload)
    pseudo = "Lorg/spongepowered/asm/mixin/Pseudo;" in annotations
    mixin = annotations.get("Lorg/spongepowered/asm/mixin/Mixin;")
    if mixin is None:
        return pseudo, False, ()
    values = mixin.get("value", ())
    if not isinstance(values, tuple):
        raise VerificationError("Mixin value annotation is not an array")
    targets = tuple(
        value[1]
        for value in values
        if isinstance(value, tuple) and len(value) == 2 and value[0] == "class"
    )
    return pseudo, True, targets


def _manifest_attributes(payload: bytes) -> dict[str, str]:
    try:
        lines = payload.decode("utf-8").replace("\r\n", "\n").split("\n")
    except UnicodeDecodeError as error:
        raise VerificationError("invalid JAR manifest encoding") from error
    unfolded: list[str] = []
    for line in lines:
        if line.startswith(" ") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return {
        key.strip(): value.strip()
        for line in unfolded
        if ":" in line
        for key, value in (line.split(":", 1),)
    }


def _declared_mixin_configs(archive: zipfile.ZipFile, names: set[str]) -> tuple[str, ...]:
    configs: set[str] = set()
    for metadata_resource in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if metadata_resource not in names:
            continue
        try:
            metadata = tomllib.loads(archive.read(metadata_resource).decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise VerificationError(
                f"cannot parse mixin declarations in {metadata_resource}: {error}"
            ) from error
        declarations = metadata.get("mixins", [])
        if isinstance(declarations, list):
            for declaration in declarations:
                if isinstance(declaration, dict) and isinstance(
                    declaration.get("config"), str
                ):
                    configs.add(declaration["config"])

    if "fabric.mod.json" in names:
        try:
            metadata = json.loads(archive.read("fabric.mod.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError(f"cannot parse fabric.mod.json: {error}") from error
        declarations = metadata.get("mixins", []) if isinstance(metadata, dict) else []
        if isinstance(declarations, list):
            for declaration in declarations:
                if isinstance(declaration, str):
                    configs.add(declaration)
                elif isinstance(declaration, dict):
                    environment = declaration.get("environment", "*")
                    config = declaration.get("config")
                    if environment != "client" and isinstance(config, str):
                        configs.add(config)

    if "quilt.mod.json" in names:
        try:
            metadata = json.loads(archive.read("quilt.mod.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError(f"cannot parse quilt.mod.json: {error}") from error
        loader = metadata.get("quilt_loader", {}) if isinstance(metadata, dict) else {}
        mixins = loader.get("mixin", []) if isinstance(loader, dict) else []
        if isinstance(mixins, str):
            configs.add(mixins)
        elif isinstance(mixins, list):
            configs.update(config for config in mixins if isinstance(config, str))

    if "META-INF/MANIFEST.MF" in names:
        attributes = _manifest_attributes(archive.read("META-INF/MANIFEST.MF"))
        declared = attributes.get("MixinConfigs", "")
        configs.update(config.strip() for config in declared.split(",") if config.strip())
    return tuple(sorted(configs))


def _scan_mixin_archive(
    label: str,
    payload: Path | bytes,
    result: dict[str, object],
    nested_queue: list[tuple[str, Path | bytes]] | None = None,
) -> None:
    try:
        archive_source = payload if isinstance(payload, Path) else io.BytesIO(payload)
        with zipfile.ZipFile(archive_source) as archive:
            names = set(archive.namelist())
            result["archive_scopes"] = int(result["archive_scopes"]) + 1
            for resource in _declared_mixin_configs(archive, names):
                if resource not in names:
                    raise VerificationError(
                        f"declared mixin config is missing: {label}!/{resource}"
                    )
                try:
                    config_payload = archive.read(resource)
                    config = json.loads(config_payload)
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise VerificationError(
                        f"cannot parse declared mixin config {label}!/{resource}: {error}"
                    ) from error
                if not isinstance(config, dict) or not isinstance(config.get("package"), str):
                    continue
                listed = [config.get(key) for key in ("mixins", "client", "server")]
                if not any(isinstance(entries, list) for entries in listed):
                    continue
                config_hashes = result["mixin_config_hashes"]
                if not isinstance(config_hashes, dict):
                    raise VerificationError("invalid mixin config hash accumulator")
                config_hash = _hash_bytes(config_payload, "sha256")
                if resource in config_hashes:
                    continue
                config_hashes[resource] = config_hash
                result["mixin_configs"] = int(result["mixin_configs"]) + 1
                common = config.get("mixins", [])
                if not isinstance(common, list):
                    raise VerificationError(f"invalid common mixin list in {label}!/{resource}")
                package = config["package"].replace(".", "/")
                for mixin_name in common:
                    if not isinstance(mixin_name, str):
                        raise VerificationError(f"invalid common mixin entry in {label}!/{resource}")
                    result["common_mixins"] = int(result["common_mixins"]) + 1
                    class_resource = f"{package}/{mixin_name.replace('.', '/')}.class"
                    if class_resource not in names:
                        raise VerificationError(
                            f"missing common mixin class {label}!/{class_resource}"
                        )
                    class_payload = archive.read(class_resource)
                    pseudo, has_mixin, targets = _mixin_targets(class_payload)
                    if (
                        has_mixin
                        and b"Lnet/minecraft/client/multiplayer/ClientLevel;" in class_payload
                    ):
                        result["direct_clientlevel_mixins"] = (
                            int(result["direct_clientlevel_mixins"]) + 1
                        )
                        if pseudo and (
                            "Lnet/minecraft/client/multiplayer/ClientLevel;" in targets
                        ):
                            candidates = result["pseudo_clientlevel_candidates"]
                            if not isinstance(candidates, list):
                                raise VerificationError("invalid candidate accumulator")
                            candidates.append(
                                (
                                    label,
                                    resource,
                                    mixin_name,
                                    class_resource,
                                    _hash_bytes(class_payload, "sha256"),
                                    targets,
                                )
                            )
            for nested in sorted(name for name in names if name.lower().endswith(".jar")):
                try:
                    nested_payload = archive.read(nested)
                    if zipfile.is_zipfile(io.BytesIO(nested_payload)):
                        nested_scope = (f"{label}!/{nested}", nested_payload)
                        if nested_queue is None:
                            _scan_mixin_archive(*nested_scope, result)
                        else:
                            nested_queue.append(nested_scope)
                except KeyError as error:
                    raise VerificationError(
                        f"cannot read nested archive {label}!/{nested}: {error}"
                    ) from error
    except (OSError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot scan mixin archive {label}: {error}") from error


def verify_sable_source_evidence(root: Path | str, install: Path | str) -> dict:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    manifest = verify_manifest(root_path)
    provenance = verify_install_provenance(root_path, install_path)
    metadata_relatives = _enabled_server_metadata(root_path, manifest, provenance)
    if len(metadata_relatives) != SABLE_ENABLED_METADATA_COUNT:
        raise VerificationError(
            "enabled server metadata count changed: "
            f"expected {SABLE_ENABLED_METADATA_COUNT}, got {len(metadata_relatives)}"
        )
    resolved = {
        relative: _resolve_source_jar(
            root_path, install_path, relative, manifest, provenance
        )
        for relative in metadata_relatives
    }
    unique_archives: dict[Path, str] = {}
    for relative, archive_path in resolved.items():
        unique_archives.setdefault(archive_path.resolve(), relative)
    if len(unique_archives) != SABLE_TOP_LEVEL_ARTIFACT_COUNT:
        raise VerificationError(
            "top-level server artifact count changed: "
            f"expected {SABLE_TOP_LEVEL_ARTIFACT_COUNT}, got {len(unique_archives)}"
        )

    sable_path = resolved[SABLE_METADATA]
    sable_hash = _hash_file(sable_path, "sha256")
    if sable_hash != SABLE_ARTIFACT_SHA256:
        raise VerificationError(
            f"Sable artifact hash mismatch: expected {SABLE_ARTIFACT_SHA256}, got {sable_hash}"
        )
    try:
        with zipfile.ZipFile(sable_path) as archive:
            mixin_payload = archive.read(SABLE_MIXIN_CONFIG)
            mixin_config = json.loads(mixin_payload)
            class_payloads = {
                mixin_name: archive.read(resource)
                for mixin_name, (_, resource, _) in SABLE_MIXIN_CLASSES.items()
            }
    except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot read Sable source evidence: {error}") from error
    mixin_config_hash = _hash_bytes(mixin_payload, "sha256")
    if mixin_config_hash != SABLE_MIXIN_CONFIG_SHA256:
        raise VerificationError(
            "Sable mixin config hash mismatch: "
            f"expected {SABLE_MIXIN_CONFIG_SHA256}, got {mixin_config_hash}"
        )
    common_mixins = mixin_config.get("mixins")
    client_mixins = mixin_config.get("client")
    if not isinstance(common_mixins, list) or not isinstance(client_mixins, list):
        raise VerificationError("Sable mixin config has invalid common or client lists")

    class_hashes: dict[str, str] = {}
    expected_candidates = []
    expected_targets = (
        "Lnet/minecraft/server/level/ServerLevel;",
        "Lnet/minecraft/client/multiplayer/ClientLevel;",
    )
    for mixin_name, (position, resource, expected_hash) in SABLE_MIXIN_CLASSES.items():
        if position >= len(common_mixins) or common_mixins[position] != mixin_name:
            raise VerificationError(
                f"Sable common mixin position changed for {mixin_name} at index {position}"
            )
        if mixin_name in client_mixins:
            raise VerificationError(f"Sable source mixin moved to client list: {mixin_name}")
        payload = class_payloads[mixin_name]
        actual_hash = _hash_bytes(payload, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"Sable mixin class hash mismatch for {resource}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        pseudo, has_mixin, targets = _mixin_targets(payload)
        if not pseudo or not has_mixin or targets != expected_targets:
            raise VerificationError(
                f"Sable mixin annotations changed for {resource}: pseudo={pseudo}, targets={targets}"
            )
        class_hashes[resource] = actual_hash
        expected_candidates.append(
            (
                SABLE_METADATA,
                SABLE_MIXIN_CONFIG,
                mixin_name,
                resource,
                actual_hash,
                targets,
            )
        )

    runtime_hashes: dict[str, str] = {}
    for relative, expected_hash in SABLE_RUNTIME_SHA256.items():
        actual_hash = _hash_file(install_path / relative, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"Sable runtime hash mismatch for {relative}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        runtime_hashes[relative] = actual_hash

    scan: dict[str, object] = {
        "archive_scopes": 0,
        "mixin_configs": 0,
        "common_mixins": 0,
        "direct_clientlevel_mixins": 0,
        "pseudo_clientlevel_candidates": [],
        "mixin_config_hashes": {},
    }
    archive_queue: list[tuple[str, Path | bytes]] = [
        (metadata_relative, archive_path)
        for archive_path, metadata_relative in sorted(
            unique_archives.items(), key=lambda item: item[1]
        )
    ]
    queue_index = 0
    while queue_index < len(archive_queue):
        label, payload = archive_queue[queue_index]
        queue_index += 1
        _scan_mixin_archive(label, payload, scan, archive_queue)
    expected_counts = {
        "archive_scopes": SABLE_ARCHIVE_SCOPE_COUNT,
        "mixin_configs": SABLE_MIXIN_CONFIG_COUNT,
        "common_mixins": SABLE_COMMON_MIXIN_COUNT,
        "direct_clientlevel_mixins": SABLE_DIRECT_CLIENTLEVEL_MIXIN_COUNT,
    }
    for key, expected in expected_counts.items():
        actual = int(scan[key])
        if actual != expected:
            raise VerificationError(
                f"Sable exhaustive {key} count changed: expected {expected}, got {actual}"
            )
    candidates = tuple(scan["pseudo_clientlevel_candidates"])
    if candidates != tuple(expected_candidates):
        raise VerificationError(
            "Sable exhaustive @Pseudo ClientLevel candidate set changed: "
            f"expected {tuple(expected_candidates)}, got {candidates}"
        )

    return {
        "artifact_sha256": sable_hash,
        "mixin_config_sha256": mixin_config_hash,
        "mixin_class_sha256": class_hashes,
        "runtime_sha256": runtime_hashes,
        "enabled_metadata": len(metadata_relatives),
        "top_level_artifacts": len(unique_archives),
        "archive_scopes": int(scan["archive_scopes"]),
        "mixin_configs": int(scan["mixin_configs"]),
        "common_mixins": int(scan["common_mixins"]),
        "direct_clientlevel_mixins": int(scan["direct_clientlevel_mixins"]),
        "pseudo_clientlevel_candidates": candidates,
    }


def verify_idas_compat_source_evidence(root: Path | str, install: Path | str) -> dict:
    root_path = Path(root).resolve()
    install_path = Path(install).resolve()
    metadata = _read_toml(root_path / IDAS_COMPAT_METADATA)
    if metadata.get("filename") != IDAS_COMPAT_FILENAME:
        raise VerificationError("IDAS compat filename changed")
    if metadata.get("side") != "both":
        raise VerificationError("IDAS compat side must remain both")
    download = metadata.get("download")
    if not isinstance(download, dict):
        raise VerificationError("IDAS compat metadata has no download table")
    expected_download = {
        "url": IDAS_COMPAT_URL,
        "hash-format": "sha512",
        "hash": IDAS_COMPAT_SHA512,
    }
    if download != expected_download:
        raise VerificationError(
            f"IDAS compat download provenance changed: {download}"
        )

    artifact = resolve_source_jar(root_path, install_path, IDAS_COMPAT_METADATA)
    artifact_sha256 = _hash_file(artifact, "sha256")
    if artifact_sha256 != IDAS_COMPAT_SHA256:
        raise VerificationError(
            "IDAS compat artifact SHA-256 mismatch: "
            f"expected {IDAS_COMPAT_SHA256}, got {artifact_sha256}"
        )
    try:
        with zipfile.ZipFile(artifact) as archive:
            names = set(archive.namelist())
            forbidden = sorted(
                name
                for name in names
                if name.endswith(".nbt")
                or name.startswith("data/idas/")
                or name.lower().endswith(".jar")
            )
            if forbidden:
                raise VerificationError(
                    f"IDAS compat artifact contains forbidden payloads: {forbidden}"
                )
            resources = {
                resource: archive.read(resource)
                for resource in IDAS_COMPAT_RESOURCE_SHA256
            }
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot inspect IDAS compat artifact: {error}") from error

    resource_hashes = {
        resource: _hash_bytes(payload, "sha256")
        for resource, payload in resources.items()
    }
    if resource_hashes != IDAS_COMPAT_RESOURCE_SHA256:
        raise VerificationError(
            f"IDAS compat resource hashes changed: {resource_hashes}"
        )
    try:
        mixin_config = json.loads(resources["afterlight_idas_compat.mixins.json"])
        mod_metadata = tomllib.loads(
            resources["META-INF/neoforge.mods.toml"].decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        raise VerificationError(f"cannot parse IDAS compat metadata: {error}") from error
    if mixin_config.get("package") != "dev.afterlight.idascompat.mixin":
        raise VerificationError("IDAS compat mixin package changed")
    if mixin_config.get("mixins") != [
        "StructureTemplateAccessor",
        "StructureTemplateManagerMixin",
    ]:
        raise VerificationError("IDAS compat mixin set changed")
    if "client" in mixin_config:
        raise VerificationError("IDAS compat gained a client-only mixin list")
    mods = mod_metadata.get("mods")
    if not isinstance(mods, list) or len(mods) != 1:
        raise VerificationError("IDAS compat mod metadata shape changed")
    if mods[0].get("modId") != "afterlight_idas_compat" or mods[0].get(
        "version"
    ) != "0.1.0+1.21.1":
        raise VerificationError("IDAS compat mod identity changed")
    dependencies = mod_metadata.get("dependencies", {}).get(
        "afterlight_idas_compat", []
    )
    idas_dependencies = [
        dependency
        for dependency in dependencies
        if isinstance(dependency, dict) and dependency.get("modId") == "idas"
    ]
    if idas_dependencies != [
        {
            "modId": "idas",
            "type": "optional",
            "versionRange": "[1.13.7+1.21.1-neoforge]",
            "ordering": "AFTER",
            "side": "BOTH",
        }
    ]:
        raise VerificationError("IDAS compat IDAS dependency pin changed")
    return {
        "artifact_sha256": artifact_sha256,
        "artifact_sha512": IDAS_COMPAT_SHA512,
        "resource_sha256": resource_hashes,
    }


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
                thread=current_match.group("thread"),
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


def _record_is(
    record: LogRecord, level: str, logger: str, message: str
) -> bool:
    return (
        record.level == level
        and record.logger == logger
        and record.message == message
    )


def _normalized_stack_payload(record: LogRecord) -> bytes:
    frames = []
    for line in record.text.splitlines():
        if not line.startswith("\tat "):
            continue
        normalized = re.sub(r" (?:~)?\[[^\]]*\]$", "", line)
        normalized = re.sub(r"jar%23\d+", "jar%23N", normalized)
        normalized = re.sub(r"\$Anonymous\$[0-9a-fA-F]+", "$Anonymous$<ANON>", normalized)
        frames.append(normalized)
    return "\n".join(frames).encode("utf-8")


def _require_stack_hash(record: LogRecord, expected: str, label: str) -> None:
    actual = _hash_bytes(_normalized_stack_payload(record), "sha256")
    if actual != expected:
        raise VerificationError(
            f"RuntimeDistCleaner {label} normalized stack hash changed: "
            f"expected {expected}, got {actual}"
        )


def _require_single_line(record: LogRecord, label: str) -> None:
    if len(record.text.splitlines()) != 1:
        raise VerificationError(f"{label} record gained unreviewed continuation context")


def project_sable_error_requirement() -> LogAllowance:
    return LogAllowance(
        label="RuntimeDistCleaner Sable ClientLevel errors",
        level="ERROR",
        logger="net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
        message=RUNTIME_DIST_CLEANER_MESSAGE,
        count=12,
    )


def _unique_record_index(
    records: Sequence[LogRecord],
    level: str,
    logger: str,
    message: str,
    label: str,
) -> int:
    indices = [
        index
        for index, record in enumerate(records)
        if _record_is(record, level, logger, message)
    ]
    if len(indices) != 1:
        raise VerificationError(
            f"RuntimeDistCleaner {label} anchor count changed: expected 1, got {len(indices)}"
        )
    return indices[0]


def _validate_sable_debug_records(
    records: Sequence[LogRecord], requirement: LogAllowance
) -> tuple[int, ...]:
    indices = [
        index
        for index, record in enumerate(records)
        if _record_is(
            record, requirement.level, requirement.logger, requirement.message
        )
    ]
    if len(indices) != requirement.count:
        raise VerificationError(
            "RuntimeDistCleaner debug provenance count mismatch: "
            f"expected {requirement.count}, got {len(indices)}"
        )
    for index in indices:
        record = records[index]
        _require_single_line(record, "RuntimeDistCleaner")
        if record.thread != "main":
            raise VerificationError(
                f"RuntimeDistCleaner record moved to unreviewed thread {record.thread}"
            )

    access_logger = "net.neoforged.accesstransformer.AccessTransformer/AXFORM"
    access_field = (
        "Transforming net.minecraft.client.multiplayer.ClientLevel FIELD entityStorage "
        "to access PUBLIC and LEAVE"
    )
    access_method = (
        "Transforming net.minecraft.client.multiplayer.ClientLevel METHOD "
        "getEntities()Lnet/minecraft/world/level/entity/LevelEntityGetter; "
        "to access PUBLIC and LEAVE"
    )
    catch_exception = f"java.lang.RuntimeException: {RUNTIME_DIST_CLEANER_MESSAGE}"
    mixin_load_warning = (
        "Error loading class: net/minecraft/client/multiplayer/ClientLevel "
        f"(java.lang.RuntimeException: {RUNTIME_DIST_CLEANER_MESSAGE})"
    )
    source_mixins = tuple(SABLE_MIXIN_CLASSES)

    for position, index in enumerate(indices[:9]):
        if index < 2 or index + 1 >= len(records):
            raise VerificationError("RuntimeDistCleaner lifecycle context is truncated")
        if not _record_is(records[index - 2], "DEBUG", access_logger, access_field):
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} lost ClientLevel field context"
            )
        if not _record_is(records[index - 1], "DEBUG", access_logger, access_method):
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} lost ClientLevel method context"
            )
        catching = records[index + 1]
        if not _record_is(catching, "TRACE", "mixin/CATCHING", "Catching"):
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} lost Mixin catch context"
            )
        if catch_exception not in catching.text:
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} exception changed"
            )

    for position, mixin_name in enumerate(source_mixins):
        index = indices[position]
        _require_stack_hash(
            records[index + 1], SABLE_STACK_SHA256["prepare"], f"prepare {mixin_name}"
        )
        segment_end = indices[position + 1]
        expected_marker = (
            "Skipping virtual target net.minecraft.client.multiplayer.ClientLevel for "
            f"sable.mixins.json:{mixin_name} from mod sable"
        )
        markers = [
            record.message
            for record in records[index + 2 : segment_end]
            if record.logger == "mixin/"
            and record.message.startswith(
                "Skipping virtual target net.minecraft.client.multiplayer.ClientLevel for "
                "sable.mixins.json:"
            )
        ]
        if markers != [expected_marker]:
            raise VerificationError(
                f"RuntimeDistCleaner prepare source context changed for {mixin_name}: {markers}"
            )

    access_logger = "net.neoforged.accesstransformer.AccessTransformer/AXFORM"
    p3_first = _unique_record_index(
        records,
        "TRACE",
        "mixin/",
        "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
        "ServerConnectionListenerMixin$1 to metadata cache",
        "P3 first start",
    )
    p3_second = _unique_record_index(
        records,
        "TRACE",
        "mixin/",
        "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
        "ServerConnectionListenerMixin$2 to metadata cache",
        "P3 second start",
    )
    if p3_second != p3_first + 1:
        raise VerificationError(
            "RuntimeDistCleaner P3 named metadata anchors are no longer adjacent"
        )
    windows = (
        (
            "P1",
            "Added class metadata for dev/ryanhcode/sable/api/command/"
            "SubLevelArgumentType$Info to metadata cache",
            (
                "DEBUG",
                access_logger,
                "Transforming net.minecraft.world.level.pathfinder.NodeEvaluator "
                "FIELD mob to access PUBLIC and LEAVE",
            ),
        ),
        (
            "P2",
            "Added class metadata for dev/ryanhcode/sable/sublevel/entity_collision/"
            "SubLevelEntityCollision$FirstCollisionInfo to metadata cache",
            (
                "TRACE",
                "mixin/",
                "Added class metadata for net/minecraft/BlockUtil$FoundRectangle "
                "to metadata cache",
            ),
        ),
        (
            "P3",
            "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
            "ServerConnectionListenerMixin$2 to metadata cache",
            (
                "DEBUG",
                "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
                "Removing method: com/simibubi/create/foundation/blockEntity/"
                "CachedRenderBBBlockEntity.getRenderBoundingBox()"
                "Lnet/minecraft/world/phys/AABB;",
            ),
        ),
    )
    for pair, (window_name, start_message, end_identity) in enumerate(windows):
        start_index = _unique_record_index(
            records, "TRACE", "mixin/", start_message, f"{window_name} start"
        )
        end_index = _unique_record_index(
            records, *end_identity, f"{window_name} end"
        )
        validate_index = indices[3 + pair * 2]
        changes_index = indices[4 + pair * 2]
        window_errors = tuple(
            index for index in indices if start_index < index < end_index
        )
        if window_errors != (validate_index, changes_index):
            raise VerificationError(
                f"RuntimeDistCleaner {window_name} source window changed: {window_errors}"
            )
        _require_stack_hash(
            records[validate_index + 1],
            SABLE_STACK_SHA256["validate"],
            f"{window_name} validate {source_mixins[pair]}",
        )
        _require_stack_hash(
            records[changes_index + 1],
            SABLE_STACK_SHA256["validate_changes"],
            f"{window_name} validate changes {source_mixins[pair]}",
        )
        mixin_name = source_mixins[pair]
        for phase_index in (validate_index, changes_index):
            if phase_index + 3 >= len(records):
                raise VerificationError(
                    f"RuntimeDistCleaner validation context is truncated for {mixin_name}"
                )
            if not _record_is(
                records[phase_index + 2], "WARN", "mixin/", mixin_load_warning
            ):
                raise VerificationError(
                    f"RuntimeDistCleaner validation warning changed for {mixin_name}"
                )
            if not _record_is(
                records[phase_index + 3],
                "TRACE",
                "mixin/",
                "Added class metadata for net/minecraft/client/multiplayer/ClientLevel "
                "to metadata cache",
            ):
                raise VerificationError(
                    f"RuntimeDistCleaner validation metadata context changed for {mixin_name}"
                )

    for position, mixin_name in enumerate(source_mixins):
        index = indices[9 + position]
        expected_source = (
            f"Mixing {mixin_name} from sable.mixins.json into "
            "net.minecraft.server.level.ServerLevel"
        )
        if index < 1 or index + 1 >= len(records):
            raise VerificationError(
                f"RuntimeDistCleaner application context is truncated for {mixin_name}"
            )
        if not _record_is(records[index - 1], "DEBUG", "mixin/", expected_source):
            raise VerificationError(
                f"RuntimeDistCleaner application source context changed for {mixin_name}"
            )
        if not _record_is(records[index + 1], "WARN", "mixin/", mixin_load_warning):
            raise VerificationError(
                f"RuntimeDistCleaner application warning changed for {mixin_name}"
            )
    return tuple(indices)


def _error_fatal_projection(
    records: Sequence[LogRecord],
) -> tuple[tuple[str, str, str], ...]:
    return tuple(
        (record.level, record.logger, record.message)
        for record in records
        if record.level in ("ERROR", "FATAL")
    )


def verify_sable_runtime_dist_cleaner_evidence(
    root: Path | str,
    install: Path | str,
    latest_text: str,
    debug_text: str,
    nonce: str,
    status: int,
) -> DedicatedErrorEvidence:
    verify_sable_source_evidence(root, install)
    validate_boot_markers(latest_text, nonce, status)
    validate_boot_markers(debug_text, nonce, status)
    latest_records = parse_log_records(latest_text)
    debug_records = parse_log_records(debug_text)
    latest_projection = _error_fatal_projection(latest_records)
    debug_projection = _error_fatal_projection(debug_records)
    if latest_projection != debug_projection:
        raise VerificationError(
            "latest.log and debug.log ordered ERROR/FATAL projections differ"
        )

    requirement = project_sable_error_requirement()
    latest_indices = tuple(
        index
        for index, record in enumerate(latest_records)
        if _record_is(
            record, requirement.level, requirement.logger, requirement.message
        )
    )
    if len(latest_indices) != requirement.count:
        raise VerificationError(
            "RuntimeDistCleaner latest.log count mismatch: "
            f"expected {requirement.count}, got {len(latest_indices)}"
        )
    debug_indices = _validate_sable_debug_records(debug_records, requirement)
    return DedicatedErrorEvidence(
        label=requirement.label,
        latest_record_indices=latest_indices,
        debug_record_indices=debug_indices,
    )


def _idas_compat_audit_projection(
    records: Sequence[LogRecord],
) -> tuple[tuple[str, str], ...]:
    return tuple(
        (record.level, record.message)
        for record in records
        if record.logger == IDAS_COMPAT_LOGGER
        and record.level in ("INFO", "WARN", "ERROR", "FATAL")
    )


def verify_idas_compat_runtime_evidence(
    root: Path | str,
    install: Path | str,
    latest_text: str,
    debug_text: str,
) -> Counter[str]:
    verify_idas_compat_source_evidence(root, install)
    latest_records = parse_log_records(latest_text)
    debug_records = parse_log_records(debug_text)
    latest_projection = _idas_compat_audit_projection(latest_records)
    debug_projection = _idas_compat_audit_projection(debug_records)
    if latest_projection != debug_projection:
        raise VerificationError(
            "latest.log and debug.log IDAS compat audit projections differ"
        )

    for label, records in (("latest.log", latest_records), ("debug.log", debug_records)):
        air_errors = [
            record
            for record in records
            if _record_is(
                record,
                "ERROR",
                "net.minecraft.world.item.ItemStack/",
                ITEMSTACK_AIR_MESSAGE,
            )
        ]
        if air_errors:
            raise VerificationError(
                f"{label} contains {len(air_errors)} generic ItemStack air ERROR records"
            )

    latest_audits = [
        (index, record)
        for index, record in enumerate(latest_records)
        if record.logger == IDAS_COMPAT_LOGGER
        and record.level in ("INFO", "WARN", "ERROR", "FATAL")
    ]
    invalid_levels = [
        record for _, record in latest_audits if record.level != "INFO"
    ]
    if invalid_levels:
        raise VerificationError(
            "IDAS compat emitted an unreviewed non-INFO audit record"
        )
    ready_indices = [
        index
        for index, record in latest_audits
        if record.message == IDAS_COMPAT_READY_MESSAGE
    ]
    if len(ready_indices) != 1:
        raise VerificationError(
            f"IDAS compat READY count mismatch: expected 1, got {len(ready_indices)}"
        )
    sanitized_pattern = re.compile(
        r"AFTERLIGHT_IDAS_SANITIZED template=(?P<template>idas:[a-z0-9_./-]+) "
        r"replacements=(?P<replacements>[1-9][0-9]*) digest=(?P<digest>[0-9a-f]{64})"
    )
    sanitized: list[tuple[int, LogRecord, re.Match[str]]] = []
    for index, record in latest_audits:
        if record.message == IDAS_COMPAT_READY_MESSAGE:
            continue
        match = sanitized_pattern.fullmatch(record.message)
        if match is None:
            raise VerificationError(
                f"unreviewed IDAS compat audit record: {record.message}"
            )
        sanitized.append((index, record, match))
    if any(index <= ready_indices[0] for index, _, _ in sanitized):
        raise VerificationError("IDAS compat SANITIZED record preceded READY")
    template_counts = Counter(match.group("template") for _, _, match in sanitized)
    duplicates = sorted(
        template for template, count in template_counts.items() if count != 1
    )
    if duplicates:
        raise VerificationError(
            f"IDAS compat sanitized a template more than once: {duplicates}"
        )
    sanitized_messages = tuple(record.message for _, record, _ in sanitized)
    if sanitized_messages != IDAS_COMPAT_BOOT_SANITIZED_MESSAGES:
        raise VerificationError(
            "IDAS compat clean-boot SANITIZED audit sequence changed: "
            f"{sanitized_messages}"
        )
    camp_count = sum(
        record.message == IDAS_COMPAT_CAMP_MESSAGE for _, record, _ in sanitized
    )
    if camp_count != 1:
        raise VerificationError(
            f"IDAS camp1 SANITIZED audit count mismatch: expected 1, got {camp_count}"
        )
    return Counter(
        {
            "IDAS compat READY": 1,
            "IDAS camp1 sanitized": 1,
            "IDAS sanitized templates": len(sanitized),
        }
    )


def validate_error_records(
    log_text: str,
    allowances: Iterable[LogAllowance],
    consumed_record_indices: Iterable[int] = (),
) -> Counter[str]:
    allowance_list = tuple(allowances)
    records = parse_log_records(log_text)
    consumed = frozenset(consumed_record_indices)
    for index in consumed:
        if not 0 <= index < len(records):
            raise VerificationError(f"consumed ERROR record index is invalid: {index}")
        if records[index].level not in ("ERROR", "FATAL"):
            raise VerificationError(f"consumed record {index} is not ERROR or FATAL")
    observed: Counter[str] = Counter()
    for index, record in enumerate(records):
        if record.level not in ("ERROR", "FATAL"):
            continue
        if index in consumed:
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
    debug_path = install_path / "logs" / "debug.log"
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        debug_text = debug_path.read_text(encoding="utf-8", errors="replace")
    except OSError as error:
        raise VerificationError(
            f"cannot read authoritative current logs {log_path} and {debug_path}: {error}"
        ) from error
    sable = verify_sable_runtime_dist_cleaner_evidence(
        root_path,
        install_path,
        log_text,
        debug_text,
        nonce,
        status,
    )
    audits = verify_idas_compat_runtime_evidence(
        root_path, install_path, log_text, debug_text
    )
    allowances = project_error_allowances()
    errors = validate_error_records(
        log_text, allowances, sable.latest_record_indices
    )
    debug_errors = validate_error_records(
        debug_text, allowances, sable.debug_record_indices
    )
    errors[sable.label] = len(sable.latest_record_indices)
    debug_errors[sable.label] = len(sable.debug_record_indices)
    if debug_errors != errors:
        raise VerificationError(
            f"latest.log and debug.log ERROR identities differ: {errors} != {debug_errors}"
        )
    warnings = validate_known_residual_warnings(log_text)
    return {"errors": errors, "warnings": warnings, "audits": audits}


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
