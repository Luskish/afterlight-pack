from __future__ import annotations

import ast
import hashlib
import importlib
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from live_install_support import requires_live_install


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

    def test_snbt_long_converts_hex_ids_to_signed_java_longs(self) -> None:
        self.assertEqual(
            self.quests.SnbtLong.from_hex("9369E4AACBCDF5A1").value,
            -7824471455364680287,
        )
        self.assertEqual(
            self.quests.SnbtLong.from_hex("B99722D6E7EF5835").value,
            -5073548148800006091,
        )
        self.assertEqual(
            self.quests.SnbtLong.from_hex("9A4FA21B1999BDD5").value,
            -7327459831431184939,
        )
        self.assertEqual(
            self.quests.SnbtLong.from_hex("5D9DAC80C11182CF").value,
            6745737485865812687,
        )
        with self.assertRaisesRegex(ValueError, "signed 64-bit"):
            self.quests.SnbtLong(1 << 63)
        with self.assertRaisesRegex(ValueError, "signed 64-bit"):
            self.quests.SnbtLong(-(1 << 63) - 1)
        with self.assertRaisesRegex(ValueError, "hex ID"):
            self.quests.SnbtLong.from_hex("10000000000000000")

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

    def test_dependency_requirement_renders_and_rejects_unknown_modes(self) -> None:
        catalog = self.make_catalog(dependency="AAAAAAAAAAAAAAAA")
        catalog[0].quests[0].dependency_requirement = "one_completed"

        rendered = self.quests.render_chapter(catalog[0])

        self.assertIn('\t\t\tdependency_requirement: "one_completed"', rendered)
        with self.assertRaisesRegex(ValueError, "dependency requirement"):
            self.quests.QuestSpec(
                slug="story/test/invalid-dependency-mode",
                title="Invalid",
                description=("Invalid dependency mode.",),
                x=0.0,
                y=0.0,
                dependency_requirement="any_completed",
            )

    def test_task_five_catalog_has_certifications_and_depot(self) -> None:
        catalog = self.quests.build_catalog()[11:20]

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
        task_five_catalog = self.quests.build_catalog()[:20]
        self.assertEqual(
            (
                len(task_five_catalog),
                sum(len(chapter.quests) for chapter in task_five_catalog),
                sum(len(quest.tasks) for chapter in task_five_catalog for quest in chapter.quests),
                sum(len(quest.rewards) for chapter in task_five_catalog for quest in chapter.quests),
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

    def test_task_five_logistics_matches_installed_pipez_upgrade_capabilities(self) -> None:
        logistics = self.quests.build_catalog()[11]

        self.assertEqual([quest.title for quest in logistics.quests], [
            "Drawer Bank",
            "Storage Controller",
            "Item Pipes",
            "Round-Robin Routing",
            "Filtered Route",
            "Overflow Safety",
        ])
        round_robin = logistics.quests[3]
        filtered = logistics.quests[4]
        overflow = logistics.quests[5]
        self.assertEqual(
            round_robin.tasks[0].data["item"]["id"],
            "pipez:improved_upgrade",
        )
        self.assertEqual(
            filtered.tasks[0].data["item"]["id"],
            "pipez:advanced_upgrade",
        )
        self.assertEqual(round_robin.dependency_ids, (logistics.quests[2].id,))
        self.assertEqual(filtered.dependency_ids, (round_robin.id,))
        self.assertEqual(overflow.dependency_ids, (filtered.id,))
        self.assertIn("distribution", " ".join(round_robin.description).lower())
        self.assertIn("filter", " ".join(filtered.description).lower())

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
            self.assertEqual(self.quests.SnbtLong.from_hex(parsed["id"]), table_id)
            actual_items = {reward["item"]["id"] for reward in parsed["rewards"]}
            self.assertEqual(actual_items, item_ids)
            self.assertFalse(actual_items & progression_items)

    def test_task_six_catalog_has_exact_side_group_shape_and_finales(self) -> None:
        catalog = self.quests.build_catalog()[20:]

        self.assertEqual([chapter.title for chapter in catalog], [
            "Names in the Circuit",
            "Spells Under Load",
            "The Soul Ledger",
            "Resonance Proof",
            "Current Below",
            "Black Distillate",
            "Hot Cell",
            "Quantum Burden",
            "Courts Above and Beyond",
            "Root and Echo",
            "Edges of the Map",
            "Corrupted Guardians",
        ])
        self.assertEqual([len(chapter.quests) for chapter in catalog], [
            6, 6, 6, 5, 7, 7, 7, 7, 8, 6, 8, 11,
        ])
        self.assertEqual([chapter.id for chapter in catalog], [
            "DCDF0BB344B02192",
            "91D0B654D6E9B714",
            "045647E54F0A1D9E",
            "1A6C8CE2A6D208F9",
            "3C0EE28909760862",
            "8A48AB2CC20BC026",
            "FA26679C913AAF90",
            "5307E7406CB0DAE6",
            "4CEEFB108A0EECF8",
            "170AB7B39A0C4E47",
            "6A433C07EC56210B",
            "EEFD817FBDA0461F",
        ])
        self.assertEqual([chapter.quests[-1].id for chapter in catalog], [
            "051EA7B2A3B36BFD",
            "DF26F92E726A22AC",
            "C9286624F8D7D554",
            "87338DE0FE8114CF",
            "4F4161F5B97E27ED",
            "3E1151169E81AD32",
            "7131E55FB7E21244",
            "505A306462A8BC7E",
            "0DAB608A7B083DB8",
            "26E98713CAC0A689",
            "A31CFB60DB42BD03",
            "00EB5746A726C5B4",
        ])
        self.assertEqual(
            [chapter.group.resolved_id for chapter in catalog],
            ["51FF272F5030D2E6"] * 4
            + ["4DEAD1F5F7AB4DA3"] * 4
            + ["C8F8381D9519D002"] * 4,
        )
        full_catalog = self.quests.build_catalog()
        self.assertEqual(
            (
                len(full_catalog),
                sum(len(chapter.quests) for chapter in full_catalog),
                sum(len(quest.tasks) for chapter in full_catalog for quest in chapter.quests),
                sum(len(quest.rewards) for chapter in full_catalog for quest in chapter.quests),
            ),
            (32, 227, 250, 298),
        )

    def test_task_six_undercurrent_requires_ars_plus_exactly_one_branch(self) -> None:
        chapters = {chapter.title: chapter for chapter in self.quests.build_catalog()[20:24]}
        ars_finale = "7480D99D56556C8E"
        branch_finales = (
            "051EA7B2A3B36BFD",
            "DF26F92E726A22AC",
            "C9286624F8D7D554",
        )

        for title in ("Names in the Circuit", "Spells Under Load", "The Soul Ledger"):
            self.assertEqual(chapters[title].quests[0].dependency_ids, (ars_finale,))

        join = chapters["Resonance Proof"].quests[0]
        self.assertEqual(join.id, "6363BCE8A71FA766")
        self.assertEqual(join.dependency_ids, branch_finales)
        self.assertEqual(join.dependency_requirement, "one_completed")
        self.assertNotIn(ars_finale, join.dependency_ids)

        finale = chapters["Resonance Proof"].quests[-1]
        precursor_rewards = [
            reward for reward in finale.rewards
            if reward.reward_type == "item"
            and reward.data.get("item", {}).get("id")
            == "kubejs:undercurrent_stabilizer_precursor"
        ]
        self.assertEqual(len(precursor_rewards), 1)
        self.assertEqual(precursor_rewards[0].data["count"], 1)
        self.assertEqual(
            [reward.data["stage"] for reward in finale.rewards if reward.reward_type == "gamestage"],
            ["afterlight_stabilizer_ready"],
        )
        self.assertFalse(any(
            task.data.get("item", {}).get("id") == "kubejs:undercurrent_stabilizer_precursor"
            for chapter in self.quests.build_catalog()
            for quest in chapter.quests
            for task in quest.tasks
        ))

    def test_task_six_deep_vault_opener_preserves_ids_and_adds_nonconsuming_key_gate(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        path = ROOT / "config/ftbquests/quests/chapters/6B2D7DB791D992C3.snbt"
        parsed = _parse_snbt(path.read_text(encoding="utf-8"))

        self.assertEqual(parsed["id"], "6B2D7DB791D992C3")
        self.assertEqual([quest["id"] for quest in parsed["quests"]], [
            "96783315E0833B1D",
            "747D181BE87A2429",
            "9738976FB1A6167A",
            "DEEFEE4A3873DE5C",
            "F2CE68CEF727A313",
        ])
        self.assertEqual(
            [task["id"] for quest in parsed["quests"] for task in quest["tasks"]],
            [
                "E595488C9696FD3D",
                "CC3B34BB975A26E4",
                "F0386E249F64C241",
                "448C181914369553",
                "88B818D0316B37F9",
                "1BE02019A215A7C4",
            ],
        )
        self.assertEqual(
            [reward["id"] for quest in parsed["quests"] for reward in quest["rewards"]],
            [
                "300AB696B71C85DF",
                "3AB2DC0BCB5633EE",
                "3F4B8DA2BF026248",
                "96B4C8E5A1B26706",
                "60C70F21C10E9726",
                "DDF12C4395F6A64A",
                "B75634D32BF15E2B",
                "937D55E3FC4E0FC8",
            ],
        )
        key_tasks = [
            task for task in parsed["quests"][0]["tasks"]
            if task.get("item", {}).get("id") == "kubejs:deep_vault_key"
        ]
        self.assertEqual(len(key_tasks), 1)
        self.assertFalse(key_tasks[0]["consume_items"])
        self.assertEqual(
            [reward.get("stage") for reward in parsed["quests"][0]["rewards"] if reward["type"] == "gamestage"],
            ["afterlight_deep_vault"],
        )
        localization_path = ROOT / "config/ftbquests/quests/lang/en_us.snbt"
        localization = _parse_snbt(localization_path.read_text(encoding="utf-8"))
        self.assertIn(
            "Everything in this wing is optional. Nothing in this wing is small. "
            "Bring the recovered Deep Vault Key and a hammer. "
            "The key opens the way; honest metallurgy does the rest.",
            localization["quest.96783315E0833B1D.quest_desc"],
        )

    def test_task_six_side_graph_remains_optional_and_acyclic(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        catalog = self.quests.build_catalog()
        story_group_id = catalog[0].group.resolved_id
        side_quest_ids = {
            quest.id
            for chapter in catalog[20:]
            for quest in chapter.quests
        }
        story_dependencies = {
            dependency
            for path in (ROOT / "config/ftbquests/quests/chapters").glob("*.snbt")
            for chapter in [_parse_snbt(path.read_text(encoding="utf-8"))]
            if chapter.get("group") == story_group_id
            for quest in chapter["quests"]
            for dependency in quest.get("dependencies", [])
        }
        self.assertEqual(len(side_quest_ids), 84)
        self.assertFalse(side_quest_ids & story_dependencies)

        deep_vault = catalog[24:28]
        self.assertEqual(deep_vault[0].quests[0].dependency_ids, ("F2CE68CEF727A313",))
        for previous, current in zip(deep_vault, deep_vault[1:]):
            self.assertEqual(current.quests[0].dependency_ids, (previous.quests[-1].id,))

        atlas = catalog[28:]
        self.assertEqual(
            atlas[-1].quests[0].dependency_ids,
            tuple(chapter.quests[-1].id for chapter in atlas[:3]),
        )

    def test_task_six_cache_tables_are_progression_safe(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        expected = {
            "ascendancy_cache_rare.snbt": (
                self.quests.ASCENDANCY_CACHE_RARE_TABLE,
                2,
                {
                    "kubejs:requisition_chit",
                    "minecraft:iron_block",
                    "minecraft:golden_apple",
                    "minecraft:diamond",
                    "create:brass_ingot",
                    "mekanism:alloy_reinforced",
                    "ae2:logic_processor",
                    "immersiveengineering:ingot_steel",
                    "modern_industrialization:stainless_steel_ingot",
                    "minecraft:experience_bottle",
                    "minecraft:netherite_scrap",
                    "minecraft:enchanted_golden_apple",
                },
            ),
            "ascendancy_cache_epic.snbt": (
                self.quests.ASCENDANCY_CACHE_EPIC_TABLE,
                3,
                {
                    "kubejs:requisition_chit",
                    "minecraft:iron_block",
                    "minecraft:golden_apple",
                    "minecraft:diamond",
                    "create:brass_ingot",
                    "mekanism:alloy_reinforced",
                    "ae2:logic_processor",
                    "immersiveengineering:ingot_steel",
                    "modern_industrialization:stainless_steel_ingot",
                    "minecraft:experience_bottle",
                    "minecraft:netherite_scrap",
                    "minecraft:enchanted_golden_apple",
                },
            ),
        }
        forbidden_fragments = (
            "deep_vault_key",
            "schematic_",
            "gate_",
            "stabilizer",
            "ascendancy_seal",
            "creative",
        )

        for filename, (table_id, loot_size, item_ids) in expected.items():
            parsed = _parse_snbt(
                (ROOT / "config/ftbquests/quests/reward_tables" / filename).read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(self.quests.SnbtLong.from_hex(parsed["id"]), table_id)
            self.assertEqual(int(parsed["loot_size"]), loot_size)
            actual_items = {reward["item"]["id"] for reward in parsed["rewards"]}
            self.assertEqual(actual_items, item_ids)
            self.assertFalse(any(
                fragment in item_id
                for item_id in actual_items
                for fragment in forbidden_fragments
            ))

    def test_all_reward_table_references_use_signed_java_longs_and_resolve(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        quest_root = ROOT / "config/ftbquests/quests"
        table_values: set[int] = set()
        for path in (quest_root / "reward_tables").glob("*.snbt"):
            parsed = _parse_snbt(path.read_text(encoding="utf-8"))
            table_values.add(self.quests.SnbtLong.from_hex(parsed["id"]).value)

        references: list[tuple[Path, str, int]] = []

        def collect(path: Path, value) -> None:
            if isinstance(value, dict):
                reward_type = value.get("type")
                if reward_type in {"choice", "random", "loot", "all_table"}:
                    raw = value.get("table_id")
                    self.assertIsInstance(raw, str, f"missing table_id in {path}")
                    self.assertTrue(raw.endswith("L"), f"untyped table_id in {path}: {raw}")
                    references.append((path, reward_type, int(raw[:-1])))
                for child in value.values():
                    collect(path, child)
            elif isinstance(value, list):
                for child in value:
                    collect(path, child)

        for path in quest_root.rglob("*.snbt"):
            collect(path, _parse_snbt(path.read_text(encoding="utf-8")))

        self.assertTrue(references)
        for path, reward_type, table_id in references:
            self.assertGreaterEqual(table_id, -(1 << 63), (path, reward_type, table_id))
            self.assertLessEqual(table_id, (1 << 63) - 1, (path, reward_type, table_id))
            self.assertIn(table_id, table_values, (path, reward_type, table_id))

    def test_retired_generators_cannot_render_unsigned_reward_table_longs(self) -> None:
        direct_base16_calls = []
        unsigned_literals = []
        missing_signed_conversion = []
        for path in ROOT.glob("tools/gen-quests*.py"):
            text = path.read_text(encoding="utf-8")
            if "table_id:" not in text:
                continue
            tree = ast.parse(text, filename=str(path))
            signed_calls = [
                node
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "from_hex"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "SnbtLong"
            ]
            if not signed_calls:
                missing_signed_conversion.append(path.name)
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "int"
                ):
                    positional_base = (
                        len(node.args) > 1
                        and isinstance(node.args[1], ast.Constant)
                        and node.args[1].value == 16
                    )
                    keyword_base = any(
                        keyword.arg == "base"
                        and isinstance(keyword.value, ast.Constant)
                        and keyword.value.value == 16
                        for keyword in node.keywords
                    )
                    if positional_base or keyword_base:
                        direct_base16_calls.append((path.name, node.lineno))
                if (
                    isinstance(node, ast.Constant)
                    and isinstance(node.value, int)
                    and node.value > (1 << 63) - 1
                ):
                    unsigned_literals.append((path.name, node.lineno, node.value))

        self.assertEqual(direct_base16_calls, [])
        self.assertEqual(unsigned_literals, [])
        self.assertEqual(missing_signed_conversion, [])

    @requires_live_install(ROOT)
    def test_task_six_registry_targets_exist_in_installed_jars(self) -> None:
        targets = {
            "item": {
                "occultism:dictionary_of_spirits", "occultism:chalk_white",
                "occultism:sacrificial_bowl", "occultism:spirit_attuned_gem",
                "occultism:storage_controller", "occultism:storage_remote",
                "occultism:stable_wormhole", "irons_spellbooks:copper_spell_book",
                "irons_spellbooks:arcane_essence", "irons_spellbooks:inscription_table",
                "irons_spellbooks:scroll_forge", "irons_spellbooks:alchemist_cauldron",
                "irons_spellbooks:arcane_anvil", "malum:encyclopedia_arcana",
                "malum:spirit_altar", "malum:spirit_jar", "malum:spirit_crucible",
                "malum:arcana_pylon", "malum:soul_stained_steel_ingot",
                "modern_industrialization:singularity",
            },
            "entity": {
                "undergarden:forgotten_guardian", "deeperdarker:stalker",
                "eternal_starlight:stranghoul", "eternal_starlight:the_gatekeeper",
                "mowziesmobs:ferrous_wroughtnaut", "mowziesmobs:frostmaw",
                "mowziesmobs:umvuthi", "cataclysm:netherite_monstrosity",
                "cataclysm:maledictus",
            },
            "structure": {
                "undergarden:catacombs", "deeperdarker:ancient_temple",
                "eternal_starlight:stranghoul_den", "eternal_starlight:cursed_garden",
                "eternal_starlight:golem_forge",
            },
            "dimension": {
                "twilightforest:twilight_forest", "aether:the_aether",
                "undergarden:undergarden", "deeperdarker:otherside",
                "eternal_starlight:starlight",
            },
            "advancement": {
                "twilightforest:progress_naga", "twilightforest:progress_lich",
                "twilightforest:progress_hydra", "aether:bronze_dungeon",
                "aether:silver_dungeon", "aether:gold_dungeon",
                "eternal_starlight:kill_lunar_monstrosity",
                "eternal_starlight:kill_golem",
                "bosses_of_mass_destruction:nether/gauntlet_defeat",
                "bosses_of_mass_destruction:adventure/night_lich_defeat",
                "bosses_of_mass_destruction:end/obsidilith_defeat",
                "bosses_of_mass_destruction:adventure/void_blossom_defeat",
            },
        }
        project_items: set[str] = set()
        for chapter in self.quests.build_catalog()[20:]:
            project_items.add(chapter.icon)
            for quest in chapter.quests:
                for task in quest.tasks:
                    item_id = task.data.get("item", {}).get("id")
                    if item_id:
                        project_items.add(item_id)
                for reward in quest.rewards:
                    item_id = reward.data.get("item", {}).get("id")
                    if item_id:
                        project_items.add(item_id)
        targets["item"].update(
            item_id for item_id in project_items if not item_id.startswith("kubejs:")
        )
        registry_script = (
            ROOT / "kubejs/startup_scripts/afterlight/registry.js"
        ).read_text(encoding="utf-8")
        for item_id in project_items:
            if item_id.startswith("kubejs:"):
                self.assertIn(f"event.create('{item_id.split(':', 1)[1]}')", registry_script)
        jar_entries: set[str] = set()
        language = b""
        for jar_path in (ROOT / "server-test/mods").glob("*.jar"):
            with zipfile.ZipFile(jar_path) as jar:
                names = jar.namelist()
                jar_entries.update(names)
                for name in names:
                    if name.endswith("/lang/en_us.json"):
                        language += jar.read(name)

        missing = []
        for kind, resource_ids in targets.items():
            for resource_id in resource_ids:
                namespace, path = resource_id.split(":", 1)
                if kind == "item":
                    found = (
                        f"assets/{namespace}/models/item/{path}.json" in jar_entries
                        or f"assets/{namespace}/items/{path}.json" in jar_entries
                        or f'item.{namespace}.{path}'.encode() in language
                    )
                elif kind == "entity":
                    found = f'entity.{namespace}.{path}'.encode() in language
                elif kind == "structure":
                    found = (
                        f"data/{namespace}/worldgen/structure/{path}.json" in jar_entries
                        or f"data/{namespace}/structures/{path}.nbt" in jar_entries
                    )
                elif kind == "dimension":
                    found = f"data/{namespace}/dimension/{path}.json" in jar_entries
                else:
                    found = (
                        f"data/{namespace}/advancement/{path}.json" in jar_entries
                        or f"data/{namespace}/advancements/{path}.json" in jar_entries
                    )
                if not found:
                    missing.append((kind, resource_id))
        self.assertEqual(missing, [])

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

    @requires_live_install(ROOT)
    def test_current_quest_corpus_validates(self) -> None:
        errors = self.quests.validate_quests(
            ROOT / "config" / "ftbquests" / "quests",
            ROOT / "server-test" / "mods",
        )
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
