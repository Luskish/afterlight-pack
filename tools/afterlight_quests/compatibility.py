from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .builder import _parse_snbt


STORY_GROUP_ID = "4A20F33642175B95"
FILTER_ITEM_ID = "ftbfiltersystem:smart_filter"
FILTER_COMPONENT = "ftbfiltersystem:filter"
TAG_PATTERN = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
UUID_PATTERN = re.compile(
    r"(?i)(?<![0-9a-f])[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-"
    r"[0-9a-f]{12}(?![0-9a-f])"
)
WINDOWS_PATH_PATTERN = re.compile(
    r"(?i)(?:(?:^|[^a-z0-9])[a-z]:[\\/]"
    r"|(?:^|[^\\])\\\\[^\\/\s]+\\[^\\/\s]+)"
)
UNIX_ROOT_PATTERN = re.compile(
    r"(?:^|[^A-Za-z0-9])/(?:Users|home|private|tmp|var/(?:tmp|folders)|"
    r"etc|opt|root)(?:/|$)"
)
PRIVATE_IDENTITY_FIELDS = {
    "player",
    "player_id",
    "player_name",
    "player_uuid",
    "playername",
    "players",
    "username",
    "uuid",
}
RAW_PROGRESS_FIELDS = {
    "claimed_rewards",
    "claims",
    "completed",
    "completion_count",
    "last_updated",
    "pins",
    "player_data",
    "progress",
    "progress_value",
    "repeatable",
    "started",
    "task_progress",
    "timestamp",
}
SECRET_FIELDS = {
    "access_key",
    "access_token",
    "api_key",
    "auth_token",
    "password",
    "private_key",
    "secret",
    "secret_key",
    "token",
}
SECRET_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?<![A-Z0-9])AKIA[0-9A-Z]{16}(?![A-Z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])gh[pousr]_[A-Za-z0-9]{20,}"),
)
EM_DASH = chr(0x2014)


@dataclass(frozen=True)
class _Identity:
    kind: str
    identifier: str
    path: str
    value: Mapping[str, object]


@dataclass(frozen=True)
class _IdentityCatalog:
    by_id: dict[str, _Identity]
    errors: tuple[str, ...]


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


def _story_localization_change_paths(corpus: Mapping[str, object]) -> set[str]:
    allowed = {
        f"$.language.en_us.chapter_group.{STORY_GROUP_ID}.title",
    }
    chapters = corpus.get("chapters")
    if not isinstance(chapters, Mapping):
        return allowed
    for chapter in chapters.values():
        if not isinstance(chapter, Mapping) or chapter.get("group") != STORY_GROUP_ID:
            continue
        quests = chapter.get("quests")
        if not isinstance(quests, list):
            continue
        for quest in quests:
            if not isinstance(quest, Mapping) or not isinstance(quest.get("id"), str):
                continue
            quest_id = quest["id"]
            allowed.add(f"$.language.en_us.quest.{quest_id}.quest_subtitle")
            allowed.add(f"$.language.en_us.quest.{quest_id}.quest_desc")
    return allowed


def _hygiene_errors(corpus: Mapping[str, object], label: str) -> list[str]:
    errors: list[str] = []

    def inspect_text(value: str, path: str) -> None:
        if UUID_PATTERN.search(value):
            errors.append(f"{path}: {label} corpus contains a UUID")
        if EM_DASH in value:
            errors.append(f"{path}: {label} corpus contains U+2014")
        if WINDOWS_PATH_PATTERN.search(value):
            errors.append(f"{path}: {label} corpus contains a Windows machine path")
        if UNIX_ROOT_PATTERN.search(value):
            errors.append(f"{path}: {label} corpus contains a Unix machine root")
        if any(pattern.search(value) for pattern in SECRET_VALUE_PATTERNS):
            errors.append(f"{path}: {label} corpus contains a secret value")

    def visit(value: object, path: str) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}"
                normalized_key = str(key).casefold().replace("-", "_")
                if normalized_key in PRIVATE_IDENTITY_FIELDS:
                    errors.append(
                        f"{child_path}: {label} corpus contains a player identity field"
                    )
                if normalized_key in RAW_PROGRESS_FIELDS:
                    errors.append(
                        f"{child_path}: {label} corpus contains a raw progress field"
                    )
                if normalized_key in SECRET_FIELDS:
                    errors.append(
                        f"{child_path}: {label} corpus contains a secret field"
                    )
                inspect_text(str(key), child_path)
                visit(child, child_path)
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, f"{path}[{index}]")
            return
        if isinstance(value, str):
            inspect_text(value, path)

    visit(corpus, "$")
    return errors


