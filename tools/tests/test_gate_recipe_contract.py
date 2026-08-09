from __future__ import annotations

import ast
import re
import unittest
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPT_ROOT = ROOT / "kubejs" / "server_scripts" / "afterlight"


COMPONENTS = (
    (
        "kubejs:gate/component/kinetic_frame",
        "AFTERLIGHT.GATE_KINETIC",
        {
            "A": "create:precision_mechanism",
            "B": "create:sturdy_sheet",
            "C": "create:brass_sheet",
            "D": "create:electron_tube",
            "E": "create:railway_casing",
            "F": "create:mechanical_crafter",
            "S": "kubejs:schematic_kinetic_frame",
        },
    ),
    (
        "kubejs:gate/component/industrial_anchor",
        "AFTERLIGHT.GATE_INDUSTRIAL",
        {
            "A": "immersiveengineering:heavy_engineering",
            "B": "immersiveengineering:component_electronic_adv",
            "C": "immersiveengineering:component_steel",
            "D": "immersiveengineering:capacitor_hv",
            "E": "immersiveengineering:radiator",
            "F": "immersiveengineering:wirecoil_electrum",
            "S": "kubejs:schematic_industrial_anchor",
        },
    ),
    (
        "kubejs:gate/component/isotopic_core",
        "AFTERLIGHT.GATE_ISOTOPIC",
        {
            "A": "mekanism:alloy_atomic",
            "B": "mekanism:ultimate_control_circuit",
            "C": "mekanism:hdpe_sheet",
            "D": "mekanism:pellet_polonium",
            "E": "mekanism:pellet_plutonium",
            "F": "mekanism:pellet_antimatter",
            "S": "kubejs:schematic_isotopic_core",
        },
    ),
    (
        "kubejs:gate/component/lattice_matrix",
        "AFTERLIGHT.GATE_LATTICE",
        {
            "A": "ae2:logic_processor",
            "B": "ae2:calculation_processor",
            "C": "ae2:engineering_processor",
            "D": "ae2:cell_component_256k",
            "E": "ae2:dense_energy_cell",
            "F": "ae2:quantum_entangled_singularity",
            "S": "kubejs:schematic_lattice_matrix",
        },
    ),
)

STABILIZERS = (
    ("kubejs:gate/stabilizer/occultism", "occultism:spirit_attuned_gem"),
    ("kubejs:gate/stabilizer/irons_spellbooks", "irons_spellbooks:magic_cloth"),
    ("kubejs:gate/stabilizer/malum", "malum:soul_stained_steel_ingot"),
)

DRACONIC = (
    (
        "draconicevolution:components/draconium_core",
        "kubejs:gated/draconium_core",
        "draconicevolution:draconium_core",
        ("ABA", "BCB", "AZA"),
        {
            "A": "#c:ingots/draconium",
            "B": "#c:ingots/gold",
            "C": "#c:gems/diamond",
        },
    ),
    (
        "draconicevolution:tools/dislocator",
        "kubejs:gated/dislocator",
        "draconicevolution:dislocator",
        ("ABA", "BCB", "AZA"),
        {
            "A": "minecraft:blaze_powder",
            "B": "#c:dusts/draconium",
            "C": "minecraft:ender_eye",
        },
    ),
    (
        "draconicevolution:modules/module_core",
        "kubejs:gated/module_core",
        "draconicevolution:module_core",
        ("IRI", "GDG", "IZI"),
        {
            "D": "#c:ingots/draconium",
            "G": "#c:ingots/gold",
            "I": "#c:ingots/iron",
            "R": "#c:dusts/redstone",
        },
    ),
)

GATE_RECIPE_SCRIPTS = (
    "gate_components.js",
    "gate_assembly.js",
    "gate_draconic.js",
)

APPROVED_GATE_RECIPE_IDS = frozenset(
    {
        "kubejs:gate/component/kinetic_frame",
        "kubejs:gate/component/industrial_anchor",
        "kubejs:gate/component/isotopic_core",
        "kubejs:gate/component/lattice_matrix",
        "kubejs:gate/stabilizer/occultism",
        "kubejs:gate/stabilizer/irons_spellbooks",
        "kubejs:gate/stabilizer/malum",
        "kubejs:gate/gate_of_return_core",
        "kubejs:gated/draconium_core",
        "kubejs:gated/dislocator",
        "kubejs:gated/module_core",
    }
)

