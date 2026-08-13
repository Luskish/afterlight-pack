#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEST_RELATIVE = Path("config/ftbquests/quests")
AUDIT_RELATIVE = Path("kubejs/server_scripts/afterlight")
REQUIRED_AUDITS = frozenset(
    {
        "generated_manual_acquisition_audit.js",
        "generated_quest_item_audit.js",
    }
)
INVENTORY_NAME = "generated-quest-inventory.json"


def _validated_directory(path: Path, label: str) -> Path:
    try:
        path_stat = path.lstat()
    except OSError as error:
        raise ValueError(f"cannot inspect {label} {path}: {error}") from error
    if stat.S_ISLNK(path_stat.st_mode):
        raise ValueError(f"{label} cannot be a symbolic link: {path}")
    if not stat.S_ISDIR(path_stat.st_mode):
        raise ValueError(f"{label} is not a directory: {path}")
    return path.resolve(strict=True)


def _regular_paths(root: Path) -> list[Path]:
    paths: list[Path] = []
    for directory, directory_names, file_names in os.walk(root, followlinks=False):
        directory_path = Path(directory)
        for name in sorted(directory_names):
            child = directory_path / name
            child_stat = child.lstat()
            if stat.S_ISLNK(child_stat.st_mode):
                raise ValueError(f"generated inventory contains a symbolic link: {child}")
            if not stat.S_ISDIR(child_stat.st_mode):
                raise ValueError(f"generated inventory contains a non-directory: {child}")
        for name in sorted(file_names):
            child = directory_path / name
            child_stat = child.lstat()
            if stat.S_ISLNK(child_stat.st_mode):
                raise ValueError(f"generated inventory contains a symbolic link: {child}")
            if not stat.S_ISREG(child_stat.st_mode):
                raise ValueError(f"generated inventory contains a nonregular file: {child}")
            if child_stat.st_nlink != 1:
                raise ValueError(f"generated inventory contains a hard-linked file: {child}")
            paths.append(child)
    return sorted(paths)


def _hash_regular_file(path: Path) -> tuple[os.stat_result, int, str]:
    before = path.lstat()
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise ValueError(f"cannot open generated file {path}: {error}") from error
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode):
            raise ValueError(f"generated inventory contains a nonregular file: {path}")
        if opened.st_nlink != 1:
            raise ValueError(f"generated inventory contains a hard-linked file: {path}")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"generated file changed while opening: {path}")
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
        after = os.fstat(descriptor)
        state_before = (
            opened.st_dev,
            opened.st_ino,
            opened.st_mode,
            opened.st_size,
            opened.st_mtime_ns,
            opened.st_ctime_ns,
        )
        state_after = (
            after.st_dev,
            after.st_ino,
            after.st_mode,
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        )
        if state_before != state_after or size != after.st_size:
            raise ValueError(f"generated file changed while hashing: {path}")
        return after, size, digest.hexdigest()
    finally:
        os.close(descriptor)


def collect_inventory(pack_root: Path | str) -> dict[str, object]:
    root = _validated_directory(Path(pack_root), "pack root")
    quest_root = _validated_directory(root / QUEST_RELATIVE, "quest root")
    audit_root = _validated_directory(root / AUDIT_RELATIVE, "audit root")

    audit_names = {
        path.name
        for path in _regular_paths(audit_root)
        if path.parent == audit_root
        and path.name.startswith("generated_")
        and path.name.endswith("_audit.js")
    }
    if audit_names != REQUIRED_AUDITS:
        raise ValueError(
            "generated audit inventory mismatch: expected "
            f"{sorted(REQUIRED_AUDITS)}, found {sorted(audit_names)}"
        )

    source_paths = _regular_paths(quest_root)
    source_paths.extend(audit_root / name for name in sorted(REQUIRED_AUDITS))
    records: list[dict[str, object]] = []
    for path in sorted(source_paths):
        path_stat, size, digest = _hash_regular_file(path)
        relative = path.relative_to(root).as_posix()
        records.append(
            {
                "mode": f"{stat.S_IMODE(path_stat.st_mode):04o}",
                "path": relative,
                "sha256": digest,
                "size": size,
            }
        )
    return {"files": records, "schema_version": 1}


def write_inventory(pack_root: Path | str, output: Path | str) -> Path:
    root = _validated_directory(Path(pack_root), "pack root")
    output_path = Path(output)
    if output_path.exists() or output_path.is_symlink():
        raise FileExistsError(f"inventory output already exists: {output_path}")
    resolved_output = output_path.resolve(strict=False)
    try:
        resolved_output.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("inventory output must be outside the pack root")
    parent = _validated_directory(resolved_output.parent, "inventory output parent")
    destination = parent / resolved_output.name
    os.mkdir(destination, 0o700)
    os.chmod(destination, 0o700)
    manifest = collect_inventory(root)
    manifest_path = destination / INVENTORY_NAME
    payload = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(
        manifest_path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        raise
    return manifest_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hash the complete generated AFTERLIGHT quest inventory."
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    try:
        manifest_path = write_inventory(arguments.root, arguments.output)
    except (FileExistsError, OSError, ValueError) as error:
        parser.exit(1, f"HASH GENERATED QUESTS: FAIL: {error}\n")
    print(f"HASH GENERATED QUESTS: OK {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
