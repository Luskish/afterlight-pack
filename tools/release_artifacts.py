#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import re
import stat
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_PRISM_NAMES = (
    ".minecraft/packwiz-installer-bootstrap.jar",
    "instance.cfg",
    "mmc-pack.json",
)
APPROVED_PRISM_JAR = ".minecraft/packwiz-installer-bootstrap.jar"
PRISM_MINECRAFT_VERSION = "1.21.1"
PRISM_NEOFORGE_VERSION = "21.1.248"
FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
FILE_MODE = stat.S_IFREG | 0o644
DEFLATE_LEVEL = 9
UTF8_FLAG = 0x800


def _instance_config(pack_url):
    return (
        "InstanceType=OneSix\n"
        "name=AFTERLIGHT\n"
        "iconKey=default\n"
        "OverrideCommands=true\n"
        f'PreLaunchCommand="$INST_JAVA" -jar packwiz-installer-bootstrap.jar {pack_url}\n'
    ).encode("utf-8")


def _mmc_pack(minecraft_version, neoforge_version):
    payload = {
        "components": [
            {
                "important": True,
                "uid": "net.minecraft",
                "version": minecraft_version,
            },
            {"uid": "net.neoforged", "version": neoforge_version},
        ],
        "formatVersion": 1,
    }
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


def _validate_archive_name(name):
    if not name:
        raise ValueError("archive entry name is empty")
    if "\\" in name:
        raise ValueError(f"archive entry uses a backslash: {name!r}")
    if name.startswith("/") or PurePosixPath(name).is_absolute():
        raise ValueError(f"archive entry uses an absolute path: {name!r}")
    parts = name.split("/")
    if ".." in parts:
        raise ValueError(f"archive entry uses parent traversal: {name!r}")
    if any(part in {"", "."} for part in parts):
        raise ValueError(f"archive entry is not canonical: {name!r}")
    if PurePosixPath(name).as_posix() != name:
        raise ValueError(f"archive entry is not canonical: {name!r}")


def _normalized_zip_info(name):
    _validate_archive_name(name)
    info = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.create_version = 20
    info.extract_version = 20
    info.external_attr = FILE_MODE << 16
    info.internal_attr = 0
    info.flag_bits = 0
    info.extra = b""
    info.comment = b""
    return info


def _write_prism_archive(archive_path, entries):
    with zipfile.ZipFile(
        archive_path,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=DEFLATE_LEVEL,
        strict_timestamps=True,
    ) as archive:
        for name in sorted(entries):
            archive.writestr(
                _normalized_zip_info(name),
                entries[name],
                compress_type=zipfile.ZIP_DEFLATED,
                compresslevel=DEFLATE_LEVEL,
            )


def build_prism_archive(
    bootstrap_path,
    output_path,
    pack_url,
    minecraft_version,
    neoforge_version,
):
    bootstrap_path = Path(bootstrap_path)
    output_path = Path(output_path)
    if not bootstrap_path.is_file():
        raise ValueError(f"bootstrap JAR is not a regular file: {bootstrap_path}")

    entries = {
        APPROVED_PRISM_JAR: bootstrap_path.read_bytes(),
        "instance.cfg": _instance_config(pack_url),
        "mmc-pack.json": _mmc_pack(minecraft_version, neoforge_version),
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.unlink(missing_ok=True)

    with tempfile.NamedTemporaryFile(
        prefix=f".{output_path.name}.",
        suffix=".tmp",
        dir=output_path.parent,
        delete=False,
    ) as temporary_file:
        temporary_path = Path(temporary_file.name)

    try:
        _write_prism_archive(temporary_path, entries)
        inspect_prism_archive(
            temporary_path,
            pack_url,
            hashlib.sha256(entries[APPROVED_PRISM_JAR]).hexdigest(),
        )
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)

    return output_path


