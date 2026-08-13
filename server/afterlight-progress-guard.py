#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
MANIFEST_NAME = "progress-manifest.json"
SAFE_COMPONENT = re.compile(r"^[A-Za-z0-9._-]+$")
HASH_PATTERN = re.compile(r"^[0-9a-f]{64}$")
MAX_DOCUMENT_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 16 * 1024 * 1024
NUMBER_PATTERN = re.compile(
    r"^([+-]?(?:(?:[0-9]+(?:\.[0-9]*)?)|(?:\.[0-9]+))"
    r"(?:[eE][+-]?[0-9]+)?)([bBsSlLfFdD]?)$"
)


class GuardError(ValueError):
    pass


@dataclass(frozen=True)
class Number:
    kind: str
    value: int | float


@dataclass(frozen=True)
class State:
    documents: tuple[dict[str, str], ...]
    filesystem: tuple[dict[str, str | int], ...]
    canonical_sha256: str
    snapshot_sha256: str


class SnbtParser:
    def __init__(self, source: str) -> None:
        self.source = source
        self.offset = 0

    def parse(self) -> Any:
        value = self._value()
        self._space()
        if self.offset != len(self.source):
            raise GuardError("parse failure")
        return value

    def _space(self) -> None:
        while self.offset < len(self.source) and self.source[self.offset].isspace():
            self.offset += 1

    def _peek(self) -> str | None:
        self._space()
        if self.offset >= len(self.source):
            return None
        return self.source[self.offset]

    def _take(self, expected: str | None = None) -> str:
        self._space()
        if self.offset >= len(self.source):
            raise GuardError("parse failure")
        value = self.source[self.offset]
        if expected is not None and value != expected:
            raise GuardError("parse failure")
        self.offset += 1
        return value

    def _value(self) -> Any:
        character = self._peek()
        if character == "{":
            return self._compound()
        if character == "[":
            return self._list()
        if character in {'"', "'"}:
            return self._quoted()
        if character is None:
            raise GuardError("parse failure")
        token = self._bare()
        lowered = token.lower()
        if lowered == "true":
            return True
        if lowered == "false":
            return False
        if re.fullmatch(r"[+-]?(?:nan|infinity)[fd]?", lowered):
            raise GuardError("parse failure")
        matched = NUMBER_PATTERN.fullmatch(token)
        if matched is None:
            return token
        return parse_number(matched.group(1), matched.group(2))

    def _compound(self) -> dict[str, Any]:
        self._take("{")
        result: dict[str, Any] = {}
        if self._peek() == "}":
            self._take("}")
            return result
        while True:
            key = self._key()
            if key in result:
                raise GuardError("parse failure: duplicate key")
            self._take(":")
            result[key] = self._value()
            character = self._take()
            if character == "}":
                return result
            if character != ",":
                raise GuardError("parse failure")
            if self._peek() == "}":
                self._take("}")
                return result

    def _key(self) -> str:
        character = self._peek()
        if character in {'"', "'"}:
            return self._quoted()
        key = self._bare()
        if not key:
            raise GuardError("parse failure")
        return key

    def _list(self) -> Any:
        self._take("[")
        saved_offset = self.offset
        character = self._peek()
        if character is not None and character not in "]{[\"'":
            token = self._bare()
            if token.upper() in {"B", "I", "L"} and self._peek() == ";":
                self._take(";")
                return self._typed_array(token.upper())
            self.offset = saved_offset
        if self._peek() == "]":
            self._take("]")
            return []
        result = []
        while True:
            result.append(self._value())
            character = self._take()
            if character == "]":
                return result
            if character != ",":
                raise GuardError("parse failure")
            if self._peek() == "]":
                self._take("]")
                return result

    def _typed_array(self, kind: str) -> tuple[str, list[Number]]:
        expected_kind = {"B": "byte", "I": "int", "L": "long"}[kind]
        result: list[Number] = []
        if self._peek() == "]":
            self._take("]")
            return (f"{expected_kind}_array", result)
        while True:
            value = self._value()
            if not isinstance(value, Number):
                raise GuardError("parse failure")
            if kind == "B" and value.kind not in {"byte", "int"}:
                raise GuardError("parse failure")
            if kind == "I" and value.kind != "int":
                raise GuardError("parse failure")
            if kind == "L" and value.kind not in {"long", "int"}:
                raise GuardError("parse failure")
            result.append(Number(expected_kind, value.value))
            character = self._take()
            if character == "]":
                return (f"{expected_kind}_array", result)
            if character != ",":
                raise GuardError("parse failure")

    def _bare(self) -> str:
        self._space()
        start = self.offset
        while self.offset < len(self.source):
            character = self.source[self.offset]
            if character.isspace() or character in "{}[],:;":
                break
            self.offset += 1
        if self.offset == start:
            raise GuardError("parse failure")
        return self.source[start:self.offset]

    def _quoted(self) -> str:
        quote = self._take()
        result: list[str] = []
        escape_map = {
            '"': '"',
            "'": "'",
            "\\": "\\",
            "/": "/",
            "b": "\b",
            "f": "\f",
            "n": "\n",
            "r": "\r",
            "t": "\t",
        }
        while self.offset < len(self.source):
            character = self.source[self.offset]
            self.offset += 1
            if character == quote:
                return "".join(result)
            if character != "\\":
                result.append(character)
                continue
            if self.offset >= len(self.source):
                raise GuardError("parse failure")
            escaped = self.source[self.offset]
            self.offset += 1
            if escaped == "u":
                digits = self.source[self.offset:self.offset + 4]
                if len(digits) != 4 or not re.fullmatch(r"[0-9A-Fa-f]{4}", digits):
                    raise GuardError("parse failure")
                result.append(chr(int(digits, 16)))
                self.offset += 4
            elif escaped in escape_map:
                result.append(escape_map[escaped])
            else:
                raise GuardError("parse failure")
        raise GuardError("parse failure")


