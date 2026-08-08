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
MANAGED_STATE_NAME = ".afterlight-managed.json"

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
        "kubejs:deep_vault_key",
        "kubejs:gate_blueprint",
        "kubejs:requisition_chit",
        "kubejs:schematic_industrial_anchor",
        "kubejs:schematic_isotopic_core",
        "kubejs:schematic_kinetic_frame",
        "kubejs:schematic_lattice_matrix",
        "kubejs:undercurrent_stabilizer_precursor",
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


class SnbtParseError(ValueError):
    pass


@dataclass(frozen=True)
class _SnbtToken:
    kind: str
    value: str
    offset: int


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


def _format_key(value: str) -> str:
    return value if re.fullmatch(r"[A-Za-z0-9_.+-]+", value) else _escape(value)


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
        fields = ", ".join(
            f"{_format_key(str(key))}: {_format_scalar(item)}"
            for key, item in value.items()
        )
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


def _merge_language(
    text: str,
    entries: Mapping[str, str | tuple[str, ...]],
    remove_keys: Iterable[str] = (),
) -> str:
    order, blocks = _split_language_entries(text)
    for key in remove_keys:
        blocks.pop(key, None)
    order = [key for key in order if key in blocks]
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


def _load_managed_state(path: Path) -> tuple[set[str], set[str]]:
    if not path.exists():
        return set(), set()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid managed quest state {path}: {error}") from error
    chapters = data.get("chapters")
    localization_keys = data.get("localization_keys")
    if not isinstance(chapters, list) or not all(isinstance(value, str) for value in chapters):
        raise ValueError(f"invalid managed chapter list in {path}")
    if not isinstance(localization_keys, list) or not all(
        isinstance(value, str) for value in localization_keys
    ):
        raise ValueError(f"invalid managed localization list in {path}")
    return set(chapters), set(localization_keys)


def _managed_state(chapters: Iterable[str], localization_keys: Iterable[str]) -> str:
    return json.dumps(
        {
            "version": 1,
            "chapters": sorted(chapters),
            "localization_keys": sorted(localization_keys),
        },
        indent=2,
        sort_keys=True,
    ) + "\n"


def write_catalog(catalog: Sequence[ChapterSpec], quest_root: Path) -> list[Path]:
    assert_no_id_collisions(catalog)
    state_path = quest_root / MANAGED_STATE_NAME
    old_chapters, old_localization_keys = _load_managed_state(state_path)
    current_chapters = {chapter.id for chapter in catalog}
    localization_entries = _localization_entries(catalog)
    lang_path = quest_root / "lang" / "en_us.snbt"
    current_language = lang_path.read_text(encoding="utf-8")
    _, current_language_blocks = _split_language_entries(current_language)
    current_localization_keys = {
        key
        for key in localization_entries
        if key in old_localization_keys or key not in current_language_blocks
    }

    for chapter_id in sorted(old_chapters - current_chapters):
        (quest_root / "chapters" / f"{chapter_id}.snbt").unlink(missing_ok=True)

    written: list[Path] = []
    for chapter in catalog:
        chapter_path = quest_root / "chapters" / f"{chapter.id}.snbt"
        _atomic_write(chapter_path, render_chapter(chapter))
        written.append(chapter_path)

    managed_entries = {
        key: value
        for key, value in localization_entries.items()
        if key in current_localization_keys
    }
    _atomic_write(
        lang_path,
        _merge_language(
            current_language,
            managed_entries,
            old_localization_keys - current_localization_keys,
        ),
    )
    _atomic_write(
        state_path,
        _managed_state(current_chapters, current_localization_keys),
    )
    _atomic_write(
        quest_root.parents[2]
        / "kubejs"
        / "server_scripts"
        / "afterlight"
        / "generated_quest_item_audit.js",
        _render_quest_item_audit(quest_root),
    )
    return written


def _language_keys(path: Path) -> set[str]:
    order, _ = _split_language_entries(path.read_text(encoding="utf-8"))
    return set(order)


def _tokenize_snbt(text: str) -> list[_SnbtToken]:
    tokens: list[_SnbtToken] = []
    cursor = 0
    punctuation = set("{}[]:,")
    while cursor < len(text):
        character = text[cursor]
        if character.isspace():
            cursor += 1
            continue
        if character in punctuation:
            tokens.append(_SnbtToken(character, character, cursor))
            cursor += 1
            continue
        if character == '"':
            start = cursor
            cursor += 1
            escaped = False
            while cursor < len(text):
                current = text[cursor]
                if current == '"' and not escaped:
                    cursor += 1
                    break
                if current == "\\" and not escaped:
                    escaped = True
                else:
                    escaped = False
                cursor += 1
            else:
                raise SnbtParseError(f"unterminated string at offset {start}")
            raw = text[start:cursor]
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as error:
                raise SnbtParseError(f"invalid string at offset {start}: {error}") from error
            tokens.append(_SnbtToken("string", value, start))
            continue
        start = cursor
        while (
            cursor < len(text)
            and not text[cursor].isspace()
            and text[cursor] not in punctuation
        ):
            cursor += 1
        if cursor == start:
            raise SnbtParseError(f"unexpected character {text[cursor]!r} at offset {cursor}")
        tokens.append(_SnbtToken("bare", text[start:cursor], start))
    return tokens