def _validate_zip_metadata(info):
    if info.date_time != FIXED_TIMESTAMP:
        raise ValueError(f"archive entry timestamp is not normalized: {info.filename!r}")
    if info.create_system != 3:
        raise ValueError(f"archive entry is not Unix metadata: {info.filename!r}")
    if info.external_attr != FILE_MODE << 16:
        raise ValueError(
            f"archive entry external attributes are not normalized: {info.filename!r}"
        )
    if info.compress_type != zipfile.ZIP_DEFLATED:
        raise ValueError(f"archive entry is not deflated: {info.filename!r}")
    if info.flag_bits & UTF8_FLAG:
        raise ValueError(f"ASCII archive entry has the UTF-8 flag set: {info.filename!r}")
    if info.flag_bits != 0:
        raise ValueError(f"archive entry has unsupported flags: {info.filename!r}")
    if info.extra or info.comment:
        raise ValueError(f"archive entry has non-normalized metadata: {info.filename!r}")


def _validate_sha256(value):
    if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        raise ValueError("bootstrap SHA-256 must be exactly 64 hexadecimal characters")
    return value.lower()


def inspect_prism_archive(archive_path, pack_url, bootstrap_sha256):
    archive_path = Path(archive_path)
    expected_bootstrap_sha256 = _validate_sha256(bootstrap_sha256)

    with zipfile.ZipFile(archive_path) as archive:
        if archive.comment:
            raise ValueError("Prism archive comment is not allowed")

        infos = archive.infolist()
        names = []
        seen_names = set()
        for info in infos:
            _validate_archive_name(info.filename)
            if info.filename in seen_names:
                raise ValueError(f"duplicate archive entry: {info.filename!r}")
            seen_names.add(info.filename)
            names.append(info.filename)

        jar_entries = [name for name in names if name.lower().endswith(".jar")]
        disallowed_jars = [name for name in jar_entries if name != APPROVED_PRISM_JAR]
        if disallowed_jars:
            raise ValueError(f"disallowed JAR in Prism archive: {disallowed_jars[0]!r}")
        if jar_entries != [APPROVED_PRISM_JAR]:
            raise ValueError("Prism archive must contain exactly one approved JAR")
        if tuple(names) != EXPECTED_PRISM_NAMES:
            raise ValueError(
                "Prism archive entries must be exactly sorted as "
                f"{EXPECTED_PRISM_NAMES!r}"
            )

        for info in infos:
            _validate_zip_metadata(info)

        bootstrap_bytes = archive.read(APPROVED_PRISM_JAR)
        actual_bootstrap_sha256 = hashlib.sha256(bootstrap_bytes).hexdigest()
        if actual_bootstrap_sha256 != expected_bootstrap_sha256:
            raise ValueError(
                "bootstrap SHA-256 mismatch: "
                f"expected {expected_bootstrap_sha256}, got {actual_bootstrap_sha256}"
            )

        expected_instance_config = _instance_config(pack_url)
        if archive.read("instance.cfg") != expected_instance_config:
            raise ValueError("instance.cfg does not use the exact Packwiz launch command")

        expected_mmc_pack = _mmc_pack(
            PRISM_MINECRAFT_VERSION,
            PRISM_NEOFORGE_VERSION,
        )
        if archive.read("mmc-pack.json") != expected_mmc_pack:
            raise ValueError("mmc-pack.json does not use the exact loader versions")

    return {
        "archive": str(archive_path),
        "bootstrap_sha256": actual_bootstrap_sha256,
        "entries": names,
        "entry_count": len(names),
        "jar_entries": jar_entries,
        "pack_url": pack_url,
    }


def _parser():
    parser = argparse.ArgumentParser(description="Build and inspect AFTERLIGHT artifacts")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build-prism")
    build_parser.add_argument("--bootstrap", required=True)
    build_parser.add_argument("--output", required=True)
    build_parser.add_argument("--pack-url", required=True)
    build_parser.add_argument("--minecraft-version", required=True)
    build_parser.add_argument("--neoforge-version", required=True)

    inspect_parser = subparsers.add_parser("inspect-prism")
    inspect_parser.add_argument("--archive", required=True)
    inspect_parser.add_argument("--pack-url", required=True)
    inspect_parser.add_argument("--bootstrap-sha256", required=True)
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.command == "build-prism":
        archive_path = build_prism_archive(
            args.bootstrap,
            args.output,
            args.pack_url,
            args.minecraft_version,
            args.neoforge_version,
        )
        print(json.dumps({"archive": str(archive_path)}, sort_keys=True))
        return 0

    summary = inspect_prism_archive(
        args.archive,
        args.pack_url,
        args.bootstrap_sha256,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
