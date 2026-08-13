from __future__ import annotations

import importlib
import importlib.util
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from copy import deepcopy
from dataclasses import FrozenInstanceError, fields, replace
from pathlib import Path
from types import MappingProxyType


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "tools") not in sys.path:
    sys.path.insert(0, str(ROOT / "tools"))
FIXTURE = ROOT / "tools" / "fixtures" / "quests" / "manual-acquisition.json"
COMMODITY_FIXTURE = (
    ROOT / "tools" / "fixtures" / "quests" / "common-commodity-tasks.json"
)


def _legacy_quest_ids(quest_root, catalog):
    specification = importlib.util.spec_from_file_location(
        "afterlight_task8_integrated_build_quests",
        ROOT / "tools" / "build-quests.py",
    )
    assert specification is not None
    assert specification.loader is not None
    build_script = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(build_script)
    return build_script._legacy_quest_ids(quest_root, catalog)


class AcquisitionModuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acquisition = importlib.import_module("tools.afterlight_quests.acquisition")

    def test_acquisition_module_exists(self) -> None:
        self.assertTrue(
            (ROOT / "tools" / "afterlight_quests" / "acquisition.py").is_file(),
            "Task 8 acquisition module is missing",
        )

    def test_public_dataclass_fields_are_exact(self) -> None:
        expected = {
            "StackProof": ("id", "count", "components"),
            "RecipeProof": (
                "task_id",
                "id",
                "recipe_type",
                "serializer",
                "extractor",
                "output",
            ),
            "StackOutputProof": (
                "kind",
                "task_id",
                "id",
                "count",
                "components",
            ),
            "TagOutputProof": ("kind", "id", "count"),
            "ProcessStepProof": (
                "id",
                "recipe_type",
                "serializer",
                "extractor",
                "role",
                "outputs",
                "attributes",
            ),
            "FluidContainerProof": (
                "kind",
                "task_id",
                "source_step",
                "cycles",
                "fluid",
                "millibuckets",
                "output",
            ),
            "EntityInteractionProof": (
                "kind",
                "task_id",
                "source_step",
                "input",
                "entity_id",
                "item_class",
                "method",
                "output",
            ),
            "ResourceProof": ("location", "sha256"),
            "CriterionProof": ("name", "trigger", "instance_class", "fields"),
            "AdvancementProof": ("id", "criteria", "requirements", "resource"),
            "RegistryKeyProof": ("registry", "key"),
            "TaskItemProof": ("task_id", "id", "count", "components"),
            "TagMembershipProof": ("id", "members"),
            "EquivalentTagProof": ("id", "equals", "minimum_members"),
            "NativeTargetProof": ("block_id", "loot_table_id", "silk_touch"),
            "WorldgenProof": (
                "registry_keys",
                "resources",
                "item_tag",
                "biome_tag",
                "native_target",
            ),
            "ManualCheckProof": ("locale", "localization_key"),
            "RecipeNodeProof": ("recipes",),
            "ProcessNodeProof": ("steps", "native_checks"),
            "AcquisitionNode": (
                "quest_id",
                "quest_slug",
                "task_ids",
                "method",
                "proof",
            ),
            "AcquisitionManifest": ("schema_version", "nodes"),
        }
        for name, field_names in expected.items():
            with self.subTest(name=name):
                model = getattr(self.acquisition, name)
                self.assertEqual(tuple(field.name for field in fields(model)), field_names)

    def test_public_model_freezes_nested_collections(self) -> None:
        source = {"test:component": "value"}
        stack = self.acquisition.StackProof("minecraft:stone", 1, source)
        source["test:component"] = "changed"

        self.assertIsInstance(stack.components, MappingProxyType)
        self.assertEqual(stack.components, {"test:component": "value"})
        with self.assertRaises(FrozenInstanceError):
            stack.count = 2
        with self.assertRaises(TypeError):
            stack.components["test:component"] = "changed"

    def test_canonical_fixture_has_all_exact_records_and_corrections(self) -> None:
        raw = FIXTURE.read_bytes()
        data = json.loads(raw)

        self.assertEqual(
            raw,
            (
                json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True)
                + "\n"
            ).encode("utf-8"),
        )
        self.assertEqual(set(data), {"nodes", "schema_version"})
        self.assertEqual(data["schema_version"], 1)
        self.assertEqual(len(data["nodes"]), 81)
        self.assertEqual(
            Counter(node["method"] for node in data["nodes"]),
            {
                "recipe": 53,
                "process": 9,
                "worldgen": 1,
                "advancement": 8,
                "manual_check": 10,
            },
        )
        self.assertEqual(
            [node["quest_id"] for node in data["nodes"]],
            sorted(node["quest_id"] for node in data["nodes"]),
        )
        by_slug = {node["quest_slug"]: node for node in data["nodes"]}
        self.assertEqual(
            by_slug["manuals/pneumaticcraft/read-pressure-safely"]["recipes"][0][
                "output"
            ],
            {
                "components": {"patchouli:book": "pneumaticcraft:book"},
                "count": 1,
                "id": "patchouli:guide_book",
            },
        )
        self.assertEqual(
            by_slug["manuals/applied-energistics-2/first-pattern"]["recipes"][0][
                "output"
            ],
            {"components": {}, "count": 2, "id": "ae2:blank_pattern"},
        )

    @staticmethod
    def write_fixture(path: Path, data: object) -> None:
        path.write_text(
            json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_loader_round_trips_exact_manifest_and_digests(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)

        self.assertIsInstance(manifest.nodes, tuple)
        self.assertEqual(len(manifest.nodes), 81)
        self.assertEqual(
            self.acquisition.manifest_to_data(manifest),
            json.loads(FIXTURE.read_text(encoding="utf-8")),
        )
        self.assertEqual(
            self.acquisition.canonical_bytes({"b": 2, "a": 1}),
            b'{"a":1,"b":2}',
        )
        self.assertEqual(
            self.acquisition.manifest_digest(manifest),
            "c232c7220be363276cc2441dde9580692ea6b103d1d6e70a70242cc2dd5278ea",
        )
        self.assertEqual(
            self.acquisition.proof_digest(
                manifest.nodes[0],
                "c232c7220be363276cc2441dde9580692ea6b103d1d6e70a70242cc2dd5278ea",
                "task8-test-nonce",
            ),
            "957babfc1639512844bab452546419fbaf1b7cacdcaca0beb478c11d597d1bb3",
        )

    def test_loader_rejects_duplicate_json_keys_before_normalization(self) -> None:
        raw = FIXTURE.read_text(encoding="utf-8").replace(
            '  "schema_version": 1',
            '  "schema_version": 1,\n  "schema_version": 1',
            1,
        )
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            path = Path(temporary) / "duplicate.json"
            path.write_text(raw, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key schema_version"):
                self.acquisition.load_manifest(path)

    def test_loader_rejects_noncanonical_bytes(self) -> None:
        data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            path = Path(temporary) / "compact.json"
            path.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fixture bytes are not canonical"):
                self.acquisition.load_manifest(path)

    def test_loader_rejects_closed_schema_and_identity_mutations(self) -> None:
        original = json.loads(FIXTURE.read_text(encoding="utf-8"))
        mutations = {
            "unknown root key": lambda data: data.update({"extra": True}),
            "unknown node key": lambda data: data["nodes"][0].update(
                {"extra": True}
            ),
            "unknown recipe key": lambda data: data["nodes"][0]["recipes"][0].update(
                {"extra": True}
            ),
            "boolean count": lambda data: data["nodes"][0]["recipes"][0][
                "output"
            ].update({"count": True}),
            "malformed quest ID": lambda data: data["nodes"][0].update(
                {"quest_id": "FFFFFFFFFFFFFFFF"}
            ),
            "duplicate quest": lambda data: data["nodes"][1].update(
                {"quest_id": data["nodes"][0]["quest_id"]}
            ),
            "duplicate task": lambda data: data["nodes"][1].update(
                {"task_ids": [data["nodes"][0]["task_ids"][0]]}
            ),
            "unsorted nodes": lambda data: data["nodes"].__setitem__(
                slice(0, 2), reversed(data["nodes"][:2])
            ),
            "wrong method count": lambda data: data["nodes"].pop(),
            "forbidden punctuation": lambda data: data["nodes"][0].update(
                {"quest_slug": f"manuals/bad{chr(0x2014)}slug"}
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                data = deepcopy(original)
                mutate(data)
                path = Path(temporary) / "mutated.json"
                self.write_fixture(path, data)
                with self.assertRaises(ValueError):
                    self.acquisition.load_manifest(path)

    def test_digest_inputs_are_fail_closed(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        with self.assertRaisesRegex(ValueError, "manifest digest"):
            self.acquisition.proof_digest(manifest.nodes[0], "0" * 63, "nonce")
        for nonce in ("", "space value", "bad:nonce"):
            with self.subTest(nonce=nonce), self.assertRaisesRegex(
                ValueError, "nonce"
            ):
                self.acquisition.proof_digest(manifest.nodes[0], "0" * 64, nonce)

    def test_manifest_and_proof_digests_bind_every_input(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        manifest_sha256 = self.acquisition.manifest_digest(manifest)
        node = manifest.nodes[0]
        changed_node = replace(node, quest_slug=node.quest_slug + "-changed")
        changed_manifest = replace(
            manifest,
            nodes=(changed_node, *manifest.nodes[1:]),
        )
        baseline = self.acquisition.proof_digest(
            node,
            manifest_sha256,
            "nonce-one",
        )
        self.assertNotEqual(
            baseline,
            self.acquisition.proof_digest(
                node,
                manifest_sha256,
                "nonce-two",
            ),
        )
        self.assertNotEqual(
            baseline,
            self.acquisition.proof_digest(
                node,
                "0" * 64,
                "nonce-one",
            ),
        )
        self.assertNotEqual(
            baseline,
            self.acquisition.proof_digest(
                changed_node,
                manifest_sha256,
                "nonce-one",
            ),
        )
        self.assertNotEqual(
            manifest_sha256,
            self.acquisition.manifest_digest(changed_manifest),
        )

    def test_fixture_agrees_with_catalog_and_parsed_generated_snbt(self) -> None:
        quests = importlib.import_module("tools.afterlight_quests")
        builder = importlib.import_module("tools.afterlight_quests.builder")
        manifest = self.acquisition.load_manifest(FIXTURE)
        catalog = quests.build_catalog()

        self.assertEqual(
            self.acquisition.validate_fixture_to_quests(manifest, catalog),
            [],
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "config", root / "config")
            fixture_root = root / "tools" / "fixtures" / "quests"
            fixture_root.mkdir(parents=True)
            (fixture_root / "manual-acquisition.json").write_bytes(
                FIXTURE.read_bytes()
            )
            (fixture_root / "common-commodity-tasks.json").write_bytes(
                COMMODITY_FIXTURE.read_bytes()
            )
            quest_root = root / "config" / "ftbquests" / "quests"
            builder._write_catalog_workspace(
                catalog,
                quest_root,
                legacy_quest_ids=_legacy_quest_ids(quest_root, catalog),
            )
            self.assertEqual(
                self.acquisition.validate_fixture_to_quests(manifest, quest_root),
                [],
            )

    def test_fixture_agreement_rejects_every_task_contract_mutation(self) -> None:
        quests = importlib.import_module("tools.afterlight_quests")
        manifest = self.acquisition.load_manifest(FIXTURE)

        def task(catalog, slug):
            return next(
                task_value
                for chapter in catalog
                for quest in chapter.quests
                for task_value in quest.tasks
                if task_value.slug == slug
            )

        def quest(catalog, slug):
            return next(
                quest_value
                for chapter in catalog
                for quest_value in chapter.quests
                if quest_value.slug == slug
            )

        mutations = {
            "quest ID": lambda catalog: setattr(
                quest(catalog, "manuals/mekanism/enrichment-chamber"),
                "explicit_id",
                "0000000000000002",
            ),
            "ordered task IDs": lambda catalog: setattr(
                quest(
                    catalog,
                    "manuals/immersive-engineering/recover-field-manual",
                ),
                "tasks",
                tuple(
                    reversed(
                        quest(
                            catalog,
                            "manuals/immersive-engineering/recover-field-manual",
                        ).tasks
                    )
                ),
            ),
            "task type": lambda catalog: setattr(
                task(
                    catalog,
                    "manuals/pneumaticcraft/air-compressor/task/item",
                ),
                "task_type",
                "checkmark",
            ),
            "task stack": lambda catalog: task(
                catalog,
                "manuals/pneumaticcraft/read-pressure-safely/task/item",
            ).data["item"].update({"id": "minecraft:book"}),
            "task components": lambda catalog: task(
                catalog,
                "manuals/pneumaticcraft/read-pressure-safely/task/item",
            ).data["item"].update(
                {"components": {"patchouli:book": "test:wrong"}}
            ),
            "task count": lambda catalog: task(
                catalog,
                "manuals/pneumaticcraft/air-compressor/task/item",
            ).data.update({"count": quests.SnbtLong(2)}),
            "advancement": lambda catalog: task(
                catalog,
                "manuals/create/water-wheel/task/advancement",
            ).data.update({"advancement": "create:wrong"}),
            "manual action": lambda catalog: setattr(
                task(catalog, "manuals/mekanism/field-test/task/checkmark"),
                "title",
                "",
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                catalog = deepcopy(quests.build_catalog())
                mutate(catalog)
                errors = self.acquisition.validate_fixture_to_quests(
                    manifest,
                    catalog,
                )
                self.assertTrue(errors, f"{label} mutation was accepted")
                self.assertTrue(
                    any(label.lower() in error.lower() for error in errors),
                    errors,
                )

    def test_fixture_agreement_requires_exact_component_matching_mode(self) -> None:
        quests = importlib.import_module("tools.afterlight_quests")
        builder = importlib.import_module("tools.afterlight_quests.builder")
        manifest = self.acquisition.load_manifest(FIXTURE)
        catalog = deepcopy(quests.build_catalog())
        task = next(
            task_value
            for chapter in catalog
            for quest in chapter.quests
            for task_value in quest.tasks
            if task_value.slug
            == "manuals/pneumaticcraft/read-pressure-safely/task/item"
        )
        self.assertEqual(task.data.pop("match_components"), "fuzzy")
        catalog_errors = self.acquisition.validate_fixture_to_quests(
            manifest,
            catalog,
        )
        self.assertTrue(
            any("match_components" in error for error in catalog_errors),
            catalog_errors,
        )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "config", root / "config")
            fixture_root = root / "tools" / "fixtures" / "quests"
            fixture_root.mkdir(parents=True)
            fixture_root.joinpath("manual-acquisition.json").write_bytes(
                FIXTURE.read_bytes()
            )
            fixture_root.joinpath("common-commodity-tasks.json").write_bytes(
                COMMODITY_FIXTURE.read_bytes()
            )
            quest_root = root / "config" / "ftbquests" / "quests"
            catalog = quests.build_catalog()
            builder._write_catalog_workspace(
                catalog,
                quest_root,
                legacy_quest_ids=_legacy_quest_ids(quest_root, catalog),
            )
            chapter = next(
                path
                for path in (quest_root / "chapters").glob("*.snbt")
                if "1B763EBDB1D20149" in path.read_text(encoding="utf-8")
            )
            source = chapter.read_text(encoding="utf-8")
            changed = source.replace(
                '\t\t\t\t\tmatch_components: "fuzzy"\n',
                "",
                1,
            )
            self.assertNotEqual(changed, source)
            chapter.write_text(changed, encoding="utf-8")
            parsed_errors = self.acquisition.validate_fixture_to_quests(
                manifest,
                quest_root,
            )
            self.assertTrue(
                any("match_components" in error for error in parsed_errors),
                parsed_errors,
            )

    def test_fixture_agreement_rejects_unapproved_explicit_id_ownership(self) -> None:
        quests = importlib.import_module("tools.afterlight_quests")
        manifest = self.acquisition.load_manifest(FIXTURE)

        for owner_kind, target_slug in (
            ("quest", "manuals/mekanism/enrichment-chamber"),
            ("task", "manuals/mekanism/enrichment-chamber/task/item"),
        ):
            with self.subTest(owner_kind=owner_kind):
                catalog = deepcopy(quests.build_catalog())
                if owner_kind == "quest":
                    owner = next(
                        quest
                        for chapter in catalog
                        for quest in chapter.quests
                        if quest.slug == target_slug
                    )
                else:
                    owner = next(
                        task
                        for chapter in catalog
                        for quest in chapter.quests
                        for task in quest.tasks
                        if task.slug == target_slug
                    )
                self.assertIsNone(owner.explicit_id)
                resolved_id = owner.id
                owner.explicit_id = resolved_id
                self.assertEqual(owner.id, resolved_id)
                errors = self.acquisition.validate_fixture_to_quests(
                    manifest,
                    catalog,
                )
                self.assertTrue(
                    any(
                        f"{owner_kind} explicit ID ownership" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_renderer_avoids_kubejs_blocked_charset_class(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        source = self.acquisition.render_manual_acquisition_audit(manifest)

        self.assertNotIn("java.nio.charset.StandardCharsets", source)
        self.assertNotIn("Java.loadClass('java.lang.String')", source)
        self.assertNotIn("new AfterlightString", source)
        self.assertNotIn("Java.to(", source)
        self.assertNotIn("Java.cast(", source)
        self.assertNotIn("AfterlightByte", source)
        self.assertNotIn("AfterlightMessageDigest", source)
        self.assertNotIn("AfterlightHexFormat", source)
        self.assertNotIn("charCodeAt", source)
        self.assertIn("value.codePointAt(textIndex)", source)
        self.assertIn("function afterlightSha256Bytes", source)
        self.assertIn("function afterlightSha256Ascii", source)
        self.assertIn("setTimeout(() => {", source)
        self.assertIn("}, Duration.ofMillis(1))", source)
        self.assertIn("var nodeReason =", source)
        self.assertIn("var outerReason =", source)
        scheduled_audit = source[source.index("setTimeout(() => {") :]
        self.assertNotIn("const reason =", scheduled_audit)
        self.assertNotIn(", error)\n", scheduled_audit)
        self.assertNotIn("task.getClass()", source)
        self.assertNotIn("AfterlightCheckmarkTask.class.isInstance(task)", source)
        self.assertIn("task instanceof AfterlightCheckmarkTask", source)
        self.assertNotIn("instance.getClass()", source)
        self.assertNotIn(".getClass()", source)
        self.assertNotIn(".class.isInstance(", source)
        self.assertIn(
            "var expectedInstanceClass = Java.loadClass(declared.instance_class)",
            source,
        )
        self.assertIn("instance instanceof expectedInstanceClass", source)
        self.assertIn("recipe instanceof AfterlightProcessingRecipe", source)
        self.assertIn("inputItem instanceof expectedItemClass", source)
        sha_function = source[
            source.index("function afterlightSha256Ascii") : source.index(
                "function afterlightProofDigest"
            )
        ]
        self.assertNotIn("const ", sha_function)
        self.assertNotIn("let ", sha_function)

    def test_renderer_indexes_rhino_java_lists_before_iterator_fallback(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        source = self.acquisition.render_manual_acquisition_audit(manifest)
        adapter = source[
            source.index("function javaArray") : source.index(
                "function sortedStrings"
            )
        ]
        harness = (
            adapter
            + "\nconst indexed = {0: 'first', 1: 'second', length: 2, "
            + "iterator: function() { throw new Error('iterator accessed') }};\n"
            + "console.log(JSON.stringify(javaArray(indexed)));\n"
            + "const iterable = {iterator: function() { var position = 0; "
            + "var values = ['third', 'fourth']; return {"
            + "hasNext: function() { return position < values.length }, "
            + "next: function() { return values[position++] }} }};\n"
            + "console.log(JSON.stringify(javaArray(iterable)));\n"
        )
        result = subprocess.run(
            ["node"],
            input=harness,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            ['["first","second"]', '["third","fourth"]'],
        )

    def test_renderer_uses_registry_context_for_every_recipe_result(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        source = self.acquisition.render_manual_acquisition_audit(manifest)

        self.assertNotIn("recipe.getResultItem()", source)
        self.assertIn(
            "recipe['getResultItem(net.minecraft.core.HolderLookup$Provider)'](registries)",
            source,
        )

    def test_renderer_is_deterministic_ascii_and_boot_bound(self) -> None:
        manifest = self.acquisition.load_manifest(FIXTURE)
        first = self.acquisition.render_manual_acquisition_audit(manifest)
        second = self.acquisition.render_manual_acquisition_audit(manifest)

        self.assertEqual(first, second)
        self.assertEqual(first.encode("ascii").decode("ascii"), first)
        self.assertTrue(first.endswith("\n"))
        self.assertEqual(first.count(self.acquisition.NONCE_PLACEHOLDER), 1)
        self.assertIn(self.acquisition.manifest_digest(manifest), first)
        self.assertIn(
            self.acquisition.canonical_bytes(
                self.acquisition.manifest_to_data(manifest)["nodes"][0]
            ).decode("ascii"),
            first,
        )
        self.assertIn("AFTERLIGHT-ACQUISITION-PROOF\\0", first)
        self.assertIn("AFTERLIGHT_ACQUISITION_AUDIT_BEGIN", first)
        self.assertIn("AFTERLIGHT_ACQUISITION_AUDIT_NODE", first)
        self.assertIn("AFTERLIGHT_ACQUISITION_AUDIT_OK", first)
        self.assertIn("AFTERLIGHT_ACQUISITION_AUDIT_FAIL", first)
        self.assertIn("getResultItem(net.minecraft.core.HolderLookup$Provider)", first)
        self.assertIn("FakePlayerFactory", first)
        self.assertIn("ServerQuestFile", first)
        self.assertIn(
            "recipe instanceof AfterlightProcessingRecipe",
            first,
        )
        self.assertIn(
            "recipe instanceof AfterlightPressureChamberRecipe",
            first,
        )
        self.assertIn(
            "recipe instanceof AfterlightExplosionCraftingRecipe",
            first,
        )
        self.assertIn("return afterlightSha256Bytes(bytes)", first)
        nonce = "task8-proof-vector"
        known_proof = (
            "397ea5d3b428d15f063935204af4bba29e1aba0cfc6437c186844296cede3a91"
        )
        self.assertEqual(
            self.acquisition.proof_digest(
                manifest.nodes[0],
                self.acquisition.manifest_digest(manifest),
                nonce,
            ),
            known_proof,
        )
        harness = (
            "global.Java = { loadClass: function() { return {}; } };\n"
            "global.ServerEvents = { loaded: function() {} };\n"
            + first
            + "\nconsole.log(afterlightProofDigest("
            + json.dumps(self.acquisition.manifest_digest(manifest))
            + ", "
            + json.dumps(nonce)
            + ", AFTERLIGHT_ACQUISITION_SPECS[0].canonical));\n"
            + "console.log(afterlightSha256Bytes([97, 98, 99]));\n"
            + "try { afterlightSha256Ascii('\\u00e9'); console.log('accepted') } "
            + "catch (error) { console.log(String(error.message)) }\n"
        )
        result = subprocess.run(
            ["node"],
            input=harness,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.splitlines(),
            [
                known_proof,
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
                "acquisition proof material is not ASCII",
            ],
        )
        self.assertNotIn(
            "spec.requirements.map(requirement => requirement.slice().sort()",
            first,
        )
        self.assertNotIn(
            self.acquisition.proof_digest(
                manifest.nodes[0],
                self.acquisition.manifest_digest(manifest),
                "fixed-nonce",
            ),
            first,
        )


class AcquisitionRuntimeParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acquisition = importlib.import_module("tools.afterlight_quests.acquisition")
        cls.manifest = cls.acquisition.load_manifest(FIXTURE)
        cls.manifest_sha256 = cls.acquisition.manifest_digest(cls.manifest)
        cls.nonce = "task8-runtime-nonce"

    def transcript(self) -> list[str]:
        lines = [
            "AFTERLIGHT_ACQUISITION_AUDIT_BEGIN "
            f"schema=1 nonce={self.nonce} manifest={self.manifest_sha256}"
        ]
        for node in self.manifest.nodes:
            lines.append(
                "AFTERLIGHT_ACQUISITION_AUDIT_NODE "
                f"quest={node.quest_id} task={','.join(node.task_ids)} "
                f"method={node.method} status=OK "
                "proof="
                + self.acquisition.proof_digest(
                    node,
                    self.manifest_sha256,
                    self.nonce,
                )
            )
        lines.append(
            "AFTERLIGHT_ACQUISITION_AUDIT_OK "
            f"count=81 nonce={self.nonce} manifest={self.manifest_sha256}"
        )
        return lines

    def validate_lines(self, lines_by_log: tuple[list[str], list[str], list[str]]):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = []
            for index, lines in enumerate(lines_by_log):
                path = root / f"log-{index}.log"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                paths.append(path)
            return self.acquisition.validate_acquisition_audit_logs(
                self.manifest,
                self.nonce,
                tuple(paths),
            )

    def test_three_complete_logs_are_required_and_accepted(self) -> None:
        lines = self.transcript()
        self.assertEqual(self.validate_lines((lines, lines, lines)), [])

    def test_parser_rejects_all_marker_state_mutations(self) -> None:
        base = self.transcript()
        first_node = self.manifest.nodes[0]
        cases = {
            "acquisition audit missing begin": base[1:],
            "acquisition audit duplicate begin": [base[0], *base],
            f"acquisition audit missing node {first_node.quest_id}": [
                base[0],
                *base[2:],
            ],
            f"acquisition audit duplicate node {first_node.quest_id}": [
                base[0],
                base[1],
                *base[1:],
            ],
            "acquisition audit stale nonce": [
                line.replace(self.nonce, "old-nonce") if line == base[0] else line
                for line in base
            ],
            "acquisition audit stale manifest": [
                base[0].replace(self.manifest_sha256, "0" * 64),
                *base[1:],
            ],
            f"acquisition audit wrong proof {first_node.quest_id}": [
                base[0],
                re.sub(r"proof=[0-9a-f]{64}$", "proof=" + "0" * 64, base[1]),
                *base[2:],
            ],
            f"acquisition audit wrong method {first_node.quest_id}": [
                base[0],
                base[1].replace(f"method={first_node.method}", "method=process"),
                *base[2:],
            ],
            f"acquisition audit wrong task list {first_node.quest_id}": [
                base[0],
                base[1].replace(
                    f"task={','.join(first_node.task_ids)}",
                    "task=0000000000000002",
                ),
                *base[2:],
            ],
            "acquisition audit missing terminal": base[:-1],
            "acquisition audit duplicate terminal": [*base, base[-1]],
            "acquisition audit wrong terminal count": [
                *base[:-1],
                base[-1].replace("count=81", "count=80"),
            ],
            "acquisition audit malformed marker": [
                base[0] + " extra=bad",
                *base[1:],
            ],
        }
        for expected, changed in cases.items():
            with self.subTest(expected=expected):
                errors = self.validate_lines((changed, base, base))
                self.assertIn(expected, errors)

    def test_fail_node_cannot_be_hidden_by_old_ok_lines(self) -> None:
        base = self.transcript()
        first = self.manifest.nodes[0]
        failed = [
            base[0],
            (
                "AFTERLIGHT_ACQUISITION_AUDIT_NODE "
                f"quest={first.quest_id} task={','.join(first.task_ids)} "
                f"method={first.method} status=FAIL reason=RECIPE_MISSING "
                "proof="
                + self.acquisition.proof_digest(
                    first,
                    self.manifest_sha256,
                    self.nonce,
                )
            ),
            (
                "AFTERLIGHT_ACQUISITION_AUDIT_FAIL count=0 "
                f"nonce={self.nonce} manifest={self.manifest_sha256} "
                "reason=RECIPE_MISSING"
            ),
            *base,
        ]
        errors = self.validate_lines((failed, base, base))
        self.assertIn(
            f"acquisition audit failure {first.quest_id} RECIPE_MISSING",
            errors,
        )

    def test_every_closed_failure_reason_is_rejected(self) -> None:
        base = self.transcript()
        first = self.manifest.nodes[0]
        for reason in sorted(self.acquisition._FAILURE_REASONS):
            with self.subTest(reason=reason):
                failed = [
                    base[0],
                    (
                        "AFTERLIGHT_ACQUISITION_AUDIT_NODE "
                        f"quest={first.quest_id} "
                        f"task={','.join(first.task_ids)} "
                        f"method={first.method} status=FAIL reason={reason} "
                        "proof="
                        + self.acquisition.proof_digest(
                            first,
                            self.manifest_sha256,
                            self.nonce,
                        )
                    ),
                    (
                        "AFTERLIGHT_ACQUISITION_AUDIT_FAIL count=0 "
                        f"nonce={self.nonce} manifest={self.manifest_sha256} "
                        f"reason={reason}"
                    ),
                ]
                errors = self.validate_lines((failed, base, base))
                self.assertIn(
                    f"acquisition audit failure {first.quest_id} {reason}",
                    errors,
                )


class AcquisitionBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("tools.afterlight_quests")
        cls.builder = importlib.import_module("tools.afterlight_quests.builder")
        cls.acquisition = importlib.import_module("tools.afterlight_quests.acquisition")
        cls.manifest = cls.acquisition.load_manifest(FIXTURE)
        specification = importlib.util.spec_from_file_location(
            "afterlight_task8_build_quests",
            ROOT / "tools" / "build-quests.py",
        )
        assert specification is not None
        assert specification.loader is not None
        cls.build_script = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(cls.build_script)

    def make_workspace(self, base: Path) -> tuple[Path, Path]:
        root = base / "repository"
        shutil.copytree(ROOT / "config", root / "config")
        fixture = root / "tools" / "fixtures" / "quests" / "manual-acquisition.json"
        fixture.parent.mkdir(parents=True)
        fixture.write_bytes(FIXTURE.read_bytes())
        commodity = (
            root
            / "tools"
            / "fixtures"
            / "quests"
            / "common-commodity-tasks.json"
        )
        commodity.write_bytes(COMMODITY_FIXTURE.read_bytes())
        return root, root / "config" / "ftbquests" / "quests"

    def test_commodity_fixture_and_generated_runtime_contract_are_exact(self) -> None:
        raw = COMMODITY_FIXTURE.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "52ca9efb512a97827c25494fb4070287709c50f968547b6a1d0d33f2d855af27",
        )
        fixture = json.loads(raw)
        self.assertEqual(
            [entry["task"]["id"] for entry in fixture["declarations"]],
            [
                "39C717BFFEE3D235",
                "1D73FB79ED38668F",
                "374F658F034EF8C5",
                "33B5B56650A6AEDF",
                "1679C5714C2F2A74",
            ],
        )
        source = self.builder._render_quest_item_audit(
            ROOT / "config" / "ftbquests" / "quests"
        )
        self.assertEqual(source.count("__AFTERLIGHT_BOOT_NONCE__"), 1)
        self.assertIn(hashlib.sha256(raw).hexdigest(), source)
        expected_markers = [
            "TAG c:foods/bread minecraft:bread,pneumaticcraft:sourdough_bread",
            "PRODUCER c:foods/bread minecraft:bread OK",
            "PRODUCER c:foods/bread pneumaticcraft:sourdough_bread OK",
            "TAG minecraft:beds minecraft:black_bed,minecraft:blue_bed,minecraft:brown_bed,minecraft:cyan_bed,minecraft:gray_bed,minecraft:green_bed,minecraft:light_blue_bed,minecraft:light_gray_bed,minecraft:lime_bed,minecraft:magenta_bed,minecraft:orange_bed,minecraft:pink_bed,minecraft:purple_bed,minecraft:red_bed,minecraft:white_bed,minecraft:yellow_bed,aether:skyroot_bed",
            "PRODUCER minecraft:beds minecraft:red_bed OK",
            "PRODUCER minecraft:beds aether:skyroot_bed OK",
            "TAG c:ingots/steel immersiveengineering:ingot_steel,mekanism:ingot_steel,modern_industrialization:steel_ingot,oritech:biosteel_ingot,oritech:steel_ingot",
            "PRODUCER c:ingots/steel immersiveengineering:ingot_steel OK",
            "PRODUCER c:ingots/steel mekanism:ingot_steel OK",
            "PRODUCER c:ingots/steel modern_industrialization:steel_ingot OK",
            "PRODUCER c:ingots/steel oritech:biosteel_ingot OK",
            "PRODUCER c:ingots/steel oritech:steel_ingot OK",
        ]
        positions = [source.index(marker) for marker in expected_markers]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("AFTERLIGHT QUEST COMMODITY AUDIT] OK", source)
        self.assertIn("AFTERLIGHT QUEST COMMODITY AUDIT] FAILED", source)
        contract = self.builder._commodity_runtime_contract(ROOT)
        self.assertEqual(
            contract["changed_old_items"],
            [
                {"tag": "c:foods/bread", "item": "minecraft:bread"},
                {"tag": "minecraft:beds", "item": "minecraft:red_bed"},
                {
                    "tag": "c:ingots/steel",
                    "item": "immersiveengineering:ingot_steel",
                },
                {
                    "tag": "c:ingots/steel",
                    "item": "immersiveengineering:ingot_steel",
                },
            ],
        )

    def test_duplicate_commodity_declaration_fails_closed(self) -> None:
        fixture = json.loads(COMMODITY_FIXTURE.read_text(encoding="utf-8"))
        fixture["declarations"].append(deepcopy(fixture["declarations"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate commodity declaration"):
            self.builder._commodity_contract_from_fixture(
                fixture,
                hashlib.sha256(COMMODITY_FIXTURE.read_bytes()).hexdigest(),
            )

    def test_workspace_builder_writes_both_canonical_audits(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root, quest_root = self.make_workspace(Path(temporary))
            catalog = self.quests.build_catalog()
            self.builder._write_catalog_workspace(
                catalog,
                quest_root,
                legacy_quest_ids=self.build_script._legacy_quest_ids(
                    quest_root,
                    catalog,
                ),
            )

            item_audit = (
                root
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "generated_quest_item_audit.js"
            )
            acquisition_audit = item_audit.with_name(
                "generated_manual_acquisition_audit.js"
            )
            self.assertEqual(
                item_audit.read_text(encoding="utf-8"),
                self.builder._render_quest_item_audit(quest_root),
            )
            self.assertEqual(
                acquisition_audit.read_text(encoding="utf-8"),
                self.acquisition.render_manual_acquisition_audit(self.manifest),
            )

    def test_catalog_acquisition_failure_leaves_all_outputs_unchanged(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root, quest_root = self.make_workspace(Path(temporary))
            audit_root = root / "kubejs" / "server_scripts" / "afterlight"
            audit_root.mkdir(parents=True)
            item_audit = audit_root / "generated_quest_item_audit.js"
            acquisition_audit = audit_root / "generated_manual_acquisition_audit.js"
            item_audit.write_bytes(b"old item audit\n")
            acquisition_audit.write_bytes(b"old acquisition audit\n")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            catalog = deepcopy(self.quests.build_catalog())
            target = next(
                task
                for chapter in catalog
                for quest in chapter.quests
                for task in quest.tasks
                if task.slug
                == "manuals/pneumaticcraft/read-pressure-safely/task/item"
            )
            target.data["item"]["id"] = "minecraft:book"

            with self.assertRaisesRegex(ValueError, "task stack ID mismatch"):
                self.quests.write_catalog(
                    catalog,
                    quest_root,
                    legacy_quest_ids=self.build_script._legacy_quest_ids(
                        quest_root,
                        catalog,
                    ),
                )

            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_unexpected_generated_audit_fails_transaction_without_changes(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root, quest_root = self.make_workspace(Path(temporary))
            audit_root = root / "kubejs" / "server_scripts" / "afterlight"
            audit_root.mkdir(parents=True)
            unexpected = audit_root / "generated_legacy_audit.js"
            unexpected.write_bytes(b"unexpected\n")
            before = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }

            with self.assertRaisesRegex(
                ValueError,
                "generated quest audit inventory mismatch",
            ):
                catalog = self.quests.build_catalog()
                self.quests.write_catalog(
                    catalog,
                    quest_root,
                    legacy_quest_ids=self.build_script._legacy_quest_ids(
                        quest_root,
                        catalog,
                    ),
                )

            after = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            }
            self.assertEqual(after, before)

    def test_two_transactional_builds_are_byte_identical(self) -> None:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            root = Path(temporary) / "repository"
            shutil.copytree(ROOT / "config", root / "config")
            shutil.copytree(ROOT / "mods", root / "mods")
            shutil.copytree(ROOT / "kubejs", root / "kubejs")
            fixture_root = root / "tools" / "fixtures" / "quests"
            fixture_root.mkdir(parents=True)
            fixture_root.joinpath("manual-acquisition.json").write_bytes(
                FIXTURE.read_bytes()
            )
            fixture_root.joinpath("common-commodity-tasks.json").write_bytes(
                COMMODITY_FIXTURE.read_bytes()
            )
            (root / "server-test" / "mods").mkdir(parents=True)
            fixture_before = FIXTURE.read_bytes()

            self.build_script._build_quests(root)
            tracked = (
                root / "config" / "ftbquests" / "quests",
                root / "kubejs" / "server_scripts" / "afterlight" / "generated_quest_item_audit.js",
                root / "kubejs" / "server_scripts" / "afterlight" / "generated_manual_acquisition_audit.js",
            )
            first = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for tracked_root in tracked
                for path in (
                    tracked_root.rglob("*")
                    if tracked_root.is_dir()
                    else (tracked_root,)
                )
                if path.is_file()
            }
            self.build_script._build_quests(root)
            second = {
                path.relative_to(root).as_posix(): path.read_bytes()
                for tracked_root in tracked
                for path in (
                    tracked_root.rglob("*")
                    if tracked_root.is_dir()
                    else (tracked_root,)
                )
                if path.is_file()
            }
            self.assertEqual(second, first)
            self.assertEqual(
                fixture_root.joinpath("manual-acquisition.json").read_bytes(),
                fixture_before,
            )
            self.assertEqual(
                self.acquisition.manifest_digest(
                    self.acquisition.load_manifest(
                        fixture_root / "manual-acquisition.json"
                    )
                ),
                self.acquisition.manifest_digest(self.manifest),
            )


class CommodityRuntimeParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.builder = importlib.import_module("tools.afterlight_quests.builder")
        cls.quest_root = ROOT / "config" / "ftbquests" / "quests"
        cls.nonce = "task8-shared-nonce"
        cls.contract = cls.builder._commodity_runtime_contract(ROOT)
        cls.item_digest = cls.builder.quest_item_audit_digest(cls.quest_root)
        cls.item_count = len(cls.builder._quest_item_ids(cls.quest_root))

    def transcript(self) -> list[str]:
        lines = [
            "[AFTERLIGHT QUEST ITEM AUDIT] OK "
            f"{self.item_digest} {self.item_count} {self.nonce}"
        ]
        lines.extend(
            f"[AFTERLIGHT QUEST COMMODITY AUDIT] {record}"
            for record in self.contract["records"]
        )
        lines.append(
            "[AFTERLIGHT QUEST COMMODITY AUDIT] OK "
            f"{self.contract['fixture_sha256']} {self.item_digest} 4 {self.nonce}"
        )
        return lines

    def validate(self, logs: tuple[list[str], list[str], list[str]]) -> list[str]:
        with tempfile.TemporaryDirectory(dir="/private/tmp") as temporary:
            paths = []
            for index, lines in enumerate(logs):
                path = Path(temporary) / f"log-{index}.log"
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                paths.append(path)
            return self.builder.validate_quest_item_audit_logs(
                self.quest_root,
                self.nonce,
                tuple(paths),
            )

    def test_three_logs_require_exact_item_and_commodity_transcripts(self) -> None:
        transcript = self.transcript()
        self.assertEqual(self.validate((transcript, transcript, transcript)), [])

        stale = [line.replace(self.nonce, "stale-nonce") for line in transcript]
        errors = self.validate((transcript, stale, transcript))
        self.assertIn("commodity audit stale nonce", errors)

        wrong_tag = list(transcript)
        wrong_tag[1] = wrong_tag[1].replace(
            "pneumaticcraft:sourdough_bread",
            "minecraft:bread",
        )
        errors = self.validate((wrong_tag, transcript, transcript))
        self.assertIn("commodity audit transcript mismatch", errors)

    def test_tag_registry_failure_cannot_be_hidden_by_old_success(self) -> None:
        transcript = self.transcript()
        failed = [
            "[AFTERLIGHT QUEST ITEM AUDIT] OK "
            f"{self.item_digest} {self.item_count} {self.nonce}",
            "[AFTERLIGHT QUEST COMMODITY AUDIT] INVALID "
            "c:foods/bread TAG_REGISTRY_MISSING",
            "[AFTERLIGHT QUEST COMMODITY AUDIT] FAILED "
            f"{self.contract['fixture_sha256']} {self.item_digest} {self.nonce}",
            *transcript,
        ]
        errors = self.validate((failed, transcript, transcript))
        self.assertIn(
            "commodity audit failure c:foods/bread TAG_REGISTRY_MISSING",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
