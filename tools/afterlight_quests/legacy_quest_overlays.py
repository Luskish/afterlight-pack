from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .builder import (
    ChapterSpec,
    QuestLinkSpec,
    SnbtParseError,
    _atomic_write,
    _canonical_quest_link_coordinate,
    _escape,
    _managed_quest_slug_index,
    _parse_snbt,
    _render_quest_item_audit,
    _require_signed_safe_ftb_identity,
    _resolve_quest_link_target,
    _scan_snbt_value_spans,
    _validate_catalog,
    _validated_legacy_quest_ids,
)
from .catalog import load_common_commodity_declarations
from .quest_build_transaction import (
    QuestBuildTransaction,
    candidate_workspace,
    quest_build_dependency_roots,
)
from .story_cohesion import STORY_LINK_ROUTES


STORY_GROUP_ID = "4525BB3160467FCB"
MANUAL_GROUP_ID = "4A20F33642175B95"
SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class LegacyQuestLinkOverlay:
    chapter_id: str
    expected_outside_sha256: str
    quest_links: tuple[QuestLinkSpec, ...]


@dataclass(frozen=True)
class LegacyChapterOrderOverlay:
    chapter_id: str
    expected_outside_sha256: str
    order_index: int


@dataclass(frozen=True)
class LegacyLocalizationOverlay:
    key: str
    value: str | tuple[str, ...]


@dataclass(frozen=True)
class LegacyLocalizationManifest:
    expected_outside_sha256: str | None
    overlays: tuple[LegacyLocalizationOverlay, ...]


@dataclass(frozen=True)
class LegacyCommodityTaskOverlay:
    chapter_id: str
    task_id: str
    expected_outside_sha256: str
    declaration_key: str


def _legacy_story_links(chapter_id: str) -> tuple[QuestLinkSpec, ...]:
    return tuple(
        route.link
        for route in STORY_LINK_ROUTES
        if route.route == "legacy" and route.owner_chapter_id == chapter_id
    )


LEGACY_QUEST_LINK_OVERLAYS = (
    LegacyQuestLinkOverlay(
        chapter_id="4C01977EF77930A6",
        expected_outside_sha256="84b682eb046cc73a8e1962ae7b98a37a3323a5d035054e372b919a43de7b3729",
        quest_links=_legacy_story_links("4C01977EF77930A6"),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="770DAD173D9C234B",
        expected_outside_sha256="3cca17187e1382064192ea9235b0679590fc844954b689d413aad90cd84adb7e",
        quest_links=_legacy_story_links("770DAD173D9C234B"),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="45491A24F6B8C192",
        expected_outside_sha256="ae8fe08053a769600b8d416bebb679b1731b0680a87f164e694ee861c533b139",
        quest_links=_legacy_story_links("45491A24F6B8C192"),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="52EF477C2D995F40",
        expected_outside_sha256="874388f975a02bda088fcb30650bb03c15935a98b3c2e85453ebf86bc4bd2df0",
        quest_links=_legacy_story_links("52EF477C2D995F40"),
    ),
)


LEGACY_CHAPTER_ORDER_OVERLAYS = (
    LegacyChapterOrderOverlay(
        chapter_id="23643435F7BE74AC",
        expected_outside_sha256="1f4c08e6b0a16ca3daea9df556a0362755651279deac7426643ac1514505899d",
        order_index=10,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="7BA8A3335FAC821A",
        expected_outside_sha256="9595ed5d1d1854b5819cceb3f711b00694dde3911f3f0ed9ccfd8d0443233db6",
        order_index=11,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="16E0B20162F6DAE5",
        expected_outside_sha256="f8bf11642044bc13d24e9f87a20d9f6c9c7438b040825dc00df168c7dd88282b",
        order_index=12,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="775CD739E3318A7E",
        expected_outside_sha256="336f13085cdf9b13e9bc950a4d96f7c3a175e565531435e3ec440759fcaebc2e",
        order_index=13,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="18471B3E458EAB62",
        expected_outside_sha256="0f1c4a5640a3cab7dde702708ad7f4489a6d59d60f2fb754d883d68fdf77eae6",
        order_index=14,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="0FAB5AA8294D4487",
        expected_outside_sha256="66dcc20b74ab4d7736306bd8b8ac42b1fdaf17045b8fee58ca79c999d72af3cf",
        order_index=15,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="5070DE6E2B300F4B",
        expected_outside_sha256="6a47c3fdd03732e2c3cb63b23d701cfeeead40ca4814d1f28ec4dd4fd2c1be13",
        order_index=16,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="758F5AEF697F7EFD",
        expected_outside_sha256="489fcf938d8b5c527e448130dfb910b1b590b03722c39b25017421b68408bb41",
        order_index=30,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="7C611E8A94BC5CE5",
        expected_outside_sha256="f4a58c6f862abdf812317f8388ad47e9bb5101979330a566cc28488dc1f227ef",
        order_index=31,
    ),
    LegacyChapterOrderOverlay(
        chapter_id="099200314296766A",
        expected_outside_sha256="6cb986df548e93ac96ff67e6a8e39e3644762ccbdb12bfc751073510aefa5cf5",
        order_index=32,
    ),
)