def parse_number(source: str, suffix: str) -> Number:
    suffix = suffix.lower()
    if suffix in {"f", "d"} or "." in source or "e" in source.lower():
        value = float(source)
        if not math.isfinite(value):
            raise GuardError("parse failure")
        return Number("float" if suffix == "f" else "double", value)
    value = int(source, 10)
    kind = {"b": "byte", "s": "short", "l": "long"}.get(suffix, "int")
    bounds = {
        "byte": (-128, 127),
        "short": (-32768, 32767),
        "int": (-(2**31), 2**31 - 1),
        "long": (-(2**63), 2**63 - 1),
    }
    minimum, maximum = bounds[kind]
    if value < minimum or value > maximum:
        raise GuardError("parse failure")
    return Number(kind, value)


def duplicate_safe_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise GuardError("parse failure: duplicate key")
        result[key] = value
    return result


def parse_json_float(source: str) -> Number:
    value = float(source)
    if not math.isfinite(value):
        raise GuardError("parse failure")
    return Number("json_float", value)


def parse_document(payload: bytes, suffix: str) -> Any:
    try:
        source = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise GuardError("parse failure") from error
    try:
        if suffix == ".snbt":
            return SnbtParser(source).parse()
        if suffix == ".json":
            return json.loads(
                source,
                object_pairs_hook=duplicate_safe_object,
                parse_int=lambda value: Number("json_int", int(value, 10)),
                parse_float=parse_json_float,
                parse_constant=lambda _value: (_ for _ in ()).throw(
                    GuardError("parse failure")
                ),
            )
    except GuardError:
        raise
    except (ValueError, RecursionError) as error:
        raise GuardError("parse failure") from error
    raise GuardError("unsupported progress document format")


def canonical_value(value: Any) -> Any:
    if isinstance(value, dict):
        return [
            "compound",
            [[key, canonical_value(value[key])] for key in sorted(value)],
        ]
    if isinstance(value, tuple) and len(value) == 2 and value[0].endswith("_array"):
        return [value[0], [canonical_value(item) for item in value[1]]]
    if isinstance(value, list):
        return ["list", [canonical_value(item) for item in value]]
    if isinstance(value, Number):
        normalized = repr(value.value) if isinstance(value.value, float) else str(value.value)
        return ["number", value.kind, normalized]
    if isinstance(value, bool):
        return ["boolean", value]
    if value is None:
        return ["null"]
    if isinstance(value, str):
        return ["string", value]
    raise GuardError("parse failure")


