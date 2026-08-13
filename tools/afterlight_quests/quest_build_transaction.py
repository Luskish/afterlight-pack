from __future__ import annotations

import ctypes
import fcntl
import hashlib
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


_ACTIVE_ROOTS: set[Path] = set()
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


@dataclass(frozen=True)
class _Artifact:
    path: Path
    parent_fd: int
    name: str
    state: _NodeState


@dataclass(frozen=True)
class _CommitRecord:
    target: Path
    parent_fd: int
    target_name: str
    original: _NodeState | None
    installed: _NodeState | None
    backup: _Artifact | None
    operation: str


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
                _fsync_directory_fd(descriptor)
                status = os.stat(component, dir_fd=descriptor, follow_symlinks=False)
                created.append((current, _node_state(status, None)))
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
) -> _Artifact:
    name = f".{target_name}.afterlight-{kind}-{uuid.uuid4().hex}"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    path = parent_path / name
    try:
        view = memoryview(payload)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        current = os.fstat(descriptor)
        if current.st_uid != uid or current.st_gid != gid:
            os.fchown(descriptor, uid, gid)
        os.fchmod(descriptor, mode)
        os.fsync(descriptor)
        status = os.fstat(descriptor)
        _require_same_device(os.fstat(parent_fd), status, path)
        state = _node_state(status, payload)
        if state.links != 1 or state.kind != "file":
            raise ValueError(f"invalid quest transaction stage: {path}")
        return _Artifact(path=path, parent_fd=parent_fd, name=name, state=state)
    except BaseException:
        try:
            os.unlink(name, dir_fd=parent_fd)
            _fsync_directory_fd(parent_fd)
        except OSError:
            pass
        raise
    finally:
        os.close(descriptor)


def _unlink_artifact(parent_fd: int, name: str) -> None:
    os.unlink(name, dir_fd=parent_fd)
    _fsync_directory_fd(parent_fd)


