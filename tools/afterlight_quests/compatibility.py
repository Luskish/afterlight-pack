from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .builder import _parse_snbt


STORY_GROUP_ID = "4A20F33642175B95"
FILTER_ITEM_ID = "ftbfiltersystem:smart_filter"
FILTER_COMPONENT = "ftbfiltersystem:filter"
TAG_PATTERN = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")


def _canonicalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize(value[key])
            for key in sorted(value, key=lambda candidate: str(candidate))
        }
    if isinstance(value, list):
        return [_canonicalize(item) for item in value]
    return value


def _read_snbt(path: Path) -> object:
    if not path.is_file():
        raise FileNotFoundError(path)
    return _canonicalize(_parse_snbt(path.read_text(encoding="utf-8")))


def capture_quest_corpus(quest_root: Path) -> dict[str, object]:
    quest_root = Path(quest_root)
    chapters = {
        path.name: _read_snbt(path)
        for path in sorted((quest_root / "chapters").glob("*.snbt"))
    }
    reward_tables = {
        path.name: _read_snbt(path)
        for path in sorted((quest_root / "reward_tables").glob("*.snbt"))
    }
    corpus = {
        "chapter_groups": _read_snbt(quest_root / "chapter_groups.snbt"),
        "chapters": chapters,
        "language": {
            "en_us": _read_snbt(quest_root / "lang" / "en_us.snbt"),
        },
        "reward_tables": reward_tables,
    }
    return _canonicalize(corpus)


def _unwrap_corpus(value: Mapping[str, object]) -> dict[str, object]:
    corpus = value.get("corpus")
    if isinstance(corpus, Mapping):
        return _canonicalize(corpus)
    return _canonicalize(value)


def _render_value(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _story_change_paths(corpus: Mapping[str, object]) -> set[str]:
    allowed = {
        f"$.language.en_us.chapter_group.{STORY_GROUP_ID}.title",
    }
    chapters = corpus.get("chapters")
    if not isinstance(chapters, Mapping):
        return allowed
    for chapter_name, chapter_value in chapters.items():
        if not isinstance(chapter_value, Mapping):
            continue
        if chapter_value.get("group") != STORY_GROUP_ID:
            continue
        allowed.add(f"$.chapters.{chapter_name}.order_index")
        quests = chapter_value.get("quests")
        if not isinstance(quests, list):
            continue
        for quest in quests:
            if not isinstance(quest, Mapping) or not isinstance(quest.get("id"), str):
                continue
            quest_id = quest["id"]
            allowed.add(f"$.language.en_us.quest.{quest_id}.quest_subtitle")
            allowed.add(f"$.language.en_us.quest.{quest_id}.quest_desc")
    return allowed


def _task_ids(corpus: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    tasks: dict[str, Mapping[str, object]] = {}
    chapters = corpus.get("chapters")
    if not isinstance(chapters, Mapping):
        return tasks
    for chapter in chapters.values():
        if not isinstance(chapter, Mapping):
            continue
        quests = chapter.get("quests")
        if not isinstance(quests, list):
            continue
        for quest in quests:
            if not isinstance(quest, Mapping):
                continue
            quest_tasks = quest.get("tasks")
            if not isinstance(quest_tasks, list):
                continue
            for task in quest_tasks:
                if isinstance(task, Mapping) and isinstance(task.get("id"), str):
                    tasks[task["id"]] = task
    return tasks


def _is_additive_mapping(path: str) -> bool:
    return path in {"$.chapters", "$.language.en_us", "$.reward_tables"}


def _is_additive_list(path: str) -> bool:
    return (
        path == "$.chapter_groups.chapter_groups"
        or path.endswith(".quest_links")
        or path.endswith(".quests")
        or path.endswith(".tasks")
        or path.endswith(".rewards")
    )


def _commodity_item(
    baseline: object,
    current: object,
    tag: str,
) -> bool:
    if not TAG_PATTERN.fullmatch(tag):
        return False
    if not isinstance(baseline, Mapping) or not isinstance(current, Mapping):
        return False
    if set(baseline) - {"count", "id"}:
        return False
    baseline_id = baseline.get("id")
    if not isinstance(baseline_id, str) or baseline_id == FILTER_ITEM_ID:
        return False
    expected: dict[str, object] = {
        "id": FILTER_ITEM_ID,
        "components": {
            FILTER_COMPONENT: f"ftbfiltersystem:item_tag({tag})",
        },
    }
    if "count" in baseline:
        expected["count"] = baseline["count"]
    return current == _canonicalize(expected)


def compare_quest_corpus(
    baseline: Mapping[str, object],
    current: Mapping[str, object],
    *,
    commodity_replacements: Mapping[str, str],
) -> list[str]:
    baseline_corpus = _unwrap_corpus(baseline)
    current_corpus = _unwrap_corpus(current)
    allowed_changes = _story_change_paths(baseline_corpus)
    baseline_tasks = _task_ids(baseline_corpus)
    errors: list[str] = []

    for task_id, tag in sorted(commodity_replacements.items()):
        task = baseline_tasks.get(task_id)
        if task is None:
            errors.append(
                f"$.commodity_replacements.{task_id}: baseline task does not exist"
            )
        elif task.get("type") != "item":
            errors.append(
                f"$.commodity_replacements.{task_id}: baseline task is not an item task"
            )
        elif not isinstance(tag, str) or not TAG_PATTERN.fullmatch(tag):
            errors.append(
                f"$.commodity_replacements.{task_id}: invalid item tag {_render_value(tag)}"
            )

    def compare_value(
        expected: object,
        actual: object,
        path: str,
        *,
        parent_expected: Mapping[str, object] | None = None,
    ) -> None:
        if path in allowed_changes:
            return

        is_task_item = (
            ".tasks[" in path
            and path.endswith(".item")
            and parent_expected is not None
            and parent_expected.get("type") == "item"
            and isinstance(parent_expected.get("id"), str)
        )
        if is_task_item and expected != actual:
            task_id = parent_expected["id"]
            tag = commodity_replacements.get(task_id)
            if isinstance(tag, str) and _commodity_item(expected, actual, tag):
                return
            errors.append(
                f"{path}: item target changed without an exact declared commodity filter"
            )
            return

        if isinstance(expected, Mapping):
            if not isinstance(actual, Mapping):
                errors.append(
                    f"{path}: expected mapping, found {_render_value(actual)}"
                )
                return
            for key in expected:
                child_path = f"{path}.{key}"
                if key not in actual:
                    errors.append(f"{child_path}: missing current value")
                    continue
                compare_value(
                    expected[key],
                    actual[key],
                    child_path,
                    parent_expected=expected,
                )
            if not _is_additive_mapping(path):
                for key in actual:
                    if key not in expected:
                        errors.append(f"{path}.{key}: unexpected current value")
            return

        if isinstance(expected, list):
            if not isinstance(actual, list):
                errors.append(f"{path}: expected list, found {_render_value(actual)}")
                return
            shared_length = min(len(expected), len(actual))
            for index in range(shared_length):
                compare_value(
                    expected[index],
                    actual[index],
                    f"{path}[{index}]",
                )
            for index in range(shared_length, len(expected)):
                errors.append(f"{path}[{index}]: missing current value")
            if not _is_additive_list(path):
                for index in range(shared_length, len(actual)):
                    errors.append(f"{path}[{index}]: unexpected current value")
            return

        if type(expected) is not type(actual) or expected != actual:
            errors.append(
                f"{path}: expected {_render_value(expected)}, found {_render_value(actual)}"
            )

    compare_value(baseline_corpus, current_corpus, "$")
    return errors
