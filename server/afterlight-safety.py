#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime
import fcntl
import hashlib
import json
import os
import re
import signal
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import tomllib
import urllib.request
import urllib.parse
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO


STATE_FORMAT = "afterlight.transaction.v2"
ARCHIVE_FORMAT = "afterlight.archive.v1"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
SAFE_NAME = re.compile(r"^[A-Za-z0-9._-]+$")
MAX_STATE_BYTES = 64 * 1024
MAX_RECEIPT_BYTES = 32 * 1024 * 1024
MAX_LOG_BYTES = 64 * 1024 * 1024
MAX_MOD_METADATA_BYTES = 1024 * 1024
TERMINATION_GRACE_SECONDS = 5.0
DEFAULT_COMMAND_TIMEOUT_SECONDS = 120.0
DEFAULT_TRANSACTION_TIMEOUT_SECONDS = 3600.0
SAFE_DIRECTORY_MODES = {
    mode for mode in range(0o700, 0o777 + 1) if mode & 0o022 == 0
}


class SafetyError(RuntimeError):
    pass


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def digest_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def mode_of(metadata: os.stat_result) -> int:
    return stat.S_IMODE(metadata.st_mode)


def identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
    )


def require_canonical_absolute(path: Path, label: str, *, exists: bool = True) -> Path:
    if not path.is_absolute():
        raise SafetyError(f"{label} must be absolute")
    normalized = Path(os.path.normpath(str(path)))
    if normalized != path:
        raise SafetyError(f"{label} must be canonical")
    try:
        resolved = path.resolve(strict=exists)
    except OSError as error:
        raise SafetyError(f"{label} is unavailable") from error
    if exists and resolved != path:
        raise SafetyError(f"{label} must not traverse links")
    return path


def require_directory(
    path: Path,
    label: str,
    *,
    owner_uid: int,
    group_gid: int,
    modes: set[int],
) -> os.stat_result:
    require_canonical_absolute(path, label)
    try:
        metadata = path.lstat()
    except OSError as error:
        raise SafetyError(f"{label} is unavailable") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise SafetyError(f"{label} must be a real directory")
    if metadata.st_uid != owner_uid or metadata.st_gid != group_gid:
        raise SafetyError(f"{label} owner or group is invalid")
    if mode_of(metadata) not in modes:
        rendered = ", ".join(f"0{value:o}" for value in sorted(modes))
        raise SafetyError(f"{label} mode must be one of {rendered}")
    return metadata


