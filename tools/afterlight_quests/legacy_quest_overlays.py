from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .builder import (
    ChapterSpec,
    QuestLinkSpec,
    SnbtParseError,
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


LEGACY_QUEST_LINK_OVERLAYS = (
    LegacyQuestLinkOverlay(
        chapter_id="4C01977EF77930A6",
        expected_outside_sha256="84b682eb046cc73a8e1962ae7b98a37a3323a5d035054e372b919a43de7b3729",
        quest_links=(),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="770DAD173D9C234B",
        expected_outside_sha256="3cca17187e1382064192ea9235b0679590fc844954b689d413aad90cd84adb7e",
        quest_links=(),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="45491A24F6B8C192",
        expected_outside_sha256="ae8fe08053a769600b8d416bebb679b1731b0680a87f164e694ee861c533b139",
        quest_links=(),
    ),
    LegacyQuestLinkOverlay(
        chapter_id="52EF477C2D995F40",
        expected_outside_sha256="874388f975a02bda088fcb30650bb03c15935a98b3c2e85453ebf86bc4bd2df0",
        quest_links=(),
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
    expected_outside_sha256=None,
    overlays=(),
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


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_staged_file(path: Path, payload: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as output:
        output.write(payload)
        output.flush()
        os.fsync(output.fileno())
    os.chmod(path, mode)


def _replace_overlay_file(staged: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(staged, target)
    _fsync_directory(target.parent)


def _commit_overlay_writes(
    writes: Mapping[Path, bytes],
    expected_originals: Mapping[Path, bytes | None],
) -> list[Path]:
    if set(writes) != set(expected_originals):
        raise ValueError("legacy overlay write set does not match preflight originals")
    for path, expected in expected_originals.items():
        current = path.read_bytes() if path.exists() else None
        if current != expected:
            raise ValueError(f"legacy overlay target changed after preflight: {path}")
    changed = [
        path
        for path in sorted(writes)
        if expected_originals[path] != writes[path]
    ]
    if not changed:
        return []

    originals = {path: expected_originals[path] for path in changed}
    modes = {
        path: stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
        for path in changed
    }
    repo_root = next(iter(changed)).parents[3]
    transaction = Path(tempfile.mkdtemp(prefix=".legacy-overlay-", dir=repo_root))
    staged_paths: dict[Path, Path] = {}
    backup_paths: dict[Path, Path] = {}
    attempted: list[Path] = []
    try:
        for index, path in enumerate(changed):
            staged = transaction / "staged" / str(index)
            _write_staged_file(staged, writes[path], modes[path])
            staged_paths[path] = staged
            if originals[path] is not None:
                backup = transaction / "backup" / str(index)
                _write_staged_file(backup, originals[path], modes[path])
                backup_paths[path] = backup

        for path in changed:
            current = path.read_bytes() if path.exists() else None
            if current != originals[path]:
                raise ValueError(f"legacy overlay target changed after preflight: {path}")

        for path in changed:
            attempted.append(path)
            _replace_overlay_file(staged_paths[path], path)
    except BaseException as error:
        rollback_errors: list[BaseException] = []
        for path in reversed(attempted):
            try:
                if originals[path] is None:
                    path.unlink(missing_ok=True)
                    _fsync_directory(path.parent)
                else:
                    os.replace(backup_paths[path], path)
                    _fsync_directory(path.parent)
            except BaseException as rollback_error:
                rollback_errors.append(rollback_error)
        if rollback_errors:
            raise RuntimeError(
                f"legacy overlay rollback failed after {error}: {rollback_errors}"
            ) from error
        raise
    finally:
        shutil.rmtree(transaction, ignore_errors=True)
    return changed


def _write_legacy_quest_overlays(
    quest_root: Path,
    *,
    link_overlays: Sequence[LegacyQuestLinkOverlay],
    order_overlays: Sequence[LegacyChapterOrderOverlay],
    localization_overlays: LegacyLocalizationManifest,
    catalog: Sequence[ChapterSpec] | None = None,
    known_quest_ids: Iterable[str] | None = None,
) -> list[Path]:
    if catalog is None and known_quest_ids is None:
        raise ValueError(
            "legacy overlays require a complete managed catalog or exact known quest ID universe"
        )
    known_ids = _validated_legacy_quest_ids(known_quest_ids or ())
    managed_catalog = tuple(catalog or ())
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
            raise ValueError(
                f"outside-span digest mismatch for {path}: "
                f"expected {overlay.expected_outside_sha256}, found {actual_digest}"
            )
        originals[path] = original
        replacements.setdefault(path, []).append((span, str(overlay.order_index)))

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
    return _commit_overlay_writes(candidate_bytes, expected_originals)


def write_legacy_quest_overlays(
    quest_root: Path,
    *,
    catalog: Sequence[ChapterSpec] | None = None,
    known_quest_ids: Iterable[str] | None = None,
) -> list[Path]:
    return _write_legacy_quest_overlays(
        quest_root,
        link_overlays=LEGACY_QUEST_LINK_OVERLAYS,
        order_overlays=LEGACY_CHAPTER_ORDER_OVERLAYS,
        localization_overlays=LEGACY_LOCALIZATION_OVERLAYS,
        catalog=catalog,
        known_quest_ids=known_quest_ids,
    )