LEGACY_LOCALIZATION_OVERLAYS = LegacyLocalizationManifest(
    expected_outside_sha256=(
        "7fef8b47eeb10126ed18472316279d750e33be9083348fae5ad9a3e5a2e5a7a0"
    ),
    overlays=(
        LegacyLocalizationOverlay(
            key="chapter_group.4A20F33642175B95.title",
            value="Field Manuals & Certifications",
        ),
        LegacyLocalizationOverlay(
            key="quest.45021BE218C5DFBD.quest_subtitle",
            value="Survival becomes a supply line.",
        ),
        LegacyLocalizationOverlay(
            key="quest.45021BE218C5DFBD.quest_desc",
            value=(
                "Cold Boot proved that you can survive one emergency. Recovery begins when the next meal, tool, and shelter no longer depend on luck.",
                "Treat every salvage stream as input, every repeated need as a process, and every waste pile as evidence. Scavenging becomes industry through repetition.",
            ),
        ),
        LegacyLocalizationOverlay(
            key="quest.718424A08FE06E9A.quest_subtitle",
            value="Material hunger leaves coordinates in the wreckage.",
        ),
        LegacyLocalizationOverlay(
            key="quest.718424A08FE06E9A.quest_desc",
            value=(
                "Scavenger's Creed made supply repeatable, then exposed the limit of local wreckage. The systems ahead require material the vault cannot provide.",
                "Survey the Scarlands and follow the surviving portal record. The Nether is evidence that movement through the old network remains possible. The Expedition Log can orient the route without becoming part of story progress.",
            ),
        ),
        LegacyLocalizationOverlay(
            key="quest.79145D1842E317AA.quest_subtitle",
            value="Passage is useful only when return is possible.",
        ),
        LegacyLocalizationOverlay(
            key="quest.79145D1842E317AA.quest_desc",
            value=(
                "The Scarlands proved that the old routes still open. A recovery plan needs defended ground to return to, repair within, and improve.",
                "Claim your territory with the map tools (the Ascendancy called this cadastral registration; the map calls it claiming chunks). Then establish permanent industry. Field Manual: Heavy Industry begins at the recovered manual and the first formed multiblock.",
            ),
        ),
        LegacyLocalizationOverlay(
            key="quest.43860D6CFEF31BB9.quest_subtitle",
            value="Steel and first current can now multiply labor.",
        ),
        LegacyLocalizationOverlay(
            key="quest.43860D6CFEF31BB9.quest_desc",
            value=(
                "Foothold secured a stable base, steel, and stored current. Those conditions support machines that repeat work without spending another pair of hands.",
                "Recover osmium and rebuild the first processing line in measured stages. Field Manual: Matter Systems starts with sided machines, power, and an observable ore-doubling loop.",
            ),
        ),
    ),
)


LEGACY_COMMODITY_TASK_OVERLAYS = (
    LegacyCommodityTaskOverlay(
        chapter_id="5B93C6934B230CFB",
        task_id="39C717BFFEE3D235",
        expected_outside_sha256=(
            "097452385aa86dcc1d136db46492b424043d4a23dc57803d3e25136707d5a5cb"
        ),
        declaration_key="39C717BFFEE3D235",
    ),
)


APPROVED_EXISTING_ORDERS = {
    overlay.chapter_id: overlay.order_index
    for overlay in LEGACY_CHAPTER_ORDER_OVERLAYS
}


def _outside_span_sha256(text: str, spans: Sequence[object]) -> str:
    digest = hashlib.sha256()
    cursor = 0
    for span in sorted(spans, key=lambda item: item.offset):
        if span.offset < cursor:
            raise ValueError("overlapping legacy overlay value spans")
        digest.update(text[cursor : span.offset].encode("utf-8"))
        cursor = span.end
    digest.update(text[cursor:].encode("utf-8"))
    return digest.hexdigest()


def _replace_value_spans(text: str, replacements: Sequence[tuple[object, str]]) -> str:
    result = text
    previous_offset = len(text) + 1
    for span, replacement in sorted(
        replacements,
        key=lambda item: item[0].offset,
        reverse=True,
    ):
        if span.end > previous_offset:
            raise ValueError("overlapping legacy overlay replacements")
        result = result[: span.offset] + replacement + result[span.end :]
        previous_offset = span.offset
    return result