def digest_json(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def checked_root(path: Path, label: str) -> tuple[Path, os.stat_result]:
    if not path.is_absolute():
        raise GuardError(f"{label} must be absolute")
    try:
        metadata = path.lstat()
    except OSError as error:
        raise GuardError(f"{label} must be a real directory") from error
    if not stat.S_ISDIR(metadata.st_mode):
        raise GuardError(f"{label} must be a real directory")
    if path.resolve() != path:
        raise GuardError(f"{label} must be canonical")
    return path, metadata


def path_digest(relative: str) -> str:
    return hashlib.sha256(relative.casefold().encode("utf-8")).hexdigest()


def filesystem_record(
    relative: str,
    kind: str,
    metadata: os.stat_result,
) -> dict[str, str | int]:
    return {
        "path_sha256": path_digest(relative),
        "kind": kind,
        "mode": stat.S_IMODE(metadata.st_mode),
        "uid": metadata.st_uid,
        "gid": metadata.st_gid,
        "nlink": metadata.st_nlink,
    }


def opened_identity(metadata: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        metadata.st_dev,
        metadata.st_ino,
        metadata.st_uid,
        metadata.st_gid,
        metadata.st_nlink,
        metadata.st_size,
    )


def open_directory_at(parent_fd: int, name: str, expected: os.stat_result) -> int:
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=parent_fd)
    except OSError as error:
        raise GuardError("progress directory open failure") from error
    opened = os.fstat(descriptor)
    if (opened.st_dev, opened.st_ino) != (expected.st_dev, expected.st_ino):
        os.close(descriptor)
        raise GuardError("progress directory identity changed during open")
    return descriptor


