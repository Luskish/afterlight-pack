from __future__ import annotations

import copy
import os
import importlib
import importlib.util
import json
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())


class QuestBuildTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.transaction_module = __import__(
            "afterlight_quests.quest_build_transaction",
            fromlist=["QuestBuildTransaction"],
        )

    def make_root(self, base: Path) -> tuple[Path, Path, Path]:
        root = base / "repository"
        data = root / "config" / "ftbquests" / "quests"
        data.mkdir(parents=True)
        first = data / "first.snbt"
        second = data / "second.snbt"
        first.write_bytes(b"first-original\n")
        second.write_bytes(b"second-original\n")
        os.chmod(first, 0o640)
        os.chmod(second, 0o600)
        return root, first, second

    @staticmethod
    def inventory(root: Path) -> dict[str, tuple[object, ...]]:
        result: dict[str, tuple[object, ...]] = {}
        for path in sorted(root.rglob("*")):
            status = path.lstat()
            if stat.S_ISREG(status.st_mode):
                kind = "file"
                payload = path.read_bytes()
            elif stat.S_ISDIR(status.st_mode):
                kind = "directory"
                payload = None
            elif stat.S_ISLNK(status.st_mode):
                kind = "symlink"
                payload = os.readlink(path)
            else:
                kind = "other"
                payload = None
            result[path.relative_to(root).as_posix()] = (
                kind,
                status.st_dev,
                status.st_ino,
                stat.S_IMODE(status.st_mode),
                status.st_uid,
                status.st_gid,
                status.st_nlink,
                payload,
            )
        return result

    @staticmethod
    def path_identity(path: Path) -> tuple[object, ...]:
        try:
            status = path.lstat()
        except FileNotFoundError:
            return ("missing",)
        if stat.S_ISREG(status.st_mode):
            kind = "file"
            payload: object = path.read_bytes()
        elif stat.S_ISDIR(status.st_mode):
            kind = "directory"
            payload = tuple(sorted(child.name for child in path.iterdir()))
        elif stat.S_ISLNK(status.st_mode):
            kind = "symlink"
            payload = os.readlink(path)
        else:
            kind = "other"
            payload = None
        return (
            kind,
            status.st_dev,
            status.st_ino,
            stat.S_IMODE(status.st_mode),
            status.st_uid,
            status.st_gid,
            status.st_nlink,
            payload,
        )

    def install_raced_object(self, path: Path, kind: str) -> tuple[object, ...]:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)
        if kind == "missing":
            return self.path_identity(path)
        if kind == "regular":
            temporary = path.with_name(f".{path.name}.third-party")
            temporary.write_bytes(b"third-party-regular\n")
            os.replace(temporary, path)
        elif kind == "symlink":
            source = path.with_name(f".{path.name}.symlink-source")
            source.write_bytes(b"third-party-symlink-source\n")
            path.symlink_to(source.name)
        elif kind == "hardlink":
            source = path.with_name(f".{path.name}.hardlink-source")
            source.write_bytes(b"third-party-hardlink\n")
            os.link(source, path)
        elif kind == "directory":
            path.mkdir()
        else:
            self.fail(f"unknown raced object kind: {kind}")
        return self.path_identity(path)

    def freeze(self, transaction, root: Path):
        return transaction.freeze((root / "config",))

    def test_repository_lock_rejects_reentrant_and_mismatched_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _, _ = self.make_root(Path(temp_dir))
            other = Path(temp_dir) / "other"
            other.mkdir()
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                with self.assertRaisesRegex(RuntimeError, "reentrant"):
                    with self.transaction_module.QuestBuildTransaction(root):
                        pass
                with self.assertRaisesRegex(ValueError, "mismatched repository root"):
                    transaction.require_root(other)

    def test_repository_lock_rejects_same_inode_case_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, _, _ = self.make_root(Path(temp_dir))
            alias = root.with_name(root.name.upper())
            try:
                alias_status = alias.stat()
            except FileNotFoundError:
                self.skipTest("temporary filesystem is case-sensitive")
            root_status = root.stat()
            if (root_status.st_dev, root_status.st_ino) != (
                alias_status.st_dev,
                alias_status.st_ino,
            ):
                self.skipTest("case alias does not resolve to the same inode")
            with self.transaction_module.QuestBuildTransaction(root):
                with self.assertRaisesRegex(RuntimeError, "reentrant"):
                    with self.transaction_module.QuestBuildTransaction(alias):
                        pass

    def test_every_enter_failure_releases_process_lock_state(self) -> None:
        cases = (
            ("lock directory creation", Path, "mkdir", OSError("mkdir failed")),
            ("lock directory inspection", Path, "lstat", OSError("lstat failed")),
            (
                "lock file open",
                self.transaction_module.os,
                "open",
                OSError("lock open failed"),
            ),
            (
                "filesystem lock",
                self.transaction_module.fcntl,
                "flock",
                OSError("flock failed"),
            ),
            (
                "root open",
                self.transaction_module,
                "_open_root",
                OSError("root open failed"),
            ),
        )
        for label, owner, attribute, injected in cases:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                root, _, _ = self.make_root(Path(temp_dir))
                original = getattr(owner, attribute)

                def fail_selected(*arguments, **keywords):
                    if label == "lock file open":
                        path = os.fspath(arguments[0])
                        if not path.endswith(".lock"):
                            return original(*arguments, **keywords)
                    raise injected

                with mock.patch.object(owner, attribute, side_effect=fail_selected):
                    with self.assertRaisesRegex(OSError, str(injected)):
                        with self.transaction_module.QuestBuildTransaction(root):
                            pass
                with self.transaction_module.QuestBuildTransaction(root):
                    pass

    def test_post_rename_fsync_failure_restores_exact_inventory(self) -> None:
        for operation in ("replace", "create", "delete"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                target = first if operation != "create" else first.with_name("new.snbt")
                before = self.inventory(root)
                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_fsync_directory_fd",
                        side_effect=OSError("post-rename fsync failed"),
                    ):
                        with self.assertRaisesRegex(BaseException, "post-rename fsync"):
                            if operation == "delete":
                                transaction.promote_bytes({}, frozen, deletions=(target,))
                            else:
                                transaction.promote_bytes(
                                    {target: b"transaction-output\n"},
                                    frozen,
                                )
                self.assertEqual(self.inventory(root), before)

    def test_actual_platform_exchange_races_preserve_every_public_object_type(self) -> None:
        for kind in ("regular", "symlink", "hardlink", "directory", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                expected: tuple[object, ...] | None = None
                raced = False
                real_exchange = self.transaction_module._atomic_exchange

                def race_then_exchange(parent_fd, staged_name, target_name):
                    nonlocal expected, raced
                    if not raced:
                        raced = True
                        expected = self.install_raced_object(first, kind)
                    return real_exchange(parent_fd, staged_name, target_name)

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_atomic_exchange",
                        side_effect=race_then_exchange,
                    ):
                        with self.assertRaises(BaseException):
                            transaction.promote_bytes(
                                {first: b"transaction-output\n"},
                                frozen,
                            )
                self.assertTrue(raced)
                self.assertEqual(self.path_identity(first), expected)

    def test_actual_platform_rollback_exchange_preserves_every_public_object_type(self) -> None:
        for kind in ("regular", "symlink", "hardlink", "directory", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                expected: tuple[object, ...] | None = None

                def race_and_fail_validation() -> None:
                    nonlocal expected
                    expected = self.install_raced_object(first, kind)
                    raise ValueError("post-validation race")

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {first: b"transaction-output\n"},
                            frozen,
                            post_validate=race_and_fail_validation,
                        )
                self.assertEqual(self.path_identity(first), expected)
                self.assertIn(first, raised.exception.unresolved_paths)
                self.assertTrue(raised.exception.recovery_paths)
                self.assertTrue(
                    any(path.read_bytes() == b"first-original\n" for path in raised.exception.recovery_paths)
                )

    def test_exchange_back_boundary_preserves_latest_public_object_type(self) -> None:
        for kind in ("regular", "symlink", "hardlink", "directory", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                real_exchange = self.transaction_module._atomic_exchange
                exchange_count = 0
                expected: tuple[object, ...] | None = None

                def race_each_boundary(parent_fd, staged_name, target_name):
                    nonlocal exchange_count, expected
                    exchange_count += 1
                    if exchange_count == 1:
                        self.install_raced_object(first, "regular")
                    elif exchange_count == 2:
                        expected = self.install_raced_object(first, kind)
                    return real_exchange(parent_fd, staged_name, target_name)

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_atomic_exchange",
                        side_effect=race_each_boundary,
                    ):
                        with self.assertRaises(
                            self.transaction_module.QuestBuildRollbackError
                        ) as raised:
                            transaction.promote_bytes(
                                {first: b"transaction-output\n"},
                                frozen,
                            )

                self.assertGreaterEqual(exchange_count, 2)
                self.assertEqual(self.path_identity(first), expected)
                self.assertIn(first, raised.exception.unresolved_paths)
                self.assertTrue(raised.exception.recovery_paths)

    def test_corrective_exchange_boundary_preserves_latest_public_object_type(self) -> None:
        for kind in ("regular", "symlink", "hardlink", "directory", "missing"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                real_exchange = self.transaction_module._atomic_exchange
                exchange_count = 0
                expected: tuple[object, ...] | None = None

                def race_corrective_exchange(parent_fd, staged_name, target_name):
                    nonlocal exchange_count, expected
                    exchange_count += 1
                    if exchange_count == 3:
                        expected = self.install_raced_object(first, kind)
                    return real_exchange(parent_fd, staged_name, target_name)

                def install_first_race() -> None:
                    self.install_raced_object(first, "regular")
                    raise ValueError("force rollback race")

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_atomic_exchange",
                        side_effect=race_corrective_exchange,
                    ):
                        with self.assertRaises(
                            self.transaction_module.QuestBuildRollbackError
                        ) as raised:
                            transaction.promote_bytes(
                                {first: b"transaction-output\n"},
                                frozen,
                                post_validate=install_first_race,
                            )

                self.assertGreaterEqual(exchange_count, 3)
                self.assertEqual(self.path_identity(first), expected)
                self.assertIn(first, raised.exception.unresolved_paths)
                self.assertTrue(raised.exception.recovery_paths)

    def test_actual_platform_atomic_wrappers_exchange_and_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            parent = Path(temp_dir)
            left = parent / "left"
            right = parent / "right"
            destination = parent / "destination"
            left.write_bytes(b"left")
            right.write_bytes(b"right")
            left_inode = left.stat().st_ino
            right_inode = right.stat().st_ino
            descriptor = os.open(parent, self.transaction_module._directory_flags())
            try:
                self.transaction_module._atomic_exchange(descriptor, left.name, right.name)
                self.assertEqual((left.read_bytes(), left.stat().st_ino), (b"right", right_inode))
                self.assertEqual((right.read_bytes(), right.stat().st_ino), (b"left", left_inode))
                self.transaction_module._atomic_no_replace(
                    descriptor,
                    right.name,
                    destination.name,
                )
                self.assertFalse(right.exists())
                self.assertEqual((destination.read_bytes(), destination.stat().st_ino), (b"left", left_inode))
                collision = parent / "collision"
                collision.write_bytes(b"collision")
                with self.assertRaises(FileExistsError):
                    self.transaction_module._atomic_no_replace(
                        descriptor,
                        destination.name,
                        collision.name,
                    )
                self.assertEqual(destination.read_bytes(), b"left")
                self.assertEqual(collision.read_bytes(), b"collision")
            finally:
                os.close(descriptor)

    def test_race_after_final_recheck_is_exchanged_back_without_data_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            third_party = b"third-party-race\n"
            original_exchange = self.transaction_module._atomic_exchange
            raced = False

            def race_then_exchange(parent_fd, staged_name, target_name):
                nonlocal raced
                if not raced:
                    raced = True
                    replacement = first.with_name("third-party.tmp")
                    replacement.write_bytes(third_party)
                    os.replace(replacement, first)
                return original_exchange(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=race_then_exchange,
                ):
                    with self.assertRaisesRegex(ValueError, "changed after preflight"):
                        transaction.promote_bytes({first: b"transaction-value\n"}, frozen)

            self.assertTrue(raced)
            self.assertEqual(first.read_bytes(), third_party)

    def test_third_party_edit_after_promotion_is_never_clobbered_by_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, second = self.make_root(Path(temp_dir))
            original_exchange = self.transaction_module._atomic_exchange
            exchange_count = 0
            third_party = b"third-party-after-promotion\n"

            def edit_then_fail(parent_fd, staged_name, target_name):
                nonlocal exchange_count
                exchange_count += 1
                if exchange_count == 1:
                    return original_exchange(parent_fd, staged_name, target_name)
                if exchange_count == 2:
                    first.write_bytes(third_party)
                    raise OSError("injected later promotion failure")
                return original_exchange(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=edit_then_fail,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {
                                first: b"first-transaction\n",
                                second: b"second-transaction\n",
                            },
                            frozen,
                        )

            self.assertEqual(first.read_bytes(), third_party)
            self.assertEqual(second.read_bytes(), b"second-original\n")
            self.assertIn(first, raised.exception.unresolved_paths)
            self.assertTrue(raised.exception.recovery_paths)
            self.assertTrue(all(path.exists() for path in raised.exception.recovery_paths))

    def test_failed_exchange_before_mutation_is_not_rolled_back_as_committed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=OSError("replace failed before mutation"),
                ), mock.patch.object(
                    transaction,
                    "_rollback_record",
                    wraps=transaction._rollback_record,
                ) as rollback:
                    with self.assertRaisesRegex(OSError, "before mutation"):
                        transaction.promote_bytes({first: b"new\n"}, frozen)
                rollback.assert_not_called()
            self.assertEqual(self.inventory(root), before)

    def test_symlink_target_symlinked_parent_and_hardlink_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            for case in ("target-symlink", "parent-symlink", "hardlink"):
                with self.subTest(case=case):
                    case_root = base / case
                    root, first, _ = self.make_root(case_root)
                    if case == "target-symlink":
                        payload = first.with_name("payload.snbt")
                        first.rename(payload)
                        first.symlink_to(payload.name)
                    elif case == "parent-symlink":
                        parent = first.parent
                        real_parent = parent.with_name("real-quests")
                        parent.rename(real_parent)
                        parent.symlink_to(real_parent.name, target_is_directory=True)
                        first = real_parent / first.name
                    else:
                        os.link(first, first.with_name("alias.snbt"))
                    before = self.inventory(root)
                    with self.assertRaisesRegex(ValueError, "symlink|hardlink"):
                        with self.transaction_module.QuestBuildTransaction(root) as transaction:
                            frozen = self.freeze(transaction, root)
                            transaction.promote_bytes({first: b"new\n"}, frozen)
                    self.assertEqual(self.inventory(root), before)

    def test_stage_device_mismatch_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "same device"):
            self.transaction_module._require_same_device(
                SimpleNamespace(st_dev=1),
                SimpleNamespace(st_dev=2),
                Path("stage"),
            )

    def test_promotion_stage_device_rejection_preserves_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_require_same_device",
                    side_effect=ValueError("stage is not on the same device"),
                ):
                    with self.assertRaisesRegex(ValueError, "same device"):
                        transaction.promote_bytes({first: b"new\n"}, frozen)
            self.assertEqual(self.inventory(root), before)

    def test_platform_atomic_wrappers_select_exchange_and_no_replace_flags(self) -> None:
        cases = (
            ("Darwin", "renameatx_np", self.transaction_module.RENAME_SWAP, self.transaction_module.RENAME_EXCL),
            ("Linux", "renameat2", self.transaction_module.RENAME_EXCHANGE, self.transaction_module.RENAME_NOREPLACE),
        )
        for platform, function, exchange_flag, no_replace_flag in cases:
            with self.subTest(platform=platform), mock.patch.object(
                self.transaction_module,
                "sys_platform",
                return_value=platform,
            ), mock.patch.object(
                self.transaction_module,
                "_libc_call",
            ) as libc_call:
                self.transaction_module._atomic_exchange(7, "stage", "target")
                self.assertEqual(libc_call.call_args.args[0], function)
                self.assertEqual(libc_call.call_args.args[1][-1], exchange_flag)
                libc_call.reset_mock()
                self.transaction_module._atomic_no_replace(7, "stage", "target")
                self.assertEqual(libc_call.call_args.args[0], function)
                self.assertEqual(libc_call.call_args.args[1][-1], no_replace_flag)

    def test_later_failure_restores_mode_owner_inode_link_type_and_inventory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, second = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            original_exchange = self.transaction_module._atomic_exchange
            exchange_count = 0

            def fail_second(parent_fd, staged_name, target_name):
                nonlocal exchange_count
                exchange_count += 1
                if exchange_count == 2:
                    raise OSError("injected second exchange failure")
                return original_exchange(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=fail_second,
                ):
                    with self.assertRaisesRegex(OSError, "second exchange"):
                        transaction.promote_bytes(
                            {first: b"new-first\n", second: b"new-second\n"},
                            frozen,
                        )
            self.assertEqual(self.inventory(root), before)

    def test_cleanup_failure_is_surfaced_with_retained_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            original_unlink = self.transaction_module._unlink_artifact
            failed = False

            def fail_once(artifact):
                nonlocal failed
                if not failed:
                    failed = True
                    raise OSError("injected cleanup failure")
                return original_unlink(artifact)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=fail_once,
                ):
                    result = transaction.promote_bytes({first: b"new\n"}, frozen)
            self.assertTrue(failed)
            self.assertTrue(result.committed)
            self.assertTrue(result.cleanup_warnings)
            self.assertEqual(first.read_bytes(), b"new\n")
            self.assertEqual(len(result.recovery_paths), 1)
            self.assertEqual(
                result.recovery_paths[0].read_bytes(),
                before["config/ftbquests/quests/first.snbt"][-1],
            )

    def test_in_root_recovery_blocks_retry_without_growing_residue(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=OSError("retain cleanup artifact"),
                ):
                    result = transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertTrue(result.cleanup_warnings)
            self.assertEqual(len(result.unexpected_recovery_paths), 1)
            recovery_identity = self.path_identity(
                result.unexpected_recovery_paths[0]
            )
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                with self.assertRaisesRegex(
                    ValueError,
                    "unresolved quest transaction artifact",
                ):
                    self.freeze(transaction, root)
            self.assertEqual(
                self.path_identity(result.unexpected_recovery_paths[0]),
                recovery_identity,
            )

    def test_private_artifact_payload_or_mode_drift_is_retained(self) -> None:
        for case in ("payload", "mode"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                real_cleanup = self.transaction_module._cleanup_private_artifact
                mutated = False

                def mutate_then_cleanup(artifact):
                    nonlocal mutated
                    if (
                        not mutated
                        and artifact.present
                        and ".afterlight-stage-" in artifact.name
                    ):
                        mutated = True
                        if case == "payload":
                            artifact.path.write_bytes(b"third-party private payload\n")
                        else:
                            os.chmod(artifact.path, 0o711)
                    return real_cleanup(artifact)

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_cleanup_private_artifact",
                        side_effect=mutate_then_cleanup,
                    ):
                        result = transaction.promote_bytes({first: b"new\n"}, frozen)

                self.assertTrue(mutated)
                self.assertTrue(result.committed)
                self.assertTrue(result.cleanup_warnings)
                self.assertEqual(len(result.recovery_paths), 1)
                retained = result.recovery_paths[0]
                self.assertTrue(retained.exists())
                if case == "payload":
                    self.assertEqual(
                        retained.read_bytes(),
                        b"third-party private payload\n",
                    )
                else:
                    self.assertEqual(stat.S_IMODE(retained.stat().st_mode), 0o711)
                retained.unlink()

    def test_private_artifact_replacement_at_unlink_boundary_is_retained(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            real_unlink = self.transaction_module._unlink_artifact
            replacement_identity: tuple[object, ...] | None = None
            injected = False

            def replace_then_unlink(*arguments, **keywords):
                nonlocal injected, replacement_identity
                private_path = arguments[0].path
                if not injected and ".afterlight-stage-" in private_path.name:
                    injected = True
                    replacement = private_path.with_name(
                        f".{private_path.name}.third-party"
                    )
                    replacement.write_bytes(b"third-party cleanup boundary\n")
                    os.chmod(replacement, 0o711)
                    os.replace(replacement, private_path)
                    replacement_identity = self.path_identity(private_path)
                return real_unlink(*arguments, **keywords)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=replace_then_unlink,
                ):
                    result = transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertTrue(injected)
            self.assertIsNotNone(replacement_identity)
            self.assertTrue(result.committed)
            self.assertTrue(result.cleanup_warnings)
            self.assertEqual(len(result.recovery_paths), 1)
            self.assertFalse(result.retained_paths)
            self.assertEqual(
                result.unexpected_recovery_paths,
                result.recovery_paths,
            )
            self.assertEqual(
                self.path_identity(result.recovery_paths[0]),
                replacement_identity,
            )

    def test_final_unlink_hook_cannot_delete_a_private_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            original_identity = self.path_identity(first)
            real_unlink = self.transaction_module.os.unlink
            injected = False
            replacement_path: Path | None = None

            def replace_at_final_unlink(path, *arguments, **keywords):
                nonlocal injected, replacement_path
                name = os.fspath(path)
                if ".afterlight-remove-" in name and not injected:
                    injected = True
                    cleanup_path = first.parent / name
                    replacement = cleanup_path.with_name(
                        f".{cleanup_path.name}.third-party"
                    )
                    replacement.write_bytes(b"third-party final unlink bytes\n")
                    os.chmod(replacement, 0o711)
                    os.replace(replacement, cleanup_path)
                    replacement_path = cleanup_path
                return real_unlink(path, *arguments, **keywords)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module.os,
                    "unlink",
                    side_effect=replace_at_final_unlink,
                ):
                    result = transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertFalse(injected)
            self.assertIsNone(replacement_path)
            self.assertFalse(result.cleanup_warnings)
            self.assertEqual(len(result.recovery_paths), 1)
            self.assertEqual(
                self.path_identity(result.recovery_paths[0]),
                original_identity,
            )

    def test_repeated_success_reuses_bounded_retention_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            observed_retention: set[Path] = set()

            for index in range(8):
                payload = f"replacement-{index}\n".encode("utf-8")
                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    result = transaction.promote_bytes({first: payload}, frozen)
                self.assertFalse(result.cleanup_warnings)
                self.assertEqual(len(result.recovery_paths), 1)
                self.assertEqual(result.retained_paths, result.recovery_paths)
                self.assertFalse(result.unexpected_recovery_paths)
                observed_retention.update(result.recovery_paths)
                self.assertEqual(first.read_bytes(), payload)
                self.assertLessEqual(
                    len([path for path in observed_retention if path.exists()]),
                    1,
                )

            retained_before = {
                path: self.path_identity(path)
                for path in observed_retention
                if path.exists()
            }
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                result = transaction.promote_bytes(
                    {first: b"replacement-7\n"},
                    frozen,
                )
            self.assertEqual(list(result), [])
            self.assertFalse(result.cleanup_warnings)
            self.assertFalse(result.recovery_paths)
            self.assertEqual(
                {
                    path: self.path_identity(path)
                    for path in observed_retention
                    if path.exists()
                },
                retained_before,
            )

    def test_repeated_delete_create_cycles_keep_two_file_records_at_most(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            observed_retention: set[Path] = set()

            for index in range(5):
                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    deleted = transaction.promote_bytes(
                        {},
                        frozen,
                        deletions=(first,),
                    )
                self.assertFalse(first.exists())
                self.assertFalse(deleted.cleanup_warnings)
                observed_retention.update(deleted.recovery_paths)
                self.assertLessEqual(
                    len([path for path in observed_retention if path.exists()]),
                    2,
                )

                payload = f"created-{index}\n".encode("utf-8")
                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    created = transaction.promote_bytes({first: payload}, frozen)
                self.assertEqual(first.read_bytes(), payload)
                self.assertFalse(created.cleanup_warnings)
                observed_retention.update(created.recovery_paths)
                self.assertLessEqual(
                    len([path for path in observed_retention if path.exists()]),
                    2,
                )

    def test_repeated_created_directory_rollbacks_reuse_retention(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            created_parent = first.parent / "new-parent"
            target = created_parent / "new.snbt"
            observed_retention: set[Path] = set()

            for _ in range(5):
                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with self.assertRaisesRegex(ValueError, "force rollback") as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )
                recovery_paths = getattr(raised.exception, "recovery_paths", ())
                self.assertEqual(len(recovery_paths), 3)
                observed_retention.update(recovery_paths)
                self.assertFalse(created_parent.exists())
                self.assertLessEqual(
                    len([path for path in observed_retention if path.exists()]),
                    3,
                )

    def test_artifact_is_registered_before_fsync_and_cleanup_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            original_identity = self.path_identity(first)
            real_fsync = self.transaction_module.os.fsync
            real_move = self.transaction_module._atomic_no_replace_between
            failed_fsync = False
            failed_cleanup = False

            def fail_stage_fsync(descriptor):
                nonlocal failed_fsync
                status = os.fstat(descriptor)
                if stat.S_ISREG(status.st_mode) and not failed_fsync:
                    failed_fsync = True
                    raise OSError("stage fsync failed")
                return real_fsync(descriptor)

            def fail_stage_cleanup(
                source_parent_fd,
                source_name,
                target_parent_fd,
                target_name,
            ):
                nonlocal failed_cleanup
                if (
                    ".afterlight-stage-" in source_name
                    and target_name.startswith(".afterlight-retained-")
                    and not failed_cleanup
                ):
                    failed_cleanup = True
                    raise OSError("stage cleanup failed")
                return real_move(
                    source_parent_fd,
                    source_name,
                    target_parent_fd,
                    target_name,
                )

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module.os,
                    "fsync",
                    side_effect=fail_stage_fsync,
                ), mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace_between",
                    side_effect=fail_stage_cleanup,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertTrue(failed_fsync)
            self.assertTrue(failed_cleanup)
            self.assertEqual(self.path_identity(first), original_identity)
            self.assertEqual(first.read_bytes(), before["config/ftbquests/quests/first.snbt"][-1])
            self.assertTrue(raised.exception.cleanup_errors)
            self.assertEqual(len(raised.exception.recovery_paths), 1)
            self.assertTrue(raised.exception.recovery_paths[0].exists())
            raised.exception.recovery_paths[0].unlink()

    def test_transactional_deletion_never_unlinks_a_raced_public_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            expected: tuple[object, ...] | None = None
            raced = False
            real_no_replace = self.transaction_module._atomic_no_replace
            real_unlink = self.transaction_module._unlink_artifact

            def race_atomic_move(parent_fd, source_name, destination_name):
                nonlocal expected, raced
                if source_name == first.name and not raced:
                    raced = True
                    expected = self.install_raced_object(first, "regular")
                return real_no_replace(parent_fd, source_name, destination_name)

            def reject_public_unlink(artifact):
                nonlocal expected, raced
                if artifact.name == first.name:
                    raced = True
                    expected = self.install_raced_object(first, "regular")
                return real_unlink(artifact)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=race_atomic_move,
                ), mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=reject_public_unlink,
                ):
                    with self.assertRaises(BaseException):
                        transaction.promote_bytes({}, frozen, deletions=(first,))

            self.assertTrue(raced)
            self.assertEqual(self.path_identity(first), expected)

    def test_new_file_rollback_never_unlinks_a_raced_public_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            target = first.with_name("new.snbt")
            expected: tuple[object, ...] | None = None
            raced = False
            create_done = False
            real_no_replace = self.transaction_module._atomic_no_replace
            real_unlink = self.transaction_module._unlink_artifact

            def race_atomic_move(parent_fd, source_name, destination_name):
                nonlocal expected, raced, create_done
                if destination_name == target.name and not create_done:
                    result = real_no_replace(parent_fd, source_name, destination_name)
                    create_done = True
                    return result
                if source_name == target.name and not raced:
                    raced = True
                    expected = self.install_raced_object(target, "regular")
                return real_no_replace(parent_fd, source_name, destination_name)

            def reject_public_unlink(artifact):
                nonlocal expected, raced
                if artifact.name == target.name:
                    raced = True
                    expected = self.install_raced_object(target, "regular")
                return real_unlink(artifact)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=race_atomic_move,
                ), mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=reject_public_unlink,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )

            self.assertTrue(raced)
            self.assertEqual(self.path_identity(target), expected)
            self.assertIn(target, raised.exception.unresolved_paths)

    def test_created_directory_cleanup_moves_then_verifies_before_removal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            created_parent = first.parent / "new-parent"
            target = created_parent / "new.snbt"
            raced = False
            expected: tuple[object, ...] | None = None
            real_no_replace = self.transaction_module._atomic_no_replace
            real_rmdir = Path.rmdir

            def race_atomic_move(parent_fd, source_name, destination_name):
                nonlocal raced, expected
                if source_name == created_parent.name and not raced:
                    raced = True
                    created_parent.rmdir()
                    created_parent.mkdir(mode=0o700)
                    expected = self.path_identity(created_parent)
                return real_no_replace(parent_fd, source_name, destination_name)

            def race_public_rmdir(path):
                nonlocal raced, expected
                if path == created_parent and not raced:
                    raced = True
                    real_rmdir(path)
                    path.mkdir(mode=0o700)
                    expected = self.path_identity(path)
                return real_rmdir(path)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=race_atomic_move,
                ), mock.patch.object(
                    Path,
                    "rmdir",
                    autospec=True,
                    side_effect=race_public_rmdir,
                ):
                    with self.assertRaises(BaseException):
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )

            self.assertTrue(raced)
            self.assertEqual(self.path_identity(created_parent), expected)

    def test_created_directory_child_is_restored_public_and_reported(self) -> None:
        for child_kind in ("file", "directory"):
            with self.subTest(child_kind=child_kind), tempfile.TemporaryDirectory() as temp_dir:
                root, first, _ = self.make_root(Path(temp_dir))
                created_parent = first.parent / "new-parent"
                target = created_parent / "new.snbt"
                real_no_replace = self.transaction_module._atomic_no_replace
                injected = False

                def add_child_then_move(parent_fd, source_name, destination_name):
                    nonlocal injected
                    if (
                        source_name == created_parent.name
                        and ".afterlight-rollback-" in destination_name
                        and not injected
                    ):
                        injected = True
                        child = created_parent / "third-party"
                        if child_kind == "file":
                            child.write_bytes(b"preserve third-party child\n")
                        else:
                            child.mkdir(mode=0o701)
                            (child / "payload").write_bytes(b"preserve nested bytes\n")
                        os.chmod(created_parent, 0o710)
                    return real_no_replace(parent_fd, source_name, destination_name)

                with self.transaction_module.QuestBuildTransaction(root) as transaction:
                    frozen = self.freeze(transaction, root)
                    with mock.patch.object(
                        self.transaction_module,
                        "_atomic_no_replace",
                        side_effect=add_child_then_move,
                    ):
                        with self.assertRaises(
                            self.transaction_module.QuestBuildRollbackError
                        ) as raised:
                            transaction.promote_bytes(
                                {target: b"transaction-output\n"},
                                frozen,
                                post_validate=lambda: (_ for _ in ()).throw(
                                    ValueError("force rollback")
                                ),
                            )

                self.assertTrue(injected)
                self.assertTrue(created_parent.is_dir())
                self.assertEqual(
                    stat.S_IMODE(created_parent.stat().st_mode),
                    0o710,
                )
                if child_kind == "file":
                    self.assertEqual(
                        (created_parent / "third-party").read_bytes(),
                        b"preserve third-party child\n",
                    )
                else:
                    self.assertEqual(
                        (created_parent / "third-party" / "payload").read_bytes(),
                        b"preserve nested bytes\n",
                    )
                self.assertIn(created_parent, raised.exception.unresolved_paths)
                self.assertIn(created_parent, raised.exception.recovery_paths)
                self.assertFalse(
                    any(
                        ".afterlight-rollback-" in child.name
                        for child in created_parent.parent.iterdir()
                    )
                )

    def test_created_directory_mode_drift_is_restored_public_and_reported(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            created_parent = first.parent / "new-parent"
            target = created_parent / "new.snbt"
            real_no_replace = self.transaction_module._atomic_no_replace
            changed = False

            def chmod_then_move(parent_fd, source_name, destination_name):
                nonlocal changed
                if (
                    source_name == created_parent.name
                    and ".afterlight-rollback-" in destination_name
                    and not changed
                ):
                    changed = True
                    os.chmod(created_parent, 0o711)
                return real_no_replace(parent_fd, source_name, destination_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=chmod_then_move,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )

            self.assertTrue(changed)
            self.assertTrue(created_parent.is_dir())
            self.assertEqual(stat.S_IMODE(created_parent.stat().st_mode), 0o711)
            self.assertIn(created_parent, raised.exception.unresolved_paths)
            self.assertIn(created_parent, raised.exception.recovery_paths)

    def test_created_directory_mutation_at_rmdir_boundary_is_restored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            created_parent = first.parent / "new-parent"
            target = created_parent / "new.snbt"
            real_remove = getattr(
                self.transaction_module,
                "_remove_created_directory",
                None,
            )
            replacement_identity: tuple[object, ...] | None = None
            injected = False

            def mutate_then_remove(*arguments, **keywords):
                nonlocal injected, replacement_identity
                private_path = arguments[2]
                if not injected:
                    injected = True
                    os.chmod(private_path, 0o711)
                    (private_path / "third-party").write_bytes(
                        b"third-party directory child\n"
                    )
                    replacement_identity = self.path_identity(private_path)
                assert real_remove is not None
                return real_remove(*arguments, **keywords)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_remove_created_directory",
                    create=True,
                    side_effect=mutate_then_remove,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )

            self.assertTrue(injected)
            self.assertIsNotNone(replacement_identity)
            self.assertEqual(
                self.path_identity(created_parent),
                replacement_identity,
            )
            self.assertEqual(
                (created_parent / "third-party").read_bytes(),
                b"third-party directory child\n",
            )
            self.assertIn(created_parent, raised.exception.unresolved_paths)
            self.assertIn(created_parent, raised.exception.recovery_paths)

    def test_final_rmdir_hook_cannot_hide_created_directory_mode_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            created_parent = first.parent / "new-parent"
            target = created_parent / "new.snbt"
            real_rmdir = self.transaction_module.os.rmdir
            injected = False

            def chmod_at_final_rmdir(path, *arguments, **keywords):
                nonlocal injected
                name = os.fspath(path)
                if ".afterlight-remove-" in name and not injected:
                    injected = True
                    os.chmod(
                        created_parent.parent / name,
                        0o711,
                    )
                return real_rmdir(path, *arguments, **keywords)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module.os,
                    "rmdir",
                    side_effect=chmod_at_final_rmdir,
                ):
                    with self.assertRaises(BaseException) as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-output\n"},
                            frozen,
                            post_validate=lambda: (_ for _ in ()).throw(
                                ValueError("force rollback")
                            ),
                        )

            self.assertFalse(injected)
            recovery_paths = getattr(raised.exception, "recovery_paths", ())
            self.assertTrue(recovery_paths)
            self.assertTrue(
                all(path.exists() for path in recovery_paths)
            )

    def test_rollback_failure_retains_recovery_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, second = self.make_root(Path(temp_dir))
            original_exchange = self.transaction_module._atomic_exchange
            exchange_count = 0

            def fail_promotion_and_rollback(parent_fd, staged_name, target_name):
                nonlocal exchange_count
                exchange_count += 1
                if exchange_count == 2:
                    raise OSError("injected promotion failure")
                if exchange_count == 3:
                    raise OSError("injected rollback failure")
                return original_exchange(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=fail_promotion_and_rollback,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {first: b"new-first\n", second: b"new-second\n"},
                            frozen,
                        )

            self.assertIn(first, raised.exception.unresolved_paths)
            self.assertTrue(raised.exception.recovery_paths)
            self.assertTrue(all(path.exists() for path in raised.exception.recovery_paths))

    def test_unresolved_later_exchange_still_rolls_back_earlier_owned_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, second = self.make_root(Path(temp_dir))
            original_exchange = self.transaction_module._atomic_exchange
            exchange_count = 0
            third_party = b"second-third-party\n"

            def race_second_and_fail_exchange_back(parent_fd, staged_name, target_name):
                nonlocal exchange_count
                exchange_count += 1
                if exchange_count == 2:
                    replacement = second.with_name("second-race.tmp")
                    replacement.write_bytes(third_party)
                    os.replace(replacement, second)
                    return original_exchange(parent_fd, staged_name, target_name)
                if exchange_count == 3:
                    raise OSError("injected second exchange-back failure")
                return original_exchange(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=race_second_and_fail_exchange_back,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {first: b"new-first\n", second: b"new-second\n"},
                            frozen,
                        )

            self.assertEqual(first.read_bytes(), b"first-original\n")
            self.assertEqual(second.read_bytes(), b"new-second\n")
            self.assertIn(second, raised.exception.unresolved_paths)
            self.assertNotIn(first, raised.exception.unresolved_paths)
            self.assertTrue(all(path.exists() for path in raised.exception.recovery_paths))

    def test_non_target_dependency_race_rolls_back_owned_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            dependency = first.parent / "data.snbt"
            dependency.write_bytes(b"data-original\n")
            original_exchange = self.transaction_module._atomic_exchange
            raced = False

            def exchange_then_race(parent_fd, staged_name, target_name):
                nonlocal raced
                result = original_exchange(parent_fd, staged_name, target_name)
                if not raced:
                    raced = True
                    dependency.write_bytes(b"data-third-party\n")
                return result

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=exchange_then_race,
                ):
                    with self.assertRaisesRegex(ValueError, "dependency changed"):
                        transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertEqual(first.read_bytes(), b"first-original\n")
            self.assertEqual(dependency.read_bytes(), b"data-third-party\n")

    def test_registry_input_race_rolls_back_owned_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            manifest = root / "mods" / "fixture.pw.toml"
            manifest.parent.mkdir()
            manifest.write_bytes(b'name = "original"\n')
            original_exchange = self.transaction_module._atomic_exchange
            raced = False

            def exchange_then_race(parent_fd, staged_name, target_name):
                nonlocal raced
                result = original_exchange(parent_fd, staged_name, target_name)
                if not raced:
                    raced = True
                    manifest.write_bytes(b'name = "third-party"\n')
                return result

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = transaction.freeze((root / "config", root / "mods"))
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_exchange",
                    side_effect=exchange_then_race,
                ):
                    with self.assertRaisesRegex(ValueError, "dependency changed"):
                        transaction.promote_bytes({first: b"new\n"}, frozen)

            self.assertEqual(first.read_bytes(), b"first-original\n")
            self.assertEqual(manifest.read_bytes(), b'name = "third-party"\n')

    def test_new_file_uses_atomic_no_replace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            target = first.with_name("new.snbt")
            third_party = b"third-party-created\n"
            original_no_replace = self.transaction_module._atomic_no_replace
            raced = False

            def create_then_no_replace(parent_fd, staged_name, target_name):
                nonlocal raced
                if not raced:
                    raced = True
                    target.write_bytes(third_party)
                return original_no_replace(parent_fd, staged_name, target_name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=create_then_no_replace,
                ):
                    with self.assertRaises(FileExistsError):
                        transaction.promote_bytes({target: b"transaction-created\n"}, frozen)
            self.assertEqual(target.read_bytes(), third_party)

    def test_new_file_ownership_loss_retains_recovery_without_clobbering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            target = first.with_name("new.snbt")
            third_party = b"third-party-after-create\n"
            original_no_replace = self.transaction_module._atomic_no_replace

            def promote_then_edit(parent_fd, staged_name, target_name):
                result = original_no_replace(parent_fd, staged_name, target_name)
                target.write_bytes(third_party)
                return result

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_atomic_no_replace",
                    side_effect=promote_then_edit,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes(
                            {target: b"transaction-created\n"},
                            frozen,
                        )

            self.assertEqual(target.read_bytes(), third_party)
            self.assertIn(target, raised.exception.unresolved_paths)
            self.assertEqual(len(raised.exception.recovery_paths), 1)
            self.assertEqual(
                raised.exception.recovery_paths[0].read_bytes(),
                b"transaction-created\n",
            )

    def test_post_validation_failure_restores_transactional_deletion_inode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root, first, _ = self.make_root(Path(temp_dir))
            before = self.inventory(root)
            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)

                def fail_validation() -> None:
                    raise ValueError("injected deletion post-validation failure")

                with self.assertRaisesRegex(ValueError, "post-validation"):
                    transaction.promote_bytes(
                        {},
                        frozen,
                        deletions=(first,),
                        post_validate=fail_validation,
                    )
            self.assertEqual(self.inventory(root), before)