def _unique_top_level_value_span(text: str, field: str, path: Path):
    try:
        matches = [
            span
            for span in _scan_snbt_value_spans(text)
            if span.path == (field,)
        ]
    except SnbtParseError as error:
        raise ValueError(f"malformed SNBT in {path}: {error}") from error
    if not matches:
        raise ValueError(f"missing top-level {field} in {path}")
    if len(matches) != 1:
        raise ValueError(f"duplicate top-level {field} in {path}")
    return matches[0]


def _commodity_task_location(
    text: str,
    task_id: str,
    path: Path,
) -> tuple[int, int, str]:
    try:
        spans = _scan_snbt_value_spans(text)
    except SnbtParseError as error:
        raise ValueError(f"malformed SNBT in {path}: {error}") from error
    matches = [
        span
        for span in spans
        if len(span.path) == 5
        and span.path[0] == "quests"
        and isinstance(span.path[1], int)
        and span.path[2] == "tasks"
        and isinstance(span.path[3], int)
        and span.path[4] == "id"
        and text[span.offset : span.end] == _escape(task_id)
    ]
    if not matches:
        raise ValueError(f"commodity overlay task {task_id} is missing from {path}")
    if len(matches) != 1:
        raise ValueError(f"duplicate commodity overlay task ID {task_id} in {path}")
    task_path = matches[0].path[:4]
    type_spans = [span for span in spans if span.path == (*task_path, "type")]
    if len(type_spans) != 1:
        raise ValueError(f"commodity overlay task {task_id} has no unique type in {path}")
    task_type_literal = text[type_spans[0].offset : type_spans[0].end]
    return int(task_path[1]), int(task_path[3]), task_type_literal


def _commodity_task_item_span(text: str, task_id: str, path: Path):
    quest_index, task_index, task_type_literal = _commodity_task_location(
        text, task_id, path
    )
    if task_type_literal != _escape("item"):
        raise ValueError(f"non-item commodity overlay task {task_id} in {path}")
    try:
        matches = [
            span
            for span in _scan_snbt_value_spans(text)
            if span.path == ("quests", quest_index, "tasks", task_index, "item")
        ]
    except SnbtParseError as error:
        raise ValueError(f"malformed SNBT in {path}: {error}") from error
    if not matches:
        raise ValueError(f"missing item span for commodity overlay task {task_id} in {path}")
    if len(matches) != 1:
        raise ValueError(f"duplicate item span for commodity overlay task {task_id} in {path}")
    return matches[0]


def _validated_sha256(value: object, label: str) -> str:
    if not isinstance(value, str) or SHA256.fullmatch(value) is None:
        raise ValueError(f"invalid outside-span SHA-256 for {label}: {value!r}")
    return value


def _render_quest_links_value(
    links: Sequence[QuestLinkSpec],
    resolved_targets: Sequence[tuple[str, str, str]],
) -> str:
    if not links:
        return "[ ]"
    lines = ["["]
    for link, (target, x_literal, y_literal) in zip(
        links,
        resolved_targets,
        strict=True,
    ):
        lines.append(
            f"\t\t{{ id: {_escape(link.id)}, linked_quest: {_escape(target)}, "
            f"x: {x_literal}, y: {y_literal} }}"
        )
    lines.append("\t]")
    return "\n".join(lines)


def _render_localization_value(value: str | tuple[str, ...]) -> str:
    if isinstance(value, str):
        return _escape(value)
    if not isinstance(value, tuple) or not all(isinstance(line, str) for line in value):
        raise ValueError(f"invalid legacy localization value: {value!r}")
    lines = ["["]
    lines.extend(f"\t\t{_escape(line)}" for line in value)
    lines.append("\t]")
    return "\n".join(lines)


def _render_commodity_item_value(tag: str) -> str:
    return "\n".join(
        (
            "{",
            "\t\t\t\t\tcount: 1",
            '\t\t\t\t\tid: "ftbfiltersystem:smart_filter"',
            "\t\t\t\t\tcomponents: { "
            f'"ftbfiltersystem:filter": "ftbfiltersystem:item_tag({tag})" }}',
            "\t\t\t\t}",
        )
    )


def _render_plain_item_value(item: Mapping[str, object]) -> str:
    if set(item) != {"count", "id"} or item.get("count") != "1":
        raise ValueError(f"unsupported frozen commodity item payload: {item!r}")
    item_id = item.get("id")
    if not isinstance(item_id, str):
        raise ValueError(f"unsupported frozen commodity item ID: {item_id!r}")
    return f"{{ count: 1, id: {_escape(item_id)} }}"


def _chapter_corpus(
    quest_root: Path,
    candidate_bytes: Mapping[Path, bytes],
) -> dict[Path, Mapping[str, object]]:
    chapters: dict[Path, Mapping[str, object]] = {}
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        payload = candidate_bytes.get(path, path.read_bytes())
        try:
            parsed = _parse_snbt(payload.decode("utf-8"))
        except (UnicodeDecodeError, SnbtParseError) as error:
            raise ValueError(f"malformed SNBT in {path}: {error}") from error
        if not isinstance(parsed, Mapping):
            raise ValueError(f"malformed SNBT in {path}: chapter root must be a compound")
        chapters[path] = parsed
    return chapters


