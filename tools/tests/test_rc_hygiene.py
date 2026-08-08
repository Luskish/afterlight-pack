from __future__ import annotations

import copy
import gzip
import hashlib
import json
import re
import struct
import sys
import tomllib
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import rc_hygiene


KUBEJS_DATA = ROOT / "kubejs" / "data"
INSTALL_ROOT = ROOT / "server-test"
LATEST_LOG = ROOT / "server-test" / "logs" / "latest.log"
CEI_FILTER_PACK = KUBEJS_DATA / "afterlight_rc_hygiene.zip"
CONFIG_FIXTURE = ROOT / "tools" / "fixtures" / "rc-hygiene" / "generated-configs.json"

SOURCE_METADATA = {
    "oritech": "mods/oritech.pw.toml",
    "industrial_foregoing": "mods/industrial-foregoing.pw.toml",
    "cataclysm": "mods/l_enders-cataclysm.pw.toml",
    "dungeons_and_taverns": "mods/dungeons-and-taverns.pw.toml",
    "dungeons_arise": "mods/when-dungeons-arise.pw.toml",
    "malum": "mods/malum.pw.toml",
    "cei": "mods/create-enchantment-industry.pw.toml",
    "create_connected": "mods/create-connected.pw.toml",
    "extendedae": "mods/ex-pattern-provider.pw.toml",
    "irons_spellbooks": "mods/irons-spells-n-spellbooks.pw.toml",
    "idas": "mods/idas.pw.toml",
    "idas_compat": "mods/afterlight-idas-compat.pw.toml",
    "terralith": "mods/terralith.pw.toml",
    "lithostitched": "mods/lithostitched.pw.toml",
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
    "Object with ID enderio:xp_juice specified in data map",
    "Object with ID enderio:fluid_xp_juice_still specified in data map",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:create_connected:blocks/dye_depot_",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:extendedae:blocks/ex_emc_interface",
    "Couldn't parse element ResourceKey[minecraft:root / minecraft:loot_table]:irons_spellbooks:test/ring_gen_break_me",
    "Couldn't load tag idas:has_structure/byg_redwood_biomes",
    "Couldn't load tag idas:has_structure/bygmohogany_biomes",
    "Couldn't load tag idas:has_structure/bopredwood_biomes",
    "Couldn't load tag idas:has_structure/bopmohogany_biomes",
    "Couldn't load tag idas:has_structure/bygredwood_biomes",
    "Couldn't load tag idas:has_structure/bygmahogany_biomes",
    "Couldn't load tag idas:has_structure/bopmahogany_biomes",
    "Not all defined tags for registry ResourceKey[minecraft:root / minecraft:worldgen/biome] are present in data pack: idas:",
    "Detected quark:stoneling that was registered with CREATURE mob category",
    "Detected quark:toretoise that was registered with CREATURE mob category",
    "Detected quark:foxhound that was registered with CREATURE mob category",
    "Detected alexsmobs:skreecher that was registered with CREATURE mob category",
    "Detected minecraft:axolotl that was registered with AXOLOTLS mob category but was added under UNDERGROUND_WATER_CREATURE mob category for terralith:",
)


def load_json(path: Path) -> dict:
    if not path.is_file():
        raise AssertionError(f"missing override {path.relative_to(ROOT)}")
    return json.loads(path.read_text(encoding="utf-8"))


def source_jar(source: str) -> Path:
    return rc_hygiene.resolve_source_jar(
        ROOT, INSTALL_ROOT, SOURCE_METADATA[source]
    )


def load_jar_json(source: str, resource: str) -> dict:
    with zipfile.ZipFile(source_jar(source)) as jar:
        return json.loads(jar.read(resource))


def override_path(resource: str) -> Path:
    return KUBEJS_DATA / resource.removeprefix("data/")