def open_regular_nofollow(
    path: Path,
    label: str,
    *,
    owner_uid: int,
    group_gid: int,
    modes: set[int],
    max_bytes: int | None = None,
) -> tuple[int, os.stat_result]:
    require_canonical_absolute(path, label)
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise SafetyError(f"{label} could not be opened safely") from error
    try:
        metadata = os.fstat(descriptor)
        path_metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise SafetyError(f"{label} must be a regular file")
        if (metadata.st_dev, metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise SafetyError(f"{label} identity changed during open")
        if metadata.st_uid != owner_uid or metadata.st_gid != group_gid:
            raise SafetyError(f"{label} owner or group is invalid")
        if metadata.st_nlink != 1:
            raise SafetyError(f"{label} link count must equal one")
        if mode_of(metadata) not in modes:
            raise SafetyError(f"{label} mode is invalid")
        if max_bytes is not None and metadata.st_size > max_bytes:
            raise SafetyError(f"{label} exceeds the size limit")
        return descriptor, metadata
    except BaseException:
        os.close(descriptor)
        raise


def read_pinned(
    descriptor: int,
    original: os.stat_result,
    label: str,
    *,
    max_bytes: int,
) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(1024 * 1024, max_bytes + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > max_bytes:
            raise SafetyError(f"{label} exceeds the size limit")
    after = os.fstat(descriptor)
    if identity(after) != identity(original) or after.st_mtime_ns != original.st_mtime_ns:
        raise SafetyError(f"{label} identity changed during read")
    return b"".join(chunks)


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write(
    path: Path,
    payload: bytes,
    *,
    mode: int,
    owner_uid: int,
    group_gid: int,
    replace: bool,
) -> None:
    parent = path.parent
    temporary = parent / f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}"
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, mode)
    try:
        os.fchmod(descriptor, mode)
        if os.geteuid() == 0:
            os.fchown(descriptor, owner_uid, group_gid)
        offset = 0
        while offset < len(payload):
            offset += os.write(descriptor, payload[offset:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    try:
        if not replace and (path.exists() or path.is_symlink()):
            raise SafetyError(f"{path.name} already exists")
        os.replace(temporary, path)
        fsync_directory(parent)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def parse_json(payload: bytes, label: str) -> Any:
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SafetyError(f"{label} is not valid UTF-8 JSON") from error
    if payload != canonical_json_bytes(value):
        raise SafetyError(f"{label} is not canonical JSON")
    return value


def state_path(arguments: argparse.Namespace) -> Path:
    return Path(arguments.state_dir) / "state"


def require_state_directory(arguments: argparse.Namespace, *, create: bool) -> Path:
    directory = require_canonical_absolute(Path(arguments.state_dir), "state directory", exists=not create)
    if create and not directory.exists():
        parent = directory.parent
        require_canonical_absolute(parent, "state directory parent")
        directory.mkdir(mode=arguments.state_dir_mode)
        if os.geteuid() == 0:
            os.chown(directory, arguments.owner_uid, arguments.group_gid)
        os.chmod(directory, arguments.state_dir_mode)
        fsync_directory(parent)
    require_directory(
        directory,
        "state directory",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={arguments.state_dir_mode},
    )
    return directory


def validate_server_mod_manifest(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SafetyError("accepted server mod manifest is invalid")
    previous = ""
    validated: list[dict[str, Any]] = []
    for record in value:
        if not isinstance(record, dict) or set(record) != {
            "filename",
            "hash_format",
            "hash",
            "size",
        }:
            raise SafetyError("accepted server mod manifest is invalid")
        filename = record["filename"]
        hash_format = record["hash_format"]
        digest = record["hash"]
        size = record["size"]
        expected_lengths = {"sha1": 40, "sha256": 64, "sha512": 128}
        if (
            not isinstance(filename, str)
            or not SAFE_NAME.fullmatch(filename)
            or filename <= previous
            or hash_format not in expected_lengths
            or not isinstance(digest, str)
            or not re.fullmatch(
                rf"[0-9a-f]{{{expected_lengths.get(hash_format, 0)}}}",
                digest,
            )
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size <= 0
        ):
            raise SafetyError("accepted server mod manifest is invalid")
        previous = filename
        validated.append(record)
    return validated


def validate_original_data_record(value: Any) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"path", "root", "marker"}:
        raise SafetyError("original data authority is invalid")
    path = value["path"]
    if not isinstance(path, str):
        raise SafetyError("original data authority is invalid")
    require_canonical_absolute(Path(path), "original data authority path", exists=False)
    for label in ("root", "marker"):
        record = value[label]
        expected = {"device", "inode", "uid", "gid", "mode", "nlink"}
        if label == "marker":
            expected |= {"size", "sha256"}
        if not isinstance(record, dict) or set(record) != expected:
            raise SafetyError("original data authority is invalid")
        numeric = expected - {"sha256"}
        if any(not isinstance(record[field], int) for field in numeric):
            raise SafetyError("original data authority is invalid")
        if label == "marker" and not SHA256.fullmatch(str(record["sha256"])):
            raise SafetyError("original data authority is invalid")
    return value


def validate_state(value: Any, arguments: argparse.Namespace) -> dict[str, Any]:
    required = {
        "format",
        "transaction_id",
        "status",
        "phase",
        "expected_sha",
        "prior_sha",
        "gate_comment",
        "snapshot_dir",
        "snapshot_root",
        "receipt_sha256",
        "containers",
    }
    optional = {"data_mutated", "original_data", "server_mods"}
    if (
        not isinstance(value, dict)
        or not required.issubset(value)
        or set(value) - required - optional
    ):
        raise SafetyError("transaction authority schema is invalid")
    if value["format"] != STATE_FORMAT:
        raise SafetyError("transaction authority format is invalid")
    transaction_id = value["transaction_id"]
    if not isinstance(transaction_id, str) or not re.fullmatch(r"[0-9a-f]{32}", transaction_id):
        raise SafetyError("transaction authority identifier is invalid")
    if value["status"] not in {"pending", "quarantine", "terminal"}:
        raise SafetyError("transaction authority status is invalid")
    if not isinstance(value["phase"], str) or not re.fullmatch(r"[a-z0-9-]{1,64}", value["phase"]):
        raise SafetyError("transaction authority phase is invalid")
    for field in ("expected_sha", "prior_sha"):
        if not isinstance(value[field], str) or not SHA40.fullmatch(value[field]):
            raise SafetyError("transaction authority revision is invalid")
    if not isinstance(value["receipt_sha256"], str) or not SHA256.fullmatch(value["receipt_sha256"]):
        raise SafetyError("transaction authority receipt digest is invalid")
    expected_comment = f"afterlight-quest-update-{value['expected_sha']}-{transaction_id}"
    if value["gate_comment"] != expected_comment:
        raise SafetyError("transaction authority gate comment is invalid")
    snapshot_root = Path(value["snapshot_root"])
    configured_snapshot_root = require_canonical_absolute(
        Path(arguments.canonical_snapshot_root),
        "configured snapshot root",
    )
    if snapshot_root != configured_snapshot_root:
        raise SafetyError("transaction snapshot root is not canonical")
    require_directory(
        snapshot_root,
        "snapshot root",
        owner_uid=arguments.snapshot_owner_uid,
        group_gid=arguments.snapshot_group_gid,
        modes={arguments.snapshot_root_mode},
    )
    snapshot_value = value["snapshot_dir"]
    if snapshot_value is not None:
        if not isinstance(snapshot_value, str):
            raise SafetyError("transaction snapshot path is invalid")
        snapshot = require_canonical_absolute(Path(snapshot_value), "transaction snapshot")
        try:
            snapshot.relative_to(snapshot_root)
        except ValueError as error:
            raise SafetyError("transaction snapshot must be beneath snapshot root") from error
        if snapshot == snapshot_root:
            raise SafetyError("transaction snapshot must not equal snapshot root")
        require_directory(
            snapshot,
            "transaction snapshot",
            owner_uid=arguments.snapshot_owner_uid,
            group_gid=arguments.snapshot_group_gid,
            modes={0o700},
        )
    containers = value["containers"]
    if not isinstance(containers, dict) or set(containers) != {"minecraft", "backup"}:
        raise SafetyError("transaction container state is invalid")
    for child in containers.values():
        if not isinstance(child, dict) or set(child) != {"restart_disabled", "stopped"}:
            raise SafetyError("transaction container state is invalid")
        if not all(isinstance(child[key], bool) for key in child):
            raise SafetyError("transaction container state is invalid")
    validate_original_data_record(value.get("original_data"))
    validate_server_mod_manifest(value.get("server_mods", []))
    if not isinstance(value.get("data_mutated", True), bool):
        raise SafetyError("transaction data mutation state is invalid")
    return value


def capture_original_data(arguments: argparse.Namespace) -> dict[str, Any] | None:
    if arguments.data_root is None:
        return None
    if arguments.data_owner_uid is None or arguments.data_group_gid is None:
        raise SafetyError("original data identity is incomplete")
    data = require_canonical_absolute(Path(arguments.data_root), "original data root")
    root = require_directory(
        data,
        "original data root",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    marker_path = data / ".afterlight-pack-sha"
    marker_fd, marker = open_regular_nofollow(
        marker_path,
        "original release marker",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes={0o600},
        max_bytes=128,
    )
    try:
        payload = read_pinned(
            marker_fd,
            marker,
            "original release marker",
            max_bytes=128,
        )
    finally:
        os.close(marker_fd)
    if payload != f"{arguments.prior_sha}\n".encode("ascii"):
        raise SafetyError("original release marker differs from prior revision")
    return {
        "path": str(data),
        "root": {
            "device": root.st_dev,
            "inode": root.st_ino,
            "uid": root.st_uid,
            "gid": root.st_gid,
            "mode": mode_of(root),
            "nlink": root.st_nlink,
        },
        "marker": {
            "device": marker.st_dev,
            "inode": marker.st_ino,
            "uid": marker.st_uid,
            "gid": marker.st_gid,
            "mode": mode_of(marker),
            "nlink": marker.st_nlink,
            "size": marker.st_size,
            "sha256": digest_bytes(payload),
        },
    }


def read_state(arguments: argparse.Namespace) -> dict[str, Any]:
    require_state_directory(arguments, create=False)
    descriptor, metadata = open_regular_nofollow(
        state_path(arguments),
        "transaction authority",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={arguments.state_file_mode},
        max_bytes=MAX_STATE_BYTES,
    )
    try:
        payload = read_pinned(
            descriptor,
            metadata,
            "transaction authority",
            max_bytes=MAX_STATE_BYTES,
        )
    finally:
        os.close(descriptor)
    return validate_state(parse_json(payload, "transaction authority"), arguments)


def command_authority_create(arguments: argparse.Namespace) -> int:
    require_state_directory(arguments, create=True)
    marker = state_path(arguments)
    if marker.exists() or marker.is_symlink():
        raise SafetyError("transaction authority is already active")
    transaction_id = os.urandom(16).hex()
    server_mods: list[dict[str, Any]] = []
    if arguments.server_mod_manifest_json is not None:
        try:
            manifest_value = json.loads(arguments.server_mod_manifest_json)
        except json.JSONDecodeError as error:
            raise SafetyError("accepted server mod manifest is invalid") from error
        server_mods = validate_server_mod_manifest(manifest_value)
    value = {
        "format": STATE_FORMAT,
        "transaction_id": transaction_id,
        "status": "pending",
        "phase": "authorized",
        "expected_sha": arguments.expected_sha,
        "prior_sha": arguments.prior_sha,
        "gate_comment": f"afterlight-quest-update-{arguments.expected_sha}-{transaction_id}",
        "snapshot_dir": None,
        "snapshot_root": str(Path(arguments.snapshot_root)),
        "receipt_sha256": arguments.receipt_sha256,
        "data_mutated": False,
        "original_data": capture_original_data(arguments),
        "server_mods": server_mods,
        "containers": {
            "minecraft": {"restart_disabled": False, "stopped": False},
            "backup": {"restart_disabled": False, "stopped": False},
        },
    }
    validate_state(value, arguments)
    atomic_write(
        marker,
        canonical_json_bytes(value),
        mode=arguments.state_file_mode,
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        replace=False,
    )
    print(transaction_id)
    return 0


def command_authority_status(arguments: argparse.Namespace) -> int:
    directory = require_state_directory(arguments, create=False)
    marker = directory / "state"
    try:
        marker.lstat()
    except FileNotFoundError:
        return 3
    value = read_state(arguments)
    if arguments.field is not None:
        field_value = value.get(arguments.field)
        if isinstance(field_value, (dict, list)):
            sys.stdout.buffer.write(canonical_json_bytes(field_value))
        else:
            print(field_value)
    elif arguments.print_json:
        sys.stdout.buffer.write(canonical_json_bytes(value))
    else:
        print(value["status"])
    return 0


def command_authority_update(arguments: argparse.Namespace) -> int:
    value = read_state(arguments)
    if value["transaction_id"] != arguments.transaction_id:
        raise SafetyError("transaction authority identifier mismatch")
    if arguments.status is not None:
        value["status"] = arguments.status
    if arguments.phase is not None:
        value["phase"] = arguments.phase
    if arguments.snapshot_dir is not None:
        value["snapshot_dir"] = arguments.snapshot_dir
    if arguments.data_mutated is not None:
        value["data_mutated"] = arguments.data_mutated
    if arguments.service is not None:
        if arguments.restart_disabled is not None:
            value["containers"][arguments.service]["restart_disabled"] = arguments.restart_disabled
        if arguments.stopped is not None:
            value["containers"][arguments.service]["stopped"] = arguments.stopped
    validate_state(value, arguments)
    atomic_write(
        state_path(arguments),
        canonical_json_bytes(value),
        mode=arguments.state_file_mode,
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        replace=True,
    )
    return 0


def command_authority_complete(arguments: argparse.Namespace) -> int:
    value = read_state(arguments)
    if value["transaction_id"] != arguments.transaction_id:
        raise SafetyError("transaction authority identifier mismatch")
    value["status"] = "terminal"
    value["phase"] = "complete"
    marker = state_path(arguments)
    atomic_write(
        marker,
        canonical_json_bytes(value),
        mode=arguments.state_file_mode,
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        replace=True,
    )
    marker.unlink()
    fsync_directory(marker.parent)
    return 0


def command_recovery_original_verify(arguments: argparse.Namespace) -> int:
    value = read_state(arguments)
    if value["transaction_id"] != arguments.transaction_id:
        raise SafetyError("transaction authority identifier mismatch")
    if value.get("data_mutated", True):
        raise SafetyError("original data recovery is forbidden after protected mutation")
    recorded = validate_original_data_record(value.get("original_data"))
    if recorded is None:
        raise SafetyError("original data recovery authority is missing")
    data = require_canonical_absolute(Path(arguments.data), "original recovery data")
    if str(data) != recorded["path"]:
        raise SafetyError("original recovery data path differs from authority")
    root = require_directory(
        data,
        "original recovery data",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes={recorded["root"]["mode"]},
    )
    actual_root = {
        "device": root.st_dev,
        "inode": root.st_ino,
        "uid": root.st_uid,
        "gid": root.st_gid,
        "mode": mode_of(root),
        "nlink": root.st_nlink,
    }
    if actual_root != recorded["root"]:
        raise SafetyError("original recovery data identity changed")
    marker_fd, marker = open_regular_nofollow(
        data / ".afterlight-pack-sha",
        "original recovery release marker",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes={recorded["marker"]["mode"]},
        max_bytes=128,
    )
    try:
        payload = read_pinned(
            marker_fd,
            marker,
            "original recovery release marker",
            max_bytes=128,
        )
    finally:
        os.close(marker_fd)
    actual_marker = {
        "device": marker.st_dev,
        "inode": marker.st_ino,
        "uid": marker.st_uid,
        "gid": marker.st_gid,
        "mode": mode_of(marker),
        "nlink": marker.st_nlink,
        "size": marker.st_size,
        "sha256": digest_bytes(payload),
    }
    if actual_marker != recorded["marker"]:
        raise SafetyError("original recovery release marker identity changed")
    if payload != f"{value['prior_sha']}\n".encode("ascii"):
        raise SafetyError("original recovery release marker differs from prior revision")
    print(value["prior_sha"])
    return 0


def command_snapshot_create(arguments: argparse.Namespace) -> int:
    root = require_canonical_absolute(Path(arguments.snapshot_root), "snapshot root")
    require_directory(
        root,
        "snapshot root",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o700},
    )
    name = arguments.name
    if not SAFE_NAME.fullmatch(name) or not name.startswith("quest-update-"):
        raise SafetyError("snapshot name is invalid")
    destination = root / name
    if destination.exists() or destination.is_symlink():
        raise SafetyError("snapshot already exists")
    root_fd = os.open(
        root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    snapshot_fd: int | None = None
    progress_created = False
    try:
        os.mkdir(name, 0o700, dir_fd=root_fd)
        if os.geteuid() == 0:
            os.chown(
                name,
                arguments.owner_uid,
                arguments.group_gid,
                dir_fd=root_fd,
                follow_symlinks=False,
            )
        snapshot_fd = os.open(
            name,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
            dir_fd=root_fd,
        )
        try:
            os.mkdir("progress", 0o700, dir_fd=snapshot_fd)
            progress_created = True
            if os.geteuid() == 0:
                os.chown(
                    "progress",
                    arguments.owner_uid,
                    arguments.group_gid,
                    dir_fd=snapshot_fd,
                    follow_symlinks=False,
                )
            os.fsync(snapshot_fd)
        finally:
            os.close(snapshot_fd)
            snapshot_fd = None
        os.fsync(root_fd)
    except BaseException:
        if progress_created:
            cleanup_fd = snapshot_fd
            if cleanup_fd is None:
                try:
                    cleanup_fd = os.open(
                        name,
                        os.O_RDONLY
                        | getattr(os, "O_DIRECTORY", 0)
                        | getattr(os, "O_NOFOLLOW", 0),
                        dir_fd=root_fd,
                    )
                except OSError:
                    cleanup_fd = None
            if cleanup_fd is not None:
                try:
                    os.rmdir("progress", dir_fd=cleanup_fd)
                    os.fsync(cleanup_fd)
                except OSError:
                    pass
                finally:
                    os.close(cleanup_fd)
        try:
            os.rmdir(name, dir_fd=root_fd)
        except OSError:
            pass
        os.fsync(root_fd)
        raise
    finally:
        os.close(root_fd)
    require_directory(
        destination,
        "snapshot",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o700},
    )
    print(destination)
    return 0


def command_release_marker_write(arguments: argparse.Namespace) -> int:
    if not SHA40.fullmatch(arguments.revision):
        raise SafetyError("release marker revision is invalid")
    data = require_canonical_absolute(Path(arguments.data), "server data")
    require_directory(
        data,
        "server data",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    atomic_write(
        data / ".afterlight-pack-sha",
        f"{arguments.revision}\n".encode("ascii"),
        mode=0o600,
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        replace=True,
    )
    return 0


def command_release_marker_read(arguments: argparse.Namespace) -> int:
    data = require_canonical_absolute(Path(arguments.data), "server data")
    require_directory(
        data,
        "server data",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    descriptor, metadata = open_regular_nofollow(
        data / ".afterlight-pack-sha",
        "release marker",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o600},
        max_bytes=41,
    )
    try:
        payload = read_pinned(
            descriptor,
            metadata,
            "release marker",
            max_bytes=41,
        )
    finally:
        os.close(descriptor)
    if not re.fullmatch(rb"[0-9a-f]{40}\n", payload):
        raise SafetyError("release marker payload is invalid")
    sys.stdout.buffer.write(payload)
    return 0


def command_snapshot_complete(arguments: argparse.Namespace) -> int:
    snapshot = require_canonical_absolute(Path(arguments.snapshot), "completed snapshot")
    require_directory(
        snapshot,
        "completed snapshot",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o700},
    )
    transaction_id = arguments.transaction_id
    if not re.fullmatch(r"[0-9a-f]{32}", transaction_id):
        raise SafetyError("completed snapshot transaction identifier is invalid")
    completed_at = arguments.completed_at
    if completed_at is None:
        completed_at = int(time.time())
    if completed_at < 0:
        raise SafetyError("completed snapshot time is invalid")
    atomic_write(
        snapshot / "retention.json",
        canonical_json_bytes(
            {
                "format": "afterlight.snapshot-retention.v1",
                "status": "successful",
                "transaction_id": transaction_id,
                "completed_at": completed_at,
            }
        ),
        mode=0o600,
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        replace=False,
    )
    return 0


def remove_owned_tree(
    parent_fd: int,
    name: str,
    *,
    owner_uid: int,
    group_gid: int,
    label: str,
) -> None:
    directory_fd = os.open(
        name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=parent_fd,
    )
    try:
        metadata = os.fstat(directory_fd)
        if metadata.st_uid != owner_uid or metadata.st_gid != group_gid:
            raise SafetyError(f"{label} owner or group is invalid")
        for child in safe_children(directory_fd):
            child_metadata = os.stat(child, dir_fd=directory_fd, follow_symlinks=False)
            if child_metadata.st_uid != owner_uid or child_metadata.st_gid != group_gid:
                raise SafetyError(f"{label} entry owner or group is invalid")
            if stat.S_ISDIR(child_metadata.st_mode):
                remove_owned_tree(
                    directory_fd,
                    child,
                    owner_uid=owner_uid,
                    group_gid=group_gid,
                    label=label,
                )
            elif stat.S_ISREG(child_metadata.st_mode) and child_metadata.st_nlink == 1:
                os.unlink(child, dir_fd=directory_fd)
            else:
                raise SafetyError(f"{label} contains an unsafe entry")
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)
    os.rmdir(name, dir_fd=parent_fd)
    os.fsync(parent_fd)


def command_snapshot_prune(arguments: argparse.Namespace) -> int:
    root = require_canonical_absolute(Path(arguments.snapshot_root), "snapshot root")
    require_directory(
        root,
        "snapshot root",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o700},
    )
    if arguments.older_than < 0:
        raise SafetyError("snapshot retention threshold is invalid")
    root_fd = os.open(
        root,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    removed: list[str] = []
    try:
        for name in safe_children(root_fd):
            if not name.startswith("quest-update-"):
                continue
            metadata = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
            if not stat.S_ISDIR(metadata.st_mode):
                raise SafetyError("snapshot retention root contains an unsafe entry")
            snapshot = root / name
            marker_path = snapshot / "retention.json"
            try:
                marker_fd, marker_metadata = open_regular_nofollow(
                    marker_path,
                    "snapshot retention marker",
                    owner_uid=arguments.owner_uid,
                    group_gid=arguments.group_gid,
                    modes={0o600},
                    max_bytes=MAX_STATE_BYTES,
                )
            except SafetyError:
                continue
            try:
                marker_payload = read_pinned(
                    marker_fd,
                    marker_metadata,
                    "snapshot retention marker",
                    max_bytes=MAX_STATE_BYTES,
                )
                marker = parse_json(marker_payload, "snapshot retention marker")
            finally:
                os.close(marker_fd)
            if (
                not isinstance(marker, dict)
                or set(marker) != {
                    "completed_at",
                    "format",
                    "status",
                    "transaction_id",
                }
                or marker_payload != canonical_json_bytes(marker)
                or marker.get("format") != "afterlight.snapshot-retention.v1"
                or marker.get("status") != "successful"
                or not isinstance(marker.get("completed_at"), int)
                or isinstance(marker.get("completed_at"), bool)
                or not re.fullmatch(r"[0-9a-f]{32}", str(marker.get("transaction_id", "")))
                or marker["completed_at"] >= arguments.older_than
            ):
                continue
            remove_owned_tree(
                root_fd,
                name,
                owner_uid=arguments.owner_uid,
                group_gid=arguments.group_gid,
                label="snapshot retention tree",
            )
            removed.append(name)
    finally:
        os.close(root_fd)
    print(canonical_json_bytes({"removed": removed}).decode("utf-8"), end="")
    return 0


def secure_lock_descriptor(arguments: argparse.Namespace) -> int:
    runtime = Path(arguments.runtime_dir)
    require_directory(
        runtime,
        "runtime directory",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={arguments.runtime_mode},
    )
    lock_path = runtime / "maintenance.lock"
    flags = os.O_RDWR | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    created = False
    try:
        descriptor = os.open(
            lock_path,
            flags | os.O_CREAT | os.O_EXCL,
            arguments.lock_mode,
        )
        created = True
    except FileExistsError:
        try:
            descriptor = os.open(lock_path, flags)
        except OSError as error:
            raise SafetyError("maintenance lock could not be opened safely") from error
    except OSError as error:
        raise SafetyError("maintenance lock could not be opened safely") from error
    try:
        metadata = os.fstat(descriptor)
        path_metadata = lock_path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise SafetyError("maintenance lock must be a regular file")
        if (metadata.st_dev, metadata.st_ino) != (path_metadata.st_dev, path_metadata.st_ino):
            raise SafetyError("maintenance lock identity changed during open")
        if created:
            if os.geteuid() == 0:
                os.fchown(descriptor, arguments.owner_uid, arguments.group_gid)
            os.fchmod(descriptor, arguments.lock_mode)
            metadata = os.fstat(descriptor)
        if metadata.st_uid != arguments.owner_uid or metadata.st_gid != arguments.group_gid:
            raise SafetyError("maintenance lock owner or group is invalid")
        if metadata.st_nlink != 1:
            raise SafetyError("maintenance lock link count must equal one")
        if mode_of(metadata) != arguments.lock_mode:
            raise SafetyError("maintenance lock mode is invalid")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise SafetyError("unable to acquire maintenance lock") from error
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def verify_inherited_lock_descriptor(arguments: argparse.Namespace) -> int:
    runtime = Path(arguments.runtime_dir)
    require_directory(
        runtime,
        "runtime directory",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={arguments.runtime_mode},
    )
    lock_path = runtime / "maintenance.lock"
    try:
        descriptor = int(arguments.lock_fd)
    except (TypeError, ValueError) as error:
        raise SafetyError("inherited maintenance lock descriptor is invalid") from error
    if descriptor < 0:
        raise SafetyError("inherited maintenance lock descriptor is invalid")
    try:
        metadata = os.fstat(descriptor)
        path_metadata = lock_path.lstat()
    except OSError as error:
        raise SafetyError("inherited maintenance lock descriptor is unavailable") from error
    if not stat.S_ISREG(metadata.st_mode):
        raise SafetyError("inherited maintenance lock must be a regular file")
    if (metadata.st_dev, metadata.st_ino) != (path_metadata.st_dev, path_metadata.st_ino):
        raise SafetyError("inherited maintenance lock identity is invalid")
    if metadata.st_uid != arguments.owner_uid or metadata.st_gid != arguments.group_gid:
        raise SafetyError("inherited maintenance lock owner or group is invalid")
    if metadata.st_nlink != 1 or mode_of(metadata) != arguments.lock_mode:
        raise SafetyError("inherited maintenance lock metadata is invalid")
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        raise SafetyError("inherited maintenance lock is not held by this process") from error
    return descriptor


def run_controlled_process(
    command: list[str],
    *,
    environment: dict[str, str],
    timeout_seconds: float,
    termination_grace_seconds: float = TERMINATION_GRACE_SECONDS,
    pass_fds: tuple[int, ...] = (),
) -> int:
    if not command:
        raise SafetyError("controlled process requires a command")
    if not 0 < timeout_seconds <= 86400:
        raise SafetyError("controlled process timeout is invalid")
    if not 0 < termination_grace_seconds <= 3600:
        raise SafetyError("controlled process termination grace is invalid")
    child = subprocess.Popen(
        command,
        env=environment,
        start_new_session=True,
        pass_fds=pass_fds,
    )
    received_signal: int | None = None
    timed_out = False
    deadline = time.monotonic() + timeout_seconds

    def forward(signum: int, _frame: Any) -> None:
        nonlocal received_signal
        received_signal = signum
        try:
            os.killpg(child.pid, signum)
        except ProcessLookupError:
            pass

    previous = {
        signum: signal.signal(signum, forward)
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)
    }
    try:
        while True:
            try:
                return_code = child.wait(timeout=0.1)
                break
            except subprocess.TimeoutExpired:
                if received_signal is None and time.monotonic() < deadline:
                    continue
                timed_out = received_signal is None
                if timed_out:
                    try:
                        os.killpg(child.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                try:
                    return_code = child.wait(timeout=termination_grace_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    return_code = child.wait()
                break
        if timed_out:
            print(
                f"ERROR: controlled command exceeded {timeout_seconds:g} seconds",
                file=sys.stderr,
            )
            return 124
        if received_signal is not None:
            return 128 + received_signal
        return return_code
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)
        try:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=TERMINATION_GRACE_SECONDS)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            pass


