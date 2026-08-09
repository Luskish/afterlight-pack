from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HEX_ID = re.compile(r"^[0-9A-F]{16}$")
FTB_LOCALIZATION_KEY = re.compile(
    r"^(?P<prefix>(?:chapter|chapter_group|quest|task|reward)\.)"
    r"(?P<identifier>[0-9A-F]{16})(?P<suffix>\..+)$"
)
MAX_FTB_ID = (1 << 63) - 1
RESOURCE_ID = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
MANAGED_STATE_NAME = ".afterlight-managed.json"
MIGRATION_JOURNAL_NAME = "journal.json"
MIGRATION_TRANSACTION_VERSION = 1
DEPENDENCY_REQUIREMENTS = frozenset(
    {"all_completed", "one_completed", "all_started", "one_started"}
)
PROGRESSION_MODES = frozenset({"linear", "flexible"})

VANILLA_ITEM_ALLOWLIST = frozenset(
    {
        "minecraft:blast_furnace",
        "minecraft:bread",
        "minecraft:chiseled_tuff_bricks",
        "minecraft:coal",
        "minecraft:copper_ingot",
        "minecraft:crafting_table",
        "minecraft:diamond",
        "minecraft:echo_shard",
        "minecraft:enchanted_golden_apple",
        "minecraft:experience_bottle",
        "minecraft:golden_apple",
        "minecraft:iron_block",
        "minecraft:iron_ingot",
        "minecraft:netherite_ingot",
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
        "kubejs:gate_industrial_anchor",
        "kubejs:gate_isotopic_core",
        "kubejs:gate_kinetic_frame",
        "kubejs:gate_lattice_matrix",
        "kubejs:gate_of_return_core",
        "kubejs:requisition_chit",
        "kubejs:schematic_industrial_anchor",
        "kubejs:schematic_isotopic_core",
        "kubejs:schematic_kinetic_frame",
        "kubejs:schematic_lattice_matrix",
        "kubejs:undercurrent_stabilizer",
        "kubejs:undercurrent_stabilizer_precursor",
    }
)


@dataclass(frozen=True)
class SnbtLong:
    value: int

    def __post_init__(self) -> None:
        if not -(1 << 63) <= self.value <= (1 << 63) - 1:
            raise ValueError(f"SNBT long is outside signed 64-bit range: {self.value}")

    @classmethod
    def from_hex(cls, identifier: str) -> SnbtLong:
        if not re.fullmatch(r"[0-9A-Fa-f]{16}", identifier):
            raise ValueError(f"reward table hex ID must be 16 hexadecimal digits: {identifier}")
        unsigned = int(identifier, 16)
        signed = unsigned if unsigned <= (1 << 63) - 1 else unsigned - (1 << 64)
        return cls(signed)


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
    end: int


