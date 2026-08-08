from __future__ import annotations

import copy
import hashlib
import json
import sys
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
KUBEJS_DATA = ROOT / "kubejs" / "data"
MODS_DIR = ROOT / "server-test" / "mods"
LATEST_LOG = ROOT / "server-test" / "logs" / "latest.log"
CEI_FILTER_PACK = KUBEJS_DATA / "afterlight_rc_hygiene.zip"

CONFIG_HASHES = {
    "jupiter.json": "ac6415cb504a1cd8d129435e67e718b0f139613f378127f0f8f21ee61ca4ffe7",
    "iceandfire/iaf-common.json": "a520e5e7909c9e50d1857874f853e6fafff8ac106fabff239868d5c57a57b546",
    "justdirethings-server.toml": "7605dc482ee04abd027f9180d1d215eb8acd4a00c95eab8e9f8ea77bd442e894",
    "mcjtylib-server.toml": "91eb6e4963efb985fe27bd7b0b70f03a3bc2bd15376649002812c4bb343e6582",
    "create_enchantment_industry-server.toml": "8434e2dcd11cb4c8098dc653e41dc06ec512f9cb3884c90ea19dcae604a256b1",
    "quark-common.toml": "9bf61c165626d5d0cc972bee5521117523d31693728430577a6d08368456e960",
    "alexsmobs-common.toml": "219d516786a0c0db3f8f7af0ce6f7d299edbd1d7eff991ba51ac59860b4cc58d",
}

MALUM_SPIRIT_REPAIRS = {
    "occultism/gold_chalk": "valid_items",
    "occultism/purple_chalk": "valid_items",
    "occultism/red_chalk": "valid_items",
    "occultism/white_chalk": "valid_items",
    "undergarden/cloggrum": "regex",
    "undergarden/forgotten": "regex",
    "undergarden/froststeel": "regex",
    "undergarden/slingshot": "valid_items",
    "undergarden/utherium": "regex",
}

MALUM_REGEX_VALID_ITEMS = {
    "undergarden/cloggrum": [
        "undergarden:cloggrum_axe",
        "undergarden:cloggrum_battleaxe",
        "undergarden:cloggrum_boots",
        "undergarden:cloggrum_chestplate",
        "undergarden:cloggrum_helmet",
        "undergarden:cloggrum_hoe",
        "undergarden:cloggrum_leggings",
        "undergarden:cloggrum_pickaxe",
        "undergarden:cloggrum_shield",
        "undergarden:cloggrum_shovel",
        "undergarden:cloggrum_sword",
    ],
    "undergarden/forgotten": [
        "undergarden:forgotten_axe",
        "undergarden:forgotten_battleaxe",
        "undergarden:forgotten_hoe",
        "undergarden:forgotten_pickaxe",
        "undergarden:forgotten_shovel",
        "undergarden:forgotten_sword",
    ],
    "undergarden/froststeel": [
        "undergarden:froststeel_axe",
        "undergarden:froststeel_boots",
        "undergarden:froststeel_chestplate",
        "undergarden:froststeel_helmet",
        "undergarden:froststeel_hoe",
        "undergarden:froststeel_leggings",
        "undergarden:froststeel_pickaxe",
        "undergarden:froststeel_shovel",
        "undergarden:froststeel_sword",
    ],
    "undergarden/utherium": [
        "undergarden:utherium_axe",
        "undergarden:utherium_boots",
        "undergarden:utherium_chestplate",
        "undergarden:utherium_helmet",
        "undergarden:utherium_hoe",
        "undergarden:utherium_leggings",
        "undergarden:utherium_pickaxe",
        "undergarden:utherium_shovel",
        "undergarden:utherium_sword",
    ],
}

DYE_DEPOT_COLORS = (
    "amber",
    "aqua",
    "beige",
    "coral",
    "forest",
    "ginger",
    "indigo",
    "maroon",
    "mint",
    "navy",
    "olive",
    "rose",
    "slate",
    "tan",
    "teal",
    "verdant",
)

