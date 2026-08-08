from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HEX_ID = re.compile(r"^[0-9A-F]{16}$")
RESOURCE_ID = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")

VANILLA_ITEM_ALLOWLIST = frozenset(
    {
        "minecraft:blast_furnace",
        "minecraft:bread",
        "minecraft:chiseled_tuff_bricks",
        "minecraft:crafting_table",
        "minecraft:diamond",
        "minecraft:enchanted_golden_apple",
        "minecraft:experience_bottle",
        "minecraft:golden_apple",
        "minecraft:iron_block",
        "minecraft:iron_ingot",
        "minecraft:netherite_scrap",
        "minecraft:netherrack",
        "minecraft:oak_planks",
        "minecraft:recovery_compass",
        "minecraft:red_bed",
        "minecraft:redstone",
        "minecraft:redstone_block",
        "minecraft:stone_pickaxe",
        "minecraft:torch",
    }
)

KUBEJS_ITEM_ALLOWLIST = frozenset(
    {
        "kubejs:ascendancy_seal",
        "kubejs:requisition_chit",
    }
)


@dataclass(frozen=True)
class SnbtLong:
    value: int


@dataclass(frozen=True)
class QuestCounts:
    chapters: int
    quests: int
    tasks: int
    rewards: int


@dataclass(frozen=True)
class GroupSpec:
    slug: str
    title: str
    id: str | None = None

    @property
    def resolved_id(self) -> str:
        return self.id or stable_id("chapter_group", self.slug)


@dataclass
class TaskSpec:
    slug: str
    task_type: str
    data: Mapping[str, Any] = field(default_factory=dict)
    title: str = ""

    @property
    def id(self) -> str:
        return stable_id("task", self.slug)


