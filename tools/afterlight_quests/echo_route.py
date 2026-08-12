from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .builder import HEX_ID, _parse_snbt


STORY_GROUP_ID = "4525BB3160467FCB"
RECOVERY_CHAPTER_ID = "6C40000000000001"
RECOVERY_QUEST_ID = "6C40000000000002"
FAR_RELAY_QUEST_ID = "6C40000000000101"
TERMINAL_QUEST_ID = "31C9557D2F51238F"
AFTERLIGHT_CHAPTER_ID = "245BADE04399406C"
AFTERLIGHT_ROUTE = (
    "51649E106286AA63",
    "1B523415541BD700",
    "7EE7B9B28787F8CC",
    "7E6A0AC031F7F484",
    "7ECCF0521DFCBED5",
    "4DD9F3D1913499F3",
)


def _segment_id(title: str) -> str:
    identifier = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    if not identifier:
        raise ValueError(f"story chapter title has no route-safe characters: {title!r}")
    return identifier


def _story_chapters(quest_root: Path) -> list[dict[str, Any]]:
    language = _parse_snbt(
        (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8")
    )
    chapters: list[dict[str, Any]] = []
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        chapter = _parse_snbt(path.read_text(encoding="utf-8"))
        if chapter.get("group") != STORY_GROUP_ID:
            continue
        if chapter.get("id") == RECOVERY_CHAPTER_ID:
            continue
        chapter_id = chapter.get("id")
        title = language.get(f"chapter.{chapter_id}.title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"story chapter {chapter_id} has no localized title")
        chapters.append(
            {
                "id": chapter_id,
                "title": title,
                "order": int(chapter["order_index"]),
                "quests": [quest["id"] for quest in chapter["quests"]],
            }
        )
    chapters.sort(key=lambda chapter: (chapter["order"], chapter["id"]))
    return chapters


def build_echo_route(quest_root: Path) -> dict[str, Any]:
    segments: list[dict[str, Any]] = []
    previous: str | None = None
    for chapter in _story_chapters(quest_root):
        segment_id = _segment_id(chapter["title"])
        quest_ids = (
            list(AFTERLIGHT_ROUTE)
            if chapter["id"] == AFTERLIGHT_CHAPTER_ID
            else list(chapter["quests"])
        )
        segments.append(
            {
                "id": segment_id,
                "after": [] if previous is None else [previous],
                "quests": quest_ids,
            }
        )
        previous = segment_id
    route = {
        "schema": 1,
        "terminal_quest": TERMINAL_QUEST_ID,
        "segments": segments,
    }
    errors = validate_echo_route(route, quest_root)
    if errors:
        raise ValueError("invalid ECHO route:\n" + "\n".join(errors))
    return route


def validate_echo_route(route: dict[str, Any], quest_root: Path) -> list[str]:
    errors: list[str] = []
    if route.get("schema") != 1:
        errors.append("schema must be 1")
    if route.get("terminal_quest") != TERMINAL_QUEST_ID:
        errors.append(f"terminal_quest must be {TERMINAL_QUEST_ID}")

    corpus_ids = {
        quest["id"]
        for path in sorted((quest_root / "chapters").glob("*.snbt"))
        for quest in _parse_snbt(path.read_text(encoding="utf-8")).get("quests", [])
    }
    segments = route.get("segments")
    if not isinstance(segments, list) or not segments:
        return [*errors, "segments must be a non-empty list"]

    seen_segments: set[str] = set()
    seen_quests: set[str] = set()
    previous: str | None = None
    for index, segment in enumerate(segments):
        if not isinstance(segment, dict):
            errors.append(f"segments[{index}] must be an object")
            continue
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not re.fullmatch(r"[a-z0-9_]+", segment_id):
            errors.append(f"segments[{index}].id is invalid")
            continue
        if segment_id in seen_segments:
            errors.append(f"duplicate segment ID {segment_id}")
        seen_segments.add(segment_id)
        expected_after = [] if previous is None else [previous]
        if segment.get("after") != expected_after:
            errors.append(f"segment {segment_id} must follow {expected_after}")
        previous = segment_id

        quest_ids = segment.get("quests")
        if not isinstance(quest_ids, list) or not quest_ids:
            errors.append(f"segment {segment_id} must contain quests")
            continue
        for quest_id in quest_ids:
            if not isinstance(quest_id, str) or not HEX_ID.fullmatch(quest_id):
                errors.append(f"segment {segment_id} has malformed quest ID {quest_id!r}")
                continue
            if quest_id in seen_quests:
                errors.append(f"duplicate route quest ID {quest_id}")
            seen_quests.add(quest_id)
            if quest_id not in corpus_ids:
                errors.append(f"route quest {quest_id} is absent from the quest corpus")

    if RECOVERY_QUEST_ID in seen_quests:
        errors.append("recovery quest must not enter normal recommendation order")
    if TERMINAL_QUEST_ID not in seen_quests:
        errors.append("terminal quest is absent from route")
    if FAR_RELAY_QUEST_ID not in seen_quests:
        errors.append("Far Relay quest is absent from route")
    if segments[-1].get("id") != "beyond_afterlight":
        errors.append("postgame must be the final optional route segment")
    return errors


def render_echo_route(route: dict[str, Any]) -> str:
    return json.dumps(route, indent=2, ensure_ascii=False) + "\n"


def write_echo_route(quest_root: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{output.name}.", suffix=".tmp", dir=output.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(render_echo_route(build_echo_route(quest_root)))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
