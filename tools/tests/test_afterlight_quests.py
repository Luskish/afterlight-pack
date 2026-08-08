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
        catalog = self.quests.build_catalog()[:6]
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
        catalog = self.quests.build_catalog()[:6]

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
        catalog = self.quests.build_catalog()[:6]
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

    def test_act_two_ae2_onramp_uses_complete_compatible_targets(self) -> None:
        quests = {
            quest.title: quest
            for chapter in self.quests.build_catalog()[:6]
            for quest in chapter.quests
        }

        press_task = quests["Lost Presses"].tasks[0]
        self.assertEqual(
            press_task.data["item"]["id"],
            "ae2:logic_processor_press",
        )

        autocraft_targets = {
            task.data["item"]["id"]
            for task in quests["First Autocraft"].tasks
        }
        self.assertEqual(
            autocraft_targets,
            {
                "ae2:pattern_encoding_terminal",
                "ae2:crafting_pattern",
                "ae2:pattern_provider",
                "ae2:molecular_assembler",
                "ae2:1k_crafting_storage",
            },
        )

    def test_act_three_catalog_has_exact_shape_chain_and_finale_ids(self) -> None:
        catalog = self.quests.build_catalog()[6:11]
        expected_quests = [
            [
                "Machine Core", "Pulverization", "Centrifuge", "Assembly",
                "Foundry", "Laser Processing", "Jetpack", "Reactor Frontier",
                "Prometheum", "Kinetic Schematic",
            ],
            [
                "Ancient Factory", "Harbinger", "Ruined Citadel",
                "Ender Guardian", "Burning Arena", "Ignis", "Sunken City",
                "Leviathan", "War Salvage", "Industry Schematic",
            ],
            [
                "Fission Assembly", "Fissile Fuel", "Turbine", "Polonium",
                "Plutonium", "SPS", "Antimatter", "100M FE Proof",
                "Isotope Schematic",
            ],
            [
                "Flight Harness", "Aeronautics Trial", "Propulsion",
                "Mobile Storage", "High-Altitude Trial", "Starlight",
                "Golem Forge", "Gatekeeper Signal", "Relay Core",
                "Lattice Schematic",
            ],
            [
                "Four Keys", "Mega Storage", "256K Crafting CPU",
                "Assembler Matrix", "Fusion Controller",
                "Certified Bulk Quotas", "Ancient Remnant", "Gate Blueprint",
            ],
        ]

        self.assertEqual([chapter.title for chapter in catalog], [
            "Frontier Machines",
            "The War Below",
            "Quantum Weather",
            "The Long Sky",
            "Architect",
        ])
        self.assertEqual([len(chapter.quests) for chapter in catalog], [10, 10, 9, 10, 8])
        self.assertEqual(
            [[quest.title for quest in chapter.quests] for chapter in catalog],
            expected_quests,
        )
        self.assertEqual([chapter.order_index for chapter in catalog], [11, 12, 13, 14, 15])
        self.assertEqual(catalog[0].quests[0].dependency_ids, ("836D1C6E20B78461",))
        for previous, current in zip(catalog, catalog[1:]):
            self.assertEqual(current.quests[0].dependency_ids, (previous.quests[-1].id,))
        self.assertEqual(
            [chapter.quests[-1].id for chapter in catalog],
            [
                "90EDD2BED35BE9E3",
                "752C3E53CA89C92D",
                "A1A99D99B372916F",
                "3497EFDF016FAFD7",
                "72446D404001B38D",
            ],
        )

    def test_act_three_finales_have_exact_memories_progression_and_stages(self) -> None:
        catalog = self.quests.build_catalog()[6:11]
        progression = [
            ("kubejs:schematic_kinetic_frame", "afterlight:gate_create"),
            ("kubejs:schematic_industrial_anchor", "afterlight:gate_ie"),
            ("kubejs:schematic_isotopic_core", "afterlight:gate_mekanism"),
            ("kubejs:schematic_lattice_matrix", "afterlight:gate_ae2"),
            ("kubejs:gate_blueprint", "afterlight_act3_complete"),
        ]

        for fragment, chapter, (item_id, stage) in zip(
            range(11, 16), catalog, progression
        ):
            finale = chapter.quests[-1]
            self.assertIn(
                f"MEMORY FRAGMENT {fragment:02d} RESTORED",
                "\n".join(finale.description),
            )
            self.assertEqual(
                [reward.reward_type for reward in finale.rewards],
                ["loot", "item", "xp", "item", "gamestage"],
            )
            self.assertEqual(finale.rewards[3].data["item"]["id"], item_id)
            self.assertEqual(finale.rewards[4].data, {"stage": stage})

        progression_ids = {
            item_id for item_id, _stage in progression
        }
        rewarded_progression = [
            reward.data["item"]["id"]
            for chapter in catalog
            for quest in chapter.quests
            for reward in quest.rewards
            if reward.reward_type == "item"
            and reward.data.get("item", {}).get("id") in progression_ids
        ]
        self.assertCountEqual(rewarded_progression, progression_ids)

    def test_act_three_uses_exact_special_task_shapes(self) -> None:
        catalog = self.quests.build_catalog()[6:11]
        pre_task_five = self.quests.build_catalog()[:11]
        quests = {
            quest.title: quest
            for chapter in catalog
            for quest in chapter.quests
        }

        self.assertEqual(
            quests["100M FE Proof"].tasks[0].data,
            {
                "value": self.quests.SnbtLong(100_000_000),
                "max_input": self.quests.SnbtLong(1_000_000),
            },
        )
        self.assertEqual(
            [task.data["advancement"] for task in quests["Aeronautics Trial"].tasks
             + quests["Propulsion"].tasks],
            ["aeronautics:head_in_the_clouds", "aeronautics:in_thrust_we_trust"],
        )
        self.assertEqual(quests["Starlight"].tasks[0].data, {
            "dimension": "eternal_starlight:starlight",
        })
        self.assertEqual(quests["Golem Forge"].tasks[0].data, {
            "structure": "eternal_starlight:golem_forge",
        })
        self.assertEqual(quests["Gatekeeper Signal"].tasks[0].data, {
            "entity": "eternal_starlight:the_gatekeeper",
            "value": self.quests.SnbtLong(1),
        })
        self.assertEqual(
            [task.data["stage"] for task in quests["Four Keys"].tasks],
            [
                "afterlight:gate_create",
                "afterlight:gate_ie",
                "afterlight:gate_mekanism",
                "afterlight:gate_ae2",
            ],
        )
        self.assertTrue(all(
            task.task_type == "gamestage" for task in quests["Four Keys"].tasks
        ))
        self.assertEqual(
            [task.data["stage"] for task in quests["Certified Bulk Quotas"].tasks],
            [
                "afterlight_cert_kinetics_i",
                "afterlight_cert_logistics_i",
                "afterlight_cert_ore_loop_i",
                "afterlight_cert_autocrafting_i",
                "afterlight_cert_cross_mod_i",
                "afterlight_cert_power_i",
                "afterlight_cert_infrastructure_ii",
            ],
        )
        gate_blueprint = quests["Gate Blueprint"]
        self.assertEqual(len(gate_blueprint.tasks), 1)
        self.assertEqual(gate_blueprint.tasks[0].task_type, "checkmark")
        self.assertEqual(gate_blueprint.tasks[0].data, {})
        self.assertFalse(any(
            "draconicevolution:" in str(task.data)
            for chapter in catalog
            for quest in chapter.quests
            for task in quest.tasks
        ))
        self.assertEqual(
            (
                len(pre_task_five),
                sum(len(chapter.quests) for chapter in pre_task_five),
                sum(
                    len(quest.tasks)
                    for chapter in pre_task_five
                    for quest in chapter.quests
                ),
                sum(
                    len(quest.rewards)
                    for chapter in pre_task_five
                    for quest in chapter.quests
                ),
            ),
            (11, 104, 117, 137),
        )

    def test_repeatable_quest_fields_render_exact_ftb_schema(self) -> None:
        catalog = self.make_catalog()
        catalog[0].quests[0].can_repeat = True
        catalog[0].quests[0].repeat_cooldown = 5

        rendered = self.quests.render_chapter(catalog[0])

        self.assertIn("\t\t\tcan_repeat: true", rendered)
        self.assertIn("\t\t\trepeat_cooldown: 5", rendered)

    def test_task_five_catalog_has_certifications_and_depot(self) -> None:
        catalog = self.quests.build_catalog()[11:]

        self.assertEqual([chapter.title for chapter in catalog], [
            "Logistics I",
            "Ore Loop I",
            "Autocrafting I",
            "Cross-Mod I",
            "Power I",
            "Infrastructure II",
            "Requisition Depot: Early",
            "Requisition Depot: Mid",
            "Requisition Depot: Late",
        ])
        self.assertEqual([len(chapter.quests) for chapter in catalog], [6, 6, 6, 6, 6, 6, 1, 1, 1])
        self.assertTrue(all(
            chapter.group.resolved_id == "CA20F33642175B95"
            for chapter in catalog
        ))
        self.assertEqual([chapter.order_index for chapter in catalog], [1, 2, 3, 4, 5, 6, 20, 21, 22])
        full_catalog = self.quests.build_catalog()
        self.assertEqual(
            (
                len(full_catalog),
                sum(len(chapter.quests) for chapter in full_catalog),
                sum(len(quest.tasks) for chapter in full_catalog for quest in chapter.quests),
                sum(len(quest.rewards) for chapter in full_catalog for quest in chapter.quests),
            ),
            (20, 143, 162, 188),
        )

    def test_task_five_certification_finales_award_exact_stages(self) -> None:
        certifications = self.quests.build_catalog()[11:17]
        expected_stages = [
            "afterlight_cert_logistics_i",
            "afterlight_cert_ore_loop_i",
            "afterlight_cert_autocrafting_i",
            "afterlight_cert_cross_mod_i",
            "afterlight_cert_power_i",
            "afterlight_cert_infrastructure_ii",
        ]

        for chapter, expected_stage in zip(certifications, expected_stages):
            stage_rewards = [
                reward for reward in chapter.quests[-1].rewards
                if reward.reward_type == "gamestage"
            ]
            self.assertEqual(len(stage_rewards), 1)
            self.assertEqual(stage_rewards[0].data, {"stage": expected_stage})

        infrastructure_proof = certifications[-1].quests[0]
        self.assertEqual(
            [task.data["stage"] for task in infrastructure_proof.tasks],
            [
                "afterlight_cert_kinetics_i",
                "afterlight_cert_logistics_i",
                "afterlight_cert_ore_loop_i",
                "afterlight_cert_autocrafting_i",
                "afterlight_cert_cross_mod_i",
                "afterlight_cert_power_i",
            ],
        )
        self.assertTrue(all(
            task.task_type == "gamestage" for task in infrastructure_proof.tasks
        ))

    def test_task_five_power_certification_uses_real_grid_finale(self) -> None:
        power = self.quests.build_catalog()[15]

        self.assertEqual(
            power.quests[0].dependency_ids,
            ("6B876A865DE7A77A",),
        )

    def test_task_five_ore_loop_uses_coherent_three_machine_path(self) -> None:
        ore_loop = self.quests.build_catalog()[12]

        self.assertEqual(
            [quest.title for quest in ore_loop.quests],
            [
                "Enrichment Stage",
                "Smelting Stage",
                "Block Assembly",
                "Measured Buffer",
                "Energy Budget",
                "32-Block Run",
            ],
        )
        self.assertEqual(
            [
                quest.tasks[0].data.get("item", {}).get("id")
                for quest in ore_loop.quests[:3]
            ],
            [
                "mekanism:enrichment_chamber",
                "mekanism:energized_smelter",
                "mekanism:formulaic_assemblicator",
            ],
        )
        finale_task = ore_loop.quests[-1].tasks[0]
        self.assertEqual(finale_task.data["item"]["id"], "mekanism:block_osmium")
        self.assertEqual(finale_task.data["count"], self.quests.SnbtLong(32))

    def test_task_five_cross_mod_uses_bridge_coherent_machine_path(self) -> None:
        cross_mod = self.quests.build_catalog()[14]

        self.assertEqual(
            [quest.title for quest in cross_mod.quests],
            [
                "Create Crushing",
                "Mekanism Smelting",
                "IE Conveyance",
                "AE2 Stocking",
                "Osmium Batch",
                "Cross-System Recovery",
            ],
        )
        expected_item_tasks = [
            ("create:crushing_wheel", 2),
            ("mekanism:energized_smelter", 1),
            ("immersiveengineering:conveyor_basic", 8),
            ("ae2:interface", 2),
            ("mekanism:ingot_osmium", 256),
        ]
        self.assertEqual(
            [
                (
                    quest.tasks[0].data["item"]["id"],
                    quest.tasks[0].data["count"].value,
                )
                for quest in cross_mod.quests[:5]
            ],
            expected_item_tasks,
        )

    def test_task_five_depot_consumes_chits_and_uses_choice_tables(self) -> None:
        depots = self.quests.build_catalog()[17:]
        expected = [
            (8, self.quests.DEPOT_EARLY_TABLE),
            (16, self.quests.DEPOT_MID_TABLE),
            (32, self.quests.DEPOT_LATE_TABLE),
        ]

        for chapter, (cost, table_id) in zip(depots, expected):
            exchange = chapter.quests[0]
            self.assertTrue(exchange.can_repeat)
            self.assertEqual(exchange.repeat_cooldown, 5)
            self.assertEqual(len(exchange.tasks), 1)
            self.assertEqual(exchange.tasks[0].task_type, "item")
            self.assertEqual(exchange.tasks[0].data, {
                "item": {"count": 1, "id": "kubejs:requisition_chit"},
                "count": self.quests.SnbtLong(cost),
                "consume_items": True,
            })
            self.assertEqual(len(exchange.rewards), 1)
            self.assertEqual(exchange.rewards[0].reward_type, "choice")
            self.assertEqual(exchange.rewards[0].data, {"table_id": table_id})

    def test_task_five_depot_tables_are_balanced_and_progression_safe(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        expected = {
            "depot_early.snbt": (
                self.quests.DEPOT_EARLY_TABLE,
                {
                    "minecraft:iron_ingot",
                    "minecraft:copper_ingot",
                    "minecraft:redstone",
                    "minecraft:coal",
                    "minecraft:bread",
                },
            ),
            "depot_mid.snbt": (
                self.quests.DEPOT_MID_TABLE,
                {
                    "create:brass_ingot",
                    "mekanism:alloy_infused",
                    "ae2:fluix_crystal",
                    "immersiveengineering:ingot_steel",
                    "minecraft:diamond",
                },
            ),
            "depot_late.snbt": (
                self.quests.DEPOT_LATE_TABLE,
                {
                    "mekanism:alloy_atomic",
                    "ae2:calculation_processor",
                    "immersiveengineering:component_electronic_adv",
                    "oritech:machine_core_2",
                    "minecraft:netherite_ingot",
                },
            ),
        }
        progression_items = {
            "kubejs:deep_vault_key",
            "kubejs:schematic_kinetic_frame",
            "kubejs:schematic_industrial_anchor",
            "kubejs:schematic_isotopic_core",
            "kubejs:schematic_lattice_matrix",
            "kubejs:gate_blueprint",
            "kubejs:undercurrent_stabilizer_precursor",
            "kubejs:ascendancy_seal",
        }

        for filename, (table_id, item_ids) in expected.items():
            path = ROOT / "config/ftbquests/quests/reward_tables" / filename
            parsed = _parse_snbt(path.read_text(encoding="utf-8"))
            self.assertEqual(int(parsed["id"], 16), table_id.value)
            actual_items = {reward["item"]["id"] for reward in parsed["rewards"]}
            self.assertEqual(actual_items, item_ids)
            self.assertFalse(actual_items & progression_items)

    def test_kinetics_finale_keeps_ids_and_awards_stage(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        path = ROOT / "config/ftbquests/quests/chapters/23643435F7BE74AC.snbt"
        parsed = _parse_snbt(path.read_text(encoding="utf-8"))

        self.assertEqual(parsed["id"], "23643435F7BE74AC")
        self.assertEqual(
            [quest["id"] for quest in parsed["quests"]],
            [
                "1641CC316D20D678",
                "2E19596E25ADFC17",
                "692967044603050B",
                "490AEF80C130D8DD",
                "93E278CD695BCE11",
                "5ADAE277C9FEF0F1",
            ],
        )
        stage_rewards = [
            reward for reward in parsed["quests"][-1]["rewards"]
            if reward["type"] == "gamestage"
        ]
        self.assertEqual(len(stage_rewards), 1)
        self.assertEqual(stage_rewards[0]["stage"], "afterlight_cert_kinetics_i")

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