class _SnbtParser:
    def __init__(self, text: str) -> None:
        self.tokens = _tokenize_snbt(text)
        self.cursor = 0

    def parse(self) -> Any:
        value = self._parse_value()
        if self.cursor != len(self.tokens):
            token = self.tokens[self.cursor]
            raise SnbtParseError(
                f"trailing token {token.value!r} at offset {token.offset}"
            )
        return value

    def _peek(self) -> _SnbtToken | None:
        return self.tokens[self.cursor] if self.cursor < len(self.tokens) else None

    def _take(self, kind: str | None = None) -> _SnbtToken:
        token = self._peek()
        if token is None:
            raise SnbtParseError("unexpected end of input")
        if kind is not None and token.kind != kind:
            raise SnbtParseError(
                f"expected {kind!r}, found {token.value!r} at offset {token.offset}"
            )
        self.cursor += 1
        return token

    def _discard_commas(self) -> None:
        while self._peek() is not None and self._peek().kind == ",":
            self.cursor += 1

    def _parse_value(self) -> Any:
        token = self._peek()
        if token is None:
            raise SnbtParseError("expected value, found end of input")
        if token.kind == "{":
            return self._parse_compound()
        if token.kind == "[":
            return self._parse_list()
        if token.kind == "string":
            return self._take().value
        if token.kind == "bare":
            value = self._take().value
            if value == "true":
                return True
            if value == "false":
                return False
            return value
        raise SnbtParseError(
            f"expected value, found {token.value!r} at offset {token.offset}"
        )

    def _parse_compound(self) -> dict[str, Any]:
        self._take("{")
        result: dict[str, Any] = {}
        self._discard_commas()
        while self._peek() is not None and self._peek().kind != "}":
            key_token = self._take()
            if key_token.kind not in {"bare", "string"}:
                raise SnbtParseError(
                    f"expected compound key at offset {key_token.offset}"
                )
            self._take(":")
            if key_token.value in result:
                raise SnbtParseError(
                    f"duplicate compound key {key_token.value!r} at offset {key_token.offset}"
                )
            result[key_token.value] = self._parse_value()
            self._discard_commas()
        self._take("}")
        return result

    def _parse_list(self) -> list[Any]:
        self._take("[")
        result: list[Any] = []
        self._discard_commas()
        while self._peek() is not None and self._peek().kind != "]":
            result.append(self._parse_value())
            self._discard_commas()
        self._take("]")
        return result


def _parse_snbt(text: str) -> Any:
    return _SnbtParser(text).parse()


def _id_values(value: Any, item_context: bool = False) -> Iterable[tuple[Any, bool]]:
    if isinstance(value, Mapping):
        for key, child in value.items():
            child_item_context = item_context or key in {"icon", "item", "stack"}
            if key == "id":
                yield child, item_context
            yield from _id_values(child, child_item_context)
    elif isinstance(value, list):
        for child in value:
            yield from _id_values(child, item_context)


def _item_references_from_parsed(parsed_files: Mapping[Path, Any]) -> dict[str, set[Path]]:
    item_references: dict[str, set[Path]] = {}
    for path, parsed in parsed_files.items():
        for value, is_item in _id_values(parsed):
            if is_item and isinstance(value, str) and RESOURCE_ID.fullmatch(value):
                item_references.setdefault(value, set()).add(path)
    return item_references


def _parsed_quest_files(quest_root: Path) -> dict[Path, Any]:
    parsed_files: dict[Path, Any] = {}
    for path in sorted(quest_root.rglob("*.snbt")):
        parsed_files[path] = _parse_snbt(path.read_text(encoding="utf-8"))
    return parsed_files


def _quest_item_ids(quest_root: Path) -> tuple[str, ...]:
    quest_item_ids = _item_references_from_parsed(_parsed_quest_files(quest_root))
    return tuple(sorted(quest_item_ids.keys() | KUBEJS_ITEM_ALLOWLIST))