APPROVED_EVENT_CALL_COUNTS = Counter(
    {
        "recipes.create.mechanical_crafting": 5,
        "shapeless": 3,
        "shaped": 3,
        "remove": 3,
    }
)

APPROVED_PRODUCER_COUNTS = {
    "kubejs:gate_kinetic_frame": 1,
    "kubejs:gate_industrial_anchor": 1,
    "kubejs:gate_isotopic_core": 1,
    "kubejs:gate_lattice_matrix": 1,
    "kubejs:undercurrent_stabilizer": 3,
    "kubejs:gate_of_return_core": 1,
    "draconicevolution:draconium_core": 1,
    "draconicevolution:dislocator": 1,
    "draconicevolution:module_core": 1,
}

RECIPE_ID_PATTERN = re.compile(r"\.id\s*\(\s*(['\"])([^'\"]+)\1\s*\)")
EVENT_CALL_PATTERN = re.compile(
    r"\bevent\.(recipes\.create\.mechanical_crafting|shaped|shapeless|remove)\s*\("
)
ANY_EVENT_CALL_PATTERN = re.compile(r"\bevent\.([A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*)\s*\(")
PRODUCER_MAP_PATTERN = re.compile(
    r"\bconst\s+expectedProducerCount\s*=\s*(\{[^{}]*\})",
    re.DOTALL,
)

NON_KUBEJS_INPUTS = {
    item_id
    for _recipe_id, _output, keys in COMPONENTS
    for key, item_id in keys.items()
    if key != "S"
} | {
    "create:iron_sheet",
    "pneumaticcraft:printed_circuit_board",
    "immersiveengineering:ingot_steel",
    *(item_id for _recipe_id, item_id in STABILIZERS),
}


def compact(source: str) -> str:
    return re.sub(r"\s+", "", source)


