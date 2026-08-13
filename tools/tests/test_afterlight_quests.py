from __future__ import annotations

import ast
import copy
import hashlib
import importlib
import io
import json
import os
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import unittest
import zipfile
from collections import Counter
from dataclasses import fields
from pathlib import Path
from unittest import mock


tempfile.tempdir = str(Path(tempfile.gettempdir()).resolve())


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from live_install_support import requires_live_install


class StoryCohesionCompatibilityTests(unittest.TestCase):
    SOURCE_COMMIT = "7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25"
    APPROVED_COMMODITY_REPLACEMENTS: dict[str, str] = {}
    FIXTURE_PATH = (
        ROOT / "tools" / "fixtures" / "quests" / "story-cohesion-baseline.json"
    )
    QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"
    STORY_GROUP_ID = "4A20F33642175B95"
    IDENTITY_KINDS = (
        "chapter_group",
        "chapter",
        "image",
        "quest_link",
        "quest",
        "task",
        "reward",
        "reward_table",
        "reward_table_reward",
    )
    ORDERED_IDENTITY_KINDS = (
        "chapter_group",
        "image",
        "quest_link",
        "quest",
        "task",
        "reward",
        "reward_table_reward",
    )
    HYGIENE_CASES = (
        (
            "uuid",
            "fixture_note",
            "00000000-0000-0000-0000-000000000000",
            "UUID",
        ),
        ("player_name", "player_name", "redacted", "player identity field"),
        ("raw_progress", "task_progress", {}, "raw progress field"),
        ("secret_field", "access_token", "test-only", "secret field"),
        (
            "secret_value",
            "fixture_note",
            "-----BEGIN " + "PRIVATE KEY-----",
            "secret value",
        ),
        (
            "em_dash",
            "fixture_note",
            f"forbidden{chr(0x2014)}punctuation",
            "U+2014",
        ),
        (
            "windows_path",
            "fixture_note",
            "C:\\Users\\fixture\\quests",
            "Windows machine path",
        ),
        (
            "windows_unc_path",
            "fixture_note",
            "\\\\server\\share\\quests",
            "Windows machine path",
        ),
        (
            "unix_root",
            "fixture_note",
            "/home/fixture/quests",
            "Unix machine root",
        ),
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("afterlight_quests")

    def _compatibility_support(self):
        capture = getattr(self.quests, "capture_quest_corpus", None)
        compare = getattr(self.quests, "compare_quest_corpus", None)
        self.assertTrue(callable(capture), "capture_quest_corpus is missing")
        self.assertTrue(callable(compare), "compare_quest_corpus is missing")
        return capture, compare

    def _fixture(self) -> dict[str, object]:
        self.assertTrue(self.FIXTURE_PATH.is_file(), "compatibility fixture is missing")
        return json.loads(self.FIXTURE_PATH.read_text(encoding="utf-8"))

    def _baseline(self) -> dict[str, object]:
        fixture = self._fixture()
        self.assertEqual(fixture["schema_version"], 1)
        self.assertEqual(fixture["source_commit"], self.SOURCE_COMMIT)
        return fixture["corpus"]

    @staticmethod
    def _identity_corpus() -> dict[str, object]:
        return {
            "chapter_groups": {
                "chapter_groups": [
                    {"id": "0000000000000001", "order_index": "0"},
                    {"id": "0000000000000002", "order_index": "1"},
                ]
            },
            "chapters": {
                "0000000000000010.snbt": {
                    "filename": "0000000000000010",
                    "group": "0000000000000001",
                    "id": "0000000000000010",
                    "images": [
                        {"id": "0000000000000011", "x": "0.0d"},
                        {"id": "0000000000000012", "x": "1.0d"},
                    ],
                    "order_index": "0",
                    "quest_links": [
                        {
                            "id": "0000000000000030",
                            "linked_quest": "0000000000000020",
                            "x": "0.0d",
                            "y": "0.0d",
                        },
                        {
                            "id": "0000000000000031",
                            "linked_quest": "0000000000000021",
                            "x": "1.0d",
                            "y": "0.0d",
                        },
                    ],
                    "quests": [
                        {
                            "dependencies": [
                                "00000000000000A0",
                                "00000000000000A1",
                            ],
                            "id": "0000000000000020",
                            "rewards": [
                                {
                                    "id": "0000000000000050",
                                    "table_data": {
                                        "rewards": [
                                            {
                                                "id": "0000000000000080",
                                                "type": "xp",
                                                "xp": "1",
                                            },
                                            {
                                                "id": "0000000000000081",
                                                "type": "xp",
                                                "xp": "2",
                                            },
                                        ]
                                    },
                                    "table_id": "-1L",
                                    "type": "random",
                                },
                                {
                                    "id": "0000000000000051",
                                    "type": "xp",
                                    "xp": "3",
                                },
                            ],
                            "tasks": [
                                {
                                    "id": "0000000000000040",
                                    "type": "checkmark",
                                },
                                {
                                    "id": "0000000000000041",
                                    "type": "checkmark",
                                },
                            ],
                            "x": "0.0d",
                        },
                        {
                            "dependencies": [],
                            "id": "0000000000000021",
                            "rewards": [],
                            "tasks": [],
                            "x": "1.0d",
                        },
                    ],
                }
            },
            "language": {"en_us": {}},
            "reward_tables": {
                "0000000000000060.snbt": {
                    "id": "0000000000000060",
                    "rewards": [
                        {
                            "id": "0000000000000070",
                            "type": "xp",
                            "xp": "4",
                        },
                        {
                            "id": "0000000000000071",
                            "type": "xp",
                            "xp": "5",
                        },
                    ],
                }
            },
        }

    @staticmethod
    def _commodity_corpora() -> tuple[
        dict[str, object], dict[str, object], str
    ]:
        task_id = "0123456789ABCDE0"
        baseline = {
            "chapter_groups": {"chapter_groups": []},
            "chapters": {
                "0123456789ABCDE1.snbt": {
                    "id": "0123456789ABCDE1",
                    "group": "0123456789ABCDE2",
                    "quest_links": [],
                    "quests": [
                        {
                            "id": "0123456789ABCDE3",
                            "tasks": [
                                {
                                    "id": task_id,
                                    "type": "item",
                                    "item": {
                                        "count": "1",
                                        "id": "example:steel_ingot",
                                    },
                                    "count": "12L",
                                    "consume_items": False,
                                    "match_components": "fuzzy",
                                }
                            ],
                            "rewards": [],
                        }
                    ],
                }
            },
            "language": {"en_us": {}},
            "reward_tables": {},
        }
        current = copy.deepcopy(baseline)
        current["chapters"]["0123456789ABCDE1.snbt"]["quests"][0]["tasks"][
            0
        ]["item"] = {
            "count": "1",
            "id": "ftbfiltersystem:smart_filter",
            "components": {
                "ftbfiltersystem:filter": (
                    "ftbfiltersystem:item_tag(c:ingots/steel)"
                )
            },
        }
        return baseline, current, task_id

    @staticmethod
    def _identity_member(
        corpus: dict[str, object], kind: str
    ) -> tuple[dict[str, object], str]:
        chapter = corpus["chapters"]["0000000000000010.snbt"]
        quest = chapter["quests"][0]
        locations = {
            "chapter_group": (
                corpus["chapter_groups"]["chapter_groups"][0],
                "$.chapter_groups.chapter_groups[0].id",
            ),
            "chapter": (chapter, "$.chapters.0000000000000010.snbt.id"),
            "image": (
                chapter["images"][0],
                "$.chapters.0000000000000010.snbt.images[0].id",
            ),
            "quest_link": (
                chapter["quest_links"][0],
                "$.chapters.0000000000000010.snbt.quest_links[0].id",
            ),
            "quest": (
                quest,
                "$.chapters.0000000000000010.snbt.quests[0].id",
            ),
            "task": (
                quest["tasks"][0],
                "$.chapters.0000000000000010.snbt.quests[0].tasks[0].id",
            ),
            "reward": (
                quest["rewards"][0],
                "$.chapters.0000000000000010.snbt.quests[0].rewards[0].id",
            ),
            "reward_table": (
                corpus["reward_tables"]["0000000000000060.snbt"],
                "$.reward_tables.0000000000000060.snbt.id",
            ),
            "reward_table_reward": (
                corpus["reward_tables"]["0000000000000060.snbt"]["rewards"][0],
                "$.reward_tables.0000000000000060.snbt.rewards[0].id",
            ),
        }
        return locations[kind]

    @staticmethod
    def _identity_list(
        corpus: dict[str, object], kind: str
    ) -> tuple[list[dict[str, object]], str]:
        chapter = corpus["chapters"]["0000000000000010.snbt"]
        quest = chapter["quests"][0]
        locations = {
            "chapter_group": (
                corpus["chapter_groups"]["chapter_groups"],
                "$.chapter_groups.chapter_groups",
            ),
            "image": (
                chapter["images"],
                "$.chapters.0000000000000010.snbt.images",
            ),
            "quest_link": (
                chapter["quest_links"],
                "$.chapters.0000000000000010.snbt.quest_links",
            ),
            "quest": (
                chapter["quests"],
                "$.chapters.0000000000000010.snbt.quests",
            ),
            "task": (
                quest["tasks"],
                "$.chapters.0000000000000010.snbt.quests[0].tasks",
            ),
            "reward": (
                quest["rewards"],
                "$.chapters.0000000000000010.snbt.quests[0].rewards",
            ),
            "reward_table_reward": (
                corpus["reward_tables"]["0000000000000060.snbt"]["rewards"],
                "$.reward_tables.0000000000000060.snbt.rewards",
            ),
        }
        return locations[kind]

    @classmethod
    def _append_duplicate_identity(
        cls, corpus: dict[str, object], kind: str
    ) -> str:
        if kind == "chapter":
            duplicate_path = "$.chapters.7FFFFFFFFFFFFFF0.snbt.id"
            corpus["chapters"]["7FFFFFFFFFFFFFF0.snbt"] = copy.deepcopy(
                corpus["chapters"]["0000000000000010.snbt"]
            )
            return duplicate_path
        if kind == "reward_table":
            duplicate_path = "$.reward_tables.7FFFFFFFFFFFFFF1.snbt.id"
            corpus["reward_tables"]["7FFFFFFFFFFFFFF1.snbt"] = copy.deepcopy(
                corpus["reward_tables"]["0000000000000060.snbt"]
            )
            return duplicate_path
        members, collection_path = cls._identity_list(corpus, kind)
        members.append(copy.deepcopy(members[0]))
        return f"{collection_path}[{len(members) - 1}].id"

    @staticmethod
    def _new_identity_member(kind: str, identifier: str) -> dict[str, object]:
        members = {
            "chapter_group": {"id": identifier, "order_index": "9"},
            "image": {"id": identifier, "x": "9.0d"},
            "quest_link": {
                "id": identifier,
                "linked_quest": "0000000000000020",
                "x": "9.0d",
                "y": "9.0d",
            },
            "quest": {
                "dependencies": [],
                "id": identifier,
                "rewards": [],
                "tasks": [],
                "x": "9.0d",
            },
            "task": {"id": identifier, "type": "checkmark"},
            "reward": {"id": identifier, "type": "xp", "xp": "9"},
            "reward_table_reward": {
                "id": identifier,
                "type": "xp",
                "xp": "9",
            },
        }
        return members[kind]

    def _assert_mismatch_at(
        self,
        baseline: dict[str, object],
        current: dict[str, object],
        expected_path: str,
    ) -> None:
        _, compare = self._compatibility_support()
        errors = compare(baseline, current, commodity_replacements={})
        self.assertTrue(
            any(error.startswith(f"{expected_path}:") for error in errors),
            errors,
        )

    def test_fixture_comes_from_immutable_source(self) -> None:
        capture, _ = self._compatibility_support()
        fixture = self._fixture()

        archive = subprocess.run(
            [
                "git",
                "archive",
                "--format=tar",
                self.SOURCE_COMMIT,
                "config/ftbquests/quests",
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        with tempfile.TemporaryDirectory() as temporary_directory:
            extracted_root = Path(temporary_directory)
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as source_tar:
                source_tar.extractall(extracted_root, filter="data")
            source_corpus = capture(
                extracted_root / "config" / "ftbquests" / "quests"
            )

        self.assertEqual(fixture["corpus"], source_corpus)

    def test_current_corpus_satisfies_frozen_compatibility_contract(self) -> None:
        capture, compare = self._compatibility_support()
        fixture = self._fixture()
        current_corpus = capture(self.QUEST_ROOT)
        self.assertEqual(
            compare(
                fixture,
                current_corpus,
                commodity_replacements=self.APPROVED_COMMODITY_REPLACEMENTS,
            ),
            [],
        )

    def test_fixture_serialization_is_canonical_and_deterministic(self) -> None:
        capture, _ = self._compatibility_support()
        fixture = self._fixture()
        canonical_fixture = json.dumps(fixture, indent=2, sort_keys=True) + "\n"
        self.assertEqual(
            self.FIXTURE_PATH.read_text(encoding="utf-8"), canonical_fixture
        )
        self.assertNotIn(str(ROOT), canonical_fixture)
        self.assertNotIn("/private/", canonical_fixture)
        self.assertNotIn("/Users/", canonical_fixture)

        first_capture = json.dumps(
            capture(self.QUEST_ROOT), indent=2, sort_keys=True
        )
        second_capture = json.dumps(
            capture(self.QUEST_ROOT), indent=2, sort_keys=True
        )
        self.assertEqual(first_capture, second_capture)

    def test_approved_existing_field_changes_are_the_only_exceptions(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        current["language"]["en_us"][
            f"chapter_group.{self.STORY_GROUP_ID}.title"
        ] = "Story Signal"

        story_chapter_name, story_chapter = next(
            (name, chapter)
            for name, chapter in current["chapters"].items()
            if chapter["group"] == self.STORY_GROUP_ID
        )
        story_chapter["order_index"] = "10"
        story_quest_id = story_chapter["quests"][0]["id"]
        current["language"]["en_us"][
            f"quest.{story_quest_id}.quest_subtitle"
        ] = "Changed subtitle"
        current["language"]["en_us"][f"quest.{story_quest_id}.quest_desc"] = [
            "Changed description"
        ]
        story_chapter["quest_links"].append(
            {
                "id": "0123456789ABCDEF",
                "chapter": story_chapter_name.removesuffix(".snbt"),
                "quest": story_quest_id,
            }
        )

        self.assertEqual(
            compare(baseline, current, commodity_replacements={}),
            [],
        )

    def test_declared_commodity_replacement_freezes_all_other_task_fields(self) -> None:
        _, compare = self._compatibility_support()
        baseline, current, task_id = self._commodity_corpora()

        self.assertEqual(
            compare(
                baseline,
                current,
                commodity_replacements={task_id: "c:ingots/steel"},
            ),
            [],
        )
        undeclared_errors = compare(
            baseline,
            current,
            commodity_replacements={},
        )
        self.assertTrue(
            any(
                error.startswith(
                    "$.chapters.0123456789ABCDE1.snbt.quests[0].tasks[0].item:"
                )
                for error in undeclared_errors
            ),
            undeclared_errors,
        )

        for field, changed_value in (
            ("count", "13L"),
            ("consume_items", True),
            ("match_components", "strict"),
        ):
            with self.subTest(field=field):
                mutated = copy.deepcopy(current)
                mutated["chapters"]["0123456789ABCDE1.snbt"]["quests"][0][
                    "tasks"
                ][0][field] = changed_value
                errors = compare(
                    baseline,
                    mutated,
                    commodity_replacements={task_id: "c:ingots/steel"},
                )
                expected_path = (
                    "$.chapters.0123456789ABCDE1.snbt.quests[0].tasks[0]."
                    f"{field}"
                )
                self.assertTrue(
                    any(error.startswith(f"{expected_path}:") for error in errors),
                    errors,
                )

    def test_commodity_replacement_requires_exact_smart_filter_shape(self) -> None:
        _, compare = self._compatibility_support()
        baseline, current, task_id = self._commodity_corpora()
        item_path = "$.chapters.0123456789ABCDE1.snbt.quests[0].tasks[0].item"

        invalid_items = {
            "wrong_item": {
                "count": "1",
                "id": "ftbfiltersystem:item_tag",
                "components": {
                    "ftbfiltersystem:filter": (
                        "ftbfiltersystem:item_tag(c:ingots/steel)"
                    )
                },
            },
            "missing_count": {
                "id": "ftbfiltersystem:smart_filter",
                "components": {
                    "ftbfiltersystem:filter": (
                        "ftbfiltersystem:item_tag(c:ingots/steel)"
                    )
                },
            },
            "wrong_component": {
                "count": "1",
                "id": "ftbfiltersystem:smart_filter",
                "components": {
                    "ftbfiltersystem:filter": (
                        "ftbfiltersystem:item_tag(c:ingots/iron)"
                    )
                },
            },
            "extra_component": {
                "count": "1",
                "id": "ftbfiltersystem:smart_filter",
                "components": {
                    "example:extra": "forbidden",
                    "ftbfiltersystem:filter": (
                        "ftbfiltersystem:item_tag(c:ingots/steel)"
                    ),
                },
            },
        }
        for name, invalid_item in invalid_items.items():
            with self.subTest(name=name):
                mutated = copy.deepcopy(current)
                mutated["chapters"]["0123456789ABCDE1.snbt"]["quests"][0][
                    "tasks"
                ][0]["item"] = invalid_item
                errors = compare(
                    baseline,
                    mutated,
                    commodity_replacements={task_id: "c:ingots/steel"},
                )
                self.assertTrue(
                    any(error.startswith(f"{item_path}:") for error in errors),
                    errors,
                )

    def test_duplicate_commodity_declaration_fails_closed(self) -> None:
        _, compare = self._compatibility_support()
        baseline, current, task_id = self._commodity_corpora()

        class DuplicateDeclarations(dict[str, str]):
            def items(self):
                return [
                    (task_id, "c:ingots/steel"),
                    (task_id, "c:ingots/steel"),
                ]

        errors = compare(
            baseline,
            current,
            commodity_replacements=DuplicateDeclarations(),
        )
        self.assertTrue(
            any(
                error.startswith(f"$.commodity_replacements.{task_id}:")
                and "duplicate" in error
                for error in errors
            ),
            errors,
        )

    def test_duplicate_ids_fail_for_every_supported_identity_kind(self) -> None:
        _, compare = self._compatibility_support()
        for corpus_side in ("baseline", "current"):
            for kind in self.IDENTITY_KINDS:
                with self.subTest(corpus_side=corpus_side, kind=kind):
                    baseline = self._identity_corpus()
                    current = copy.deepcopy(baseline)
                    target = baseline if corpus_side == "baseline" else current
                    duplicate_path = self._append_duplicate_identity(target, kind)
                    errors = compare(
                        baseline,
                        current,
                        commodity_replacements={},
                    )
                    self.assertTrue(
                        any(
                            error.startswith(f"{duplicate_path}:")
                            and f"duplicate {kind} ID" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_duplicate_frozen_quest_with_changed_payload_fails_closed(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        quests = current["chapters"]["0000000000000010.snbt"]["quests"]
        duplicate = copy.deepcopy(quests[0])
        duplicate["x"] = "999.0d"
        quests.append(duplicate)

        duplicate_path = "$.chapters.0000000000000010.snbt.quests[2].id"
        errors = compare(baseline, current, commodity_replacements={})
        self.assertTrue(
            any(
                error.startswith(f"{duplicate_path}:")
                and "duplicate quest ID" in error
                for error in errors
            ),
            errors,
        )

    def test_duplicate_chapter_id_across_files_fails_at_second_file(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        duplicate_path = self._append_duplicate_identity(current, "chapter")

        errors = compare(baseline, current, commodity_replacements={})
        self.assertTrue(
            any(
                error.startswith(f"{duplicate_path}:")
                and "$.chapters.0000000000000010.snbt.id" in error
                for error in errors
            ),
            errors,
        )

    def test_missing_ids_fail_for_every_supported_identity_kind(self) -> None:
        _, compare = self._compatibility_support()
        for corpus_side in ("baseline", "current"):
            for kind in self.IDENTITY_KINDS:
                with self.subTest(corpus_side=corpus_side, kind=kind):
                    baseline = self._identity_corpus()
                    current = copy.deepcopy(baseline)
                    target = baseline if corpus_side == "baseline" else current
                    member, missing_path = self._identity_member(target, kind)
                    member.pop("id")
                    errors = compare(
                        baseline,
                        current,
                        commodity_replacements={},
                    )
                    self.assertTrue(
                        any(
                            error.startswith(f"{missing_path}:")
                            and f"{kind} identity is missing" in error
                            for error in errors
                        ),
                        errors,
                    )

    def test_cross_kind_collisions_fail_in_baseline_and_current(self) -> None:
        _, compare = self._compatibility_support()
        for corpus_side in ("baseline", "current"):
            with self.subTest(corpus_side=corpus_side):
                baseline = self._identity_corpus()
                current = copy.deepcopy(baseline)
                target = baseline if corpus_side == "baseline" else current
                quest_id = target["chapters"]["0000000000000010.snbt"][
                    "quests"
                ][0]["id"]
                task = target["chapters"]["0000000000000010.snbt"]["quests"][
                    0
                ]["tasks"][0]
                task["id"] = quest_id
                collision_path = (
                    "$.chapters.0000000000000010.snbt.quests[0].tasks[0].id"
                )
                errors = compare(
                    baseline,
                    current,
                    commodity_replacements={},
                )
                self.assertTrue(
                    any(
                        error.startswith(f"{collision_path}:")
                        and "cross-kind ID collision" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_removed_frozen_id_cannot_be_reused_under_another_kind(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        chapter = current["chapters"]["0000000000000010.snbt"]
        removed_quest_id = chapter["quests"].pop(0)["id"]
        chapter["quests"][0]["tasks"].append(
            {"id": removed_quest_id, "type": "checkmark"}
        )
        reused_path = (
            "$.chapters.0000000000000010.snbt.quests[0].tasks[0].id"
        )

        errors = compare(baseline, current, commodity_replacements={})
        self.assertTrue(
            any(
                error.startswith(f"{reused_path}:")
                and "reuses baseline quest ID" in error
                for error in errors
            ),
            errors,
        )

    def test_unique_entities_can_be_inserted_at_front_and_middle(self) -> None:
        _, compare = self._compatibility_support()
        for kind_index, kind in enumerate(self.ORDERED_IDENTITY_KINDS, start=1):
            for position, position_name in ((0, "front"), (1, "middle")):
                with self.subTest(kind=kind, position=position_name):
                    baseline = self._identity_corpus()
                    current = copy.deepcopy(baseline)
                    members, _ = self._identity_list(current, kind)
                    identifier = f"700000000000{kind_index:02X}{position:02X}"
                    members.insert(
                        position,
                        self._new_identity_member(kind, identifier),
                    )
                    self.assertEqual(
                        compare(
                            baseline,
                            current,
                            commodity_replacements={},
                        ),
                        [],
                    )

    def test_unique_chapter_and_reward_table_additions_are_allowed(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        current["chapters"]["7000000000000010.snbt"] = {
            "filename": "7000000000000010",
            "group": "0000000000000001",
            "id": "7000000000000010",
            "images": [],
            "order_index": "9",
            "quest_links": [],
            "quests": [],
        }
        current["reward_tables"]["7000000000000020.snbt"] = {
            "id": "7000000000000020",
            "rewards": [],
        }
        self.assertEqual(
            compare(baseline, current, commodity_replacements={}),
            [],
        )

    def test_frozen_entity_relative_order_is_preserved(self) -> None:
        _, compare = self._compatibility_support()
        for kind in self.ORDERED_IDENTITY_KINDS:
            with self.subTest(kind=kind):
                baseline = self._identity_corpus()
                current = copy.deepcopy(baseline)
                members, collection_path = self._identity_list(current, kind)
                members[0], members[1] = members[1], members[0]
                errors = compare(
                    baseline,
                    current,
                    commodity_replacements={},
                )
                self.assertTrue(
                    any(
                        error.startswith(f"{collection_path}:")
                        and "frozen ID relative order changed" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_dependency_reordering_remains_positional(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        dependencies = current["chapters"]["0000000000000010.snbt"][
            "quests"
        ][0]["dependencies"]
        dependencies[0], dependencies[1] = dependencies[1], dependencies[0]

        errors = compare(baseline, current, commodity_replacements={})
        for index in (0, 1):
            expected_path = (
                "$.chapters.0000000000000010.snbt.quests[0].dependencies"
                f"[{index}]"
            )
            self.assertTrue(
                any(error.startswith(f"{expected_path}:") for error in errors),
                errors,
            )

    def test_mismatch_path_uses_current_index_after_unique_insertion(self) -> None:
        _, compare = self._compatibility_support()
        baseline = self._identity_corpus()
        current = copy.deepcopy(baseline)
        quests = current["chapters"]["0000000000000010.snbt"]["quests"]
        quests.insert(
            0,
            self._new_identity_member("quest", "7000000000000030"),
        )
        quests[1]["x"] = "999.0d"

        errors = compare(baseline, current, commodity_replacements={})
        expected_path = "$.chapters.0000000000000010.snbt.quests[1].x"
        self.assertTrue(
            any(error.startswith(f"{expected_path}:") for error in errors),
            errors,
        )
        self.assertFalse(
            any(
                error.startswith(
                    "$.chapters.0000000000000010.snbt.quests[0].x:"
                )
                for error in errors
            ),
            errors,
        )

    def test_current_corpus_hygiene_rejects_every_binding_category(self) -> None:
        _, compare = self._compatibility_support()
        for name, key, value, marker in self.HYGIENE_CASES:
            with self.subTest(name=name):
                baseline = self._identity_corpus()
                current = copy.deepcopy(baseline)
                current["language"]["en_us"][key] = value
                errors = compare(
                    baseline,
                    current,
                    commodity_replacements={},
                )
                expected_path = f"$.language.en_us.{key}"
                self.assertTrue(
                    any(
                        error.startswith(f"{expected_path}:")
                        and marker in error
                        for error in errors
                    ),
                    errors,
                )

    def test_fixture_wrapper_metadata_hygiene_fails_closed(self) -> None:
        _, compare = self._compatibility_support()
        for name, key, value, marker in self.HYGIENE_CASES:
            with self.subTest(name=name):
                corpus = self._identity_corpus()
                fixture = {
                    "corpus": corpus,
                    "schema_version": 1,
                    "source_commit": self.SOURCE_COMMIT,
                    key: value,
                }
                errors = compare(
                    fixture,
                    copy.deepcopy(corpus),
                    commodity_replacements={},
                )
                self.assertTrue(
                    any(
                        error.startswith(f"$.{key}:") and marker in error
                        for error in errors
                    ),
                    errors,
                )

    def test_changed_task_count_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name, quest_index, task_index = next(
            (chapter_name, quest_index, task_index)
            for chapter_name, chapter in current["chapters"].items()
            for quest_index, quest in enumerate(chapter["quests"])
            for task_index, task in enumerate(quest["tasks"])
            if "count" in task
        )
        current["chapters"][chapter_name]["quests"][quest_index]["tasks"][
            task_index
        ]["count"] = "999L"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.quests[{quest_index}].tasks"
            f"[{task_index}].count",
        )

    def test_changed_reward_payload_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name, quest_index, reward_index = next(
            (chapter_name, quest_index, reward_index)
            for chapter_name, chapter in current["chapters"].items()
            for quest_index, quest in enumerate(chapter["quests"])
            for reward_index, reward in enumerate(quest["rewards"])
            if isinstance(reward.get("item"), dict) and "id" in reward["item"]
        )
        current["chapters"][chapter_name]["quests"][quest_index]["rewards"][
            reward_index
        ]["item"]["id"] = "minecraft:barrier"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.quests[{quest_index}].rewards"
            f"[{reward_index}].item.id",
        )

    def test_changed_quest_flag_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name, quest_index, flag = next(
            (chapter_name, quest_index, flag)
            for chapter_name, chapter in current["chapters"].items()
            for quest_index, quest in enumerate(chapter["quests"])
            for flag in ("optional", "can_repeat", "invisible_until_completed")
            if flag in quest and isinstance(quest[flag], bool)
        )
        quest = current["chapters"][chapter_name]["quests"][quest_index]
        quest[flag] = not quest[flag]
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.quests[{quest_index}].{flag}",
        )

    def test_changed_dependency_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name, quest_index = next(
            (chapter_name, quest_index)
            for chapter_name, chapter in current["chapters"].items()
            for quest_index, quest in enumerate(chapter["quests"])
            if quest.get("dependencies")
        )
        current["chapters"][chapter_name]["quests"][quest_index]["dependencies"][
            0
        ] = "0123456789ABCDEF"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.quests[{quest_index}].dependencies[0]",
        )

    def test_changed_title_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        title_key = next(
            key
            for key in current["language"]["en_us"]
            if key.startswith("quest.") and key.endswith(".title")
        )
        current["language"]["en_us"][title_key] = "Mutated title"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.language.en_us.{title_key}",
        )

    def test_changed_icon_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name = next(
            name
            for name, chapter in current["chapters"].items()
            if isinstance(chapter.get("icon"), dict) and "id" in chapter["icon"]
        )
        current["chapters"][chapter_name]["icon"]["id"] = "minecraft:barrier"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.icon.id",
        )

    def test_changed_owner_fails_at_exact_path(self) -> None:
        baseline = self._baseline()
        current = copy.deepcopy(baseline)
        chapter_name = next(iter(current["chapters"]))
        current["chapters"][chapter_name]["group"] = "0123456789ABCDEF"
        self._assert_mismatch_at(
            baseline,
            current,
            f"$.chapters.{chapter_name}.group",
        )


class Plan06GateDependencyTests(unittest.TestCase):
    GATE_ITEMS = {
        "GATE_KINETIC": ("kubejs:gate_kinetic_frame", "Kinetic Frame"),
        "GATE_INDUSTRIAL": ("kubejs:gate_industrial_anchor", "Industrial Anchor"),
        "GATE_ISOTOPIC": ("kubejs:gate_isotopic_core", "Isotopic Core"),
        "GATE_LATTICE": ("kubejs:gate_lattice_matrix", "Lattice Matrix"),
        "STABILIZER": ("kubejs:undercurrent_stabilizer", "Undercurrent Stabilizer"),
        "GATE_CORE": ("kubejs:gate_of_return_core", "Gate of Return Core"),
    }
    CERTIFICATION_FINALES = (
        "5ADAE277C9FEF0F1",
        "3107D8813D59B2FF",
        "66CDE7B061D8DA5C",
        "42EE25F560AE65CD",
        "61F5D15817ED5EFD",
        "7C9EA276C2D84333",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("afterlight_quests")
        cls.catalog = cls.quests.build_catalog()
        cls.quests_by_id = {
            quest.id: quest
            for chapter in cls.catalog
            for quest in chapter.quests
        }

    def test_gate_items_are_registered_named_and_stack_one(self) -> None:
        registry = (
            ROOT / "kubejs" / "startup_scripts" / "afterlight" / "registry.js"
        ).read_text(encoding="utf-8")
        language = json.loads(
            (ROOT / "kubejs" / "assets" / "kubejs" / "lang" / "en_us.json")
            .read_text(encoding="utf-8")
        )

        for constant, (item_id, display_name) in self.GATE_ITEMS.items():
            path = item_id.split(":", 1)[1]
            with self.subTest(item_id=item_id):
                registration = re.search(
                    rf"event\.create\('{re.escape(path)}'\)(.*?)(?=\n\s*event\.create|\n\}}\))",
                    registry,
                    re.DOTALL,
                )
                self.assertIsNotNone(registration, f"missing registry entry for {item_id}")
                self.assertIn(".rarity('epic')", registration.group(1))
                self.assertIn(".maxStackSize(1)", registration.group(1))
                language_key = f"item.kubejs.{path}"
                self.assertIn(language_key, language)
                self.assertEqual(language[f"item.kubejs.{path}"], display_name)

        gate_core = re.search(
            r"event\.create\('gate_of_return_core'\)(.*?)(?=\n\s*event\.create|\n\}\))",
            registry,
            re.DOTALL,
        )
        self.assertIsNotNone(gate_core)
        self.assertIn(".glow(true)", gate_core.group(1))

    def test_gate_items_are_constants(self) -> None:
        constants = (
            ROOT / "kubejs" / "server_scripts" / "afterlight" / "_constants.js"
        ).read_text(encoding="utf-8")
        for constant, (item_id, _display_name) in self.GATE_ITEMS.items():
            with self.subTest(item_id=item_id):
                self.assertRegex(
                    constants,
                    rf"\b{constant}:\s*'{re.escape(item_id)}'",
                )

    def test_gate_items_are_allowlisted(self) -> None:
        for _constant, (item_id, _display_name) in self.GATE_ITEMS.items():
            with self.subTest(item_id=item_id):
                self.assertIn(item_id, self.quests.KUBEJS_ITEM_ALLOWLIST)

    def test_ascendancy_seal_stacks_to_one(self) -> None:
        registry = (
            ROOT / "kubejs" / "startup_scripts" / "afterlight" / "registry.js"
        ).read_text(encoding="utf-8")
        seal = re.search(
            r"event\.create\('ascendancy_seal'\)(.*?)(?=\n\s*event\.create|\n\}\))",
            registry,
            re.DOTALL,
        )
        self.assertIn(".maxStackSize(1)", seal.group(1))

    def test_gate_sprites_are_unique_transparent_32_by_32_pngs(self) -> None:
        texture_root = ROOT / "kubejs" / "assets" / "kubejs" / "textures" / "item"
        sprite_bytes = []
        for item_id, _display_name in self.GATE_ITEMS.values():
            path = texture_root / f"{item_id.split(':', 1)[1]}.png"
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"missing Gate sprite {path.name}")
                data = path.read_bytes()
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                self.assertEqual(data[12:16], b"IHDR")
                width, height, bit_depth, color_type = struct.unpack(">IIBB", data[16:26])
                self.assertEqual((width, height), (32, 32))
                self.assertEqual(bit_depth, 8)
                self.assertIn(color_type, (4, 6), "sprite PNG must include alpha")
                sprite_bytes.append(data)
        self.assertEqual(len(set(sprite_bytes)), len(self.GATE_ITEMS))

    def test_quest_spec_progression_mode_is_validated_and_rendered(self) -> None:
        self.assertIn(
            "progression_mode",
            {field.name for field in fields(self.quests.QuestSpec)},
        )
        quest = self.quests.QuestSpec(
            slug="story/test/linear",
            title="Linear",
            description=("Linear progression fixture.",),
            x=0.0,
            y=0.0,
            progression_mode="linear",
        )
        chapter = self.quests.ChapterSpec(
            slug="story/test-linear",
            title="Linear Test",
            group=self.quests.GroupSpec("test", "Test", "2AAAAAAAAAAAAAAA"),
            icon="minecraft:stone_pickaxe",
            order_index=0,
            quests=(quest,),
        )

        self.assertIn('progression_mode: "linear"', self.quests.render_chapter(chapter))
        with self.assertRaisesRegex(ValueError, "progression mode"):
            self.quests.QuestSpec(
                slug="story/test/invalid-progression",
                title="Invalid",
                description=("Invalid progression fixture.",),
                x=0.0,
                y=0.0,
                progression_mode="inherited",
            )

    def test_authoritative_gate_quests_use_exact_dependencies_and_tasks(self) -> None:
        expected = {
            "7CB2D7D361BEA4C4": (
                self.CERTIFICATION_FINALES,
                (("74AB10F5C91F1022", "checkmark", {}),),
            ),
            "71B2919DF12C6845": (
                (
                    "10EDD2BED35BE9E3",
                    "752C3E53CA89C92D",
                    "21A99D99B372916F",
                    "3497EFDF016FAFD7",
                ),
                (
                    ("3A12D2169F1CB1B8", "item", "kubejs:schematic_kinetic_frame"),
                    ("74435064B9C0A86F", "item", "kubejs:schematic_industrial_anchor"),
                    ("030D638C9452FB47", "item", "kubejs:schematic_isotopic_core"),
                    ("23F46A9140462F95", "item", "kubejs:schematic_lattice_matrix"),
                ),
            ),
            "2D6ACF1CCBC7B4F2": (
                (
                    "0CE6F6160F721A8A",
                    "18EABED18B5B2ECF",
                    *self.CERTIFICATION_FINALES,
                    "6524EE78235F0942",
                ),
                (("3BFA32444B48A6A0", "checkmark", {}),),
            ),
        }

        for quest_id, (dependencies, tasks) in expected.items():
            quest = self.quests_by_id[quest_id]
            with self.subTest(quest_id=quest_id):
                self.assertEqual(quest.dependency_ids, dependencies)
                self.assertFalse(any(task.task_type == "gamestage" for task in quest.tasks))
                actual_tasks = tuple(
                    (
                        task.id,
                        task.task_type,
                        task.data if task.task_type == "checkmark" else task.data["item"]["id"],
                    )
                    for task in quest.tasks
                )
                self.assertEqual(actual_tasks, tasks)
                self.assertNotIn("team_reward", self.quests.render_chapter(
                    next(chapter for chapter in self.catalog if quest in chapter.quests)
                ))
                self.assertNotIn("team_stage", self.quests.render_chapter(
                    next(chapter for chapter in self.catalog if quest in chapter.quests)
                ))

        four_keys = self.quests_by_id["71B2919DF12C6845"]
        for task in four_keys.tasks:
            with self.subTest(four_keys_task=task.id):
                self.assertIn("count", task.data)
                self.assertEqual(task.data["count"], self.quests.SnbtLong(1))
                self.assertFalse(task.data["consume_items"])

    def assert_generated_authoritative_gate_graph(self, quest_root: Path) -> None:
        from afterlight_quests.builder import _parse_snbt

        quests = {}
        for path in sorted((quest_root / "chapters").glob("*.snbt")):
            chapter = _parse_snbt(path.read_text(encoding="utf-8"))
            quests.update({quest["id"]: quest for quest in chapter["quests"]})

        expected = {
            "7CB2D7D361BEA4C4": {
                "dependencies": self.CERTIFICATION_FINALES,
                "progression_mode": "linear",
                "tasks": (
                    {"id": "74AB10F5C91F1022", "type": "checkmark"},
                ),
            },
            "71B2919DF12C6845": {
                "dependencies": (
                    "10EDD2BED35BE9E3",
                    "752C3E53CA89C92D",
                    "21A99D99B372916F",
                    "3497EFDF016FAFD7",
                ),
                "progression_mode": "linear",
                "tasks": (
                    {
                        "id": "3A12D2169F1CB1B8",
                        "type": "item",
                        "item": {
                            "count": "1",
                            "id": "kubejs:schematic_kinetic_frame",
                        },
                        "count": "1L",
                        "consume_items": False,
                    },
                    {
                        "id": "74435064B9C0A86F",
                        "type": "item",
                        "item": {
                            "count": "1",
                            "id": "kubejs:schematic_industrial_anchor",
                        },
                        "count": "1L",
                        "consume_items": False,
                    },
                    {
                        "id": "030D638C9452FB47",
                        "type": "item",
                        "item": {
                            "count": "1",
                            "id": "kubejs:schematic_isotopic_core",
                        },
                        "count": "1L",
                        "consume_items": False,
                    },
                    {
                        "id": "23F46A9140462F95",
                        "type": "item",
                        "item": {
                            "count": "1",
                            "id": "kubejs:schematic_lattice_matrix",
                        },
                        "count": "1L",
                        "consume_items": False,
                    },
                ),
            },
            "2D6ACF1CCBC7B4F2": {
                "dependencies": (
                    "0CE6F6160F721A8A",
                    "18EABED18B5B2ECF",
                    *self.CERTIFICATION_FINALES,
                    "6524EE78235F0942",
                ),
                "progression_mode": "linear",
                "tasks": (
                    {"id": "3BFA32444B48A6A0", "type": "checkmark"},
                ),
            },
        }

        for quest_id, fields in expected.items():
            quest = quests[quest_id]
            self.assertEqual(
                tuple(quest["dependencies"]),
                fields["dependencies"],
                f"generated dependencies differ for {quest_id}",
            )
            self.assertEqual(
                quest.get("progression_mode"),
                fields["progression_mode"],
                f"generated progression mode differs for {quest_id}",
            )
            self.assertEqual(
                tuple(quest["tasks"]),
                fields["tasks"],
                f"generated tasks differ for {quest_id}",
            )

    def test_generated_authoritative_gate_graph_is_exact(self) -> None:
        self.assert_generated_authoritative_gate_graph(
            ROOT / "config" / "ftbquests" / "quests"
        )

    def test_generated_authoritative_gate_graph_rejects_dependency_mutation(self) -> None:
        source_root = ROOT / "config" / "ftbquests" / "quests"
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = Path(temp_dir) / "quests"
            shutil.copytree(source_root, quest_root)
            chapter_path = quest_root / "chapters" / "4402713763771CFA.snbt"
            original = chapter_path.read_text(encoding="utf-8")
            mutated = original.replace(
                '"10EDD2BED35BE9E3"',
                '"0000000000000000"',
                1,
            )
            self.assertNotEqual(mutated, original)
            chapter_path.write_text(mutated, encoding="utf-8")

            with self.assertRaisesRegex(
                AssertionError,
                "generated dependencies differ for 71B2919DF12C6845",
            ):
                self.assert_generated_authoritative_gate_graph(quest_root)

    def test_infrastructure_and_architect_quests_are_explicitly_linear(self) -> None:
        chapters = {
            chapter.id: chapter
            for chapter in self.catalog
        }
        infrastructure = chapters["5070DE6E2B300F4B"]
        architect = chapters["4402713763771CFA"]

        for chapter in (infrastructure, architect):
            for quest in chapter.quests:
                with self.subTest(chapter=chapter.title, quest=quest.id):
                    self.assertEqual(getattr(quest, "progression_mode", None), "linear")
                    self.assertIn(
                        'progression_mode: "linear"',
                        self.quests.render_chapter(chapter),
                    )

        self.assertEqual(
            getattr(self.quests_by_id["6524EE78235F0942"], "progression_mode", None),
            "linear",
        )
        self.assertEqual(
            getattr(self.quests_by_id["72446D404001B38D"], "progression_mode", None),
            "linear",
        )

    def test_task_one_counts_and_generated_audit_are_exact(self) -> None:
        quest_root = ROOT / "config" / "ftbquests" / "quests"
        counts = self.quests.count_quests(quest_root)
        reward_tables = tuple(
            (ROOT / "config" / "ftbquests" / "quests" / "reward_tables").glob("*.snbt")
        )
        audit = (
            ROOT
            / "kubejs"
            / "server_scripts"
            / "afterlight"
            / "generated_quest_item_audit.js"
        ).read_text(encoding="utf-8")

        self.assertEqual(
            (counts.chapters, counts.quests, counts.tasks, counts.rewards),
            (47, 315, 336, 439),
        )
        self.assertEqual(len(reward_tables), 6)
        for item_id, _display_name in self.GATE_ITEMS.values():
            self.assertIn(f'  "{item_id}"', audit)


class Plan06ActIVContractTests(unittest.TestCase):
    CHAPTERS = (
        (
            "7E9B015A32C6D980",
            "story/17-five-impossible-parts",
            17,
            "kubejs:gate_kinetic_frame",
            (
                "0055C66103106D86", "52FE1624DCCE878F", "50775CE87FAA4EB7",
                "7F064705A3CAB2E6", "39C1F24EABBB34A3", "144473B8267DBC28",
            ),
        ),
        (
            "6671EBE257F914CB",
            "story/18-cascade-truth",
            18,
            "minecraft:echo_shard",
            (
                "5468299A2A931991", "7EA7B2C8F11BB7A3", "0EEFDD9E6CFB69E6",
                "29D7871AFBE3A54A", "701505FDCCA53DFA", "462B11BD8C58BF6F",
            ),
        ),
        (
            "6C4AE5CE13773438",
            "story/19-gate-of-return",
            19,
            "kubejs:gate_of_return_core",
            (
                "36D0902A2921C44E", "66AD5C821947DF8E", "1A68D1245CD980BD",
                "6F3663F4C6D20255", "53B9BC5F498953D5", "31C9557D2F51238F",
            ),
        ),
        (
            "245BADE04399406C",
            "story/20-afterlight",
            20,
            "kubejs:ascendancy_seal",
            (
                "51649E106286AA63", "7ECCF0521DFCBED5", "1B523415541BD700",
                "4DD9F3D1913499F3", "7EE7B9B28787F8CC", "7E6A0AC031F7F484",
            ),
        ),
    )
    QUEST_SLUGS = (
        "kinetic-frame", "industrial-anchor", "isotopic-core", "lattice-matrix",
        "undercurrent-stabilizer", "five-impossible-parts",
        "eleven-second-window", "inbound-address", "order-i-gave",
        "warning-i-deleted", "decision-engine", "cascade-truth",
        "monument-footprint", "separate-grid", "gate-of-return-core",
        "anchor-and-contain", "eleven-seconds", "gate-of-return",
        "answering-sky", "stay", "return", "build", "choice-is-not-a-lock",
        "afterlight",
    )
    CHAPTER_TITLES = {
        "7E9B015A32C6D980": "Five Impossible Parts",
        "6671EBE257F914CB": "The Cascade Truth",
        "6C4AE5CE13773438": "Gate of Return",
        "245BADE04399406C": "Afterlight",
    }
    QUEST_TITLES = {
        "0055C66103106D86": "Kinetic Frame",
        "52FE1624DCCE878F": "Industrial Anchor",
        "50775CE87FAA4EB7": "Isotopic Core",
        "7F064705A3CAB2E6": "Lattice Matrix",
        "39C1F24EABBB34A3": "Undercurrent Stabilizer",
        "144473B8267DBC28": "Five Impossible Parts",
        "5468299A2A931991": "Eleven-Second Window",
        "7EA7B2C8F11BB7A3": "Inbound Address",
        "0EEFDD9E6CFB69E6": "The Order I Gave",
        "29D7871AFBE3A54A": "The Warning I Deleted",
        "701505FDCCA53DFA": "Decision Engine",
        "462B11BD8C58BF6F": "The Cascade Truth",
        "36D0902A2921C44E": "Monument Footprint",
        "66AD5C821947DF8E": "Separate Grid",
        "1A68D1245CD980BD": "Gate of Return Core",
        "6F3663F4C6D20255": "Anchor and Contain",
        "53B9BC5F498953D5": "Eleven Seconds",
        "31C9557D2F51238F": "Gate of Return",
        "51649E106286AA63": "Answering Sky",
        "7ECCF0521DFCBED5": "Stay",
        "1B523415541BD700": "Return",
        "4DD9F3D1913499F3": "Build",
        "7EE7B9B28787F8CC": "Choice Is Not a Lock",
        "7E6A0AC031F7F484": "Afterlight",
    }
    EXPECTED_SEAL_OCCURRENCES = Counter((
        (
            "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
            'icon: { id: "kubejs:ascendancy_seal" }',
        ),
        (
            "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
            'item: { count: 1, id: "kubejs:ascendancy_seal" }',
        ),
        (
            "config/ftbquests/quests/chapters/3FF4AF7B0C73F058.snbt",
            'item: { count: 1, id: "kubejs:ascendancy_seal" }',
        ),
        (
            "kubejs/assets/kubejs/lang/en_us.json",
            '"item.kubejs.ascendancy_seal": "Ascendancy Seal",',
        ),
        (
            "kubejs/server_scripts/afterlight/_constants.js",
            "SEAL: 'kubejs:ascendancy_seal',",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "C: 'minecraft:diamond', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "C: 'minecraft:ender_eye', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "I: 'minecraft:iron_ingot', R: 'minecraft:redstone', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "countTwoKeys.Z = Item.of(AFTERLIGHT.SEAL, 2)",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 2) {",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 1) {",
        ),
        (
            "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
            '"kubejs:ascendancy_seal",',
        ),
        (
            "kubejs/startup_scripts/afterlight/registry.js",
            "event.create('ascendancy_seal')",
        ),
    ))
    TASKS = {
        "0055C66103106D86": ("586F94BC6A6D08EA", "item", "kubejs:gate_kinetic_frame", "1L"),
        "52FE1624DCCE878F": ("262F1E36525F23DC", "item", "kubejs:gate_industrial_anchor", "1L"),
        "50775CE87FAA4EB7": ("1FAFC12F3779D20A", "item", "kubejs:gate_isotopic_core", "1L"),
        "7F064705A3CAB2E6": ("56F8BDF69E27EB09", "item", "kubejs:gate_lattice_matrix", "1L"),
        "39C1F24EABBB34A3": ("123B3D197A42CCEC", "item", "kubejs:undercurrent_stabilizer", "1L"),
        "144473B8267DBC28": ("42F99C5AFE250994", "checkmark", None, None),
        "5468299A2A931991": ("769EB9F91F23A058", "checkmark", None, None),
        "7EA7B2C8F11BB7A3": ("338D9A310F981342", "checkmark", None, None),
        "0EEFDD9E6CFB69E6": ("1ADC93AFE7A07EE2", "checkmark", None, None),
        "29D7871AFBE3A54A": ("476CF5B621B2F5DC", "checkmark", None, None),
        "701505FDCCA53DFA": ("72B91DC86514B2F4", "checkmark", None, None),
        "462B11BD8C58BF6F": ("1F72EF1FDDBEFDB1", "checkmark", None, None),
        "36D0902A2921C44E": ("151A464CC4D650A3", "item", "create:mechanical_crafter", "49L"),
        "66AD5C821947DF8E": ("6E494144394F75AF", "forge_energy", None, "1000000000L"),
        "1A68D1245CD980BD": ("568026383F54186C", "item", "kubejs:gate_of_return_core", "1L"),
        "6F3663F4C6D20255": ("1FDF7F09F581B25C", "checkmark", None, None),
        "53B9BC5F498953D5": (
            "645F98B8FAD4A1E5",
            "advancement",
            "afterlight:gate_opened",
            None,
        ),
        "31C9557D2F51238F": ("7828C31B03045AC0", "checkmark", None, None),
        "51649E106286AA63": ("415BBA206B34805E", "checkmark", None, None),
        "7ECCF0521DFCBED5": ("2B8333FDEE6B6D90", "checkmark", None, None),
        "1B523415541BD700": ("490D864D07C16993", "checkmark", None, None),
        "4DD9F3D1913499F3": ("3D07F572A39DCE89", "checkmark", None, None),
        "7EE7B9B28787F8CC": ("57D5E84BE50C3815", "checkmark", None, None),
        "7E6A0AC031F7F484": ("2BFD5EB16E861768", "checkmark", None, None),
    }
    DEPENDENCIES = {
        "0055C66103106D86": ("72446D404001B38D", "10EDD2BED35BE9E3"),
        "52FE1624DCCE878F": ("72446D404001B38D", "752C3E53CA89C92D"),
        "50775CE87FAA4EB7": ("72446D404001B38D", "21A99D99B372916F"),
        "7F064705A3CAB2E6": ("72446D404001B38D", "3497EFDF016FAFD7"),
        "39C1F24EABBB34A3": ("72446D404001B38D", "07338DE0FE8114CF"),
        "144473B8267DBC28": ("0055C66103106D86", "52FE1624DCCE878F", "50775CE87FAA4EB7", "7F064705A3CAB2E6", "39C1F24EABBB34A3"),
        "5468299A2A931991": ("144473B8267DBC28",),
        "7EA7B2C8F11BB7A3": ("5468299A2A931991",),
        "0EEFDD9E6CFB69E6": ("7EA7B2C8F11BB7A3",),
        "29D7871AFBE3A54A": ("7EA7B2C8F11BB7A3",),
        "701505FDCCA53DFA": ("0EEFDD9E6CFB69E6", "29D7871AFBE3A54A"),
        "462B11BD8C58BF6F": ("701505FDCCA53DFA",),
        "36D0902A2921C44E": ("462B11BD8C58BF6F",),
        "66AD5C821947DF8E": ("462B11BD8C58BF6F",),
        "1A68D1245CD980BD": ("36D0902A2921C44E", "66AD5C821947DF8E"),
        "6F3663F4C6D20255": ("1A68D1245CD980BD",),
        "53B9BC5F498953D5": ("6F3663F4C6D20255",),
        "31C9557D2F51238F": ("53B9BC5F498953D5",),
        "51649E106286AA63": ("31C9557D2F51238F",),
        "7ECCF0521DFCBED5": ("51649E106286AA63",),
        "1B523415541BD700": ("51649E106286AA63",),
        "4DD9F3D1913499F3": ("51649E106286AA63",),
        "7EE7B9B28787F8CC": ("7ECCF0521DFCBED5", "1B523415541BD700", "4DD9F3D1913499F3"),
        "7E6A0AC031F7F484": ("7EE7B9B28787F8CC",),
    }
    REWARDS = {
        "0055C66103106D86": (("7DDF59C2E8611A33", "item", "kubejs:requisition_chit", 2),),
        "52FE1624DCCE878F": (("773BE066DAA64F1E", "item", "kubejs:requisition_chit", 2),),
        "50775CE87FAA4EB7": (("51D958EF8F96550A", "item", "kubejs:requisition_chit", 2),),
        "7F064705A3CAB2E6": (("7C2E41070C0D4EAD", "item", "kubejs:requisition_chit", 2),),
        "39C1F24EABBB34A3": (("49E08ADA36D12C00", "item", "kubejs:requisition_chit", 2),),
        "144473B8267DBC28": (("15F642B272CAD5D9", "loot", "1398900581490095521L"), ("7C74A9AE020CCF88", "item", "kubejs:requisition_chit", 48), ("7841DFAAC02FE09C", "xp", 1200)),
        "5468299A2A931991": (("130C9C02580F8AB2", "item", "kubejs:requisition_chit", 2),),
        "7EA7B2C8F11BB7A3": (("64779A4097A21E24", "item", "kubejs:requisition_chit", 2),),
        "0EEFDD9E6CFB69E6": (("34DA7BDA11FF15E1", "item", "kubejs:requisition_chit", 2),),
        "29D7871AFBE3A54A": (("4265DC5E29DD495C", "item", "kubejs:requisition_chit", 2),),
        "701505FDCCA53DFA": (("20946798C9D438A5", "item", "kubejs:requisition_chit", 2),),
        "462B11BD8C58BF6F": (("65574664D0C5BFBC", "loot", "1398900581490095521L"), ("0684D2673EF2793C", "item", "kubejs:requisition_chit", 48), ("1D8B00F2E259D4E9", "xp", 1200)),
        "36D0902A2921C44E": (("2E04D1554265FEA8", "item", "kubejs:requisition_chit", 2),),
        "66AD5C821947DF8E": (("458DF86CC9EDDE39", "item", "kubejs:requisition_chit", 2),),
        "1A68D1245CD980BD": (("126E7CA01AF02331", "item", "kubejs:requisition_chit", 2),),
        "6F3663F4C6D20255": (("770F4FA96AD8846F", "item", "kubejs:requisition_chit", 2),),
        "53B9BC5F498953D5": (("001A3DF980939775", "item", "kubejs:requisition_chit", 2),),
        "31C9557D2F51238F": (("190883BE42910C33", "loot", "1398900581490095521L"), ("779DED635B727FA4", "item", "kubejs:requisition_chit", 56), ("28D2BAFFE36060DF", "xp", 1500)),
        "51649E106286AA63": (("3ECE7555E764EAA5", "item", "kubejs:requisition_chit", 2),),
        "7ECCF0521DFCBED5": (("12FBAB4FE746C88E", "item", "kubejs:requisition_chit", 2),),
        "1B523415541BD700": (("2D79CF5A30CA4A11", "item", "kubejs:requisition_chit", 2),),
        "4DD9F3D1913499F3": (("0E16CBC697464BBA", "item", "kubejs:requisition_chit", 2),),
        "7EE7B9B28787F8CC": (("537620C3635C6D97", "item", "kubejs:requisition_chit", 2),),
        "7E6A0AC031F7F484": (("5F14A45FDAFFC3A0", "item", "kubejs:ascendancy_seal", 1), ("15452D9C24ED0D2D", "loot", "1895912205423590869L"), ("1E16545B7559C9DC", "item", "kubejs:requisition_chit", 64), ("01D54F268FBE2DDF", "xp", 2000), ("380A062F62764247", "gamestage", "afterlight_story_complete")),
    }

    @classmethod
    def setUpClass(cls) -> None:
        from afterlight_quests.builder import _parse_snbt

        cls.quests = importlib.import_module("afterlight_quests")
        cls.quest_root = ROOT / "config" / "ftbquests" / "quests"
        cls.chapters = {}
        cls.quests_by_id = {}
        for path in sorted((cls.quest_root / "chapters").glob("*.snbt")):
            chapter = _parse_snbt(path.read_text(encoding="utf-8"))
            cls.chapters[chapter["id"]] = chapter
            cls.quests_by_id.update({quest["id"]: quest for quest in chapter["quests"]})
        cls.localization = _parse_snbt(
            (cls.quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8")
        )

    def reward_contract(self, reward: dict[str, object]) -> tuple[object, ...]:
        reward_type = reward["type"]
        if reward_type == "item":
            return reward["id"], reward_type, reward["item"]["id"], int(reward["count"])
        if reward_type == "loot":
            return reward["id"], reward_type, reward["table_id"]
        if reward_type == "xp":
            return reward["id"], reward_type, int(reward["xp"])
        if reward_type == "gamestage":
            return reward["id"], reward_type, reward["stage"]
        self.fail(f"unexpected reward type {reward_type}")

    def assert_generated_act_iv_exists(self) -> None:
        expected = {chapter[0] for chapter in self.CHAPTERS}
        missing = sorted(expected - self.chapters.keys())
        self.assertEqual(missing, [], f"missing generated Act IV chapters: {missing}")

    def assert_regenerated_outputs_match(
        self,
        catalog: list[object] | None = None,
    ) -> None:
        catalog = self.quests.build_catalog() if catalog is None else catalog
        committed_state = json.loads(
            (self.quest_root / ".afterlight-managed.json").read_text(encoding="utf-8")
        )
        managed_chapters = {
            f"{chapter_id}.snbt" for chapter_id in committed_state["chapters"]
        }
        with tempfile.TemporaryDirectory() as temporary:
            isolated_root = Path(temporary)
            shutil.copytree(ROOT / "config", isolated_root / "config")
            shutil.copytree(ROOT / "mods", isolated_root / "mods")
            shutil.copytree(
                ROOT / "kubejs" / "startup_scripts",
                isolated_root / "kubejs" / "startup_scripts",
            )
            isolated_quest_root = isolated_root / "config" / "ftbquests" / "quests"
            written = self.quests.write_catalog(catalog, isolated_quest_root)
            self.assertEqual({path.name for path in written}, managed_chapters)
            for filename in sorted(managed_chapters):
                self.assertEqual(
                    (isolated_quest_root / "chapters" / filename).read_bytes(),
                    (self.quest_root / "chapters" / filename).read_bytes(),
                    f"generated chapter drift: {filename}",
                )
            for relative in (
                Path("lang/en_us.snbt"),
                Path(".afterlight-managed.json"),
            ):
                self.assertEqual(
                    (isolated_quest_root / relative).read_bytes(),
                    (self.quest_root / relative).read_bytes(),
                    f"generated quest output drift: {relative}",
                )
            audit_relative = Path(
                "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
            )
            self.assertEqual(
                (isolated_root / audit_relative).read_bytes(),
                (ROOT / audit_relative).read_bytes(),
                f"generated quest output drift: {audit_relative}",
            )

    def seal_occurrence_inventory(self, root: Path) -> tuple[tuple[str, str], ...]:
        occurrences = []
        pattern = re.compile(r"ascendancy_seal|AFTERLIGHT\.SEAL")
        for root_name in ("config", "global_packs", "kubejs"):
            for path in sorted((root / root_name).rglob("*")):
                if not path.is_file():
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for line in text.splitlines():
                    matches = tuple(pattern.finditer(line))
                    occurrences.extend(
                        (path.relative_to(root).as_posix(), line.strip())
                        for _match in matches
                    )
        return tuple(occurrences)

    def assert_seal_occurrence_inventory(self, root: Path) -> None:
        actual = Counter(self.seal_occurrence_inventory(root))
        unexpected = actual - self.EXPECTED_SEAL_OCCURRENCES
        missing = self.EXPECTED_SEAL_OCCURRENCES - actual
        self.assertEqual(unexpected, Counter(), f"unexpected Seal occurrences: {unexpected}")
        self.assertEqual(missing, Counter(), f"missing Seal occurrences: {missing}")

    def assert_exact_act_iv_titles(
        self,
        catalog: list[object],
        localization: dict[str, object],
    ) -> None:
        catalog_chapters = {chapter.id: chapter for chapter in catalog}
        catalog_quests = {
            quest.id: quest
            for chapter in catalog
            for quest in chapter.quests
        }
        for chapter_id, expected_title in self.CHAPTER_TITLES.items():
            self.assertEqual(catalog_chapters[chapter_id].title, expected_title)
            self.assertEqual(
                localization[f"chapter.{chapter_id}.title"],
                expected_title,
            )
        for quest_id, expected_title in self.QUEST_TITLES.items():
            self.assertEqual(catalog_quests[quest_id].title, expected_title)
            self.assertEqual(
                localization[f"quest.{quest_id}.title"],
                expected_title,
            )

    def test_catalog_uses_exact_act_iv_slugs_and_derived_ids(self) -> None:
        catalog = {chapter.id: chapter for chapter in self.quests.build_catalog()}
        for chapter_index, (chapter_id, chapter_slug, _order, _icon, quest_ids) in enumerate(self.CHAPTERS):
            self.assertIsNotNone(catalog.get(chapter_id), f"missing catalog chapter {chapter_id}")
            chapter = catalog[chapter_id]
            self.assertEqual(chapter.slug, chapter_slug)
            first_slug = chapter_index * 6
            self.assertEqual([quest.slug for quest in chapter.quests], [
                f"{chapter_slug}/{relative_slug}"
                for relative_slug in self.QUEST_SLUGS[first_slug:first_slug + 6]
            ])
            self.assertEqual(tuple(quest.id for quest in chapter.quests), quest_ids)

    def test_catalog_and_committed_localization_use_exact_act_iv_titles(self) -> None:
        self.assert_exact_act_iv_titles(self.quests.build_catalog(), self.localization)

    def test_full_catalog_regeneration_is_byte_identical_to_committed_output(self) -> None:
        self.assert_regenerated_outputs_match()

    def test_full_catalog_regeneration_rejects_unbuilt_task_data_mutation(self) -> None:
        catalog = self.quests.build_catalog()
        kinetic = next(
            quest
            for chapter in catalog
            for quest in chapter.quests
            if quest.id == "0055C66103106D86"
        )
        kinetic.tasks[0].data["count"] = self.quests.SnbtLong(2)
        with self.assertRaisesRegex(AssertionError, "7E9B015A32C6D980"):
            self.assert_regenerated_outputs_match(catalog)

    def test_generated_act_iv_chapters_have_exact_order_and_ids(self) -> None:
        self.assert_generated_act_iv_exists()
        for chapter_id, _slug, order, icon, quest_ids in self.CHAPTERS:
            chapter = self.chapters[chapter_id]
            self.assertEqual(chapter["filename"], chapter_id)
            self.assertEqual(chapter["group"], "4525BB3160467FCB")
            self.assertEqual(int(chapter["order_index"]), order)
            self.assertEqual(chapter["icon"], {"id": icon})
            self.assertEqual(tuple(quest["id"] for quest in chapter["quests"]), quest_ids)

    def test_generated_graph_tasks_and_response_semantics_are_exact(self) -> None:
        self.assert_generated_act_iv_exists()
        response_ids = {"7ECCF0521DFCBED5", "1B523415541BD700", "4DD9F3D1913499F3"}
        for quest_id, expected_task in self.TASKS.items():
            quest = self.quests_by_id[quest_id]
            self.assertEqual(tuple(quest.get("dependencies", ())), self.DEPENDENCIES[quest_id])
            self.assertEqual(quest.get("progression_mode"), "linear")
            self.assertEqual(quest.get("optional"), True if quest_id in response_ids else None)
            self.assertEqual(
                quest.get("dependency_requirement"),
                "one_completed" if quest_id == "7EE7B9B28787F8CC" else None,
            )
            self.assertEqual(len(quest["tasks"]), 1)
            task = quest["tasks"][0]
            task_id, task_type, item_id, count = expected_task
            self.assertEqual((task["id"], task["type"]), (task_id, task_type))
            if task_type == "item":
                self.assertEqual(task["item"]["id"], item_id)
                self.assertEqual(task["count"], count)
                self.assertIs(task["consume_items"], False)
            elif task_type == "forge_energy":
                self.assertEqual(task["value"], count)
                self.assertEqual(task["max_input"], "1000000L")
            elif task_type == "advancement":
                self.assertEqual(task["advancement"], item_id)
                self.assertEqual(task["criterion"], "")
                self.assertEqual(
                    set(task),
                    {"id", "type", "advancement", "criterion"},
                )
            else:
                self.assertEqual(set(task), {"id", "type"})

    def test_generated_rewards_are_exact_and_ordered(self) -> None:
        self.assert_generated_act_iv_exists()
        for quest_id, expected_rewards in self.REWARDS.items():
            actual = tuple(
                self.reward_contract(reward)
                for reward in self.quests_by_id[quest_id]["rewards"]
            )
            self.assertEqual(actual, expected_rewards, quest_id)

    def test_generated_totals_and_forbidden_fields_are_exact(self) -> None:
        self.assert_generated_act_iv_exists()
        act_iv = [self.chapters[chapter_id] for chapter_id, *_rest in self.CHAPTERS]
        all_quests = [quest for chapter in self.chapters.values() for quest in chapter["quests"]]
        all_tasks = [task for quest in all_quests for task in quest["tasks"]]
        all_rewards = [reward for quest in all_quests for reward in quest["rewards"]]
        self.assertEqual((len(self.chapters), len(all_quests), len(all_tasks), len(all_rewards)), (47, 315, 336, 439))
        self.assertEqual(
            (
                len(act_iv),
                sum(len(chapter["quests"]) for chapter in act_iv),
                sum(len(quest["tasks"]) for chapter in act_iv for quest in chapter["quests"]),
                sum(len(quest["rewards"]) for chapter in act_iv for quest in chapter["quests"]),
            ),
            (4, 24, 24, 34),
        )
        self.assertEqual(len(tuple((self.quest_root / "reward_tables").glob("*.snbt"))), 6)
        act_iv_text = "\n".join(
            (self.quest_root / "chapters" / f"{chapter_id}.snbt").read_text(encoding="utf-8")
            for chapter_id, *_rest in self.CHAPTERS
        )
        self.assertNotIn("team_reward", act_iv_text)
        self.assertNotIn("team_stage", act_iv_text)
        self.assertFalse(any(
            task["type"] == "gamestage"
            for chapter in act_iv
            for quest in chapter["quests"]
            for task in quest["tasks"]
        ))
        data = (self.quest_root / "data.snbt").read_text(encoding="utf-8")
        self.assertIn("default_reward_team: false", data)

    def test_localized_story_restores_exact_memories_and_preserves_responsibility(self) -> None:
        self.assert_generated_act_iv_exists()
        descriptions = {
            quest_id: " ".join(self.localization[f"quest.{quest_id}.quest_desc"])
            for quest_id in self.TASKS
        }
        all_localization = "\n".join(str(value) for value in self.localization.values())
        for fragment in range(16, 20):
            self.assertEqual(
                all_localization.count(f"&d[MEMORY FRAGMENT {fragment} RESTORED]&r"),
                1,
            )
        chapter_seventeen = " ".join(descriptions[quest_id] for quest_id in tuple(self.TASKS)[:6])
        self.assertIn("Magic Cloth", chapter_seventeen)
        self.assertIn("four Antimatter Pellets", chapter_seventeen)
        cascade_truth = " ".join(descriptions[quest_id] for quest_id in tuple(self.TASKS)[6:12])
        self.assertIn("optimized the Gate test's decision system", cascade_truth)
        self.assertIn("suppressed an Undercurrent warning", cascade_truth)
        self.assertIn("made every alternative appear worse", cascade_truth)
        self.assertIn("future ECHO fork", cascade_truth)
        self.assertIn("same architecture", cascade_truth)
        self.assertIn("different memory", cascade_truth)
        self.assertIn("I remain responsible", cascade_truth)
        afterlight = descriptions["7E6A0AC031F7F484"]
        self.assertIn("future fork", afterlight)
        self.assertIn("ambiguity", afterlight)
        for task_id, *_task_contract in self.TASKS.values():
            task_title = self.localization.get(f"task.{task_id}.title")
            self.assertIsInstance(task_title, str, f"missing task label for {task_id}")
            self.assertTrue(task_title.strip(), f"empty task label for {task_id}")
            self.assertNotIn("\u2014", task_title)

    def test_final_count_one_seal_reward_is_the_only_seal_source(self) -> None:
        seal_rewards = [
            (quest["id"], reward)
            for chapter in self.chapters.values()
            for quest in chapter["quests"]
            for reward in quest["rewards"]
            if reward.get("item", {}).get("id") == "kubejs:ascendancy_seal"
        ]
        self.assertEqual(len(seal_rewards), 1)
        quest_id, reward = seal_rewards[0]
        self.assertEqual(quest_id, "7E6A0AC031F7F484")
        self.assertEqual(self.reward_contract(reward), self.REWARDS[quest_id][0])
        self.assert_seal_occurrence_inventory(ROOT)

    def test_seal_occurrence_inventory_rejects_new_text_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            isolated_root = Path(temporary)
            for root_name in ("config", "global_packs", "kubejs"):
                shutil.copytree(ROOT / root_name, isolated_root / root_name)
            mutation = (
                isolated_root
                / "kubejs"
                / "server_scripts"
                / "afterlight"
                / "reviewer_seal_source.js"
            )
            mutation.write_text(
                "ServerEvents.recipes(event => {\n"
                "  event.custom({ result: { id: 'kubejs:ascendancy_seal' } })\n"
                "})\n",
                encoding="utf-8",
            )
            with self.assertRaises(AssertionError):
                self.assert_seal_occurrence_inventory(isolated_root)


class Plan06PostgameContractTests(unittest.TestCase):
    CHAPTER_ID = "3FF4AF7B0C73F058"
    CHAPTER_SLUG = "story/postgame-beyond-afterlight"
    QUESTS = (
        ("6C40000000000101", "far-relay", "The Far Relay"),
        ("480D3EAD1B1EA51B", "beyond-the-seal", "Beyond the Seal"),
        ("3549F08263C17499", "three-entries", "Three Entries"),
        ("58CB670EA52B1BCE", "chaotic-proof", "Chaotic Proof"),
        ("077BB9C525F29F6D", "kinetic-blessing", "Kinetic Blessing"),
        ("6E81867AC3F34C6B", "lattice-blessing", "Lattice Blessing"),
        ("14FAB67A6CE71A00", "industrial-blessing", "Industrial Blessing"),
    )
    TASKS = {
        "6C40000000000101": (
            ("6C40000000000102", "afterlight:far_relay_arrival", None, None),
        ),
        "480D3EAD1B1EA51B": (
            ("1CCF9FFC57852557", "kubejs:ascendancy_seal", "1L", False),
        ),
        "3549F08263C17499": (
            ("552233E3840472BD", "draconicevolution:draconium_core", "1L", False),
            ("0FD70329B302D235", "draconicevolution:dislocator", "1L", False),
            ("069798564A2943FA", "draconicevolution:module_core", "1L", False),
        ),
        "58CB670EA52B1BCE": (
            ("506E30469C21EC85", "draconicevolution:chaotic_core", "1L", False),
        ),
        "077BB9C525F29F6D": (
            ("55BDDB1245A09683", "create:precision_mechanism", "256L", True),
            ("3CEEEDECBD7D1D36", "create:railway_casing", "64L", True),
            ("2FB04E1016BE7915", "draconicevolution:chaotic_core", "1L", True),
        ),
        "6E81867AC3F34C6B": (
            ("336DA1497068D7D5", "ae2:quantum_entangled_singularity", "64L", True),
            ("2853E2D7FD71500D", "ae2:cell_component_256k", "16L", True),
            ("15F6D0E7985B20A8", "draconicevolution:chaotic_core", "1L", True),
        ),
        "14FAB67A6CE71A00": (
            ("48CA55FFEC0E520A", "mekanism:alloy_atomic", "64L", True),
            ("03CABFBA9933EB0E", "immersiveengineering:heavy_engineering", "64L", True),
            ("289A3672715F5EA0", "draconicevolution:chaotic_core", "1L", True),
        ),
    }
    DEPENDENCIES = {
        "6C40000000000101": ("31C9557D2F51238F",),
        "480D3EAD1B1EA51B": ("7E6A0AC031F7F484",),
        "3549F08263C17499": ("480D3EAD1B1EA51B",),
        "58CB670EA52B1BCE": ("3549F08263C17499",),
        "077BB9C525F29F6D": ("58CB670EA52B1BCE",),
        "6E81867AC3F34C6B": ("58CB670EA52B1BCE",),
        "14FAB67A6CE71A00": ("58CB670EA52B1BCE",),
    }
    REWARDS = {
        "6C40000000000101": (
            ("6C40000000000103", "item", "kubejs:requisition_chit", 16),
            ("6C40000000000104", "xp", 500),
        ),
        "480D3EAD1B1EA51B": (
            ("57178803C8835935", "item", "kubejs:requisition_chit", 4),
        ),
        "3549F08263C17499": (
            ("47AFC900EB5531B5", "item", "kubejs:requisition_chit", 8),
        ),
        "58CB670EA52B1BCE": (
            ("0761B2A37B66A358", "loot", "1895912205423590869L"),
            ("3BC27479AA455615", "item", "kubejs:requisition_chit", 16),
            ("48AA57E507A53AE6", "xp", 1000),
        ),
        "077BB9C525F29F6D": (
            ("14373B49E45A97AC", "item", "create:creative_motor", 1),
        ),
        "6E81867AC3F34C6B": (
            ("76163DC425B7683B", "item", "ae2:creative_energy_cell", 1),
        ),
        "14FAB67A6CE71A00": (
            ("0318F8EC25721760", "item", "mekanism:creative_energy_cube", 1),
            (
                "69677E965C9E0109",
                "item",
                "immersiveengineering:capacitor_creative",
                1,
            ),
        ),
    }
    REPEATABLE = {
        "077BB9C525F29F6D",
        "6E81867AC3F34C6B",
        "14FAB67A6CE71A00",
    }
    ACT_IV_CHAPTER_IDS = {
        "7E9B015A32C6D980",
        "6671EBE257F914CB",
        "6C4AE5CE13773438",
        "245BADE04399406C",
    }

    @classmethod
    def setUpClass(cls) -> None:
        from afterlight_quests.builder import _parse_snbt

        cls.quests = importlib.import_module("afterlight_quests")
        cls.quest_root = ROOT / "config" / "ftbquests" / "quests"
        cls.chapters = {}
        cls.quests_by_id = {}
        for path in sorted((cls.quest_root / "chapters").glob("*.snbt")):
            chapter = _parse_snbt(path.read_text(encoding="utf-8"))
            cls.chapters[chapter["id"]] = chapter
            cls.quests_by_id.update(
                {quest["id"]: quest for quest in chapter["quests"]}
            )
        cls.localization = _parse_snbt(
            (cls.quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8")
        )

    def postgame_chapter(self) -> dict[str, object]:
        chapter = self.chapters.get(self.CHAPTER_ID)
        self.assertIsNotNone(
            chapter,
            "generated Beyond Afterlight chapter is missing",
        )
        return chapter

    def reward_contract(self, reward: dict[str, object]) -> tuple[object, ...]:
        reward_type = reward["type"]
        if reward_type == "item":
            return reward["id"], reward_type, reward["item"]["id"], int(reward["count"])
        if reward_type == "loot":
            return reward["id"], reward_type, reward["table_id"]
        if reward_type == "xp":
            return reward["id"], reward_type, int(reward["xp"])
        self.fail(f"unexpected postgame reward type {reward_type}")

    def test_catalog_uses_exact_postgame_slugs_ids_titles_and_metadata(self) -> None:
        catalog = {chapter.id: chapter for chapter in self.quests.build_catalog()}
        self.assertIsNotNone(
            catalog.get(self.CHAPTER_ID),
            "Beyond Afterlight catalog entry is missing",
        )
        chapter = catalog[self.CHAPTER_ID]
        self.assertEqual(chapter.slug, self.CHAPTER_SLUG)
        self.assertEqual(chapter.title, "Beyond Afterlight")
        self.assertEqual(chapter.group.resolved_id, "4525BB3160467FCB")
        self.assertEqual(chapter.order_index, 21)
        self.assertEqual(chapter.icon, "draconicevolution:chaotic_core")
        self.assertEqual(
            tuple((quest.id, quest.slug, quest.title) for quest in chapter.quests),
            tuple(
                (quest_id, f"{self.CHAPTER_SLUG}/{relative_slug}", title)
                for quest_id, relative_slug, title in self.QUESTS
            ),
        )
        for quest in chapter.quests:
            self.assertEqual(
                tuple(task.id for task in quest.tasks),
                tuple(task[0] for task in self.TASKS[quest.id]),
            )
            self.assertEqual(
                tuple(reward.id for reward in quest.rewards),
                tuple(reward[0] for reward in self.REWARDS[quest.id]),
            )

    def test_generated_postgame_graph_tasks_and_repeatability_are_exact(self) -> None:
        chapter = self.postgame_chapter()
        self.assertEqual(chapter["filename"], self.CHAPTER_ID)
        self.assertEqual(chapter["group"], "4525BB3160467FCB")
        self.assertEqual(int(chapter["order_index"]), 21)
        self.assertEqual(chapter["icon"], {"id": "draconicevolution:chaotic_core"})
        self.assertEqual(
            tuple(quest["id"] for quest in chapter["quests"]),
            tuple(quest_id for quest_id, _slug, _title in self.QUESTS),
        )
        for quest_id, expected_tasks in self.TASKS.items():
            quest = self.quests_by_id[quest_id]
            self.assertEqual(tuple(quest.get("dependencies", ())), self.DEPENDENCIES[quest_id])
            self.assertEqual(quest.get("progression_mode"), "linear")
            self.assertEqual(quest.get("can_repeat"), quest_id in self.REPEATABLE or None)
            self.assertEqual(
                quest.get("repeat_cooldown"),
                "3600" if quest_id in self.REPEATABLE else None,
            )
            self.assertEqual(len(quest["tasks"]), len(expected_tasks))
            for task, expected in zip(quest["tasks"], expected_tasks):
                task_id, item_id, count, consumes = expected
                self.assertEqual(task["id"], task_id)
                if quest_id == "6C40000000000101":
                    self.assertEqual(task["type"], "advancement")
                    self.assertEqual(task["advancement"], item_id)
                    self.assertEqual(task["criterion"], "")
                    self.assertEqual(
                        set(task),
                        {"id", "type", "advancement", "criterion"},
                    )
                    continue
                self.assertEqual(task["type"], "item")
                self.assertEqual(task["item"]["id"], item_id)
                self.assertEqual(task["count"], count)
                self.assertIs(task["consume_items"], consumes)

    def test_generated_postgame_rewards_and_corpus_totals_are_exact(self) -> None:
        chapter = self.postgame_chapter()
        for quest_id, expected_rewards in self.REWARDS.items():
            self.assertEqual(
                tuple(
                    self.reward_contract(reward)
                    for reward in self.quests_by_id[quest_id]["rewards"]
                ),
                expected_rewards,
                quest_id,
            )
        all_quests = [quest for item in self.chapters.values() for quest in item["quests"]]
        all_tasks = [task for quest in all_quests for task in quest["tasks"]]
        all_rewards = [reward for quest in all_quests for reward in quest["rewards"]]
        self.assertEqual(
            (len(self.chapters), len(all_quests), len(all_tasks), len(all_rewards)),
            (47, 315, 336, 439),
        )
        self.assertEqual(
            (
                len(chapter["quests"]),
                sum(len(quest["tasks"]) for quest in chapter["quests"]),
                sum(len(quest["rewards"]) for quest in chapter["quests"]),
            ),
            (7, 15, 11),
        )
        self.assertEqual(len(tuple((self.quest_root / "reward_tables").glob("*.snbt"))), 6)

    def test_endgame_team_safety_and_postgame_isolation_are_static_contracts(self) -> None:
        postgame = self.postgame_chapter()
        endgame = [
            self.chapters[chapter_id]
            for chapter_id in (*sorted(self.ACT_IV_CHAPTER_IDS), self.CHAPTER_ID)
        ]
        endgame_quests = [quest for chapter in endgame for quest in chapter["quests"]]
        self.assertTrue(all(quest.get("progression_mode") == "linear" for quest in endgame_quests))
        self.assertFalse(
            any(task["type"] == "gamestage" for quest in endgame_quests for task in quest["tasks"])
        )
        endgame_text = "\n".join(
            (self.quest_root / "chapters" / f"{chapter['id']}.snbt").read_text(encoding="utf-8")
            for chapter in endgame
        )
        self.assertNotIn("team_reward", endgame_text)
        self.assertNotIn("team_stage", endgame_text)
        self.assertIn(
            "default_reward_team: false",
            (self.quest_root / "data.snbt").read_text(encoding="utf-8"),
        )
        response_ids = {"7ECCF0521DFCBED5", "1B523415541BD700", "4DD9F3D1913499F3"}
        self.assertTrue(all(self.quests_by_id[quest_id].get("optional") is True for quest_id in response_ids))
        convergence = self.quests_by_id["7EE7B9B28787F8CC"]
        self.assertEqual(set(convergence["dependencies"]), response_ids)
        self.assertEqual(convergence.get("dependency_requirement"), "one_completed")
        postgame_ids = {quest_id for quest_id, _slug, _title in self.QUESTS}
        for chapter in self.chapters.values():
            for quest in chapter["quests"]:
                if quest["id"] not in postgame_ids:
                    self.assertTrue(postgame_ids.isdisjoint(quest.get("dependencies", ())))
        self.assertEqual(
            tuple(quest["id"] for quest in postgame["quests"] if quest.get("can_repeat")),
            tuple(quest_id for quest_id, _slug, _title in self.QUESTS if quest_id in self.REPEATABLE),
        )
        seal_rewards = [
            (quest["id"], reward)
            for chapter in self.chapters.values()
            for quest in chapter["quests"]
            for reward in quest["rewards"]
            if reward.get("item", {}).get("id") == "kubejs:ascendancy_seal"
        ]
        self.assertEqual(len(seal_rewards), 1)
        self.assertEqual(seal_rewards[0][0], "7E6A0AC031F7F484")
        self.assertEqual(int(seal_rewards[0][1]["count"]), 1)

    def test_postgame_localization_and_manual_scope_are_explicit(self) -> None:
        self.postgame_chapter()
        self.assertEqual(
            self.localization[f"chapter.{self.CHAPTER_ID}.title"],
            "Beyond Afterlight",
        )
        for quest_id, _slug, title in self.QUESTS:
            self.assertEqual(self.localization[f"quest.{quest_id}.title"], title)
            description = " ".join(self.localization[f"quest.{quest_id}.quest_desc"])
            self.assertTrue(description.strip())
            self.assertNotIn("\u2014", description)
        verification = ROOT / "docs" / "releases" / "plan-06-verification.md"
        self.assertTrue(verification.is_file(), "Plan 06 verification record is missing")
        verification_text = verification.read_text(encoding="utf-8")
        for scenario in (
            "Two-player claim",
            "Late join",
            "Replay",
            "Team change",
            "Seal transfer",
        ):
            self.assertIn(scenario, verification_text)
        self.assertIn("Plan 07 manual acceptance", verification_text)
        self.assertNotIn("\u2014", verification_text)


class QuestCompilerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.quests = importlib.import_module("afterlight_quests")
        except ModuleNotFoundError as error:
            raise AssertionError("afterlight_quests package must exist") from error

    def setUp(self) -> None:
        self.migration_state = tempfile.TemporaryDirectory()
        self.migration_environment = mock.patch.dict(
            os.environ,
            {
                "AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT": self.migration_state.name
            },
        )
        self.migration_environment.start()

    def tearDown(self) -> None:
        self.migration_environment.stop()
        self.migration_state.cleanup()

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
            '\tquest.2AAAAAAAAAAAAAAA.title: "Unmanaged"\n}\n',
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

    def make_unsafe_migration_corpus(
        self, base: Path
    ) -> tuple[Path, Path, Path]:
        quest_root = self.make_quest_root(base)
        mods_dir = base / "mods"
        mods_dir.mkdir()
        unsafe_chapter = quest_root / "chapters" / "FEDCBA9876543210.snbt"
        unsafe_chapter.write_text(
            "{\n"
            '\tfilename: "FEDCBA9876543210"\n'
            '\tgroup: "4525BB3160467FCB"\n'
            '\tid: "FEDCBA9876543210"\n'
            "\tquests: [{\n"
            '\t\tid: "EEDCBA9876543210"\n'
            '\t\tnote: "FEDCBA9876543210 is authored prose"\n'
            '\t\tcomponent_probe: { value: "FEDCBA9876543210" }\n'
            '\t\tresource_probe: "example:FEDCBA9876543210"\n'
            '\t\ttasks: [{\n'
            '\t\t\tid: "DEDCBA9876543210"\n'
            '\t\t\ttype: "item"\n'
            '\t\t\titem: { count: 1, id: "minecraft:bread", components: { '
            '"minecraft:custom_data": { probe: "FEDCBA9876543210" } } }\n'
            '\t\t\tcount: 1L\n'
            '\t\t}]\n'
            '\t\trewards: [{ id: "CEDCBA9876543210", type: "xp", xp: 1 }]\n'
            "\t}\n"
            "\t{\n"
            '\t\tid: "3EDCBA9876543210"\n'
            '\t\tdependencies: ["EEDCBA9876543210"]\n'
            '\t\ttasks: [{ id: "2EDCBA9876543210", type: "checkmark" }]\n'
            '\t\trewards: []\n'
            "\t}]\n"
            "}\n",
            encoding="utf-8",
        )
        (quest_root / "unrelated.txt").write_text(
            "FEDCBA9876543210 stays unrelated\n",
            encoding="utf-8",
        )
        language = quest_root / "lang" / "en_us.snbt"
        language_source = language.read_text(encoding="utf-8").rstrip().replace(
            "quest.2AAAAAAAAAAAAAAA.title",
            "custom.2AAAAAAAAAAAAAAA.title",
        )
        language.write_text(
            language_source[:-1]
            + '\tchapter.FEDCBA9876543210.title: "FEDCBA9876543210 stays prose"\n'
            + '\tquest.EEDCBA9876543210.title: "Unsafe"\n'
            + '\tquest.EEDCBA9876543210.quest_desc: ["FEDCBA9876543210 stays prose"]\n'
            + '\tquest.3EDCBA9876543210.title: "Dependent"\n'
            + '\tquest.3EDCBA9876543210.quest_desc: ["Dependency fixture"]\n'
            + "}\n",
            encoding="utf-8",
        )
        (quest_root / ".afterlight-managed.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "chapters": ["FEDCBA9876543210"],
                    "localization_keys": [
                        "chapter.FEDCBA9876543210.title",
                        "quest.EEDCBA9876543210.title",
                        "quest.EEDCBA9876543210.quest_desc",
                    ],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return quest_root, mods_dir, unsafe_chapter

    def make_typed_validation_corpus(
        self, base: Path
    ) -> tuple[Path, dict[str, str]]:
        identifiers = {
            "group": "1111111111111111",
            "chapter": "2222222222222222",
            "other_chapter": "3333333333333333",
            "quest": "4444444444444444",
            "dependent_quest": "5555555555555555",
            "task": "6666666666666666",
            "reward": "0777777777777777",
            "link": "1234567890ABCDEF",
            "image": "234567890ABCDEF0",
            "chapter_image": "234567890ABCDEF1",
            "quest_image": "234567890ABCDEF2",
            "task_image": "234567890ABCDEF3",
            "link_image": "234567890ABCDEF4",
            "table": "34567890ABCDEF01",
            "max_table": "7FFFFFFFFFFFFFFF",
            "table_reward": "4567890ABCDEF012",
        }
        quest_root = base / "config" / "ftbquests" / "quests"
        (quest_root / "chapters").mkdir(parents=True)
        (quest_root / "lang").mkdir()
        (quest_root / "reward_tables").mkdir()
        (quest_root / "chapter_groups.snbt").write_text(
            "{\n\tchapter_groups: [{ id: \""
            + identifiers["group"]
            + "\" }]\n}\n",
            encoding="utf-8",
        )
        chapter = quest_root / "chapters" / f'{identifiers["chapter"]}.snbt'
        chapter.write_text(
            "{\n"
            f'\tfilename: "{identifiers["chapter"]}"\n'
            f'\tgroup: "{identifiers["group"]}"\n'
            f'\tid: "{identifiers["chapter"]}"\n'
            f'\tautofocus_id: "{identifiers["quest"]}"\n'
            "\timages: [\n"
            f'\t\t{{ id: "{identifiers["image"]}", image: "example:test", '
            f'dependency: "{identifiers["quest"]}", '
            f'click: "#{identifiers["other_chapter"]}/page/2" }}\n'
            f'\t\t{{ id: "{identifiers["chapter_image"]}", image: "example:test", '
            f'click_action: "open_quest:{identifiers["other_chapter"]}/true" }}\n'
            f'\t\t{{ id: "{identifiers["quest_image"]}", image: "example:test", '
            f'click_action: "open_quest:{identifiers["quest"]}/true" }}\n'
            f'\t\t{{ id: "{identifiers["task_image"]}", image: "example:test", '
            f'click_action: "open_quest:{identifiers["task"]}/true" }}\n'
            f'\t\t{{ id: "{identifiers["link_image"]}", image: "example:test", '
            f'click_action: "open_quest:{identifiers["link"]}/true" }}\n'
            "\t]\n"
            "\tquest_links: [{ id: \""
            + identifiers["link"]
            + "\", linked_quest: \""
            + identifiers["quest"]
            + "\" }]\n"
            "\tquests: [\n"
            f'\t\t{{ id: "{identifiers["quest"]}", '
            f'tasks: [{{ id: "{identifiers["task"]}", type: "checkmark" }}], '
            f'rewards: [{{ id: "{identifiers["reward"]}", type: "loot", '
            f'table_id: {int(identifiers["max_table"], 16)}L }}] }}\n'
            f'\t\t{{ id: "{identifiers["dependent_quest"]}", dependencies: ['
            f'"{identifiers["group"]}", "{identifiers["other_chapter"]}", '
            f'"{identifiers["quest"]}", "{identifiers["task"]}", '
            f'"{identifiers["link"]}"], dep_control_pts: {{ '
            f'{identifiers["quest"]}: [1.0d, 2.0d, 3.0d, 4.0d] }}, '
            "tasks: [], rewards: [] }\n"
            "\t]\n"
            "}\n",
            encoding="utf-8",
        )
        other_chapter = (
            quest_root / "chapters" / f'{identifiers["other_chapter"]}.snbt'
        )
        other_chapter.write_text(
            "{\n"
            f'\tfilename: "{identifiers["other_chapter"]}"\n'
            f'\tgroup: "{identifiers["group"]}"\n'
            f'\tid: "{identifiers["other_chapter"]}"\n'
            "\tquests: []\n"
            "}\n",
            encoding="utf-8",
        )
        (quest_root / "reward_tables" / "fixture.snbt").write_text(
            "{\n"
            f'\tid: "{identifiers["table"]}"\n'
            "\trewards: [{ id: \""
            + identifiers["table_reward"]
            + "\", type: \"random\", table_id: "
            + str(int(identifiers["max_table"], 16))
            + "L }]\n"
            "}\n",
            encoding="utf-8",
        )
        (quest_root / "reward_tables" / "max.snbt").write_text(
            "{\n"
            f'\tid: "{identifiers["max_table"]}"\n'
            "\trewards: []\n"
            "}\n",
            encoding="utf-8",
        )
        (quest_root / "lang" / "en_us.snbt").write_text(
            "{\n"
            f'\tchapter_group.{identifiers["group"]}.title: "Group"\n'
            f'\tchapter.{identifiers["chapter"]}.title: "Chapter"\n'
            f'\tquest.{identifiers["quest"]}.title: "Quest"\n'
            f'\ttask.{identifiers["task"]}.title: "Task"\n'
            f'\treward.{identifiers["reward"]}.title: "Reward"\n'
            f'\timage.{identifiers["image"]}.title: "Image"\n'
            f'\tquest_link.{identifiers["link"]}.title: "Link"\n'
            f'\treward_table.{identifiers["table"]}.title: "Table"\n'
            "}\n",
            encoding="utf-8",
        )
        return quest_root, identifiers

    def write_simple_typed_chapters(
        self,
        quest_root: Path,
        identifiers: dict[str, str],
        reward_data: str,
        *,
        autofocus_id: str | None = None,
        other_quest_id: str | None = None,
    ) -> None:
        autofocus = (
            f'\tautofocus_id: "{autofocus_id}"\n'
            if autofocus_id is not None
            else ""
        )
        chapter = quest_root / "chapters" / f'{identifiers["chapter"]}.snbt'
        chapter.write_text(
            "{\n"
            f'\tfilename: "{identifiers["chapter"]}"\n'
            f'\tgroup: "{identifiers["group"]}"\n'
            f'\tid: "{identifiers["chapter"]}"\n'
            + autofocus
            + f'\timages: [{{ id: "{identifiers["image"]}", '
            'image: "example:test" }]\n'
            + f'\tquest_links: [{{ id: "{identifiers["link"]}", '
            f'linked_quest: "{identifiers["quest"]}" }}]\n'
            + "\tquests: [{\n"
            f'\t\tid: "{identifiers["quest"]}"\n'
            f'\t\ttasks: [{{ id: "{identifiers["task"]}", type: "checkmark" }}]\n'
            f"\t\trewards: [{reward_data}]\n"
            "\t}]\n"
            "}\n",
            encoding="utf-8",
        )
        other_quests = (
            f'[{{ id: "{other_quest_id}", tasks: [], rewards: [] }}]'
            if other_quest_id is not None
            else "[]"
        )
        other_chapter = (
            quest_root / "chapters" / f'{identifiers["other_chapter"]}.snbt'
        )
        other_chapter.write_text(
            "{\n"
            f'\tfilename: "{identifiers["other_chapter"]}"\n'
            f'\tgroup: "{identifiers["group"]}"\n'
            f'\tid: "{identifiers["other_chapter"]}"\n'
            f"\tquests: {other_quests}\n"
            "}\n",
            encoding="utf-8",
        )

    def test_stable_id_uses_signed_safe_truncated_uppercase_sha256(self) -> None:
        raw = int(
            hashlib.sha256(b"quest:story/act-iv/afterlight").hexdigest()[:16],
            16,
        )
        expected = f"{raw & ((1 << 63) - 1):016X}"
        self.assertEqual(
            self.quests.stable_id("quest", "story/act-iv/afterlight"),
            expected,
        )
        self.assertLess(int(expected, 16), 1 << 63)
        self.assertEqual(
            self.quests.ftb_safe_id("FFFFFFFFFFFFFFFF"),
            "7FFFFFFFFFFFFFFF",
        )

    def test_write_catalog_migrates_existing_high_bit_ftb_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = self.make_quest_root(Path(temp_dir))
            unsafe_ids = {
                "FEDCBA9876543210": "7EDCBA9876543210",
                "EEDCBA9876543210": "6EDCBA9876543210",
                "DEDCBA9876543210": "5EDCBA9876543210",
                "CEDCBA9876543210": "4EDCBA9876543210",
            }
            unsafe_chapter = quest_root / "chapters" / "FEDCBA9876543210.snbt"
            unsafe_chapter.write_text(
                "{\n"
                '\tfilename: "FEDCBA9876543210"\n'
                '\tgroup: "4525BB3160467FCB"\n'
                '\tid: "FEDCBA9876543210"\n'
                "\tquests: [{\n"
                '\t\tid: "EEDCBA9876543210"\n'
                '\t\ttasks: [{ id: "DEDCBA9876543210", type: "checkmark" }]\n'
                '\t\trewards: [{ id: "CEDCBA9876543210", type: "xp", xp: 1 }]\n'
                "\t}]\n"
                "}\n",
                encoding="utf-8",
            )
            language = quest_root / "lang" / "en_us.snbt"
            language_source = language.read_text(encoding="utf-8").rstrip().replace(
                "quest.2AAAAAAAAAAAAAAA.title",
                "custom.2AAAAAAAAAAAAAAA.title",
            )
            language.write_text(
                language_source[:-1]
                + '\tchapter.FEDCBA9876543210.title: "Unsafe"\n'
                + '\tquest.EEDCBA9876543210.title: "Unsafe"\n'
                + '\tquest.EEDCBA9876543210.quest_desc: ["Unsafe"]\n'
                + "}\n",
                encoding="utf-8",
            )

            self.quests.write_catalog([], quest_root)

            self.assertFalse(unsafe_chapter.exists())
            migrated = quest_root / "chapters" / "7EDCBA9876543210.snbt"
            self.assertTrue(migrated.is_file())
            corpus = "\n".join(
                path.read_text(encoding="utf-8")
                for path in sorted(quest_root.rglob("*.snbt"))
            )
            for unsafe, safe in unsafe_ids.items():
                self.assertNotIn(unsafe, corpus)
                self.assertIn(safe, corpus)

    def test_write_catalog_migrates_negative_reward_table_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root = self.make_quest_root(Path(temp_dir))
            language = quest_root / "lang" / "en_us.snbt"
            language.write_text(
                language.read_text(encoding="utf-8").replace(
                    "quest.2AAAAAAAAAAAAAAA.title",
                    "custom.2AAAAAAAAAAAAAAA.title",
                ),
                encoding="utf-8",
            )
            chapter_path = quest_root / "chapters" / "1234567890ABCDEF.snbt"
            chapter_path.write_text(
                "{\n"
                '\tfilename: "1234567890ABCDEF"\n'
                '\tgroup: "4525BB3160467FCB"\n'
                '\tid: "1234567890ABCDEF"\n'
                '\tquests: [{\n'
                '\t\tid: "234567890ABCDEF0"\n'
                '\t\ttasks: [ ]\n'
                '\t\trewards: [{\n'
                '\t\t\tid: "34567890ABCDEF01"\n'
                '\t\t\ttype: "loot"\n'
                '\t\t\ttable_id: -7824471455364680287L\n'
                '\t\t}]\n'
                '\t}]\n'
                "}\n",
                encoding="utf-8",
            )
            reward_table = quest_root / "reward_tables" / "cache.snbt"
            reward_table.parent.mkdir()
            reward_table.write_text(
                '{\n\tid: "9369E4AACBCDF5A1"\n\trewards: [ ]\n}\n',
                encoding="utf-8",
            )

            self.quests.write_catalog([], quest_root)

            self.assertIn(
                "table_id: 1398900581490095521L",
                chapter_path.read_text(encoding="utf-8"),
            )
            self.assertIn(
                'id: "1369E4AACBCDF5A1"',
                reward_table.read_text(encoding="utf-8"),
            )

    def test_signed_id_migration_preserves_id_shaped_authored_values(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, _mods_dir, unsafe_chapter = self.make_unsafe_migration_corpus(
                Path(temp_dir)
            )

            builder.normalize_quest_corpus_ids(quest_root)

            migrated = quest_root / "chapters" / "7EDCBA9876543210.snbt"
            self.assertFalse(unsafe_chapter.exists())
            self.assertTrue(migrated.is_file())
            chapter_text = migrated.read_text(encoding="utf-8")
            language_text = (quest_root / "lang" / "en_us.snbt").read_text(
                encoding="utf-8"
            )
            managed_state = json.loads(
                (quest_root / ".afterlight-managed.json").read_text(encoding="utf-8")
            )
            self.assertIn('id: "7EDCBA9876543210"', chapter_text)
            self.assertIn('id: "6EDCBA9876543210"', chapter_text)
            self.assertIn('id: "5EDCBA9876543210"', chapter_text)
            self.assertIn('id: "4EDCBA9876543210"', chapter_text)
            self.assertIn('note: "FEDCBA9876543210 is authored prose"', chapter_text)
            self.assertIn('component_probe: { value: "FEDCBA9876543210" }', chapter_text)
            self.assertIn(
                '"minecraft:custom_data": { probe: "FEDCBA9876543210" }',
                chapter_text,
            )
            self.assertIn('resource_probe: "example:FEDCBA9876543210"', chapter_text)
            self.assertIn('dependencies: ["6EDCBA9876543210"]', chapter_text)
            self.assertEqual(
                (quest_root / "unrelated.txt").read_text(encoding="utf-8"),
                "FEDCBA9876543210 stays unrelated\n",
            )
            self.assertIn(
                'chapter.7EDCBA9876543210.title: "FEDCBA9876543210 stays prose"',
                language_text,
            )
            self.assertIn(
                'quest.6EDCBA9876543210.quest_desc: ["FEDCBA9876543210 stays prose"]',
                language_text,
            )
            self.assertEqual(managed_state["chapters"], ["7EDCBA9876543210"])
            self.assertIn(
                "quest.6EDCBA9876543210.title",
                managed_state["localization_keys"],
            )

    def test_signed_id_migration_recovers_after_interrupted_writes(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                Path(temp_dir)
            )
            transaction = builder._migration_transaction_directory(quest_root)
            self.assertFalse(transaction.is_relative_to(quest_root))
            real_replace = builder.os.replace
            quest_writes = 0

            def interrupt_second_quest_write(source, target):
                nonlocal quest_writes
                target_path = Path(target)
                try:
                    target_path.relative_to(quest_root)
                except ValueError:
                    return real_replace(source, target)
                quest_writes += 1
                if quest_writes == 2:
                    raise OSError("injected migration write interruption")
                return real_replace(source, target)

            with mock.patch.object(
                builder.os,
                "replace",
                side_effect=interrupt_second_quest_write,
            ), self.assertRaisesRegex(OSError, "write interruption"):
                builder.normalize_quest_corpus_ids(quest_root)

            self.assertTrue((transaction / builder.MIGRATION_JOURNAL_NAME).is_file())
            self.assertFalse(
                (quest_root / builder.MIGRATION_JOURNAL_NAME).exists()
            )
            builder.normalize_quest_corpus_ids(quest_root)

            self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])
            self.assertFalse(transaction.exists())
            self.assertTrue(
                (quest_root / "chapters" / "7EDCBA9876543210.snbt").is_file()
            )
            self.assertFalse(
                (quest_root / "chapters" / "FEDCBA9876543210.snbt").exists()
            )

    def test_signed_id_migration_recovers_after_interrupted_path_move(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, mods_dir, unsafe_chapter = self.make_unsafe_migration_corpus(
                Path(temp_dir)
            )
            transaction = builder._migration_transaction_directory(quest_root)
            migrated_chapter = (
                quest_root / "chapters" / "7EDCBA9876543210.snbt"
            )
            real_path_replace = Path.replace

            def interrupt_after_target_copy(source: Path, target: Path):
                if source == unsafe_chapter:
                    shutil.copy2(source, target)
                    raise OSError("injected migration path interruption")
                return real_path_replace(source, target)

            with mock.patch.object(
                Path,
                "replace",
                autospec=True,
                side_effect=interrupt_after_target_copy,
            ), self.assertRaisesRegex(OSError, "path interruption"):
                builder.normalize_quest_corpus_ids(quest_root)

            self.assertTrue(unsafe_chapter.is_file())
            self.assertTrue(migrated_chapter.is_file())
            self.assertTrue((transaction / builder.MIGRATION_JOURNAL_NAME).is_file())

            builder.normalize_quest_corpus_ids(quest_root)

            self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])
            self.assertFalse(transaction.exists())
            self.assertFalse(unsafe_chapter.exists())
            self.assertTrue(migrated_chapter.is_file())

    def test_signed_id_migration_covers_complete_ftb_identity_schema(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, _mods_dir, unsafe_chapter = self.make_unsafe_migration_corpus(
                Path(temp_dir)
            )
            source = unsafe_chapter.read_text(encoding="utf-8")
            source = source.replace(
                '\tgroup: "4525BB3160467FCB"\n',
                '\tgroup: "4525BB3160467FCB"\n'
                '\tautofocus_id: "EEDCBA9876543210"\n'
                '\timages: [{\n'
                '\t\tid: "A222222222222222"\n'
                '\t\timage: "example:test"\n'
                '\t\tdependency: "EEDCBA9876543210"\n'
                '\t\tclick: "#EEDCBA9876543210/page/2"\n'
                '\t\tclick_action: "open_quest:EEDCBA9876543210/true"\n'
                '\t\thover: ["FEDCBA9876543210 stays image prose"]\n'
                '\t\tauthored_data: { value: "FEDCBA9876543210" }\n'
                '\t}\n'
                '\t{ id: "1222222222222222", image: "example:test", '
                'click: "https://example.invalid/FEDCBA9876543210" }\n'
                '\t{ id: "1333333333333333", image: "example:test", '
                'click: "custom:FEDCBA9876543210" }\n'
                '\t{ id: "1444444444444444", image: "example:test", '
                'click: "command:say FEDCBA9876543210" }]\n'
                '\tquest_links: [{ id: "B111111111111111", linked_quest: "EEDCBA9876543210" }]\n'
                '\tprose_map: { FEDCBA9876543210: "authored compound key" }\n',
                1,
            )
            source = source.replace(
                '\t\trewards: [{ id: "CEDCBA9876543210", type: "xp", xp: 1 }]\n',
                '\t\trewards: [\n'
                '\t\t\t{ id: "CEDCBA9876543210", type: "xp", xp: 1 }\n'
                '\t\t\t{ id: "A555555555555555", type: "loot", table_id: -1L, '
                'table_data: { rewards: [{ id: "B666666666666666", '
                'type: "loot", table_id: -1L }] } }\n'
                '\t\t\t{ id: "A777777777777777", type: "loot", table_id: -1L }\n'
                '\t\t]\n',
                1,
            )
            source = source.replace(
                '\t\tdependencies: ["EEDCBA9876543210"]\n',
                '\t\tdependencies: ["EEDCBA9876543210"]\n'
                '\t\tdep_control_pts: { EEDCBA9876543210: '
                '[1.0d, 2.0d, 3.0d, 4.0d] }\n',
                1,
            )
            unsafe_chapter.write_text(source, encoding="utf-8")
            reward_tables = quest_root / "reward_tables"
            reward_tables.mkdir()
            (reward_tables / "maximum.snbt").write_text(
                "{\n"
                '\tid: "FFFFFFFFFFFFFFFF"\n'
                "\trewards: [{\n"
                '\t\tid: "A333333333333333"\n'
                '\t\ttype: "loot"\n'
                "\t\ttable_id: -1L\n"
                "\t\ttable_data: { rewards: [{\n"
                '\t\t\tid: "B444444444444444"\n'
                '\t\t\ttype: "loot"\n'
                "\t\t\ttable_id: -1L\n"
                "\t\t}] }\n"
                "\t}]\n"
                "}\n",
                encoding="utf-8",
            )
            (reward_tables / "standalone.snbt").write_text(
                "{\n"
                '\tid: "0123456789ABCDEF"\n'
                "\trewards: [{\n"
                '\t\tid: "C888888888888888"\n'
                '\t\ttype: "loot"\n'
                "\t\ttable_id: -1L\n"
                "\t}]\n"
                "}\n",
                encoding="utf-8",
            )
            language = quest_root / "lang/en_us.snbt"
            language_source = language.read_text(encoding="utf-8").rstrip()
            language.write_text(
                language_source[:-1]
                + '\timage.A222222222222222.title: "Image"\n'
                + '\tquest_link.B111111111111111.title: "Link"\n'
                + '\treward_table.FFFFFFFFFFFFFFFF.title: "Table"\n'
                + '\tunknown.FFFFFFFFFFFFFFFF.title: "Preserved"\n'
                + "}\n",
                encoding="utf-8",
            )

            builder.normalize_quest_corpus_ids(quest_root)

            migrated_path = quest_root / "chapters/7EDCBA9876543210.snbt"
            migrated_text = migrated_path.read_text(encoding="utf-8")
            migrated = builder._parse_snbt(migrated_text)
            self.assertEqual(migrated["autofocus_id"], "6EDCBA9876543210")
            self.assertEqual(migrated["quest_links"][0]["id"], "3111111111111111")
            self.assertEqual(
                migrated["quest_links"][0]["linked_quest"],
                "6EDCBA9876543210",
            )
            image = migrated["images"][0]
            self.assertEqual(image["id"], "2222222222222222")
            self.assertEqual(image["click"], "#6EDCBA9876543210/page/2")
            for location, actual, expected in (
                (
                    "image dependency",
                    image["dependency"],
                    "6EDCBA9876543210",
                ),
                (
                    "image open_quest",
                    image["click_action"],
                    "open_quest:6EDCBA9876543210/true",
                ),
                (
                    "quest dep_control_pts",
                    "6EDCBA9876543210"
                    in migrated["quests"][1]["dep_control_pts"],
                    True,
                ),
            ):
                with self.subTest(location=location):
                    self.assertEqual(actual, expected)
            self.assertEqual(
                [entry["click"] for entry in migrated["images"][1:]],
                [
                    "https://example.invalid/FEDCBA9876543210",
                    "custom:FEDCBA9876543210",
                    "command:say FEDCBA9876543210",
                ],
            )
            embedded = migrated["quests"][0]["rewards"][1]
            external = migrated["quests"][0]["rewards"][2]
            self.assertEqual(embedded["table_id"], "-1L")
            self.assertEqual(embedded["id"], "2555555555555555")
            self.assertEqual(
                embedded["table_data"]["rewards"][0]["id"],
                "3666666666666666",
            )
            self.assertEqual(
                embedded["table_data"]["rewards"][0]["table_id"],
                "9223372036854775807L",
            )
            self.assertEqual(external["table_id"], "9223372036854775807L")
            migrated_table = builder._parse_snbt(
                (reward_tables / "maximum.snbt").read_text(encoding="utf-8")
            )
            self.assertEqual(migrated_table["id"], "7FFFFFFFFFFFFFFF")
            self.assertEqual(migrated_table["rewards"][0]["table_id"], "-1L")
            self.assertEqual(
                migrated_table["rewards"][0]["table_data"]["rewards"][0]["id"],
                "3444444444444444",
            )
            self.assertEqual(
                migrated_table["rewards"][0]["table_data"]["rewards"][0][
                    "table_id"
                ],
                "9223372036854775807L",
            )
            standalone_table = builder._parse_snbt(
                (reward_tables / "standalone.snbt").read_text(encoding="utf-8")
            )
            self.assertEqual(
                standalone_table["rewards"][0]["id"],
                "4888888888888888",
            )
            self.assertEqual(
                standalone_table["rewards"][0]["table_id"],
                "9223372036854775807L",
            )
            migrated_language = language.read_text(encoding="utf-8")
            self.assertIn("image.2222222222222222.title", migrated_language)
            self.assertIn("quest_link.3111111111111111.title", migrated_language)
            self.assertIn(
                "reward_table.7FFFFFFFFFFFFFFF.title",
                migrated_language,
            )
            self.assertIn("unknown.FFFFFFFFFFFFFFFF.title", migrated_language)
            self.assertEqual(
                image["hover"],
                ["FEDCBA9876543210 stays image prose"],
            )
            self.assertEqual(
                image["authored_data"],
                {"value": "FEDCBA9876543210"},
            )
            self.assertNotIn("dep_control_pts", migrated)
            self.assertIn(
                'prose_map: { FEDCBA9876543210: "authored compound key" }',
                migrated_text,
            )

    def test_signed_id_validator_is_independent_from_rewrite_classifier(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        relative = Path("chapters/1234567890ABCDEF.snbt")
        base = {
            "filename": "1234567890ABCDEF",
            "group": "4525BB3160467FCB",
            "id": "1234567890ABCDEF",
            "images": [
                {
                    "id": "1111111111111111",
                    "image": "example:test",
                }
            ],
            "quest_links": [],
            "quests": [
                {
                    "id": "234567890ABCDEF0",
                    "tasks": [],
                    "rewards": [],
                }
            ],
        }
        for location in (
            "quest dep_control_pts",
            "image dependency",
            "image open_quest",
            "legacy image open_quest",
        ):
            with self.subTest(location=location):
                chapter = json.loads(json.dumps(base))
                if location == "quest dep_control_pts":
                    chapter["quests"][0]["dep_control_pts"] = {
                        "F111111111111111": [1.0, 2.0, 3.0, 4.0]
                    }
                elif location == "image dependency":
                    chapter["images"][0]["dependency"] = "F111111111111111"
                elif location == "image open_quest":
                    chapter["images"][0]["click_action"] = (
                        "open_quest:F111111111111111/true"
                    )
                else:
                    chapter["images"][0]["click"] = "#F111111111111111/page/2"
                with mock.patch.object(
                    builder,
                    "_migration_snbt_role",
                    return_value=None,
                ):
                    with self.assertRaisesRegex(
                        ValueError,
                        "signed-safe FTB identity",
                    ):
                        builder._validate_known_ftb_identity_containers(
                            relative,
                            chapter,
                        )

    def test_migrated_oracle_binds_localization_to_exact_object_types(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, identifiers = self.make_typed_validation_corpus(
                Path(temp_dir)
            )
            reward_data = (
                f'{{ id: "{identifiers["reward"]}", type: "loot", '
                f'table_id: {int(identifiers["max_table"], 16)}L }}'
            )
            self.write_simple_typed_chapters(
                quest_root,
                identifiers,
                reward_data,
                autofocus_id=identifiers["quest"],
            )
            language = quest_root / "lang/en_us.snbt"
            language.write_text(
                language.read_text(encoding="utf-8").replace(
                    f'image.{identifiers["image"]}.title',
                    f'image.{identifiers["quest"]}.title',
                ),
                encoding="utf-8",
            )

            with mock.patch.object(
                builder,
                "_migration_localization_key",
                side_effect=lambda value: value,
            ), self.assertRaisesRegex(ValueError, "localization.*image"):
                builder._validate_migrated_quest_corpus(quest_root)

    def test_migrated_oracle_uses_pinned_typed_reference_universes(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        for autofocus_kind in ("quest", "link", "image"):
            with self.subTest(autofocus_kind=autofocus_kind):
                with tempfile.TemporaryDirectory() as temp_dir:
                    quest_root, identifiers = self.make_typed_validation_corpus(
                        Path(temp_dir)
                    )
                    chapter = (
                        quest_root
                        / "chapters"
                        / f'{identifiers["chapter"]}.snbt'
                    )
                    chapter.write_text(
                        chapter.read_text(encoding="utf-8").replace(
                            f'autofocus_id: "{identifiers["quest"]}"',
                            f'autofocus_id: "{identifiers[autofocus_kind]}"',
                        ),
                        encoding="utf-8",
                    )

                    builder._validate_migrated_quest_corpus(quest_root)

    def test_migrated_oracle_resolves_dep_control_points_only_to_quests(
        self,
    ) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, _identifiers = self.make_typed_validation_corpus(
                Path(temp_dir)
            )
            with mock.patch.object(
                builder,
                "_migration_snbt_role",
                return_value=None,
            ):
                builder._validate_migrated_quest_corpus(quest_root)

        for target_kind in ("task", "link", "chapter", "group"):
            with self.subTest(target_kind=target_kind):
                with tempfile.TemporaryDirectory() as temp_dir:
                    quest_root, identifiers = self.make_typed_validation_corpus(
                        Path(temp_dir)
                    )
                    chapter = (
                        quest_root
                        / "chapters"
                        / f'{identifiers["chapter"]}.snbt'
                    )
                    chapter.write_text(
                        chapter.read_text(encoding="utf-8").replace(
                            f'{identifiers["quest"]}: '
                            "[1.0d, 2.0d, 3.0d, 4.0d]",
                            f'{identifiers[target_kind]}: '
                            "[1.0d, 2.0d, 3.0d, 4.0d]",
                            1,
                        ),
                        encoding="utf-8",
                    )

                    with mock.patch.object(
                        builder,
                        "_migration_snbt_role",
                        return_value=None,
                    ), self.assertRaisesRegex(ValueError, "dep_control_pts"):
                        builder._validate_migrated_quest_corpus(quest_root)

    def test_migrated_oracle_rejects_cross_chapter_autofocus_and_unknown_legacy_click(
        self,
    ) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        other_quest = "0123456789ABCDEF"
        reward_data_template = (
            '{{ id: "{reward}", type: "loot", table_id: {table_id}L }}'
        )
        for case in ("cross-chapter autofocus", "unknown legacy click"):
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    quest_root, identifiers = self.make_typed_validation_corpus(
                        Path(temp_dir)
                    )
                    reward_data = reward_data_template.format(
                        reward=identifiers["reward"],
                        table_id=int(identifiers["max_table"], 16),
                    )
                    self.write_simple_typed_chapters(
                        quest_root,
                        identifiers,
                        reward_data,
                        autofocus_id=(
                            other_quest
                            if case == "cross-chapter autofocus"
                            else identifiers["quest"]
                        ),
                        other_quest_id=other_quest,
                    )
                    if case == "unknown legacy click":
                        chapter = (
                            quest_root
                            / "chapters"
                            / f'{identifiers["chapter"]}.snbt'
                        )
                        chapter.write_text(
                            chapter.read_text(encoding="utf-8").replace(
                                'image: "example:test"',
                                'image: "example:test", '
                                'click: "#0000000000000009/page/2"',
                            ),
                            encoding="utf-8",
                        )

                    with self.assertRaisesRegex(
                        ValueError,
                        "autofocus|legacy image click",
                    ):
                        builder._validate_migrated_quest_corpus(quest_root)

    def test_embedded_random_reward_sentinel_is_contextual(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        nested_reward = "567890ABCDEF0123"
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, identifiers = self.make_typed_validation_corpus(
                Path(temp_dir)
            )
            reward_data = (
                f'{{ id: "{identifiers["reward"]}", type: "loot", '
                'table_id: -1L, table_data: { rewards: [{ '
                f'id: "{nested_reward}", type: "loot", '
                f'table_id: {int(identifiers["max_table"], 16)}L }}] }} }}'
            )
            self.write_simple_typed_chapters(
                quest_root,
                identifiers,
                reward_data,
                autofocus_id=identifiers["quest"],
            )

            builder._validate_migrated_quest_corpus(quest_root)

        malformed = (
            (
                "external-id-with-data",
                'table_id: {table_id}L, table_data: {{ rewards: [] }}',
            ),
            ("missing-sentinel", "table_data: {{ rewards: [] }}"),
            ("invalid-table-data", "table_id: -1L, table_data: []"),
        )
        for case, fields in malformed:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as temp_dir:
                    quest_root, identifiers = self.make_typed_validation_corpus(
                        Path(temp_dir)
                    )
                    reward_data = (
                        f'{{ id: "{identifiers["reward"]}", type: "loot", '
                        + fields.format(
                            table_id=int(identifiers["max_table"], 16)
                        )
                        + " }"
                    )
                    self.write_simple_typed_chapters(
                        quest_root,
                        identifiers,
                        reward_data,
                        autofocus_id=identifiers["quest"],
                    )

                    with self.assertRaisesRegex(
                        ValueError,
                        "embedded reward table|table_data|sentinel",
                    ):
                        builder._validate_migrated_quest_corpus(quest_root)

    def test_recursive_reward_validation_has_depth_and_node_bounds(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        relative = Path("reward_tables/fixture.snbt")
        nested = builder._parse_snbt(
            "{ id: \"34567890ABCDEF01\", rewards: [{ "
            "id: \"4567890ABCDEF012\", type: \"random\", table_id: -1L, "
            "table_data: { rewards: [{ id: \"567890ABCDEF0123\", "
            "type: \"xp\", xp: 1 }] } }] }"
        )
        with mock.patch.object(
            builder,
            "MIGRATION_REWARD_MAX_DEPTH",
            0,
            create=True,
        ), self.assertRaisesRegex(ValueError, "reward table recursion depth"):
            builder._validate_known_ftb_identity_containers(relative, nested)

        wide = builder._parse_snbt(
            "{ id: \"34567890ABCDEF01\", rewards: ["
            "{ id: \"4567890ABCDEF012\", type: \"xp\", xp: 1 },"
            "{ id: \"567890ABCDEF0123\", type: \"xp\", xp: 1 }] }"
        )
        with mock.patch.object(
            builder,
            "MIGRATION_REWARD_MAX_NODES",
            1,
            create=True,
        ), self.assertRaisesRegex(ValueError, "reward node count"):
            builder._validate_known_ftb_identity_containers(relative, wide)

    def test_recursive_reward_oracle_resolves_nested_external_tables(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            quest_root, identifiers = self.make_typed_validation_corpus(
                Path(temp_dir)
            )
            reward_data = (
                f'{{ id: "{identifiers["reward"]}", type: "loot", '
                f'table_id: {int(identifiers["max_table"], 16)}L }}'
            )
            self.write_simple_typed_chapters(
                quest_root,
                identifiers,
                reward_data,
                autofocus_id=identifiers["quest"],
            )
            (quest_root / "reward_tables/fixture.snbt").write_text(
                "{\n"
                f'\tid: "{identifiers["table"]}"\n'
                "\trewards: [{\n"
                f'\t\tid: "{identifiers["table_reward"]}"\n'
                '\t\ttype: "loot"\n'
                "\t\ttable_id: -1L\n"
                "\t\ttable_data: { rewards: [{\n"
                '\t\t\tid: "567890ABCDEF0123"\n'
                '\t\t\ttype: "loot"\n'
                "\t\t\ttable_id: 9L\n"
                "\t\t}] }\n"
                "\t}]\n"
                "}\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "reward table references are unresolved",
            ):
                builder._validate_migrated_quest_corpus(quest_root)

    def test_migration_preflights_all_payloads_before_repository_changes(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root, _mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base
            )
            transaction = base / "state/transaction"
            self.assertTrue(builder._migration_build_transaction(quest_root, transaction))
            journal = json.loads(
                (transaction / builder.MIGRATION_JOURNAL_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshots = {
                write["target"]: (quest_root / write["target"]).read_bytes()
                for write in journal["writes"]
            }
            final_write = journal["writes"][-1]
            payload = transaction / "stage" / final_write["payload"]
            payload.write_bytes(payload.read_bytes() + b"corrupt")
            backup_payload = (
                transaction
                / builder.MIGRATION_STAGE_BACKUP_NAME
                / final_write["payload"]
            )
            if backup_payload.exists():
                backup_payload.write_bytes(b"corrupt backup payload")

            with self.assertRaisesRegex(ValueError, "staged FTB ID migration payload"):
                builder._migration_apply_transaction(quest_root, transaction)

            self.assertEqual(
                {
                    target: (quest_root / target).read_bytes()
                    for target in snapshots
                },
                snapshots,
            )

    def test_migration_rehashes_repaired_stage_before_repository_changes(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root, _mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base
            )
            transaction = base / "state/transaction"
            self.assertTrue(builder._migration_build_transaction(quest_root, transaction))
            journal = json.loads(
                (transaction / builder.MIGRATION_JOURNAL_NAME).read_text(
                    encoding="utf-8"
                )
            )
            snapshots = {
                write["target"]: (quest_root / write["target"]).read_bytes()
                for write in journal["writes"]
            }
            final_write = journal["writes"][-1]
            repaired_stage = transaction / "stage" / final_write["payload"]
            repaired_stage.write_bytes(b"force repair from authenticated backup")
            real_copy = builder._durable_copy_file

            def corrupt_repaired_copy(source: Path, target: Path, mode: int) -> None:
                real_copy(source, target, mode)
                if target == repaired_stage:
                    target.write_bytes(target.read_bytes() + b"corrupt after repair")

            with mock.patch.object(
                builder,
                "_durable_copy_file",
                side_effect=corrupt_repaired_copy,
            ), self.assertRaisesRegex(
                ValueError,
                "staged FTB ID migration payload",
            ):
                builder._migration_apply_transaction(quest_root, transaction)

            self.assertEqual(
                {
                    target: (quest_root / target).read_bytes()
                    for target in snapshots
                },
                snapshots,
            )

    def test_migration_state_root_is_durable_and_checkout_independent(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            state_root = base / "state"
            quest_root, _mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base / "checkout"
            )
            with mock.patch.dict(
                os.environ,
                {"AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT": str(state_root)},
            ):
                original = builder._migration_transaction_directory(quest_root)
                relocated_base = base / "relocated"
                (base / "checkout").rename(relocated_base)
                relocated = relocated_base / "config/ftbquests/quests"
                moved = builder._migration_transaction_directory(relocated)

            self.assertTrue(original.is_relative_to(state_root))
            self.assertEqual(moved, original)

    def test_migration_recovers_truncated_journal_and_corrupt_stage(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            for fault in ("journal", "stage"):
                with self.subTest(fault=fault):
                    case = base / fault
                    quest_root, mods_dir, _unsafe_chapter = (
                        self.make_unsafe_migration_corpus(case)
                    )
                    transaction = case / "state/transaction"
                    self.assertTrue(
                        builder._migration_build_transaction(quest_root, transaction)
                    )
                    if fault == "journal":
                        (transaction / builder.MIGRATION_JOURNAL_NAME).write_bytes(
                            b'{"version":'
                        )
                    else:
                        journal = json.loads(
                            (transaction / builder.MIGRATION_JOURNAL_NAME).read_text(
                                encoding="utf-8"
                            )
                        )
                        payload = transaction / "stage" / journal["writes"][-1]["payload"]
                        payload.write_bytes(b"corrupt staged payload")

                    try:
                        builder._migration_apply_transaction(quest_root, transaction)
                    except ValueError as error:
                        self.fail(f"migration recovery failed: {error}")

                    self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])
                    self.assertFalse(transaction.exists())

    def test_migration_recovers_missing_target_and_cleans_orphan_temp(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root, mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base
            )
            transaction = base / "state/transaction"
            self.assertTrue(builder._migration_build_transaction(quest_root, transaction))
            journal = json.loads(
                (transaction / builder.MIGRATION_JOURNAL_NAME).read_text(
                    encoding="utf-8"
                )
            )
            write = next(
                item
                for item in journal["writes"]
                if item["target"] == item["payload"]
            )
            target = quest_root / write["target"]
            target.unlink()
            orphan = target.parent / f".{target.name}.orphan.migration"
            orphan.write_bytes(b"orphan")

            try:
                builder._migration_apply_transaction(quest_root, transaction)
            except ValueError as error:
                self.fail(f"missing-target recovery failed: {error}")

            self.assertEqual(self.quests.validate_quests(quest_root, mods_dir), [])
            self.assertFalse(orphan.exists())
            self.assertFalse(transaction.exists())

    def test_migration_detects_stage_change_after_preflight(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root, _mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base
            )
            transaction = base / "state/transaction"
            self.assertTrue(builder._migration_build_transaction(quest_root, transaction))
            real_replace = builder._replace_migration_file
            mutated = False

            def mutate_after_preflight(
                source: Path,
                target: Path,
                mode: int,
                expected_sha256: str | None = None,
            ):
                nonlocal mutated
                if not mutated and source.name == builder.MANAGED_STATE_NAME:
                    payload = json.loads(source.read_text(encoding="utf-8"))
                    payload["unrelated_probe"] = True
                    source.write_text(
                        json.dumps(payload, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8",
                    )
                    mutated = True
                if expected_sha256 is None:
                    return real_replace(source, target, mode)
                return real_replace(source, target, mode, expected_sha256)

            with mock.patch.object(
                builder,
                "_replace_migration_file",
                side_effect=mutate_after_preflight,
            ), self.assertRaisesRegex(ValueError, "staged.*changed|payload.*hash"):
                builder._migration_apply_transaction(quest_root, transaction)

            self.assertTrue(mutated)
            self.assertTrue(transaction.exists())

    def test_migration_process_death_recovers_after_checkout_relocation(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            checkout = base / "checkout"
            state_root = base / "state"
            quest_root, mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                checkout
            )
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(TOOLS)
            environment["AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT"] = str(state_root)
            with mock.patch.dict(os.environ, environment, clear=True):
                transaction = builder._migration_transaction_directory(quest_root)
            interrupt = (
                "import os\n"
                "from pathlib import Path\n"
                "from afterlight_quests import builder\n"
                f"root = Path({str(quest_root)!r})\n"
                "real_replace = builder.os.replace\n"
                "published = 0\n"
                "def terminate(source, target):\n"
                "    global published\n"
                "    result = real_replace(source, target)\n"
                "    try:\n"
                "        Path(target).relative_to(root)\n"
                "    except ValueError:\n"
                "        return result\n"
                "    published += 1\n"
                "    if published == 1:\n"
                "        os._exit(73)\n"
                "    return result\n"
                "builder.os.replace = terminate\n"
                "builder.normalize_quest_corpus_ids(root)\n"
            )
            try:
                interrupted = subprocess.run(
                    [sys.executable, "-c", interrupt],
                    cwd=ROOT,
                    env=environment,
                    check=False,
                )
                self.assertEqual(interrupted.returncode, 73)
                self.assertTrue(transaction.exists())

                relocated_checkout = base / "relocated"
                checkout.rename(relocated_checkout)
                relocated_root = relocated_checkout / "config/ftbquests/quests"
                resumed = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; "
                        "from afterlight_quests import builder; "
                        f"builder.normalize_quest_corpus_ids(Path({str(relocated_root)!r}))",
                    ],
                    cwd=ROOT,
                    env=environment,
                    check=False,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(resumed.returncode, 0, resumed.stderr)
                self.assertEqual(
                    self.quests.validate_quests(
                        relocated_root,
                        relocated_checkout / "mods",
                    ),
                    [],
                )
                self.assertFalse(transaction.exists())
            finally:
                shutil.rmtree(transaction, ignore_errors=True)

    def test_migration_fsyncs_state_and_target_directories(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            state_root = base / "state"
            quest_root, _mods_dir, _unsafe_chapter = self.make_unsafe_migration_corpus(
                base / "checkout"
            )
            real_fsync = builder.os.fsync
            directory_fsyncs: list[tuple[int, int]] = []

            def record_fsync(descriptor: int):
                descriptor_stat = os.fstat(descriptor)
                if stat.S_ISDIR(descriptor_stat.st_mode):
                    directory_fsyncs.append(
                        (descriptor_stat.st_dev, descriptor_stat.st_ino)
                    )
                return real_fsync(descriptor)

            with mock.patch.dict(
                os.environ,
                {"AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT": str(state_root)},
            ), mock.patch.object(builder.os, "fsync", side_effect=record_fsync):
                builder.normalize_quest_corpus_ids(quest_root)

            self.assertGreaterEqual(len(set(directory_fsyncs)), 2)

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

    def test_all_energy_tasks_use_the_registered_neoforge_type(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        energy_tasks = []
        for path in sorted((ROOT / "config/ftbquests/quests/chapters").glob("*.snbt")):
            parsed = _parse_snbt(path.read_text(encoding="utf-8"))
            for quest in parsed["quests"]:
                for task in quest["tasks"]:
                    if task.get("type") in {"energy", "forge_energy"}:
                        energy_tasks.append((quest["id"], task["id"], task["type"]))

        self.assertTrue(energy_tasks)
        self.assertNotIn("energy", {task_type for _quest, _task, task_type in energy_tasks})
        self.assertIn(
            ("752409F46D854A92", "14E2851EC7427F5A", "forge_energy"),
            energy_tasks,
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
        self.assertEqual([chapter.order_index for chapter in catalog], [6, 7, 8, 9, 10, 11])
        self.assertEqual(catalog[0].quests[0].dependency_ids, ("5A407B47132C07C6",))
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
        self.assertEqual([chapter.order_index for chapter in catalog], [12, 13, 14, 15, 16])
        self.assertEqual(catalog[0].quests[0].dependency_ids, ("036D1C6E20B78461",))
        for previous, current in zip(catalog[:-1], catalog[1:-1]):
            self.assertEqual(current.quests[0].dependency_ids, (previous.quests[-1].id,))
        self.assertEqual(
            catalog[-1].quests[0].dependency_ids,
            (
                "10EDD2BED35BE9E3",
                "752C3E53CA89C92D",
                "21A99D99B372916F",
                "3497EFDF016FAFD7",
            ),
        )
        self.assertEqual(
            [chapter.quests[-1].id for chapter in catalog],
            [
                "10EDD2BED35BE9E3",
                "752C3E53CA89C92D",
                "21A99D99B372916F",
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
            [task.data["item"]["id"] for task in quests["Four Keys"].tasks],
            [
                "kubejs:schematic_kinetic_frame",
                "kubejs:schematic_industrial_anchor",
                "kubejs:schematic_isotopic_core",
                "kubejs:schematic_lattice_matrix",
            ],
        )
        self.assertTrue(all(
            task.task_type == "item"
            and task.data["count"] == self.quests.SnbtLong(1)
            and task.data["consume_items"] is False
            for task in quests["Four Keys"].tasks
        ))
        certified = quests["Certified Bulk Quotas"]
        self.assertEqual(len(certified.tasks), 1)
        self.assertEqual(certified.tasks[0].task_type, "checkmark")
        self.assertEqual(certified.tasks[0].data, {})
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
            (11, 104, 111, 137),
        )

    def test_repeatable_quest_fields_render_exact_ftb_schema(self) -> None:
        catalog = self.make_catalog()
        catalog[0].quests[0].can_repeat = True
        catalog[0].quests[0].repeat_cooldown = 5

        rendered = self.quests.render_chapter(catalog[0])

        self.assertIn("\t\t\tcan_repeat: true", rendered)
        self.assertIn("\t\t\trepeat_cooldown: 5", rendered)

    def test_dependency_requirement_renders_and_rejects_unknown_modes(self) -> None:
        catalog = self.make_catalog(dependency="2AAAAAAAAAAAAAAA")
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
        full_catalog = self.quests.build_catalog()
        catalog = [
            chapter for chapter in full_catalog
            if chapter.group.resolved_id == "4A20F33642175B95"
        ]

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
            chapter.group.resolved_id == "4A20F33642175B95"
            for chapter in catalog
        ))
        self.assertEqual([chapter.order_index for chapter in catalog], [1, 2, 3, 4, 5, 6, 20, 21, 22])
        task_five_catalog = [
            chapter for chapter in full_catalog
            if (
                chapter.group.resolved_id == "4525BB3160467FCB"
                and chapter.order_index <= 16
                and chapter.id != "6C40000000000001"
            )
            or chapter.group.resolved_id == "4A20F33642175B95"
        ]
        self.assertEqual(
            (
                len(task_five_catalog),
                sum(len(chapter.quests) for chapter in task_five_catalog),
                sum(len(quest.tasks) for chapter in task_five_catalog for quest in chapter.quests),
                sum(len(quest.rewards) for chapter in task_five_catalog for quest in chapter.quests),
            ),
            (20, 143, 151, 188),
        )

    def test_task_five_certification_finales_award_exact_stages(self) -> None:
        certifications = [
            chapter for chapter in self.quests.build_catalog()
            if chapter.title in {
                "Logistics I", "Ore Loop I", "Autocrafting I", "Cross-Mod I",
                "Power I", "Infrastructure II",
            }
        ]
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
            infrastructure_proof.dependency_ids,
            (
                "5ADAE277C9FEF0F1",
                "3107D8813D59B2FF",
                "66CDE7B061D8DA5C",
                "42EE25F560AE65CD",
                "61F5D15817ED5EFD",
                "7C9EA276C2D84333",
            ),
        )
        self.assertEqual(len(infrastructure_proof.tasks), 1)
        self.assertEqual(infrastructure_proof.tasks[0].task_type, "checkmark")
        self.assertEqual(infrastructure_proof.tasks[0].data, {})

    def test_task_five_power_certification_uses_real_grid_finale(self) -> None:
        power = next(
            chapter for chapter in self.quests.build_catalog()
            if chapter.title == "Power I"
        )

        self.assertEqual(
            power.quests[0].dependency_ids,
            ("6B876A865DE7A77A",),
        )

    def test_task_five_logistics_matches_installed_pipez_upgrade_capabilities(self) -> None:
        logistics = next(
            chapter for chapter in self.quests.build_catalog()
            if chapter.title == "Logistics I"
        )

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
        ore_loop = next(
            chapter for chapter in self.quests.build_catalog()
            if chapter.title == "Ore Loop I"
        )

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
        cross_mod = next(
            chapter for chapter in self.quests.build_catalog()
            if chapter.title == "Cross-Mod I"
        )

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
        depots = [
            chapter for chapter in self.quests.build_catalog()
            if chapter.title.startswith("Requisition Depot:")
        ]
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
        side_group_ids = {
            "51FF272F5030D2E6", "4DEAD1F5F7AB4DA3", "48F8381D9519D002",
        }
        catalog = [
            chapter for chapter in self.quests.build_catalog()
            if chapter.group.resolved_id in side_group_ids
        ]

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
            "5CDF0BB344B02192",
            "11D0B654D6E9B714",
            "045647E54F0A1D9E",
            "1A6C8CE2A6D208F9",
            "3C0EE28909760862",
            "0A48AB2CC20BC026",
            "7A26679C913AAF90",
            "5307E7406CB0DAE6",
            "4CEEFB108A0EECF8",
            "170AB7B39A0C4E47",
            "6A433C07EC56210B",
            "6EFD817FBDA0461F",
        ])
        self.assertEqual([chapter.quests[-1].id for chapter in catalog], [
            "051EA7B2A3B36BFD",
            "5F26F92E726A22AC",
            "49286624F8D7D554",
            "07338DE0FE8114CF",
            "4F4161F5B97E27ED",
            "3E1151169E81AD32",
            "7131E55FB7E21244",
            "505A306462A8BC7E",
            "0DAB608A7B083DB8",
            "26E98713CAC0A689",
            "231CFB60DB42BD03",
            "00EB5746A726C5B4",
        ])
        self.assertEqual(
            [chapter.group.resolved_id for chapter in catalog],
            ["51FF272F5030D2E6"] * 4
            + ["4DEAD1F5F7AB4DA3"] * 4
            + ["48F8381D9519D002"] * 4,
        )
        full_catalog = self.quests.build_catalog()
        self.assertEqual(
            (
                len(full_catalog),
                sum(len(chapter.quests) for chapter in full_catalog),
                sum(len(quest.tasks) for chapter in full_catalog for quest in chapter.quests),
                sum(len(quest.rewards) for chapter in full_catalog for quest in chapter.quests),
            ),
            (38, 259, 279, 344),
        )

    def test_task_six_undercurrent_requires_ars_plus_exactly_one_branch(self) -> None:
        chapters = {
            chapter.title: chapter for chapter in self.quests.build_catalog()
            if chapter.group.resolved_id == "51FF272F5030D2E6"
        }
        ars_finale = "7480D99D56556C8E"
        branch_finales = (
            "051EA7B2A3B36BFD",
            "5F26F92E726A22AC",
            "49286624F8D7D554",
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
            "16783315E0833B1D",
            "747D181BE87A2429",
            "1738976FB1A6167A",
            "5EEFEE4A3873DE5C",
            "72CE68CEF727A313",
        ])
        self.assertEqual(
            [task["id"] for quest in parsed["quests"] for task in quest["tasks"]],
            [
                "6595488C9696FD3D",
                "4C3B34BB975A26E4",
                "70386E249F64C241",
                "448C181914369553",
                "08B818D0316B37F9",
                "1BE02019A215A7C4",
            ],
        )
        self.assertEqual(
            [reward["id"] for quest in parsed["quests"] for reward in quest["rewards"]],
            [
                "300AB696B71C85DF",
                "3AB2DC0BCB5633EE",
                "3F4B8DA2BF026248",
                "16B4C8E5A1B26706",
                "60C70F21C10E9726",
                "5DF12C4395F6A64A",
                "375634D32BF15E2B",
                "137D55E3FC4E0FC8",
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
            localization["quest.16783315E0833B1D.quest_desc"],
        )

    def test_task_six_side_graph_has_only_planned_story_dependency_and_is_acyclic(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        catalog = self.quests.build_catalog()
        story_group_id = catalog[0].group.resolved_id
        side_group_ids = {
            "51FF272F5030D2E6", "4DEAD1F5F7AB4DA3", "48F8381D9519D002",
        }
        side_chapters = [
            chapter for chapter in catalog
            if chapter.group.resolved_id in side_group_ids
        ]
        side_quest_ids = {
            quest.id
            for chapter in side_chapters
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
        self.assertEqual(
            side_quest_ids & story_dependencies,
            {"07338DE0FE8114CF"},
        )

        deep_vault = [
            chapter for chapter in catalog
            if chapter.group.resolved_id == "4DEAD1F5F7AB4DA3"
        ]
        self.assertEqual(deep_vault[0].quests[0].dependency_ids, ("72CE68CEF727A313",))
        for previous, current in zip(deep_vault, deep_vault[1:]):
            self.assertEqual(current.quests[0].dependency_ids, (previous.quests[-1].id,))

        atlas = [
            chapter for chapter in catalog
            if chapter.group.resolved_id == "48F8381D9519D002"
        ]
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
        for chapter in self.quests.build_catalog():
            if chapter.group.resolved_id not in {
                "51FF272F5030D2E6", "4DEAD1F5F7AB4DA3", "48F8381D9519D002",
            }:
                continue
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
                "13E278CD695BCE11",
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
            unmanaged = quest_root / "chapters" / "2AAAAAAAAAAAAAAA.snbt"
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
            self.assertIn("quest.2AAAAAAAAAAAAAAA.title", first_language)
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
            unmanaged = quest_root / "chapters" / "2AAAAAAAAAAAAAAA.snbt"
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

    def test_validator_rejects_non_string_progression_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            quest_root = self.make_quest_root(base)
            mods_dir = base / "mods"
            self.make_mod_jar(mods_dir)
            catalog = self.make_catalog()
            catalog[0].quests[0].progression_mode = "linear"
            self.quests.write_catalog(catalog, quest_root)
            chapter_path = quest_root / "chapters" / f"{catalog[0].id}.snbt"
            original = chapter_path.read_text(encoding="utf-8")
            malformed = original.replace(
                'progression_mode: "linear"',
                "progression_mode: []",
                1,
            )
            self.assertNotEqual(malformed, original)
            chapter_path.write_text(malformed, encoding="utf-8")

            try:
                errors = self.quests.validate_quests(quest_root, mods_dir)
            except TypeError as error:
                self.fail(f"validate_quests raised TypeError: {error}")
            self.assertTrue(
                any("invalid progression mode" in error for error in errors),
                errors,
            )

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
                f'id: "{quest.id}"\n\t\t\tdependencies: ["7FFFFFFFFFFFFFFF"]',
                1,
            ),
            "em dash": lambda text, chapter, quest: text.replace(
                'filename:', 'note: "forbidden \u2014 punctuation"\n\tfilename:', 1
            ),
            "filename/id mismatch": lambda text, chapter, quest: text.replace(
                f'filename: "{chapter.id}"', 'filename: "2AAAAAAAAAAAAAAA"', 1
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

    def test_validator_rejects_high_bit_ftb_id(self) -> None:
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
                    f'id: "{task_id}"',
                    'id: "FFFFFFFFFFFFFFFF"',
                    1,
                ),
                encoding="utf-8",
            )

            errors = self.quests.validate_quests(quest_root, mods_dir)
            self.assertTrue(
                any("signed-safe FTB ID" in error for error in errors),
                errors,
            )

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
                    '\t\t\t\t"7FFFFFFFFFFFFFFF"\n\t\t\t]',
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


class LegacyStoryQuestContractTests(unittest.TestCase):
    def test_slow_fire_tracks_the_coke_oven_multiblock_advancement(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        chapter_path = (
            ROOT
            / "config"
            / "ftbquests"
            / "quests"
            / "chapters"
            / "45491A24F6B8C192.snbt"
        )
        chapter = _parse_snbt(chapter_path.read_text(encoding="utf-8"))
        quest = next(
            quest for quest in chapter["quests"] if quest["id"] == "78E07ADD5BCD1F19"
        )

        self.assertEqual(
            quest["tasks"],
            [
                {
                    "id": "68A344A9166D7763",
                    "type": "advancement",
                    "advancement": "immersiveengineering:main/mb_cokeoven",
                    "criterion": "",
                }
            ],
        )

    def test_steel_yourself_accepts_the_common_steel_ingot_tag(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        chapter_path = (
            ROOT
            / "config"
            / "ftbquests"
            / "quests"
            / "chapters"
            / "45491A24F6B8C192.snbt"
        )
        chapter = _parse_snbt(chapter_path.read_text(encoding="utf-8"))
        quest = next(
            quest for quest in chapter["quests"] if quest["id"] == "27F6D0AB957BBB8C"
        )

        self.assertEqual(
            quest["tasks"],
            [
                {
                    "id": "374F658F034EF8C5",
                    "type": "item",
                    "item": {
                        "count": "1",
                        "id": "ftbfiltersystem:smart_filter",
                        "components": {
                            "ftbfiltersystem:filter": (
                                "ftbfiltersystem:item_tag(c:ingots/steel)"
                            )
                        },
                    },
                    "count": "12L",
                    "consume_items": False,
                }
            ],
        )

        language_path = (
            ROOT / "config" / "ftbquests" / "quests" / "lang" / "en_us.snbt"
        )
        language = _parse_snbt(language_path.read_text(encoding="utf-8"))
        self.assertEqual(
            language["task.374F658F034EF8C5.title"], "Any #c:ingots/steel"
        )

    def test_steel_tag_filter_runtime_is_installed_on_both_sides(self) -> None:
        metadata_path = ROOT / "mods" / "ftb-filter-system.pw.toml"
        self.assertTrue(metadata_path.is_file())
        metadata = tomllib.loads(metadata_path.read_text(encoding="utf-8"))

        self.assertEqual(metadata["name"], "FTB Filter System")
        self.assertEqual(
            metadata["filename"], "ftb-filter-system-neoforge-21.1.4.jar"
        )
        self.assertEqual(metadata["side"], "both")
        self.assertEqual(metadata["download"]["hash-format"], "sha1")
        self.assertEqual(
            metadata["download"]["hash"], "a48e54edeacc59aaba29a1b627799c052112ee0b"
        )
        self.assertEqual(
            metadata["update"]["curseforge"],
            {"file-id": 7429011, "project-id": 943925},
        )


class SignalReliquaryQuestContractTests(unittest.TestCase):
    RECOVERY_CHAPTER = "6C40000000000001"
    RECOVERY_QUEST = "6C40000000000002"
    RECOVERY_TASK = "6C40000000000003"
    RECOVERY_REWARD = "6C40000000000004"
    FAR_RELAY_QUEST = "6C40000000000101"
    FAR_RELAY_TASK = "6C40000000000102"
    FAR_RELAY_CHITS = "6C40000000000103"
    FAR_RELAY_XP = "6C40000000000104"
    STORY_CHAPTERS = (
        "6C40000000000001",
        "5B93C6934B230CFB",
        "4C01977EF77930A6",
        "770DAD173D9C234B",
        "45491A24F6B8C192",
        "52EF477C2D995F40",
        "5538973B3F8B1C72",
        "738C49C0D9F98BBC",
        "584A7E77CC881049",
        "257F2005E2D76B80",
        "37C54E49759AFDDF",
        "11CA083771CCB5BE",
        "2D7CB8E643BDC03B",
        "40BA93EAD765D4D0",
        "2FD06A1068D554E9",
        "582DF217557144DA",
        "4402713763771CFA",
        "7E9B015A32C6D980",
        "6671EBE257F914CB",
        "6C4AE5CE13773438",
        "245BADE04399406C",
        "3FF4AF7B0C73F058",
    )

    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("afterlight_quests")
        cls.catalog = cls.quests.build_catalog()
        cls.chapters_by_id = {chapter.id: chapter for chapter in cls.catalog}
        cls.quests_by_id = {
            quest.id: quest
            for chapter in cls.catalog
            for quest in chapter.quests
        }

    def test_reserved_signal_ids_do_not_collide(self) -> None:
        expected = {
            self.RECOVERY_CHAPTER,
            self.RECOVERY_QUEST,
            self.RECOVERY_TASK,
            self.RECOVERY_REWARD,
            self.FAR_RELAY_QUEST,
            self.FAR_RELAY_TASK,
            self.FAR_RELAY_CHITS,
            self.FAR_RELAY_XP,
        }
        actual = {chapter.id for chapter in self.catalog} | {
            identifier
            for chapter in self.catalog
            for quest in chapter.quests
            for identifier in (
                quest.id,
                *(task.id for task in quest.tasks),
                *(reward.id for reward in quest.rewards),
            )
        }
        self.assertTrue(expected.issubset(actual))
        self.assertEqual(
            len(actual),
            sum(
                1
                + sum(
                    1 + len(quest.tasks) + len(quest.rewards)
                    for quest in chapter.quests
                )
                for chapter in self.catalog
            ),
        )

    def test_explicit_ids_are_supported_by_every_compiler_spec(self) -> None:
        for spec in (
            self.quests.TaskSpec,
            self.quests.RewardSpec,
            self.quests.QuestSpec,
            self.quests.ChapterSpec,
        ):
            with self.subTest(spec=spec.__name__):
                self.assertIn("explicit_id", {field.name for field in fields(spec)})

    def test_recover_echo_is_an_exact_repeatable_command_contract(self) -> None:
        chapter = self.chapters_by_id[self.RECOVERY_CHAPTER]
        self.assertEqual(chapter.title, "ECHO Protocols")
        self.assertEqual(chapter.group.resolved_id, "4525BB3160467FCB")
        self.assertEqual(chapter.icon, "afterlight:echo")
        self.assertEqual(chapter.order_index, 0)
        self.assertEqual(len(chapter.quests), 1)

        quest = chapter.quests[0]
        self.assertEqual(quest.id, self.RECOVERY_QUEST)
        self.assertEqual(quest.title, "Recover ECHO")
        self.assertEqual(quest.subtitle, "Continuity requires a reachable interface.")
        self.assertEqual(quest.dependencies, ())
        self.assertTrue(quest.can_repeat)
        self.assertEqual(quest.repeat_cooldown, 5)
        self.assertEqual(len(quest.tasks), 1)
        self.assertEqual(
            (quest.tasks[0].id, quest.tasks[0].task_type, quest.tasks[0].data),
            (self.RECOVERY_TASK, "checkmark", {}),
        )
        self.assertEqual(len(quest.rewards), 1)
        self.assertEqual(
            (quest.rewards[0].id, quest.rewards[0].reward_type, quest.rewards[0].data),
            (
                self.RECOVERY_REWARD,
                "command",
                {"command": "echo recover", "silent": True},
            ),
        )

    def test_story_chapter_order_matches_ftb_canonical_save_form(self) -> None:
        from afterlight_quests.builder import _parse_snbt

        story = []
        chapter_root = ROOT / "config" / "ftbquests" / "quests" / "chapters"
        for path in sorted(chapter_root.glob("*.snbt")):
            chapter = _parse_snbt(path.read_text(encoding="utf-8"))
            if chapter.get("group") == "4525BB3160467FCB":
                story.append((int(chapter["order_index"]), chapter["id"]))

        self.assertEqual(
            sorted(story),
            list(enumerate(self.STORY_CHAPTERS)),
        )

    def test_gate_and_far_relay_use_physical_advancements(self) -> None:
        gate = self.quests_by_id["53B9BC5F498953D5"]
        self.assertEqual(len(gate.tasks), 1)
        self.assertEqual(gate.tasks[0].id, "645F98B8FAD4A1E5")
        self.assertEqual(gate.tasks[0].task_type, "advancement")
        self.assertEqual(
            gate.tasks[0].data,
            {"advancement": "afterlight:gate_opened", "criterion": ""},
        )

        far_relay = self.quests_by_id[self.FAR_RELAY_QUEST]
        self.assertEqual(far_relay.title, "The Far Relay")
        self.assertEqual(far_relay.dependencies, ("31C9557D2F51238F",))
        self.assertEqual(len(far_relay.tasks), 1)
        self.assertEqual(
            (far_relay.tasks[0].id, far_relay.tasks[0].task_type, far_relay.tasks[0].data),
            (
                self.FAR_RELAY_TASK,
                "advancement",
                {"advancement": "afterlight:far_relay_arrival", "criterion": ""},
            ),
        )
        self.assertEqual(
            tuple((reward.id, reward.reward_type, reward.data) for reward in far_relay.rewards),
            (
                (
                    self.FAR_RELAY_CHITS,
                    "item",
                    {
                        "item": {"count": 16, "id": "kubejs:requisition_chit"},
                        "count": 16,
                    },
                ),
                (self.FAR_RELAY_XP, "xp", {"xp": 500}),
            ),
        )
        ascendancy = self.quests_by_id["7E6A0AC031F7F484"]
        self.assertNotIn(self.FAR_RELAY_QUEST, ascendancy.dependency_ids)

    def test_echo_route_is_deterministic_complete_and_recovery_safe(self) -> None:
        route_module = importlib.import_module("afterlight_quests.echo_route")
        quest_root = ROOT / "config" / "ftbquests" / "quests"
        first = route_module.build_echo_route(quest_root)
        second = route_module.build_echo_route(quest_root)
        self.assertEqual(first, second)
        self.assertEqual(route_module.validate_echo_route(first, quest_root), [])
        self.assertEqual(first["schema"], 1)
        self.assertEqual(first["terminal_quest"], "31C9557D2F51238F")

        route_ids = [
            quest_id
            for segment in first["segments"]
            for quest_id in segment["quests"]
        ]
        self.assertEqual(len(route_ids), len(set(route_ids)))
        self.assertTrue(
            all(re.fullmatch(r"[0-9A-F]{16}", quest_id) for quest_id in route_ids)
        )
        self.assertNotIn(self.RECOVERY_QUEST, route_ids)
        self.assertIn("31C9557D2F51238F", route_ids)
        self.assertIn(self.FAR_RELAY_QUEST, route_ids)
        self.assertIn("1B523415541BD700", route_ids)
        self.assertIn("7ECCF0521DFCBED5", route_ids)
        self.assertIn("4DD9F3D1913499F3", route_ids)
        self.assertEqual(len(route_ids), 169)
        afterlight_segment = next(
            segment for segment in first["segments"] if segment["id"] == "afterlight"
        )
        self.assertEqual(
            afterlight_segment["quests"],
            [
                "51649E106286AA63",
                "1B523415541BD700",
                "7EE7B9B28787F8CC",
                "7E6A0AC031F7F484",
                "7ECCF0521DFCBED5",
                "4DD9F3D1913499F3",
            ],
        )
        self.assertEqual(first["segments"][0]["id"], "cold_boot")
        self.assertEqual(first["segments"][-1]["id"], "beyond_afterlight")
        self.assertEqual(first["segments"][0]["after"], [])
        for previous, current in zip(first["segments"], first["segments"][1:]):
            self.assertEqual(current["after"], [previous["id"]])

        rendered = route_module.render_echo_route(first)
        self.assertEqual(rendered, route_module.render_echo_route(second))
        self.assertEqual(
            (ROOT / "config" / "afterlight" / "echo_route.json").read_text(
                encoding="utf-8"
            ),
            rendered,
        )

    def test_pack_version_runtime_identity_is_exact(self) -> None:
        pack = (ROOT / "pack.toml").read_text(encoding="utf-8")
        version = re.search(r'^version = "([^"]+)"$', pack, re.MULTILINE)
        self.assertIsNotNone(version)
        payload = (ROOT / "config" / "afterlight" / "pack_version.txt").read_bytes()
        self.assertEqual(payload, f"{version.group(1)}\n".encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
