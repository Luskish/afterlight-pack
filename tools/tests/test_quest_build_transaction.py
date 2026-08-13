from __future__ import annotations

import os
import importlib
import importlib.util
import json
import shutil
import stat
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
            kind = "file" if stat.S_ISREG(status.st_mode) else "directory"
            payload = path.read_bytes() if kind == "file" else None
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

            def fail_once(parent_fd, name):
                nonlocal failed
                if not failed:
                    failed = True
                    raise OSError("injected cleanup failure")
                return original_unlink(parent_fd, name)

            with self.transaction_module.QuestBuildTransaction(root) as transaction:
                frozen = self.freeze(transaction, root)
                with mock.patch.object(
                    self.transaction_module,
                    "_unlink_artifact",
                    side_effect=fail_once,
                ):
                    with self.assertRaises(
                        self.transaction_module.QuestBuildRollbackError
                    ) as raised:
                        transaction.promote_bytes({first: b"new\n"}, frozen)
            self.assertTrue(failed)
            self.assertEqual(first.read_bytes(), b"new\n")
            self.assertTrue(raised.exception.cleanup_errors)
            self.assertEqual(len(raised.exception.recovery_paths), 1)
            self.assertEqual(
                raised.exception.recovery_paths[0].read_bytes(),
                before["config/ftbquests/quests/first.snbt"][-1],
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
                        *(
                            f"config/ftbquests/quests/chapters/{chapter_id}.snbt"
                            for chapter_id in self.ORDER_CHAPTERS
                        ),
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