class QuestBuildTransaction:
    def __init__(self, repository_root: Path) -> None:
        self.repository_root = _absolute_existing_directory(repository_root)
        self._root_fd: int | None = None
        self._lock_fd: int | None = None
        self._active = False
        self._workspace_roots: set[Path] = set()

    def __enter__(self) -> QuestBuildTransaction:
        with _ACTIVE_ROOTS_LOCK:
            if self.repository_root in _ACTIVE_ROOTS:
                raise RuntimeError(
                    f"reentrant quest build transaction is not allowed: {self.repository_root}"
                )
            _ACTIVE_ROOTS.add(self.repository_root)
        lock_directory = Path(tempfile.gettempdir()) / "afterlight-quest-build-locks"
        lock_directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        lock_directory_status = lock_directory.lstat()
        if (
            stat.S_ISLNK(lock_directory_status.st_mode)
            or not stat.S_ISDIR(lock_directory_status.st_mode)
            or lock_directory_status.st_uid != os.geteuid()
        ):
            self._release()
            raise ValueError(f"unsafe quest build lock directory: {lock_directory}")
        key = hashlib.sha256(os.fsencode(self.repository_root)).hexdigest()
        lock_path = lock_directory / f"{key}.lock"
        try:
            lock_flags = os.O_RDWR | os.O_CREAT
            if hasattr(os, "O_NOFOLLOW"):
                lock_flags |= os.O_NOFOLLOW
            self._lock_fd = os.open(lock_path, lock_flags, 0o600)
            lock_status = os.fstat(self._lock_fd)
            if not stat.S_ISREG(lock_status.st_mode) or lock_status.st_nlink != 1:
                raise ValueError(f"unsafe quest build lock file: {lock_path}")
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX)
            self._root_fd = _open_root(self.repository_root)
            self._active = True
            return self
        except BaseException:
            self._release()
            raise

    def __exit__(self, error_type, error, traceback) -> None:
        self._release()

    def _release(self) -> None:
        self._active = False
        self._workspace_roots.clear()
        if self._root_fd is not None:
            os.close(self._root_fd)
            self._root_fd = None
        if self._lock_fd is not None:
            try:
                fcntl.flock(self._lock_fd, fcntl.LOCK_UN)
            finally:
                os.close(self._lock_fd)
                self._lock_fd = None
        with _ACTIVE_ROOTS_LOCK:
            _ACTIVE_ROOTS.discard(self.repository_root)

    def _require_active(self) -> None:
        if not self._active or self._root_fd is None:
            raise RuntimeError("quest build transaction token is not active")

    def require_root(self, repository_root: Path) -> None:
        self._require_active()
        candidate = _absolute_existing_directory(repository_root)
        if candidate != self.repository_root and candidate not in self._workspace_roots:
            raise ValueError(
                "mismatched repository root for quest build transaction: "
                f"expected {self.repository_root}, found {candidate}"
            )

    def authorize_workspace(self, repository_root: Path) -> None:
        self._require_active()
        candidate = _absolute_existing_directory(repository_root)
        if candidate == self.repository_root:
            raise ValueError("repository root cannot be registered as a candidate workspace")
        if candidate in self._workspace_roots:
            raise RuntimeError(f"reentrant quest candidate workspace: {candidate}")
        self._workspace_roots.add(candidate)

    def revoke_workspace(self, repository_root: Path) -> None:
        candidate = Path(os.path.abspath(repository_root))
        if candidate not in self._workspace_roots:
            raise ValueError(f"unknown quest candidate workspace: {candidate}")
        self._workspace_roots.remove(candidate)

    def is_workspace(self, repository_root: Path) -> bool:
        self._require_active()
        return Path(os.path.abspath(repository_root)) in self._workspace_roots

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
    ) -> list[Path]:
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
            return []

        root_fd = self._root_fd
        assert root_fd is not None
        originals: dict[Path, _NodeState | None] = {}
        parent_handles: dict[Path, int] = {}
        created_directories: dict[Path, _NodeState] = {}
        stages: dict[Path, _Artifact] = {}
        new_recoveries: dict[Path, _Artifact] = {}
        extra_artifacts: list[_Artifact] = []
        commits: list[_CommitRecord] = []
        changed: list[Path] = []
        cleanup_errors: list[BaseException] = []
        promotion_complete = False

        try:
            for raw_path, raw_plan in sorted(writes.items(), key=lambda item: str(item[0])):
                path = Path(os.path.abspath(raw_path))
                relative = _relative_to_root(self.repository_root, path)
                target_name = relative.name
                parent_path = path.parent
                if parent_path not in parent_handles:
                    parent_fd, created = _open_parent(
                        self.repository_root,
                        root_fd,
                        path,
                        create=True,
                    )
                    parent_handles[parent_path] = parent_fd
                    created_directories.update(created)
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
                    )
                changed.append(path)

            for path in deletion_paths:
                relative = _relative_to_root(self.repository_root, path)
                parent_path = path.parent
                if parent_path not in parent_handles:
                    parent_fd, created = _open_parent(
                        self.repository_root,
                        root_fd,
                        path,
                        create=False,
                    )
                    parent_handles[parent_path] = parent_fd
                    created_directories.update(created)
                parent_fd = parent_handles[parent_path]
                original = _read_regular_at(parent_fd, relative.name, path)
                if original is None:
                    raise ValueError(f"quest transaction deletion target is missing: {path}")
                originals[path] = original
                stage = _create_artifact(
                    parent_fd,
                    parent_path,
                    relative.name,
                    b"",
                    original.mode,
                    original.uid,
                    original.gid,
                    "delete",
                )
                stages[path] = stage
                changed.append(path)

            ignored = {
                *(artifact.path for artifact in stages.values()),
                *(artifact.path for artifact in new_recoveries.values()),
            }
            frozen.assert_matches(
                added_directories=created_directories,
                ignored=ignored,
            )

            for path in changed:
                original = originals[path]
                stage = stages[path]
                target_name = path.name
                if path in deletion_paths:
                    assert original is not None
                    _atomic_exchange(stage.parent_fd, stage.name, target_name)
                    _fsync_directory_fd(stage.parent_fd)
                    swapped_out = _read_regular_at(
                        stage.parent_fd,
                        stage.name,
                        stage.path,
                    )
                    if swapped_out is None or not _states_match(original, swapped_out):
                        mismatch_error = ValueError(
                            f"quest transaction target changed after preflight: {path}"
                        )
                        try:
                            _atomic_exchange(stage.parent_fd, stage.name, target_name)
                            _fsync_directory_fd(stage.parent_fd)
                        except BaseException as rollback_error:
                            raise QuestBuildRollbackError(
                                mismatch_error,
                                unresolved_paths=(path,),
                                recovery_paths=(stage.path,),
                                rollback_errors=(rollback_error,),
                            ) from mismatch_error
                        raise mismatch_error
                    installed = _read_regular_at(
                        stage.parent_fd,
                        target_name,
                        path,
                    )
                    if installed is None or not _states_match(stage.state, installed):
                        raise QuestBuildRollbackError(
                            ValueError(
                                f"quest transaction deletion marker changed: {path}"
                            ),
                            unresolved_paths=(path,),
                            recovery_paths=(stage.path,),
                        )
                    commits.append(
                        _CommitRecord(
                            target=path,
                            parent_fd=stage.parent_fd,
                            target_name=target_name,
                            original=original,
                            installed=installed,
                            backup=_Artifact(
                                path=stage.path,
                                parent_fd=stage.parent_fd,
                                name=stage.name,
                                state=swapped_out,
                            ),
                            operation="delete-staged",
                        )
                    )
                    continue
                if original is None:
                    _atomic_no_replace(stage.parent_fd, stage.name, target_name)
                    _fsync_directory_fd(stage.parent_fd)
                    installed = _read_regular_at(stage.parent_fd, target_name, path)
                    if installed is None or not _states_match(stage.state, installed):
                        raise QuestBuildRollbackError(
                            ValueError(
                                f"quest transaction installed file changed: {path}"
                            ),
                            unresolved_paths=(path,),
                            recovery_paths=(new_recoveries[path].path,),
                        )
                    commits.append(
                        _CommitRecord(
                            target=path,
                            parent_fd=stage.parent_fd,
                            target_name=target_name,
                            original=None,
                            installed=installed,
                            backup=new_recoveries[path],
                            operation="create",
                        )
                    )
                    continue

                _atomic_exchange(stage.parent_fd, stage.name, target_name)
                _fsync_directory_fd(stage.parent_fd)
                swapped_out = _read_regular_at(stage.parent_fd, stage.name, stage.path)
                if swapped_out is None or not _states_match(original, swapped_out):
                    mismatch_error = ValueError(
                        f"quest transaction target changed after preflight: {path}"
                    )
                    try:
                        _atomic_exchange(stage.parent_fd, stage.name, target_name)
                        _fsync_directory_fd(stage.parent_fd)
                    except BaseException as rollback_error:
                        raise QuestBuildRollbackError(
                            mismatch_error,
                            unresolved_paths=(path,),
                            recovery_paths=(stage.path,),
                            rollback_errors=(rollback_error,),
                        ) from mismatch_error
                    raise mismatch_error
                installed = _read_regular_at(stage.parent_fd, target_name, path)
                if installed is None or not _states_match(stage.state, installed):
                    raise QuestBuildRollbackError(
                        ValueError(f"quest transaction installed file changed: {path}"),
                        unresolved_paths=(path,),
                        recovery_paths=(stage.path,),
                    )
                backup = _Artifact(
                    path=stage.path,
                    parent_fd=stage.parent_fd,
                    name=stage.name,
                    state=swapped_out,
                )
                commits.append(
                    _CommitRecord(
                        target=path,
                        parent_fd=stage.parent_fd,
                        target_name=target_name,
                        original=original,
                        installed=installed,
                        backup=backup,
                        operation="replace",
                    )
                )

            for index, record in enumerate(tuple(commits)):
                if record.operation != "delete-staged":
                    continue
                removal = _create_artifact(
                    record.parent_fd,
                    record.target.parent,
                    record.target_name,
                    b"",
                    0o600,
                    os.geteuid(),
                    os.getegid(),
                    "remove",
                )
                extra_artifacts.append(removal)
                exchanged = False
                try:
                    _atomic_exchange(
                        record.parent_fd,
                        removal.name,
                        record.target_name,
                    )
                    exchanged = True
                    _fsync_directory_fd(record.parent_fd)
                    swapped_marker = _read_regular_at(
                        record.parent_fd,
                        removal.name,
                        removal.path,
                    )
                    if (
                        swapped_marker is None
                        or record.installed is None
                        or not _states_match(record.installed, swapped_marker)
                    ):
                        raise ValueError(
                            f"quest transaction lost deletion ownership: {record.target}"
                        )
                    _unlink_artifact(record.parent_fd, record.target_name)
                    commits[index] = _CommitRecord(
                        target=record.target,
                        parent_fd=record.parent_fd,
                        target_name=record.target_name,
                        original=record.original,
                        installed=None,
                        backup=record.backup,
                        operation="delete",
                    )
                    exchanged = False
                    _unlink_artifact(record.parent_fd, removal.name)
                except BaseException as deletion_error:
                    if exchanged:
                        try:
                            _atomic_exchange(
                                record.parent_fd,
                                removal.name,
                                record.target_name,
                            )
                            _fsync_directory_fd(record.parent_fd)
                            exchanged = False
                        except BaseException as exchange_back_error:
                            recovery_paths = [removal.path]
                            if record.backup is not None:
                                recovery_paths.append(record.backup.path)
                            raise QuestBuildRollbackError(
                                deletion_error,
                                unresolved_paths=(record.target,),
                                recovery_paths=recovery_paths,
                                rollback_errors=(exchange_back_error,),
                            ) from deletion_error
                    raise

            overrides = {
                record.target: record.installed
                for record in commits
            }
            recovery_paths = {
                record.backup.path
                for record in commits
                if record.backup is not None
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

            promotion_complete = True
            committed_cleanup_errors: list[BaseException] = []
            retained_recovery: list[Path] = []
            for record in commits:
                if record.backup is not None:
                    try:
                        _unlink_artifact(record.backup.parent_fd, record.backup.name)
                    except BaseException as cleanup_error:
                        committed_cleanup_errors.append(cleanup_error)
                        if record.backup.path.exists():
                            retained_recovery.append(record.backup.path)
            if committed_cleanup_errors:
                raise QuestBuildRollbackError(
                    RuntimeError("quest transaction cleanup failure"),
                    unresolved_paths=(),
                    recovery_paths=retained_recovery,
                    cleanup_errors=committed_cleanup_errors,
                )
            return changed
        except BaseException as error:
            if promotion_complete:
                raise
            if isinstance(error, QuestBuildRollbackError):
                aggregate_primary = error.primary_error
                unresolved = list(error.unresolved_paths)
                recovery = list(error.recovery_paths)
                rollback_errors = list(error.rollback_errors)
                cleanup_errors.extend(error.cleanup_errors)
            else:
                aggregate_primary = error
                unresolved = []
                recovery = []
                rollback_errors = []
            owned_unresolved, owned_recovery, owned_rollback_errors = (
                self._rollback_committed(
                    commits,
                    skip_targets=frozenset(unresolved),
                )
            )
            unresolved.extend(owned_unresolved)
            recovery.extend(owned_recovery)
            rollback_errors.extend(owned_rollback_errors)
            protected_recovery = set(recovery)
            for path, artifact in stages.items():
                if any(record.target == path for record in commits):
                    continue
                if artifact.path in protected_recovery:
                    continue
                try:
                    if artifact.path.exists():
                        _unlink_artifact(artifact.parent_fd, artifact.name)
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
                    recovery.append(artifact.path)
            for artifact in extra_artifacts:
                if artifact.path in protected_recovery:
                    continue
                try:
                    if artifact.path.exists():
                        _unlink_artifact(artifact.parent_fd, artifact.name)
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
                    recovery.append(artifact.path)
            for path, artifact in new_recoveries.items():
                if any(record.target == path for record in commits):
                    continue
                if artifact.path in protected_recovery:
                    continue
                try:
                    if artifact.path.exists():
                        _unlink_artifact(artifact.parent_fd, artifact.name)
                except BaseException as cleanup_error:
                    cleanup_errors.append(cleanup_error)
                    recovery.append(artifact.path)
            if unresolved:
                recovery.extend(
                    path
                    for path in created_directories
                    if path.exists()
                )
            else:
                cleanup_errors.extend(
                    self._cleanup_created_directories(created_directories)
                )
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

    def _rollback_committed(
        self,
        commits: Sequence[_CommitRecord],
        *,
        skip_targets: frozenset[Path] = frozenset(),
    ) -> tuple[list[Path], list[Path], list[BaseException]]:
        unresolved: list[Path] = []
        recovery: list[Path] = []
        rollback_errors: list[BaseException] = []
        for record in reversed(commits):
            if record.target in skip_targets:
                continue
            try:
                self._rollback_record(record)
            except BaseException as error:
                unresolved.append(record.target)
                rollback_errors.append(error)
                if record.backup is not None and record.backup.path.exists():
                    recovery.append(record.backup.path)
        return unresolved, recovery, rollback_errors

    def _rollback_record(self, record: _CommitRecord) -> None:
        if record.operation == "delete":
            assert record.backup is not None
            assert record.original is not None
            _atomic_no_replace(
                record.parent_fd,
                record.backup.name,
                record.target_name,
            )
            _fsync_directory_fd(record.parent_fd)
            restored = _read_regular_at(
                record.parent_fd,
                record.target_name,
                record.target,
            )
            if restored is None or not _states_match(record.original, restored):
                raise ValueError(
                    f"quest transaction deletion rollback verification failed: {record.target}"
                )
            return

        if record.operation == "delete-staged":
            assert record.backup is not None
            assert record.original is not None
            _atomic_exchange(
                record.parent_fd,
                record.backup.name,
                record.target_name,
            )
            _fsync_directory_fd(record.parent_fd)
            swapped_marker = _read_regular_at(
                record.parent_fd,
                record.backup.name,
                record.backup.path,
            )
            restored = _read_regular_at(
                record.parent_fd,
                record.target_name,
                record.target,
            )
            if (
                swapped_marker is None
                or record.installed is None
                or not _states_match(record.installed, swapped_marker)
                or restored is None
                or not _states_match(record.original, restored)
            ):
                _atomic_exchange(
                    record.parent_fd,
                    record.backup.name,
                    record.target_name,
                )
                _fsync_directory_fd(record.parent_fd)
                raise ValueError(
                    f"quest transaction lost deletion rollback ownership: {record.target}"
                )
            _unlink_artifact(record.parent_fd, record.backup.name)
            return

        if record.operation == "replace":
            assert record.backup is not None
            assert record.original is not None
            _atomic_exchange(
                record.parent_fd,
                record.backup.name,
                record.target_name,
            )
            _fsync_directory_fd(record.parent_fd)
            swapped_installed = _read_regular_at(
                record.parent_fd,
                record.backup.name,
                record.backup.path,
            )
            restored = _read_regular_at(
                record.parent_fd,
                record.target_name,
                record.target,
            )
            if (
                swapped_installed is None
                or record.installed is None
                or not _states_match(record.installed, swapped_installed)
                or restored is None
                or not _states_match(record.original, restored)
            ):
                _atomic_exchange(
                    record.parent_fd,
                    record.backup.name,
                    record.target_name,
                )
                _fsync_directory_fd(record.parent_fd)
                raise ValueError(
                    f"quest transaction lost rollback ownership: {record.target}"
                )
            _unlink_artifact(record.parent_fd, record.backup.name)
            return

        marker = _create_artifact(
            record.parent_fd,
            record.target.parent,
            record.target_name,
            b"",
            0o600,
            os.geteuid(),
            os.getegid(),
            "rollback",
        )
        try:
            _atomic_exchange(record.parent_fd, marker.name, record.target_name)
            _fsync_directory_fd(record.parent_fd)
            swapped_installed = _read_regular_at(
                record.parent_fd,
                marker.name,
                marker.path,
            )
            if (
                swapped_installed is None
                or record.installed is None
                or not _states_match(record.installed, swapped_installed)
            ):
                _atomic_exchange(record.parent_fd, marker.name, record.target_name)
                _fsync_directory_fd(record.parent_fd)
                raise ValueError(
                    f"quest transaction lost rollback ownership: {record.target}"
                )
            _unlink_artifact(record.parent_fd, record.target_name)
            _unlink_artifact(record.parent_fd, marker.name)
            if record.backup is not None:
                _unlink_artifact(record.backup.parent_fd, record.backup.name)
        except BaseException:
            raise

    def _cleanup_created_directories(
        self,
        created: Mapping[Path, _NodeState],
    ) -> list[BaseException]:
        errors: list[BaseException] = []
        for path, expected in sorted(
            created.items(), key=lambda item: len(item[0].parts), reverse=True
        ):
            try:
                current = _read_path(path)
                if not _states_match(expected, current):
                    raise ValueError(
                        f"quest transaction lost created-directory ownership: {path}"
                    )
                path.rmdir()
                parent_fd = os.open(path.parent, _directory_flags())
                try:
                    _fsync_directory_fd(parent_fd)
                finally:
                    os.close(parent_fd)
            except BaseException as error:
                errors.append(error)
        return errors