@dataclass
class RewardSpec:
    slug: str
    reward_type: str
    data: Mapping[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return stable_id("reward", self.slug)


@dataclass
class QuestSpec:
    slug: str
    title: str
    description: tuple[str, ...]
    x: float
    y: float
    subtitle: str = ""
    dependencies: tuple[str, ...] = ()
    tasks: tuple[TaskSpec, ...] = ()
    rewards: tuple[RewardSpec, ...] = ()
    shape: str = ""
    size: float | None = None
    optional: bool | None = None

    @property
    def id(self) -> str:
        return stable_id("quest", self.slug)

    @property
    def dependency_ids(self) -> tuple[str, ...]:
        return tuple(
            dependency
            if HEX_ID.fullmatch(dependency)
            else stable_id("quest", dependency)
            for dependency in self.dependencies
        )


@dataclass
class ChapterSpec:
    slug: str
    title: str
    group: GroupSpec
    icon: str
    order_index: int
    quests: tuple[QuestSpec, ...]
    default_quest_shape: str = ""

    @property
    def id(self) -> str:
        return stable_id("chapter", self.slug)


def stable_id(kind: str, slug: str) -> str:
    return hashlib.sha256(f"{kind}:{slug}".encode("utf-8")).hexdigest()[:16].upper()


def assert_no_id_collisions(catalog: Sequence[ChapterSpec]) -> None:
    owners: dict[str, tuple[str, str]] = {}
    seen_groups: set[tuple[str, str]] = set()

    def register(identifier: str, kind: str, slug: str, allow_repeat: bool = False) -> None:
        if not HEX_ID.fullmatch(identifier):
            raise ValueError(f"malformed {kind} ID for {slug}: {identifier}")
        owner = (kind, slug)
        if allow_repeat and owner in seen_groups:
            return
        previous = owners.get(identifier)
        if previous is not None:
            raise ValueError(
                f"ID collision for {kind}:{slug} and {previous[0]}:{previous[1]}: "
                f"{identifier}"
            )
        owners[identifier] = owner
        if allow_repeat:
            seen_groups.add(owner)

    for chapter in catalog:
        register(chapter.group.resolved_id, "chapter_group", chapter.group.slug, True)
        register(chapter.id, "chapter", chapter.slug)
        for quest in chapter.quests:
            register(quest.id, "quest", quest.slug)
            for task in quest.tasks:
                register(task.id, "task", task.slug)
            for reward in quest.rewards:
                register(reward.id, "reward", reward.slug)


def _escape(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _format_scalar(value: Any) -> str:
    if isinstance(value, SnbtLong):
        return f"{value.value}L"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return _escape(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return f"{value:.1f}d"
    if isinstance(value, Mapping):
        fields = ", ".join(f"{key}: {_format_scalar(item)}" for key, item in value.items())
        return f"{{ {fields} }}"
    if isinstance(value, (tuple, list)):
        return "[" + ", ".join(_format_scalar(item) for item in value) + "]"
    raise TypeError(f"unsupported SNBT value: {value!r}")


def _render_object(fields: Iterable[tuple[str, Any]], indent: int) -> list[str]:
    prefix = "\t" * indent
    lines = [f"{prefix}{{"]
    for key, value in fields:
        lines.append(f"{prefix}\t{key}: {_format_scalar(value)}")
    lines.append(f"{prefix}}}")
    return lines


def render_chapter(chapter: ChapterSpec) -> str:
    lines = [
        "{",
        "\tdefault_hide_dependency_lines: false",
        f"\tdefault_quest_shape: {_escape(chapter.default_quest_shape)}",
        f"\tfilename: {_escape(chapter.id)}",
        f"\tgroup: {_escape(chapter.group.resolved_id)}",
        f"\ticon: {{ id: {_escape(chapter.icon)} }}",
        f"\tid: {_escape(chapter.id)}",
        "\timages: [ ]",
        f"\torder_index: {chapter.order_index}",
        "\tquest_links: [ ]",
        "\tquests: [",
    ]
    for quest in chapter.quests:
        quest_fields: list[tuple[str, Any]] = [("id", quest.id)]
        if quest.dependency_ids:
            quest_fields.append(("dependencies", quest.dependency_ids))
        quest_fields.extend((("x", quest.x), ("y", quest.y)))
        if quest.shape:
            quest_fields.append(("shape", quest.shape))
        if quest.size is not None:
            quest_fields.append(("size", quest.size))
        if quest.optional is not None:
            quest_fields.append(("optional", quest.optional))

        lines.append("\t\t{")
        for key, value in quest_fields:
            lines.append(f"\t\t\t{key}: {_format_scalar(value)}")
        lines.append("\t\t\ttasks: [")
        for task in quest.tasks:
            fields = (("id", task.id), ("type", task.task_type), *task.data.items())
            lines.extend(_render_object(fields, 4))
        lines.append("\t\t\t]")
        lines.append("\t\t\trewards: [")
        for reward in quest.rewards:
            fields = (("id", reward.id), ("type", reward.reward_type), *reward.data.items())
            lines.extend(_render_object(fields, 4))
        lines.append("\t\t\t]")
        lines.append("\t\t}")
    lines.extend(("\t]", "}"))
    return "\n".join(lines) + "\n"


def _localization_entries(catalog: Sequence[ChapterSpec]) -> dict[str, str | tuple[str, ...]]:
    entries: dict[str, str | tuple[str, ...]] = {}
    for chapter in catalog:
        entries[f"chapter_group.{chapter.group.resolved_id}.title"] = chapter.group.title
        entries[f"chapter.{chapter.id}.title"] = chapter.title
        for quest in chapter.quests:
            entries[f"quest.{quest.id}.title"] = quest.title
            if quest.subtitle:
                entries[f"quest.{quest.id}.quest_subtitle"] = quest.subtitle
            entries[f"quest.{quest.id}.quest_desc"] = quest.description
            for task in quest.tasks:
                if task.title:
                    entries[f"task.{task.id}.title"] = task.title
    return entries


def _split_language_entries(text: str) -> tuple[list[str], dict[str, list[str]]]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "{" or lines[-1].strip() != "}":
        raise ValueError("language file must be wrapped in braces")
    order: list[str] = []
    blocks: dict[str, list[str]] = {}
    current_key: str | None = None
    key_pattern = re.compile(r"^\t([A-Za-z0-9_.-]+):")
    for line in lines[1:-1]:
        match = key_pattern.match(line)
        if match:
            current_key = match.group(1)
            order.append(current_key)
            blocks[current_key] = [line]
        elif current_key is not None:
            blocks[current_key].append(line)
        elif line.strip():
            raise ValueError(f"unrecognized language content: {line}")
    return order, blocks


def _render_language_entry(key: str, value: str | tuple[str, ...]) -> list[str]:
    if isinstance(value, str):
        return [f"\t{key}: {_escape(value)}"]
    lines = [f"\t{key}: ["]
    lines.extend(f"\t\t{_escape(line)}" for line in value)
    lines.append("\t]")
    return lines


def _merge_language(text: str, entries: Mapping[str, str | tuple[str, ...]]) -> str:
    order, blocks = _split_language_entries(text)
    for key, value in entries.items():
        if key not in blocks:
            order.append(key)
        blocks[key] = _render_language_entry(key, value)
    lines = ["{"]
    for key in order:
        lines.extend(blocks[key])
    lines.append("}")
    return "\n".join(lines) + "\n"


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temp_path = Path(temp_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def write_catalog(catalog: Sequence[ChapterSpec], quest_root: Path) -> list[Path]:
    assert_no_id_collisions(catalog)
    if not catalog:
        return []
    written: list[Path] = []
    for chapter in catalog:
        chapter_path = quest_root / "chapters" / f"{chapter.id}.snbt"
        _atomic_write(chapter_path, render_chapter(chapter))
        written.append(chapter_path)
    lang_path = quest_root / "lang" / "en_us.snbt"
    current_language = lang_path.read_text(encoding="utf-8")
    _atomic_write(lang_path, _merge_language(current_language, _localization_entries(catalog)))
    return written


def _language_keys(path: Path) -> set[str]:
    order, _ = _split_language_entries(path.read_text(encoding="utf-8"))
    return set(order)


def _jar_item_ids(mods_dir: Path) -> set[str]:
    item_ids: set[str] = set()
    asset_pattern = re.compile(r"^assets/([^/]+)/(?:models/item|items)/(.+)\.json$")
    for jar_path in sorted(mods_dir.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar_path) as jar:
                for name in jar.namelist():
                    match = asset_pattern.fullmatch(name)
                    if match:
                        item_ids.add(f"{match.group(1)}:{match.group(2)}")
        except zipfile.BadZipFile as error:
            raise ValueError(f"unreadable mod jar {jar_path.name}: {error}") from error
    return item_ids


def count_quests(quest_root: Path) -> QuestCounts:
    chapter_files = sorted((quest_root / "chapters").glob("*.snbt"))
    quest_count = 0
    task_count = 0
    reward_count = 0
    for path in chapter_files:
        section = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("\t\t\ttasks: ["):
                section = "tasks"
                continue
            if line.startswith("\t\t\trewards: ["):
                section = "rewards"
                continue
            if line == "\t\t\t]":
                section = ""
                continue
            if re.match(r'^\t\t\tid:\s*"[0-9A-F]{16}"', line):
                quest_count += 1
            elif section and re.search(r'\bid:\s*"[0-9A-F]{16}"', line):
                if section == "tasks":
                    task_count += 1
                else:
                    reward_count += 1
    return QuestCounts(
        chapters=len(chapter_files),
        quests=quest_count,
        tasks=task_count,
        rewards=reward_count,
    )


def _dependency_cycles(dependencies: Mapping[str, set[str]]) -> list[list[str]]:
    cycles: list[list[str]] = []
    visiting: list[str] = []
    state: dict[str, int] = {}

    def visit(quest_id: str) -> None:
        current = state.get(quest_id, 0)
        if current == 2:
            return
        if current == 1:
            start = visiting.index(quest_id)
            cycles.append(visiting[start:] + [quest_id])
            return
        state[quest_id] = 1
        visiting.append(quest_id)
        for dependency in dependencies.get(quest_id, set()):
            if dependency in dependencies:
                visit(dependency)
        visiting.pop()
        state[quest_id] = 2

    for quest_id in dependencies:
        visit(quest_id)
    return cycles


def validate_quests(
    quest_root: Path,
    mods_dir: Path,
    runtime_logs: Sequence[Path] = (),
) -> list[str]:
    errors: list[str] = []
    chapter_dir = quest_root / "chapters"
    chapter_files = sorted(chapter_dir.glob("*.snbt"))
    all_snbt_files = sorted(quest_root.rglob("*.snbt"))
    all_ids: dict[str, list[Path]] = {}
    quest_ids: set[str] = set()
    chapter_ids: set[str] = set()
    group_ids: set[str] = set()
    dependency_graph: dict[str, set[str]] = {}
    item_references: dict[str, set[Path]] = {}

    for path in all_snbt_files:
        text = path.read_text(encoding="utf-8")
        if "\u2014" in text:
            errors.append(f"em dash in {path}")
        for value in re.findall(r"\bid\s*:\s*\"([^\"]+)\"", text):
            if RESOURCE_ID.fullmatch(value):
                item_references.setdefault(value, set()).add(path)
            elif HEX_ID.fullmatch(value):
                all_ids.setdefault(value, []).append(path)
            else:
                errors.append(f"malformed IDs in {path}: {value}")

    group_path = quest_root / "chapter_groups.snbt"
    if group_path.exists():
        group_text = group_path.read_text(encoding="utf-8")
        group_ids.update(re.findall(r"\bid\s*:\s*\"([0-9A-F]{16})\"", group_text))

    for path in chapter_files:
        text = path.read_text(encoding="utf-8")
        chapter_match = re.search(r"(?m)^\tid:\s*\"([^\"]+)\"", text)
        filename_match = re.search(r"(?m)^\tfilename:\s*\"([^\"]+)\"", text)
        group_match = re.search(r"(?m)^\tgroup:\s*\"([^\"]+)\"", text)
        if not chapter_match:
            errors.append(f"malformed IDs in {path}: missing chapter id")
            continue
        chapter_id = chapter_match.group(1)
        chapter_ids.add(chapter_id)
        filename = filename_match.group(1) if filename_match else ""
        if filename != chapter_id or path.stem != chapter_id:
            errors.append(
                f"filename/id mismatch in {path}: filename={filename!r}, id={chapter_id!r}"
            )
        if group_match and group_match.group(1) not in group_ids:
            errors.append(f"unresolved group in {path}: {group_match.group(1)}")

        current_quest: str | None = None
        for line in text.splitlines():
            quest_match = re.match(r'^\t\t\tid:\s*"([^"]+)"', line)
            if quest_match:
                current_quest = quest_match.group(1)
                quest_ids.add(current_quest)
                dependency_graph.setdefault(current_quest, set())
                continue
            dependency_match = re.match(r"^\t\t\tdependencies:\s*\[(.*)\]", line)
            if dependency_match and current_quest:
                dependencies = set(re.findall(r'"([^"]+)"', dependency_match.group(1)))
                dependency_graph[current_quest].update(dependencies)
                for dependency in dependencies:
                    if not HEX_ID.fullmatch(dependency):
                        errors.append(f"malformed IDs in {path}: {dependency}")

    for identifier, paths in all_ids.items():
        if len(paths) > 1:
            locations = ", ".join(str(path) for path in paths)
            errors.append(f"duplicate ID {identifier}: {locations}")

    for quest_id, dependencies in dependency_graph.items():
        for dependency in sorted(dependencies - quest_ids):
            errors.append(f"unresolved dependency {dependency} from quest {quest_id}")
    for cycle in _dependency_cycles(dependency_graph):
        errors.append(f"dependency cycle: {' -> '.join(cycle)}")

    lang_path = quest_root / "lang" / "en_us.snbt"
    try:
        language_keys = _language_keys(lang_path)
    except (OSError, ValueError) as error:
        errors.append(f"missing localization file or malformed language: {error}")
        language_keys = set()
    for group_id in sorted(group_ids):
        key = f"chapter_group.{group_id}.title"
        if key not in language_keys:
            errors.append(f"missing localization: {key}")
    for chapter_id in sorted(chapter_ids):
        key = f"chapter.{chapter_id}.title"
        if key not in language_keys:
            errors.append(f"missing localization: {key}")
    for quest_id in sorted(quest_ids):
        for suffix in ("title", "quest_desc"):
            key = f"quest.{quest_id}.{suffix}"
            if key not in language_keys:
                errors.append(f"missing localization: {key}")

    for key in language_keys:
        match = re.match(r"^(?:chapter|chapter_group|quest|task)\.([^.]+)\.", key)
        if match and not HEX_ID.fullmatch(match.group(1)):
            errors.append(f"malformed IDs in localization key: {key}")

    if not mods_dir.is_dir():
        errors.append(f"item audit unavailable: missing mods directory {mods_dir}")
    else:
        try:
            valid_items = _jar_item_ids(mods_dir)
        except ValueError as error:
            errors.append(f"item audit unavailable: {error}")
            valid_items = set()
        valid_items.update(VANILLA_ITEM_ALLOWLIST)
        valid_items.update(KUBEJS_ITEM_ALLOWLIST)
        for item_id in sorted(item_references):
            if item_id not in valid_items:
                locations = ", ".join(str(path) for path in sorted(item_references[item_id]))
                errors.append(f"impossible item reference {item_id}: {locations}")

    runtime_item_pattern = re.compile(
        r"Unknown registry key[^\n]*minecraft:item\]:\s*"
        r"([a-z0-9_.-]+:[a-z0-9_./-]+)"
    )
    runtime_warnings: dict[str, set[Path]] = {}
    for runtime_log in runtime_logs:
        if not runtime_log.is_file():
            continue
        for item_id in runtime_item_pattern.findall(runtime_log.read_text(encoding="utf-8")):
            if item_id in item_references:
                runtime_warnings.setdefault(item_id, set()).add(runtime_log)
    for item_id, paths in sorted(runtime_warnings.items()):
        locations = ", ".join(str(path) for path in sorted(paths))
        errors.append(f"runtime item warning for {item_id}: {locations}")

    return errors