class NbtReader:
    def __init__(self, payload: bytes):
        self.payload = memoryview(payload)
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.payload):
            raise AssertionError("truncated NBT fixture")
        value = self.payload[self.offset:end].tobytes()
        self.offset = end
        return value

    def unpack(self, format_string: str):
        size = struct.calcsize(format_string)
        return struct.unpack(format_string, self.read(size))[0]

    def string(self) -> str:
        length = self.unpack(">H")
        return self.read(length).decode("utf-8")

    def payload_value(self, tag_type: int):
        if tag_type == 1:
            return self.unpack(">b")
        if tag_type == 2:
            return self.unpack(">h")
        if tag_type == 3:
            return self.unpack(">i")
        if tag_type == 4:
            return self.unpack(">q")
        if tag_type == 5:
            return self.unpack(">f")
        if tag_type == 6:
            return self.unpack(">d")
        if tag_type == 7:
            return self.read(self.unpack(">i"))
        if tag_type == 8:
            return self.string()
        if tag_type == 9:
            element_type = self.unpack(">B")
            return [self.payload_value(element_type) for _ in range(self.unpack(">i"))]
        if tag_type == 10:
            compound = {}
            while True:
                child_type = self.unpack(">B")
                if child_type == 0:
                    return compound
                child_name = self.string()
                compound[child_name] = self.payload_value(child_type)
        if tag_type == 11:
            return [self.unpack(">i") for _ in range(self.unpack(">i"))]
        if tag_type == 12:
            return [self.unpack(">q") for _ in range(self.unpack(">i"))]
        raise AssertionError(f"unsupported NBT tag type {tag_type}")


def parse_nbt(payload: bytes):
    if payload.startswith(b"\x1f\x8b"):
        payload = gzip.decompress(payload)
    reader = NbtReader(payload)
    root_type = reader.unpack(">B")
    if root_type != 10:
        raise AssertionError(f"expected compound NBT root, got {root_type}")
    reader.string()
    result = reader.payload_value(root_type)
    if reader.offset != len(reader.payload):
        raise AssertionError("unparsed NBT fixture bytes")
    return result


