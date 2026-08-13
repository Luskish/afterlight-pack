#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ctypes
import errno
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
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
REQUIRED_QUEST_OUTPUTS = frozenset(
    {
        "config/ftbquests/quests/.afterlight-managed.json",
        "config/ftbquests/quests/chapter_groups.snbt",
        "config/ftbquests/quests/data.snbt",
        "config/ftbquests/quests/lang/en_us.snbt",
    }
)
INVENTORY_NAME = "generated-quest-inventory.json"
RENAME_NOREPLACE = 1
RENAME_EXCL = 0x00000004
DARWIN_ROOT_ALIASES = frozenset({Path("/etc"), Path("/tmp"), Path("/var")})


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


def _reject_symlinked_parent_components(path: Path, label: str) -> None:
    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        try:
            current_stat = current.lstat()
        except FileNotFoundError:
            break
        except OSError as error:
            raise ValueError(f"cannot inspect {label} component {current}: {error}") from error
        if stat.S_ISLNK(current_stat.st_mode):
            if sys.platform == "darwin" and current in DARWIN_ROOT_ALIASES:
                continue
            raise ValueError(f"{label} contains a symbolic-link component: {current}")


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


def _relative_path(root: Path, path: Path) -> str:
    relative = path.relative_to(root).as_posix()
    try:
        relative.encode("utf-8", "strict")
    except UnicodeEncodeError as error:
        raise ValueError(f"generated path is not UTF-8: {relative!r}") from error
    if relative.startswith("/") or ".." in Path(relative).parts:
        raise ValueError(f"generated path escapes the pack root: {relative}")
    return relative