def command_run(arguments: argparse.Namespace) -> int:
    pass_fds: tuple[int, ...] = ()
    inherited_lock = os.environ.get("AFTERLIGHT_LOCK_FD")
    if inherited_lock is not None:
        try:
            lock_fd = int(inherited_lock)
            os.fstat(lock_fd)
        except (TypeError, ValueError, OSError) as error:
            raise SafetyError("inherited maintenance lock descriptor is unavailable") from error
        pass_fds = (lock_fd,)
    return run_controlled_process(
        arguments.command,
        environment=os.environ.copy(),
        timeout_seconds=arguments.timeout,
        pass_fds=pass_fds,
    )


def command_lock_run(arguments: argparse.Namespace) -> int:
    if not arguments.command:
        raise SafetyError("lock-run requires a command")
    descriptor = secure_lock_descriptor(arguments)
    environment = os.environ.copy()
    environment.pop("AFTERLIGHT_LOCK_HELD", None)
    environment["AFTERLIGHT_LOCK_FD"] = str(descriptor)
    os.set_inheritable(descriptor, True)
    try:
        return run_controlled_process(
            arguments.command,
            environment=environment,
            timeout_seconds=arguments.timeout,
            termination_grace_seconds=arguments.termination_grace,
            pass_fds=(descriptor,),
        )
    finally:
        os.close(descriptor)