def _unmanaged_quest_ids(
    quest_root: Path,
    catalog: Sequence[ChapterSpec],
) -> tuple[str, ...]:
    managed_chapter_ids = {chapter.id for chapter in catalog}
    quest_ids: list[str] = []
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        if path.stem in managed_chapter_ids:
            continue
        try:
            chapter = _parse_snbt(path.read_text(encoding="utf-8"))
        except (OSError, SnbtParseError) as error:
            raise ValueError(f"malformed unmanaged chapter in {path}: {error}") from error
        if (
            not isinstance(chapter, Mapping)
            or chapter.get("id") != path.stem
            or not isinstance(chapter.get("quests"), list)
        ):
            raise ValueError(f"malformed unmanaged chapter in {path}")
        for quest in chapter["quests"]:
            if not isinstance(quest, Mapping) or not isinstance(quest.get("id"), str):
                raise ValueError(f"malformed unmanaged quest in {path}")
            quest_ids.append(quest["id"])
    return _validated_legacy_quest_ids(quest_ids)


def _collect_corpus_ids(
    chapters: Mapping[Path, Mapping[str, object]],
    link_owner_ids: set[str],
) -> set[str]:
    identifiers: set[str] = set()

    def visit(value: object) -> None:
        if isinstance(value, Mapping):
            identifier = value.get("id")
            if isinstance(identifier, str) and re.fullmatch(r"[0-9A-F]{16}", identifier):
                identifiers.add(identifier)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    for chapter in chapters.values():
        chapter_id = chapter.get("id")
        if chapter_id in link_owner_ids:
            chapter = dict(chapter)
            chapter["quest_links"] = []
        visit(chapter)
    return identifiers


def _validate_story_group_orders(
    chapters: Mapping[Path, Mapping[str, object]],
) -> None:
    orders: dict[int, str] = {}
    observed_existing: set[str] = set()
    for path, chapter in chapters.items():
        if chapter.get("group") != MANUAL_GROUP_ID:
            continue
        chapter_id = chapter.get("id")
        raw_order = chapter.get("order_index")
        if not isinstance(chapter_id, str):
            raise ValueError(f"malformed manual-group chapter ID in {path}")
        if not isinstance(raw_order, str) or re.fullmatch(r"-?[0-9]+", raw_order) is None:
            raise ValueError(f"malformed manual-group order_index in {path}: {raw_order!r}")
        order = int(raw_order)
        previous = orders.get(order)
        if previous is not None:
            raise ValueError(
                f"duplicate manual-group order_index {order}: {previous}, {chapter_id}"
            )
        orders[order] = chapter_id
        expected = APPROVED_EXISTING_ORDERS.get(chapter_id)
        if expected is not None:
            observed_existing.add(chapter_id)
            if order != expected:
                raise ValueError(
                    f"invalid approved order for existing chapter {chapter_id}: "
                    f"expected {expected}, found {order}"
                )
        elif order not in range(8):
            raise ValueError(
                f"unapproved manual-group order for chapter {chapter_id}: {order}"
            )
    missing = set(APPROVED_EXISTING_ORDERS) - observed_existing
    if missing:
        raise ValueError(
            "missing existing manual-group chapters: " + ", ".join(sorted(missing))
        )


