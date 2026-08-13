from __future__ import annotations

import ctypes
import fcntl
import os
import shutil
import stat
import tempfile
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator, Mapping, Sequence


RENAME_NOREPLACE = 0x00000001
RENAME_EXCHANGE = 0x00000002
RENAME_SWAP = 0x00000002
RENAME_EXCL = 0x00000004


_ACTIVE_ROOTS: set[tuple[int, int]] = set()
_ACTIVE_ROOTS_LOCK = threading.Lock()


def is_quest_transaction_artifact(path: Path) -> bool:
    name = path.name
    if not name.startswith(".") or ".afterlight-" not in name:
        return False
    marker = name.rsplit(".afterlight-", 1)[-1]
    try:
        kind, suffix = marker.rsplit("-", 1)
    except ValueError:
        return False
    return (
        kind in {"stage", "delete", "remove", "rollback", "recovery"}
        and len(suffix) == 32
        and all(character in "0123456789abcdef" for character in suffix)
    )


def quest_build_dependency_roots(
    repository_root: Path,
    *,
    include_validation_inputs: bool = False,
) -> tuple[Path, ...]:
    root = Path(os.path.abspath(repository_root))
    paths = [root / "config", root / "mods", root / "kubejs"]
    if include_validation_inputs:
        paths.append(root / "server-test" / "mods")
    return tuple(paths)


@dataclass(frozen=True)
class PlannedWrite:
    payload: bytes
    mode: int | None = None
    uid: int | None = None
    gid: int | None = None


@dataclass(frozen=True)
class _NodeState:
    kind: str
    device: int
    inode: int
    mode: int
    uid: int
    gid: int
    links: int
    size: int
    modified_ns: int
    flags: int | None
    birth_ns: int | None
    payload: bytes | None


@dataclass
class _Artifact:
    path: Path
    parent_fd: int
    name: str
    created_state: _NodeState
    state: _NodeState | None = None
    present: bool = True
    retain: bool = False


@dataclass
class _CommitRecord:
    target: Path
    parent_fd: int
    target_name: str
    original: _NodeState | None
    installed: _NodeState | None
    backup: _Artifact | None
    stage: _Artifact | None
    operation: str
    phase: str = "pending"


@dataclass
class _CreatedDirectory:
    path: Path
    parent_fd: int
    name: str
    state: _NodeState | None = None
    phase: str = "public"
    private_name: str | None = None
    private_path: Path | None = None


class PromotionResult(list[Path]):
    def __init__(
        self,
        paths: Iterable[Path],
        *,
        cleanup_warnings: Iterable[BaseException] = (),
        recovery_paths: Iterable[Path] = (),
    ) -> None:
        super().__init__(paths)
        self.committed = True
        self.cleanup_warnings = tuple(cleanup_warnings)
        self.recovery_paths = tuple(dict.fromkeys(recovery_paths))


class QuestBuildRollbackError(RuntimeError):
    def __init__(
        self,
        primary_error: BaseException,
        *,
        unresolved_paths: Iterable[Path],
        recovery_paths: Iterable[Path],
        rollback_errors: Iterable[BaseException] = (),
        cleanup_errors: Iterable[BaseException] = (),
    ) -> None:
        self.primary_error = primary_error
        self.unresolved_paths = tuple(dict.fromkeys(unresolved_paths))
        self.recovery_paths = tuple(dict.fromkeys(recovery_paths))
        self.rollback_errors = tuple(rollback_errors)
        self.cleanup_errors = tuple(cleanup_errors)
        details = [f"quest build transaction failed: {primary_error}"]
        if self.unresolved_paths:
            details.append(
                "unresolved paths: "
                + ", ".join(str(path) for path in self.unresolved_paths)
            )
        if self.recovery_paths:
            details.append(
                "retained recovery paths: "
                + ", ".join(str(path) for path in self.recovery_paths)
            )
        if self.rollback_errors:
            details.append(
                "rollback errors: "
                + "; ".join(str(error) for error in self.rollback_errors)
            )
        if self.cleanup_errors:
            details.append(
                "cleanup errors: "
                + "; ".join(str(error) for error in self.cleanup_errors)
            )
        super().__init__("; ".join(details))


def _birth_ns(status: os.stat_result) -> int | None:
    value = getattr(status, "st_birthtime", None)
    return None if value is None else int(value * 1_000_000_000)


def _node_state(status: os.stat_result, payload: bytes | None) -> _NodeState:
    if stat.S_ISREG(status.st_mode):
        kind = "file"
    elif stat.S_ISDIR(status.st_mode):
        kind = "directory"
    elif stat.S_ISLNK(status.st_mode):
        kind = "symlink"
    else:
        kind = "other"
    return _NodeState(
        kind=kind,
        device=status.st_dev,
        inode=status.st_ino,
        mode=stat.S_IMODE(status.st_mode),
        uid=status.st_uid,
        gid=status.st_gid,
        links=status.st_nlink,
        size=status.st_size,
        modified_ns=status.st_mtime_ns,
        flags=getattr(status, "st_flags", None),
        birth_ns=_birth_ns(status),
        payload=payload,
    )


def _states_match(expected: _NodeState, actual: _NodeState) -> bool:
    if expected.kind == actual.kind == "directory":
        return (
            expected.device,
            expected.inode,
            expected.mode,
            expected.uid,
            expected.gid,
            expected.flags,
            expected.birth_ns,
        ) == (
            actual.device,
            actual.inode,
            actual.mode,
            actual.uid,
            actual.gid,
            actual.flags,
            actual.birth_ns,
        )
    return expected == actual


def _same_identity(expected: _NodeState, actual: _NodeState) -> bool:
    return (
        expected.kind,
        expected.device,
        expected.inode,
        expected.mode,
        expected.uid,
        expected.gid,
        expected.links,
        expected.flags,
        expected.birth_ns,
    ) == (
        actual.kind,
        actual.device,
        actual.inode,
        actual.mode,
        actual.uid,
        actual.gid,
        actual.links,
        actual.flags,
        actual.birth_ns,
    )


def _fsync_directory_fd(descriptor: int) -> None:
    os.fsync(descriptor)


def _absolute_existing_directory(path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    descriptor = os.open(absolute.anchor, _directory_flags())
    current = Path(absolute.anchor)
    try:
        for component in absolute.parts[1:]:
            current = current / component
            status = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            if stat.S_ISLNK(status.st_mode):
                raise ValueError(f"symlinked repository path is not allowed: {current}")
            if not stat.S_ISDIR(status.st_mode):
                raise ValueError(f"repository path is not a directory: {current}")
            child = os.open(component, _directory_flags(), dir_fd=descriptor)
            child_status = os.fstat(child)
            if child_status.st_dev != status.st_dev or child_status.st_ino != status.st_ino:
                os.close(child)
                raise ValueError(f"repository path changed while opening: {current}")
            os.close(descriptor)
            descriptor = child
    finally:
        os.close(descriptor)
    return absolute


def _directory_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _file_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _open_root(path: Path) -> int:
    return os.open(path, _directory_flags())


def _validate_component_name(value: str) -> None:
    if value in {"", ".", ".."} or "/" in value or "\0" in value:
        raise ValueError(f"unsafe quest transaction path component: {value!r}")


def _relative_to_root(root: Path, path: Path) -> Path:
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"quest transaction path is outside repository root {root}: {absolute}"
        ) from error
    if relative == Path("."):
        raise ValueError(f"quest transaction target cannot be repository root: {absolute}")
    for part in relative.parts:
        _validate_component_name(part)
    return relative