REPAIRED_LOG_SIGNATURES = (
    "Failed to load config: ./config/jupiter.json",
    "Failed to load config: ./config/iceandfire/iaf-common.json",
    "dispatch for modid mcjtylib",
    "Incorrect key kinetics.fluids.mechanicalGrindstoneFluidCapacity",
    "oritech:mixing/compat/create/turbofuel[create:mixing]",
    "example is not a registered slot type",
    "cataclysm:needs_black_steel_tool",
    "cataclysm:needs_monstrosity_tool",
    "Couldn't load advancements: [",
    "Parsing error loading recipe malum:malum/spirit_repair/",
    "Failed to parse recipe 'malum:malum/spirit_repair/",
    "malum:create/milling/grim_talc[create:milling]",
    "Parsing error loading recipe malum:create/milling/grim_talc",
    "Object with ID enderio:xpjuice specified in data map",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:create_connected:blocks/dye_depot_",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:extendedae:blocks/ex_emc_interface",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:irons_spellbooks:test/ring_gen_break_me",
    "Couldn't load tag idas:has_structure/byg_redwood_biomes",
    "Couldn't load tag idas:has_structure/bygmohogany_biomes",
    "Couldn't load tag idas:has_structure/bopredwood_biomes",
    "Couldn't load tag idas:has_structure/bopmohogany_biomes",
    "Detected quark:stoneling that was registered with CREATURE mob category",
    "Detected quark:toretoise that was registered with CREATURE mob category",
    "Detected quark:foxhound that was registered with CREATURE mob category",
    "Detected alexsmobs:skreecher that was registered with CREATURE mob category",
    "Detected minecraft:axolotl that was registered with AXOLOTLS mob category but was added under UNDERGROUND_WATER_CREATURE mob category for terralith:",
)