def air_item_paths(value, path=()):
    matches = []
    if isinstance(value, dict):
        if value.get("id") == "minecraft:air":
            matches.append(path)
        for key, child in value.items():
            matches.extend(air_item_paths(child, path + (str(key),)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            matches.extend(air_item_paths(child, path + (str(index),)))
    return matches


class ReviewedConfigFixtureTests(unittest.TestCase):
    def test_reviewed_configs_reverse_to_clean_generated_fingerprints(self) -> None:
        config_root = ROOT / "config"
        fixture = load_json(CONFIG_FIXTURE)
        self.assertEqual(
            fixture["evidence"],
            "Clean server generation on 2026-08-08 with the reviewed files absent",
        )
        self.assertEqual(
            fixture["normalization"], "Remove one final LF before SHA-256"
        )
        for relative_path, evidence in fixture["configs"].items():
            with self.subTest(config=relative_path):
                config_path = config_root / relative_path
                self.assertTrue(config_path.is_file(), f"missing reviewed config {relative_path}")
                reconstructed = config_path.read_text(encoding="utf-8")
                for replacement in evidence["reverse_replacements"]:
                    reviewed = replacement["reviewed"]
                    generated = replacement["generated"]
                    self.assertEqual(
                        reconstructed.count(reviewed),
                        1,
                        f"approved config edit is not unique in {relative_path}",
                    )
                    reconstructed = reconstructed.replace(reviewed, generated, 1)
                normalized = reconstructed.encode().removesuffix(b"\n")
                self.assertEqual(
                    hashlib.sha256(normalized).hexdigest(),
                    evidence["generated_sha256"],
                )

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
        source = load_jar_json("oritech", resource)
        expected = copy.deepcopy(source)
        expected["ingredients"][1]["type"] = "neoforge:single"
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_industrial_foregoing_removes_only_invalid_curios_slot(self) -> None:
        resource = "data/industrialforegoing/curios/entities/entities.json"
        source = load_jar_json("industrial_foregoing", resource)
        expected = copy.deepcopy(source)
        expected["slots"].remove("example")
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cataclysm_defines_only_the_two_missing_empty_block_tags(self) -> None:
        jar = source_jar("cataclysm")
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
                "dungeons_and_taverns",
                "data/minecraft/advancement/wander_add_map.json",
                "nova_structures:root",
            ),
            (
                "dungeons_and_taverns",
                "data/minecraft/advancement/give_quest_trader_trade.json",
                "nova_structures:root",
            ),
            (
                "dungeons_arise",
                "data/dungeons_arise/advancement/find_fishing_hut.json",
                "dungeons_arise:wda_root",
            ),
            (
                "dungeons_arise",
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
                source = load_jar_json("malum", resource)
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
        source = load_jar_json("malum", resource)
        expected = copy.deepcopy(source)
        for result in expected["results"]:
            result["id"] = result.pop("item")
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cei_experience_map_preserves_every_value_except_enderio_id(self) -> None:
        resource = "data/create_enchantment_industry/data_maps/fluid/unit/experience.json"
        source = load_jar_json("cei", resource)
        expected = copy.deepcopy(source)
        expected["replace"] = True
        expected["remove"] = ["enderio:xpjuice"]
        expected["values"]["enderio:fluid_xp_juice_still"] = expected["values"].pop(
            "enderio:xpjuice"
        )
        replacement = expected["values"]["enderio:fluid_xp_juice_still"]
        self.assertEqual(replacement["neoforge:value"], 20)
        self.assertEqual(
            replacement["neoforge:conditions"],
            [{"type": "neoforge:mod_loaded", "modid": "enderio"}],
        )
        self.assertEqual(load_json(override_path(resource)), expected)

    def test_cei_filter_pack_blocks_only_the_stale_lower_resource(self) -> None:
        archive_bytes = CEI_FILTER_PACK.read_bytes()
        self.assertEqual(archive_bytes, rc_hygiene.build_filter_archive())
        self.assertEqual(
            hashlib.sha256(archive_bytes).hexdigest(),
            "414a79bb450bdfb11fb18e51808c7baba2d87c0197d938ed82c7442b94746262",
        )
        with zipfile.ZipFile(CEI_FILTER_PACK) as archive:
            self.assertEqual(archive.namelist(), ["pack.mcmeta"])
            info = archive.getinfo("pack.mcmeta")
            self.assertEqual(info.date_time, (1980, 1, 1, 0, 0, 0))
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            self.assertEqual(info.create_system, 3)
            self.assertEqual(info.external_attr >> 16, 0o100644)
            self.assertEqual(info.extra, b"")
            self.assertEqual(info.comment, b"")
            self.assertEqual(archive.comment, b"")
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
                            "namespace": "^create_enchantment_industry$",
                            "path": "^data_maps/fluid/unit/experience\\.json$",
                        }
                    ]
                },
            },
        )
        block = metadata["filter"]["block"][0]
        provenance = rc_hygiene.verify_install_provenance(ROOT, INSTALL_ROOT)
        metadata_paths = sorted(
            relative
            for relative, cached in provenance["cachedFiles"].items()
            if relative.endswith(".pw.toml")
            and cached.get("optionValue") is True
            and cached.get("onlyOtherSide") is not True
        )
        artifacts = rc_hygiene.resolve_source_jars(
            ROOT, INSTALL_ROOT, metadata_paths
        )
        blocked = []
        for metadata_path, artifact in artifacts.items():
            with zipfile.ZipFile(artifact) as archive:
                for resource in archive.namelist():
                    match = re.fullmatch(r"data/([^/]+)/(.+)", resource)
                    if match and rc_hygiene.filter_matches(
                        block["namespace"],
                        block["path"],
                        match.group(1),
                        match.group(2),
                    ):
                        blocked.append((metadata_path, artifact.name, resource))
        self.assertEqual(
            blocked,
            [
                (
                    "mods/create-enchantment-industry.pw.toml",
                    "create-enchantment-industry-2.5.1.jar",
                    "data/create_enchantment_industry/data_maps/fluid/unit/experience.json",
                )
            ],
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
            ("extendedae", "data/extendedae/loot_table/blocks/ex_emc_interface.json")
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
                source = load_jar_json("idas", resource)
                expected = copy.deepcopy(source)
                expected["replace"] = True
                expected["values"] = [
                    {"id": biome_id, "required": False} for biome_id in source["values"]
                ]
                self.assertEqual(load_json(override_path(resource)), expected)

    def test_every_idas_structure_biome_tag_resolves_to_source_or_exact_empty_override(self) -> None:
        jar = source_jar("idas")
        with zipfile.ZipFile(jar) as archive:
            resources = set(archive.namelist())
            references = set()
            for resource in resources:
                if not resource.startswith("data/idas/worldgen/structure/") or not resource.endswith(
                    ".json"
                ):
                    continue
                biomes = json.loads(archive.read(resource)).get("biomes")
                if isinstance(biomes, str) and biomes.startswith("#idas:"):
                    references.add(biomes.removeprefix("#idas:"))

        missing_source_tags = {
            tag
            for tag in references
            if f"data/idas/tags/worldgen/biome/{tag}.json" not in resources
        }
        self.assertEqual(
            missing_source_tags,
            {
                "has_structure/bygredwood_biomes",
                "has_structure/bygmahogany_biomes",
                "has_structure/bopmahogany_biomes",
            },
        )
        for tag in missing_source_tags:
            with self.subTest(tag=tag):
                resource = f"data/idas/tags/worldgen/biome/{tag}.json"
                self.assertEqual(
                    load_json(override_path(resource)),
                    {"replace": True, "values": []},
                )
        unresolved = {
            tag
            for tag in references
            if f"data/idas/tags/worldgen/biome/{tag}.json" not in resources
            and not override_path(
                f"data/idas/tags/worldgen/biome/{tag}.json"
            ).is_file()
        }
        self.assertEqual(unresolved, set())

    def test_no_idas_structure_nbt_is_redistributed(self) -> None:
        idas_root = KUBEJS_DATA / "idas"
        nbt_files = list(idas_root.rglob("*.nbt")) if idas_root.exists() else []
        self.assertEqual(nbt_files, [])

    def test_idas_camp1_has_the_two_reviewed_sanitizer_candidates(self) -> None:
        resource = "data/idas/structure/underground_camp/underground_camp1.nbt"
        with zipfile.ZipFile(source_jar("idas")) as archive:
            payload = archive.read(resource)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "0d7ecc5059d0d94d8cde9621d5358df1a9b89bf7dc27e93fd564668064aceb8a",
        )
        paths = air_item_paths(parse_nbt(payload))
        self.assertEqual(
            paths,
            [
                ("blocks", "92", "nbt", "Filter"),
                ("blocks", "95", "nbt", "Inventory", "Compartments", "0"),
            ],
        )

    def test_sable_source_is_authenticated_and_exhaustive(self) -> None:
        evidence = rc_hygiene.verify_sable_source_evidence(ROOT, INSTALL_ROOT)
        self.assertEqual(
            evidence["artifact_sha256"],
            "da6c3b66238586603d1dcaa2afb012d36815fbce0a2d5938fbb2936701d42279",
        )
        self.assertEqual(
            evidence["mixin_config_sha256"],
            "02dd86d2bd0ed6bef4841b1ae4ac8579edeb33fe0134f2060191b49102c4878d",
        )
        self.assertEqual(evidence["enabled_metadata"], 158)
        self.assertEqual(evidence["top_level_artifacts"], 157)
        self.assertEqual(evidence["archive_scopes"], 305)
        self.assertEqual(evidence["mixin_configs"], 255)
        self.assertEqual(evidence["common_mixins"], 2258)
        self.assertEqual(evidence["direct_clientlevel_mixins"], 10)
        self.assertEqual(len(evidence["pseudo_clientlevel_candidates"]), 3)
        self.assertEqual(
            tuple(candidate[2] for candidate in evidence["pseudo_clientlevel_candidates"]),
            tuple(rc_hygiene.SABLE_MIXIN_CLASSES),
        )

    def test_idas_compat_release_is_source_authenticated_and_data_free(self) -> None:
        evidence = rc_hygiene.verify_idas_compat_source_evidence(ROOT, INSTALL_ROOT)
        self.assertEqual(
            evidence["artifact_sha256"],
            "458bbaeb5d93923d24b18d69ed7f60dbf3bab9854d50a02671f6ecb7a0338b1b",
        )
        self.assertEqual(
            evidence["artifact_sha512"],
            "26a490e6f4e2bde870ada10325dc8f7cad2774b96fa1c35e11a709010de50d126e0ffb33853a8b5f8fcfa1ced28e2d377b7603ddae056c634e959b760be82c54",
        )
        self.assertEqual(source_jar("idas_compat").name, rc_hygiene.IDAS_COMPAT_FILENAME)


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
        self.assertEqual(
            source_jar("terralith").name,
            "Terralith_1.21.1_v2.6.2_Neoforge.jar",
        )

    def test_lithostitched_is_installed_on_both_sides(self) -> None:
        metadata = tomllib.loads((ROOT / "mods" / "lithostitched.pw.toml").read_text())
        self.assertEqual(metadata["side"], "both")
        self.assertEqual(source_jar("lithostitched").name, metadata["filename"])