@dataclass(frozen=True)
class GroupSpec:
    slug: str
    title: str
    id: str | None = None

    @property
    def resolved_id(self) -> str:
        return ftb_safe_id(self.id) if self.id else stable_id("chapter_group", self.slug)


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
    dependency_requirement: str | None = None
    progression_mode: str | None = None
    tasks: tuple[TaskSpec, ...] = ()
    rewards: tuple[RewardSpec, ...] = ()
    shape: str = ""
    size: float | None = None
    optional: bool | None = None
    can_repeat: bool | None = None
    repeat_cooldown: int | None = None

    def __post_init__(self) -> None:
        if (
            self.dependency_requirement is not None
            and self.dependency_requirement not in DEPENDENCY_REQUIREMENTS
        ):
            raise ValueError(
                f"unsupported dependency requirement: {self.dependency_requirement}"
            )
        if (
            self.progression_mode is not None
            and self.progression_mode not in PROGRESSION_MODES
        ):
            raise ValueError(f"unsupported progression mode: {self.progression_mode}")

    @property
    def id(self) -> str:
        return stable_id("quest", self.slug)

    @property
    def dependency_ids(self) -> tuple[str, ...]:
        return tuple(
            ftb_safe_id(dependency)
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


def ftb_safe_id(identifier: str) -> str:
    if not HEX_ID.fullmatch(identifier):
        raise ValueError(f"FTB ID must be 16 uppercase hexadecimal digits: {identifier}")
    value = int(identifier, 16) & MAX_FTB_ID
    if value < 2:
        value += 2
    return f"{value:016X}"


def stable_id(kind: str, slug: str) -> str:
    digest = hashlib.sha256(f"{kind}:{slug}".encode("utf-8")).hexdigest()[:16].upper()
    return ftb_safe_id(digest)


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
        if quest.dependency_requirement is not None:
            quest_fields.append(("dependency_requirement", quest.dependency_requirement))
        if quest.progression_mode is not None:
            quest_fields.append(("progression_mode", quest.progression_mode))
        quest_fields.extend((("x", quest.x), ("y", quest.y)))
        if quest.shape:
            quest_fields.append(("shape", quest.shape))
        if quest.size is not None:
            quest_fields.append(("size", quest.size))
        if quest.optional is not None:
            quest_fields.append(("optional", quest.optional))
        if quest.can_repeat is not None:
            quest_fields.append(("can_repeat", quest.can_repeat))
        if quest.repeat_cooldown is not None:
            quest_fields.append(("repeat_cooldown", quest.repeat_cooldown))

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


def normalize_quest_corpus_ids(quest_root: Path) -> int:
    return _normalize_quest_corpus_ids_transaction(quest_root)


def write_catalog(catalog: Sequence[ChapterSpec], quest_root: Path) -> list[Path]:
    assert_no_id_collisions(catalog)
    normalize_quest_corpus_ids(quest_root)
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
            tokens.append(_SnbtToken(character, character, cursor, cursor + 1))
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
            tokens.append(_SnbtToken("string", value, start, cursor))
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
        tokens.append(_SnbtToken("bare", text[start:cursor], start, cursor))
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


class _SnbtPathScanner:
    def __init__(self, text: str) -> None:
        self.tokens = _tokenize_snbt(text)
        self.cursor = 0
        self.scalars: list[tuple[tuple[str | int, ...], _SnbtToken]] = []
        self.keys: list[tuple[tuple[str | int, ...], _SnbtToken]] = []

    def scan(
        self,
    ) -> tuple[
        tuple[tuple[tuple[str | int, ...], _SnbtToken], ...],
        tuple[tuple[tuple[str | int, ...], _SnbtToken], ...],
    ]:
        self._scan_value(())
        if self.cursor != len(self.tokens):
            token = self.tokens[self.cursor]
            raise SnbtParseError(
                f"trailing token {token.value!r} at offset {token.offset}"
            )
        return tuple(self.scalars), tuple(self.keys)

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

    def _scan_value(self, path: tuple[str | int, ...]) -> None:
        token = self._peek()
        if token is None:
            raise SnbtParseError("expected value, found end of input")
        if token.kind == "{":
            self._take("{")
            self._discard_commas()
            while self._peek() is not None and self._peek().kind != "}":
                key_token = self._take()
                if key_token.kind not in {"bare", "string"}:
                    raise SnbtParseError(
                        f"expected compound key at offset {key_token.offset}"
                    )
                self.keys.append((path, key_token))
                self._take(":")
                self._scan_value((*path, key_token.value))
                self._discard_commas()
            self._take("}")
            return
        if token.kind == "[":
            self._take("[")
            self._discard_commas()
            index = 0
            while self._peek() is not None and self._peek().kind != "]":
                self._scan_value((*path, index))
                index += 1
                self._discard_commas()
            self._take("]")
            return
        if token.kind not in {"bare", "string"}:
            raise SnbtParseError(
                f"expected value, found {token.value!r} at offset {token.offset}"
            )
        self.scalars.append((path, self._take()))


def _migration_localization_key(value: str) -> str:
    match = FTB_LOCALIZATION_KEY.fullmatch(value)
    if match is None:
        return value
    identifier = match.group("identifier")
    return (
        f"{match.group('prefix')}{ftb_safe_id(identifier)}{match.group('suffix')}"
    )


def _migration_snbt_role(
    relative: Path,
    path: tuple[str | int, ...],
) -> str | None:
    if relative == Path("chapter_groups.snbt"):
        if (
            len(path) == 3
            and path[0] == "chapter_groups"
            and isinstance(path[1], int)
            and path[2] == "id"
        ):
            return "definition"
        return None

    if len(relative.parts) == 2 and relative.parts[0] == "chapters":
        if path == ("id",):
            return "definition"
        if path in (("filename",), ("group",)):
            return "identity"
        if (
            len(path) == 3
            and path[0] == "quests"
            and isinstance(path[1], int)
            and path[2] == "id"
        ):
            return "definition"
        if (
            len(path) == 4
            and path[0] == "quests"
            and isinstance(path[1], int)
            and path[2] == "dependencies"
            and isinstance(path[3], int)
        ):
            return "identity"
        if (
            len(path) == 5
            and path[0] == "quests"
            and isinstance(path[1], int)
            and path[2] in {"tasks", "rewards"}
            and isinstance(path[3], int)
        ):
            if path[4] == "id":
                return "definition"
            if path[4] == "table_id":
                return "table_reference"
        return None

    if len(relative.parts) == 2 and relative.parts[0] == "reward_tables":
        if path == ("id",):
            return "definition"
        if (
            len(path) == 3
            and path[0] == "rewards"
            and isinstance(path[1], int)
        ):
            if path[2] == "id":
                return "definition"
            if path[2] == "table_id":
                return "table_reference"
    return None


def _migration_table_reference(value: str) -> str:
    match = re.fullmatch(r"(-?[0-9]+)L", value)
    if match is None:
        raise ValueError(f"malformed reward table reference: {value!r}")
    signed_value = int(match.group(1))
    if signed_value >= 0:
        return value
    unsigned_identifier = f"{signed_value & ((1 << 64) - 1):016X}"
    return f"{int(ftb_safe_id(unsigned_identifier), 16)}L"


def _migration_token_text(token: _SnbtToken, value: str) -> str:
    return _escape(value) if token.kind == "string" else value


def _migration_apply_replacements(
    text: str,
    replacements: Sequence[tuple[_SnbtToken, str]],
) -> str:
    migrated = text
    previous_offset = len(text)
    for token, value in sorted(
        replacements, key=lambda replacement: replacement[0].offset, reverse=True
    ):
        if token.end > previous_offset:
            raise ValueError("overlapping FTB ID migration replacements")
        migrated = (
            migrated[: token.offset]
            + _migration_token_text(token, value)
            + migrated[token.end :]
        )
        previous_offset = token.offset
    return migrated


def _migration_scan_snbt(
    relative: Path,
    text: str,
) -> tuple[str, tuple[tuple[str, str], ...]]:
    scalar_tokens, key_tokens = _SnbtPathScanner(text).scan()
    replacements: list[tuple[_SnbtToken, str]] = []
    definitions: list[tuple[str, str]] = []
    for path, token in scalar_tokens:
        role = _migration_snbt_role(relative, path)
        if role in {"definition", "identity"}:
            if token.kind != "string" or HEX_ID.fullmatch(token.value) is None:
                raise ValueError(
                    f"malformed FTB identity in {relative} at {path}: {token.value!r}"
                )
            target = ftb_safe_id(token.value)
            if role == "definition":
                definitions.append((target, f"{relative}:{path}"))
            if target != token.value:
                replacements.append((token, target))
        elif role == "table_reference":
            target = _migration_table_reference(token.value)
            if target != token.value:
                replacements.append((token, target))

    if relative.parts and relative.parts[0] == "lang":
        for parent_path, token in key_tokens:
            if parent_path:
                continue
            target = _migration_localization_key(token.value)
            if target != token.value:
                replacements.append((token, target))

    return _migration_apply_replacements(text, replacements), tuple(definitions)


def _migration_managed_state(text: str, path: Path) -> str:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid managed quest state {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError(f"invalid managed quest state {path}: root must be an object")
    chapters = data.get("chapters")
    localization_keys = data.get("localization_keys")
    if not isinstance(chapters, list) or not all(
        isinstance(value, str) for value in chapters
    ):
        raise ValueError(f"invalid managed chapter list in {path}")
    if not isinstance(localization_keys, list) or not all(
        isinstance(value, str) for value in localization_keys
    ):
        raise ValueError(f"invalid managed localization list in {path}")
    migrated_chapters = [
        ftb_safe_id(value) if HEX_ID.fullmatch(value) else value for value in chapters
    ]
    migrated_keys = [_migration_localization_key(value) for value in localization_keys]
    if migrated_chapters == chapters and migrated_keys == localization_keys:
        return text
    data["chapters"] = migrated_chapters
    data["localization_keys"] = migrated_keys
    return json.dumps(data, indent=2, sort_keys=True) + "\n"


def _migration_file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _migration_transaction_directory(quest_root: Path) -> Path:
    root_key = hashlib.sha256(
        os.fsencode(str(quest_root.resolve()))
    ).hexdigest()
    return (
        Path(tempfile.gettempdir())
        / "afterlight-quest-id-migrations"
        / root_key
    )


def _migration_relative_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"invalid migration {label}: {value!r}")
    relative = Path(value)
    if relative.is_absolute() or ".." in relative.parts or "." in relative.parts:
        raise ValueError(f"unsafe migration {label}: {value!r}")
    return relative


def _replace_migration_file(source: Path, target: Path, mode: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.", suffix=".migration", dir=target.parent
    )
    temp_path = Path(temp_name)
    try:
        with source.open("rb") as input_handle, os.fdopen(descriptor, "wb") as output_handle:
            shutil.copyfileobj(input_handle, output_handle)
            output_handle.flush()
            os.fsync(output_handle.fileno())
        os.chmod(temp_path, mode)
        os.replace(temp_path, target)
    finally:
        temp_path.unlink(missing_ok=True)


def _migration_apply_transaction(quest_root: Path, transaction: Path) -> int:
    journal_path = transaction / MIGRATION_JOURNAL_NAME
    try:
        journal = json.loads(journal_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid FTB ID migration journal {journal_path}: {error}") from error
    if not isinstance(journal, dict) or journal.get("version") != MIGRATION_TRANSACTION_VERSION:
        raise ValueError(f"invalid FTB ID migration journal version: {journal_path}")
    if journal.get("quest_root") != str(quest_root.resolve()):
        raise ValueError(f"FTB ID migration journal root mismatch: {journal_path}")
    writes = journal.get("writes")
    moves = journal.get("moves")
    changed = journal.get("changed")
    if not isinstance(writes, list) or not isinstance(moves, list) or not isinstance(changed, int):
        raise ValueError(f"invalid FTB ID migration journal operations: {journal_path}")

    move_by_source: dict[Path, dict[str, object]] = {}
    for move in moves:
        if not isinstance(move, dict):
            raise ValueError(f"invalid FTB ID migration move: {move!r}")
        source_relative = _migration_relative_path(move.get("source"), "move source")
        _migration_relative_path(move.get("target"), "move target")
        move_by_source[source_relative] = move

    for write in writes:
        if not isinstance(write, dict):
            raise ValueError(f"invalid FTB ID migration write: {write!r}")
        target_relative = _migration_relative_path(write.get("target"), "write target")
        payload_relative = _migration_relative_path(write.get("payload"), "write payload")
        before_sha256 = write.get("before_sha256")
        after_sha256 = write.get("after_sha256")
        mode = write.get("mode")
        if not all(
            isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value)
            for value in (before_sha256, after_sha256)
        ) or not isinstance(mode, int):
            raise ValueError(f"invalid FTB ID migration write metadata: {write!r}")
        payload = transaction / "stage" / payload_relative
        if not payload.is_file() or _migration_file_sha256(payload) != after_sha256:
            raise ValueError(f"invalid staged FTB ID migration payload: {payload}")
        target = quest_root / target_relative
        move = move_by_source.get(target_relative)
        if move is not None:
            move_target = quest_root / _migration_relative_path(
                move.get("target"), "move target"
            )
            if move_target.exists():
                if _migration_file_sha256(move_target) != after_sha256:
                    raise ValueError(
                        f"FTB ID migration target changed during recovery: {move_target}"
                    )
                if target.exists() and _migration_file_sha256(target) != after_sha256:
                    raise ValueError(
                        f"FTB ID migration source changed during recovery: {target}"
                    )
                continue
        if not target.is_file():
            raise ValueError(f"FTB ID migration write target is missing: {target}")
        current_sha256 = _migration_file_sha256(target)
        if current_sha256 == after_sha256:
            continue
        if current_sha256 != before_sha256:
            raise ValueError(f"FTB ID migration write target changed: {target}")
        _replace_migration_file(payload, target, mode)

    for move in moves:
        source_relative = _migration_relative_path(move.get("source"), "move source")
        target_relative = _migration_relative_path(move.get("target"), "move target")
        after_sha256 = move.get("after_sha256")
        if not isinstance(after_sha256, str):
            raise ValueError(f"invalid FTB ID migration move hash: {move!r}")
        source = quest_root / source_relative
        target = quest_root / target_relative
        if source.exists():
            if _migration_file_sha256(source) != after_sha256:
                raise ValueError(f"FTB ID migration source changed: {source}")
            if target.exists() and _migration_file_sha256(target) != after_sha256:
                raise ValueError(f"FTB ID migration target changed: {target}")
            source.replace(target)
        elif not target.is_file() or _migration_file_sha256(target) != after_sha256:
            raise ValueError(f"FTB ID migration move is incomplete: {source} -> {target}")

    _validate_migrated_quest_corpus(quest_root)
    journal_path.unlink()
    shutil.rmtree(transaction)
    try:
        transaction.parent.rmdir()
    except OSError:
        pass
    return changed


def _validate_migrated_quest_corpus(quest_root: Path) -> None:
    parsed_files: dict[Path, Any] = {}
    definition_owners: dict[str, list[str]] = {}
    for path in sorted(quest_root.rglob("*.snbt")):
        relative = path.relative_to(quest_root)
        text = path.read_text(encoding="utf-8")
        parsed_files[relative] = _parse_snbt(text)
        migrated, definitions = _migration_scan_snbt(relative, text)
        if migrated != text:
            raise ValueError(f"incomplete signed-safe FTB ID migration in {path}")
        for identifier, owner in definitions:
            definition_owners.setdefault(identifier, []).append(owner)
    collisions = {
        identifier: owners
        for identifier, owners in definition_owners.items()
        if len(owners) > 1
    }
    if collisions:
        raise ValueError(f"FTB signed-safe ID migration collisions: {collisions}")

    group_data = parsed_files.get(Path("chapter_groups.snbt"))
    if not isinstance(group_data, Mapping) or not isinstance(
        group_data.get("chapter_groups"), list
    ):
        raise ValueError("migrated chapter group registry is malformed")
    group_ids = {
        group.get("id")
        for group in group_data["chapter_groups"]
        if isinstance(group, Mapping) and isinstance(group.get("id"), str)
    }
    quest_ids: set[str] = set()
    dependencies: list[tuple[str, str]] = []
    table_references: list[tuple[str, int]] = []
    for relative, chapter in parsed_files.items():
        if len(relative.parts) != 2 or relative.parts[0] != "chapters":
            continue
        if not isinstance(chapter, Mapping):
            raise ValueError(f"migrated chapter is malformed: {relative}")
        chapter_id = chapter.get("id")
        if chapter_id != chapter.get("filename") or chapter_id != relative.stem:
            raise ValueError(f"migrated chapter path identity mismatch: {relative}")
        if chapter.get("group") not in group_ids:
            raise ValueError(f"migrated chapter group is unresolved: {relative}")
        quests = chapter.get("quests")
        if not isinstance(quests, list):
            raise ValueError(f"migrated chapter quest list is malformed: {relative}")
        for quest in quests:
            if not isinstance(quest, Mapping) or not isinstance(quest.get("id"), str):
                raise ValueError(f"migrated quest is malformed: {relative}")
            quest_id = quest["id"]
            quest_ids.add(quest_id)
            for dependency in quest.get("dependencies", []):
                if not isinstance(dependency, str):
                    raise ValueError(f"migrated dependency is malformed: {relative}")
                dependencies.append((quest_id, dependency))
            for reward in quest.get("rewards", []):
                if not isinstance(reward, Mapping):
                    raise ValueError(f"migrated reward is malformed: {relative}")
                table_id = reward.get("table_id")
                if table_id is not None:
                    match = re.fullmatch(r"([0-9]+)L", str(table_id))
                    if match is None:
                        raise ValueError(f"migrated table reference is malformed: {relative}")
                    table_references.append((quest_id, int(match.group(1))))

    unresolved_dependencies = [
        (quest_id, dependency)
        for quest_id, dependency in dependencies
        if dependency not in quest_ids
    ]
    if unresolved_dependencies:
        raise ValueError(
            f"migrated quest dependencies are unresolved: {unresolved_dependencies[:20]}"
        )

    table_ids = {
        int(table["id"], 16)
        for relative, table in parsed_files.items()
        if len(relative.parts) == 2
        and relative.parts[0] == "reward_tables"
        and isinstance(table, Mapping)
        and isinstance(table.get("id"), str)
    }
    unresolved_tables = [
        (quest_id, table_id)
        for quest_id, table_id in table_references
        if table_id not in table_ids
    ]
    if unresolved_tables:
        raise ValueError(
            f"migrated reward table references are unresolved: {unresolved_tables[:20]}"
        )

    state_path = quest_root / MANAGED_STATE_NAME
    if state_path.is_file():
        chapters, localization_keys = _load_managed_state(state_path)
        invalid_chapters = sorted(
            identifier
            for identifier in chapters
            if HEX_ID.fullmatch(identifier) is None or ftb_safe_id(identifier) != identifier
        )
        invalid_keys = sorted(
            key for key in localization_keys if _migration_localization_key(key) != key
        )
        if invalid_chapters or invalid_keys:
            raise ValueError(
                "managed quest state migration is incomplete: "
                f"chapters={invalid_chapters} localization_keys={invalid_keys}"
            )


def _migration_build_transaction(quest_root: Path, transaction: Path) -> bool:
    transformed: dict[Path, str] = {}
    definition_owners: dict[str, list[str]] = {}
    for path in sorted(quest_root.rglob("*.snbt")):
        relative = path.relative_to(quest_root)
        text = path.read_text(encoding="utf-8")
        migrated, definitions = _migration_scan_snbt(relative, text)
        if migrated != text:
            transformed[relative] = migrated
        for identifier, owner in definitions:
            definition_owners.setdefault(identifier, []).append(owner)

    state_path = quest_root / MANAGED_STATE_NAME
    if state_path.is_file():
        state_text = state_path.read_text(encoding="utf-8")
        migrated_state = _migration_managed_state(state_text, state_path)
        if migrated_state != state_text:
            transformed[Path(MANAGED_STATE_NAME)] = migrated_state

    collisions = {
        identifier: owners
        for identifier, owners in definition_owners.items()
        if len(owners) > 1
    }
    if collisions:
        raise ValueError(f"FTB signed-safe ID migration collisions: {collisions}")

    moves: list[tuple[Path, Path]] = []
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        if HEX_ID.fullmatch(path.stem) is None:
            continue
        target_id = ftb_safe_id(path.stem)
        if target_id == path.stem:
            continue
        target = path.with_name(f"{target_id}.snbt")
        if target.exists():
            raise ValueError(
                f"FTB signed-safe chapter migration target already exists: {target}"
            )
        moves.append((path.relative_to(quest_root), target.relative_to(quest_root)))

    if not transformed and not moves:
        return False

    transaction.parent.mkdir(parents=True, exist_ok=True)
    setup = Path(
        tempfile.mkdtemp(prefix=f".{transaction.name}.", dir=transaction.parent)
    )
    try:
        stage = setup / "stage"
        shutil.copytree(quest_root, stage)
        for relative, content in transformed.items():
            _atomic_write(stage / relative, content)
        for source_relative, target_relative in moves:
            (stage / source_relative).replace(stage / target_relative)
        _validate_migrated_quest_corpus(stage)

        move_targets = dict(moves)
        write_relatives = sorted(set(transformed) | {source for source, _target in moves})
        writes: list[dict[str, object]] = []
        for relative in write_relatives:
            payload_relative = move_targets.get(relative, relative)
            source = quest_root / relative
            payload = stage / payload_relative
            writes.append(
                {
                    "target": relative.as_posix(),
                    "payload": payload_relative.as_posix(),
                    "before_sha256": _migration_file_sha256(source),
                    "after_sha256": _migration_file_sha256(payload),
                    "mode": stat.S_IMODE(source.stat().st_mode),
                }
            )
        journal_moves = [
            {
                "source": source.as_posix(),
                "target": target.as_posix(),
                "after_sha256": _migration_file_sha256(stage / target),
            }
            for source, target in moves
        ]
        _atomic_write(
            setup / MIGRATION_JOURNAL_NAME,
            json.dumps(
                {
                    "version": MIGRATION_TRANSACTION_VERSION,
                    "quest_root": str(quest_root.resolve()),
                    "changed": len(transformed) + len(moves),
                    "writes": writes,
                    "moves": journal_moves,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        if transaction.exists():
            raise ValueError(f"FTB ID migration transaction already exists: {transaction}")
        os.replace(setup, transaction)
    finally:
        if setup.exists():
            shutil.rmtree(setup)
    return True


def _normalize_quest_corpus_ids_transaction(quest_root: Path) -> int:
    transaction = _migration_transaction_directory(quest_root)
    journal = transaction / MIGRATION_JOURNAL_NAME
    if transaction.exists() and not journal.is_file():
        shutil.rmtree(transaction)
    if journal.is_file():
        return _migration_apply_transaction(quest_root, transaction)
    if not _migration_build_transaction(quest_root, transaction):
        return 0
    return _migration_apply_transaction(quest_root, transaction)


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
                if ftb_safe_id(value) != value:
                    errors.append(f"non signed-safe FTB ID in {path}: {value}")
                else:
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
            dependency_requirement = quest.get("dependency_requirement")
            if (
                dependency_requirement is not None
                and dependency_requirement not in DEPENDENCY_REQUIREMENTS
            ):
                errors.append(
                    f"invalid dependency requirement in {path}: "
                    f"{dependency_requirement!r}"
                )
            progression_mode = quest.get("progression_mode")
            if progression_mode is not None and (
                not isinstance(progression_mode, str)
                or progression_mode not in PROGRESSION_MODES
            ):
                errors.append(
                    f"invalid progression mode in {path}: {progression_mode!r}"
                )

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
        if match:
            identifier = match.group(1)
            if not HEX_ID.fullmatch(identifier):
                errors.append(f"malformed IDs in localization key: {key}")
            elif ftb_safe_id(identifier) != identifier:
                errors.append(f"non signed-safe FTB ID in localization key: {key}")

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