class WholeQuestBuildTransactionTests(unittest.TestCase):
    ORDER_CHAPTERS = (
        "23643435F7BE74AC",
        "7BA8A3335FAC821A",
        "16E0B20162F6DAE5",
        "775CD739E3318A7E",
        "18471B3E458EAB62",
        "0FAB5AA8294D4487",
        "5070DE6E2B300F4B",
        "758F5AEF697F7EFD",
        "7C611E8A94BC5CE5",
        "099200314296766A",
    )
    MANUAL_CHAPTERS = (
        "150C6F996983394C",
        "4DE10FFCDEEF9892",
        "01749E1554DFF98B",
        "4690C88367D47FF3",
        "0A510C4BD2A3818B",
        "67F13F819570ED52",
        "67C126F7B1338CB1",
        "0B7C7859EBD6EFF3",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("afterlight_quests")
        cls.builder = importlib.import_module("afterlight_quests.builder")
        specification = importlib.util.spec_from_file_location(
            "afterlight_build_quests_transaction_test",
            TOOLS / "build-quests.py",
        )
        assert specification is not None
        assert specification.loader is not None
        cls.build_script = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.build_script)

    def setUp(self) -> None:
        self.migration_state = tempfile.TemporaryDirectory()
        self.migration_environment = mock.patch.dict(
            os.environ,
            {"AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT": self.migration_state.name},
        )
        self.migration_environment.start()

    def tearDown(self) -> None:
        self.migration_environment.stop()
        self.migration_state.cleanup()

    def copy_repository_inputs(self, root: Path) -> Path:
        shutil.copytree(ROOT / "config", root / "config")
        shutil.copytree(ROOT / "mods", root / "mods")
        shutil.copytree(
            ROOT / "kubejs" / "startup_scripts",
            root / "kubejs" / "startup_scripts",
        )
        audit_source = (
            ROOT
            / "kubejs"
            / "server_scripts"
            / "afterlight"
            / "generated_quest_item_audit.js"
        )
        audit_target = (
            root
            / "kubejs"
            / "server_scripts"
            / "afterlight"
            / "generated_quest_item_audit.js"
        )
        audit_target.parent.mkdir(parents=True)
        shutil.copy2(audit_source, audit_target)
        mods = root / "server-test" / "mods"
        mods.mkdir(parents=True)
        with zipfile.ZipFile(mods / "fixture.jar", "w"):
            pass
        return root / "config" / "ftbquests" / "quests"

    @staticmethod
    def inventory(root: Path) -> dict[str, tuple[object, ...]]:
        result: dict[str, tuple[object, ...]] = {}
        for path in sorted(root.rglob("*")):
            status = path.lstat()
            if stat.S_ISREG(status.st_mode):
                kind = "file"
                payload = path.read_bytes()
            elif stat.S_ISDIR(status.st_mode):
                kind = "directory"
                payload = None
            elif stat.S_ISLNK(status.st_mode):
                kind = "symlink"
                payload = os.readlink(path)
            else:
                kind = "other"
                payload = None
            result[path.relative_to(root).as_posix()] = (
                kind,
                status.st_dev,
                status.st_ino,
                stat.S_IMODE(status.st_mode),
                status.st_uid,
                status.st_gid,
                status.st_nlink,
                payload,
            )
        return result

    @staticmethod
    def byte_snapshot(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in sorted(root.rglob("*"))
            if path.is_file()
        }

    def test_poisoned_managed_state_fails_without_mutating_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            quest_root = self.copy_repository_inputs(root)
            state_path = quest_root / ".afterlight-managed.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["chapters"].append("4C01977EF77930A6")
            state_path.write_text(
                json.dumps(state, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            before = self.inventory(root)

            with self.assertRaisesRegex(ValueError, "unknown prior managed chapter"):
                self.build_script._build_quests(root, catalog=self.quests.build_catalog())

            self.assertEqual(self.inventory(root), before)
            self.assertTrue(
                (quest_root / "chapters" / "4C01977EF77930A6.snbt").is_file()
            )

    def test_duplicate_and_unknown_managed_state_entries_fail_before_mutation(self) -> None:
        cases = {
            "duplicate managed chapter": lambda state: state["chapters"].append(
                state["chapters"][0]
            ),
            "duplicate managed localization key": lambda state: state[
                "localization_keys"
            ].append(state["localization_keys"][0]),
            "unknown prior managed localization": lambda state: state[
                "localization_keys"
            ].append("quest.1234567890ABCDEF.title"),
        }
        for expected, poison in cases.items():
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "repository"
                quest_root = self.copy_repository_inputs(root)
                state_path = quest_root / ".afterlight-managed.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                poison(state)
                state_path.write_text(
                    json.dumps(state, indent=2, sort_keys=True) + "\n",
                    encoding="utf-8",
                )
                before = self.inventory(root)

                with self.assertRaisesRegex(ValueError, expected):
                    self.build_script._build_quests(
                        root,
                        catalog=self.quests.build_catalog(),
                    )

                self.assertEqual(self.inventory(root), before)

    def test_public_writers_share_lock_and_reject_mismatched_tokens(self) -> None:
        transaction_module = importlib.import_module(
            "afterlight_quests.quest_build_transaction"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = base / "repository"
            quest_root = self.copy_repository_inputs(root)
            other_root = base / "other-repository"
            other_quest_root = self.copy_repository_inputs(other_root)
            before = self.inventory(root)
            other_before = self.inventory(other_root)

            with transaction_module.QuestBuildTransaction(root) as transaction:
                with self.assertRaisesRegex(RuntimeError, "reentrant"):
                    self.quests.write_catalog(
                        self.quests.build_catalog(),
                        quest_root,
                    )
                with self.assertRaisesRegex(RuntimeError, "reentrant"):
                    self.quests.write_legacy_quest_overlays(
                        quest_root,
                        catalog=self.quests.build_catalog(),
                    )
                with self.assertRaisesRegex(ValueError, "mismatched repository root"):
                    self.quests.write_catalog(
                        self.quests.build_catalog(),
                        other_quest_root,
                        transaction=transaction,
                    )
                with self.assertRaisesRegex(ValueError, "mismatched repository root"):
                    self.quests.write_legacy_quest_overlays(
                        other_quest_root,
                        catalog=self.quests.build_catalog(),
                        transaction=transaction,
                    )

            self.assertEqual(self.inventory(root), before)
            self.assertEqual(self.inventory(other_root), other_before)

    def test_public_catalog_writer_propagates_committed_cleanup_warnings(self) -> None:
        transaction_module = importlib.import_module(
            "afterlight_quests.quest_build_transaction"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            quest_root = self.copy_repository_inputs(root)
            catalog = copy.deepcopy(list(self.quests.build_catalog()))
            catalog[0].title += " Warning Probe"
            real_unlink = transaction_module._unlink_artifact
            failed = False

            def fail_once(artifact):
                nonlocal failed
                if not failed:
                    failed = True
                    raise OSError("catalog cleanup warning")
                return real_unlink(artifact)

            with mock.patch.object(
                transaction_module,
                "_unlink_artifact",
                side_effect=fail_once,
            ):
                result = self.quests.write_catalog(catalog, quest_root)

            self.assertTrue(failed)
            self.assertTrue(result.committed)
            self.assertTrue(result.cleanup_warnings)
            self.assertTrue(result.recovery_paths)

    def test_build_orchestration_propagates_committed_cleanup_warnings(self) -> None:
        transaction_module = importlib.import_module(
            "afterlight_quests.quest_build_transaction"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            self.copy_repository_inputs(root)
            real_unlink = transaction_module._unlink_artifact
            failed = False

            def fail_once(artifact):
                nonlocal failed
                if not failed:
                    failed = True
                    raise OSError("build cleanup warning")
                return real_unlink(artifact)

            with mock.patch.object(
                transaction_module,
                "_unlink_artifact",
                side_effect=fail_once,
            ):
                result = self.build_script._build_quests(
                    root,
                    catalog=self.quests.build_catalog(),
                )

            self.assertTrue(failed)
            self.assertTrue(result.committed)
            self.assertTrue(result.cleanup_warnings)
            self.assertTrue(result.recovery_paths)

    def test_full_candidate_build_uses_git_ownership_after_process_restart(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            quest_root = self.copy_repository_inputs(root)
            synthetic_chapter_id = "1234567890ABCDEF"
            managed_state = json.loads(
                (quest_root / ".afterlight-managed.json").read_text(encoding="utf-8")
            )
            managed_state["chapters"].append(synthetic_chapter_id)
            managed_state["chapters"].sort()
            synthetic_key = f"chapter.{synthetic_chapter_id}.title"
            managed_state["localization_keys"].append(synthetic_key)
            managed_state["localization_keys"].sort()
            (quest_root / ".afterlight-managed.json").write_text(
                json.dumps(managed_state, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            removed_chapter = quest_root / "chapters" / f"{synthetic_chapter_id}.snbt"
            removed_chapter.write_text(
                "{\n"
                f'\tfilename: "{synthetic_chapter_id}"\n'
                '\tgroup: "4A20F33642175B95"\n'
                f'\tid: "{synthetic_chapter_id}"\n'
                "\torder_index: 99\n"
                "\tquest_links: [ ]\n"
                "\tquests: [ ]\n"
                "}\n",
                encoding="utf-8",
            )
            language_path = quest_root / "lang" / "en_us.snbt"
            language = language_path.read_text(encoding="utf-8")
            language_path.write_text(
                language.rstrip()[:-1]
                + f'\n\t{synthetic_key}: "Synthetic Managed Chapter"\n'
                + "}\n",
                encoding="utf-8",
            )
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.name", "Afterlight Test"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "afterlight-test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "fixture"],
                cwd=root,
                check=True,
            )
            chapter_relative = removed_chapter.relative_to(root).as_posix()
            tracked_chapter = subprocess.run(
                ["git", "show", f"HEAD:{chapter_relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
            tracked_language = subprocess.run(
                ["git", "show", f"HEAD:{language_path.relative_to(root).as_posix()}"],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertEqual(tracked_chapter, removed_chapter.read_bytes())
            self.assertIn(
                f'\t{synthetic_key}: "Synthetic Managed Chapter"\n',
                tracked_language,
            )
            environment = dict(os.environ)
            environment["PYTHONPATH"] = os.fspath(TOOLS)
            build_script_path = TOOLS / "build-quests.py"
            code = (
                "import importlib.util, pathlib, sys; "
                "spec=importlib.util.spec_from_file_location('build_quests_restart', sys.argv[1]); "
                "module=importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(module); "
                "result=module._build_quests(pathlib.Path(sys.argv[2])); "
                "raise SystemExit(2 if result.cleanup_warnings else 0)"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code,
                    os.fspath(build_script_path),
                    os.fspath(root),
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(removed_chapter.exists())
            self.assertNotIn(
                synthetic_key,
                language_path.read_text(encoding="utf-8"),
            )

    def test_full_candidate_build_rejects_working_tree_ownership_poison(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            quest_root = self.copy_repository_inputs(root)
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            subprocess.run(
                ["git", "config", "user.name", "Afterlight Test"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "afterlight-test@example.invalid"],
                cwd=root,
                check=True,
            )
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "-q", "-m", "trusted fixture"],
                cwd=root,
                check=True,
            )
            poisoned_chapter_id = "4C01977EF77930A6"
            poisoned_key = f"chapter.{poisoned_chapter_id}.title"
            state_path = quest_root / ".afterlight-managed.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["chapters"].append(poisoned_chapter_id)
            state["chapters"].sort()
            state["localization_keys"].append(poisoned_key)
            state["localization_keys"].sort()
            state_path.write_text(
                json.dumps(state, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            before = self.inventory(root)
            environment = dict(os.environ)
            environment["PYTHONPATH"] = os.fspath(TOOLS)
            build_script_path = TOOLS / "build-quests.py"
            code = (
                "import importlib.util, pathlib, sys; "
                "spec=importlib.util.spec_from_file_location('build_quests_poison', sys.argv[1]); "
                "module=importlib.util.module_from_spec(spec); "
                "spec.loader.exec_module(module); "
                "module._build_quests(pathlib.Path(sys.argv[2]))"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    code,
                    os.fspath(build_script_path),
                    os.fspath(root),
                ],
                cwd=root,
                env=environment,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0, result.stderr)
            self.assertIn("unknown prior managed chapter", result.stderr)
            self.assertEqual(self.inventory(root), before)
            self.assertTrue(
                (
                    quest_root
                    / "chapters"
                    / f"{poisoned_chapter_id}.snbt"
                ).is_file()
            )
            self.assertIn(
                poisoned_key,
                (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8"),
            )

    def test_candidate_stage_failures_leave_real_inventory_unchanged(self) -> None:
        cases = {
            "normalization": (
                self.builder,
                "normalize_quest_corpus_ids",
                ValueError("injected normalization failure"),
            ),
            "overlay": (
                self.build_script,
                "write_legacy_quest_overlays",
                ValueError("injected overlay failure"),
            ),
            "audit": (
                self.builder,
                "_render_quest_item_audit",
                ValueError("injected audit failure"),
            ),
        }
        for label, (owner, attribute, error) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "repository"
                self.copy_repository_inputs(root)
                before = self.inventory(root)
                with mock.patch.object(owner, attribute, side_effect=error):
                    with self.assertRaisesRegex(ValueError, f"injected {label} failure"):
                        self.build_script._build_quests(
                            root,
                            catalog=self.quests.build_catalog(),
                        )
                self.assertEqual(self.inventory(root), before)

    def test_candidate_and_post_promotion_validation_failures_restore_inventory(self) -> None:
        for label, side_effect in (
            ("candidate", [["candidate validation failure"]]),
            ("post", [[], ["post validation failure"]]),
        ):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir) / "repository"
                self.copy_repository_inputs(root)
                before = self.inventory(root)
                with mock.patch.object(
                    self.build_script,
                    "validate_quests",
                    side_effect=side_effect,
                ):
                    with self.assertRaisesRegex(ValueError, "validation failed"):
                        self.build_script._build_quests(
                            root,
                            catalog=self.quests.build_catalog(),
                        )
                self.assertEqual(self.inventory(root), before)

    def test_build_order_complete_diff_and_second_success_are_idempotent(self) -> None:
        transaction_module = importlib.import_module(
            "afterlight_quests.quest_build_transaction"
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "repository"
            self.copy_repository_inputs(root)
            sentinel = root / "unrelated.bin"
            sentinel.write_bytes(b"unrelated\0sentinel")
            before = self.byte_snapshot(root)
            events: list[str] = []
            real_write_catalog = self.build_script.write_catalog
            real_overlays = self.build_script.write_legacy_quest_overlays
            real_validate = self.build_script.validate_quests
            real_promote = transaction_module.QuestBuildTransaction.promote_bytes

            def write_catalog(*arguments, **keywords):
                events.append("catalog")
                return real_write_catalog(*arguments, **keywords)

            def overlays(*arguments, **keywords):
                events.append("overlays")
                return real_overlays(*arguments, **keywords)

            def validate(*arguments, **keywords):
                events.append("validate")
                return real_validate(*arguments, **keywords)

            def promote(transaction, *arguments, **keywords):
                events.append("promote")
                return real_promote(transaction, *arguments, **keywords)

            with mock.patch.object(
                self.build_script,
                "write_catalog",
                side_effect=write_catalog,
            ), mock.patch.object(
                self.build_script,
                "write_legacy_quest_overlays",
                side_effect=overlays,
            ), mock.patch.object(
                self.build_script,
                "validate_quests",
                side_effect=validate,
            ), mock.patch.object(
                transaction_module.QuestBuildTransaction,
                "promote_bytes",
                new=promote,
            ):
                self.build_script._build_quests(
                    root,
                    catalog=self.quests.build_catalog(),
                )

            self.assertEqual(
                events,
                ["catalog", "overlays", "validate", "promote", "validate"],
            )
            first = self.byte_snapshot(root)
            changed = sorted(
                path
                for path in set(before) | set(first)
                if before.get(path) != first.get(path)
            )
            self.assertEqual(
                changed,
                sorted(
                    [
                        "config/ftbquests/quests/.afterlight-managed.json",
                        *(
                            f"config/ftbquests/quests/chapters/{chapter_id}.snbt"
                            for chapter_id in self.ORDER_CHAPTERS
                        ),
                        *(
                            f"config/ftbquests/quests/chapters/{chapter_id}.snbt"
                            for chapter_id in self.MANUAL_CHAPTERS
                        ),
                        "config/ftbquests/quests/chapters/11CA083771CCB5BE.snbt",
                        "config/ftbquests/quests/chapters/5B93C6934B230CFB.snbt",
                        "config/ftbquests/quests/lang/en_us.snbt",
                        "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
                    ]
                ),
            )
            first_inventory = self.inventory(root)
            self.build_script._build_quests(root, catalog=self.quests.build_catalog())
            self.assertEqual(self.byte_snapshot(root), first)
            self.assertEqual(self.inventory(root), first_inventory)
            self.assertEqual(sentinel.read_bytes(), b"unrelated\0sentinel")


if __name__ == "__main__":
    unittest.main()
