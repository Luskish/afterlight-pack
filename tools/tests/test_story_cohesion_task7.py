from __future__ import annotations

import copy
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


EXPECTED_REVISED_IDS = (
    "45021BE218C5DFBD",
    "718424A08FE06E9A",
    "79145D1842E317AA",
    "43860D6CFEF31BB9",
    "0CEB581902A9D016",
    "4B0048F311BDF3D9",
    "4D41BE537DD35854",
    "0D1D4842B326D878",
    "3F12A84AF92F28B8",
    "27AEE834BFD148F2",
    "6A0FBE1789BEFD37",
    "10EEBFB30F143EC4",
    "19D5F09EADF78A32",
    "557DC7BACD462EFE",
    "71B2919DF12C6845",
    "72446D404001B38D",
    "5468299A2A931991",
    "462B11BD8C58BF6F",
    "51649E106286AA63",
    "480D3EAD1B1EA51B",
)

EXPECTED_STORY_LINKS = (
    ("4C01977EF77930A6", "0576C37E9FA4116C", "links/story/alloy-of-beginnings/to/field-manual-kinetics", "6DF395B943C61424", "686943DC0749D6E0", 2.0, 3.0, "legacy"),
    ("770DAD173D9C234B", "718424A08FE06E9A", "links/story/the-scarlands/to/expedition-log", "0D5D96C7E6A8C06E", "5DBA48B322065E95", 0.0, -2.0, "legacy"),
    ("770DAD173D9C234B", "5413406A90BD2714", "links/story/through-the-scarred-door/to/anomalous-readings", "47BC70AE3B641049", "6546BA910285D6EB", 6.0, -2.0, "legacy"),
    ("45491A24F6B8C192", "20169EC099FABBA0", "links/story/the-engineers-bench/to/field-manual-heavy-industry", "592BE773528C7941", "3E77A16CB0C0AD11", 2.0, -3.0, "legacy"),
    ("45491A24F6B8C192", "1AC07872BABAC949", "links/story/first-current/to/field-manual-matter-systems", "49620AF9257B2051", "6B09A1A11CD08E68", 6.0, -3.0, "legacy"),
    ("52EF477C2D995F40", "43860D6CFEF31BB9", "links/story/the-engine-room/to/field-manual-matter-systems", "5982ACD18755589A", "6B09A1A11CD08E68", 0.0, -2.0, "legacy"),
    ("52EF477C2D995F40", "5A407B47132C07C6", "links/story/the-room-hums/to/deep-vault", "5DE7E217677CA8EC", "16783315E0833B1D", 8.0, -2.0, "legacy"),
    ("5538973B3F8B1C72", "0CEB581902A9D016", "links/story/certus-resonance/to/field-manual-storage-lattice", "5E7D4B6F8E276102", "70380821D8D0339D", 0.0, -2.0, "managed"),
    ("738C49C0D9F98BBC", "4B0048F311BDF3D9", "links/story/brass-standard/to/field-manual-kinetics", "629176DBDA9F156A", "686943DC0749D6E0", 0.0, -2.0, "managed"),
    ("738C49C0D9F98BBC", "7199A16DB5D83154", "links/story/256-track-capstone/to/certification-kinetics-i", "69EE43798DB7CA99", "1641CC316D20D678", 14.0, -2.0, "managed"),
    ("584A7E77CC881049", "4D41BE537DD35854", "links/story/air-compressor/to/field-manual-pressure", "61802D4BBFDF55DF", "084209B68927F9FC", 0.0, -2.0, "managed"),
    ("584A7E77CC881049", "53C65BE4DB17F1B9", "links/story/logistics-drone/to/logistics-i", "52AA7825E2F97C4E", "25E5B276B9FA47ED", 12.0, -2.0, "managed"),
    ("257F2005E2D76B80", "0D1D4842B326D878", "links/story/energizing-orb/to/field-manual-power-networks", "2316FCA654FE01E8", "5334545A948815F6", 0.0, -2.0, "managed"),
    ("257F2005E2D76B80", "6B876A865DE7A77A", "links/story/10m-fe-reserve/to/power-i", "4BEDC9C2880C08FC", "64659C3AE503FE5D", 14.0, -2.0, "managed"),
    ("37C54E49759AFDDF", "3F12A84AF92F28B8", "links/story/oxygen-separation/to/field-manual-matter-systems", "34F3D13C79A4FB05", "6B09A1A11CD08E68", 0.0, -2.0, "managed"),
    ("37C54E49759AFDDF", "45A86A6AA4AD7824", "links/story/reactor-warning/to/field-manual-nuclear-safety", "35725A5429FF1BA4", "4EEAB6F41DB426E7", 14.0, -2.0, "managed"),
    ("37C54E49759AFDDF", "3C72E0ADC8E785D0", "links/story/1024-ingot-quota/to/ore-loop-i", "664CCB012CC47823", "1AE92DE8CA81283E", 12.0, -3.0, "managed"),
    ("11CA083771CCB5BE", "4F8F8B4545572260", "links/story/drone-delivery/to/logistics-i", "128E1BA6D3EE37C3", "25E5B276B9FA47ED", 4.0, -3.0, "managed"),
    ("11CA083771CCB5BE", "27AEE834BFD148F2", "links/story/ae-stockkeeping/to/autocrafting-i", "364E22ABAC317B0F", "3011977E372A3BC6", 0.0, -2.0, "managed"),
    ("11CA083771CCB5BE", "742BEB99DFA479FD", "links/story/create-feed-line/to/cross-mod-i", "65486B7C21041B56", "02BA27AF63721ACA", 2.0, -2.0, "managed"),
    ("2D7CB8E643BDC03B", "6A0FBE1789BEFD37", "links/story/machine-core/to/field-manual-frontier-machines", "5D99BED063D4488E", "6CC0CCE16F9FB5BE", 0.0, -2.0, "managed"),
    ("40BA93EAD765D4D0", "10EEBFB30F143EC4", "links/story/ancient-factory/to/expedition-log", "06070155FD5469A5", "5DBA48B322065E95", 0.0, -2.0, "managed"),
    ("2FD06A1068D554E9", "19D5F09EADF78A32", "links/story/fission-assembly/to/field-manual-nuclear-safety", "7F357CA7C9FBB077", "4EEAB6F41DB426E7", 0.0, -2.0, "managed"),
    ("582DF217557144DA", "557DC7BACD462EFE", "links/story/flight-harness/to/field-manual-frontier-machines", "7861131F24E674B1", "6CC0CCE16F9FB5BE", 0.0, -2.0, "managed"),
    ("582DF217557144DA", "23C08FB037E35BDE", "links/story/starlight/to/expedition-log", "3C3AE361791A7594", "5DBA48B322065E95", 10.0, -2.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/certification-kinetics-i", "3AC941407F3E02BF", "1641CC316D20D678", 6.0, -2.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/logistics-i", "3BCDB42DD3DDE3D9", "25E5B276B9FA47ED", 8.0, -2.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/ore-loop-i", "28ED48250EEEB0B0", "1AE92DE8CA81283E", 10.0, -2.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/autocrafting-i", "1F67BD0B535DE519", "3011977E372A3BC6", 6.0, -4.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/cross-mod-i", "7E8B551630D5E4B4", "02BA27AF63721ACA", 8.0, -4.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/power-i", "02BB08E9E27536BE", "64659C3AE503FE5D", 10.0, -4.0, "managed"),
    ("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/infrastructure-ii", "15E20CF17890BA99", "7CB2D7D361BEA4C4", 8.0, -6.0, "managed"),
    ("7E9B015A32C6D980", "0055C66103106D86", "links/story/kinetic-frame/to/field-manual-kinetics", "1DFDF1063452C6CE", "686943DC0749D6E0", 0.0, -4.0, "managed"),
    ("7E9B015A32C6D980", "52FE1624DCCE878F", "links/story/industrial-anchor/to/field-manual-heavy-industry", "2801038AFDC85960", "3E77A16CB0C0AD11", 0.0, -3.0, "managed"),
    ("7E9B015A32C6D980", "50775CE87FAA4EB7", "links/story/isotopic-core/to/field-manual-nuclear-safety", "6EEE18DA9492CAD2", "4EEAB6F41DB426E7", 2.0, 0.0, "managed"),
    ("7E9B015A32C6D980", "7F064705A3CAB2E6", "links/story/lattice-matrix/to/field-manual-storage-lattice", "2036C916B89B3B5A", "70380821D8D0339D", 0.0, 3.0, "managed"),
    ("7E9B015A32C6D980", "39C1F24EABBB34A3", "links/story/undercurrent-stabilizer/to/resonance-proof", "427385B56F487768", "6363BCE8A71FA766", 0.0, 4.0, "managed"),
    ("6C4AE5CE13773438", "36D0902A2921C44E", "links/story/monument-footprint/to/field-manual-kinetics", "24D5FA8885DE541F", "686943DC0749D6E0", 0.0, -3.0, "managed"),
    ("6C4AE5CE13773438", "66AD5C821947DF8E", "links/story/separate-grid/to/field-manual-power-networks", "31E79CC52B5D1639", "5334545A948815F6", 0.0, 3.0, "managed"),
)

