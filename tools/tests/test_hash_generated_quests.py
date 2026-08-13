from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "hash-generated-quests.py"


def load_module():
    spec = importlib.util.spec_from_file_location("hash_generated_quests", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load generated quest hash tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GeneratedQuestHashTests(unittest.TestCase):
    @staticmethod
    def write_fixture(root: Path) -> dict[str, bytes]:
        files = {
            "config/ftbquests/quests/.afterlight-managed.json": b"{}\n",
            "config/ftbquests/quests/chapter_groups.snbt": b"{chapter_groups:[]}\n",
            "config/ftbquests/quests/data.snbt": b"{version:13}\n",
            "config/ftbquests/quests/chapters/0000000000000001.snbt": b"{id:\"0000000000000001\"}\n",
            "config/ftbquests/quests/lang/en_us.snbt": b"{}\n",
            "config/ftbquests/quests/reward_tables/reward.snbt": b"{id:\"reward\"}\n",
            "kubejs/server_scripts/afterlight/generated_quest_item_audit.js": b"item\n",
            "kubejs/server_scripts/afterlight/generated_manual_acquisition_audit.js": b"manual\n",
        }
        for relative, payload in files.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
        os.chmod(
            root
            / "config/ftbquests/quests/chapters/0000000000000001.snbt",
            0o640,
        )
        (root / ".gitignore").write_text(
            "config/ftbquests/quests/.afterlight-managed.json\n",
            encoding="utf-8",
        )
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Fixture"], cwd=root, check=True
        )
        subprocess.run(
            ["git", "config", "user.email", "fixture@example.invalid"],
            cwd=root,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "fixture"], cwd=root, check=True
        )
        return files

    def test_inventory_covers_complete_filesystem_and_exact_metadata(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            files = self.write_fixture(root)
            output = Path(temporary_directory) / "inventory"

            manifest_path = module.write_inventory(root, output)
            payload = json.loads(manifest_path.read_text(encoding="utf-8"))

            self.assertEqual(payload["schema_version"], 1)
            self.assertEqual(
                [entry["path"] for entry in payload["files"]],
                sorted(files),
            )
            by_path = {entry["path"]: entry for entry in payload["files"]}
            for relative, content in files.items():
                self.assertEqual(by_path[relative]["size"], len(content))
                self.assertEqual(
                    by_path[relative]["sha256"], hashlib.sha256(content).hexdigest()
                )
                copied = output / relative
                self.assertEqual(copied.read_bytes(), content)
                self.assertEqual(
                    stat.S_IMODE(copied.stat().st_mode),
                    stat.S_IMODE((root / relative).stat().st_mode),
                )
            self.assertEqual(
                by_path[
                    "config/ftbquests/quests/.afterlight-managed.json"
                ]["git_state"],
                "ignored",
            )
            self.assertTrue(
                all(
                    entry["git_state"] == "tracked"
                    for entry in payload["files"]
                    if entry["path"]
                    != "config/ftbquests/quests/.afterlight-managed.json"
                )
            )
            self.assertEqual(
                by_path[
                    "config/ftbquests/quests/chapters/0000000000000001.snbt"
                ]["mode"],
                "0640",
            )
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o700)
            self.assertEqual(
                manifest_path.read_text(encoding="utf-8"),
                json.dumps(
                    payload,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    sort_keys=True,
                )
                + "\n",
            )

    def test_untracked_quest_file_changes_inventory(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            first = Path(temporary_directory) / "first"
            second = Path(temporary_directory) / "second"
            module.write_inventory(root, first)
            extra = root / "config/ftbquests/quests/chapters/0000000000000002.snbt"
            extra.write_text('{id:"0000000000000002"}\n', encoding="utf-8")
            module.write_inventory(root, second)
            second_payload = json.loads(
                (second / module.INVENTORY_NAME).read_text(encoding="utf-8")
            )
            extra_record = next(
                entry
                for entry in second_payload["files"]
                if entry["path"].endswith("0000000000000002.snbt")
            )
            self.assertEqual(extra_record["git_state"], "untracked")
            self.assertEqual((second / extra_record["path"]).read_bytes(), extra.read_bytes())
            self.assertNotEqual(
                (first / module.INVENTORY_NAME).read_bytes(),
                (second / module.INVENTORY_NAME).read_bytes(),
            )

    def test_missing_or_extra_generated_audit_fails_closed(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            audit_root = root / "kubejs/server_scripts/afterlight"

            (audit_root / "generated_manual_acquisition_audit.js").unlink()
            with self.assertRaisesRegex(ValueError, "generated audit inventory"):
                module.collect_inventory(root)

            (audit_root / "generated_manual_acquisition_audit.js").write_text(
                "manual\n", encoding="utf-8"
            )
            (audit_root / "generated_unexpected_audit.js").write_text(
                "unexpected\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "generated audit inventory"):
                module.collect_inventory(root)

    def test_missing_required_quest_output_fails_closed(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            (root / "config/ftbquests/quests/data.snbt").unlink()
            with self.assertRaisesRegex(ValueError, "required quest output"):
                module.collect_inventory(root)

    def test_links_nonregular_files_and_existing_output_are_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            target = root / "outside.snbt"
            target.write_text("outside\n", encoding="utf-8")
            link = root / "config/ftbquests/quests/chapters/link.snbt"
            link.symlink_to(target)
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                module.collect_inventory(root)

            link.unlink()
            output = Path(temporary_directory) / "inventory"
            output.mkdir()
            with self.assertRaisesRegex(FileExistsError, "already exists"):
                module.write_inventory(root, output)

    def test_root_and_output_must_not_overlap(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            with self.assertRaisesRegex(ValueError, "outside the pack root"):
                module.write_inventory(root, root / "inventory")

    def test_symlinked_output_parent_is_rejected(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            root = base / "pack"
            root.mkdir()
            self.write_fixture(root)
            real_parent = base / "real-parent"
            real_parent.mkdir()
            linked_parent = base / "linked-parent"
            linked_parent.symlink_to(real_parent, target_is_directory=True)

            with self.assertRaisesRegex(ValueError, "symbolic-link component"):
                module.write_inventory(root, linked_parent / "inventory")

            self.assertFalse((real_parent / "inventory").exists())

    def test_repeatable_snapshots_are_byte_and_mode_identical(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            base = Path(temporary_directory)
            root = base / "pack"
            root.mkdir()
            self.write_fixture(root)
            first = base / "first"
            second = base / "second"

            module.write_inventory(root, first)
            module.write_inventory(root, second)

            first_paths = sorted(
                path.relative_to(first)
                for path in first.rglob("*")
                if path.is_file()
            )
            second_paths = sorted(
                path.relative_to(second)
                for path in second.rglob("*")
                if path.is_file()
            )
            self.assertEqual(first_paths, second_paths)
            for relative in first_paths:
                self.assertEqual(
                    (first / relative).read_bytes(),
                    (second / relative).read_bytes(),
                )
                self.assertEqual(
                    stat.S_IMODE((first / relative).stat().st_mode),
                    stat.S_IMODE((second / relative).stat().st_mode),
                )

    def test_source_mutation_aborts_without_publishing_snapshot(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            source = root / "config/ftbquests/quests/chapter_groups.snbt"
            output = Path(temporary_directory) / "inventory"
            original_read = module.os.read
            changed = False
            source_inode = source.stat().st_ino

            def mutating_read(descriptor: int, count: int) -> bytes:
                nonlocal changed
                payload = original_read(descriptor, count)
                if (
                    payload
                    and not changed
                    and os.fstat(descriptor).st_ino == source_inode
                ):
                    source.write_bytes(source.read_bytes() + b"changed\n")
                    changed = True
                return payload

            with mock.patch.object(module.os, "read", side_effect=mutating_read):
                with self.assertRaisesRegex(ValueError, "changed while copying"):
                    module.write_inventory(root, output)
            self.assertFalse(output.exists())
            self.assertEqual(
                list(output.parent.glob(f".{output.name}.staging.*")),
                [],
            )

    def test_source_path_replacement_aborts_without_publishing_snapshot(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "pack"
            root.mkdir()
            self.write_fixture(root)
            source = root / "config/ftbquests/quests/chapter_groups.snbt"
            output = Path(temporary_directory) / "inventory"
            original_read = module.os.read
            replaced = False
            source_inode = source.stat().st_ino

            def replacing_read(descriptor: int, count: int) -> bytes:
                nonlocal replaced
                payload = original_read(descriptor, count)
                if (
                    payload
                    and not replaced
                    and os.fstat(descriptor).st_ino == source_inode
                ):
                    replacement = source.with_name("replacement.snbt")
                    replacement.write_bytes(source.read_bytes())
                    os.replace(replacement, source)
                    replaced = True
                return payload

            with mock.patch.object(module.os, "read", side_effect=replacing_read):
                with self.assertRaisesRegex(ValueError, "changed while copying"):
                    module.write_inventory(root, output)
            self.assertFalse(output.exists())
            self.assertEqual(
                list(output.parent.glob(f".{output.name}.staging.*")),
                [],
            )


if __name__ == "__main__":
    unittest.main()