def _apply_legacy_quest_overlays_workspace(
    quest_root: Path,
    *,
    link_overlays: Sequence[LegacyQuestLinkOverlay],
    order_overlays: Sequence[LegacyChapterOrderOverlay],
    localization_overlays: LegacyLocalizationManifest,
    commodity_overlays: Sequence[LegacyCommodityTaskOverlay],
    catalog: Sequence[ChapterSpec] | None = None,
    known_quest_ids: Iterable[str] | None = None,
) -> list[Path]:
    if catalog is None and known_quest_ids is None:
        raise ValueError(
            "legacy overlays require a complete managed catalog or exact known quest ID universe"
        )
    managed_catalog = tuple(catalog or ())
    known_ids = (
        _unmanaged_quest_ids(quest_root, managed_catalog)
        if known_quest_ids is None and catalog is not None
        else _validated_legacy_quest_ids(known_quest_ids or ())
    )
    if catalog is not None:
        _validate_catalog(managed_catalog, legacy_quest_ids=known_ids)
    quest_slug_index = _managed_quest_slug_index(managed_catalog)
    valid_target_ids = {identifier for identifier, _ in quest_slug_index.values()} | set(known_ids)

    link_chapters: set[str] = set()
    order_chapters: set[str] = set()
    link_ids: set[str] = set()
    resolved_link_overlays: dict[str, tuple[tuple[str, str, str], ...]] = {}
    for overlay_index, overlay in enumerate(link_overlays):
        try:
            chapter_id = _require_signed_safe_ftb_identity(
                overlay.chapter_id,
                f"legacy link overlay chapter at index {overlay_index}",
            )
        except ValueError as error:
            raise ValueError(f"invalid manifest chapter ID: {overlay.chapter_id!r}") from error
        if chapter_id in link_chapters:
            raise ValueError(f"duplicate link overlay chapter ID: {chapter_id}")
        link_chapters.add(chapter_id)
        _validated_sha256(overlay.expected_outside_sha256, f"link overlay {chapter_id}")
        target_coordinates: set[tuple[str, str, str]] = set()
        resolved_links: list[tuple[str, str, str]] = []
        for link_index, link in enumerate(overlay.quest_links):
            try:
                link_id = link.id
            except ValueError as error:
                raise ValueError(
                    f"invalid quest link ID in overlay {chapter_id} at index {link_index}"
                ) from error
            if link_id in link_ids:
                raise ValueError(f"duplicate quest link ID: {link_id}")
            link_ids.add(link_id)
            x_literal = _canonical_quest_link_coordinate(
                link.x,
                f"legacy quest link {link.slug} x coordinate",
            )
            y_literal = _canonical_quest_link_coordinate(
                link.y,
                f"legacy quest link {link.slug} y coordinate",
            )
            target = _resolve_quest_link_target(
                link,
                path=f"link_overlays[{overlay_index}].quest_links[{link_index}].linked_quest",
                chapter_slug=chapter_id,
                quest_slug_index=quest_slug_index,
                valid_explicit_ids=valid_target_ids,
            )
            triple = (target, x_literal, y_literal)
            if triple in target_coordinates:
                raise ValueError(
                    "duplicate quest link target and coordinate triple in chapter "
                    f"{chapter_id}: {target}, {x_literal}, {y_literal}"
                )
            target_coordinates.add(triple)
            resolved_links.append(triple)
        resolved_link_overlays[chapter_id] = tuple(resolved_links)

    for overlay_index, overlay in enumerate(order_overlays):
        try:
            chapter_id = _require_signed_safe_ftb_identity(
                overlay.chapter_id,
                f"legacy order overlay chapter at index {overlay_index}",
            )
        except ValueError as error:
            raise ValueError(f"invalid manifest chapter ID: {overlay.chapter_id!r}") from error
        if chapter_id in order_chapters:
            raise ValueError(f"duplicate order overlay chapter ID: {chapter_id}")
        if chapter_id in link_chapters:
            raise ValueError(f"duplicate legacy overlay chapter ID: {chapter_id}")
        if type(overlay.order_index) is not int:
            raise ValueError(
                f"invalid order_index for legacy overlay {chapter_id}: {overlay.order_index!r}"
            )
        order_chapters.add(chapter_id)
        _validated_sha256(overlay.expected_outside_sha256, f"order overlay {chapter_id}")

    commodity_pairs: set[tuple[str, str]] = set()
    commodity_task_ids: set[str] = set()
    commodity_manifest = load_common_commodity_declarations()
    commodity_declarations = commodity_manifest.by_task_id
    for overlay_index, overlay in enumerate(commodity_overlays):
        try:
            chapter_id = _require_signed_safe_ftb_identity(
                overlay.chapter_id,
                f"legacy commodity overlay chapter at index {overlay_index}",
            )
            task_id = _require_signed_safe_ftb_identity(
                overlay.task_id,
                f"legacy commodity overlay task at index {overlay_index}",
            )
        except ValueError as error:
            raise ValueError(
                f"invalid commodity overlay identity at index {overlay_index}"
            ) from error
        pair = (chapter_id, task_id)
        if pair in commodity_pairs:
            raise ValueError(
                f"duplicate commodity overlay chapter-task pair: {chapter_id}, {task_id}"
            )
        commodity_pairs.add(pair)
        if task_id in commodity_task_ids:
            raise ValueError(f"duplicate commodity overlay task ID: {task_id}")
        commodity_task_ids.add(task_id)
        _validated_sha256(
            overlay.expected_outside_sha256,
            f"commodity overlay {chapter_id}/{task_id}",
        )
        declaration = commodity_declarations.get(overlay.declaration_key)
        if declaration is None:
            raise ValueError(
                f"undeclared commodity fixture key: {overlay.declaration_key}"
            )
        if declaration.chapter_id != chapter_id:
            raise ValueError(
                f"commodity overlay task {task_id} is outside declared chapter {chapter_id}"
            )
        if declaration.already_generalized:
            raise ValueError(
                f"already generalized task {task_id} cannot have a mutating overlay"
            )

    candidate_bytes: dict[Path, bytes] = {}
    originals: dict[Path, bytes] = {}
    replacements: dict[Path, list[tuple[object, str]]] = {}
    for overlay in link_overlays:
        path = quest_root / "chapters" / f"{overlay.chapter_id}.snbt"
        try:
            original = path.read_bytes()
            text = original.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(f"missing or unreadable legacy overlay target {path}: {error}") from error
        span = _unique_top_level_value_span(text, "quest_links", path)
        if not text[span.offset : span.end].startswith("["):
            raise ValueError(f"malformed top-level quest_links in {path}: expected list")
        actual_digest = _outside_span_sha256(text, (span,))
        if actual_digest != overlay.expected_outside_sha256:
            raise ValueError(
                f"outside-span digest mismatch for {path}: "
                f"expected {overlay.expected_outside_sha256}, found {actual_digest}"
            )
        originals[path] = original
        replacements.setdefault(path, []).append(
            (
                span,
                _render_quest_links_value(
                    overlay.quest_links,
                    resolved_link_overlays[overlay.chapter_id],
                ),
            )
        )

    for overlay in order_overlays:
        path = quest_root / "chapters" / f"{overlay.chapter_id}.snbt"
        try:
            original = path.read_bytes()
            text = original.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(f"missing or unreadable legacy overlay target {path}: {error}") from error
        span = _unique_top_level_value_span(text, "order_index", path)
        if re.fullmatch(r"-?[0-9]+", text[span.offset : span.end]) is None:
            raise ValueError(f"malformed top-level order_index in {path}: expected integer")
        actual_digest = _outside_span_sha256(text, (span,))
        if actual_digest != overlay.expected_outside_sha256:
            normalized = text
            for declaration in commodity_manifest.declarations:
                if (
                    declaration.chapter_id != overlay.chapter_id
                    or declaration.already_generalized
                ):
                    continue
                item_span = _commodity_task_item_span(
                    normalized, declaration.task_id, path
                )
                parsed = _parse_snbt(normalized)
                quest_index, task_index, _ = _commodity_task_location(
                    normalized, declaration.task_id, path
                )
                task = parsed["quests"][quest_index]["tasks"][task_index]
                if task.get("item") != declaration.smart_filter_item:
                    continue
                if {
                    key: value for key, value in task.items() if key != "item"
                } != {
                    key: value
                    for key, value in declaration.baseline_task.items()
                    if key != "item"
                }:
                    raise ValueError(
                        f"commodity task {declaration.task_id} fields outside item "
                        "differ during order overlay validation"
                    )
                normalized = _replace_value_spans(
                    normalized,
                    ((item_span, _render_plain_item_value(declaration.old_item)),),
                )
            normalized_span = _unique_top_level_value_span(
                normalized, "order_index", path
            )
            actual_digest = _outside_span_sha256(normalized, (normalized_span,))
        if actual_digest != overlay.expected_outside_sha256:
            raise ValueError(
                f"outside-span digest mismatch for {path}: "
                f"expected {overlay.expected_outside_sha256}, found {actual_digest}"
            )
        originals[path] = original
        replacements.setdefault(path, []).append((span, str(overlay.order_index)))

    for overlay in commodity_overlays:
        path = quest_root / "chapters" / f"{overlay.chapter_id}.snbt"
        try:
            original = path.read_bytes()
            text = original.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(
                f"missing or unreadable commodity overlay target {path}: {error}"
            ) from error
        try:
            quest_index, task_index, _ = _commodity_task_location(
                text, overlay.task_id, path
            )
        except ValueError as error:
            if " is missing from " not in str(error):
                raise
            owner_paths: list[Path] = []
            for candidate_path in sorted((quest_root / "chapters").glob("*.snbt")):
                if candidate_path == path:
                    continue
                try:
                    _commodity_task_location(
                        candidate_path.read_text(encoding="utf-8"),
                        overlay.task_id,
                        candidate_path,
                    )
                except (OSError, UnicodeDecodeError, ValueError):
                    continue
                owner_paths.append(candidate_path)
            if owner_paths:
                raise ValueError(
                    f"commodity overlay task {overlay.task_id} is outside declared "
                    f"chapter {overlay.chapter_id}: {owner_paths[0]}"
                ) from error
            raise
        span = _commodity_task_item_span(text, overlay.task_id, path)
        declaration = commodity_declarations[overlay.declaration_key]
        if declaration.task_id != overlay.task_id:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} does not match fixture "
                f"declaration {overlay.declaration_key}"
            )
        actual_digest = _outside_span_sha256(text, (span,))
        if actual_digest != overlay.expected_outside_sha256:
            raise ValueError(
                f"outside-span digest mismatch for {path}: expected "
                f"{overlay.expected_outside_sha256}, found {actual_digest}"
            )
        try:
            chapter = _parse_snbt(text)
        except SnbtParseError as error:
            raise ValueError(f"malformed SNBT in {path}: {error}") from error
        task = chapter["quests"][quest_index]["tasks"][task_index]
        baseline_task = dict(declaration.baseline_task)
        if {
            key: value for key, value in task.items() if key != "item"
        } != {
            key: value for key, value in baseline_task.items() if key != "item"
        }:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} fields outside item differ "
                "from the frozen task"
            )
        if task.get("item") == declaration.old_item:
            replacement = _render_commodity_item_value(declaration.tag)
        elif task.get("item") == declaration.smart_filter_item:
            replacement = text[span.offset : span.end]
        else:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} item differs from both "
                "the frozen and declared payloads"
            )
        originals[path] = original
        replacements.setdefault(path, []).append((span, replacement))

    for path, path_replacements in replacements.items():
        text = originals[path].decode("utf-8")
        candidate_bytes[path] = _replace_value_spans(text, path_replacements).encode("utf-8")

    chapters = _chapter_corpus(quest_root, candidate_bytes)
    corpus_ids = _collect_corpus_ids(chapters, link_chapters)
    collisions = corpus_ids & link_ids
    if collisions:
        raise ValueError(
            "quest link ID collides with existing corpus ID: "
            + ", ".join(sorted(collisions))
        )

    localization_entries = localization_overlays.overlays
    if localization_entries and localization_overlays.expected_outside_sha256 is None:
        raise ValueError("localization overlays require an outside-span SHA-256")
    if not localization_entries and localization_overlays.expected_outside_sha256 is not None:
        raise ValueError("empty localization overlays cannot declare an outside-span SHA-256")
    if localization_entries:
        localization_digest = _validated_sha256(
            localization_overlays.expected_outside_sha256,
            "legacy localization overlays",
        )
        story_quest_ids = {
            quest.get("id")
            for chapter in chapters.values()
            if chapter.get("group") == STORY_GROUP_ID
            for quest in chapter.get("quests", [])
            if isinstance(quest, Mapping) and isinstance(quest.get("id"), str)
        }
        seen_keys: set[str] = set()
        lang_path = quest_root / "lang" / "en_us.snbt"
        try:
            original = lang_path.read_bytes()
            text = original.decode("utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise ValueError(f"missing or unreadable localization target {lang_path}: {error}") from error
        lang_replacements: list[tuple[object, str]] = []
        lang_spans: list[object] = []
        for overlay in localization_entries:
            if overlay.key in seen_keys:
                raise ValueError(f"duplicate localization overlay key: {overlay.key}")
            seen_keys.add(overlay.key)
            quest_match = re.fullmatch(
                r"quest\.([0-9A-F]{16})\.(quest_subtitle|quest_desc)",
                overlay.key,
            )
            declared = overlay.key == f"chapter_group.{MANUAL_GROUP_ID}.title"
            declared = declared or (
                quest_match is not None and quest_match.group(1) in story_quest_ids
            )
            if not declared:
                raise ValueError(f"undeclared localization overlay key: {overlay.key}")
            try:
                span = _unique_top_level_value_span(text, overlay.key, lang_path)
            except ValueError as error:
                if str(error).startswith("missing top-level"):
                    raise ValueError(
                        f"missing localization key {overlay.key} in {lang_path}"
                    ) from error
                if str(error).startswith("duplicate top-level"):
                    raise ValueError(
                        f"duplicate localization key {overlay.key} in {lang_path}"
                    ) from error
                raise
            lang_spans.append(span)
            lang_replacements.append((span, _render_localization_value(overlay.value)))
        actual_digest = _outside_span_sha256(text, lang_spans)
        if actual_digest != localization_digest:
            raise ValueError(
                f"outside-span digest mismatch for {lang_path}: "
                f"expected {localization_digest}, found {actual_digest}"
            )
        candidate_bytes[lang_path] = _replace_value_spans(text, lang_replacements).encode("utf-8")
        originals[lang_path] = original

    final_chapters = _chapter_corpus(quest_root, candidate_bytes)
    _validate_story_group_orders(final_chapters)
    for path, chapter in final_chapters.items():
        expected_id = path.stem
        if chapter.get("id") != expected_id or chapter.get("filename") != expected_id:
            raise ValueError(
                f"legacy overlay chapter identity mismatch in {path}: "
                f"filename={chapter.get('filename')!r}, id={chapter.get('id')!r}"
            )
    for overlay in commodity_overlays:
        path = quest_root / "chapters" / f"{overlay.chapter_id}.snbt"
        chapter = final_chapters[path]
        declaration = commodity_declarations[overlay.declaration_key]
        matching_tasks = [
            task
            for quest in chapter.get("quests", [])
            if isinstance(quest, Mapping)
            for task in quest.get("tasks", [])
            if isinstance(task, Mapping) and task.get("id") == overlay.task_id
        ]
        if len(matching_tasks) != 1:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} is not unique after rendering"
            )
        final_task = matching_tasks[0]
        if final_task.get("item") != declaration.smart_filter_item:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} did not render its declared item"
            )
        if {
            key: value for key, value in final_task.items() if key != "item"
        } != {
            key: value
            for key, value in declaration.baseline_task.items()
            if key != "item"
        }:
            raise ValueError(
                f"commodity overlay task {overlay.task_id} fields outside item differ "
                "after rendering"
            )

    audit_path = (
        quest_root.parents[2]
        / "kubejs"
        / "server_scripts"
        / "afterlight"
        / "generated_quest_item_audit.js"
    )
    audit_original = audit_path.read_bytes() if audit_path.exists() else None
    candidate_bytes[audit_path] = _render_quest_item_audit(
        quest_root,
        candidate_bytes,
    ).encode("utf-8")
    expected_originals: dict[Path, bytes | None] = {
        path: originals[path]
        for path in candidate_bytes
        if path != audit_path
    }
    expected_originals[audit_path] = audit_original
    changed = [
        path
        for path in sorted(candidate_bytes)
        if expected_originals[path] != candidate_bytes[path]
    ]
    for path in changed:
        _atomic_write(path, candidate_bytes[path].decode("utf-8"))
    return changed