EXPECTED_MANUAL_RETURNS = (
    ("4690C88367D47FF3", "links/manuals/kinetics/return/alloy-of-beginnings", "39C96EB4C75EED18", "0576C37E9FA4116C", 0.0, -2.0),
    ("150C6F996983394C", "links/manuals/heavy-industry/return/the-engineers-bench", "386444141B66F453", "20169EC099FABBA0", 0.0, -2.0),
    ("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/first-current", "6D41B7269E44A298", "1AC07872BABAC949", 0.0, -2.0),
    ("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/the-engine-room", "71C9341BE0B9B992", "43860D6CFEF31BB9", 2.0, -2.0),
    ("01749E1554DFF98B", "links/manuals/storage-lattice/return/certus-resonance", "54328C23013544B5", "0CEB581902A9D016", 0.0, -2.0),
    ("4690C88367D47FF3", "links/manuals/kinetics/return/brass-standard", "2468522409E683FD", "4B0048F311BDF3D9", 2.0, -2.0),
    ("0A510C4BD2A3818B", "links/manuals/pressure/return/air-compressor", "68E005D35965E4F9", "4D41BE537DD35854", 0.0, -2.0),
    ("67F13F819570ED52", "links/manuals/power-networks/return/energizing-orb", "277025CE751ECC8D", "0D1D4842B326D878", 0.0, -2.0),
    ("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/oxygen-separation", "3C25350A9C3F2146", "3F12A84AF92F28B8", 4.0, -2.0),
    ("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/reactor-warning", "5C9799B0DE4547F7", "45A86A6AA4AD7824", 0.0, -2.0),
    ("67C126F7B1338CB1", "links/manuals/frontier-machines/return/machine-core", "44EA9C1D7956D65F", "6A0FBE1789BEFD37", 0.0, -2.0),
    ("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/fission-assembly", "0AA077A5B734EE35", "19D5F09EADF78A32", 2.0, -2.0),
    ("67C126F7B1338CB1", "links/manuals/frontier-machines/return/flight-harness", "0BA82C65D67C3755", "557DC7BACD462EFE", 2.0, -2.0),
    ("4690C88367D47FF3", "links/manuals/kinetics/return/kinetic-frame", "7981C54795DE1D80", "0055C66103106D86", 4.0, -2.0),
    ("150C6F996983394C", "links/manuals/heavy-industry/return/industrial-anchor", "2837E3B154B9CF56", "52FE1624DCCE878F", 2.0, -2.0),
    ("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/isotopic-core", "1768F75584D09447", "50775CE87FAA4EB7", 4.0, -2.0),
    ("01749E1554DFF98B", "links/manuals/storage-lattice/return/lattice-matrix", "6FDA5AEE392F30BF", "7F064705A3CAB2E6", 2.0, -2.0),
    ("4690C88367D47FF3", "links/manuals/kinetics/return/monument-footprint", "2C837083D839A135", "36D0902A2921C44E", 6.0, -2.0),
    ("67F13F819570ED52", "links/manuals/power-networks/return/separate-grid", "663E47307E11A38C", "66AD5C821947DF8E", 2.0, -2.0),
)