def _open_parent(
    root: Path,
    root_fd: int,
    target: Path,
    *,
    create: bool,
    created_registry: list[_CreatedDirectory] | None = None,
) -> tuple[int, tuple[tuple[Path, _NodeState], ...]]:
    relative = _relative_to_root(root, target)
    descriptor = os.dup(root_fd)
    created: list[tuple[Path, _NodeState]] = []
    current = root
    try:
        for component in relative.parts[:-1]:
            current = current / component
            try:
                status = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(component, 0o755, dir_fd=descriptor)
                created_record = _CreatedDirectory(
                    path=current,
                    parent_fd=(
                        os.dup(descriptor)
                        if created_registry is not None
                        else -1
                    ),
                    name=component,
                )
                if created_registry is not None:
                    created_registry.append(created_record)
                status = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                created_record.state = _node_state(status, None)
                created.append((current, created_record.state))
                _fsync_directory_fd(descriptor)
            if stat.S_ISLNK(status.st_mode):
                raise ValueError(f"symlinked parent component is not allowed: {current}")
            if not stat.S_ISDIR(status.st_mode):
                raise ValueError(f"non-directory parent component: {current}")
            child_descriptor = os.open(component, _directory_flags(), dir_fd=descriptor)
            child_status = os.fstat(child_descriptor)
            if child_status.st_dev != status.st_dev or child_status.st_ino != status.st_ino:
                os.close(child_descriptor)
                raise ValueError(f"quest transaction parent changed while opening: {current}")
            os.close(descriptor)
            descriptor = child_descriptor
        return descriptor, tuple(created)
    except BaseException:
        os.close(descriptor)
        raise