class GateRecipeContractTests(unittest.TestCase):
    def read_script(self, name: str) -> str:
        path = SCRIPT_ROOT / name
        self.assertTrue(path.is_file(), f"missing Task 2 script {path}")
        return path.read_text(encoding="utf-8")

    def assert_fragment(self, source: str, fragment: str) -> None:
        self.assertIn(compact(fragment), compact(source))

    def test_registration_has_exact_eleven_test_owned_recipe_ids(self) -> None:
        sources = {
            name: self.read_script(name)
            for name in GATE_RECIPE_SCRIPTS
        }
        recipe_ids = [
            match.group(2)
            for source in sources.values()
            for match in RECIPE_ID_PATTERN.finditer(source)
        ]
        event_calls = Counter(
            match.group(1)
            for source in sources.values()
            for match in ANY_EVENT_CALL_PATTERN.finditer(source)
        )
        recognized_calls = Counter(
            match.group(1)
            for source in sources.values()
            for match in EVENT_CALL_PATTERN.finditer(source)
        )

        self.assertEqual(len(recipe_ids), 11)
        self.assertEqual(len(recipe_ids), len(set(recipe_ids)))
        self.assertEqual(frozenset(recipe_ids), APPROVED_GATE_RECIPE_IDS)
        self.assertEqual(event_calls, APPROVED_EVENT_CALL_COUNTS)
        self.assertEqual(recognized_calls, APPROVED_EVENT_CALL_COUNTS)

    def test_audit_producer_cardinality_matches_test_owned_map(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        declarations = list(PRODUCER_MAP_PATTERN.finditer(source))
        self.assertEqual(len(declarations), 1)
        expression = ast.parse(declarations[0].group(1), mode="eval").body
        self.assertIsInstance(expression, ast.Dict)
        keys = [ast.literal_eval(key) for key in expression.keys]
        values = [ast.literal_eval(value) for value in expression.values]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(dict(zip(keys, values)), APPROVED_PRODUCER_COUNTS)

    def test_four_component_recipes_are_exact_and_asymmetric(self) -> None:
        source = self.read_script("gate_components.js")
        self.assertEqual(source.count("event.recipes.create.mechanical_crafting("), 4)
        self.assertEqual(source.count(".acceptMirrored(false)"), 4)
        self.assertEqual(source.count("['ABCDF', 'EFABC', 'DASBE', 'CDEFA', 'FBCDE']"), 4)
        for recipe_id, output, keys in COMPONENTS:
            with self.subTest(recipe_id=recipe_id):
                self.assertIn(f".id('{recipe_id}')", source)
                self.assertIn(output, source)
                for key, item_id in keys.items():
                    self.assertRegex(
                        source,
                        rf"\b{key}\s*:\s*'{re.escape(item_id)}'",
                    )

    def test_three_stabilizer_recipes_are_exact(self) -> None:
        source = self.read_script("gate_assembly.js")
        self.assertEqual(source.count("event.shapeless(AFTERLIGHT.STABILIZER"), 3)
        for recipe_id, branch_item in STABILIZERS:
            with self.subTest(recipe_id=recipe_id):
                self.assert_fragment(
                    source,
                    f"event.shapeless(AFTERLIGHT.STABILIZER, "
                    f"['kubejs:undercurrent_stabilizer_precursor', '{branch_item}'])"
                    f".id('{recipe_id}')",
                )

    def test_gate_core_recipe_is_exact_and_has_no_alternative(self) -> None:
        source = self.read_script("gate_assembly.js")
        pattern = (
            "['CCAAPPS', 'CC B AA', 'A PKS S', 'P IUO S', "
            "'A SLP P', 'CA   CS', 'SSPPACC']"
        )
        self.assert_fragment(
            source,
            "event.recipes.create.mechanical_crafting(AFTERLIGHT.GATE_CORE, "
            f"{pattern}, {{"
            "B: 'kubejs:gate_blueprint', K: AFTERLIGHT.GATE_KINETIC, "
            "I: AFTERLIGHT.GATE_INDUSTRIAL, O: AFTERLIGHT.GATE_ISOTOPIC, "
            "L: AFTERLIGHT.GATE_LATTICE, U: AFTERLIGHT.STABILIZER, "
            "C: 'create:iron_sheet', A: 'ae2:logic_processor', "
            "P: 'pneumaticcraft:printed_circuit_board', "
            "S: 'immersiveengineering:ingot_steel'"
            "}).acceptMirrored(false).id('kubejs:gate/gate_of_return_core')",
        )
        all_sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in sorted(SCRIPT_ROOT.glob("*.js"))
        )
        self.assertEqual(all_sources.count("kubejs:gate/gate_of_return_core"), 2)
        self.assertNotIn("modularmachinery", all_sources.lower())

    def test_draconic_replacements_use_exact_shaped_keep_contract(self) -> None:
        source = self.read_script("gate_draconic.js")
        self.assertNotIn("event.custom", source)
        self.assertEqual(source.count("event.shaped("), 3)
        self.assertEqual(
            source.count(".keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })"),
            3,
        )
        for original_id, recipe_id, output, pattern, keys in DRACONIC:
            with self.subTest(recipe_id=recipe_id):
                self.assertIn(f"event.remove({{ id: '{original_id}' }})", source)
                self.assertIn(f".id('{recipe_id}')", source)
                self.assertIn(f"event.shaped('{output}'", source)
                self.assertIn(repr(list(pattern)).replace('"', "'"), source)
                self.assertRegex(source, r"\bZ\s*:\s*AFTERLIGHT\.SEAL")
                for key, ingredient in keys.items():
                    self.assertRegex(
                        source,
                        rf"\b{key}\s*:\s*'{re.escape(ingredient)}'",
                    )

    def test_audit_has_exact_import_listener_helper_and_marker_contract(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        imports = (
            "const MechanicalCraftingInput = Java.loadClass('com.simibubi.create.content.kinetics.crafter.MechanicalCraftingInput')",
            "const GroupedItems = Java.loadClass('com.simibubi.create.content.kinetics.crafter.RecipeGridHandler$GroupedItems')",
            "const CraftingInput = Java.loadClass('net.minecraft.world.item.crafting.CraftingInput')",
            "const ItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')",
            "const ArrayList = Java.loadClass('java.util.ArrayList')",
            "const CompoundTag = Java.loadClass('net.minecraft.nbt.CompoundTag')",
            "const ListTag = Java.loadClass('net.minecraft.nbt.ListTag')",
            "const ResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')",
        )
        positions = [source.index(statement) for statement in imports]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("Java.loadClass("), len(imports))
        self.assertEqual(source.count("ServerEvents.loaded("), 1)
        helpers = (
            "afterlightRecipe",
            "afterlightMechanicalInput",
            "afterlightCraftingInput",
            "afterlightAssertMatch",
            "afterlightAssertNoMatch",
            "afterlightAssertOnlySealRemainder",
        )
        for helper in helpers:
            self.assertEqual(source.count(f"function {helper}("), 1)
        self.assertEqual(re.findall(r"\bfunction\s+(\w+)\(", source), list(helpers))
        self.assertEqual(source.count("__AFTERLIGHT_GATE_AUDIT_SHA256__"), 1)
        self.assertEqual(source.count("__AFTERLIGHT_GATE_BOOT_NONCE__"), 1)
        self.assertEqual(source.count("[AFTERLIGHT GATE RECIPE AUDIT] OK"), 1)

    def test_audit_uses_exact_input_construction_order(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        self.assertIn("entry.putInt('y', pattern.length - 1 - row)", source)
        mechanical_steps = (
            "root.put('Grid', grid)",
            "const grouped = GroupedItems.read(root, registries)",
            "grouped.calcStats()",
            "return MechanicalCraftingInput.of(grouped)",
        )
        positions = [source.index(step) for step in mechanical_steps]
        self.assertEqual(positions, sorted(positions))
        self.assertIn(
            "return CraftingInput.of(pattern[0].length, pattern.length, items)",
            source,
        )

    def test_audit_uses_rhino_safe_recipe_type_identity(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        self.assertNotIn(".getClass()", source)
        self.assertIn(
            "String(recipe).startsWith('com.simibubi.create.content.kinetics."
            "crafter.MechanicalCraftingRecipe@')",
            source,
        )

    def test_audit_uses_rhino_safe_loop_bindings(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        self.assertEqual(source.count("let character = pattern[row][column]"), 2)
        self.assertIn("let entry = new CompoundTag()", source)
        self.assertIn("let stack = Item.of(keys[character]).copy()", source)
        self.assertIn("let rotatedPattern = spec.pattern.slice()", source)
        self.assertIn("let nextRotation = []", source)
        self.assertNotIn("const nextRotation = []", source)
        self.assertIn("let deletedPattern = spec.pattern.slice()", source)
        self.assertIn("let replacedPattern = spec.pattern.slice()", source)
        self.assertIn("let insertedPattern = spec.pattern.slice()", source)
        self.assertIn("let insertedKeys = {}", source)
        self.assertNotIn("const insertedKeys = {}", source)
        self.assertIn("let wrongSlotPattern = spec.pattern.slice()", source)
        self.assertIn("let character = spec.pattern[row][column]", source)
        self.assertEqual(source.count("const changedKeys = {}"), 3)
        self.assertIn("let replacementKeys = {}", source)
        self.assertNotIn("const replacementKeys = {}", source)
        self.assertIn("let wrongRow = Math.floor(wrongSlot / 3)", source)
        self.assertNotIn("const wrongRow = Math.floor(wrongSlot / 3)", source)
        self.assertIn("let wrongColumn = wrongSlot % 3", source)
        self.assertNotIn("const wrongColumn = wrongSlot % 3", source)
        self.assertIn("let displaced = spec.pattern[wrongRow][wrongColumn]", source)
        self.assertNotIn("const displaced = spec.pattern[wrongRow][wrongColumn]", source)
        self.assertIn("let stack = remainder.get(index)", source)
        self.assertIn("let stack = countTwoRemainder.get(index)", source)
        self.assertIn("let mergedCount = countTwoInput.getItem(index).getCount() - 1 + stack.getCount()", source)

    def test_audit_uses_exact_seal_identity_and_count_checks(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        identity = "ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL))"
        self.assertEqual(source.count(identity), 2)
        self.assertIn(f"!{identity} || stack.getCount() !== 1", source)
        self.assertIn(f"!{identity} || stack.getCount() !== 2", source)

    def test_audit_contains_no_temporary_debug_markers(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        self.assertNotIn("[AFTERLIGHT GATE DEBUG]", source)
        self.assertNotIn("[AFTERLIGHT GATE ACTION DEBUG]", source)
        self.assertNotIn("[AFTERLIGHT GATE REMAINDER DEBUG]", source)

    def test_audit_selects_unambiguous_recipe_result_overload(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        self.assertNotIn("holder.value().getResultItem(registries)", source)
        self.assertIn(
            "holder.value()['getResultItem(net.minecraft.core.HolderLookup$Provider)'](registries)",
            source,
        )
        self.assertIn(
            "String(recipe.getSerializer()).startsWith('dev.latvian.mods.kubejs."
            "recipe.special.ShapedKubeJSRecipe$SerializerKJS@')",
            source,
        )

    def test_audit_checks_exact_thirty_inputs_and_all_live_recipes(self) -> None:
        source = self.read_script("gate_recipe_audit.js")
        exists_matches = re.findall(r"Item\.exists\('([^']+)'\)", source)
        exists_ids = set(exists_matches)
        self.assertEqual(len(NON_KUBEJS_INPUTS), 30)
        self.assertEqual(len(exists_matches), 30)
        self.assertEqual(exists_ids, NON_KUBEJS_INPUTS)
        all_recipe_ids = {
            *(recipe_id for recipe_id, _output, _keys in COMPONENTS),
            *(recipe_id for recipe_id, _item in STABILIZERS),
            "kubejs:gate/gate_of_return_core",
            *(recipe_id for _original, recipe_id, _output, _pattern, _keys in DRACONIC),
        }
        for recipe_id in all_recipe_ids:
            with self.subTest(recipe_id=recipe_id):
                self.assertIn(f"afterlightRecipe('{recipe_id}')", source)
        recipe_matches = re.findall(r"afterlightRecipe\('([^']+)'\)", source)
        self.assertEqual(len(recipe_matches), 11)
        self.assertEqual(set(recipe_matches), all_recipe_ids)
        for original_id, _recipe_id, _output, _pattern, _keys in DRACONIC:
            self.assertIn(original_id, source)
        for proof in (
            "recipe.matches(input, level)",
            "recipe.assemble(input, registries)",
            "recipe.getRemainingItems(input)",
            "acceptsMirrored()",
            ".width()",
            ".height()",
            "unsupported count-two KeepAction characterization",
            "expectedProducerCount",
        ):
            self.assertIn(proof, source)

    def test_harness_and_documentation_cover_install_gameplay_and_recovery(self) -> None:
        harness = (ROOT / "tools" / "server-test.sh").read_text(encoding="utf-8")
        self.assertIn("render-installed-gate-audit", harness)
        self.assertIn("verify-gate-audit", harness)
        self.assertIn("verify-seal-sources", harness)
        gameplay = ROOT / "docs" / "gameplay" / "gate-of-return.md"
        recovery = ROOT / "docs" / "operations" / "progression-token-recovery.md"
        self.assertTrue(gameplay.is_file())
        self.assertTrue(recovery.is_file())
        gameplay_text = gameplay.read_text(encoding="utf-8").lower()
        for phrase in (
            "7 by 7",
            "mechanical crafter",
            "eight",
            "five unique",
            "one billion fe",
            "manual client visual acceptance",
        ):
            self.assertIn(phrase, gameplay_text)
        recovery_text = recovery.read_text(encoding="utf-8").lower()
        for phrase in (
            "current or archived team data",
            "at most one",
            "schematic",
            "deep vault key",
            "blueprint",
            "precursor",
            "gate output",
            "seal",
            "immutable recovery log",
            "timestamp",
            "operator",
            "player",
            "team",
            "quest id",
            "item id",
            "count",
            "reason",
            "evidence path",
        ):
            self.assertIn(phrase, recovery_text)


if __name__ == "__main__":
    unittest.main()