def _write_legacy_quest_overlays(
    quest_root: Path,
    *,
    link_overlays: Sequence[LegacyQuestLinkOverlay],
    order_overlays: Sequence[LegacyChapterOrderOverlay],
    localization_overlays: LegacyLocalizationManifest,
    commodity_overlays: Sequence[LegacyCommodityTaskOverlay],
    catalog: Sequence[ChapterSpec] | None = None,
    known_quest_ids: Iterable[str] | None = None,
    transaction: QuestBuildTransaction | None = None,
) -> list[Path]:
    repository_root = quest_root.parents[2]
    frozen_link_overlays = copy.deepcopy(tuple(link_overlays))
    frozen_order_overlays = copy.deepcopy(tuple(order_overlays))
    frozen_localization_overlays = copy.deepcopy(localization_overlays)
    frozen_commodity_overlays = copy.deepcopy(tuple(commodity_overlays))
    frozen_catalog = None if catalog is None else copy.deepcopy(tuple(catalog))
    frozen_known_ids = None if known_quest_ids is None else tuple(known_quest_ids)
    if transaction is None:
        with QuestBuildTransaction(repository_root) as owned_transaction:
            return _write_legacy_quest_overlays(
                quest_root,
                link_overlays=frozen_link_overlays,
                order_overlays=frozen_order_overlays,
                localization_overlays=frozen_localization_overlays,
                commodity_overlays=frozen_commodity_overlays,
                catalog=frozen_catalog,
                known_quest_ids=frozen_known_ids,
                transaction=owned_transaction,
            )
    transaction.require_root(repository_root)
    if transaction.is_workspace(repository_root):
        return _apply_legacy_quest_overlays_workspace(
            quest_root,
            link_overlays=frozen_link_overlays,
            order_overlays=frozen_order_overlays,
            localization_overlays=frozen_localization_overlays,
            commodity_overlays=frozen_commodity_overlays,
            catalog=frozen_catalog,
            known_quest_ids=frozen_known_ids,
        )
    frozen = transaction.freeze(quest_build_dependency_roots(repository_root))
    audit_path = (
        repository_root
        / "kubejs"
        / "server_scripts"
        / "afterlight"
        / "generated_quest_item_audit.js"
    )
    with candidate_workspace(transaction, frozen) as candidate_root:
        candidate_quest_root = (
            candidate_root / quest_root.relative_to(repository_root)
        )
        _apply_legacy_quest_overlays_workspace(
            candidate_quest_root,
            link_overlays=frozen_link_overlays,
            order_overlays=frozen_order_overlays,
            localization_overlays=frozen_localization_overlays,
            commodity_overlays=frozen_commodity_overlays,
            catalog=frozen_catalog,
            known_quest_ids=frozen_known_ids,
        )
        writes, deletions = frozen.candidate_changes(
            candidate_root,
            (quest_root, audit_path),
        )
    return transaction.promote_bytes(writes, frozen, deletions=deletions)


def write_legacy_quest_overlays(
    quest_root: Path,
    *,
    catalog: Sequence[ChapterSpec] | None = None,
    known_quest_ids: Iterable[str] | None = None,
    transaction: QuestBuildTransaction | None = None,
) -> list[Path]:
    return _write_legacy_quest_overlays(
        quest_root,
        link_overlays=LEGACY_QUEST_LINK_OVERLAYS,
        order_overlays=LEGACY_CHAPTER_ORDER_OVERLAYS,
        localization_overlays=LEGACY_LOCALIZATION_OVERLAYS,
        commodity_overlays=LEGACY_COMMODITY_TASK_OVERLAYS,
        catalog=catalog,
        known_quest_ids=known_quest_ids,
        transaction=transaction,
    )