def _read_regular_at(parent_fd: int, name: str, path: Path) -> _NodeState | None:
    try:
        status = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(status.st_mode):
        raise ValueError(f"symlink target is not allowed: {path}")
    if not stat.S_ISREG(status.st_mode):
        raise ValueError(f"quest transaction target is not a regular file: {path}")
    if status.st_nlink != 1:
        raise ValueError(f"hardlink target is not allowed: {path}")
    descriptor = os.open(name, _file_flags(), dir_fd=parent_fd)
    try:
        before = os.fstat(descriptor)
        if before.st_dev != status.st_dev or before.st_ino != status.st_ino:
            raise ValueError(f"quest transaction target changed while opening: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        before_state = _node_state(before, b"".join(chunks))
        after_state = _node_state(after, before_state.payload)
        if not _states_match(before_state, after_state):
            raise ValueError(f"quest transaction target changed while reading: {path}")
        return after_state
    finally:
        os.close(descriptor)


def _read_any_at(parent_fd: int, name: str, path: Path) -> _NodeState | None:
    try:
        status = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None
    if stat.S_ISREG(status.st_mode):
        descriptor = os.open(name, _file_flags(), dir_fd=parent_fd)
        try:
            before = os.fstat(descriptor)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
            before_state = _node_state(before, b"".join(chunks))
            after_state = _node_state(after, before_state.payload)
            if not _states_match(before_state, after_state):
                raise ValueError(f"quest transaction object changed while reading: {path}")
            return after_state
        finally:
            os.close(descriptor)
    if stat.S_ISLNK(status.st_mode):
        target = os.readlink(name, dir_fd=parent_fd)
        return _node_state(status, os.fsencode(target))
    return _node_state(status, None)


def _read_path(path: Path) -> _NodeState:
    status = path.lstat()
    if stat.S_ISLNK(status.st_mode):
        raise ValueError(f"symlink dependency is not allowed: {path}")
    if stat.S_ISDIR(status.st_mode):
        return _node_state(status, None)
    if not stat.S_ISREG(status.st_mode):
        raise ValueError(f"non-regular quest dependency is not allowed: {path}")
    if status.st_nlink != 1:
        raise ValueError(f"hardlink quest dependency is not allowed: {path}")
    descriptor = os.open(path, _file_flags())
    try:
        before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        state = _node_state(after, b"".join(chunks))
        if not _states_match(_node_state(before, state.payload), state):
            raise ValueError(f"quest dependency changed while reading: {path}")
        return state
    finally:
        os.close(descriptor)


def _capture_roots(
    roots: Sequence[Path],
    *,
    ignored: frozenset[Path] = frozenset(),
) -> tuple[dict[Path, _NodeState], frozenset[Path]]:
    entries: dict[Path, _NodeState] = {}
    missing: set[Path] = set()
    for root in roots:
        if root in ignored:
            continue
        try:
            root_state = _read_path(root)
        except FileNotFoundError:
            missing.add(root)
            continue
        entries[root] = root_state
        if root_state.kind != "directory":
            continue
        for directory, directory_names, file_names in os.walk(root, followlinks=False):
            directory_path = Path(directory)
            directory_names.sort()
            file_names.sort()
            for name in tuple(directory_names):
                child = directory_path / name
                if child in ignored:
                    directory_names.remove(name)
                    continue
                child_state = _read_path(child)
                if child_state.kind != "directory":
                    raise ValueError(f"symlinked parent component is not allowed: {child}")
                entries[child] = child_state
            for name in file_names:
                child = directory_path / name
                if child in ignored:
                    continue
                entries[child] = _read_path(child)
    return entries, frozenset(missing)


def _capture_node_at(
    parent_fd: int,
    name: str,
    path: Path,
    entries: dict[Path, _NodeState],
    ignored: frozenset[Path],
) -> None:
    if path in ignored:
        return
    status = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    if stat.S_ISLNK(status.st_mode):
        raise ValueError(f"symlink quest dependency is not allowed: {path}")
    if stat.S_ISREG(status.st_mode):
        state = _read_regular_at(parent_fd, name, path)
        assert state is not None
        entries[path] = state
        return
    if not stat.S_ISDIR(status.st_mode):
        raise ValueError(f"non-regular quest dependency is not allowed: {path}")
    descriptor = os.open(name, _directory_flags(), dir_fd=parent_fd)
    try:
        opened = os.fstat(descriptor)
        if opened.st_dev != status.st_dev or opened.st_ino != status.st_ino:
            raise ValueError(f"quest dependency changed while opening: {path}")
        entries[path] = _node_state(opened, None)
        for child_name in sorted(os.listdir(descriptor)):
            _validate_component_name(child_name)
            _capture_node_at(
                descriptor,
                child_name,
                path / child_name,
                entries,
                ignored,
            )
        after = os.fstat(descriptor)
        if not _states_match(entries[path], _node_state(after, None)):
            raise ValueError(f"quest dependency changed while scanning: {path}")
    finally:
        os.close(descriptor)


def _capture_repository_roots(
    repository_root: Path,
    root_fd: int,
    roots: Sequence[Path],
    *,
    ignored: frozenset[Path] = frozenset(),
) -> tuple[dict[Path, _NodeState], frozenset[Path]]:
    entries: dict[Path, _NodeState] = {}
    missing: set[Path] = set()
    for root in roots:
        relative = _relative_to_root(repository_root, root)
        try:
            parent_fd, _ = _open_parent(
                repository_root,
                root_fd,
                root,
                create=False,
            )
        except FileNotFoundError:
            missing.add(root)
            continue
        try:
            try:
                _capture_node_at(
                    parent_fd,
                    relative.name,
                    root,
                    entries,
                    ignored,
                )
            except FileNotFoundError:
                missing.add(root)
        finally:
            os.close(parent_fd)
    return entries, frozenset(missing)


@dataclass(frozen=True)
class FrozenRepository:
    repository_root: Path
    repository_state: _NodeState
    roots: tuple[Path, ...]
    entries: Mapping[Path, _NodeState]
    missing_roots: frozenset[Path]

    def materialize(self, candidate_root: Path) -> None:
        candidate_root.mkdir(mode=0o700, parents=True, exist_ok=False)
        repository_status = self.repository_root.lstat()
        candidate_status = candidate_root.lstat()
        if repository_status.st_dev != candidate_status.st_dev:
            candidate_root.rmdir()
            raise ValueError(
                f"quest candidate must be on the same device as {self.repository_root}"
            )
        directories = [
            (path, state)
            for path, state in self.entries.items()
            if state.kind == "directory"
        ]
        files = [
            (path, state)
            for path, state in self.entries.items()
            if state.kind == "file"
        ]
        for source, state in sorted(directories, key=lambda item: len(item[0].parts)):
            target = candidate_root / source.relative_to(self.repository_root)
            target.mkdir(mode=state.mode, parents=True, exist_ok=True)
        for source, state in sorted(files):
            target = candidate_root / source.relative_to(self.repository_root)
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                state.mode,
            )
            try:
                payload = state.payload or b""
                view = memoryview(payload)
                written = 0
                while written < len(view):
                    written += os.write(descriptor, view[written:])
                os.fchmod(descriptor, state.mode)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        for source, state in sorted(
            directories,
            key=lambda item: len(item[0].parts),
            reverse=True,
        ):
            target = candidate_root / source.relative_to(self.repository_root)
            os.chmod(target, state.mode)
            descriptor = os.open(target, _directory_flags())
            try:
                _fsync_directory_fd(descriptor)
            finally:
                os.close(descriptor)
        parent_descriptor = os.open(candidate_root.parent, _directory_flags())
        try:
            _fsync_directory_fd(parent_descriptor)
        finally:
            os.close(parent_descriptor)

    def candidate_changes(
        self,
        candidate_root: Path,
        output_roots: Iterable[Path],
    ) -> tuple[dict[Path, PlannedWrite], tuple[Path, ...]]:
        real_output_roots = tuple(
            sorted(Path(os.path.abspath(path)) for path in output_roots)
        )
        candidate_output_roots = tuple(
            candidate_root / path.relative_to(self.repository_root)
            for path in real_output_roots
        )
        candidate_entries, _ = _capture_roots(candidate_output_roots)
        original_files = {
            path: state
            for path, state in self.entries.items()
            if state.kind == "file"
            and any(path == root or path.is_relative_to(root) for root in real_output_roots)
        }
        candidate_files: dict[Path, _NodeState] = {}
        for candidate_path, state in candidate_entries.items():
            if state.kind != "file":
                continue
            real_path = self.repository_root / candidate_path.relative_to(candidate_root)
            candidate_files[real_path] = state
        writes: dict[Path, PlannedWrite] = {}
        for path, candidate_state in candidate_files.items():
            original = original_files.get(path)
            owner = original or candidate_state
            if original is not None and (
                original.payload == candidate_state.payload
                and original.mode == candidate_state.mode
                and original.uid == owner.uid
                and original.gid == owner.gid
            ):
                continue
            writes[path] = PlannedWrite(
                payload=candidate_state.payload or b"",
                mode=candidate_state.mode,
                uid=owner.uid,
                gid=owner.gid,
            )
        deletions = tuple(sorted(set(original_files) - set(candidate_files)))
        return writes, deletions

    def assert_matches(
        self,
        *,
        overrides: Mapping[Path, _NodeState | None] | None = None,
        added_directories: Mapping[Path, _NodeState] | None = None,
        ignored: Iterable[Path] = (),
        message: str = "quest build dependency changed",
    ) -> None:
        ignored_paths = frozenset(ignored)
        _absolute_existing_directory(self.repository_root)
        root_fd = _open_root(self.repository_root)
        try:
            current_repository = _node_state(os.fstat(root_fd), None)
            if not _states_match(self.repository_state, current_repository):
                raise ValueError(f"{message}: {self.repository_root}")
            current, current_missing = _capture_repository_roots(
                self.repository_root,
                root_fd,
                self.roots,
                ignored=ignored_paths,
            )
        finally:
            os.close(root_fd)
        expected = {
            path: state
            for path, state in self.entries.items()
            if path not in ignored_paths
        }
        for path, state in (overrides or {}).items():
            if not any(path == root or path.is_relative_to(root) for root in self.roots):
                continue
            if state is None:
                expected.pop(path, None)
            else:
                expected[path] = state
        for path, state in (added_directories or {}).items():
            if any(path == root or path.is_relative_to(root) for root in self.roots):
                expected[path] = state
        expected_missing = {
            path for path in self.missing_roots if path not in expected
        }
        if current_missing != frozenset(expected_missing):
            changed = sorted(current_missing ^ frozenset(expected_missing))
            raise ValueError(f"{message}: {changed[0] if changed else self.repository_root}")
        if set(current) != set(expected):
            changed = sorted(set(current) ^ set(expected))
            raise ValueError(f"{message}: {changed[0]}")
        for path in sorted(expected):
            if not _states_match(expected[path], current[path]):
                raise ValueError(f"{message}: {path}")


@contextmanager
def candidate_workspace(
    transaction: QuestBuildTransaction,
    frozen: FrozenRepository,
) -> Iterator[Path]:
    transaction._require_active()
    candidate = transaction.repository_root.parent / (
        f".{transaction.repository_root.name}.quest-candidate-{uuid.uuid4().hex}"
    )
    authorized = False
    primary_error: BaseException | None = None
    cleanup_error: BaseException | None = None
    try:
        frozen.materialize(candidate)
        transaction.authorize_workspace(candidate)
        authorized = True
        yield candidate
    except BaseException as error:
        primary_error = error
        raise
    finally:
        try:
            if authorized:
                transaction.revoke_workspace(candidate)
            if candidate.exists():
                shutil.rmtree(candidate)
                parent_descriptor = os.open(candidate.parent, _directory_flags())
                try:
                    _fsync_directory_fd(parent_descriptor)
                finally:
                    os.close(parent_descriptor)
        except BaseException as error:
            cleanup_error = error
        if cleanup_error is not None:
            raise RuntimeError(
                "quest candidate cleanup failure"
                + (f" after {primary_error}" if primary_error is not None else "")
                + f": {cleanup_error}"
            ) from (primary_error or cleanup_error)


