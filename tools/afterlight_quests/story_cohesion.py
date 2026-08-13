from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from .builder import ChapterSpec, QuestLinkSpec, QuestSpec


STORY_GROUP_ID = "4525BB3160467FCB"
MANUAL_GROUP_ID = "4A20F33642175B95"
STORY_AUDIT_PATH = Path("tools/fixtures/quests/story-audit.json")
STORY_AUDIT_SHA256 = "a6d3b144dc76c144a5044fb6c8c353757395c1717dcbf36f670f3d71c2e3142b"
STORY_AUDIT_SOURCE_COMMIT = "7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25"
_FTB_ID = re.compile(r"^[0-7][0-9A-F]{15}$")
_AUDIT_KEYS = {"schema_version", "source_commit", "story_group_id", "counts", "quests"}
_RECORD_KEYS = {
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
_EXPECTED_COUNTS = {
    "story_chapters": 22,
    "story_quests": 170,
    "retained": 150,
    "revised": 20,
    "linked": 33,
    "outbound_links": 39,
}


@dataclass(frozen=True)
class StoryLinkRoute:
    owner_chapter_id: str
    source_quest_id: str
    slug: str
    expected_id: str
    target_quest_id: str
    x: float
    y: float
    route: str

    @property
    def link(self) -> QuestLinkSpec:
        link = QuestLinkSpec(self.slug, self.target_quest_id, self.x, self.y)
        if link.id != self.expected_id:
            raise ValueError(
                f"story link ID mismatch for {self.slug}: "
                f"expected {self.expected_id}, found {link.id}"
            )
        return link

    def as_tuple(self) -> tuple[str, str, str, str, str, float, float, str]:
        return (
            self.owner_chapter_id,
            self.source_quest_id,
            self.slug,
            self.expected_id,
            self.target_quest_id,
            self.x,
            self.y,
            self.route,
        )


@dataclass(frozen=True)
class ManualReturnRoute:
    owner_chapter_id: str
    slug: str
    expected_id: str
    target_quest_id: str
    x: float
    y: float

    @property
    def link(self) -> QuestLinkSpec:
        link = QuestLinkSpec(self.slug, self.target_quest_id, self.x, self.y)
        if link.id != self.expected_id:
            raise ValueError(
                f"manual return ID mismatch for {self.slug}: "
                f"expected {self.expected_id}, found {link.id}"
            )
        return link

    def as_tuple(self) -> tuple[str, str, str, str, float, float]:
        return (
            self.owner_chapter_id,
            self.slug,
            self.expected_id,
            self.target_quest_id,
            self.x,
            self.y,
        )


STORY_LINK_ROUTES = (
    StoryLinkRoute("4C01977EF77930A6", "0576C37E9FA4116C", "links/story/alloy-of-beginnings/to/field-manual-kinetics", "6DF395B943C61424", "686943DC0749D6E0", 2.0, 3.0, "legacy"),
    StoryLinkRoute("770DAD173D9C234B", "718424A08FE06E9A", "links/story/the-scarlands/to/expedition-log", "0D5D96C7E6A8C06E", "5DBA48B322065E95", 0.0, -2.0, "legacy"),
    StoryLinkRoute("770DAD173D9C234B", "5413406A90BD2714", "links/story/through-the-scarred-door/to/anomalous-readings", "47BC70AE3B641049", "6546BA910285D6EB", 6.0, -2.0, "legacy"),
    StoryLinkRoute("45491A24F6B8C192", "20169EC099FABBA0", "links/story/the-engineers-bench/to/field-manual-heavy-industry", "592BE773528C7941", "3E77A16CB0C0AD11", 2.0, -3.0, "legacy"),
    StoryLinkRoute("45491A24F6B8C192", "1AC07872BABAC949", "links/story/first-current/to/field-manual-matter-systems", "49620AF9257B2051", "6B09A1A11CD08E68", 6.0, -3.0, "legacy"),
    StoryLinkRoute("52EF477C2D995F40", "43860D6CFEF31BB9", "links/story/the-engine-room/to/field-manual-matter-systems", "5982ACD18755589A", "6B09A1A11CD08E68", 0.0, -2.0, "legacy"),
    StoryLinkRoute("52EF477C2D995F40", "5A407B47132C07C6", "links/story/the-room-hums/to/deep-vault", "5DE7E217677CA8EC", "16783315E0833B1D", 8.0, -2.0, "legacy"),
    StoryLinkRoute("5538973B3F8B1C72", "0CEB581902A9D016", "links/story/certus-resonance/to/field-manual-storage-lattice", "5E7D4B6F8E276102", "70380821D8D0339D", 0.0, -2.0, "managed"),
    StoryLinkRoute("738C49C0D9F98BBC", "4B0048F311BDF3D9", "links/story/brass-standard/to/field-manual-kinetics", "629176DBDA9F156A", "686943DC0749D6E0", 0.0, -2.0, "managed"),
    StoryLinkRoute("738C49C0D9F98BBC", "7199A16DB5D83154", "links/story/256-track-capstone/to/certification-kinetics-i", "69EE43798DB7CA99", "1641CC316D20D678", 14.0, -2.0, "managed"),
    StoryLinkRoute("584A7E77CC881049", "4D41BE537DD35854", "links/story/air-compressor/to/field-manual-pressure", "61802D4BBFDF55DF", "084209B68927F9FC", 0.0, -2.0, "managed"),
    StoryLinkRoute("584A7E77CC881049", "53C65BE4DB17F1B9", "links/story/logistics-drone/to/logistics-i", "52AA7825E2F97C4E", "25E5B276B9FA47ED", 12.0, -2.0, "managed"),
    StoryLinkRoute("257F2005E2D76B80", "0D1D4842B326D878", "links/story/energizing-orb/to/field-manual-power-networks", "2316FCA654FE01E8", "5334545A948815F6", 0.0, -2.0, "managed"),
    StoryLinkRoute("257F2005E2D76B80", "6B876A865DE7A77A", "links/story/10m-fe-reserve/to/power-i", "4BEDC9C2880C08FC", "64659C3AE503FE5D", 14.0, -2.0, "managed"),
    StoryLinkRoute("37C54E49759AFDDF", "3F12A84AF92F28B8", "links/story/oxygen-separation/to/field-manual-matter-systems", "34F3D13C79A4FB05", "6B09A1A11CD08E68", 0.0, -2.0, "managed"),
    StoryLinkRoute("37C54E49759AFDDF", "45A86A6AA4AD7824", "links/story/reactor-warning/to/field-manual-nuclear-safety", "35725A5429FF1BA4", "4EEAB6F41DB426E7", 14.0, -2.0, "managed"),
    StoryLinkRoute("37C54E49759AFDDF", "3C72E0ADC8E785D0", "links/story/1024-ingot-quota/to/ore-loop-i", "664CCB012CC47823", "1AE92DE8CA81283E", 12.0, -3.0, "managed"),
    StoryLinkRoute("11CA083771CCB5BE", "4F8F8B4545572260", "links/story/drone-delivery/to/logistics-i", "128E1BA6D3EE37C3", "25E5B276B9FA47ED", 4.0, -3.0, "managed"),
    StoryLinkRoute("11CA083771CCB5BE", "27AEE834BFD148F2", "links/story/ae-stockkeeping/to/autocrafting-i", "364E22ABAC317B0F", "3011977E372A3BC6", 0.0, -2.0, "managed"),
    StoryLinkRoute("11CA083771CCB5BE", "742BEB99DFA479FD", "links/story/create-feed-line/to/cross-mod-i", "65486B7C21041B56", "02BA27AF63721ACA", 2.0, -2.0, "managed"),
    StoryLinkRoute("2D7CB8E643BDC03B", "6A0FBE1789BEFD37", "links/story/machine-core/to/field-manual-frontier-machines", "5D99BED063D4488E", "6CC0CCE16F9FB5BE", 0.0, -2.0, "managed"),
    StoryLinkRoute("40BA93EAD765D4D0", "10EEBFB30F143EC4", "links/story/ancient-factory/to/expedition-log", "06070155FD5469A5", "5DBA48B322065E95", 0.0, -2.0, "managed"),
    StoryLinkRoute("2FD06A1068D554E9", "19D5F09EADF78A32", "links/story/fission-assembly/to/field-manual-nuclear-safety", "7F357CA7C9FBB077", "4EEAB6F41DB426E7", 0.0, -2.0, "managed"),
    StoryLinkRoute("582DF217557144DA", "557DC7BACD462EFE", "links/story/flight-harness/to/field-manual-frontier-machines", "7861131F24E674B1", "6CC0CCE16F9FB5BE", 0.0, -2.0, "managed"),
    StoryLinkRoute("582DF217557144DA", "23C08FB037E35BDE", "links/story/starlight/to/expedition-log", "3C3AE361791A7594", "5DBA48B322065E95", 10.0, -2.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/certification-kinetics-i", "3AC941407F3E02BF", "1641CC316D20D678", 6.0, -2.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/logistics-i", "3BCDB42DD3DDE3D9", "25E5B276B9FA47ED", 8.0, -2.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/ore-loop-i", "28ED48250EEEB0B0", "1AE92DE8CA81283E", 10.0, -2.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/autocrafting-i", "1F67BD0B535DE519", "3011977E372A3BC6", 6.0, -4.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/cross-mod-i", "7E8B551630D5E4B4", "02BA27AF63721ACA", 8.0, -4.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/power-i", "02BB08E9E27536BE", "64659C3AE503FE5D", 10.0, -4.0, "managed"),
    StoryLinkRoute("4402713763771CFA", "2D6ACF1CCBC7B4F2", "links/story/certified-bulk-quotas/to/infrastructure-ii", "15E20CF17890BA99", "7CB2D7D361BEA4C4", 8.0, -6.0, "managed"),
    StoryLinkRoute("7E9B015A32C6D980", "0055C66103106D86", "links/story/kinetic-frame/to/field-manual-kinetics", "1DFDF1063452C6CE", "686943DC0749D6E0", 0.0, -4.0, "managed"),
    StoryLinkRoute("7E9B015A32C6D980", "52FE1624DCCE878F", "links/story/industrial-anchor/to/field-manual-heavy-industry", "2801038AFDC85960", "3E77A16CB0C0AD11", 0.0, -3.0, "managed"),
    StoryLinkRoute("7E9B015A32C6D980", "50775CE87FAA4EB7", "links/story/isotopic-core/to/field-manual-nuclear-safety", "6EEE18DA9492CAD2", "4EEAB6F41DB426E7", 2.0, 0.0, "managed"),
    StoryLinkRoute("7E9B015A32C6D980", "7F064705A3CAB2E6", "links/story/lattice-matrix/to/field-manual-storage-lattice", "2036C916B89B3B5A", "70380821D8D0339D", 0.0, 3.0, "managed"),
    StoryLinkRoute("7E9B015A32C6D980", "39C1F24EABBB34A3", "links/story/undercurrent-stabilizer/to/resonance-proof", "427385B56F487768", "6363BCE8A71FA766", 0.0, 4.0, "managed"),
    StoryLinkRoute("6C4AE5CE13773438", "36D0902A2921C44E", "links/story/monument-footprint/to/field-manual-kinetics", "24D5FA8885DE541F", "686943DC0749D6E0", 0.0, -3.0, "managed"),
    StoryLinkRoute("6C4AE5CE13773438", "66AD5C821947DF8E", "links/story/separate-grid/to/field-manual-power-networks", "31E79CC52B5D1639", "5334545A948815F6", 0.0, 3.0, "managed"),
)


MANUAL_RETURN_ROUTES = (
    ManualReturnRoute("4690C88367D47FF3", "links/manuals/kinetics/return/alloy-of-beginnings", "39C96EB4C75EED18", "0576C37E9FA4116C", 0.0, -2.0),
    ManualReturnRoute("150C6F996983394C", "links/manuals/heavy-industry/return/the-engineers-bench", "386444141B66F453", "20169EC099FABBA0", 0.0, -2.0),
    ManualReturnRoute("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/first-current", "6D41B7269E44A298", "1AC07872BABAC949", 0.0, -2.0),
    ManualReturnRoute("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/the-engine-room", "71C9341BE0B9B992", "43860D6CFEF31BB9", 2.0, -2.0),
    ManualReturnRoute("01749E1554DFF98B", "links/manuals/storage-lattice/return/certus-resonance", "54328C23013544B5", "0CEB581902A9D016", 0.0, -2.0),
    ManualReturnRoute("4690C88367D47FF3", "links/manuals/kinetics/return/brass-standard", "2468522409E683FD", "4B0048F311BDF3D9", 2.0, -2.0),
    ManualReturnRoute("0A510C4BD2A3818B", "links/manuals/pressure/return/air-compressor", "68E005D35965E4F9", "4D41BE537DD35854", 0.0, -2.0),
    ManualReturnRoute("67F13F819570ED52", "links/manuals/power-networks/return/energizing-orb", "277025CE751ECC8D", "0D1D4842B326D878", 0.0, -2.0),
    ManualReturnRoute("4DE10FFCDEEF9892", "links/manuals/matter-systems/return/oxygen-separation", "3C25350A9C3F2146", "3F12A84AF92F28B8", 4.0, -2.0),
    ManualReturnRoute("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/reactor-warning", "5C9799B0DE4547F7", "45A86A6AA4AD7824", 0.0, -2.0),
    ManualReturnRoute("67C126F7B1338CB1", "links/manuals/frontier-machines/return/machine-core", "44EA9C1D7956D65F", "6A0FBE1789BEFD37", 0.0, -2.0),
    ManualReturnRoute("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/fission-assembly", "0AA077A5B734EE35", "19D5F09EADF78A32", 2.0, -2.0),
    ManualReturnRoute("67C126F7B1338CB1", "links/manuals/frontier-machines/return/flight-harness", "0BA82C65D67C3755", "557DC7BACD462EFE", 2.0, -2.0),
    ManualReturnRoute("4690C88367D47FF3", "links/manuals/kinetics/return/kinetic-frame", "7981C54795DE1D80", "0055C66103106D86", 4.0, -2.0),
    ManualReturnRoute("150C6F996983394C", "links/manuals/heavy-industry/return/industrial-anchor", "2837E3B154B9CF56", "52FE1624DCCE878F", 2.0, -2.0),
    ManualReturnRoute("0B7C7859EBD6EFF3", "links/manuals/nuclear-safety/return/isotopic-core", "1768F75584D09447", "50775CE87FAA4EB7", 4.0, -2.0),
    ManualReturnRoute("01749E1554DFF98B", "links/manuals/storage-lattice/return/lattice-matrix", "6FDA5AEE392F30BF", "7F064705A3CAB2E6", 2.0, -2.0),
    ManualReturnRoute("4690C88367D47FF3", "links/manuals/kinetics/return/monument-footprint", "2C837083D839A135", "36D0902A2921C44E", 6.0, -2.0),
    ManualReturnRoute("67F13F819570ED52", "links/manuals/power-networks/return/separate-grid", "663E47307E11A38C", "66AD5C821947DF8E", 2.0, -2.0),
)


def _exact_keys(value: object, expected: set[str], path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    if set(value) != expected:
        raise ValueError(
            f"{path} has invalid fields: expected {sorted(expected)}, found {sorted(value)}"
        )
    return value


def _required_string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _required_id(value: object, path: str) -> str:
    identifier = _required_string(value, path)
    if _FTB_ID.fullmatch(identifier) is None:
        raise ValueError(f"{path} must be a signed-safe FTB identity")
    return identifier


def load_story_audit(
    fixture_path: Path | None = None,
    *,
    repository_root: Path | None = None,
) -> dict[str, object]:
    repository_root = (
        Path(__file__).resolve().parents[2]
        if repository_root is None
        else Path(repository_root)
    )
    fixture_path = (
        repository_root / STORY_AUDIT_PATH
        if fixture_path is None
        else Path(fixture_path)
    )
    try:
        payload = fixture_path.read_bytes()
        audit = json.loads(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid story audit {fixture_path}: {error}") from error
    if not payload.endswith(b"\n") or b"\r" in payload:
        raise ValueError(f"story audit is not canonical: {fixture_path}")
    canonical = (json.dumps(audit, indent=2, sort_keys=True) + "\n").encode("utf-8")
    if payload != canonical:
        raise ValueError(f"story audit is not canonical: {fixture_path}")
    canonical_path = repository_root / STORY_AUDIT_PATH
    if fixture_path.resolve() == canonical_path.resolve():
        digest = hashlib.sha256(payload).hexdigest()
        if digest != STORY_AUDIT_SHA256:
            raise ValueError(
                f"story audit SHA-256 mismatch: expected {STORY_AUDIT_SHA256}, found {digest}"
            )

    root = _exact_keys(audit, _AUDIT_KEYS, "story audit")
    if root.get("schema_version") != 1:
        raise ValueError("story audit schema_version must be 1")
    if root.get("source_commit") != STORY_AUDIT_SOURCE_COMMIT:
        raise ValueError("story audit source_commit does not match the frozen contract")
    if root.get("story_group_id") != STORY_GROUP_ID:
        raise ValueError("story audit story_group_id does not match the Story group")
    counts = _exact_keys(root.get("counts"), set(_EXPECTED_COUNTS), "story audit counts")
    if dict(counts) != _EXPECTED_COUNTS:
        raise ValueError("story audit counts do not match the frozen contract")
    records = root.get("quests")
    if not isinstance(records, list):
        raise ValueError("story audit quests must be an array")

    seen_ids: set[str] = set()
    retained = revised = linked = outbound_links = 0
    for index, raw_record in enumerate(records):
        path = f"story audit quests[{index}]"
        record = _exact_keys(raw_record, _RECORD_KEYS, path)
        _required_id(record.get("chapter_id"), f"{path}.chapter_id")
        quest_id = _required_id(record.get("quest_id"), f"{path}.quest_id")
        if quest_id in seen_ids:
            raise ValueError(f"duplicate story audit quest ID: {quest_id}")
        seen_ids.add(quest_id)
        if type(record.get("chapter_order")) is not int or type(record.get("quest_order")) is not int:
            raise ValueError(f"{path} orders must be integers")
        _required_string(record.get("chapter_title"), f"{path}.chapter_title")
        _required_string(record.get("title"), f"{path}.title")
        dependencies = record.get("dependencies")
        if not isinstance(dependencies, list) or any(_FTB_ID.fullmatch(value) is None for value in dependencies if isinstance(value, str)) or any(not isinstance(value, str) for value in dependencies):
            raise ValueError(f"{path}.dependencies must contain signed-safe FTB identities")
        if not isinstance(record.get("current_subtitle"), str):
            raise ValueError(f"{path}.current_subtitle must be a string")
        description = record.get("current_description")
        if not isinstance(description, list) or not all(isinstance(line, str) for line in description):
            raise ValueError(f"{path}.current_description must be a string array")
        status = record.get("prose_status")
        replacement_subtitle = record.get("replacement_subtitle")
        replacement_description = record.get("replacement_description")
        if status == "retained":
            retained += 1
            if replacement_subtitle is not None or replacement_description is not None:
                raise ValueError(f"{path} retained prose must not declare replacements")
        elif status == "revised":
            revised += 1
            if not isinstance(replacement_subtitle, str) or not replacement_subtitle:
                raise ValueError(f"{path} revised subtitle must be non-empty")
            if not isinstance(replacement_description, list) or not replacement_description or not all(isinstance(line, str) and line for line in replacement_description):
                raise ValueError(f"{path} revised description must be a non-empty string array")
        else:
            raise ValueError(f"{path}.prose_status must be retained or revised")
        is_linked = record.get("linked")
        slugs = record.get("outbound_link_slugs")
        if type(is_linked) is not bool or not isinstance(slugs, list) or not all(isinstance(slug, str) and slug for slug in slugs):
            raise ValueError(f"{path} has invalid link classification")
        if is_linked != bool(slugs):
            raise ValueError(f"{path} linked flag does not match outbound_link_slugs")
        linked += int(is_linked)
        outbound_links += len(slugs)

    observed_counts = {
        "story_chapters": len({record["chapter_id"] for record in records}),
        "story_quests": len(records),
        "retained": retained,
        "revised": revised,
        "linked": linked,
        "outbound_links": outbound_links,
    }
    if observed_counts != _EXPECTED_COUNTS:
        raise ValueError(
            f"story audit observed counts do not match the contract: {observed_counts}"
        )
    route_slugs: dict[str, list[str]] = defaultdict(list)
    for route in STORY_LINK_ROUTES:
        route_slugs[route.source_quest_id].append(route.slug)
    for record in records:
        if record["outbound_link_slugs"] != route_slugs[record["quest_id"]]:
            raise ValueError(
                f"story audit outbound links do not match the route map for {record['quest_id']}"
            )
    return copy.deepcopy(dict(root))


def _merge_links(
    chapter: ChapterSpec,
    links: Sequence[QuestLinkSpec],
) -> ChapterSpec:
    by_slug = {link.slug: link for link in chapter.quest_links}
    by_id = {link.id: link for link in chapter.quest_links}
    merged = list(chapter.quest_links)
    for link in links:
        existing = by_slug.get(link.slug)
        if existing is not None:
            if existing != link:
                raise ValueError(f"conflicting quest link declaration: {link.slug}")
            continue
        existing = by_id.get(link.id)
        if existing is not None:
            raise ValueError(
                f"quest link ID collision between {existing.slug} and {link.slug}: {link.id}"
            )
        merged.append(link)
        by_slug[link.slug] = link
        by_id[link.id] = link
    return replace(chapter, quest_links=tuple(merged))


def apply_manual_return_links(
    chapters: Sequence[ChapterSpec],
) -> tuple[ChapterSpec, ...]:
    routes_by_owner: dict[str, list[QuestLinkSpec]] = defaultdict(list)
    for route in MANUAL_RETURN_ROUTES:
        routes_by_owner[route.owner_chapter_id].append(route.link)
    found: set[str] = set()
    result = []
    for chapter in chapters:
        links = routes_by_owner.get(chapter.id)
        if links is None:
            result.append(chapter)
            continue
        if chapter.group.resolved_id != MANUAL_GROUP_ID or not chapter.slug.startswith("manuals/"):
            raise ValueError(f"manual return owner is not a field manual: {chapter.id}")
        found.add(chapter.id)
        result.append(_merge_links(chapter, links))
    missing = set(routes_by_owner) - found
    if missing:
        raise ValueError("missing manual return owners: " + ", ".join(sorted(missing)))
    return tuple(result)


def apply_managed_story_cohesion(
    chapters: Sequence[ChapterSpec],
) -> tuple[ChapterSpec, ...]:
    audit = load_story_audit()
    records = {record["quest_id"]: record for record in audit["quests"]}
    routes_by_owner: dict[str, list[QuestLinkSpec]] = defaultdict(list)
    expected_sources: dict[str, set[str]] = defaultdict(set)
    for route in STORY_LINK_ROUTES:
        if route.route != "managed":
            continue
        routes_by_owner[route.owner_chapter_id].append(route.link)
        expected_sources[route.owner_chapter_id].add(route.source_quest_id)

    found_story_ids: set[str] = set()
    found_route_owners: set[str] = set()
    result = []
    for chapter in chapters:
        if chapter.group.resolved_id != STORY_GROUP_ID:
            result.append(chapter)
            continue
        revised_quests: list[QuestSpec] = []
        chapter_quest_ids = {quest.id for quest in chapter.quests}
        for quest in chapter.quests:
            record = records.get(quest.id)
            if record is None:
                raise ValueError(f"managed Story quest is absent from the audit: {quest.id}")
            if record["chapter_id"] != chapter.id:
                raise ValueError(f"managed Story quest has wrong audited owner: {quest.id}")
            found_story_ids.add(quest.id)
            subtitle = (
                record["replacement_subtitle"]
                if record["prose_status"] == "revised"
                else record["current_subtitle"]
            )
            description = (
                tuple(record["replacement_description"])
                if record["prose_status"] == "revised"
                else tuple(record["current_description"])
            )
            revised_quests.append(
                replace(quest, subtitle=subtitle, description=description)
            )
        missing_sources = expected_sources.get(chapter.id, set()) - chapter_quest_ids
        if missing_sources:
            raise ValueError(
                f"managed Story link sources missing from {chapter.id}: "
                + ", ".join(sorted(missing_sources))
            )
        updated = replace(chapter, quests=tuple(revised_quests))
        links = routes_by_owner.get(chapter.id)
        if links is not None:
            found_route_owners.add(chapter.id)
            updated = _merge_links(updated, links)
        result.append(updated)

    expected_managed_story_ids = {
        record["quest_id"]
        for record in audit["quests"]
        if any(chapter.id == record["chapter_id"] for chapter in chapters)
    }
    if found_story_ids != expected_managed_story_ids:
        raise ValueError("managed Story audit coverage is incomplete")
    missing_owners = set(routes_by_owner) - found_route_owners
    if missing_owners:
        raise ValueError("missing managed Story link owners: " + ", ".join(sorted(missing_owners)))
    return tuple(result)


def apply_story_cohesion(
    catalog: Sequence[ChapterSpec],
) -> list[ChapterSpec]:
    with_returns = apply_manual_return_links(catalog)
    return list(apply_managed_story_cohesion(with_returns))
