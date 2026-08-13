#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import tempfile
import tomllib
from pathlib import Path


class LockError(RuntimeError):
    pass


def digest_file(path: Path, algorithm: str) -> tuple[str, int]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_nlink != 1:
        raise LockError(f"installed mod is not a single-link regular file: {path.name}")
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        opened = os.fstat(descriptor)
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise LockError(f"installed mod changed during open: {path.name}")
        digest = hashlib.new(algorithm)
        size = 0
        while chunk := os.read(descriptor, 1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        if (
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)
        ):
            raise LockError(f"installed mod changed during read: {path.name}")
    finally:
        os.close(descriptor)
    return digest.hexdigest(), size


def build(repository: Path, installed_mods: Path) -> dict[str, object]:
    repository = repository.resolve(strict=True)
    installed_mods = installed_mods.resolve(strict=True)
    records: list[dict[str, object]] = []
    expected_names: set[str] = set()
    for metadata_path in sorted((repository / "mods").glob("*.pw.toml")):
        metadata = tomllib.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("side", "both") == "client":
            continue
        filename = metadata.get("filename")
        download = metadata.get("download")
        if not isinstance(filename, str) or not isinstance(download, dict):
            raise LockError(f"invalid Packwiz metadata: {metadata_path.name}")
        hash_format = download.get("hash-format")
        expected_hash = download.get("hash")
        if hash_format not in {"sha1", "sha256", "sha512"} or not isinstance(expected_hash, str):
            raise LockError(f"invalid Packwiz digest: {metadata_path.name}")
        if filename in expected_names:
            raise LockError(f"duplicate installed mod filename: {filename}")
        expected_names.add(filename)
        actual_hash, size = digest_file(installed_mods / filename, hash_format)
        if actual_hash != expected_hash:
            raise LockError(f"installed mod digest differs from Packwiz: {filename}")
        records.append(
            {
                "filename": filename,
                "hash": expected_hash,
                "hash_format": hash_format,
                "metadata_path": metadata_path.relative_to(repository).as_posix(),
                "size": size,
            }
        )
    actual_names = {path.name for path in installed_mods.iterdir() if path.is_file()}
    if actual_names != expected_names:
        raise LockError("installed server mod inventory differs from Packwiz")
    return {"files": records, "format": 1}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--installed-mods", type=Path, required=True)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("tools/server-mod-manifest-lock.json"),
    )
    arguments = parser.parse_args()
    payload = (json.dumps(build(arguments.repository, arguments.installed_mods), indent=2, sort_keys=True) + "\n").encode("utf-8")
    output = arguments.output
    if not output.is_absolute():
        output = arguments.repository / output
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{output.name}.", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(payload)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, output)
        parent_fd = os.open(output.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise
    print(f"SERVER MOD MANIFEST LOCK: OK {len(json.loads(payload)['files'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