def _checked_corpus(
    value: Mapping[str, object], label: str
) -> tuple[dict[str, object], list[str]]:
    errors = _hygiene_errors(value, label)
    return _unwrap_corpus(value), errors


def _identity_catalog(corpus: Mapping[str, object], label: str) -> _IdentityCatalog:
    by_id: dict[str, _Identity] = {}
    errors: list[str] = []

    def record(kind: str, value: object, path: str) -> Mapping[str, object] | None:
        if not isinstance(value, Mapping):
            errors.append(f"{path}: {label} {kind} member must be a mapping")
            return None
        identifier = value.get("id")
        identity_path = f"{path}.id"
        if identifier is None:
            errors.append(f"{identity_path}: {label} {kind} identity is missing")
            return value
        if not isinstance(identifier, str) or not identifier:
            errors.append(
                f"{identity_path}: {label} {kind} identity must be a non-empty string"
            )
            return value
        identity = _Identity(kind, identifier, path, value)
        prior = by_id.get(identifier)
        if prior is None:
            by_id[identifier] = identity
        elif prior.kind == kind:
            errors.append(
                f"{identity_path}: {label} duplicate {kind} ID "
                f"{_render_value(identifier)}; first defined at {prior.path}.id"
            )
        else:
            errors.append(
                f"{identity_path}: {label} cross-kind ID collision for "
                f"{_render_value(identifier)}; {kind} conflicts with {prior.kind} "
                f"at {prior.path}.id"
            )
        return value

    def visit_list(
        values: object,
        path: str,
        kind: str,
        member_visitor: Any = None,
    ) -> None:
        if not isinstance(values, list):
            return
        for index, value in enumerate(values):
            member_path = f"{path}[{index}]"
            member = record(kind, value, member_path)
            if member is not None and member_visitor is not None:
                member_visitor(member, member_path)

    def visit_rewards(values: object, path: str, kind: str) -> None:
        def visit_reward(reward: Mapping[str, object], reward_path: str) -> None:
            table_data = reward.get("table_data")
            if not isinstance(table_data, Mapping):
                return
            visit_rewards(
                table_data.get("rewards"),
                f"{reward_path}.table_data.rewards",
                "reward_table_reward",
            )

        visit_list(values, path, kind, visit_reward)

    def visit_quest(quest: Mapping[str, object], quest_path: str) -> None:
        visit_list(quest.get("tasks"), f"{quest_path}.tasks", "task")
        visit_rewards(quest.get("rewards"), f"{quest_path}.rewards", "reward")

    def visit_chapter(chapter: Mapping[str, object], chapter_path: str) -> None:
        visit_list(chapter.get("images"), f"{chapter_path}.images", "image")
        visit_list(
            chapter.get("quest_links"),
            f"{chapter_path}.quest_links",
            "quest_link",
        )
        visit_list(
            chapter.get("quests"),
            f"{chapter_path}.quests",
            "quest",
            visit_quest,
        )

    chapter_groups = corpus.get("chapter_groups")
    if isinstance(chapter_groups, Mapping):
        visit_list(
            chapter_groups.get("chapter_groups"),
            "$.chapter_groups.chapter_groups",
            "chapter_group",
        )

    chapters = corpus.get("chapters")
    if isinstance(chapters, Mapping):
        for chapter_name in sorted(chapters):
            chapter_path = f"$.chapters.{chapter_name}"
            chapter = record("chapter", chapters[chapter_name], chapter_path)
            if chapter is not None:
                visit_chapter(chapter, chapter_path)

    reward_tables = corpus.get("reward_tables")
    if isinstance(reward_tables, Mapping):
        for table_name in sorted(reward_tables):
            table_path = f"$.reward_tables.{table_name}"
            table = record("reward_table", reward_tables[table_name], table_path)
            if table is not None:
                visit_rewards(
                    table.get("rewards"),
                    f"{table_path}.rewards",
                    "reward_table_reward",
                )

    return _IdentityCatalog(by_id, tuple(errors))