def _git_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for name in (
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_DIR",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_WORK_TREE",
    ):
        environment.pop(name, None)
    environment["GIT_LITERAL_PATHSPECS"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_OPTIONAL_LOCKS"] = "0"
    return environment


def _git_states(root: Path, relatives: list[str]) -> dict[str, str]:
    command = [
        "git",
        "-c",
        "core.quotePath=false",
        "status",
        "--porcelain=v1",
        "-z",
        "--ignored=matching",
        "--untracked-files=all",
        "--no-renames",
        "--",
        *relatives,
    ]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            env=_git_environment(),
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ValueError(f"cannot capture generated Git state: {error}") from error
    states = {relative: "tracked" for relative in relatives}
    for raw_record in result.stdout.split(b"\0"):
        if not raw_record:
            continue
        if len(raw_record) < 4 or raw_record[2:3] != b" ":
            raise ValueError("generated Git status record is malformed")
        status_code = raw_record[:2]
        try:
            path = raw_record[3:].decode("utf-8", "strict")
        except UnicodeDecodeError as error:
            raise ValueError("generated Git path is not UTF-8") from error
        if path not in states:
            raise ValueError(f"generated Git status returned an unknown path: {path}")
        if status_code == b"??":
            states[path] = "untracked"
        elif status_code == b"!!":
            states[path] = "ignored"
        else:
            states[path] = "tracked"
    return states


def _source_inventory(pack_root: Path | str) -> tuple[Path, list[Path], dict[str, str]]:
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
    source_paths = sorted(source_paths)
    relatives = [_relative_path(root, path) for path in source_paths]
    if len(relatives) != len(set(relatives)):
        raise ValueError("generated inventory contains duplicate normalized paths")
    missing_outputs = REQUIRED_QUEST_OUTPUTS - set(relatives)
    if missing_outputs:
        raise ValueError(
            "required quest output is missing: " + ", ".join(sorted(missing_outputs))
        )
    if not any(
        relative.startswith("config/ftbquests/quests/chapters/")
        and relative.endswith(".snbt")
        for relative in relatives
    ):
        raise ValueError("required quest output is missing: chapters/*.snbt")
    return root, source_paths, _git_states(root, relatives)


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
        path_after = path.lstat()
        if (path_after.st_dev, path_after.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError(f"generated file changed while hashing: {path}")
        return after, size, digest.hexdigest()
    finally:
        os.close(descriptor)


def collect_inventory(pack_root: Path | str) -> dict[str, object]:
    root, source_paths, git_states = _source_inventory(pack_root)
    records: list[dict[str, object]] = []
    for path in sorted(source_paths):
        path_stat, size, digest = _hash_regular_file(path)
        relative = _relative_path(root, path)
        records.append(
            {
                "git_state": git_states[relative],
                "mode": f"{stat.S_IMODE(path_stat.st_mode):04o}",
                "path": relative,
                "sha256": digest,
                "size": size,
            }
        )
    return {"files": records, "schema_version": 1}


def _copy_regular_file(source: Path, destination: Path) -> tuple[os.stat_result, int, str]:
    before = source.lstat()
    source_flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        source_flags |= os.O_NOFOLLOW
    source_descriptor = os.open(source, source_flags)
    destination_descriptor = -1
    try:
        opened = os.fstat(source_descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1:
            raise ValueError(f"generated source is not an owned regular file: {source}")
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"generated file changed while opening: {source}")
        destination_descriptor = os.open(
            destination,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            stat.S_IMODE(opened.st_mode),
        )
        os.fchmod(destination_descriptor, stat.S_IMODE(opened.st_mode))
        digest = hashlib.sha256()
        size = 0
        while True:
            chunk = os.read(source_descriptor, 1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            size += len(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(destination_descriptor, view)
                if written <= 0:
                    raise OSError("short write while copying generated file")
                view = view[written:]
        os.fsync(destination_descriptor)
        after = os.fstat(source_descriptor)
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
            raise ValueError(f"generated file changed while copying: {source}")
        path_after = source.lstat()
        if (path_after.st_dev, path_after.st_ino) != (after.st_dev, after.st_ino):
            raise ValueError(f"generated file changed while copying: {source}")
        return after, size, digest.hexdigest()
    finally:
        if destination_descriptor >= 0:
            os.close(destination_descriptor)
        os.close(source_descriptor)


def _snapshot_parent(root: Path, relative: Path) -> Path:
    current = root
    for component in relative.parts:
        current /= component
        try:
            current.mkdir(mode=0o700)
        except FileExistsError:
            status = current.lstat()
            if stat.S_ISLNK(status.st_mode) or not stat.S_ISDIR(status.st_mode):
                raise ValueError(f"snapshot parent is unsafe: {current}")
        os.chmod(current, 0o700)
    return current


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _atomic_no_replace(parent: Path, source_name: str, target_name: str) -> None:
    descriptor = os.open(parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        library = ctypes.CDLL(None, use_errno=True)
        function_name = "renameatx_np" if sys.platform == "darwin" else "renameat2"
        flags = RENAME_EXCL if sys.platform == "darwin" else RENAME_NOREPLACE
        if sys.platform not in {"darwin", "linux"}:
            raise NotImplementedError(
                f"atomic no-replace is unsupported on {sys.platform}"
            )
        try:
            function = getattr(library, function_name)
        except AttributeError as error:
            raise NotImplementedError(
                f"atomic no-replace primitive is unavailable: {function_name}"
            ) from error
        function.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        ctypes.set_errno(0)
        result = function(
            descriptor,
            os.fsencode(source_name),
            descriptor,
            os.fsencode(target_name),
            flags,
        )
        if result != 0:
            error_number = ctypes.get_errno()
            if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
                raise FileExistsError(
                    error_number,
                    os.strerror(error_number),
                    str(parent / target_name),
                )
            raise OSError(error_number, os.strerror(error_number))
    finally:
        os.close(descriptor)


def write_inventory(pack_root: Path | str, output: Path | str) -> Path:
    root = _validated_directory(Path(pack_root), "pack root")
    output_path = Path(output)
    _reject_symlinked_parent_components(output_path.parent, "inventory output parent")
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
    root, source_paths, git_states = _source_inventory(root)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.staging.", dir=parent)
    )
    os.chmod(staging, 0o700)
    try:
        records: list[dict[str, object]] = []
        directories = {staging}
        for source in source_paths:
            relative_text = _relative_path(root, source)
            relative = Path(relative_text)
            target_parent = _snapshot_parent(staging, relative.parent)
            cursor = target_parent
            while cursor != staging:
                directories.add(cursor)
                cursor = cursor.parent
            target = target_parent / relative.name
            source_stat, size, digest = _copy_regular_file(source, target)
            records.append(
                {
                    "git_state": git_states[relative_text],
                    "mode": f"{stat.S_IMODE(source_stat.st_mode):04o}",
                    "path": relative_text,
                    "sha256": digest,
                    "size": size,
                }
            )
        manifest = {"files": records, "schema_version": 1}
        payload = (
            json.dumps(
                manifest,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
        manifest_path = staging / INVENTORY_NAME
        descriptor = os.open(
            manifest_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
        try:
            view = memoryview(payload)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short write while writing generated inventory")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        for directory in sorted(
            directories, key=lambda candidate: len(candidate.parts), reverse=True
        ):
            _fsync_directory(directory)
        _atomic_no_replace(parent, staging.name, destination.name)
        _fsync_directory(parent)
        staging = Path()
        return destination / INVENTORY_NAME
    finally:
        if staging != Path() and staging.exists():
            shutil.rmtree(staging)


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