KNOWN_RESIDUALS = {
    "Kaleidoscope carrier warnings": (
        "Failed to read component 'carrier: ingredient?' from recipe kaleidoscope_cookery:",
        27,
    ),
    "Incendium smithing fallback": (
        "Failed to parse recipe 'incendium:upgrade_elytra[minecraft:smithing_transform]'",
        1,
    ),
    "EnderIO Malum inheritance warnings": (
        "[EnderIO] Unable to inherit the cooking recipe with ID: malum:",
        9,
    ),
    "IDAS air ItemStack errors": (
        "Tried to load invalid item: 'Item must not be minecraft:air'",
        2,
    ),
    "Just Dire Things config lifecycle warning": (
        "Error white registering dispenser behavior for item justdirethings:fuel_canister",
        1,
    ),
    "EnderIO XP Juice registry mismatch": (
        "Object with ID enderio:xp_juice specified in data map",
        1,
    ),
    "Apothic Enchanting stale data map type": (
        "Found data map file for non-existent data map type 'apothic_enchanting:enchantment_info'",
        1,
    ),
    "IDAS empty optional tag registry warnings": (
        "Not all defined tags for registry ResourceKey[minecraft:root / minecraft:worldgen/biome] are present in data pack: idas:",
        2,
    ),
    "RuntimeDistCleaner client class errors": (
        "[net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM]: Attempted to load class net/minecraft/client/multiplayer/ClientLevel for invalid dist DEDICATED_SERVER",
        12,
    ),
    "Moonlight Fabric API detection error": (
        "Fabric API detected! This is not a Fabric mod",
        1,
    ),
    "Fabric overlay metadata error": (
        "Couldn't load fabric:overlays metadata",
        1,
    ),
}


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing override {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def find_jar(name_fragment: str) -> Path:
    matches = sorted(
        path for path in MODS_DIR.glob("*.jar") if name_fragment.lower() in path.name.lower()
    )
    if len(matches) != 1:
        raise AssertionError(
            f"expected one jar containing {name_fragment!r}, found {[path.name for path in matches]}"
        )
    return matches[0]


def load_jar_json(name_fragment: str, resource: str) -> dict:
    with zipfile.ZipFile(find_jar(name_fragment)) as jar:
        return json.loads(jar.read(resource))


def override_path(resource: str) -> Path:
    return KUBEJS_DATA / resource.removeprefix("data/")


class ReviewedConfigFixtureTests(unittest.TestCase):
    def test_only_reviewed_generated_configs_are_tracked_with_exact_values(self) -> None:
        config_root = ROOT / "config"
        for relative_path, expected_hash in CONFIG_HASHES.items():
            with self.subTest(config=relative_path):
                config_path = config_root / relative_path
                self.assertTrue(config_path.is_file(), f"missing reviewed config {relative_path}")
                normalized = config_path.read_bytes().removesuffix(b"\n")
                actual_hash = hashlib.sha256(normalized).hexdigest()
                self.assertEqual(actual_hash, expected_hash)

    def test_quark_spawn_modules_stay_enabled_with_empty_whitelists(self) -> None:
        config_path = ROOT / "config" / "quark-common.toml"
        self.assertTrue(config_path.is_file(), "missing reviewed Quark config")
        text = config_path.read_text(encoding="utf-8")
        for module in ("Foxhound", "Stonelings", "Toretoise"):
            self.assertIn(f"\t{module} = true", text)

        for section in (
            "mobs.foxhound.spawn_config",
            "mobs.foxhound.lesser_spawn_config",
            "mobs.stonelings.spawn_config",
            "mobs.toretoise.spawn_config",
        ):
            with self.subTest(section=section):
                tags = (
                    f"\t\t\t\t[{section}.biomes.tags]\n"
                    '\t\t\t\t\t"Biome Tags" = []\n'
                    '\t\t\t\t\t"Is Blacklist" = false'
                )
                biomes = (
                    f"\t\t\t\t[{section}.biomes.biomes]\n"
                    "\t\t\t\t\tBiomes = []\n"
                    '\t\t\t\t\t"Is Blacklist" = false'
                )
                self.assertIn(tags, text)
                self.assertIn(biomes, text)

    def test_alexs_mobs_disables_only_skreecher_spawning(self) -> None:
        config_path = ROOT / "config" / "alexsmobs-common.toml"
        self.assertTrue(config_path.is_file(), "missing reviewed Alex's Mobs config")
        text = config_path.read_text(encoding="utf-8")
        self.assertEqual(text.count("\tskreecherSpawnWeight = 0"), 1)
        self.assertEqual(text.count("\tskreecherSpawnRolls = 1"), 1)


class JarOverrideFixtureTests(unittest.TestCase):
    def test_oritech_turbofuel_changes_only_fluid_ingredient_serializer(self) -> None:
        resource = "data/oritech/recipe/mixing/compat/create/turbofuel.json"
        source = load_jar_json("oritech-neoforge", resource)
        expected = copy.deepcopy(source)
        expected["ingredients"][1]["type"] = "neoforge:single"
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_industrial_foregoing_removes_only_invalid_curios_slot(self) -> None:
        resource = "data/industrialforegoing/curios/entities/entities.json"
        source = load_jar_json("industrialforegoing", resource)
        expected = copy.deepcopy(source)
        expected["slots"].remove("example")
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cataclysm_defines_only_the_two_missing_empty_block_tags(self) -> None:
        jar = find_jar("L_Ender's Cataclysm")
        with zipfile.ZipFile(jar) as archive:
            resources = set(archive.namelist())
        for tag_name in ("needs_black_steel_tool", "needs_monstrosity_tool"):
            resource = f"data/cataclysm/tags/block/{tag_name}.json"
            with self.subTest(tag=tag_name):
                self.assertNotIn(resource, resources)
                self.assertEqual(load_json(override_path(resource)), {"replace": False, "values": []})

    def test_advancements_change_only_the_approved_parent(self) -> None:
        fixtures = (
            (
                "dungeons-and-taverns",
                "data/minecraft/advancement/wander_add_map.json",
                "nova_structures:root",
            ),
            (
                "dungeons-and-taverns",
                "data/minecraft/advancement/give_quest_trader_trade.json",
                "nova_structures:root",
            ),
            (
                "DungeonsArise",
                "data/dungeons_arise/advancement/find_fishing_hut.json",
                "dungeons_arise:wda_root",
            ),
            (
                "DungeonsArise",
                "data/dungeons_arise/advancement/find_thornborn_towers.json",
                "dungeons_arise:wda_root",
            ),
        )
        for jar_name, resource, parent in fixtures:
            with self.subTest(resource=resource):
                source = load_jar_json(jar_name, resource)
                expected = copy.deepcopy(source)
                expected["parent"] = parent
                self.assertEqual(load_json(override_path(resource)), expected)

    def test_malum_repairs_follow_the_installed_schema_only(self) -> None:
        for relative_name, selector_type in MALUM_SPIRIT_REPAIRS.items():
            resource = f"data/malum/recipe/malum/spirit_repair/{relative_name}.json"
            with self.subTest(recipe=relative_name):
                source = load_jar_json("malum-", resource)
                expected = copy.deepcopy(source)

                if selector_type == "valid_items" and "inputs" in expected:
                    expected["validItems"] = expected.pop("inputs")
                if relative_name == "undergarden/forgotten":
                    expected.pop("inputs")
                    expected["regex"] = {
                        "itemIdRegex": expected.pop("itemIdRegex"),
                        "modIdRegex": expected.pop("modIdRegex"),
                    }
                if relative_name == "undergarden/utherium":
                    expected.pop("inputs")
                if selector_type == "regex":
                    expected["validItems"] = MALUM_REGEX_VALID_ITEMS[relative_name]

                for spirit in expected["spirits"]:
                    if ":" not in spirit["type"]:
                        spirit["type"] = f"malum:{spirit['type']}"

                actual = load_json(override_path(resource))
                self.assertEqual(actual, expected)
                self.assertNotIn("inputs", actual)
                if selector_type == "valid_items":
                    self.assertIn("validItems", actual)
                else:
                    self.assertIn("regex", actual)

    def test_malum_grim_talc_changes_only_create_result_keys(self) -> None:
        resource = "data/malum/recipe/create/milling/grim_talc.json"
        source = load_jar_json("malum-", resource)
        expected = copy.deepcopy(source)
        for result in expected["results"]:
            result["id"] = result.pop("item")
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cei_experience_map_preserves_every_value_except_enderio_id(self) -> None:
        resource = "data/create_enchantment_industry/data_maps/fluid/unit/experience.json"
        source = load_jar_json("create-enchantment-industry", resource)
        expected = copy.deepcopy(source)
        expected["replace"] = True
        expected["remove"] = ["enderio:xpjuice"]
        expected["values"]["enderio:xp_juice"] = expected["values"].pop("enderio:xpjuice")
        self.assertEqual(expected["values"]["enderio:xp_juice"]["neoforge:value"], 20)
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cei_filter_pack_blocks_only_the_stale_lower_resource(self) -> None:
        with zipfile.ZipFile(CEI_FILTER_PACK) as archive:
            self.assertEqual(archive.namelist(), ["pack.mcmeta"])
            metadata = json.loads(archive.read("pack.mcmeta"))
        self.assertEqual(
            metadata,
            {
                "pack": {
                    "description": "AFTERLIGHT RC hygiene resource filter",
                    "pack_format": 48,
                },
                "filter": {
                    "block": [
                        {
                            "namespace": "create_enchantment_industry",
                            "path": "data_maps/fluid/unit/experience\\.json",
                        }
                    ]
                },
            },
        )

    def test_invalid_block_loot_tables_are_replaced_with_empty_block_tables(self) -> None:
        fixtures = [
            (
                "create_connected",
                f"data/create_connected/loot_table/blocks/dye_depot_{color}_fan_dyeing_catalyst.json",
            )
            for color in DYE_DEPOT_COLORS
        ]
        fixtures.append(
            ("ExtendedAE", "data/extendedae/loot_table/blocks/ex_emc_interface.json")
        )
        for jar_name, resource in fixtures:
            with self.subTest(resource=resource):
                source = load_jar_json(jar_name, resource)
                self.assertNotEqual(source.get("pools"), [])
                self.assertEqual(
                    load_json(override_path(resource)),
                    {"type": "minecraft:block", "pools": []},
                )

    def test_invalid_irons_spellbooks_test_loot_is_replaced_with_empty_table(self) -> None:
        resource = "data/irons_spellbooks/loot_table/test/ring_gen_break_me.json"
        source = load_jar_json("irons_spellbooks", resource)
        self.assertNotEqual(source.get("pools"), [])
        self.assertEqual(load_json(override_path(resource)), {"pools": []})

    def test_idas_optional_biomes_keep_ids_but_become_non_required(self) -> None:
        tag_names = (
            "byg_redwood_biomes",
            "bygmohogany_biomes",
            "bopredwood_biomes",
            "bopmohogany_biomes",
        )
        for tag_name in tag_names:
            resource = f"data/idas/tags/worldgen/biome/has_structure/{tag_name}.json"
            with self.subTest(tag=tag_name):
                source = load_jar_json("idas-", resource)
                expected = copy.deepcopy(source)
                expected["replace"] = True
                expected["values"] = [
                    {"id": biome_id, "required": False} for biome_id in source["values"]
                ]
                self.assertEqual(load_json(override_path(resource)), expected)

    def test_no_idas_structure_nbt_is_redistributed(self) -> None:
        idas_root = KUBEJS_DATA / "idas"
        nbt_files = list(idas_root.rglob("*.nbt")) if idas_root.exists() else []
        self.assertEqual(nbt_files, [])


class ModMetadataFixtureTests(unittest.TestCase):
    def test_terralith_is_pinned_to_reviewed_262_artifact(self) -> None:
        metadata = tomllib.loads((ROOT / "mods" / "terralith.pw.toml").read_text())
        self.assertEqual(metadata["filename"], "Terralith_1.21.1_v2.6.2_Neoforge.jar")
        self.assertEqual(metadata["side"], "both")
        self.assertEqual(metadata["download"]["hash-format"], "sha512")
        self.assertEqual(
            metadata["download"]["hash"],
            "35298f1682567f63dc16658b04cee5498b30819f1c05f9712b4480d7f5eb17059db3b13ab14f81a05fe257149d11ced2cce2030d3727c1747edd8657c53e2a85",
        )
        self.assertEqual(metadata["update"]["modrinth"]["version"], "IY93YaEe")

    def test_lithostitched_is_installed_on_both_sides(self) -> None:
        metadata = tomllib.loads((ROOT / "mods" / "lithostitched.pw.toml").read_text())
        self.assertEqual(metadata["side"], "both")


class CleanBootSignatureFixtureTests(unittest.TestCase):
    def test_clean_boot_has_no_repaired_signatures_and_exact_known_residuals(self) -> None:
        log_text = LATEST_LOG.read_text(encoding="utf-8", errors="replace")
        self.assertIn("Done (", log_text)

        for signature in REPAIRED_LOG_SIGNATURES:
            with self.subTest(repaired_signature=signature):
                self.assertEqual(log_text.count(signature), 0)

        for label, (signature, expected_count) in KNOWN_RESIDUALS.items():
            with self.subTest(residual=label):
                self.assertEqual(log_text.count(signature), expected_count)


if __name__ == "__main__":
    unittest.main(verbosity=2)