def _commodity_declarations(
    commodity_replacements: Mapping[str, str],
) -> tuple[dict[str, str], list[str]]:
    declarations: dict[str, str] = {}
    errors: list[str] = []
    for task_id, tag in commodity_replacements.items():
        declaration_path = f"$.commodity_replacements.{task_id}"
        if task_id in declarations:
            errors.append(f"{declaration_path}: duplicate commodity declaration")
            continue
        declarations[task_id] = tag
    return declarations, errors


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
    baseline_corpus, baseline_hygiene_errors = _checked_corpus(
        baseline, "baseline"
    )
    current_corpus, current_hygiene_errors = _checked_corpus(current, "current")
    allowed_localization_changes = _story_localization_change_paths(baseline_corpus)
    baseline_catalog = _identity_catalog(baseline_corpus, "baseline")
    current_catalog = _identity_catalog(current_corpus, "current")
    declarations, declaration_errors = _commodity_declarations(
        commodity_replacements
    )
    errors = [
        *baseline_hygiene_errors,
        *current_hygiene_errors,
        *baseline_catalog.errors,
        *current_catalog.errors,
        *declaration_errors,
    ]

    for identifier, current_identity in current_catalog.by_id.items():
        baseline_identity = baseline_catalog.by_id.get(identifier)
        if baseline_identity is None or baseline_identity.kind == current_identity.kind:
            continue
        errors.append(
            f"{current_identity.path}.id: current {current_identity.kind} reuses "
            f"baseline {baseline_identity.kind} ID {_render_value(identifier)} "
            f"from {baseline_identity.path}.id"
        )

    for task_id, tag in sorted(declarations.items()):
        identity = baseline_catalog.by_id.get(task_id)
        declaration_path = f"$.commodity_replacements.{task_id}"
        if identity is None:
            errors.append(f"{declaration_path}: baseline task does not exist")
        elif identity.kind != "task" or identity.value.get("type") != "item":
            errors.append(f"{declaration_path}: baseline task is not an item task")
        elif not isinstance(tag, str) or not TAG_PATTERN.fullmatch(tag):
            errors.append(
                f"{declaration_path}: invalid item tag {_render_value(tag)}"
            )

    def compare_entity_list(
        expected: object,
        actual: object,
        path: str,
        kind: str,
        role: str,
    ) -> None:
        if not isinstance(expected, list):
            errors.append(f"{path}: baseline {kind} collection is not a list")
            return
        if not isinstance(actual, list):
            errors.append(f"{path}: expected list, found {_render_value(actual)}")
            return

        def index_members(
            members: list[object],
        ) -> tuple[dict[str, tuple[Mapping[str, object], str]], list[str]]:
            indexed: dict[str, tuple[Mapping[str, object], str]] = {}
            identifiers: list[str] = []
            for index, member in enumerate(members):
                if not isinstance(member, Mapping):
                    continue
                identifier = member.get("id")
                if not isinstance(identifier, str) or not identifier:
                    continue
                identifiers.append(identifier)
                indexed.setdefault(identifier, (member, f"{path}[{index}]"))
            return indexed, identifiers

        expected_index, expected_ids = index_members(expected)
        actual_index, actual_ids = index_members(actual)
        all_frozen_present = True
        for identifier in expected_ids:
            expected_member, expected_path = expected_index[identifier]
            current_member = actual_index.get(identifier)
            if current_member is None:
                all_frozen_present = False
                errors.append(
                    f"{expected_path}.id: frozen {kind} ID "
                    f"{_render_value(identifier)} is missing from current "
                    f"collection {path}"
                )
                continue
            actual_member, actual_path = current_member
            compare_value(
                expected_member,
                actual_member,
                actual_path,
                role=role,
            )

        if all_frozen_present:
            frozen_ids = set(expected_ids)
            actual_frozen_ids = [
                identifier for identifier in actual_ids if identifier in frozen_ids
            ]
            if actual_frozen_ids != expected_ids:
                errors.append(
                    f"{path}: frozen ID relative order changed for {kind}; "
                    f"expected {_render_value(expected_ids)}, found "
                    f"{_render_value(actual_frozen_ids)}"
                )

    def compare_entity_mapping(
        expected: object,
        actual: object,
        path: str,
        kind: str,
        role: str,
    ) -> None:
        if not isinstance(expected, Mapping):
            errors.append(f"{path}: baseline {kind} collection is not a mapping")
            return
        if not isinstance(actual, Mapping):
            errors.append(f"{path}: expected mapping, found {_render_value(actual)}")
            return

        def index_members(
            members: Mapping[str, object],
        ) -> dict[str, tuple[Mapping[str, object], str]]:
            indexed: dict[str, tuple[Mapping[str, object], str]] = {}
            for name, member in members.items():
                if not isinstance(member, Mapping):
                    continue
                identifier = member.get("id")
                if not isinstance(identifier, str) or not identifier:
                    continue
                indexed.setdefault(identifier, (member, f"{path}.{name}"))
            return indexed

        expected_index = index_members(expected)
        actual_index = index_members(actual)
        for identifier, (expected_member, expected_path) in expected_index.items():
            current_member = actual_index.get(identifier)
            if current_member is None:
                errors.append(
                    f"{expected_path}.id: frozen {kind} ID "
                    f"{_render_value(identifier)} is missing from current "
                    f"collection {path}"
                )
                continue
            actual_member, actual_path = current_member
            compare_value(
                expected_member,
                actual_member,
                actual_path,
                role=role,
            )

    def compare_value(
        expected: object,
        actual: object,
        path: str,
        *,
        role: str = "generic",
        parent_expected: Mapping[str, object] | None = None,
    ) -> None:
        if path in allowed_localization_changes:
            return

        is_task_item = (
            role == "generic"
            and ".tasks[" in path
            and path.endswith(".item")
            and parent_expected is not None
            and parent_expected.get("type") == "item"
            and isinstance(parent_expected.get("id"), str)
        )
        if is_task_item and expected != actual:
            task_id = parent_expected["id"]
            tag = declarations.get(task_id)
            if isinstance(tag, str) and _commodity_item(expected, actual, tag):
                return
            errors.append(
                f"{path}: item target changed without an exact declared "
                "commodity filter"
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
                if role == "corpus" and key == "chapters":
                    compare_entity_mapping(
                        expected[key], actual[key], child_path, "chapter", "chapter"
                    )
                    continue
                if role == "corpus" and key == "reward_tables":
                    compare_entity_mapping(
                        expected[key],
                        actual[key],
                        child_path,
                        "reward_table",
                        "reward_table",
                    )
                    continue
                if role == "chapter_group_registry" and key == "chapter_groups":
                    compare_entity_list(
                        expected[key],
                        actual[key],
                        child_path,
                        "chapter_group",
                        "chapter_group",
                    )
                    continue
                if role == "chapter" and key == "images":
                    compare_entity_list(
                        expected[key], actual[key], child_path, "image", "image"
                    )
                    continue
                if role == "chapter" and key == "quest_links":
                    compare_entity_list(
                        expected[key],
                        actual[key],
                        child_path,
                        "quest_link",
                        "quest_link",
                    )
                    continue
                if role == "chapter" and key == "quests":
                    compare_entity_list(
                        expected[key], actual[key], child_path, "quest", "quest"
                    )
                    continue
                if role == "quest" and key == "tasks":
                    compare_entity_list(
                        expected[key], actual[key], child_path, "task", "task"
                    )
                    continue
                if role == "quest" and key == "rewards":
                    compare_entity_list(
                        expected[key], actual[key], child_path, "reward", "reward"
                    )
                    continue
                if role in {"reward_table", "reward_table_data"} and key == "rewards":
                    compare_entity_list(
                        expected[key],
                        actual[key],
                        child_path,
                        "reward_table_reward",
                        "reward_table_reward",
                    )
                    continue
                if (
                    role in {"reward", "reward_table_reward"}
                    and key == "table_data"
                ):
                    compare_value(
                        expected[key],
                        actual[key],
                        child_path,
                        role="reward_table_data",
                    )
                    continue

                child_role = "generic"
                if role == "corpus" and key == "chapter_groups":
                    child_role = "chapter_group_registry"
                elif role == "corpus" and key == "language":
                    child_role = "language"
                elif role == "language" and key == "en_us":
                    child_role = "language_entries"
                if (
                    role == "chapter"
                    and key == "order_index"
                    and expected.get("group") == STORY_GROUP_ID
                ):
                    continue
                compare_value(
                    expected[key],
                    actual[key],
                    child_path,
                    role=child_role,
                    parent_expected=expected,
                )
            if role != "language_entries":
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
            for index in range(shared_length, len(actual)):
                errors.append(f"{path}[{index}]: unexpected current value")
            return

        if type(expected) is not type(actual) or expected != actual:
            errors.append(
                f"{path}: expected {_render_value(expected)}, found "
                f"{_render_value(actual)}"
            )

    compare_value(baseline_corpus, current_corpus, "$", role="corpus")
    return errors