def command_lock_verify(arguments: argparse.Namespace) -> int:
    verify_inherited_lock_descriptor(arguments)
    return 0


def safe_children(directory_fd: int) -> list[str]:
    try:
        names = os.listdir(directory_fd)
    except OSError as error:
        raise SafetyError("archive source traversal failed") from error
    for name in names:
        if not SAFE_NAME.fullmatch(name) or name in {".", ".."}:
            raise SafetyError("archive source contains an unsafe name")
    return sorted(names)


def inventory_record(path: str, kind: str, metadata: os.stat_result, digest: str | None) -> dict[str, Any]:
    return {
        "path": path,
        "kind": kind,
        "mode": mode_of(metadata),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
        "size": metadata.st_size if kind == "file" else 0,
        "sha256": digest,
    }


def read_regular_from_dir(
    directory_fd: int,
    name: str,
    before: os.stat_result,
) -> tuple[BinaryIO, str]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, dir_fd=directory_fd)
    try:
        opened = os.fstat(descriptor)
        if identity(opened) != identity(before) or opened.st_mtime_ns != before.st_mtime_ns:
            raise SafetyError("archive source identity changed during open")
        digest = hashlib.sha256()
        spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024)
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            spool.write(chunk)
        after = os.fstat(descriptor)
        if identity(after) != identity(before) or after.st_mtime_ns != before.st_mtime_ns:
            spool.close()
            raise SafetyError("archive source changed during read")
        spool.seek(0)
        return spool, digest.hexdigest()
    finally:
        os.close(descriptor)