class JdtLifecycleFixtureTests(unittest.TestCase):
    def test_warning_allowance_is_bound_to_reviewed_bytecode_and_runtime(self) -> None:
        rc_hygiene.verify_jdt_evidence(ROOT, INSTALL_ROOT)

    def test_no_broad_disable_or_custom_compensation_is_shipped(self) -> None:
        supplementaries_config = (
            INSTALL_ROOT / "config" / "supplementaries-common.toml"
        ).read_text(encoding="utf-8")
        self.assertEqual(supplementaries_config.count("\tpancake = true"), 1)
        self.assertEqual(supplementaries_config.count("\tdispensers = true"), 1)
        scripts = "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in (ROOT / "kubejs").rglob("*.js")
        )
        self.assertNotIn("justdirethings:fuel_canister", scripts)
        self.assertNotIn("registerBehavior", scripts)
        self.assertEqual(list((ROOT / "mods").glob("*.jar")), [])


class CleanBootSignatureFixtureTests(unittest.TestCase):
    def test_clean_boot_has_no_repaired_signatures_and_exact_known_residuals(self) -> None:
        log_text = LATEST_LOG.read_text(encoding="utf-8", errors="replace")
        nonce = (INSTALL_ROOT / "afterlight-audit-nonce.txt").read_text(
            encoding="utf-8"
        ).strip()
        status_text = (INSTALL_ROOT / "afterlight-server-exit-status.txt").read_text(
            encoding="utf-8"
        ).strip()
        self.assertRegex(status_text, r"^\d+$")
        result = rc_hygiene.verify_boot_run(
            ROOT, INSTALL_ROOT, nonce, int(status_text)
        )

        for signature in REPAIRED_LOG_SIGNATURES:
            with self.subTest(repaired_signature=signature):
                self.assertEqual(log_text.count(signature), 0)

        self.assertEqual(
            result["errors"],
            {
                "Moonlight Fabric API detection error": 1,
                "Fabric overlay metadata error": 1,
                "RuntimeDistCleaner Sable ClientLevel errors": 12,
            },
        )
        self.assertEqual(
            result["audits"],
            {
                "IDAS compat READY": 1,
                "IDAS camp1 sanitized": 1,
                "IDAS sanitized templates": 4,
            },
        )
        warnings = result["warnings"]
        self.assertEqual(
            sum(count for label, count in warnings.items() if label.startswith("Kaleidoscope carrier ")),
            27,
        )
        self.assertEqual(warnings["Incendium smithing fallback"], 1)
        self.assertEqual(
            sum(
                count
                for label, count in warnings.items()
                if label.startswith("EnderIO Malum inheritance ")
            ),
            9,
        )
        self.assertEqual(warnings["Apothic Enchanting stale data map type"], 1)
        self.assertEqual(
            warnings["Just Dire Things early pancake candidate scan"], 1
        )
        self.assertEqual(sum(warnings.values()), 39)


if __name__ == "__main__":
    unittest.main(verbosity=2)