def _libc_call(function_name: str, arguments: tuple[object, ...]) -> None:
    library = ctypes.CDLL(None, use_errno=True)
    try:
        function = getattr(library, function_name)
    except AttributeError as error:
        raise NotImplementedError(
            f"atomic rename primitive is unavailable: {function_name}"
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
    result = function(*arguments)
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, os.strerror(error_number))


def _atomic_exchange(parent_fd: int, staged_name: str, target_name: str) -> None:
    if sys_platform() == "Darwin":
        _libc_call(
            "renameatx_np",
            (
                parent_fd,
                os.fsencode(staged_name),
                parent_fd,
                os.fsencode(target_name),
                RENAME_SWAP,
            ),
        )
        return
    if sys_platform() == "Linux":
        _libc_call(
            "renameat2",
            (
                parent_fd,
                os.fsencode(staged_name),
                parent_fd,
                os.fsencode(target_name),
                RENAME_EXCHANGE,
            ),
        )
        return
    raise NotImplementedError(f"atomic exchange is unsupported on {sys_platform()}")


def _atomic_no_replace(parent_fd: int, staged_name: str, target_name: str) -> None:
    if sys_platform() == "Darwin":
        _libc_call(
            "renameatx_np",
            (
                parent_fd,
                os.fsencode(staged_name),
                parent_fd,
                os.fsencode(target_name),
                RENAME_EXCL,
            ),
        )
        return
    if sys_platform() == "Linux":
        _libc_call(
            "renameat2",
            (
                parent_fd,
                os.fsencode(staged_name),
                parent_fd,
                os.fsencode(target_name),
                RENAME_NOREPLACE,
            ),
        )
        return
    raise NotImplementedError(f"atomic no-replace is unsupported on {sys_platform()}")


def sys_platform() -> str:
    return os.uname().sysname


def _require_same_device(
    parent_status: os.stat_result,
    stage_status: os.stat_result,
    stage_path: Path,
) -> None:
    if parent_status.st_dev != stage_status.st_dev:
        raise ValueError(
            f"quest transaction stage must be on the same device as its target: {stage_path}"
        )


def _create_artifact(
    parent_fd: int,
    parent_path: Path,
    target_name: str,
    payload: bytes,
    mode: int,
    uid: int,
    gid: int,
    kind: str,
    registry: list[_Artifact],
) -> _Artifact:
    name = f".{target_name}.afterlight-{kind}-{uuid.uuid4().hex}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    path = parent_path / name
    created_state = _node_state(os.fstat(descriptor), b"")
    artifact = _Artifact(
        path=path,
        parent_fd=parent_fd,
        name=name,
        created_state=created_state,
    )
    registry.append(artifact)
    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
            artifact.state = _node_state(
                os.fstat(descriptor),
                bytes(view[:written]),
            )
        current = os.fstat(descriptor)
        if current.st_uid != uid or current.st_gid != gid:
            os.fchown(descriptor, uid, gid)
            artifact.state = _node_state(os.fstat(descriptor), payload)
        os.fchmod(descriptor, mode)
        artifact.state = _node_state(os.fstat(descriptor), payload)
        os.fsync(descriptor)
        status = os.fstat(descriptor)
        state = _node_state(status, payload)
        artifact.state = state
        _require_same_device(os.fstat(parent_fd), status, path)
        if state.links != 1 or state.kind != "file":
            raise ValueError(f"invalid quest transaction stage: {path}")
        return artifact
    finally:
        os.close(descriptor)


def _unlink_artifact(artifact: _Artifact) -> None:
    expected = artifact.state or artifact.created_state
    original_name = artifact.name
    original_path = artifact.path
    cleanup_name = f".{original_name}.afterlight-remove-{uuid.uuid4().hex}"
    cleanup_path = original_path.parent / cleanup_name
    _atomic_no_replace(artifact.parent_fd, original_name, cleanup_name)
    artifact.name = cleanup_name
    artifact.path = cleanup_path
    sync_error: BaseException | None = None
    try:
        _fsync_directory_fd(artifact.parent_fd)
    except BaseException as error:
        sync_error = error
    moved = _artifact_current_state(artifact)
    if moved is None or not _states_match(expected, moved):
        try:
            if moved is not None:
                _atomic_no_replace(
                    artifact.parent_fd,
                    cleanup_name,
                    original_name,
                )
                artifact.name = original_name
                artifact.path = original_path
                _fsync_directory_fd(artifact.parent_fd)
                restored = _artifact_current_state(artifact)
                if restored is None or not _states_match(moved, restored):
                    raise ValueError(
                        "quest transaction could not verify restored private "
                        f"artifact: {original_path}"
                    )
        except BaseException:
            artifact.retain = True
            raise
        artifact.retain = True
        raise ValueError(
            f"quest transaction lost private artifact ownership: {original_path}"
        )
    os.unlink(cleanup_name, dir_fd=artifact.parent_fd)
    artifact.present = False
    try:
        _fsync_directory_fd(artifact.parent_fd)
    except BaseException as error:
        if sync_error is None:
            sync_error = error
    if sync_error is not None:
        raise sync_error


def _artifact_current_state(artifact: _Artifact) -> _NodeState | None:
    return _read_any_at(artifact.parent_fd, artifact.name, artifact.path)


def _cleanup_private_artifact(artifact: _Artifact) -> None:
    if not artifact.present:
        return
    current = _artifact_current_state(artifact)
    if current is None:
        artifact.present = False
        return
    expected = artifact.state or artifact.created_state
    if not _states_match(expected, current):
        artifact.retain = True
        raise ValueError(f"quest transaction lost private artifact ownership: {artifact.path}")
    try:
        _unlink_artifact(artifact)
    except BaseException:
        if _artifact_current_state(artifact) is None:
            artifact.present = False
        raise
    artifact.present = False