def _registry_input_digest(repo_root: Path) -> str:
    digest = hashlib.sha256()
    paths = [
        *sorted((repo_root / "mods").glob("*.pw.toml")),
        *sorted((repo_root / "kubejs" / "startup_scripts").rglob("*")),
        *sorted((repo_root / "config").rglob("*")),
    ]
    for path in paths:
        if not path.is_file():
            continue
        digest.update(path.relative_to(repo_root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def quest_item_audit_digest(quest_root: Path) -> str:
    repo_root = quest_root.parents[2]
    payload = json.dumps(
        {
            "items": _quest_item_ids(quest_root),
            "registry_inputs": _registry_input_digest(repo_root),
            "version": 3,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _render_quest_item_audit(quest_root: Path) -> str:
    item_ids = _quest_item_ids(quest_root)
    digest = quest_item_audit_digest(quest_root)
    rendered_ids = json.dumps(item_ids, indent=2)
    return (
        "// Generated by tools/build-quests.py. Do not edit by hand.\n"
        f"const AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST = '{digest}'\n"
        f"const AFTERLIGHT_QUEST_ITEM_IDS = {rendered_ids}\n\n"
        "ServerEvents.loaded(() => {\n"
        "  const bootNonce = '__AFTERLIGHT_BOOT_NONCE__'\n"
        "  const invalid = AFTERLIGHT_QUEST_ITEM_IDS.filter(id => !Item.exists(id))\n"
        "  if (invalid.length > 0) {\n"
        "    invalid.forEach(id => console.error(`[AFTERLIGHT QUEST ITEM AUDIT] INVALID ${id}`))\n"
        "    console.error(`[AFTERLIGHT QUEST ITEM AUDIT] FAILED ${AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST} ${bootNonce}`)\n"
        "    return\n"
        "  }\n"
        "  console.info(`[AFTERLIGHT QUEST ITEM AUDIT] OK ${AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST} ${AFTERLIGHT_QUEST_ITEM_IDS.length} ${bootNonce}`)\n"
        "})\n"
    )


def _jar_asset_namespaces(mods_dir: Path) -> set[str]:
    namespaces: set[str] = set()
    asset_pattern = re.compile(r"^assets/([^/]+)/")
    for jar_path in sorted(mods_dir.glob("*.jar")):
        try:
            with zipfile.ZipFile(jar_path) as jar:
                for name in jar.namelist():
                    match = asset_pattern.match(name)
                    if match:
                        namespaces.add(match.group(1))
        except zipfile.BadZipFile as error:
            raise ValueError(f"unreadable mod jar {jar_path.name}: {error}") from error
    return namespaces


def count_quests(quest_root: Path) -> QuestCounts:
    chapter_files = sorted((quest_root / "chapters").glob("*.snbt"))
    quest_count = 0
    task_count = 0
    reward_count = 0
    for path in chapter_files:
        parsed = _parse_snbt(path.read_text(encoding="utf-8"))
        if not isinstance(parsed, Mapping):
            raise SnbtParseError(f"chapter root must be a compound: {path}")
        quests = parsed.get("quests", [])
        if not isinstance(quests, list):
            raise SnbtParseError(f"chapter quests must be a list: {path}")
        quest_count += len(quests)
        for quest in quests:
            if not isinstance(quest, Mapping):
                raise SnbtParseError(f"quest must be a compound: {path}")
            tasks = quest.get("tasks", [])
            rewards = quest.get("rewards", [])
            if not isinstance(tasks, list) or not isinstance(rewards, list):
                raise SnbtParseError(f"quest tasks and rewards must be lists: {path}")
            task_count += len(tasks)
            reward_count += len(rewards)
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
    require_runtime_audit: bool = False,
) -> list[str]:
    errors: list[str] = []
    chapter_dir = quest_root / "chapters"
    chapter_files = sorted(chapter_dir.glob("*.snbt"))
    all_snbt_files = sorted(quest_root.rglob("*.snbt"))
    parsed_files: dict[Path, Any] = {}
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
        try:
            parsed = _parse_snbt(text)
        except SnbtParseError as error:
            errors.append(f"malformed SNBT in {path}: {error}")
            continue
        parsed_files[path] = parsed
        for value, is_item in _id_values(parsed):
            if not isinstance(value, str):
                errors.append(f"malformed IDs in {path}: {value!r}")
                continue
            if is_item:
                if RESOURCE_ID.fullmatch(value):
                    item_references.setdefault(value, set()).add(path)
                else:
                    errors.append(f"malformed item ID in {path}: {value}")
            elif HEX_ID.fullmatch(value):
                all_ids.setdefault(value, []).append(path)
            else:
                errors.append(f"malformed IDs in {path}: {value}")

    group_path = quest_root / "chapter_groups.snbt"
    if group_path.exists():
        group_data = parsed_files.get(group_path)
        if isinstance(group_data, Mapping):
            groups = group_data.get("chapter_groups", [])
            if isinstance(groups, list):
                for group in groups:
                    if isinstance(group, Mapping) and isinstance(group.get("id"), str):
                        group_ids.add(group["id"])

    for path in chapter_files:
        chapter = parsed_files.get(path)
        if not isinstance(chapter, Mapping):
            continue
        chapter_id = chapter.get("id")
        if not isinstance(chapter_id, str):
            errors.append(f"malformed IDs in {path}: missing chapter id")
            continue
        chapter_ids.add(chapter_id)
        filename = chapter.get("filename")
        if filename != chapter_id or path.stem != chapter_id:
            errors.append(
                f"filename/id mismatch in {path}: filename={filename!r}, id={chapter_id!r}"
            )
        group_id = chapter.get("group")
        if isinstance(group_id, str) and group_id not in group_ids:
            errors.append(f"unresolved group in {path}: {group_id}")

        quests = chapter.get("quests", [])
        if not isinstance(quests, list):
            errors.append(f"malformed SNBT in {path}: quests must be a list")
            continue
        for quest in quests:
            if not isinstance(quest, Mapping):
                errors.append(f"malformed SNBT in {path}: quest must be a compound")
                continue
            quest_id = quest.get("id")
            if not isinstance(quest_id, str):
                errors.append(f"malformed IDs in {path}: missing quest id")
                continue
            quest_ids.add(quest_id)
            dependency_graph.setdefault(quest_id, set())
            dependencies = quest.get("dependencies", [])
            if not isinstance(dependencies, list):
                errors.append(f"malformed SNBT in {path}: dependencies must be a list")
                continue
            for dependency in dependencies:
                if not isinstance(dependency, str) or not HEX_ID.fullmatch(dependency):
                    errors.append(f"malformed IDs in {path}: {dependency}")
                    continue
                dependency_graph[quest_id].add(dependency)

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
            _jar_asset_namespaces(mods_dir)
        except ValueError as error:
            errors.append(f"item audit unavailable: {error}")
        for item_id in sorted(item_references):
            namespace = item_id.split(":", 1)[0]
            is_known_builtin = (
                item_id in VANILLA_ITEM_ALLOWLIST or item_id in KUBEJS_ITEM_ALLOWLIST
            )
            if namespace in {"minecraft", "kubejs"} and not is_known_builtin:
                locations = ", ".join(str(path) for path in sorted(item_references[item_id]))
                errors.append(f"impossible item reference {item_id}: {locations}")

    if require_runtime_audit:
        item_ids = _quest_item_ids(quest_root)
        digest = quest_item_audit_digest(quest_root)
        repo_root = quest_root.parents[2]
        audit_script = (
            repo_root
            / "kubejs"
            / "server_scripts"
            / "afterlight"
            / "generated_quest_item_audit.js"
        )
        nonce_path = repo_root / "server-test" / "afterlight-audit-nonce.txt"
        try:
            boot_nonce = nonce_path.read_text(encoding="utf-8").strip()
        except OSError:
            boot_nonce = ""
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", boot_nonce):
            errors.append(f"runtime item audit missing or stale: invalid boot nonce {nonce_path}")
            boot_nonce = "missing"
        available_logs = [
            path
            for path in runtime_logs
            if path.is_file()
            and audit_script.is_file()
            and path.stat().st_mtime >= audit_script.stat().st_mtime
        ]
        success_marker = (
            f"[AFTERLIGHT QUEST ITEM AUDIT] OK {digest} {len(item_ids)} {boot_nonce}"
        )
        failure_marker = f"[AFTERLIGHT QUEST ITEM AUDIT] FAILED {digest} {boot_nonce}"
        failed_logs = [
            path
            for path in available_logs
            if failure_marker in path.read_text(encoding="utf-8")
        ]
        successful_logs = [
            path
            for path in available_logs
            if success_marker in path.read_text(encoding="utf-8")
        ]
        fresh_success = bool(successful_logs)
        if failed_logs:
            invalid_pattern = re.compile(r"\[AFTERLIGHT QUEST ITEM AUDIT\] INVALID ([^\s]+)")
            invalid_items = sorted(
                {
                    item_id
                    for path in failed_logs
                    for item_id in invalid_pattern.findall(path.read_text(encoding="utf-8"))
                }
            )
            suffix = f": {', '.join(invalid_items)}" if invalid_items else ""
            errors.append(f"runtime item audit failed for digest {digest}{suffix}")
        elif not fresh_success:
            errors.append(f"runtime item audit missing or stale: expected digest {digest}")

    return errors