def add_tree_to_archive(
    archive: tarfile.TarFile,
    directory_fd: int,
    relative: str,
    inventory: list[dict[str, Any]],
    *,
    owner_uid: int,
    group_gid: int,
) -> None:
    for name in safe_children(directory_fd):
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        if metadata.st_uid != owner_uid or metadata.st_gid != group_gid:
            raise SafetyError("archive source owner or group is invalid")
        child_relative = name if relative == "." else f"{relative}/{name}"
        if stat.S_ISDIR(metadata.st_mode):
            child_fd = os.open(
                name,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(child_fd)
                if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                    raise SafetyError("archive directory identity changed during open")
                record = inventory_record(child_relative, "directory", opened, None)
                inventory.append(record)
                info = tarfile.TarInfo(child_relative)
                info.type = tarfile.DIRTYPE
                info.mode = record["mode"]
                info.uid = record["uid"]
                info.gid = record["gid"]
                info.mtime = 0
                archive.addfile(info)
                add_tree_to_archive(
                    archive,
                    child_fd,
                    child_relative,
                    inventory,
                    owner_uid=owner_uid,
                    group_gid=group_gid,
                )
                if identity(os.fstat(child_fd)) != identity(opened):
                    raise SafetyError("archive directory changed during traversal")
            finally:
                os.close(child_fd)
        elif stat.S_ISREG(metadata.st_mode):
            if metadata.st_nlink != 1:
                raise SafetyError("archive source file link count must equal one")
            stream, digest = read_regular_from_dir(directory_fd, name, metadata)
            try:
                record = inventory_record(child_relative, "file", metadata, digest)
                inventory.append(record)
                info = tarfile.TarInfo(child_relative)
                info.type = tarfile.REGTYPE
                info.mode = record["mode"]
                info.uid = record["uid"]
                info.gid = record["gid"]
                info.size = record["size"]
                info.mtime = 0
                archive.addfile(info, stream)
            finally:
                stream.close()
        else:
            raise SafetyError("archive source contains a link or unsupported entry")


def command_archive_create(arguments: argparse.Namespace) -> int:
    source = require_canonical_absolute(Path(arguments.source), "archive source")
    source_metadata = require_directory(
        source,
        "archive source",
        owner_uid=arguments.source_owner_uid,
        group_gid=arguments.source_group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    archive_path = require_canonical_absolute(Path(arguments.archive), "archive path", exists=False)
    receipt_path = require_canonical_absolute(Path(arguments.receipt), "archive receipt path", exists=False)
    if archive_path.parent != receipt_path.parent:
        raise SafetyError("archive and receipt must share one directory")
    require_directory(
        archive_path.parent,
        "archive output directory",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o700},
    )
    if any(path.exists() or path.is_symlink() for path in (archive_path, receipt_path)):
        raise SafetyError("archive output already exists")
    flags = os.O_RDWR | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    archive_fd = os.open(archive_path, flags, 0o600)
    inventory = [inventory_record(".", "directory", source_metadata, None)]
    try:
        if os.geteuid() == 0:
            os.fchown(archive_fd, arguments.owner_uid, arguments.group_gid)
        archive_owner = os.fstat(archive_fd)
        if (
            archive_owner.st_uid != arguments.owner_uid
            or archive_owner.st_gid != arguments.group_gid
        ):
            raise SafetyError("archive owner or group could not be established")
        os.fchmod(archive_fd, 0o600)
        source_fd = os.open(
            source,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            with os.fdopen(os.dup(archive_fd), "wb") as archive_stream:
                with tarfile.open(fileobj=archive_stream, mode="w:gz", compresslevel=6) as archive:
                    add_tree_to_archive(
                        archive,
                        source_fd,
                        ".",
                        inventory,
                        owner_uid=arguments.source_owner_uid,
                        group_gid=arguments.source_group_gid,
                    )
                archive_stream.flush()
                os.fsync(archive_stream.fileno())
            if identity(os.fstat(source_fd)) != identity(source_metadata):
                raise SafetyError("archive source root changed during traversal")
        finally:
            os.close(source_fd)
        os.fchmod(archive_fd, 0o600)
        os.fsync(archive_fd)
        archive_metadata = os.fstat(archive_fd)
        os.lseek(archive_fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        while chunk := os.read(archive_fd, 1024 * 1024):
            digest.update(chunk)
        final_metadata = os.fstat(archive_fd)
        if identity(final_metadata) != identity(archive_metadata):
            raise SafetyError("archive identity changed during authentication")
        receipt = {
            "format": ARCHIVE_FORMAT,
            "archive": {
                "device": archive_metadata.st_dev,
                "inode": archive_metadata.st_ino,
                "uid": archive_metadata.st_uid,
                "gid": archive_metadata.st_gid,
                "mode": mode_of(archive_metadata),
                "nlink": archive_metadata.st_nlink,
                "size": archive_metadata.st_size,
                "sha256": digest.hexdigest(),
            },
            "inventory": inventory,
        }
        atomic_write(
            receipt_path,
            canonical_json_bytes(receipt),
            mode=0o600,
            owner_uid=arguments.owner_uid,
            group_gid=arguments.group_gid,
            replace=False,
        )
        fsync_directory(archive_path.parent)
        print(receipt["archive"]["sha256"])
        return 0
    except BaseException:
        archive_path.unlink(missing_ok=True)
        receipt_path.unlink(missing_ok=True)
        fsync_directory(archive_path.parent)
        raise
    finally:
        os.close(archive_fd)


def validate_archive_receipt(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"format", "archive", "inventory"}:
        raise SafetyError("archive receipt schema is invalid")
    if value["format"] != ARCHIVE_FORMAT:
        raise SafetyError("archive receipt format is invalid")
    archive = value["archive"]
    if not isinstance(archive, dict) or set(archive) != {
        "device", "inode", "uid", "gid", "mode", "nlink", "size", "sha256"
    }:
        raise SafetyError("archive receipt identity is invalid")
    if not isinstance(archive["sha256"], str) or not SHA256.fullmatch(archive["sha256"]):
        raise SafetyError("archive receipt digest is invalid")
    inventory = value["inventory"]
    if not isinstance(inventory, list) or not inventory:
        raise SafetyError("archive receipt inventory is invalid")
    seen: set[str] = set()
    for record in inventory:
        if not isinstance(record, dict) or set(record) != {
            "path", "kind", "mode", "uid", "gid", "nlink", "size", "sha256"
        }:
            raise SafetyError("archive receipt inventory is invalid")
        path = record["path"]
        if not isinstance(path, str) or path in seen:
            raise SafetyError("archive receipt inventory is invalid")
        parts = PurePosixPath(path).parts
        if path != "." and (not parts or any(not SAFE_NAME.fullmatch(part) for part in parts)):
            raise SafetyError("archive receipt path is invalid")
        seen.add(path)
        if record["kind"] not in {"file", "directory"}:
            raise SafetyError("archive receipt entry kind is invalid")
        if record["kind"] == "file" and (
            record["nlink"] != 1
            or not isinstance(record["sha256"], str)
            or not SHA256.fullmatch(record["sha256"])
        ):
            raise SafetyError("archive receipt file identity is invalid")
        if record["kind"] == "directory" and record["sha256"] is not None:
            raise SafetyError("archive receipt directory identity is invalid")
    if inventory[0]["path"] != "." or inventory[0]["kind"] != "directory":
        raise SafetyError("archive receipt root is invalid")
    return value


def collect_restored_inventory(root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(directory: Path, relative: str) -> None:
        for entry in sorted(os.scandir(directory), key=lambda child: child.name):
            if not SAFE_NAME.fullmatch(entry.name):
                raise SafetyError("restored tree contains an unsafe name")
            metadata = entry.stat(follow_symlinks=False)
            child_relative = entry.name if relative == "." else f"{relative}/{entry.name}"
            if stat.S_ISDIR(metadata.st_mode):
                records.append(inventory_record(child_relative, "directory", metadata, None))
                visit(Path(entry.path), child_relative)
            elif stat.S_ISREG(metadata.st_mode):
                if metadata.st_nlink != 1:
                    raise SafetyError("restored file link count must equal one")
                descriptor = os.open(
                    entry.path,
                    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_CLOEXEC", 0),
                )
                try:
                    opened = os.fstat(descriptor)
                    if identity(opened) != identity(metadata):
                        raise SafetyError("restored file identity changed during open")
                    digest = file_digest_from_fd(descriptor)
                    after = os.fstat(descriptor)
                    if identity(after) != identity(opened) or after.st_mtime_ns != opened.st_mtime_ns:
                        raise SafetyError("restored file changed during verification")
                finally:
                    os.close(descriptor)
                records.append(inventory_record(child_relative, "file", metadata, digest))
            else:
                raise SafetyError("restored tree contains a link or unsupported entry")

    root_metadata = root.lstat()
    records.append(inventory_record(".", "directory", root_metadata, None))
    visit(root, ".")
    return records


def file_digest_from_fd(descriptor: int) -> str:
    os.lseek(descriptor, 0, os.SEEK_SET)
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, 1024 * 1024):
        digest.update(chunk)
    return digest.hexdigest()


def activate_verified_destination(
    destination: Path,
    current: Path,
    rescue: Path,
    receipt: dict[str, Any],
    *,
    parent_owner_uid: int,
    parent_group_gid: int,
    resume: bool,
) -> None:
    if current.parent != destination.parent or rescue.parent != destination.parent:
        raise SafetyError("restore activation paths must share the pinned parent")
    parent = destination.parent
    parent_metadata = require_directory(
        parent,
        "restore activation parent",
        owner_uid=parent_owner_uid,
        group_gid=parent_group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    if mode_of(parent_metadata) & 0o022:
        raise SafetyError("restore parent must not be group or other writable")
    destination_exists = destination.exists() and not destination.is_symlink()
    current_exists = current.exists() and not current.is_symlink()
    rescue_exists = rescue.exists() and not rescue.is_symlink()
    if any(path.is_symlink() for path in (destination, current, rescue)):
        raise SafetyError("restore activation path must not be a link")
    if resume and current_exists and rescue_exists and not destination_exists:
        if collect_restored_inventory(current) != receipt["inventory"]:
            raise SafetyError("activated restore differs from authenticated receipt")
        fsync_directory(parent)
        return
    if not destination_exists:
        raise SafetyError("verified restore staging is missing")
    if collect_restored_inventory(destination) != receipt["inventory"]:
        raise SafetyError("restore staging differs from authenticated receipt")
    if current_exists and rescue_exists:
        raise SafetyError("restore activation state is ambiguous")
    if not current_exists and not rescue_exists:
        raise SafetyError("restore activation has neither current nor rescue data")
    parent_fd = os.open(
        parent,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        destination_metadata = os.stat(
            destination.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if current_exists:
            current_metadata = os.stat(
                current.name,
                dir_fd=parent_fd,
                follow_symlinks=False,
            )
            if not stat.S_ISDIR(current_metadata.st_mode):
                raise SafetyError("current restore root must be a directory")
            os.rename(
                current.name,
                rescue.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
            os.fsync(parent_fd)
        elif not resume or not rescue_exists:
            raise SafetyError("restore activation state is not resumable")
        try:
            os.rename(
                destination.name,
                current.name,
                src_dir_fd=parent_fd,
                dst_dir_fd=parent_fd,
            )
        except BaseException:
            if current_exists:
                os.rename(
                    rescue.name,
                    current.name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                os.fsync(parent_fd)
            raise
        os.fsync(parent_fd)
        activated = os.stat(
            current.name,
            dir_fd=parent_fd,
            follow_symlinks=False,
        )
        if (activated.st_dev, activated.st_ino) != (
            destination_metadata.st_dev,
            destination_metadata.st_ino,
        ):
            raise SafetyError("activated restore identity differs from verified staging")
    finally:
        os.close(parent_fd)


def command_archive_restore(arguments: argparse.Namespace) -> int:
    archive_path = Path(arguments.archive)
    receipt_path = Path(arguments.receipt)
    destination = require_canonical_absolute(Path(arguments.destination), "restore destination", exists=False)
    require_directory(
        destination.parent,
        "restore parent",
        owner_uid=arguments.parent_owner_uid,
        group_gid=arguments.parent_group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    destination_preexisting = destination.exists() or destination.is_symlink()
    if destination_preexisting and not arguments.resume:
        raise SafetyError("restore destination already exists")
    receipt_fd, receipt_metadata = open_regular_nofollow(
        receipt_path,
        "archive receipt",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o600},
        max_bytes=MAX_RECEIPT_BYTES,
    )
    try:
        receipt = validate_archive_receipt(
            parse_json(
                read_pinned(
                    receipt_fd,
                    receipt_metadata,
                    "archive receipt",
                    max_bytes=MAX_RECEIPT_BYTES,
                ),
                "archive receipt",
            )
        )
    finally:
        os.close(receipt_fd)
    archive_fd, archive_metadata = open_regular_nofollow(
        archive_path,
        "archive",
        owner_uid=arguments.owner_uid,
        group_gid=arguments.group_gid,
        modes={0o600},
    )
    expected_identity = receipt["archive"]
    actual_identity = {
        "device": archive_metadata.st_dev,
        "inode": archive_metadata.st_ino,
        "uid": archive_metadata.st_uid,
        "gid": archive_metadata.st_gid,
        "mode": mode_of(archive_metadata),
        "nlink": archive_metadata.st_nlink,
        "size": archive_metadata.st_size,
    }
    if any(actual_identity[key] != expected_identity[key] for key in actual_identity):
        os.close(archive_fd)
        raise SafetyError("archive identity does not match authenticated receipt")
    initial_digest = file_digest_from_fd(archive_fd)
    if initial_digest != expected_identity["sha256"]:
        os.close(archive_fd)
        raise SafetyError("archive digest does not match authenticated receipt")
    records = {record["path"]: record for record in receipt["inventory"]}
    if arguments.resume:
        if arguments.activate_current is None or arguments.rescue is None:
            os.close(archive_fd)
            raise SafetyError("resumable restore requires current and rescue paths")
        current = require_canonical_absolute(
            Path(arguments.activate_current),
            "current data root",
            exists=False,
        )
        rescue = require_canonical_absolute(
            Path(arguments.rescue),
            "restore rescue path",
            exists=False,
        )
        current_exists = current.exists() and not current.is_symlink()
        rescue_exists = rescue.exists() and not rescue.is_symlink()
        if current.is_symlink() or rescue.is_symlink() or destination.is_symlink():
            os.close(archive_fd)
            raise SafetyError("resumable restore path must not be a link")
        if current_exists and rescue_exists and not destination_preexisting:
            try:
                activate_verified_destination(
                    destination,
                    current,
                    rescue,
                    receipt,
                    parent_owner_uid=arguments.parent_owner_uid,
                    parent_group_gid=arguments.parent_group_gid,
                    resume=True,
                )
                return 0
            finally:
                os.close(archive_fd)
        if destination_preexisting:
            try:
                complete_inventory = collect_restored_inventory(destination)
            except SafetyError:
                complete_inventory = None
            if complete_inventory == receipt["inventory"]:
                try:
                    activate_verified_destination(
                        destination,
                        current,
                        rescue,
                        receipt,
                        parent_owner_uid=arguments.parent_owner_uid,
                        parent_group_gid=arguments.parent_group_gid,
                        resume=True,
                    )
                    return 0
                finally:
                    os.close(archive_fd)
            if current_exists == rescue_exists:
                os.close(archive_fd)
                raise SafetyError("partial restore staging has an ambiguous activation state")
            parent_fd = os.open(
                destination.parent,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                remove_owned_tree(
                    parent_fd,
                    destination.name,
                    owner_uid=arguments.destination_owner_uid,
                    group_gid=arguments.destination_group_gid,
                    label="partial restore staging",
                )
            finally:
                os.close(parent_fd)
            destination_preexisting = False
    try:
        destination.mkdir(mode=0o700)
        if os.geteuid() == 0:
            os.chown(
                destination,
                arguments.destination_owner_uid,
                arguments.destination_group_gid,
            )
        destination_fd = os.open(
            destination,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        )
        try:
            os.lseek(archive_fd, 0, os.SEEK_SET)
            archive_stream = os.fdopen(os.dup(archive_fd), "rb")
            with archive_stream, tarfile.open(fileobj=archive_stream, mode="r:gz") as archive:
                members = archive.getmembers()
                member_paths = [member.name.rstrip("/") for member in members]
                expected_paths = [record["path"] for record in receipt["inventory"] if record["path"] != "."]
                if member_paths != expected_paths:
                    raise SafetyError("archive member inventory mismatch")
                opened_directories: dict[str, int] = {".": destination_fd}
                try:
                    for member in members:
                        name = member.name.rstrip("/")
                        record = records[name]
                        parts = PurePosixPath(name).parts
                        parent_name = "." if len(parts) == 1 else "/".join(parts[:-1])
                        parent_fd = opened_directories.get(parent_name)
                        if parent_fd is None:
                            raise SafetyError("archive parent inventory is invalid")
                        leaf = parts[-1]
                        if member.uid != record["uid"] or member.gid != record["gid"] or member.mode != record["mode"]:
                            raise SafetyError("archive member metadata mismatch")
                        if record["kind"] == "directory":
                            if not member.isdir():
                                raise SafetyError("archive member type mismatch")
                            os.mkdir(leaf, 0o700, dir_fd=parent_fd)
                            child_fd = os.open(
                                leaf,
                                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                                dir_fd=parent_fd,
                            )
                            opened_directories[name] = child_fd
                        else:
                            if not member.isreg() or member.size != record["size"]:
                                raise SafetyError("archive member type or size mismatch")
                            source = archive.extractfile(member)
                            if source is None:
                                raise SafetyError("archive member could not be read")
                            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_CLOEXEC", 0)
                            if hasattr(os, "O_NOFOLLOW"):
                                flags |= os.O_NOFOLLOW
                            target_fd = os.open(leaf, flags, 0o600, dir_fd=parent_fd)
                            digest = hashlib.sha256()
                            size = 0
                            try:
                                while chunk := source.read(1024 * 1024):
                                    digest.update(chunk)
                                    size += len(chunk)
                                    os.write(target_fd, chunk)
                                os.fchmod(target_fd, record["mode"])
                                if os.geteuid() == 0:
                                    os.fchown(target_fd, record["uid"], record["gid"])
                                os.fsync(target_fd)
                                metadata = os.fstat(target_fd)
                                if metadata.st_nlink != 1:
                                    raise SafetyError("restored file link count is invalid")
                            finally:
                                os.close(target_fd)
                                source.close()
                            if size != record["size"] or digest.hexdigest() != record["sha256"]:
                                raise SafetyError("restored file identity mismatch")
                    for name in reversed(expected_paths):
                        record = records[name]
                        if record["kind"] != "directory":
                            continue
                        descriptor = opened_directories[name]
                        os.fchmod(descriptor, record["mode"])
                        if os.geteuid() == 0:
                            os.fchown(descriptor, record["uid"], record["gid"])
                        os.fsync(descriptor)
                    root_record = records["."]
                    os.fchmod(destination_fd, root_record["mode"])
                    if os.geteuid() == 0:
                        os.fchown(destination_fd, root_record["uid"], root_record["gid"])
                    os.fsync(destination_fd)
                finally:
                    for name, descriptor in opened_directories.items():
                        if name != ".":
                            os.close(descriptor)
        finally:
            os.close(destination_fd)
        after = os.fstat(archive_fd)
        if identity(after) != identity(archive_metadata) or after.st_mtime_ns != archive_metadata.st_mtime_ns:
            raise SafetyError("archive identity changed during extraction")
        if file_digest_from_fd(archive_fd) != expected_identity["sha256"]:
            raise SafetyError("archive digest changed during extraction")
        if collect_restored_inventory(destination) != receipt["inventory"]:
            raise SafetyError("restored complete inventory differs from authenticated receipt")
        if arguments.activate_current is not None or arguments.rescue is not None:
            if arguments.activate_current is None or arguments.rescue is None:
                raise SafetyError("restore activation requires current and rescue paths")
            current = require_canonical_absolute(
                Path(arguments.activate_current),
                "current data root",
            )
            rescue = require_canonical_absolute(
                Path(arguments.rescue),
                "restore rescue path",
                exists=False,
            )
            activate_verified_destination(
                destination,
                current,
                rescue,
                receipt,
                parent_owner_uid=arguments.parent_owner_uid,
                parent_group_gid=arguments.parent_group_gid,
                resume=arguments.resume,
            )
        fsync_directory(destination.parent)
        return 0
    except BaseException:
        if (
            not destination_preexisting
            and destination.exists()
            and not destination.is_symlink()
        ):
            parent_fd = os.open(
                destination.parent,
                os.O_RDONLY
                | getattr(os, "O_DIRECTORY", 0)
                | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                remove_owned_tree(
                    parent_fd,
                    destination.name,
                    owner_uid=arguments.destination_owner_uid,
                    group_gid=arguments.destination_group_gid,
                    label="failed restore staging",
                )
            finally:
                os.close(parent_fd)
        raise
    finally:
        os.close(archive_fd)


def read_repository_file(repository: Path, relative: str, label: str) -> bytes:
    relative_path = PurePosixPath(relative)
    if relative_path.is_absolute() or any(
        part in {"", ".", ".."} or not SAFE_NAME.fullmatch(part)
        for part in relative_path.parts
    ):
        raise SafetyError(f"{label} path is invalid")
    path = repository.joinpath(*relative_path.parts)
    path_status = path.lstat()
    descriptor, metadata = open_regular_nofollow(
        path,
        label,
        owner_uid=path_status.st_uid,
        group_gid=path_status.st_gid,
        modes={mode_of(path_status)},
        max_bytes=MAX_MOD_METADATA_BYTES,
    )
    try:
        return read_pinned(
            descriptor,
            metadata,
            label,
            max_bytes=MAX_MOD_METADATA_BYTES,
        )
    finally:
        os.close(descriptor)


def release_policy_pack_url(repository: Path) -> str:
    payload = read_repository_file(
        repository,
        "tools/release-policy.env",
        "accepted release policy",
    )
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as error:
        raise SafetyError("accepted release policy is not UTF-8") from error
    values: dict[str, str] = {}
    for line in lines:
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise SafetyError("accepted release policy is invalid")
        key, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", key) or not value or key in values:
            raise SafetyError("accepted release policy is invalid")
        values[key] = value
    pack_url = values.get("RELEASE_PACK_URL")
    if not isinstance(pack_url, str):
        raise SafetyError("accepted release policy Packwiz URL is missing")
    parsed = urllib.parse.urlsplit(pack_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or not parsed.path.endswith("/pack.toml")
    ):
        raise SafetyError("accepted release policy Packwiz URL is invalid")
    return pack_url


def accepted_server_mod_manifest(repository: Path) -> list[dict[str, Any]]:
    mods_root = repository / "mods"
    if not mods_root.is_dir() or mods_root.is_symlink():
        return []
    lock_payload = read_repository_file(
        repository,
        "tools/server-mod-manifest-lock.json",
        "accepted server-mod size lock",
    )
    try:
        size_lock = json.loads(lock_payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SafetyError("accepted server-mod size lock is invalid") from error
    if (
        not isinstance(size_lock, dict)
        or size_lock.get("format") != 1
        or not isinstance(size_lock.get("files"), list)
    ):
        raise SafetyError("accepted server-mod size lock is invalid")
    lock_by_metadata: dict[str, dict[str, Any]] = {}
    for record in size_lock["files"]:
        if not isinstance(record, dict) or set(record) != {
            "filename",
            "hash",
            "hash_format",
            "metadata_path",
            "size",
        }:
            raise SafetyError("accepted server-mod size lock is invalid")
        metadata_path = record.get("metadata_path")
        if not isinstance(metadata_path, str) or metadata_path in lock_by_metadata:
            raise SafetyError("accepted server-mod size lock is invalid")
        lock_by_metadata[metadata_path] = record

    result: list[dict[str, Any]] = []
    expected_metadata_paths: set[str] = set()
    for metadata_path in sorted(mods_root.glob("*.pw.toml")):
        relative = metadata_path.relative_to(repository).as_posix()
        payload = read_repository_file(repository, relative, "accepted Packwiz mod metadata")
        try:
            metadata = tomllib.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise SafetyError("accepted Packwiz mod metadata is invalid") from error
        if metadata.get("side", "both") == "client":
            continue
        filename = metadata.get("filename")
        download = metadata.get("download")
        if (
            not isinstance(filename, str)
            or not SAFE_NAME.fullmatch(filename)
            or not isinstance(download, dict)
        ):
            raise SafetyError("accepted Packwiz mod metadata is invalid")
        hash_format = download.get("hash-format")
        digest = download.get("hash")
        expected_length = {"sha1": 40, "sha256": 64, "sha512": 128}.get(hash_format)
        if (
            expected_length is None
            or not isinstance(digest, str)
            or not re.fullmatch(rf"[0-9a-f]{{{expected_length}}}", digest)
        ):
            raise SafetyError("accepted Packwiz mod digest is invalid")
        record = lock_by_metadata.get(relative)
        if (
            not isinstance(record, dict)
            or record.get("filename") != filename
            or record.get("hash_format") != hash_format
            or record.get("hash") != digest
            or not isinstance(record.get("size"), int)
            or isinstance(record.get("size"), bool)
            or record["size"] <= 0
        ):
            raise SafetyError("accepted server-mod size identity is invalid")
        expected_metadata_paths.add(relative)
        result.append(
            {
                "filename": filename,
                "hash_format": hash_format,
                "hash": digest,
                "size": record["size"],
            }
        )
    if set(lock_by_metadata) != expected_metadata_paths:
        raise SafetyError("accepted server-mod size lock inventory differs from Packwiz")
    result.sort(key=lambda record: record["filename"])
    return validate_server_mod_manifest(result)


def command_receipt_verify(arguments: argparse.Namespace) -> int:
    if not SHA40.fullmatch(arguments.expected_sha):
        raise SafetyError("accepted release revision is invalid")
    if not SHA256.fullmatch(arguments.receipt_sha256):
        raise SafetyError("accepted release receipt digest is invalid")
    repository = require_canonical_absolute(Path(arguments.repository), "repository")
    receipt_path = Path(arguments.receipt)
    descriptor, metadata = open_regular_nofollow(
        receipt_path,
        "accepted release receipt",
        owner_uid=arguments.receipt_owner_uid,
        group_gid=arguments.receipt_group_gid,
        modes={0o600, 0o640, 0o644},
        max_bytes=MAX_RECEIPT_BYTES,
    )
    try:
        payload = read_pinned(
            descriptor,
            metadata,
            "accepted release receipt",
            max_bytes=MAX_RECEIPT_BYTES,
        )
    finally:
        os.close(descriptor)
    if digest_bytes(payload) != arguments.receipt_sha256:
        raise SafetyError("accepted release receipt digest mismatch")
    receipt = parse_json(payload, "accepted release receipt")
    if payload != canonical_json_bytes(receipt):
        raise SafetyError("accepted release receipt is not canonical JSON")
    if (
        not isinstance(receipt, dict)
        or set(receipt) != {"format", "git_sha", "pack_url", "packwiz", "public_files", "version"}
        or receipt.get("format") != 1
    ):
        raise SafetyError("accepted release receipt format is invalid")
    if receipt.get("git_sha") != arguments.expected_sha:
        raise SafetyError("accepted release receipt revision mismatch")
    api_root = os.environ.get(
        "AFTERLIGHT_GITHUB_API_ROOT",
        "https://api.github.com/repos/Luskish/afterlight-pack",
    ).rstrip("/")
    expected_url = release_policy_pack_url(repository)
    if receipt.get("pack_url") != expected_url:
        raise SafetyError("accepted release receipt Packwiz URL mismatch")
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != arguments.expected_sha:
        raise SafetyError("repository HEAD does not equal the accepted release")
    clean = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if clean.returncode != 0 or clean.stdout:
        raise SafetyError("accepted release checkout is not clean")
    public = receipt_path.parent / "public"
    public_files = receipt.get("public_files")
    expected_public_names = {
        "AFTERLIGHT-prism-instance.zip",
        "AFTERLIGHT-curseforge.zip",
        "AFTERLIGHT.mrpack",
        "SHA256SUMS",
        "release-metadata.json",
    }
    if not isinstance(public_files, dict) or set(public_files) != expected_public_names:
        raise SafetyError("accepted release receipt public inventory is invalid")
    public_payloads: dict[str, bytes] = {}
    for name, record in public_files.items():
        if (
            not isinstance(name, str)
            or not SAFE_NAME.fullmatch(name)
            or not isinstance(record, dict)
            or set(record) != {"sha256", "size"}
            or not SHA256.fullmatch(str(record.get("sha256", "")))
            or not isinstance(record.get("size"), int)
            or record["size"] <= 0
        ):
            raise SafetyError("accepted release receipt public inventory is invalid")
        path = public / name
        file_descriptor, file_metadata = open_regular_nofollow(
            path,
            "accepted public artifact",
            owner_uid=arguments.receipt_owner_uid,
            group_gid=arguments.receipt_group_gid,
            modes={0o600, 0o640, 0o644},
        )
        try:
            actual_digest = file_digest_from_fd(file_descriptor)
            after = os.fstat(file_descriptor)
            if identity(after) != identity(file_metadata) or after.st_mtime_ns != file_metadata.st_mtime_ns:
                raise SafetyError("accepted public artifact changed during verification")
            artifact_payload = None
            if name == "release-metadata.json":
                artifact_payload = read_pinned(
                    file_descriptor,
                    file_metadata,
                    "accepted release metadata",
                    max_bytes=MAX_RECEIPT_BYTES,
                )
        finally:
            os.close(file_descriptor)
        if record.get("size") != file_metadata.st_size or record.get("sha256") != actual_digest:
            raise SafetyError("accepted public artifact identity mismatch")
        if artifact_payload is not None:
            public_payloads[name] = artifact_payload
    version = receipt.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+[.][0-9]+[.][0-9]+(?:-rc[.][0-9]+)?", version):
        raise SafetyError("accepted release version is invalid")
    packwiz = receipt.get("packwiz")
    if not isinstance(packwiz, dict) or set(packwiz) != {"bootstrap", "installer"}:
        raise SafetyError("accepted Packwiz identity is invalid")
    for label, record in packwiz.items():
        if (
            not isinstance(record, dict)
            or set(record) != {"version", "size", "sha256"}
            or not isinstance(record.get("version"), str)
            or not record["version"]
            or not isinstance(record.get("size"), int)
            or record["size"] <= 0
            or not SHA256.fullmatch(str(record.get("sha256", "")))
        ):
            raise SafetyError(f"accepted Packwiz {label} identity is invalid")
    release_metadata = parse_json(
        public_payloads["release-metadata.json"],
        "accepted release metadata",
    )
    if (
        not isinstance(release_metadata, dict)
        or release_metadata.get("git_sha") != arguments.expected_sha
        or release_metadata.get("version") != version
        or release_metadata.get("pack_url") != expected_url
        or release_metadata.get("packwiz") != packwiz
    ):
        raise SafetyError("accepted release metadata differs from the receipt")

    def fetch_json(url: str, label: str) -> Any:
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "AFTERLIGHT-deployment-verifier/1",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = response.read(MAX_RECEIPT_BYTES + 1)
        except OSError as error:
            raise SafetyError(f"{label} verification failed") from error
        if len(payload) > MAX_RECEIPT_BYTES:
            raise SafetyError(f"{label} response exceeds the size limit")
        try:
            return json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SafetyError(f"{label} response is invalid") from error

    tag_name = f"v{version}"
    tag_ref = fetch_json(
        f"{api_root}/git/ref/tags/{urllib.parse.quote(tag_name, safe='')}",
        "release tag",
    )
    tag_object = tag_ref.get("object") if isinstance(tag_ref, dict) else None
    if not isinstance(tag_object, dict) or tag_object.get("type") != "tag":
        raise SafetyError("release tag is not annotated")
    annotated = fetch_json(
        f"{api_root}/git/tags/{tag_object.get('sha', '')}",
        "annotated release tag",
    )
    tagged_object = annotated.get("object") if isinstance(annotated, dict) else None
    if not isinstance(tagged_object, dict) or tagged_object.get("sha") != arguments.expected_sha:
        raise SafetyError("release tag does not bind the accepted revision")
    release = fetch_json(
        f"{api_root}/releases/tags/{urllib.parse.quote(tag_name, safe='')}",
        "published release",
    )
    if (
        not isinstance(release, dict)
        or release.get("draft") is not False
        or release.get("tag_name") != tag_name
    ):
        raise SafetyError("accepted release is not published")
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise SafetyError("published release asset inventory is invalid")
    release_assets = {
        asset.get("name"): asset
        for asset in assets
        if isinstance(asset, dict) and isinstance(asset.get("name"), str)
    }
    if set(release_assets) != expected_public_names:
        raise SafetyError("published release asset inventory differs from acceptance")
    for name, record in public_files.items():
        asset = release_assets[name]
        if (
            asset.get("size") != record.get("size")
            or asset.get("digest") != f"sha256:{record.get('sha256')}"
        ):
            raise SafetyError("published release asset identity differs from acceptance")
    for branch in ("dev", "main"):
        query = urllib.parse.urlencode(
            {
                "branch": branch,
                "event": "push",
                "status": "success",
                "head_sha": arguments.expected_sha,
                "per_page": "20",
            }
        )
        runs = fetch_json(
            f"{api_root}/actions/workflows/pack-ci.yml/runs?{query}",
            f"accepted {branch} CI",
        )
        workflow_runs = runs.get("workflow_runs") if isinstance(runs, dict) else None
        if not isinstance(workflow_runs, list) or not any(
            isinstance(run, dict)
            and run.get("head_sha") == arguments.expected_sha
            and run.get("head_branch") == branch
            and run.get("event") == "push"
            and run.get("conclusion") == "success"
            for run in workflow_runs
        ):
            raise SafetyError(f"accepted {branch} CI evidence is missing")
    for relative in ("pack.toml", "index.toml"):
        local_path = repository / relative
        local_status = local_path.lstat()
        local_descriptor, local_metadata = open_regular_nofollow(
            local_path,
            f"accepted {relative}",
            owner_uid=local_status.st_uid,
            group_gid=local_status.st_gid,
            modes={mode_of(local_status)},
            max_bytes=MAX_RECEIPT_BYTES,
        )
        try:
            local = read_pinned(
                local_descriptor,
                local_metadata,
                f"accepted {relative}",
                max_bytes=MAX_RECEIPT_BYTES,
            )
        finally:
            os.close(local_descriptor)
        remote_url = (
            expected_url
            if relative == "pack.toml"
            else urllib.parse.urljoin(expected_url, "index.toml")
        )
        request = urllib.request.Request(
            remote_url,
            headers={"User-Agent": "AFTERLIGHT-deployment-verifier/1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                remote = response.read(len(local) + 1)
        except OSError as error:
            raise SafetyError("published Packwiz verification failed") from error
        if remote != local:
            raise SafetyError("published Packwiz bytes differ from accepted checkout")
    server_mods = accepted_server_mod_manifest(repository)
    print(canonical_json_bytes(server_mods).decode("utf-8"), end="")
    return 0


def hash_tree(root: Path) -> str:
    require_canonical_absolute(root, "tree root")
    records: list[list[str | int]] = []
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root).as_posix()
        metadata = path.lstat()
        if path.is_symlink():
            raise SafetyError("tree contains a link")
        if path.is_dir():
            records.append([relative, "directory", mode_of(metadata), metadata.st_uid, metadata.st_gid])
        elif path.is_file():
            if metadata.st_nlink != 1:
                raise SafetyError("tree file link count must equal one")
            descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                digest = file_digest_from_fd(descriptor)
                after = os.fstat(descriptor)
            finally:
                os.close(descriptor)
            if identity(after) != identity(metadata):
                raise SafetyError("tree file identity changed during read")
            records.append([relative, "file", metadata.st_size, digest])
        else:
            raise SafetyError("tree contains an unsupported entry")
    return digest_bytes(canonical_json_bytes(records))


def command_live_verify(arguments: argparse.Namespace) -> int:
    if not SHA40.fullmatch(arguments.expected_sha):
        raise SafetyError("live release revision is invalid")
    repository = require_canonical_absolute(Path(arguments.repository), "repository")
    data = require_canonical_absolute(Path(arguments.data), "server data")
    require_directory(
        data,
        "server data",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes=SAFE_DIRECTORY_MODES,
    )
    head = subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "--verify", "HEAD^{commit}"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    clean = subprocess.run(
        ["git", "-C", str(repository), "status", "--porcelain=v1", "--untracked-files=all"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if head.returncode != 0 or head.stdout.strip() != arguments.expected_sha or clean.returncode != 0 or clean.stdout:
        raise SafetyError("live release checkout is not the exact clean accepted revision")
    marker_path = data / ".afterlight-pack-sha"
    marker_descriptor, marker_metadata = open_regular_nofollow(
        marker_path,
        "live release marker",
        owner_uid=arguments.data_owner_uid,
        group_gid=arguments.data_group_gid,
        modes={0o600},
        max_bytes=128,
    )
    try:
        marker_payload = read_pinned(
            marker_descriptor,
            marker_metadata,
            "live release marker",
            max_bytes=128,
        )
    finally:
        os.close(marker_descriptor)
    if marker_payload != f"{arguments.expected_sha}\n".encode("ascii"):
        raise SafetyError("live release marker differs from the accepted revision")
    expected_quests = repository / "config" / "ftbquests" / "quests"
    installed_quests = data / "config" / "ftbquests" / "quests"
    if hash_tree(expected_quests) != hash_tree(installed_quests):
        raise SafetyError("live quest corpus differs from accepted checkout")
    manifest_json = getattr(arguments, "server_mod_manifest_json", None)
    if manifest_json is None:
        expected_manifest = accepted_server_mod_manifest(repository)
    else:
        try:
            parsed_manifest = json.loads(manifest_json)
        except json.JSONDecodeError as error:
            raise SafetyError("accepted server mod manifest is invalid") from error
        if isinstance(parsed_manifest, dict):
            parsed_manifest = parsed_manifest.get("server_mods")
        expected_manifest = validate_server_mod_manifest(parsed_manifest)
    expected_mods = {record["filename"]: record for record in expected_manifest}
    mods_root = data / "mods"
    actual_mods: set[str] = set()
    for path in mods_root.iterdir():
        metadata = path.lstat()
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
            raise SafetyError("live server mod inventory contains an unsafe entry")
        actual_mods.add(path.name)
        expected = expected_mods.get(path.name)
        if expected is None:
            continue
        flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        try:
            opened = os.fstat(descriptor)
            if identity(opened) != identity(metadata):
                raise SafetyError("live server mod identity changed during open")
            digest = hashlib.new(expected["hash_format"])
            size = 0
            while chunk := os.read(descriptor, 1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
            after = os.fstat(descriptor)
            if identity(after) != identity(opened) or after.st_mtime_ns != opened.st_mtime_ns:
                raise SafetyError("live server mod identity changed during verification")
        finally:
            os.close(descriptor)
        if size != expected["size"] or digest.hexdigest() != expected["hash"]:
            raise SafetyError("live server mod digest or size differs from acceptance")
    if actual_mods != set(expected_mods):
        raise SafetyError("live server mod inventory differs from accepted checkout")
    container_id = getattr(arguments, "container_id", None)
    started_at = getattr(arguments, "started_at", None)
    if not isinstance(container_id, str) or not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
        raise SafetyError("candidate container identity is invalid")
    if not isinstance(started_at, str):
        raise SafetyError("candidate container start time is invalid")
    try:
        parsed_start = datetime.datetime.fromisoformat(started_at.replace("Z", "+00:00"))
    except ValueError as error:
        raise SafetyError("candidate container start time is invalid") from error
    if parsed_start.tzinfo is None:
        raise SafetyError("candidate container start time is invalid")
    started_ns = int(parsed_start.timestamp() * 1_000_000_000)
    log_path = data / "logs" / "latest.log"
    log_descriptor = os.open(log_path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        log_metadata = os.fstat(log_descriptor)
        if not stat.S_ISREG(log_metadata.st_mode) or log_metadata.st_nlink != 1 or log_metadata.st_size > MAX_LOG_BYTES:
            raise SafetyError("live server log identity is invalid")
        if log_metadata.st_mtime_ns < started_ns:
            raise SafetyError("live server log predates the candidate container start")
        log_payload = read_pinned(
            log_descriptor,
            log_metadata,
            "live server log",
            max_bytes=MAX_LOG_BYTES,
        )
    finally:
        os.close(log_descriptor)
    try:
        log_text = log_payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise SafetyError("live server log is not UTF-8") from error
    load_pattern = re.compile(
        r"Loaded ([0-9]+) chapter groups, ([0-9]+) chapters, ([0-9]+) quests, ([0-9]+) reward tables"
    )
    load_match = load_pattern.search(log_text)
    if load_match is None:
        raise SafetyError("live FTB Quests load evidence is missing")
    if any(int(value) <= 0 for value in load_match.groups()[:3]):
        raise SafetyError("live FTB Quests load evidence requires positive quest counts")
    if any(
        "ftb quests" in line.casefold()
        and re.search(r"(?i)(?:^|[^a-z])(?:ERROR|FATAL)(?:[^a-z]|$)", line)
        for line in log_text.splitlines()
    ):
        raise SafetyError("live FTB Quests load evidence contains an error")
    print(
        canonical_json_bytes(
            {
                "quest_corpus_sha256": hash_tree(installed_quests),
                "server_mod_count": len(actual_mods),
            }
        ).decode("utf-8"),
        end="",
    )
    return 0


def add_identity_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--owner-uid", type=int, required=True)
    parser.add_argument("--group-gid", type=int, required=True)


def add_state_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--state-dir-mode", type=lambda value: int(value, 8), default=0o750)
    parser.add_argument("--state-file-mode", type=lambda value: int(value, 8), default=0o640)
    add_identity_arguments(parser)
    parser.add_argument("--snapshot-owner-uid", type=int, required=True)
    parser.add_argument("--snapshot-group-gid", type=int, required=True)
    parser.add_argument("--snapshot-root-mode", type=lambda value: int(value, 8), default=0o700)
    parser.add_argument("--canonical-snapshot-root", type=Path, required=True)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command_name", required=True)

    lock = subparsers.add_parser("lock-run")
    lock.add_argument("--runtime-dir", type=Path, required=True)
    lock.add_argument("--runtime-mode", type=lambda value: int(value, 8), default=0o750)
    lock.add_argument("--lock-mode", type=lambda value: int(value, 8), default=0o660)
    lock.add_argument("--timeout", type=float, default=DEFAULT_TRANSACTION_TIMEOUT_SECONDS)
    lock.add_argument("--termination-grace", type=float, default=TERMINATION_GRACE_SECONDS)
    add_identity_arguments(lock)
    lock.add_argument("command", nargs=argparse.REMAINDER)
    lock.set_defaults(handler=command_lock_run)

    lock_verify = subparsers.add_parser("lock-verify")
    lock_verify.add_argument("--runtime-dir", type=Path, required=True)
    lock_verify.add_argument("--runtime-mode", type=lambda value: int(value, 8), default=0o700)
    lock_verify.add_argument("--lock-mode", type=lambda value: int(value, 8), default=0o600)
    lock_verify.add_argument("--lock-fd", required=True)
    add_identity_arguments(lock_verify)
    lock_verify.set_defaults(handler=command_lock_verify)

    run = subparsers.add_parser("run-command")
    run.add_argument("--timeout", type=float, default=DEFAULT_COMMAND_TIMEOUT_SECONDS)
    run.add_argument("command", nargs=argparse.REMAINDER)
    run.set_defaults(handler=command_run)

    create = subparsers.add_parser("authority-create")
    add_state_arguments(create)
    create.add_argument("--expected-sha", required=True)
    create.add_argument("--prior-sha", required=True)
    create.add_argument("--snapshot-root", type=Path, required=True)
    create.add_argument("--receipt-sha256", required=True)
    create.add_argument("--data-root", type=Path)
    create.add_argument("--data-owner-uid", type=int)
    create.add_argument("--data-group-gid", type=int)
    create.add_argument("--server-mod-manifest-json")
    create.set_defaults(handler=command_authority_create)

    status_parser = subparsers.add_parser("authority-status")
    add_state_arguments(status_parser)
    status_parser.add_argument("--print-json", action="store_true")
    status_parser.add_argument(
        "--field",
        choices=(
            "transaction_id",
            "status",
            "phase",
            "gate_comment",
            "expected_sha",
            "prior_sha",
            "snapshot_dir",
            "original_data",
            "server_mods",
            "data_mutated",
        ),
    )
    status_parser.set_defaults(handler=command_authority_status)

    update = subparsers.add_parser("authority-update")
    add_state_arguments(update)
    update.add_argument("--transaction-id", required=True)
    update.add_argument("--status", choices=("pending", "quarantine"))
    update.add_argument("--phase")
    update.add_argument("--snapshot-dir")
    update.add_argument("--data-mutated", type=lambda value: value == "true")
    update.add_argument("--service", choices=("minecraft", "backup"))
    update.add_argument("--restart-disabled", type=lambda value: value == "true")
    update.add_argument("--stopped", type=lambda value: value == "true")
    update.set_defaults(handler=command_authority_update)

    complete = subparsers.add_parser("authority-complete")
    add_state_arguments(complete)
    complete.add_argument("--transaction-id", required=True)
    complete.set_defaults(handler=command_authority_complete)

    recovery_original = subparsers.add_parser("recovery-original-verify")
    add_state_arguments(recovery_original)
    recovery_original.add_argument("--transaction-id", required=True)
    recovery_original.add_argument("--data", type=Path, required=True)
    recovery_original.add_argument("--data-owner-uid", type=int, required=True)
    recovery_original.add_argument("--data-group-gid", type=int, required=True)
    recovery_original.set_defaults(handler=command_recovery_original_verify)

    snapshot_create = subparsers.add_parser("snapshot-create")
    snapshot_create.add_argument("--snapshot-root", type=Path, required=True)
    snapshot_create.add_argument("--name", required=True)
    add_identity_arguments(snapshot_create)
    snapshot_create.set_defaults(handler=command_snapshot_create)

    release_marker = subparsers.add_parser("release-marker-write")
    release_marker.add_argument("--data", type=Path, required=True)
    release_marker.add_argument("--revision", required=True)
    add_identity_arguments(release_marker)
    release_marker.set_defaults(handler=command_release_marker_write)

    release_marker_read = subparsers.add_parser("release-marker-read")
    release_marker_read.add_argument("--data", type=Path, required=True)
    add_identity_arguments(release_marker_read)
    release_marker_read.set_defaults(handler=command_release_marker_read)

    snapshot_complete = subparsers.add_parser("snapshot-complete")
    snapshot_complete.add_argument("--snapshot", type=Path, required=True)
    snapshot_complete.add_argument("--transaction-id", required=True)
    snapshot_complete.add_argument("--completed-at", type=int)
    add_identity_arguments(snapshot_complete)
    snapshot_complete.set_defaults(handler=command_snapshot_complete)

    snapshot_prune = subparsers.add_parser("snapshot-prune")
    snapshot_prune.add_argument("--snapshot-root", type=Path, required=True)
    snapshot_prune.add_argument("--older-than", type=int, required=True)
    add_identity_arguments(snapshot_prune)
    snapshot_prune.set_defaults(handler=command_snapshot_prune)

    archive_create = subparsers.add_parser("archive-create")
    archive_create.add_argument("--source", type=Path, required=True)
    archive_create.add_argument("--archive", type=Path, required=True)
    archive_create.add_argument("--receipt", type=Path, required=True)
    add_identity_arguments(archive_create)
    archive_create.add_argument("--source-owner-uid", type=int)
    archive_create.add_argument("--source-group-gid", type=int)
    archive_create.set_defaults(handler=command_archive_create)

    archive_restore = subparsers.add_parser("archive-restore")
    archive_restore.add_argument("--archive", type=Path, required=True)
    archive_restore.add_argument("--receipt", type=Path, required=True)
    archive_restore.add_argument("--destination", type=Path, required=True)
    archive_restore.add_argument("--activate-current", type=Path)
    archive_restore.add_argument("--rescue", type=Path)
    archive_restore.add_argument("--resume", action="store_true")
    add_identity_arguments(archive_restore)
    archive_restore.add_argument("--parent-owner-uid", type=int)
    archive_restore.add_argument("--parent-group-gid", type=int)
    archive_restore.add_argument("--destination-owner-uid", type=int)
    archive_restore.add_argument("--destination-group-gid", type=int)
    archive_restore.set_defaults(handler=command_archive_restore)

    receipt = subparsers.add_parser("receipt-verify")
    receipt.add_argument("--repository", type=Path, required=True)
    receipt.add_argument("--receipt", type=Path, required=True)
    receipt.add_argument("--receipt-sha256", required=True)
    receipt.add_argument("--expected-sha", required=True)
    receipt.add_argument("--receipt-owner-uid", type=int, required=True)
    receipt.add_argument("--receipt-group-gid", type=int, required=True)
    receipt.set_defaults(handler=command_receipt_verify)

    live = subparsers.add_parser("live-verify")
    live.add_argument("--repository", type=Path, required=True)
    live.add_argument("--data", type=Path, required=True)
    live.add_argument("--expected-sha", required=True)
    live.add_argument("--container-id", required=True)
    live.add_argument("--started-at", required=True)
    live.add_argument("--data-owner-uid", type=int, required=True)
    live.add_argument("--data-group-gid", type=int, required=True)
    live.add_argument("--server-mod-manifest-json")
    live.set_defaults(handler=command_live_verify)
    return parser


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()
    if arguments.command_name == "archive-create":
        if arguments.source_owner_uid is None:
            arguments.source_owner_uid = arguments.owner_uid
        if arguments.source_group_gid is None:
            arguments.source_group_gid = arguments.group_gid
    if arguments.command_name == "archive-restore":
        if arguments.parent_owner_uid is None:
            arguments.parent_owner_uid = arguments.owner_uid
        if arguments.parent_group_gid is None:
            arguments.parent_group_gid = arguments.group_gid
        if arguments.destination_owner_uid is None:
            arguments.destination_owner_uid = arguments.owner_uid
        if arguments.destination_group_gid is None:
            arguments.destination_group_gid = arguments.group_gid
    if getattr(arguments, "command", None) and arguments.command[0] == "--":
        arguments.command = arguments.command[1:]
    try:
        return arguments.handler(arguments)
    except (SafetyError, OSError, subprocess.SubprocessError, tarfile.TarError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