def read_document_at(
    directory_fd: int,
    name: str,
    expected: os.stat_result,
) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
    except OSError as error:
        raise GuardError("progress document no-follow open failure") from error
    try:
        opened = os.fstat(descriptor)
        if (
            opened_identity(opened) != opened_identity(expected)
            or opened.st_mtime_ns != expected.st_mtime_ns
        ):
            raise GuardError("progress document identity changed during open")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, MAX_DOCUMENT_BYTES + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > MAX_DOCUMENT_BYTES:
                raise GuardError("progress document exceeds size limit")
        after = os.fstat(descriptor)
        if (
            opened_identity(after) != opened_identity(opened)
            or after.st_mtime_ns != opened.st_mtime_ns
        ):
            raise GuardError("progress document changed during read")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def collect_state(world: Path) -> State:
    _world, world_metadata = checked_root(world, "world")
    world_fd = os.open(
        world,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    records: list[dict[str, str]] = []
    filesystem: list[dict[str, str | int]] = [
        filesystem_record("world", "directory", world_metadata)
    ]
    identifiers: set[str] = set()
    try:
        for root_name in ("ftbquests", "ftbteams"):
            try:
                root_metadata = os.stat(
                    root_name,
                    dir_fd=world_fd,
                    follow_symlinks=False,
                )
            except OSError as error:
                raise GuardError("progress root must be a real directory") from error
            if not stat.S_ISDIR(root_metadata.st_mode):
                raise GuardError("progress root must be a real directory")
            if (
                root_metadata.st_uid != world_metadata.st_uid
                or root_metadata.st_gid != world_metadata.st_gid
            ):
                raise GuardError("progress root owner or group mismatch")
            filesystem.append(filesystem_record(root_name, "directory", root_metadata))
            root_fd = open_directory_at(world_fd, root_name, root_metadata)
            try:
                scan_directory(
                    root_fd,
                    root_name,
                    records,
                    filesystem,
                    identifiers,
                    expected_uid=world_metadata.st_uid,
                    expected_gid=world_metadata.st_gid,
                )
            finally:
                os.close(root_fd)
    finally:
        os.close(world_fd)
    records.sort(key=lambda item: item["path_sha256"])
    filesystem.sort(key=lambda item: str(item["path_sha256"]))
    canonical_sha256 = digest_json(
        [
            [record["path_sha256"], record["canonical_sha256"]]
            for record in records
        ]
    )
    snapshot_sha256 = digest_json(
        {
            "canonical_sha256": canonical_sha256,
            "filesystem": filesystem,
        }
    )
    return State(tuple(records), tuple(filesystem), canonical_sha256, snapshot_sha256)


def scan_directory(
    directory_fd: int,
    relative: str,
    records: list[dict[str, str]],
    filesystem: list[dict[str, str | int]],
    identifiers: set[str],
    *,
    expected_uid: int,
    expected_gid: int,
) -> None:
    try:
        names = sorted(os.listdir(directory_fd))
    except OSError as error:
        raise GuardError("progress tree scan failure") from error
    for name in names:
        if not SAFE_COMPONENT.fullmatch(name):
            raise GuardError("unsafe progress path")
        child_relative = f"{relative}/{name}"
        try:
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        except OSError as error:
            raise GuardError("progress tree scan failure") from error
        if metadata.st_uid != expected_uid or metadata.st_gid != expected_gid:
            raise GuardError("progress tree owner or group mismatch")
        if stat.S_ISDIR(metadata.st_mode):
            filesystem.append(filesystem_record(child_relative, "directory", metadata))
            child_fd = open_directory_at(directory_fd, name, metadata)
            try:
                scan_directory(
                    child_fd,
                    child_relative,
                    records,
                    filesystem,
                    identifiers,
                    expected_uid=expected_uid,
                    expected_gid=expected_gid,
                )
                after = os.fstat(child_fd)
                if opened_identity(after) != opened_identity(metadata):
                    raise GuardError("progress directory changed during scan")
            finally:
                os.close(child_fd)
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise GuardError("link in progress tree")
        if not stat.S_ISREG(metadata.st_mode):
            raise GuardError("unsupported progress tree entry")
        if metadata.st_nlink != 1:
            raise GuardError("progress document link count must equal one")
        filesystem.append(filesystem_record(child_relative, "file", metadata))
        suffix = Path(name).suffix.lower()
        if suffix not in {".snbt", ".json"}:
            raise GuardError("unsupported progress document format")
        folded = child_relative.casefold()
        if folded in identifiers:
            raise GuardError("duplicate document identifier")
        identifiers.add(folded)
        payload = read_document_at(directory_fd, name, metadata)
        parsed = parse_document(payload, suffix)
        records.append(
            {
                "path_sha256": path_digest(child_relative),
                "byte_sha256": hashlib.sha256(payload).hexdigest(),
                "canonical_sha256": digest_json(canonical_value(parsed)),
            }
        )


def checked_snapshot_directory(snapshot: Path, *, empty: bool) -> None:
    _snapshot, metadata = checked_root(snapshot, "snapshot directory")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise GuardError("snapshot directory must have mode 0700")
    entries = list(os.scandir(snapshot))
    if empty and entries:
        raise GuardError("snapshot directory must be empty")
    if not empty and {entry.name for entry in entries} != {MANIFEST_NAME}:
        raise GuardError("snapshot directory inventory mismatch")


def write_manifest(snapshot: Path, state: State) -> None:
    checked_snapshot_directory(snapshot, empty=True)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "document_count": len(state.documents),
        "documents": list(state.documents),
        "filesystem": list(state.filesystem),
        "canonical_sha256": state.canonical_sha256,
        "snapshot_sha256": state.snapshot_sha256,
    }
    payload = (
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    ).encode("utf-8")
    manifest_path = snapshot / MANIFEST_NAME
    descriptor = os.open(
        manifest_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    try:
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(descriptor)
    directory_fd = os.open(snapshot, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def read_manifest(snapshot: Path) -> dict[str, Any]:
    checked_snapshot_directory(snapshot, empty=False)
    manifest_path = snapshot / MANIFEST_NAME
    snapshot_metadata = snapshot.lstat()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(manifest_path, flags)
    except OSError as error:
        raise GuardError("snapshot manifest must be a real file") from error
    try:
        metadata = os.fstat(descriptor)
        path_metadata = manifest_path.lstat()
        if not stat.S_ISREG(metadata.st_mode):
            raise GuardError("snapshot manifest must be a real file")
        if (metadata.st_dev, metadata.st_ino) != (
            path_metadata.st_dev,
            path_metadata.st_ino,
        ):
            raise GuardError("snapshot manifest identity changed during open")
        if stat.S_IMODE(metadata.st_mode) != 0o600:
            raise GuardError("snapshot manifest mode must be 0600")
        if metadata.st_uid != snapshot_metadata.st_uid or metadata.st_gid != snapshot_metadata.st_gid:
            raise GuardError("snapshot manifest owner or group mismatch")
        if metadata.st_nlink != 1:
            raise GuardError("snapshot manifest link count must equal one")
        if metadata.st_size > MAX_MANIFEST_BYTES:
            raise GuardError("snapshot manifest exceeds size limit")
        payload = b""
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            payload += chunk
            if len(payload) > MAX_MANIFEST_BYTES:
                raise GuardError("snapshot manifest exceeds size limit")
        after = os.fstat(descriptor)
        if opened_identity(after) != opened_identity(metadata) or after.st_mtime_ns != metadata.st_mtime_ns:
            raise GuardError("snapshot manifest changed during read")
        manifest = json.loads(
            payload,
            object_pairs_hook=duplicate_safe_object,
        )
    except GuardError:
        raise
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise GuardError("snapshot manifest parse failure") from error
    finally:
        os.close(descriptor)
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "document_count",
        "documents",
        "filesystem",
        "canonical_sha256",
        "snapshot_sha256",
    }:
        raise GuardError("snapshot manifest schema mismatch")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise GuardError("snapshot manifest schema mismatch")
    documents = manifest["documents"]
    if not isinstance(documents, list) or manifest["document_count"] != len(documents):
        raise GuardError("snapshot manifest schema mismatch")
    seen: set[str] = set()
    for document in documents:
        if not isinstance(document, dict) or set(document) != {
            "path_sha256",
            "byte_sha256",
            "canonical_sha256",
        }:
            raise GuardError("snapshot manifest schema mismatch")
        identifier = document["path_sha256"]
        if not isinstance(identifier, str) or not HASH_PATTERN.fullmatch(identifier):
            raise GuardError("snapshot manifest schema mismatch")
        if identifier in seen:
            raise GuardError("duplicate document identifier")
        seen.add(identifier)
        for key in ("byte_sha256", "canonical_sha256"):
            if not isinstance(document[key], str) or not HASH_PATTERN.fullmatch(document[key]):
                raise GuardError("snapshot manifest schema mismatch")
    filesystem = manifest["filesystem"]
    if not isinstance(filesystem, list) or not filesystem:
        raise GuardError("snapshot manifest schema mismatch")
    seen_paths: set[str] = set()
    for record in filesystem:
        if not isinstance(record, dict) or set(record) != {
            "path_sha256", "kind", "mode", "uid", "gid", "nlink"
        }:
            raise GuardError("snapshot manifest schema mismatch")
        path_hash = record["path_sha256"]
        if not isinstance(path_hash, str) or not HASH_PATTERN.fullmatch(path_hash) or path_hash in seen_paths:
            raise GuardError("snapshot manifest schema mismatch")
        seen_paths.add(path_hash)
        if record["kind"] not in {"file", "directory"}:
            raise GuardError("snapshot manifest schema mismatch")
        if not all(isinstance(record[key], int) for key in ("mode", "uid", "gid", "nlink")):
            raise GuardError("snapshot manifest schema mismatch")
    for key in ("canonical_sha256", "snapshot_sha256"):
        if not isinstance(manifest[key], str) or not HASH_PATTERN.fullmatch(manifest[key]):
            raise GuardError("snapshot manifest schema mismatch")
    return manifest


def compare_state(state: State, manifest: dict[str, Any]) -> None:
    current = {record["path_sha256"]: record for record in state.documents}
    expected = {record["path_sha256"]: record for record in manifest["documents"]}
    if set(current) != set(expected):
        raise GuardError("document inventory mismatch")
    if any(
        current[identifier]["canonical_sha256"]
        != expected[identifier]["canonical_sha256"]
        for identifier in current
    ) or state.canonical_sha256 != manifest["canonical_sha256"]:
        raise GuardError("canonical progress mismatch")
    if list(state.filesystem) != manifest["filesystem"] or state.snapshot_sha256 != manifest["snapshot_sha256"]:
        raise GuardError("permission, owner, group, or link mismatch")


def print_summary(state: State) -> None:
    print(
        f"documents={len(state.documents)} "
        f"canonical_sha256={state.canonical_sha256} "
        f"snapshot_sha256={state.snapshot_sha256}"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    snapshot_parser = subparsers.add_parser("snapshot")
    snapshot_parser.add_argument("--world", type=Path, required=True)
    snapshot_parser.add_argument("--output", type=Path, required=True)
    compare_parser = subparsers.add_parser("compare")
    compare_parser.add_argument("--world", type=Path, required=True)
    compare_parser.add_argument("--snapshot", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        state = collect_state(arguments.world)
        if arguments.command == "snapshot":
            write_manifest(arguments.output, state)
        else:
            compare_state(state, read_manifest(arguments.snapshot))
        print_summary(state)
        return 0
    except GuardError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
