#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import stat
import sys
import tomllib
from pathlib import Path, PurePath


ALLOWED_SIDES = {"client", "server", "both"}
STREAM_CHUNK_SIZE = 1024 * 1024


def _require_directory(path, label):
    path = Path(path)
    try:
        path_status = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unreadable: {path}") from error
    if stat.S_ISLNK(path_status.st_mode) or not stat.S_ISDIR(path_status.st_mode):
        raise ValueError(f"{label} is not a regular directory: {path}")
    return path


def _require_regular_file(path, label):
    try:
        file_status = path.lstat()
    except OSError as error:
        raise ValueError(f"{label} is unreadable: {path}") from error
    if not stat.S_ISREG(file_status.st_mode):
        raise ValueError(f"{label} is not a regular file: {path}")


def _sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(STREAM_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def expected_mod_inventory(mods_dir):
    metadata_directory = _require_directory(mods_dir, "Packwiz mods directory")
    metadata_paths = sorted(metadata_directory.glob("*.pw.toml"))
    if not metadata_paths:
        raise ValueError("Packwiz mods directory contains no metadata")

    client_required = set()
    server_only = set()
    filenames = {}
    for metadata_path in metadata_paths:
        _require_regular_file(metadata_path, "Packwiz mod metadata")
        try:
            with metadata_path.open("rb") as source:
                metadata = tomllib.load(source)
        except (OSError, tomllib.TOMLDecodeError) as error:
            raise ValueError(f"invalid Packwiz metadata: {metadata_path}") from error

        side = metadata.get("side")
        if side not in ALLOWED_SIDES:
            raise ValueError(
                f"Packwiz metadata requires a deliberate side: {metadata_path.name}"
            )
        filename = metadata.get("filename")
        if (
            not isinstance(filename, str)
            or not filename
            or PurePath(filename).name != filename
            or "/" in filename
            or "\\" in filename
        ):
            raise ValueError(f"invalid mod filename in {metadata_path.name}")
        if not filename.casefold().endswith(".jar"):
            raise ValueError(f"mod filename must end with .jar: {filename}")

        collision_key = filename.casefold()
        if collision_key in filenames:
            raise ValueError(
                "duplicate mod filename: "
                f"{filenames[collision_key]} and {metadata_path.name}"
            )
        filenames[collision_key] = metadata_path.name
        if side == "server":
            server_only.add(filename)
        else:
            client_required.add(filename)

    return client_required, server_only


def validate_client_install(instance_dir, mods_dir):
    instance_directory = _require_directory(instance_dir, "client instance directory")
    installed_mods_directory = _require_directory(
        instance_directory / "mods", "installed client mods directory"
    )
    client_required, server_only = expected_mod_inventory(mods_dir)

    actual_paths = {}
    for entry in os.scandir(installed_mods_directory):
        if not entry.name.casefold().endswith(".jar"):
            continue
        path = Path(entry.path)
        _require_regular_file(path, "installed client mod")
        collision_key = entry.name.casefold()
        if collision_key in actual_paths:
            raise ValueError(f"duplicate installed client mod: {entry.name}")
        actual_paths[collision_key] = path

    required_by_key = {name.casefold(): name for name in client_required}
    server_by_key = {name.casefold(): name for name in server_only}
    actual_keys = set(actual_paths)

    present_server_only = sorted(actual_keys & set(server_by_key))
    if present_server_only:
        raise ValueError(
            f"server-only mod present in client: {server_by_key[present_server_only[0]]}"
        )
    missing = sorted(set(required_by_key) - actual_keys)
    if missing:
        raise ValueError(f"missing client mod: {required_by_key[missing[0]]}")
    unexpected = sorted(actual_keys - set(required_by_key))
    if unexpected:
        raise ValueError(f"unexpected client mod: {actual_paths[unexpected[0]].name}")

    digest_lines = []
    for filename in sorted(client_required):
        path = actual_paths[filename.casefold()]
        digest_lines.append(f"{_sha256_file(path)}  {filename}\n")
    modset_sha256 = hashlib.sha256(
        "".join(digest_lines).encode("utf-8")
    ).hexdigest()
    return {
        "client_mod_count": len(client_required),
        "server_only_count": len(server_only),
        "modset_sha256": modset_sha256,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate an AFTERLIGHT client install")
    parser.add_argument("--instance-dir", required=True)
    parser.add_argument("--mods-dir", required=True)
    args = parser.parse_args(argv)
    summary = validate_client_install(args.instance_dir, args.mods_dir)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
