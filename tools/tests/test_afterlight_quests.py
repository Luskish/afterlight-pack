from __future__ import annotations

import hashlib
import importlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


class QuestCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.quests = importlib.import_module("afterlight_quests")
        except ModuleNotFoundError as error:
            raise AssertionError("afterlight_quests package must exist") from error

    def make_catalog(self, item_id: str = "example:widget", dependency: str = ""):
        group = self.quests.GroupSpec(
            slug="story",
            title="The Story",
            id="4525BB3160467FCB",
        )
        dependencies = (dependency,) if dependency else ()
        task = self.quests.TaskSpec(
            slug="story/test/widget-task",
            task_type="item",
            data={
                "item": {"count": 1, "id": item_id},
                "count": self.quests.SnbtLong(1),
                "consume_items": False,
            },
        )
        reward = self.quests.RewardSpec(
            slug="story/test/widget-reward",
            reward_type="xp",
            data={"xp": 50},
        )
        quest = self.quests.QuestSpec(
            slug="story/test/widget",
            title="Build a Widget",
            subtitle="A deterministic fixture.",
            description=("Build one widget.",),
            x=0.0,
            y=0.0,
            dependencies=dependencies,
            tasks=(task,),
            rewards=(reward,),
        )
        chapter = self.quests.ChapterSpec(
            slug="story/test",
            title="Test Chapter",
            group=group,
            icon=item_id,
            order_index=99,
            quests=(quest,),
        )
        return [chapter]

    def make_quest_root(self, base: Path) -> Path:
        quest_root = base / "config" / "ftbquests" / "quests"
        (quest_root / "chapters").mkdir(parents=True)
        (quest_root / "lang").mkdir()
        (quest_root / "chapter_groups.snbt").write_text(
            '{\n\tchapter_groups: [\n\t\t{ id: "4525BB3160467FCB" }\n\t]\n}\n',
            encoding="utf-8",
        )
        (quest_root / "lang" / "en_us.snbt").write_text(
            '{\n\tchapter_group.4525BB3160467FCB.title: "The Story"\n'
            '\tquest.AAAAAAAAAAAAAAAA.title: "Unmanaged"\n}\n',
            encoding="utf-8",
        )
        return quest_root

    def make_mod_jar(self, mods_dir: Path, item_id: str = "example:widget") -> None:
        namespace, path = item_id.split(":", 1)
        mods_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(mods_dir / "example.jar", "w") as jar:
            jar.writestr(f"assets/{namespace}/models/item/{path}.json", "{}")

    def write_runtime_nonce(self, base: Path, nonce: str = "test-boot-nonce") -> str:
        nonce_path = base / "server-test" / "afterlight-audit-nonce.txt"
        nonce_path.parent.mkdir(parents=True, exist_ok=True)
        nonce_path.write_text(f"{nonce}\n", encoding="utf-8")
        return nonce

    def audit_item_count(self, item_id: str = "example:widget") -> int:
        return len(self.quests.KUBEJS_ITEM_ALLOWLIST | {item_id})

    def test_stable_id_uses_truncated_uppercase_sha256(self) -> None:
        expected = hashlib.sha256(b"quest:story/test/widget").hexdigest()[:16].upper()
        self.assertEqual(
            self.quests.stable_id("quest", "story/test/widget"),
            expected,
        )

    def test_act_two_catalog_has_exact_shape_and_dependency_chain(self) -> None:
        catalog = self.quests.build_catalog()
        expected_quests = [
            [
                "Certus Resonance", "Charged Matter", "Fluix", "Lost Presses",
                "Processor Line", "Controller", "Cell Bank", "Crafting Terminal",
                "External Storage", "First Autocraft",
            ],
            [
                "Brass Standard", "Precision Mechanism", "Deployer", "Filtered Belts",
                "Mechanical Arm", "Portable Interface", "Rail Stock",
                "Station and Schedule", "256-Track Capstone",
            ],
            [
                "Air Compressor", "Pressure Chamber", "Compressed Iron", "Plastic",
                "Etching Acid", "Printed Circuit", "Programmer", "Logistics Drone",
                "64-Circuit Capstone",
            ],
            [
                "Energizing Orb", "Reliable Generation", "Reactor Core", "Energy Cell",
                "Capacitor Bank", "Conduit Backbone", "Flux Plug",
                "Flux Point and Controller", "10M FE Reserve",
            ],
            [
                "Oxygen Separation", "Purification", "Crushing", "Chemical Injection",
                "Factory Upgrade", "Digital Miner", "Sulfur Chain", "Fissile Fuel",
                "1,024-Ingot Quota", "Reactor Warning",
            ],
            [
                "AE Stockkeeping", "Create Feed Line", "Drone Delivery", "IE Assembly",
                "Conduit Routing", "Laser Extraction", "Automated Processor Batch",
                "Automated Steel Batch", "Stable Power Proof", "Signal Triangulated",
            ],
        ]

        self.assertEqual([chapter.title for chapter in catalog], [
            "The Lattice",
            "Lines of Motion",
            "Pressure Language",
            "The Grid",
            "Thresholds",
            "Convergence",
        ])
        self.assertEqual([len(chapter.quests) for chapter in catalog], [10, 9, 9, 9, 10, 10])
        self.assertEqual(
            [[quest.title for quest in chapter.quests] for chapter in catalog],
            expected_quests,
        )
        self.assertEqual(sum(len(chapter.quests) for chapter in catalog), 57)
        self.assertTrue(
            all(chapter.group.resolved_id == "4525BB3160467FCB" for chapter in catalog)
        )
        self.assertEqual([chapter.order_index for chapter in catalog], [5, 6, 7, 8, 9, 10])
        self.assertEqual(catalog[0].quests[0].dependency_ids, ("DA407B47132C07C6",))
        for previous, current in zip(catalog, catalog[1:]):
            self.assertEqual(
                current.quests[0].dependency_ids,
                (previous.quests[-1].id,),
            )

    def test_act_two_finales_have_memory_cache_chits_and_xp(self) -> None:
        catalog = self.quests.build_catalog()

        for fragment, chapter in enumerate(catalog, start=5):
            finale = chapter.quests[-1]
            reward_types = [reward.reward_type for reward in finale.rewards]
            self.assertIn(f"MEMORY FRAGMENT {fragment:02d} RESTORED", "\n".join(finale.description))
            self.assertEqual(reward_types.count("loot"), 1)
            self.assertEqual(reward_types.count("xp"), 1)
            self.assertTrue(
                any(
                    reward.reward_type == "item"
                    and reward.data.get("item", {}).get("id") == "kubejs:requisition_chit"
                    for reward in finale.rewards
                )
            )

        key_rewards = [
            reward
            for chapter in catalog
            for quest in chapter.quests
            for reward in quest.rewards
            if reward.reward_type == "item"
            and reward.data.get("item", {}).get("id") == "kubejs:deep_vault_key"
        ]
        self.assertEqual(len(key_rewards), 1)
        self.assertIn(key_rewards[0], catalog[-1].quests[-1].rewards)
        self.assertFalse(
            any(
                "schematic" in str(reward.data)
                for chapter in catalog
                for quest in chapter.quests
                for reward in quest.rewards
            )
        )

    def test_act_two_uses_proven_energy_and_conduit_task_shapes(self) -> None:
        catalog = self.quests.build_catalog()
        quests = {
            quest.title: quest
            for chapter in catalog
            for quest in chapter.quests
        }

        reserve = quests["10M FE Reserve"].tasks[0]
        stable = quests["Stable Power Proof"].tasks[0]
        self.assertEqual(reserve.task_type, "forge_energy")
        self.assertEqual(reserve.data, {
            "value": self.quests.SnbtLong(10_000_000),
            "max_input": self.quests.SnbtLong(250_000),
        })
        self.assertEqual(stable.task_type, "forge_energy")
        self.assertEqual(stable.data, {
            "value": self.quests.SnbtLong(50_000_000),
            "max_input": self.quests.SnbtLong(500_000),
        })

        rendered = "\n".join(self.quests.render_chapter(chapter) for chapter in catalog)
        self.assertIn('"enderio:conduit": "enderio:energy"', rendered)
        self.assertIn('"enderio:conduit": "enderio:item"', rendered)
        self.assertEqual(rendered.count('match_components: "fuzzy"'), 2)

    def test_catalog_collision_detection_rejects_reused_id(self) -> None:
        catalog = self.make_catalog()
        duplicate = self.quests.QuestSpec(
            slug=catalog[0].quests[0].slug,
            title="Duplicate",
            description=("Duplicate identifier.",),
            x=1.0,
            y=0.0,
        )
        catalog[0].quests += (duplicate,)

        with self.assertRaisesRegex(ValueError, "collision"):
            self.quests.assert_no_id_collisions(catalog)

    def test_writer_preserves_unmanaged_files_and_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = self.make_quest_root(Path(temp_dir))
            unmanaged = quest_root / "chapters" / "AAAAAAAAAAAAAAAA.snbt"
            unmanaged.write_text("unmanaged\n", encoding="utf-8")
            catalog = self.make_catalog()

            written = self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            first_chapter = chapter_path.read_text(encoding="utf-8")
            first_language = (quest_root / "lang" / "en_us.snbt").read_text(
                encoding="utf-8"
            )

            self.assertEqual(written, [chapter_path])
            self.assertEqual(unmanaged.read_text(encoding="utf-8"), "unmanaged\n")
            self.assertIn("quest.AAAAAAAAAAAAAAAA.title", first_language)
            self.assertIn(f"chapter.{catalog[0].id}.title", first_language)

            self.quests.write_catalog(catalog, quest_root)
            self.assertEqual(chapter_path.read_text(encoding="utf-8"), first_chapter)
            self.assertEqual(
                (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8"),
                first_language,
            )
            self.assertEqual(list(quest_root.rglob("*.tmp")), [])

    def test_writer_removes_only_stale_compiler_managed_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = self.make_quest_root(Path(temp_dir))
            unmanaged = quest_root / "chapters" / "AAAAAAAAAAAAAAAA.snbt"
            unmanaged.write_text("unmanaged\n", encoding="utf-8")
            catalog = self.make_catalog()
            managed_chapter = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            managed_key = f"chapter.{catalog[0].id}.title"

            self.quests.write_catalog(catalog, quest_root)
            self.assertTrue(managed_chapter.exists())
            self.assertIn(
                managed_key,
                (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8"),
            )

            self.quests.write_catalog([], quest_root)

            self.assertFalse(managed_chapter.exists())
            self.assertNotIn(
                managed_key,
                (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8"),
            )
            self.assertEqual(unmanaged.read_text(encoding="utf-8"), "unmanaged\n")

    def test_validator_accepts_valid_generated_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            self.quests.write_catalog(self.make_catalog(), quest_root)

            self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])

    def test_validator_rejects_runtime_failed_item_audit(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            runtime_log = base / "debug.log"
            self.make_mod_jar(mods_dir)
            self.quests.write_catalog(self.make_catalog(), quest_root)
            nonce = self.write_runtime_nonce(base)
            digest = self.quests.quest_item_audit_digest(quest_root)
            runtime_log.write_text(
                f"[AFTERLIGHT QUEST ITEM AUDIT] INVALID example:widget\n"
                f"[AFTERLIGHT QUEST ITEM AUDIT] FAILED {digest} {nonce}\n",
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(
                quest_root,
                mods_dir,
                runtime_logs=(runtime_log,),
                require_runtime_audit=True,
            )
            self.assertTrue(any("runtime item audit failed" in error for error in errors))

    def test_runtime_item_audit_requires_a_fresh_matching_digest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            runtime_log = base / "server.log"
            self.make_mod_jar(mods_dir)
            self.quests.write_catalog(self.make_catalog(), quest_root)
            nonce = self.write_runtime_nonce(base)

            missing_errors = self.quests.validate_quests(
                quest_root,
                mods_dir,
                runtime_logs=(runtime_log,),
                require_runtime_audit=True,
            )
            self.assertTrue(
                any("runtime item audit missing or stale" in error for error in missing_errors)
            )

            digest = self.quests.quest_item_audit_digest(quest_root)
            runtime_log.write_text(
                f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} "
                f"{self.audit_item_count()} {nonce}\n",
                encoding="utf-8",
            )
            self.assertEqual(
                self.quests.validate_quests(
                    quest_root,
                    mods_dir,
                    runtime_logs=(runtime_log,),
                    require_runtime_audit=True,
                ),
                [],
            )

    def test_runtime_item_audit_rejects_log_older_than_generated_script(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            runtime_log = base / "server.log"
            self.make_mod_jar(mods_dir)
            self.quests.write_catalog(self.make_catalog(), quest_root)
            nonce = self.write_runtime_nonce(base)
            digest = self.quests.quest_item_audit_digest(quest_root)
            runtime_log.write_text(
                f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} "
                f"{self.audit_item_count()} {nonce}\n",
                encoding="utf-8",
            )
            audit_script = (
                base
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "generated_quest_item_audit.js"
            )
            stale_time = audit_script.stat().st_mtime - 1
            os.utime(runtime_log, (stale_time, stale_time))

            errors = self.quests.validate_quests(
                quest_root,
                mods_dir,
                runtime_logs=(runtime_log,),
                require_runtime_audit=True,
            )
            self.assertTrue(any("runtime item audit missing or stale" in error for error in errors))

    def test_item_audit_digest_changes_with_registry_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            manifest_dir = base / "mods"
            manifest_dir.mkdir()
            manifest = manifest_dir / "example.pw.toml"
            manifest.write_text('name = "One"\n', encoding="utf-8")
            startup_script = base / "kubejs" / "startup_scripts" / "registry.js"
            startup_script.parent.mkdir(parents=True)
            startup_script.write_text("// one\n", encoding="utf-8")
            config = base / "config" / "registry-options.toml"
            config.write_text("enabled = true\n", encoding="utf-8")
            self.quests.write_catalog(self.make_catalog(), quest_root)
            first = self.quests.quest_item_audit_digest(quest_root)

            manifest.write_text('name = "Two"\n', encoding="utf-8")
            second = self.quests.quest_item_audit_digest(quest_root)
            startup_script.write_text("// two\n", encoding="utf-8")
            third = self.quests.quest_item_audit_digest(quest_root)
            config.write_text("enabled = false\n", encoding="utf-8")
            fourth = self.quests.quest_item_audit_digest(quest_root)

            self.assertNotEqual(first, second)
            self.assertNotEqual(second, third)
            self.assertNotEqual(third, fourth)

    def test_runtime_item_audit_includes_allowlisted_kubejs_items_without_quests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)

            self.quests.write_catalog([], quest_root)

            audit_script = (
                base
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "generated_quest_item_audit.js"
            ).read_text(encoding="utf-8")
            for item_id in self.quests.KUBEJS_ITEM_ALLOWLIST:
                self.assertIn(f'  "{item_id}"', audit_script)

    def test_runtime_item_audit_rejects_nonce_from_prior_boot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            runtime_log = base / "server.log"
            self.make_mod_jar(mods_dir)
            self.quests.write_catalog(self.make_catalog(), quest_root)
            self.write_runtime_nonce(base, "current-boot")
            digest = self.quests.quest_item_audit_digest(quest_root)
            runtime_log.write_text(
                f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} "
                f"{self.audit_item_count()} prior-boot\n",
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(
                quest_root,
                mods_dir,
                runtime_logs=(runtime_log,),
                require_runtime_audit=True,
            )
            self.assertTrue(any("runtime item audit missing or stale" in error for error in errors))

    def test_static_validator_allows_items_without_asset_namespaces(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            mods_dir.mkdir()
            with zipfile.ZipFile(mods_dir / "dynamic.jar", "w") as jar:
                jar.writestr("META-INF/neoforge.mods.toml", 'modId="dynamic"')
            self.quests.write_catalog(self.make_catalog("dynamic:widget"), quest_root)

            self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])

    def test_count_quests_reports_actual_corpus_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = self.make_quest_root(Path(temp_dir))
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)

            self.assertEqual(
                self.quests.count_quests(quest_root),
                self.quests.QuestCounts(chapters=1, quests=1, tasks=1, rewards=1),
            )

    def test_validator_reports_every_required_failure_class(self) -> None:
        cases = {
            "malformed IDs": lambda text, chapter, quest: text.replace(
                f'id: "{quest.tasks[0].id}"', 'id: "NOT_HEX"', 1
            ),
            "duplicate ID": lambda text, chapter, quest: text.replace(
                f'id: "{quest.tasks[0].id}"', f'id: "{quest.id}"', 1
            ),
            "unresolved dependency": lambda text, chapter, quest: text.replace(
                f'id: "{quest.id}"',
                f'id: "{quest.id}"\n\t\t\tdependencies: ["FFFFFFFFFFFFFFFF"]',
                1,
            ),
            "em dash": lambda text, chapter, quest: text.replace(
                'filename:', 'note: "forbidden \u2014 punctuation"\n\tfilename:', 1
            ),
            "filename/id mismatch": lambda text, chapter, quest: text.replace(
                f'filename: "{chapter.id}"', 'filename: "AAAAAAAAAAAAAAAA"', 1
            ),
            "malformed item ID": lambda text, chapter, quest: text.replace(
                "example:widget", "Example:missing"
            ),
        }

        for expected, mutate in cases.items():
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as temp_dir:
                base = Path(temp_dir)
                quest_root = self.make_quest_root(base)
                mods_dir = base / "mods"
                self.make_mod_jar(mods_dir)
                catalog = self.make_catalog()
                self.quests.write_catalog(catalog, quest_root)
                chapter = catalog[0]
                quest = chapter.quests[0]
                chapter_path = quest_root / "chapters" / f"{chapter.id}.snbt"
                chapter_path.write_text(
                    mutate(chapter_path.read_text(encoding="utf-8"), chapter, quest),
                    encoding="utf-8",
                )

                errors = self.quests.validate_quests(quest_root, mods_dir)
                self.assertTrue(
                    any(expected in error for error in errors),
                    f"{expected!r} not found in {errors!r}",
                )

    def test_validator_rejects_resource_shaped_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            task_id = catalog[0].quests[0].tasks[0].id
            chapter_path.write_text(
                chapter_path.read_text(encoding="utf-8").replace(
                    f'id: "{task_id}"', 'id: "minecraft:diamond"', 1
                ),
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(any("malformed IDs" in error for error in errors), errors)

    def test_validator_rejects_non_string_ftb_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            task_id = catalog[0].quests[0].tasks[0].id
            chapter_path.write_text(
                chapter_path.read_text(encoding="utf-8").replace(
                    f'id: "{task_id}"', "id: true", 1
                ),
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(any("malformed IDs" in error for error in errors), errors)

    def test_validator_rejects_unbalanced_snbt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            chapter_path.write_text(
                chapter_path.read_text(encoding="utf-8").rstrip()[:-1] + "\n",
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(any("malformed SNBT" in error for error in errors), errors)

    def test_validator_reads_multiline_dependency_arrays(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            quest_id = catalog[0].quests[0].id
            chapter_path.write_text(
                chapter_path.read_text(encoding="utf-8").replace(
                    f'id: "{quest_id}"',
                    f'id: "{quest_id}"\n\t\t\tdependencies: [\n'
                    '\t\t\t\t"FFFFFFFFFFFFFFFF"\n\t\t\t]',
                    1,
                ),
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(any("unresolved dependency" in error for error in errors), errors)

    def test_validator_reports_missing_localization(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            self.quests.write_catalog(catalog, quest_root)
            quest_id = catalog[0].quests[0].id
            lang_path = quest_root / "lang" / "en_us.snbt"
            language = lang_path.read_text(encoding="utf-8")
            language = language.replace(
                f'\tquest.{quest_id}.title: "Build a Widget"\n', ""
            )
            lang_path.write_text(language, encoding="utf-8")

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(any("missing localization" in error for error in errors))

    def test_current_quest_corpus_validates(self) -> None:
        errors = self.quests.validate_quests(
            ROOT / "config" / "ftbquests" / "quests",
            ROOT / "server-test" / "mods",
        )
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
