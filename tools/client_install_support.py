#!/usr/bin/env python3

import argparse
import hashlib
import json
import os
import stat
import sys
import tomllib
from pathlib import Path, PurePath, PurePosixPath


ALLOWED_SIDES = {"client", "server", "both"}
ALLOWED_HASHES = {"sha1", "sha256", "sha512"}
STREAM_CHUNK_SIZE = 1024 * 1024
INSTALLER_INFRASTRUCTURE_FILES = frozenset(
    {
        "packwiz-installer-bootstrap.jar",
        "packwiz-installer.jar",
        "packwiz.json",
    }
)


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


def _hash_file(path, hash_name):
    digest = hashlib.new(hash_name)
    with path.open("rb") as source:
        while chunk := source.read(STREAM_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file(path):
    return _hash_file(path, "sha256")


def _load_toml(path, label):
    _require_regular_file(path, label)
    try:
        with path.open("rb") as source:
            document = tomllib.load(source)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ValueError(f"invalid {label}: {path}") from error
    if not isinstance(document, dict):
        raise ValueError(f"invalid {label}: {path}")
    return document


def _relative_pack_path(value, label):
    if not isinstance(value, str) or not value or "\\" in value or "//" in value:
        raise ValueError(f"invalid {label}")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value or any(
        part in {"", ".", ".."} for part in path.parts
    ):
        raise ValueError(f"invalid {label}")
    return value


def _expected_packwiz_payload(pack_root):
    root = _require_directory(pack_root, "Packwiz source root")
    pack = _load_toml(root / "pack.toml", "Packwiz pack metadata")
    index_reference = pack.get("index")
    if not isinstance(index_reference, dict):
        raise ValueError("Packwiz pack metadata has no index")
    index_relative_path = _relative_pack_path(
        index_reference.get("file"), "Packwiz index path"
    )
    index_hash_name = index_reference.get("hash-format")
    if index_hash_name not in ALLOWED_HASHES:
        raise ValueError("Packwiz index reference uses an unsupported hash")
    index_hash = index_reference.get("hash")
    if not isinstance(index_hash, str) or index_hash != _hash_file(
        root / index_relative_path, index_hash_name
    ):
        raise ValueError("Packwiz index hash does not match pack.toml")

    index = _load_toml(root / index_relative_path, "Packwiz index")
    payload_hash_name = index.get("hash-format")
    if payload_hash_name not in ALLOWED_HASHES:
        raise ValueError("Packwiz index uses an unsupported hash")
    records = index.get("files")
    if not isinstance(records, list) or not records:
        raise ValueError("Packwiz index contains no files")

    expected = {}
    collision_paths = {}
    for record in records:
        if not isinstance(record, dict) or not {"file", "hash"}.issubset(record):
            raise ValueError("Packwiz index file record is invalid")
        if set(record) - {"file", "hash", "metafile", "preserve"}:
            raise ValueError("Packwiz index file record is invalid")
        relative_path = _relative_pack_path(
            record["file"], "Packwiz index file path"
        )
        expected_source_hash = record["hash"]
        if not isinstance(expected_source_hash, str):
            raise ValueError(f"Packwiz index hash is invalid: {relative_path}")
        source_path = root / relative_path
        _require_regular_file(source_path, "Packwiz indexed source")
        if _hash_file(source_path, payload_hash_name) != expected_source_hash:
            raise ValueError(f"Packwiz indexed source hash mismatch: {relative_path}")

        metafile = record.get("metafile", False)
        if type(metafile) is not bool:
            raise ValueError(f"Packwiz metafile flag is invalid: {relative_path}")
        if "preserve" in record and type(record["preserve"]) is not bool:
            raise ValueError(f"Packwiz preserve flag is invalid: {relative_path}")
        if metafile:
            metadata = _load_toml(source_path, "Packwiz file metadata")
            side = metadata.get("side")
            if side not in ALLOWED_SIDES:
                raise ValueError(
                    f"Packwiz metadata requires a deliberate side: {relative_path}"
                )
            if side == "server":
                continue
            filename = metadata.get("filename")
            if (
                not isinstance(filename, str)
                or not filename
                or PurePosixPath(filename).name != filename
                or "\\" in filename
            ):
                raise ValueError(f"invalid Packwiz payload filename: {relative_path}")
            parent = PurePosixPath(relative_path).parent
            installed_relative_path = (parent / filename).as_posix()
            download = metadata.get("download")
            if not isinstance(download, dict):
                raise ValueError(f"Packwiz download metadata is invalid: {relative_path}")
            installed_hash_name = download.get("hash-format")
            if installed_hash_name not in ALLOWED_HASHES:
                raise ValueError(f"Packwiz download hash is invalid: {relative_path}")
            installed_hash = download.get("hash")
            if not isinstance(installed_hash, str):
                raise ValueError(f"Packwiz download hash is invalid: {relative_path}")
        else:
            installed_relative_path = relative_path
            installed_hash_name = payload_hash_name
            installed_hash = expected_source_hash

        collision_key = installed_relative_path.casefold()
        if collision_key in collision_paths:
            raise ValueError(
                "duplicate Packwiz payload path: "
                f"{collision_paths[collision_key]} and {installed_relative_path}"
            )
        collision_paths[collision_key] = installed_relative_path
        expected[installed_relative_path] = (installed_hash_name, installed_hash)
    return expected


def _installed_file_inventory(instance_directory):
    installed = {}
    collisions = {}
    for current_root, directory_names, file_names in os.walk(
        instance_directory,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current_root)
        for directory_name in directory_names:
            directory_path = current_path / directory_name
            try:
                directory_status = directory_path.lstat()
            except OSError as error:
                raise ValueError(
                    f"installed directory is unreadable: {directory_path}"
                ) from error
            if stat.S_ISLNK(directory_status.st_mode) or not stat.S_ISDIR(
                directory_status.st_mode
            ):
                raise ValueError(
                    f"installed directory is not a regular directory: {directory_path}"
                )
        for file_name in file_names:
            file_path = current_path / file_name
            _require_regular_file(file_path, "installed file")
            relative_path = file_path.relative_to(instance_directory).as_posix()
            collision_key = relative_path.casefold()
            if collision_key in collisions:
                raise ValueError(
                    "duplicate installed file path: "
                    f"{collisions[collision_key]} and {relative_path}"
                )
            collisions[collision_key] = relative_path
            installed[relative_path] = file_path
    return installed


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


def validate_client_install(instance_dir, mods_dir, pack_root=None):
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
    summary = {
        "client_mod_count": len(client_required),
        "server_only_count": len(server_only),
        "modset_sha256": modset_sha256,
    }
    if pack_root is not None:
        expected_payload = _expected_packwiz_payload(pack_root)
        installed_files = _installed_file_inventory(instance_directory)
        allowed_files = set(expected_payload) | INSTALLER_INFRASTRUCTURE_FILES
        unexpected_files = sorted(set(installed_files) - allowed_files)
        if unexpected_files:
            raise ValueError(f"unexpected installed file: {unexpected_files[0]}")
        payload_lines = []
        for relative_path in sorted(expected_payload):
            path = instance_directory / relative_path
            try:
                _require_regular_file(path, "installed Packwiz payload")
            except ValueError as error:
                raise ValueError(
                    f"missing installed payload: {relative_path}"
                ) from error
            hash_name, expected_hash = expected_payload[relative_path]
            if _hash_file(path, hash_name) != expected_hash:
                raise ValueError(
                    f"installed payload hash mismatch: {relative_path}"
                )
            payload_lines.append(f"{_sha256_file(path)}  {relative_path}\n")
        summary.update(
            {
                "payload_file_count": len(expected_payload),
                "payload_sha256": hashlib.sha256(
                    "".join(payload_lines).encode("utf-8")
                ).hexdigest(),
            }
        )
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate an AFTERLIGHT client install")
    parser.add_argument("--instance-dir", required=True)
    parser.add_argument("--mods-dir", required=True)
    parser.add_argument("--pack-root", required=True)
    args = parser.parse_args(argv)
    summary = validate_client_install(args.instance_dir, args.mods_dir, args.pack_root)
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