class StoryCohesionTask7Tests(unittest.TestCase):
    AUDIT_KEYS = {"schema_version", "source_commit", "story_group_id", "counts", "quests"}
    RECORD_KEYS = {
        "chapter_id",
        "chapter_order",
        "chapter_title",
        "quest_id",
        "quest_order",
        "title",
        "dependencies",
        "current_subtitle",
        "current_description",
        "prose_status",
        "linked",
        "outbound_link_slugs",
        "replacement_subtitle",
        "replacement_description",
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls.quests = importlib.import_module("afterlight_quests")
        cls.story = importlib.import_module("afterlight_quests.story_cohesion")
        cls.audit = cls.quests.load_story_audit()
        cls.baseline = json.loads(
            (ROOT / "tools" / "fixtures" / "quests" / "story-cohesion-baseline.json").read_text(encoding="utf-8")
        )["corpus"]

    def test_story_audit_schema_is_exact_and_canonical(self) -> None:
        path = ROOT / self.quests.STORY_AUDIT_PATH
        payload = path.read_text(encoding="utf-8")
        self.assertEqual(set(self.audit), self.AUDIT_KEYS)
        self.assertEqual(
            {key for record in self.audit["quests"] for key in record},
            self.RECORD_KEYS,
        )
        self.assertEqual(payload, json.dumps(self.audit, indent=2, sort_keys=True) + "\n")
        mutated = copy.deepcopy(self.audit)
        mutated["quests"][0]["unknown"] = True
        with tempfile.TemporaryDirectory() as temporary:
            fixture = Path(temporary) / "story-audit.json"
            fixture.write_text(json.dumps(mutated, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid fields"):
                self.quests.load_story_audit(fixture)

    def test_exact_revised_set_and_frozen_inventory(self) -> None:
        self.assertEqual(
            self.audit["counts"],
            {
                "story_chapters": 22,
                "story_quests": 170,
                "retained": 150,
                "revised": 20,
                "linked": 33,
                "outbound_links": 39,
            },
        )
        self.assertEqual(
            tuple(record["quest_id"] for record in self.audit["quests"] if record["prose_status"] == "revised"),
            EXPECTED_REVISED_IDS,
        )
        self.assertEqual(sum(record["linked"] and record["prose_status"] == "revised" for record in self.audit["quests"]), 12)
        story_chapters = sorted(
            (
                chapter
                for chapter in self.baseline["chapters"].values()
                if chapter["group"] == "4525BB3160467FCB"
            ),
            key=lambda chapter: int(chapter["order_index"]),
        )
        frozen_ids = tuple(quest["id"] for chapter in story_chapters for quest in chapter["quests"])
        self.assertEqual(tuple(record["quest_id"] for record in self.audit["quests"]), frozen_ids)

    def test_story_and_return_link_maps_are_exact_and_resolve(self) -> None:
        story_routes = tuple(route.as_tuple() for route in self.quests.STORY_LINK_ROUTES)
        return_routes = tuple(route.as_tuple() for route in self.quests.MANUAL_RETURN_ROUTES)
        self.assertEqual(story_routes, EXPECTED_STORY_LINKS)
        self.assertEqual(return_routes, EXPECTED_MANUAL_RETURNS)
        all_slugs = [route[2] for route in story_routes] + [route[1] for route in return_routes]
        all_ids = [route[3] for route in story_routes] + [route[2] for route in return_routes]
        self.assertEqual(len(all_slugs), len(set(all_slugs)))
        self.assertEqual(len(all_ids), len(set(all_ids)))
        self.assertTrue(all(re.fullmatch(r"[0-7][0-9A-F]{15}", identifier) for identifier in all_ids))
        self.assertEqual(
            [self.quests.stable_id("quest_link", slug) for slug in all_slugs],
            all_ids,
        )
        audit_ids = {record["quest_id"] for record in self.audit["quests"]}
        frozen_ids = {
            quest["id"]
            for chapter in self.baseline["chapters"].values()
            for quest in chapter["quests"]
        }
        catalog = self.quests.build_catalog()
        catalog_ids = {quest.id for chapter in catalog for quest in chapter.quests}
        quest_owners = {
            quest["id"]: chapter["id"]
            for chapter in self.baseline["chapters"].values()
            for quest in chapter["quests"]
        }
        quest_owners.update(
            {
                quest.id: chapter.id
                for chapter in catalog
                for quest in chapter.quests
            }
        )
        targets = {route[4] for route in story_routes} | {route[3] for route in return_routes}
        self.assertFalse(targets - audit_ids - frozen_ids - catalog_ids)
        for route in self.quests.STORY_LINK_ROUTES:
            self.assertEqual(quest_owners[route.source_quest_id], route.owner_chapter_id)
            self.assertIn(route.target_quest_id, quest_owners)
        for route in self.quests.MANUAL_RETURN_ROUTES:
            self.assertEqual(quest_owners[route.target_quest_id], next(
                story_route.owner_chapter_id
                for story_route in self.quests.STORY_LINK_ROUTES
                if story_route.source_quest_id == route.target_quest_id
            ))

    def test_audit_link_assignments_match_exact_route_sources(self) -> None:
        expected = defaultdict(list)
        for _chapter_id, source_id, slug, _link_id, _target_id, _x, _y, _route in EXPECTED_STORY_LINKS:
            expected[source_id].append(slug)
        for record in self.audit["quests"]:
            self.assertEqual(record["linked"], bool(record["outbound_link_slugs"]))
            self.assertEqual(record["outbound_link_slugs"], expected[record["quest_id"]])

    def test_story_audit_matches_frozen_and_current_corpus(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        baseline_chapters = {
            chapter["id"]: chapter
            for chapter in self.baseline["chapters"].values()
        }
        baseline_language = self.baseline["language"]["en_us"]
        current_chapters = {
            chapter["id"]: chapter
            for path in sorted((ROOT / "config" / "ftbquests" / "quests" / "chapters").glob("*.snbt"))
            for chapter in [builder._parse_snbt(path.read_text(encoding="utf-8"))]
        }
        current_language = builder._parse_snbt(
            (ROOT / "config" / "ftbquests" / "quests" / "lang" / "en_us.snbt").read_text(encoding="utf-8")
        )
        for record in self.audit["quests"]:
            with self.subTest(quest=record["quest_id"]):
                baseline_chapter = baseline_chapters[record["chapter_id"]]
                current_chapter = current_chapters[record["chapter_id"]]
                baseline_index = next(
                    index
                    for index, quest in enumerate(baseline_chapter["quests"])
                    if quest["id"] == record["quest_id"]
                )
                current_index = next(
                    index
                    for index, quest in enumerate(current_chapter["quests"])
                    if quest["id"] == record["quest_id"]
                )
                baseline_quest = baseline_chapter["quests"][baseline_index]
                current_quest = current_chapter["quests"][current_index]
                title_key = f"quest.{record['quest_id']}.title"
                subtitle_key = f"quest.{record['quest_id']}.quest_subtitle"
                description_key = f"quest.{record['quest_id']}.quest_desc"
                self.assertEqual(int(baseline_chapter["order_index"]), record["chapter_order"])
                self.assertEqual(int(current_chapter["order_index"]), record["chapter_order"])
                self.assertEqual(baseline_index, record["quest_order"])
                self.assertEqual(current_index, record["quest_order"])
                self.assertEqual(baseline_language[f"chapter.{record['chapter_id']}.title"], record["chapter_title"])
                self.assertEqual(current_language[f"chapter.{record['chapter_id']}.title"], record["chapter_title"])
                self.assertEqual(baseline_language[title_key], record["title"])
                self.assertEqual(current_language[title_key], record["title"])
                self.assertEqual(baseline_quest.get("dependencies", []), record["dependencies"])
                self.assertEqual(current_quest.get("dependencies", []), record["dependencies"])
                self.assertEqual(baseline_language.get(subtitle_key, ""), record["current_subtitle"])
                self.assertEqual(baseline_language.get(description_key, []), record["current_description"])
                expected_subtitle = (
                    record["replacement_subtitle"]
                    if record["prose_status"] == "revised"
                    else record["current_subtitle"]
                )
                expected_description = (
                    record["replacement_description"]
                    if record["prose_status"] == "revised"
                    else record["current_description"]
                )
                self.assertEqual(current_language.get(subtitle_key, ""), expected_subtitle)
                self.assertEqual(current_language.get(description_key, []), expected_description)

    def test_compiler_places_exact_story_links_and_manual_returns(self) -> None:
        catalog = self.quests.build_catalog()
        chapters = {chapter.id: chapter for chapter in catalog}
        expected_managed = defaultdict(list)
        for route in self.quests.STORY_LINK_ROUTES:
            if route.route == "managed":
                expected_managed[route.owner_chapter_id].append(route.link)
        for chapter_id, links in expected_managed.items():
            self.assertEqual(chapters[chapter_id].quest_links, tuple(links))

        expected_returns = defaultdict(list)
        for route in self.quests.MANUAL_RETURN_ROUTES:
            expected_returns[route.owner_chapter_id].append(route.link)
        for chapter_id, links in expected_returns.items():
            self.assertEqual(chapters[chapter_id].quest_links, tuple(links))

        overlays = importlib.import_module("afterlight_quests.legacy_quest_overlays")
        expected_legacy = defaultdict(list)
        for route in self.quests.STORY_LINK_ROUTES:
            if route.route == "legacy":
                expected_legacy[route.owner_chapter_id].append(route.link)
        self.assertEqual(
            {
                overlay.chapter_id: overlay.quest_links
                for overlay in overlays.LEGACY_QUEST_LINK_OVERLAYS
            },
            {
                chapter_id: tuple(links)
                for chapter_id, links in expected_legacy.items()
            },
        )

    def test_every_manual_route_has_one_exact_return_and_other_routes_do_not(self) -> None:
        catalog = self.quests.build_catalog()
        quest_owner = {
            quest.id: chapter.id
            for chapter in catalog
            for quest in chapter.quests
        }
        manual_chapters = {
            chapter.id
            for chapter in catalog
            if chapter.slug.startswith("manuals/")
        }
        returns = {
            (route.owner_chapter_id, route.target_quest_id)
            for route in self.quests.MANUAL_RETURN_ROUTES
        }
        manual_routes = 0
        established_routes = 0
        for route in self.quests.STORY_LINK_ROUTES:
            owner = quest_owner.get(route.target_quest_id)
            if owner in manual_chapters:
                manual_routes += 1
                self.assertIn((owner, route.source_quest_id), returns)
            else:
                established_routes += 1
                self.assertFalse(
                    any(
                        return_route.target_quest_id == route.source_quest_id
                        for return_route in self.quests.MANUAL_RETURN_ROUTES
                    )
                )
        self.assertEqual((manual_routes, established_routes), (19, 20))

    def test_catalog_preserves_ids_completion_shapes_and_dependencies(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        catalog = self.quests.build_catalog()
        story_records = {record["quest_id"]: record for record in self.audit["quests"]}
        baseline_quests = {
            quest["id"]: quest
            for chapter in self.baseline["chapters"].values()
            for quest in chapter["quests"]
        }
        managed_story = [
            chapter
            for chapter in catalog
            if chapter.group.resolved_id == "4525BB3160467FCB"
        ]
        commodity_task_ids = {
            declaration.task_id
            for declaration in self.quests.load_common_commodity_declarations().declarations
        }
        self.assertEqual(len(managed_story), 17)
        for chapter in managed_story:
            rendered = builder._parse_snbt(self.quests.render_chapter(chapter))
            rendered_quests = {quest["id"]: quest for quest in rendered["quests"]}
            for quest in chapter.quests:
                with self.subTest(quest=quest.id):
                    record = story_records[quest.id]
                    baseline = baseline_quests[quest.id]
                    rendered_quest = rendered_quests[quest.id]
                    expected_subtitle = record["replacement_subtitle"] if record["prose_status"] == "revised" else record["current_subtitle"]
                    expected_description = record["replacement_description"] if record["prose_status"] == "revised" else record["current_description"]
                    self.assertEqual(quest.title, record["title"])
                    self.assertEqual(quest.subtitle, expected_subtitle)
                    self.assertEqual(quest.description, tuple(expected_description))
                    self.assertEqual(quest.dependency_ids, tuple(record["dependencies"]))
                    self.assertEqual(
                        tuple((task.id, task.task_type) for task in quest.tasks),
                        tuple((task["id"], task["type"]) for task in baseline["tasks"]),
                    )
                    self.assertEqual(
                        tuple((reward.id, reward.reward_type) for reward in quest.rewards),
                        tuple((reward["id"], reward["type"]) for reward in baseline["rewards"]),
                    )
                    self.assertEqual(rendered_quest["rewards"], baseline["rewards"])
                    self.assertEqual(len(rendered_quest["tasks"]), len(baseline["tasks"]))
                    for rendered_task, baseline_task in zip(
                        rendered_quest["tasks"],
                        baseline["tasks"],
                        strict=True,
                    ):
                        self.assertEqual(rendered_task["id"], baseline_task["id"])
                        if rendered_task["id"] in commodity_task_ids:
                            rendered_task = copy.deepcopy(rendered_task)
                            rendered_task["item"] = baseline_task["item"]
                        self.assertEqual(rendered_task, baseline_task)

    def test_links_are_navigation_only_and_do_not_add_mandatory_edges(self) -> None:
        catalog = self.quests.build_catalog()
        audit_dependencies = {
            record["quest_id"]: tuple(record["dependencies"])
            for record in self.audit["quests"]
        }
        manual_ids = {
            quest.id
            for chapter in catalog
            if chapter.group.resolved_id == "4A20F33642175B95" and chapter.slug.startswith("manuals/")
            for quest in chapter.quests
        }
        for chapter in catalog:
            for quest in chapter.quests:
                if quest.id in audit_dependencies:
                    self.assertEqual(quest.dependency_ids, audit_dependencies[quest.id])
                    self.assertFalse(set(quest.dependency_ids) & manual_ids)
                if chapter.slug.startswith("manuals/"):
                    self.assertFalse(set(quest.dependency_ids) & set(audit_dependencies))
        for chapter in catalog:
            for link in chapter.quest_links:
                self.assertFalse(hasattr(link, "dependencies"))

    def test_routes_have_no_collisions_or_covered_quest_nodes(self) -> None:
        catalog = self.quests.build_catalog()
        owner_coordinates = {
            chapter["id"]: {
                (float(quest["x"].removesuffix("d")), float(quest["y"].removesuffix("d")))
                for quest in chapter["quests"]
            }
            for chapter in self.baseline["chapters"].values()
        }
        owner_coordinates.update(
            {
                chapter.id: {(quest.x, quest.y) for quest in chapter.quests}
                for chapter in catalog
            }
        )
        frozen_identities = set()

        def collect_identities(value: object) -> None:
            if isinstance(value, dict):
                for nested in value.values():
                    collect_identities(nested)
            elif isinstance(value, list):
                for nested in value:
                    collect_identities(nested)
            elif isinstance(value, str) and re.fullmatch(r"[0-7][0-9A-F]{15}", value):
                frozen_identities.add(value)

        collect_identities(self.baseline)
        link_ids = {
            route.expected_id
            for route in (*self.quests.STORY_LINK_ROUTES, *self.quests.MANUAL_RETURN_ROUTES)
        }
        self.assertFalse(link_ids & frozen_identities)
        triples = set()
        for route in (*self.quests.STORY_LINK_ROUTES, *self.quests.MANUAL_RETURN_ROUTES):
            coordinate = (0.0 if route.x == 0.0 else route.x, 0.0 if route.y == 0.0 else route.y)
            self.assertIn(route.owner_chapter_id, owner_coordinates)
            self.assertNotIn(coordinate, owner_coordinates[route.owner_chapter_id])
            triple = (route.owner_chapter_id, route.target_quest_id, *coordinate)
            self.assertNotIn(triple, triples)
            triples.add(triple)
        fan = tuple((route.x, route.y) for route in self.quests.STORY_LINK_ROUTES if route.source_quest_id == "2D6ACF1CCBC7B4F2")
        self.assertEqual(fan, ((6.0, -2.0), (8.0, -2.0), (10.0, -2.0), (6.0, -4.0), (8.0, -4.0), (10.0, -4.0), (8.0, -6.0)))

    def test_story_cohesion_application_is_idempotent(self) -> None:
        catalog = self.quests.build_catalog()
        reapplied = self.quests.apply_story_cohesion(copy.deepcopy(catalog))
        self.assertEqual(reapplied, catalog)
        first = tuple(self.quests.render_chapter(chapter) for chapter in catalog)
        second_catalog = self.quests.build_catalog()
        second = tuple(self.quests.render_chapter(chapter) for chapter in second_catalog)
        self.assertEqual(first, second)

    def test_task7_generation_is_idempotent_in_independent_roots(self) -> None:
        builder = importlib.import_module("afterlight_quests.builder")
        temporary_parent = Path(tempfile.gettempdir()).resolve()

        def generate_twice() -> tuple[dict[str, bytes], dict[str, bytes]]:
            with tempfile.TemporaryDirectory(dir=temporary_parent) as temporary:
                root = Path(temporary)
                shutil.copytree(ROOT / "config", root / "config")
                shutil.copytree(ROOT / "mods", root / "mods")
                shutil.copytree(
                    ROOT / "kubejs" / "startup_scripts",
                    root / "kubejs" / "startup_scripts",
                )
                audit_source = ROOT / "kubejs" / "server_scripts" / "afterlight" / "generated_quest_item_audit.js"
                audit_target = root / audit_source.relative_to(ROOT)
                audit_target.parent.mkdir(parents=True)
                shutil.copy2(audit_source, audit_target)
                quest_root = root / "config" / "ftbquests" / "quests"
                catalog = self.quests.build_catalog()
                managed_chapter_ids = {chapter.id for chapter in catalog}
                legacy_quest_ids = tuple(
                    quest["id"]
                    for path in sorted((quest_root / "chapters").glob("*.snbt"))
                    if path.stem not in managed_chapter_ids
                    for quest in builder._parse_snbt(
                        path.read_text(encoding="utf-8")
                    )["quests"]
                )

                def generate() -> dict[str, bytes]:
                    self.quests.write_catalog(
                        catalog,
                        quest_root,
                        legacy_quest_ids=legacy_quest_ids,
                    )
                    self.quests.write_legacy_quest_overlays(
                        quest_root,
                        catalog=catalog,
                        known_quest_ids=legacy_quest_ids,
                    )
                    return {
                        path.relative_to(root).as_posix(): path.read_bytes()
                        for path in sorted(root.rglob("*"))
                        if path.is_file()
                    }

                with tempfile.TemporaryDirectory(dir=temporary_parent) as migration_state:
                    with mock.patch.dict(
                        os.environ,
                        {"AFTERLIGHT_QUEST_MIGRATION_STATE_ROOT": migration_state},
                    ):
                        return generate(), generate()

        first_root_first_pass, first_root_second_pass = generate_twice()
        second_root_first_pass, second_root_second_pass = generate_twice()
        self.assertEqual(first_root_first_pass, first_root_second_pass)
        self.assertEqual(second_root_first_pass, second_root_second_pass)
        self.assertEqual(first_root_first_pass, second_root_first_pass)

    def test_legacy_localization_map_matches_revised_audit_records(self) -> None:
        overlays = importlib.import_module("afterlight_quests.legacy_quest_overlays")
        legacy_owner_ids = {
            route.owner_chapter_id
            for route in self.quests.STORY_LINK_ROUTES
            if route.route == "legacy"
        }
        expected = {
            "chapter_group.4A20F33642175B95.title": "Field Manuals & Certifications"
        }
        for record in self.audit["quests"]:
            if record["chapter_id"] not in legacy_owner_ids or record["prose_status"] != "revised":
                continue
            expected[f"quest.{record['quest_id']}.quest_subtitle"] = record["replacement_subtitle"]
            expected[f"quest.{record['quest_id']}.quest_desc"] = tuple(record["replacement_description"])
        self.assertEqual(
            {overlay.key: overlay.value for overlay in overlays.LEGACY_LOCALIZATION_OVERLAYS.overlays},
            expected,
        )

    def test_task7_prose_and_sources_are_u2014_and_identity_clean(self) -> None:
        values = []
        for record in self.audit["quests"]:
            if record["replacement_subtitle"] is not None:
                values.append(record["replacement_subtitle"])
                values.extend(record["replacement_description"])
        text = "\n".join(values)
        self.assertNotIn("\u2014", text)
        self.assertIsNone(re.search(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", text))
        self.assertIsNone(re.search(r"(?i)access[_ -]?token|private key|task_progress|player_uuid", text))
        for path in (
            ROOT / "tools" / "afterlight_quests" / "story_cohesion.py",
            ROOT / "tools" / "fixtures" / "quests" / "story-audit.json",
            ROOT / "tools" / "tests" / "test_story_cohesion_task7.py",
        ):
            self.assertNotIn("\u2014", path.read_text(encoding="utf-8"), path)


if __name__ == "__main__":
    unittest.main()