def _remove_created_directory(
    record: _CreatedDirectory,
    private_name: str,
    private_path: Path,
    expected: _NodeState,
) -> None:
    cleanup_name = f".{record.name}.afterlight-remove-{uuid.uuid4().hex}"
    cleanup_path = record.path.parent / cleanup_name
    _atomic_no_replace(record.parent_fd, private_name, cleanup_name)
    record.phase = "cleanup-private"
    record.private_name = cleanup_name
    record.private_path = cleanup_path
    _fsync_directory_fd(record.parent_fd)
    moved = _read_any_at(record.parent_fd, cleanup_name, cleanup_path)
    mismatch = moved is None or not _same_identity(expected, moved)
    if not mismatch:
        descriptor = os.open(cleanup_name, _directory_flags(), dir_fd=record.parent_fd)
        try:
            mismatch = bool(os.listdir(descriptor))
        finally:
            os.close(descriptor)
    if mismatch:
        if moved is not None:
            _atomic_no_replace(record.parent_fd, cleanup_name, private_name)
            record.phase = "moved-private"
            record.private_name = private_name
            record.private_path = private_path
            _fsync_directory_fd(record.parent_fd)
            restored = _read_any_at(record.parent_fd, private_name, private_path)
            if restored is None or not _same_identity(moved, restored):
                raise ValueError(
                    "quest transaction could not verify restored private "
                    f"directory: {record.path}"
                )
        raise ValueError(
            f"quest transaction lost created-directory ownership: {record.path}"
        )
    os.rmdir(cleanup_name, dir_fd=record.parent_fd)
    record.phase = "removed"
    record.private_name = None
    record.private_path = None
    _fsync_directory_fd(record.parent_fd)


class QuestBuildTransaction:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = Path(os.path.abspath(repository_root))
        self._root_fd: int | None = None
        self._lock_fd: int | None = None
        self._root_identity: tuple[int, int] | None = None
        self._registered_identity: tuple[int, int] | None = None
        self._lock_acquired = False
        self._active = False
        self._workspace_roots: dict[tuple[int, int], Path] = {}

    def __enter__(self) -> QuestBuildTransaction:
        try:
            self.repository_root = _absolute_existing_directory(self.repository_root)
            self._root_fd = _open_root(self.repository_root)
            root_status = os.fstat(self._root_fd)
            self._root_identity = (root_status.st_dev, root_status.st_ino)
            with _ACTIVE_ROOTS_LOCK:
                if self._root_identity in _ACTIVE_ROOTS:
                    raise RuntimeError(
                        "reentrant quest build transaction is not allowed for "
                        f"repository identity {self._root_identity}: {self.repository_root}"
                    )
                _ACTIVE_ROOTS.add(self._root_identity)
                self._registered_identity = self._root_identity
            lock_directory = Path(tempfile.gettempdir()) / "afterlight-quest-build-locks"
            lock_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            lock_directory_status = lock_directory.lstat()
            if (
                stat.S_ISLNK(lock_directory_status.st_mode)
                or not stat.S_ISDIR(lock_directory_status.st_mode)
                or lock_directory_status.st_uid != os.geteuid()
            ):
                raise ValueError(f"unsafe quest build lock directory: {lock_directory}")
            key = f"{self._root_identity[0]:x}-{self._root_identity[1]:x}"
            lock_path = lock_directory / f"{key}.lock"
            lock_flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                lock_flags |= os.O_NOFOLLOW
            self._lock_fd = os.open(lock_path, lock_flags, 0o600)
            lock_status = os.fstat(self._lock_fd)
            if not stat.S_ISREG(lock_status.st_mode) or lock_status.st_nlink != 1:
                raise ValueError(f"unsafe quest build lock file: {lock_path}")
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
            self._lock_acquired = True
            current_root = os.fstat(self._root_fd)
            if (current_root.st_dev, current_root.st_ino) != self._root_identity:
                raise ValueError(f"repository root changed during lock entry: {self.repository_root}")
            self._active = True
            return self
        except BaseException as error:
            try:
                self._release()
            except BaseException as cleanup_error:
                raise QuestBuildRollbackError(
                    error,
                    unresolved_paths=(),
                    recovery_paths=(),
                    cleanup_errors=(cleanup_error,),
                ) from error
            raise

    def __exit__(self, error_type, error, traceback) -> None:
        try:
            self._release()
        except BaseException as cleanup_error:
            if error is None:
                raise
            raise QuestBuildRollbackError(
                error,
                unresolved_paths=(),
                recovery_paths=(),
                cleanup_errors=(cleanup_error,),
            ) from error

    def _release(self) -> None:
        self._active = False
        self._workspace_roots.clear()
        errors: list[BaseException] = []
        if self._root_fd is not None:
            try:
                os.close(self._root_fd)
            except BaseException as error:
                errors.append(error)
            self._root_fd = None
        if self._lock_fd is not None:
            try:
                if self._lock_acquired:
                    fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            except BaseException as error:
                errors.append(error)
            try:
                os.close(self._lock_fd)
            except BaseException as error:
                errors.append(error)
            self._lock_fd = None
        self._lock_acquired = False
        with _ACTIVE_ROOTS_LOCK:
            if self._registered_identity is not None:
                _ACTIVE_ROOTS.discard(self._registered_identity)
        self._registered_identity = None
        self._root_identity = None
        if errors:
            raise RuntimeError(
                "quest build lock cleanup failure: "
                + "; ".join(str(error) for error in errors)
            )

    def _require_active(self) -> None:
        if not self._active or self._root_fd is None:
            raise RuntimeError("quest build transaction token is not active")

    def require_root(self, repository_root: Path) -> None:
        self._require_active()
        candidate = _absolute_existing_directory(repository_root)
        descriptor = _open_root(candidate)
        try:
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
        finally:
            os.close(descriptor)
        if identity != self._root_identity and identity not in self._workspace_roots:
            raise ValueError(
                "mismatched repository root for quest build transaction: "
                f"expected {self.repository_root}, found {candidate}"
            )

    def authorize_workspace(self, repository_root: Path) -> None:
        self._require_active()
        candidate = _absolute_existing_directory(repository_root)
        descriptor = _open_root(candidate)
        try:
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
        finally:
            os.close(descriptor)
        if identity == self._root_identity:
            raise ValueError("repository root cannot be registered as a candidate workspace")
        if identity in self._workspace_roots:
            raise RuntimeError(f"reentrant quest candidate workspace: {candidate}")
        self._workspace_roots[identity] = candidate

    def revoke_workspace(self, repository_root: Path) -> None:
        candidate = _absolute_existing_directory(repository_root)
        descriptor = _open_root(candidate)
        try:
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
        finally:
            os.close(descriptor)
        if identity not in self._workspace_roots:
            raise ValueError(f"unknown quest candidate workspace: {candidate}")
        del self._workspace_roots[identity]

    def is_workspace(self, repository_root: Path) -> bool:
        self._require_active()
        candidate = _absolute_existing_directory(repository_root)
        descriptor = _open_root(candidate)
        try:
            status = os.fstat(descriptor)
            identity = (status.st_dev, status.st_ino)
        finally:
            os.close(descriptor)
        return identity in self._workspace_roots

    def freeze(self, roots: Iterable[Path]) -> FrozenRepository:
        self._require_active()
        normalized = tuple(
            sorted(
                {
                    Path(os.path.abspath(root))
                    for root in roots
                }
            )
        )
        for root in normalized:
            if root != self.repository_root:
                _relative_to_root(self.repository_root, root)
        root_fd = self._root_fd
        assert root_fd is not None
        repository_state = _node_state(os.fstat(root_fd), None)
        entries, missing = _capture_repository_roots(
            self.repository_root,
            root_fd,
            normalized,
        )
        frozen = FrozenRepository(
            repository_root=self.repository_root,
            repository_state=repository_state,
            roots=normalized,
            entries=entries,
            missing_roots=missing,
        )
        frozen.assert_matches(message="quest build dependency changed during snapshot")
        return frozen

    def promote_bytes(
        self,
        writes: Mapping[Path, bytes | PlannedWrite],
        frozen: FrozenRepository,
        *,
        deletions: Iterable[Path] = (),
        post_validate: Callable[[], None] | None = None,
    ) -> PromotionResult:
        self._require_active()
        if frozen.repository_root != self.repository_root:
            raise ValueError("mismatched frozen repository root")
        deletion_paths = tuple(
            sorted({Path(os.path.abspath(path)) for path in deletions})
        )
        if set(writes) & set(deletion_paths):
            raise ValueError("quest transaction path cannot be written and deleted")
        if not writes and not deletion_paths:
            frozen.assert_matches()
            if post_validate is not None:
                post_validate()
                frozen.assert_matches()
            return PromotionResult(())

        root_fd = self._root_fd
        assert root_fd is not None
        originals: dict[Path, _NodeState | None] = {}
        parent_handles: dict[Path, int] = {}
        created_records: list[_CreatedDirectory] = []
        stages: dict[Path, _Artifact] = {}
        new_recoveries: dict[Path, _Artifact] = {}
        artifacts: list[_Artifact] = []
        commits: list[_CommitRecord] = []
        changed: list[Path] = []

        try:
            for raw_path, raw_plan in sorted(writes.items(), key=lambda item: str(item[0])):
                path = Path(os.path.abspath(raw_path))
                relative = _relative_to_root(self.repository_root, path)
                target_name = relative.name
                parent_path = path.parent
                if parent_path not in parent_handles:
                    parent_fd, _ = _open_parent(
                        self.repository_root,
                        root_fd,
                        path,
                        create=True,
                        created_registry=created_records,
                    )
                    parent_handles[parent_path] = parent_fd
                parent_fd = parent_handles[parent_path]
                original = _read_regular_at(parent_fd, target_name, path)
                originals[path] = original
                if isinstance(raw_plan, PlannedWrite):
                    requested = raw_plan
                else:
                    requested = PlannedWrite(payload=bytes(raw_plan))
                mode = requested.mode if requested.mode is not None else (
                    original.mode if original is not None else 0o644
                )
                uid = requested.uid if requested.uid is not None else (
                    original.uid if original is not None else os.geteuid()
                )
                gid = requested.gid if requested.gid is not None else (
                    original.gid if original is not None else os.getegid()
                )
                plan = PlannedWrite(requested.payload, mode, uid, gid)
                if original is not None and (
                    original.payload == plan.payload
                    and original.mode == plan.mode
                    and original.uid == plan.uid
                    and original.gid == plan.gid
                ):
                    continue
                stage = _create_artifact(
                    parent_fd,
                    parent_path,
                    target_name,
                    plan.payload,
                    plan.mode,
                    plan.uid,
                    plan.gid,
                    "stage",
                    artifacts,
                )
                stages[path] = stage
                if original is None:
                    new_recoveries[path] = _create_artifact(
                        parent_fd,
                        parent_path,
                        target_name,
                        plan.payload,
                        plan.mode,
                        plan.uid,
                        plan.gid,
                        "recovery",
                        artifacts,
                    )
                changed.append(path)

            for path in deletion_paths:
                relative = _relative_to_root(self.repository_root, path)
                parent_path = path.parent
                if parent_path not in parent_handles:
                    parent_fd, _ = _open_parent(
                        self.repository_root,
                        root_fd,
                        path,
                        create=False,
                    )
                    parent_handles[parent_path] = parent_fd
                parent_fd = parent_handles[parent_path]
                original = _read_regular_at(parent_fd, relative.name, path)
                if original is None:
                    raise ValueError(f"quest transaction deletion target is missing: {path}")
                originals[path] = original
                changed.append(path)

            created_directories = {
                record.path: record.state
                for record in created_records
                if record.state is not None
            }
            ignored = {artifact.path for artifact in artifacts if artifact.present}
            frozen.assert_matches(
                added_directories=created_directories,
                ignored=ignored,
            )

            for path in changed:
                original = originals[path]
                target_name = path.name
                if path in deletion_paths:
                    assert original is not None
                    parent_fd = parent_handles[path.parent]
                    backup_name = (
                        f".{target_name}.afterlight-delete-{uuid.uuid4().hex}"
                    )
                    backup = _Artifact(
                        path=path.parent / backup_name,
                        parent_fd=parent_fd,
                        name=backup_name,
                        created_state=original,
                        state=original,
                        present=False,
                    )
                    artifacts.append(backup)
                    record = _CommitRecord(
                        target=path,
                        parent_fd=parent_fd,
                        target_name=target_name,
                        original=original,
                        installed=None,
                        backup=backup,
                        stage=None,
                        operation="delete",
                    )
                    commits.append(record)
                    _atomic_no_replace(parent_fd, target_name, backup_name)
                    record.phase = "promoted"
                    backup.present = True
                    _fsync_directory_fd(parent_fd)
                    moved = _read_any_at(parent_fd, backup_name, backup.path)
                    public = _read_any_at(parent_fd, target_name, path)
                    if moved is None or not _states_match(original, moved) or public is not None:
                        if moved is not None:
                            backup.state = moved
                        mismatch = ValueError(
                            f"quest transaction target changed after preflight: {path}"
                        )
                        self._restore_moved_name(record, backup, moved, mismatch)
                        raise mismatch
                    continue
                stage = stages[path]
                assert stage.state is not None
                if original is None:
                    record = _CommitRecord(
                        target=path,
                        parent_fd=stage.parent_fd,
                        target_name=target_name,
                        original=None,
                        installed=stage.state,
                        backup=new_recoveries[path],
                        stage=stage,
                        operation="create",
                    )
                    commits.append(record)
                    _atomic_no_replace(stage.parent_fd, stage.name, target_name)
                    record.phase = "promoted"
                    stage.present = False
                    _fsync_directory_fd(stage.parent_fd)
                    installed = _read_any_at(stage.parent_fd, target_name, path)
                    if installed is None or not _states_match(record.installed, installed):
                        raise QuestBuildRollbackError(
                            ValueError(
                                f"quest transaction installed file changed: {path}"
                            ),
                            unresolved_paths=(path,),
                            recovery_paths=(new_recoveries[path].path,),
                        )
                    continue

                record = _CommitRecord(
                    target=path,
                    parent_fd=stage.parent_fd,
                    target_name=target_name,
                    original=original,
                    installed=stage.state,
                    backup=stage,
                    stage=stage,
                    operation="replace",
                )
                commits.append(record)
                _atomic_exchange(stage.parent_fd, stage.name, target_name)
                record.phase = "promoted"
                stage.state = original
                _fsync_directory_fd(stage.parent_fd)
                swapped_out = _read_any_at(stage.parent_fd, stage.name, stage.path)
                installed = _read_any_at(stage.parent_fd, target_name, path)
                if (
                    swapped_out is None
                    or not _states_match(original, swapped_out)
                    or installed is None
                    or not _states_match(record.installed, installed)
                ):
                    mismatch_error = ValueError(
                        f"quest transaction target changed after preflight: {path}"
                    )
                    if swapped_out is not None:
                        stage.state = swapped_out
                    self._restore_exchange(record, swapped_out, mismatch_error)
                    raise mismatch_error

            overrides = {
                record.target: record.installed
                for record in commits
            }
            recovery_paths = {
                artifact.path for artifact in artifacts if artifact.present
            }
            frozen.assert_matches(
                overrides=overrides,
                added_directories=created_directories,
                ignored=recovery_paths,
            )
            if post_validate is not None:
                post_validate()
                frozen.assert_matches(
                    overrides=overrides,
                    added_directories=created_directories,
                    ignored=recovery_paths,
                )

            committed_cleanup_errors: list[BaseException] = []
            retained_recovery: list[Path] = []
            for artifact in artifacts:
                try:
                    _cleanup_private_artifact(artifact)
                except BaseException as cleanup_error:
                    committed_cleanup_errors.append(cleanup_error)
                    if _artifact_current_state(artifact) is not None:
                        artifact.retain = True
                        retained_recovery.append(artifact.path)
            return PromotionResult(
                changed,
                cleanup_warnings=committed_cleanup_errors,
                recovery_paths=retained_recovery,
            )
        except BaseException as error:
            if isinstance(error, QuestBuildRollbackError):
                aggregate_primary = error.primary_error
                unresolved = list(error.unresolved_paths)
                recovery = list(error.recovery_paths)
                rollback_errors = list(error.rollback_errors)
                cleanup_errors = list(error.cleanup_errors)
            else:
                aggregate_primary = error
                unresolved = []
                recovery = []
                rollback_errors = []
                cleanup_errors = []
            (
                owned_unresolved,
                owned_recovery,
                owned_rollback_errors,
                owned_cleanup_errors,
            ) = (
                self._rollback_committed(
                    commits,
                    skip_targets=frozenset(unresolved),
                )
            )
            unresolved.extend(owned_unresolved)
            recovery.extend(owned_recovery)
            rollback_errors.extend(owned_rollback_errors)
            cleanup_errors.extend(owned_cleanup_errors)
            protected_recovery = set(recovery)
            for artifact in artifacts:
                if artifact.retain or artifact.path in protected_recovery:
                    if _artifact_current_state(artifact) is not None:
                        recovery.append(artifact.path)
                    continue
                try:
                    _cleanup_private_artifact(artifact)
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
                    if _artifact_current_state(artifact) is not None:
                        artifact.retain = True
                        recovery.append(artifact.path)
            if unresolved:
                recovery.extend(
                    record.path
                    for record in created_records
                    if record.phase != "removed"
                )
            else:
                directory_errors, directory_recovery, directory_unresolved = (
                    self._cleanup_created_directories(created_records)
                )
                cleanup_errors.extend(directory_errors)
                recovery.extend(directory_recovery)
                unresolved.extend(directory_unresolved)
            if (
                isinstance(error, QuestBuildRollbackError)
                or unresolved
                or rollback_errors
                or cleanup_errors
            ):
                raise QuestBuildRollbackError(
                    aggregate_primary,
                    unresolved_paths=unresolved,
                    recovery_paths=recovery,
                    rollback_errors=rollback_errors,
                    cleanup_errors=cleanup_errors,
                ) from error
            raise
        finally:
            for descriptor in parent_handles.values():
                os.close(descriptor)
            for record in created_records:
                os.close(record.parent_fd)

    def _rollback_committed(
        self,
        commits: Sequence[_CommitRecord],
        *,
        skip_targets: frozenset[Path] = frozenset(),
    ) -> tuple[
        list[Path],
        list[Path],
        list[BaseException],
        list[BaseException],
    ]:
        unresolved: list[Path] = []
        recovery: list[Path] = []
        rollback_errors: list[BaseException] = []
        cleanup_errors: list[BaseException] = []
        for record in reversed(commits):
            if record.target in skip_targets or record.phase in {"pending", "rolled-back"}:
                continue
            if record.phase == "unresolved":
                unresolved.append(record.target)
                if record.backup is not None and _artifact_current_state(record.backup) is not None:
                    recovery.append(record.backup.path)
                continue
            try:
                self._rollback_record(record)
            except BaseException as error:
                if record.phase == "rolled-back":
                    cleanup_errors.append(error)
                    continue
                unresolved.append(record.target)
                rollback_errors.append(error)
                if record.backup is not None and _artifact_current_state(record.backup) is not None:
                    record.backup.retain = True
                    recovery.append(record.backup.path)
                if record.stage is not None and _artifact_current_state(record.stage) is not None:
                    record.stage.retain = True
                    recovery.append(record.stage.path)
        return unresolved, recovery, rollback_errors, cleanup_errors

    def _rollback_record(self, record: _CommitRecord) -> None:
        if record.operation == "delete":
            assert record.backup is not None
            assert record.original is not None
            self._restore_moved_name(
                record,
                record.backup,
                record.original,
                ValueError(
                    f"quest transaction deletion rollback verification failed: {record.target}"
                ),
            )
            return

        if record.operation == "replace":
            assert record.backup is not None
            assert record.original is not None
            self._restore_exchange(
                record,
                record.original,
                ValueError(f"quest transaction lost rollback ownership: {record.target}"),
            )
            return

        assert record.stage is not None
        assert record.installed is not None
        stage = record.stage
        try:
            _atomic_no_replace(record.parent_fd, record.target_name, stage.name)
            record.phase = "rollback-moved"
            stage.present = True
            stage.state = record.installed
            sync_error: BaseException | None = None
            try:
                _fsync_directory_fd(record.parent_fd)
            except BaseException as error:
                sync_error = error
            moved = _read_any_at(record.parent_fd, stage.name, stage.path)
            if moved is not None and _states_match(record.installed, moved):
                record.phase = "rolled-back"
                if sync_error is not None:
                    raise sync_error
                return
            if moved is not None:
                stage.state = moved
            ownership_error = ValueError(
                f"quest transaction lost rollback ownership: {record.target}"
            )
            self._restore_moved_name(record, stage, moved, ownership_error)
            record.phase = "unresolved"
            if record.backup is not None:
                record.backup.retain = True
            raise QuestBuildRollbackError(
                ownership_error,
                unresolved_paths=(record.target,),
                recovery_paths=(record.backup.path,) if record.backup is not None else (),
            ) from ownership_error
        except FileNotFoundError as error:
            record.phase = "unresolved"
            if record.backup is not None:
                record.backup.retain = True
            raise QuestBuildRollbackError(
                error,
                unresolved_paths=(record.target,),
                recovery_paths=(record.backup.path,) if record.backup is not None else (),
            ) from error

    def _restore_exchange(
        self,
        record: _CommitRecord,
        desired_public: _NodeState | None,
        primary_error: BaseException,
    ) -> None:
        assert record.backup is not None
        assert record.installed is not None
        backup = record.backup
        try:
            _atomic_exchange(record.parent_fd, backup.name, record.target_name)
            record.phase = "reverse-swapped"
            backup.state = record.installed
            sync_error: BaseException | None = None
            try:
                _fsync_directory_fd(record.parent_fd)
            except BaseException as error:
                sync_error = error
            public = _read_any_at(record.parent_fd, record.target_name, record.target)
            private = _read_any_at(record.parent_fd, backup.name, backup.path)
            if (
                desired_public is not None
                and public is not None
                and _states_match(desired_public, public)
                and private is not None
                and _states_match(record.installed, private)
            ):
                record.phase = "rolled-back"
                if sync_error is not None:
                    raise sync_error
                return

            rollback_errors: list[BaseException] = []
            if sync_error is not None:
                rollback_errors.append(sync_error)
            observed_public = public
            observed_private = private
            for _ in range(8):
                if observed_public is None or observed_private is None:
                    break
                _atomic_exchange(record.parent_fd, backup.name, record.target_name)
                record.phase = "correction-swapped"
                correction_sync_error: BaseException | None = None
                try:
                    _fsync_directory_fd(record.parent_fd)
                except BaseException as error:
                    correction_sync_error = error
                corrected_public = _read_any_at(
                    record.parent_fd,
                    record.target_name,
                    record.target,
                )
                corrected_private = _read_any_at(
                    record.parent_fd,
                    backup.name,
                    backup.path,
                )
                if correction_sync_error is not None:
                    rollback_errors.append(correction_sync_error)
                if (
                    corrected_public is not None
                    and corrected_private is not None
                    and _states_match(observed_private, corrected_public)
                    and _states_match(observed_public, corrected_private)
                ):
                    record.phase = "unresolved"
                    backup.state = corrected_private
                    backup.retain = True
                    raise QuestBuildRollbackError(
                        primary_error,
                        unresolved_paths=(record.target,),
                        recovery_paths=(backup.path,),
                        rollback_errors=rollback_errors,
                    ) from primary_error
                observed_public = corrected_public
                observed_private = corrected_private
            record.phase = "unresolved"
            backup.state = observed_private or backup.state
            backup.retain = True
            rollback_errors.append(
                ValueError(
                    f"quest transaction exchange reversal could not be proven: {record.target}"
                )
            )
            raise QuestBuildRollbackError(
                primary_error,
                unresolved_paths=(record.target,),
                recovery_paths=(backup.path,) if observed_private is not None else (),
                rollback_errors=rollback_errors,
            ) from primary_error
        except QuestBuildRollbackError:
            raise
        except BaseException as rollback_error:
            if record.phase == "rolled-back":
                raise
            record.phase = "unresolved"
            backup.retain = True
            raise QuestBuildRollbackError(
                primary_error,
                unresolved_paths=(record.target,),
                recovery_paths=(backup.path,),
                rollback_errors=(rollback_error,),
            ) from primary_error

    def _restore_moved_name(
        self,
        record: _CommitRecord,
        artifact: _Artifact,
        desired_public: _NodeState | None,
        primary_error: BaseException,
    ) -> None:
        try:
            _atomic_no_replace(record.parent_fd, artifact.name, record.target_name)
            record.phase = "rolled-back"
            artifact.present = False
            sync_error: BaseException | None = None
            try:
                _fsync_directory_fd(record.parent_fd)
            except BaseException as error:
                sync_error = error
            restored = _read_any_at(
                record.parent_fd,
                record.target_name,
                record.target,
            )
            if (
                desired_public is None
                or restored is None
                or not _states_match(desired_public, restored)
            ):
                record.phase = "unresolved"
                raise ValueError(
                    f"quest transaction moved-name restoration could not be proven: {record.target}"
                )
            if sync_error is not None:
                raise sync_error
        except BaseException as rollback_error:
            if record.phase == "rolled-back":
                raise
            record.phase = "unresolved"
            artifact.retain = True
            raise QuestBuildRollbackError(
                primary_error,
                unresolved_paths=(record.target,),
                recovery_paths=(artifact.path,) if artifact.present else (),
                rollback_errors=(rollback_error,),
            ) from primary_error

    def _cleanup_created_directories(
        self,
        created: Sequence[_CreatedDirectory],
    ) -> tuple[list[BaseException], list[Path], list[Path]]:
        errors: list[BaseException] = []
        recovery: list[Path] = []
        unresolved: list[Path] = []
        for record in sorted(
            created, key=lambda item: len(item.path.parts), reverse=True
        ):
            private_name = (
                f".{record.name}.afterlight-rollback-{uuid.uuid4().hex}"
            )
            private_path = record.path.parent / private_name
            moved: _NodeState | None = None
            try:
                if record.state is None:
                    raise ValueError(
                        f"quest transaction has no created-directory identity: {record.path}"
                    )
                _atomic_no_replace(record.parent_fd, record.name, private_name)
                record.phase = "moved-private"
                record.private_name = private_name
                record.private_path = private_path
                _fsync_directory_fd(record.parent_fd)
                moved = _read_any_at(record.parent_fd, private_name, private_path)
                if moved is None or not _same_identity(record.state, moved):
                    raise ValueError(
                        f"quest transaction lost created-directory ownership: {record.path}"
                    )
                _remove_created_directory(
                    record,
                    private_name,
                    private_path,
                    moved,
                )
            except BaseException as error:
                restore_error: BaseException | None = None
                if record.phase in {"moved-private", "cleanup-private"}:
                    try:
                        source_name = record.private_name
                        source_path = record.private_path
                        if source_name is None or source_path is None:
                            raise ValueError(
                                "quest transaction lost private created-directory "
                                f"record: {record.path}"
                            )
                        _atomic_no_replace(
                            record.parent_fd,
                            source_name,
                            record.name,
                        )
                        record.phase = "public"
                        record.private_name = None
                        record.private_path = None
                        _fsync_directory_fd(record.parent_fd)
                        restored = _read_any_at(
                            record.parent_fd,
                            record.name,
                            record.path,
                        )
                        expected_restored = moved
                        if expected_restored is None:
                            expected_restored = _read_any_at(
                                record.parent_fd,
                                record.name,
                                record.path,
                            )
                        if (
                            restored is None
                            or expected_restored is None
                            or not _same_identity(expected_restored, restored)
                        ):
                            raise ValueError(
                                "quest transaction could not verify restored "
                                f"created directory: {record.path}"
                            )
                    except BaseException as caught_restore_error:
                        restore_error = caught_restore_error
                errors.append(error)
                unresolved.append(record.path)
                if restore_error is not None:
                    errors.append(restore_error)
                if record.phase in {"moved-private", "cleanup-private"}:
                    if record.private_path is not None:
                        recovery.append(record.private_path)
                elif record.phase == "public":
                    recovery.append(record.path)
        return errors, recovery, unresolved
