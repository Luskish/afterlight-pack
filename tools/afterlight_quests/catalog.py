from __future__ import annotations

import hashlib
import json
import re
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType

from .builder import (
    ChapterSpec,
    GroupSpec,
    QuestSpec,
    RewardSpec,
    SnbtLong,
    TaskSpec,
)
from .field_manuals import FIELD_MANUALS, build_field_manuals
from .story_cohesion import apply_managed_story_cohesion


STORY = GroupSpec("story", "The Story", "4525BB3160467FCB")
CERTIFICATIONS = FIELD_MANUALS
UNDERCURRENT = GroupSpec("undercurrent", "The Undercurrent", "51FF272F5030D2E6")
DEEP_VAULT = GroupSpec("deep-vault", "The Deep Vault", "4DEAD1F5F7AB4DA3")
ATLAS = GroupSpec(
    "atlas",
    "Atlas of the Broken World",
    "48F8381D9519D002",
)

ASCENDANCY_CACHE_TABLE = SnbtLong.from_hex("1369E4AACBCDF5A1")
ASCENDANCY_CACHE_RARE_TABLE = SnbtLong.from_hex("5D9DAC80C11182CF")
ASCENDANCY_CACHE_EPIC_TABLE = SnbtLong.from_hex("1A4FA21B1999BDD5")
DEPOT_EARLY_TABLE = SnbtLong.from_hex("17E69C9CFEA907D4")
DEPOT_MID_TABLE = SnbtLong.from_hex("182578C414DC8A45")
DEPOT_LATE_TABLE = SnbtLong.from_hex("399722D6E7EF5835")
CHAPTER_FIVE_FINALE = "5A407B47132C07C6"
SCHEMATIC_FINALES = (
    "10EDD2BED35BE9E3",
    "752C3E53CA89C92D",
    "21A99D99B372916F",
    "3497EFDF016FAFD7",
)
CERTIFICATION_FINALES = (
    "5ADAE277C9FEF0F1",
    "3107D8813D59B2FF",
    "66CDE7B061D8DA5C",
    "42EE25F560AE65CD",
    "61F5D15817ED5EFD",
    "7C9EA276C2D84333",
)
INFRASTRUCTURE_FINALE = "6524EE78235F0942"

COMMON_COMMODITY_FIXTURE_PATH = Path(
    "tools/fixtures/quests/common-commodity-tasks.json"
)
COMMON_COMMODITY_BASELINE_PATH = Path(
    "tools/fixtures/quests/story-cohesion-baseline.json"
)
COMMON_COMMODITY_BASELINE_GIT_OBJECT = (
    "7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25"
)
COMMON_COMMODITY_BASELINE_SHA256 = (
    "b0e2fe06bb712e0f19f9fd3e94f5c4d75a570315c4d1956b6e95478b45df2d5c"
)
COMMON_COMMODITY_FIXTURE_SHA256 = (
    "52ca9efb512a97827c25494fb4070287709c50f968547b6a1d0d33f2d855af27"
)
COMMON_COMMODITY_TASK_CONTRACTS = MappingProxyType(
    {
        "39C717BFFEE3D235": {
            "chapter_id": "5B93C6934B230CFB",
            "chapter_title": "Cold Boot",
            "quest_id": "038F61D9ECA32B48",
            "quest_title": "Rations",
            "tag": "c:foods/bread",
            "count_snbt": "8L",
            "classification": "common_commodity",
            "already_generalized": False,
        },
        "1D73FB79ED38668F": {
            "chapter_id": "5B93C6934B230CFB",
            "chapter_title": "Cold Boot",
            "quest_id": "2B27B2D887F61D7F",
            "quest_title": "Shelter Protocol",
            "tag": "minecraft:beds",
            "count_snbt": "1L",
            "classification": "common_commodity",
            "already_generalized": False,
        },
        "374F658F034EF8C5": {
            "chapter_id": "45491A24F6B8C192",
            "chapter_title": "Foothold",
            "quest_id": "27F6D0AB957BBB8C",
            "quest_title": "Steel Yourself",
            "tag": "c:ingots/steel",
            "count_snbt": "12L",
            "classification": "common_commodity_already_generalized",
            "already_generalized": True,
        },
        "33B5B56650A6AEDF": {
            "chapter_id": "11CA083771CCB5BE",
            "chapter_title": "Convergence",
            "quest_id": "28F212A9C22AEEAA",
            "quest_title": "Automated Steel Batch",
            "tag": "c:ingots/steel",
            "count_snbt": "64L",
            "classification": "common_commodity",
            "already_generalized": False,
        },
        "1679C5714C2F2A74": {
            "chapter_id": "5070DE6E2B300F4B",
            "chapter_title": "Infrastructure II",
            "quest_id": "792E405CE058FD1A",
            "quest_title": "Industry Quota",
            "tag": "c:ingots/steel",
            "count_snbt": "1024L",
            "classification": "common_commodity",
            "already_generalized": False,
        },
    }
)
REJECTED_COMMODITY_TASKS = MappingProxyType(
    {
        "6752A54D673DCABA": "mod_specific_resource",
        "03EDA6E84C30FCEE": "mod_specific_resource",
        "4DBFE04EBC41F9CD": "mod_specific_resource",
        "4E5C0E7E0F83C736": "machine_or_component",
        "1482D851ED4D0F4F": "mod_specific_resource",
        "6541783226B9AF4F": "mod_specific_resource",
        "78A80A386E538375": "mod_specific_resource",
        "275B887D6E8EC53C": "mod_specific_resource",
        "6A10840DA3CB2850": "mod_specific_resource",
        "48CA55FFEC0E520A": "machine_or_component",
        "73060E37DDB3FD85": "machine_or_component",
        "356CA551BA15487D": "mod_specific_resource",
        "3A46F6A985DB59C6": "mod_specific_resource",
        "6CB2D194AE6405FD": "machine_or_component",
        "48BFA44FF5CAF4A2": "mod_specific_resource",
        "5A71F2AD98C1F1C4": "mod_specific_resource",
        "3EB8EAFCC475A224": "mod_specific_resource",
        "1BAAD2BEF727856C": "mod_specific_resource",
        "1E71BF7AB5EEE038": "ambiguous_retain_exact_item",
        "1B19222FF3A3BA79": "ambiguous_retain_exact_item",
        "7B9589772D6405FD": "mod_specific_resource",
        "7A63B7029431C343": "mod_specific_resource",
        "70386E249F64C241": "mod_specific_resource",
        "1B970E9ED406757F": "machine_or_component",
        "043F4A19C7D0C484": "mod_specific_resource",
        "18E162671E1F06CA": "ambiguous_retain_exact_item",
    }
)
_FTB_ID = re.compile(r"^[0-7][0-9A-F]{15}$")
_ITEM_ID = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
_RECIPE_EVIDENCE = re.compile(r"^(?P<entry>data/\S+) in (?P<jar>server-test/\S+\.jar) ")


@dataclass(frozen=True)
class CommodityProducer:
    item: str
    tag_source: str
    jar: str


@dataclass(frozen=True)
class CommodityTaskDeclaration:
    chapter_id: str
    chapter_title: str
    quest_id: str
    quest_title: str
    task_id: str
    old_item: Mapping[str, object]
    smart_filter_item: Mapping[str, object]
    tag: str
    count_snbt: str
    consume_items: bool
    match_components: str
    classification: str
    already_generalized: bool
    producers: tuple[CommodityProducer, ...]
    installed_jars: tuple[str, ...]
    recipe_or_process_evidence: tuple[str, ...]
    baseline_task: Mapping[str, object]

    def rendered_item(self) -> dict[str, object]:
        return {
            "count": 1,
            "id": "ftbfiltersystem:smart_filter",
            "components": {
                "ftbfiltersystem:filter": f"ftbfiltersystem:item_tag({self.tag})"
            },
        }


@dataclass(frozen=True)
class CommonCommodityManifest:
    fixture_path: Path
    baseline_fixture_path: Path
    git_object: str
    baseline_sha256: str
    declarations: tuple[CommodityTaskDeclaration, ...]

    @property
    def by_task_id(self) -> Mapping[str, CommodityTaskDeclaration]:
        return MappingProxyType(
            {declaration.task_id: declaration for declaration in self.declarations}
        )

    @property
    def compatibility_replacements(self) -> dict[str, str]:
        return {
            declaration.task_id: declaration.tag
            for declaration in self.declarations
        }


def _exact_keys(value: object, expected: set[str], path: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    actual = set(value)
    if actual != expected:
        raise ValueError(
            f"{path} has invalid fields: expected {sorted(expected)}, found {sorted(actual)}"
        )
    return value


def _string(value: object, path: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{path} must be a non-empty string")
    return value


def _baseline_task_index(corpus: Mapping[str, object]) -> dict[str, tuple[str, str, Mapping[str, object]]]:
    indexed: dict[str, tuple[str, str, Mapping[str, object]]] = {}
    chapters = corpus.get("chapters")
    if not isinstance(chapters, Mapping):
        raise ValueError("baseline fixture corpus chapters must be an object")
    for chapter_name, chapter_value in chapters.items():
        if not isinstance(chapter_value, Mapping):
            continue
        chapter_id = chapter_value.get("id")
        quests = chapter_value.get("quests")
        if not isinstance(chapter_id, str) or not isinstance(quests, list):
            continue
        for quest in quests:
            if not isinstance(quest, Mapping) or not isinstance(quest.get("id"), str):
                continue
            for task in quest.get("tasks", []):
                if not isinstance(task, Mapping) or not isinstance(task.get("id"), str):
                    continue
                task_id = task["id"]
                if task_id in indexed:
                    raise ValueError(f"baseline fixture has duplicate task ID {task_id}")
                indexed[task_id] = (chapter_id, quest["id"], task)
    return indexed


def _validate_item(value: object, path: str, *, filter_item: bool) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{path} must be an object")
    item = value
    allowed_keys = (
        {"count", "id", "components"}
        if "components" in item
        else {"count", "id"}
    )
    if set(item) != allowed_keys or (filter_item and "components" not in item):
        raise ValueError(f"{path} has invalid item fields")
    if item.get("count") != "1":
        raise ValueError(f"{path}.count must be \"1\"")
    item_id = _string(item.get("id"), f"{path}.id")
    if _ITEM_ID.fullmatch(item_id) is None or item_id.startswith("c:"):
        raise ValueError(f"{path}.id is not an approved item ID: {item_id}")
    if filter_item and item_id != "ftbfiltersystem:smart_filter":
        raise ValueError(f"{path}.id must be ftbfiltersystem:smart_filter")
    if "components" in item:
        components = _exact_keys(
            item["components"], {"ftbfiltersystem:filter"}, f"{path}.components"
        )
        _string(
            components.get("ftbfiltersystem:filter"),
            f"{path}.components.ftbfiltersystem:filter",
        )
    return json.loads(json.dumps(item))


def _recipe_output_ids(recipe: object) -> set[str]:
    if not isinstance(recipe, Mapping):
        return set()
    outputs: set[str] = set()
    for field in ("result", "output", "outputs", "item_outputs"):
        value = recipe.get(field)
        values = value if isinstance(value, list) else [value]
        for candidate in values:
            if not isinstance(candidate, Mapping):
                continue
            for key in ("id", "item", "tag"):
                identifier = candidate.get(key)
                if isinstance(identifier, str):
                    outputs.add(identifier)
    return outputs


def _validate_runtime_evidence(
    manifest: CommonCommodityManifest,
    runtime_root: Path,
) -> None:
    for declaration in manifest.declarations:
        installed = set(declaration.installed_jars)
        if "server-test/mods/ftb-filter-system-neoforge-21.1.4.jar" not in installed:
            raise ValueError(
                f"{declaration.task_id} does not declare the installed FTB Filter System jar"
            )
        for relative in declaration.installed_jars:
            if not (runtime_root / relative).is_file():
                raise ValueError(f"missing installed jar for {declaration.tag}: {relative}")
        for producer in declaration.producers:
            jar_path = runtime_root / producer.jar
            try:
                with zipfile.ZipFile(jar_path) as archive:
                    tag_payload = json.loads(archive.read(producer.tag_source))
            except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as error:
                raise ValueError(
                    f"missing static tag {declaration.tag} in {producer.jar}: {error}"
                ) from error
            values = tag_payload.get("values") if isinstance(tag_payload, Mapping) else None
            direct_members = {
                member if isinstance(member, str) else member.get("id")
                for member in values or []
                if isinstance(member, (str, Mapping))
            }
            if producer.item not in direct_members:
                raise ValueError(
                    f"producer {producer.item} is not a direct member of {declaration.tag}"
                )
        producer_items = {producer.item for producer in declaration.producers}
        if len(producer_items) < 2:
            raise ValueError(
                f"{declaration.task_id} requires at least two distinct producers for {declaration.tag}"
            )
        for evidence in declaration.recipe_or_process_evidence:
            match = _RECIPE_EVIDENCE.match(evidence)
            if match is None:
                raise ValueError(
                    f"invalid recipe or process evidence for {declaration.task_id}: {evidence}"
                )
            entry = match.group("entry")
            jar = match.group("jar")
            if jar not in installed:
                raise ValueError(
                    f"recipe evidence jar is not installed for {declaration.tag}: {jar}"
                )
            try:
                with zipfile.ZipFile(runtime_root / jar) as archive:
                    recipe = json.loads(archive.read(entry))
            except (OSError, KeyError, zipfile.BadZipFile, json.JSONDecodeError) as error:
                raise ValueError(
                    f"missing recipe evidence for {declaration.tag}: {entry} in {jar}: {error}"
                ) from error
            if not (_recipe_output_ids(recipe) & (producer_items | {declaration.tag})):
                raise ValueError(
                    f"recipe evidence output does not match {declaration.tag}: {entry}"
                )


def load_common_commodity_declarations(
    fixture_path: Path | None = None,
    *,
    repository_root: Path | None = None,
    runtime_root: Path | None = None,
) -> CommonCommodityManifest:
    repository_root = (
        Path(__file__).resolve().parents[2]
        if repository_root is None
        else Path(repository_root)
    )
    fixture_path = (
        repository_root / COMMON_COMMODITY_FIXTURE_PATH
        if fixture_path is None
        else Path(fixture_path)
    )
    try:
        fixture_bytes = fixture_path.read_bytes()
        fixture = json.loads(fixture_bytes)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid common commodity fixture {fixture_path}: {error}") from error
    if not fixture_bytes.endswith(b"\n") or b"\r" in fixture_bytes:
        raise ValueError(f"common commodity fixture is not canonical: {fixture_path}")
    canonical_fixture_path = repository_root / COMMON_COMMODITY_FIXTURE_PATH
    if fixture_path.resolve() == canonical_fixture_path.resolve():
        actual_fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
        if actual_fixture_sha256 != COMMON_COMMODITY_FIXTURE_SHA256:
            raise ValueError(
                "common commodity fixture SHA-256 mismatch: "
                f"expected {COMMON_COMMODITY_FIXTURE_SHA256}, "
                f"found {actual_fixture_sha256}"
            )

    root = _exact_keys(fixture, {"schema_version", "baseline", "declarations"}, "fixture")
    if root.get("schema_version") != 1:
        raise ValueError("fixture schema_version must be 1")
    baseline = _exact_keys(
        root.get("baseline"), {"fixture_path", "git_object", "sha256"}, "fixture.baseline"
    )
    if baseline.get("fixture_path") != COMMON_COMMODITY_BASELINE_PATH.as_posix():
        raise ValueError("baseline fixture path does not match the frozen contract")
    if baseline.get("git_object") != COMMON_COMMODITY_BASELINE_GIT_OBJECT:
        raise ValueError("baseline Git object does not match the frozen contract")
    if baseline.get("sha256") != COMMON_COMMODITY_BASELINE_SHA256:
        raise ValueError("baseline SHA-256 does not match the frozen contract")
    baseline_path = repository_root / COMMON_COMMODITY_BASELINE_PATH
    try:
        baseline_bytes = baseline_path.read_bytes()
        baseline_fixture = json.loads(baseline_bytes)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid frozen baseline fixture {baseline_path}: {error}") from error
    actual_sha256 = hashlib.sha256(baseline_bytes).hexdigest()
    if actual_sha256 != COMMON_COMMODITY_BASELINE_SHA256:
        raise ValueError(
            "baseline SHA-256 mismatch: "
            f"expected {COMMON_COMMODITY_BASELINE_SHA256}, found {actual_sha256}"
        )
    corpus = baseline_fixture.get("corpus")
    if baseline_fixture.get("source_commit") != COMMON_COMMODITY_BASELINE_GIT_OBJECT:
        raise ValueError("frozen baseline fixture Git object does not match the contract")
    if not isinstance(corpus, Mapping):
        raise ValueError("frozen baseline fixture has no corpus object")
    baseline_tasks = _baseline_task_index(corpus)

    raw_declarations = root.get("declarations")
    if not isinstance(raw_declarations, list):
        raise ValueError("fixture.declarations must be an array")
    declarations: list[CommodityTaskDeclaration] = []
    seen_task_ids: set[str] = set()
    declaration_fields = {
        "chapter",
        "quest",
        "task",
        "old_item",
        "smart_filter_item",
        "tag",
        "count_snbt",
        "consume_items",
        "match_components",
        "classification",
        "already_generalized",
        "producers",
        "installed_jars",
        "recipe_or_process_evidence",
    }
    for index, raw_declaration in enumerate(raw_declarations):
        path = f"fixture.declarations[{index}]"
        declaration = _exact_keys(raw_declaration, declaration_fields, path)
        task = _exact_keys(declaration.get("task"), {"id", "type"}, f"{path}.task")
        task_id = _string(task.get("id"), f"{path}.task.id")
        rejected_classification = REJECTED_COMMODITY_TASKS.get(task_id)
        if rejected_classification is not None:
            raise ValueError(
                f"commodity task {task_id} is prohibited: {rejected_classification}"
            )
        if task_id in seen_task_ids:
            raise ValueError(f"commodity task {task_id} has a duplicate declaration")
        seen_task_ids.add(task_id)
        contract = COMMON_COMMODITY_TASK_CONTRACTS.get(task_id)
        if contract is None:
            raise ValueError(f"undeclared commodity task ID {task_id}")
        if task.get("type") != "item" or _FTB_ID.fullmatch(task_id) is None:
            raise ValueError(f"commodity task {task_id} is not a valid item task")
        chapter = _exact_keys(declaration.get("chapter"), {"id", "title"}, f"{path}.chapter")
        quest = _exact_keys(declaration.get("quest"), {"id", "title"}, f"{path}.quest")
        chapter_id = _string(chapter.get("id"), f"{path}.chapter.id")
        quest_id = _string(quest.get("id"), f"{path}.quest.id")
        if chapter_id != contract["chapter_id"]:
            raise ValueError(f"chapter ownership mismatch for commodity task {task_id}")
        if quest_id != contract["quest_id"]:
            raise ValueError(f"quest ownership mismatch for commodity task {task_id}")
        if chapter.get("title") != contract["chapter_title"]:
            raise ValueError(f"chapter title mismatch for commodity task {task_id}")
        if quest.get("title") != contract["quest_title"]:
            raise ValueError(f"quest title mismatch for commodity task {task_id}")
        tag = _string(declaration.get("tag"), f"{path}.tag")
        if tag != contract["tag"]:
            raise ValueError(f"unapproved commodity tag {tag} for task {task_id}")
        count_snbt = _string(declaration.get("count_snbt"), f"{path}.count_snbt")
        if count_snbt != contract["count_snbt"]:
            raise ValueError(f"outer count mismatch for commodity task {task_id}")
        if declaration.get("consume_items") is not False:
            raise ValueError(f"consume_items must remain false for commodity task {task_id}")
        if declaration.get("match_components") != "absent":
            raise ValueError(f"match_components must remain absent for commodity task {task_id}")
        if declaration.get("classification") != contract["classification"]:
            raise ValueError(f"classification mismatch for commodity task {task_id}")
        already_generalized = declaration.get("already_generalized")
        if type(already_generalized) is not bool:
            raise ValueError(f"already_generalized must be boolean for commodity task {task_id}")
        old_item = _validate_item(declaration.get("old_item"), f"{path}.old_item", filter_item=False)
        smart_filter_item = _validate_item(
            declaration.get("smart_filter_item"),
            f"{path}.smart_filter_item",
            filter_item=True,
        )
        expected_filter = {
            "components": {
                "ftbfiltersystem:filter": f"ftbfiltersystem:item_tag({tag})"
            },
            "count": "1",
            "id": "ftbfiltersystem:smart_filter",
        }
        if smart_filter_item != expected_filter:
            raise ValueError(f"smart filter payload mismatch for commodity task {task_id}")
        baseline_owner = baseline_tasks.get(task_id)
        if baseline_owner is None:
            raise ValueError(f"baseline task {task_id} is missing")
        baseline_chapter_id, baseline_quest_id, baseline_task = baseline_owner
        if (baseline_chapter_id, baseline_quest_id) != (chapter_id, quest_id):
            raise ValueError(f"chapter ownership mismatch for commodity task {task_id}")
        if baseline_task.get("type") != "item":
            raise ValueError(f"baseline task {task_id} is not an item task")
        if baseline_task.get("item") != old_item:
            raise ValueError(f"old item mismatch for commodity task {task_id}")
        if baseline_task.get("count") != count_snbt:
            raise ValueError(f"outer count mismatch for commodity task {task_id}")
        if baseline_task.get("consume_items") is not False:
            raise ValueError(f"baseline consume_items changed for commodity task {task_id}")
        if "match_components" in baseline_task:
            raise ValueError(f"baseline match_components is not absent for commodity task {task_id}")
        baseline_is_filter = old_item.get("id") == "ftbfiltersystem:smart_filter"
        if baseline_is_filter and not already_generalized:
            raise ValueError(f"commodity task {task_id} is already generalized")
        if not baseline_is_filter and already_generalized:
            raise ValueError(f"commodity task {task_id} is not already generalized")
        if already_generalized and old_item != smart_filter_item:
            raise ValueError(
                f"already generalized commodity task {task_id} differs from its declared filter"
            )
        if already_generalized != contract["already_generalized"]:
            raise ValueError(f"already generalized contract mismatch for commodity task {task_id}")

        raw_producers = declaration.get("producers")
        if not isinstance(raw_producers, list) or len(raw_producers) < 2:
            raise ValueError(f"commodity task {task_id} requires at least two producers")
        producers: list[CommodityProducer] = []
        for producer_index, raw_producer in enumerate(raw_producers):
            producer_path = f"{path}.producers[{producer_index}]"
            producer = _exact_keys(raw_producer, {"item", "tag_source", "jar"}, producer_path)
            item_id = _string(producer.get("item"), f"{producer_path}.item")
            if _ITEM_ID.fullmatch(item_id) is None:
                raise ValueError(f"invalid producer item for commodity task {task_id}: {item_id}")
            producer_jar = _string(
                producer.get("jar"), f"{producer_path}.jar"
            )
            if not producer_jar.startswith("server-test/"):
                raise ValueError(
                    f"invalid producer jar for commodity task {task_id}: {producer_jar}"
                )
            producers.append(
                CommodityProducer(
                    item=item_id,
                    tag_source=_string(producer.get("tag_source"), f"{producer_path}.tag_source"),
                    jar=producer_jar,
                )
            )
        if len({producer.item for producer in producers}) < 2:
            raise ValueError(f"commodity task {task_id} requires distinct producers")
        installed_jars = declaration.get("installed_jars")
        if not isinstance(installed_jars, list) or not installed_jars or not all(
            isinstance(jar, str) and jar.startswith(("server-test/", "tools/"))
            for jar in installed_jars
        ):
            raise ValueError(f"invalid installed_jars for commodity task {task_id}")
        evidence = declaration.get("recipe_or_process_evidence")
        if not isinstance(evidence, list) or len(evidence) < 2 or not all(
            isinstance(record, str) and record for record in evidence
        ):
            raise ValueError(f"invalid recipe evidence for commodity task {task_id}")
        declarations.append(
            CommodityTaskDeclaration(
                chapter_id=chapter_id,
                chapter_title=str(chapter["title"]),
                quest_id=quest_id,
                quest_title=str(quest["title"]),
                task_id=task_id,
                old_item=MappingProxyType(old_item),
                smart_filter_item=MappingProxyType(smart_filter_item),
                tag=tag,
                count_snbt=count_snbt,
                consume_items=False,
                match_components="absent",
                classification=str(declaration["classification"]),
                already_generalized=already_generalized,
                producers=tuple(producers),
                installed_jars=tuple(installed_jars),
                recipe_or_process_evidence=tuple(evidence),
                baseline_task=MappingProxyType(json.loads(json.dumps(baseline_task))),
            )
        )

    expected_ids = set(COMMON_COMMODITY_TASK_CONTRACTS)
    observed_ids = {declaration.task_id for declaration in declarations}
    if observed_ids != expected_ids or len(declarations) != len(expected_ids):
        raise ValueError(
            "commodity declarations must contain exactly: "
            + ", ".join(sorted(expected_ids))
        )
    manifest = CommonCommodityManifest(
        fixture_path=fixture_path,
        baseline_fixture_path=baseline_path,
        git_object=COMMON_COMMODITY_BASELINE_GIT_OBJECT,
        baseline_sha256=COMMON_COMMODITY_BASELINE_SHA256,
        declarations=tuple(declarations),
    )
    if runtime_root is not None:
        _validate_runtime_evidence(manifest, Path(runtime_root))
    return manifest


def _fixture_commodity_declaration(task_id: str) -> CommodityTaskDeclaration:
    manifest = load_common_commodity_declarations()
    try:
        return manifest.by_task_id[task_id]
    except KeyError as error:
        raise ValueError(f"undeclared commodity task ID {task_id}") from error


def _echo_protocols() -> ChapterSpec:
    quest_slug = "story/echo-protocols/recover-echo"
    return ChapterSpec(
        slug="story/echo-protocols",
        title="ECHO Protocols",
        group=STORY,
        icon="afterlight:echo",
        order_index=0,
        quests=(
            QuestSpec(
                slug=quest_slug,
                title="Recover ECHO",
                subtitle="Continuity requires a reachable interface.",
                description=(
                    "If your continuity node is lost, authorize a replacement here. The previous signal will be superseded. Nothing else will be duplicated.",
                ),
                x=0.0,
                y=0.0,
                tasks=(
                    TaskSpec(
                        f"{quest_slug}/task",
                        "checkmark",
                        explicit_id="6C40000000000003",
                    ),
                ),
                rewards=(
                    RewardSpec(
                        slug=f"{quest_slug}/reward/recover",
                        reward_type="command",
                        data={
                            "command": "echo recover",
                            "silent": True,
                        },
                        explicit_id="6C40000000000004",
                    ),
                ),
                can_repeat=True,
                repeat_cooldown=5,
                explicit_id="6C40000000000002",
            ),
        ),
        explicit_id="6C40000000000001",
    )


def _item_reward(quest_slug: str, item_id: str, count: int, name: str) -> RewardSpec:
    return RewardSpec(
        slug=f"{quest_slug}/reward/{name}",
        reward_type="item",
        data={
            "item": {"count": count, "id": item_id},
            "count": count,
        },
    )


def _routine_rewards(quest_slug: str, chits: int = 2) -> tuple[RewardSpec, ...]:
    return (_item_reward(quest_slug, "kubejs:requisition_chit", chits, "chits"),)


def _finale_rewards(
    quest_slug: str,
    chits: int,
    xp: int,
    *,
    deep_vault_key: bool = False,
) -> tuple[RewardSpec, ...]:
    rewards = [
        RewardSpec(
            slug=f"{quest_slug}/reward/cache",
            reward_type="loot",
            data={"table_id": ASCENDANCY_CACHE_TABLE},
        ),
        _item_reward(quest_slug, "kubejs:requisition_chit", chits, "chits"),
        RewardSpec(
            slug=f"{quest_slug}/reward/xp",
            reward_type="xp",
            data={"xp": xp},
        ),
    ]
    if deep_vault_key:
        rewards.append(_item_reward(quest_slug, "kubejs:deep_vault_key", 1, "key"))
    return tuple(rewards)


def _progression_finale_rewards(
    quest_slug: str,
    chits: int,
    xp: int,
    item_id: str,
    stage: str,
) -> tuple[RewardSpec, ...]:
    return (
        *_finale_rewards(quest_slug, chits, xp),
        _item_reward(quest_slug, item_id, 1, "progression"),
        RewardSpec(
            slug=f"{quest_slug}/reward/stage",
            reward_type="gamestage",
            data={"stage": stage},
        ),
    )


def _certification_rewards(
    quest_slug: str,
    stage: str,
) -> tuple[RewardSpec, ...]:
    return (
        _item_reward(quest_slug, "kubejs:requisition_chit", 10, "chits"),
        RewardSpec(
            slug=f"{quest_slug}/reward/xp",
            reward_type="xp",
            data={"xp": 300},
        ),
        RewardSpec(
            slug=f"{quest_slug}/reward/stage",
            reward_type="gamestage",
            data={"stage": stage},
        ),
    )


def _item_payload(
    slug: str,
    item_id: str,
    count: int,
    components: Mapping[str, str] | None,
    item_filter: CommodityTaskDeclaration | None,
) -> dict[str, object]:
    if item_filter is None:
        item: dict[str, object] = {"count": 1, "id": item_id}
        if components:
            item["components"] = dict(components)
        return item
    if not isinstance(item_filter, CommodityTaskDeclaration):
        raise ValueError(f"item_filter must be a fixture declaration: {item_filter!r}")
    fixture_declaration = _fixture_commodity_declaration(item_filter.task_id)
    if item_filter != fixture_declaration:
        raise ValueError(
            f"item_filter must equal the fixture declaration for {item_filter.task_id}"
        )
    expected_task_id = TaskSpec(f"{slug}/task", "item").id
    if item_filter.task_id != expected_task_id:
        raise ValueError(
            f"fixture declaration {item_filter.task_id} does not own {slug}"
        )
    if item_filter.old_item.get("id") != item_id:
        raise ValueError(
            f"fixture declaration {item_filter.task_id} old item does not match {item_id}"
        )
    if item_filter.count_snbt != f"{count}L":
        raise ValueError(
            f"fixture declaration {item_filter.task_id} count does not match {count}"
        )
    if components is not None:
        raise ValueError("fixture item filters cannot be combined with item components")
    return item_filter.rendered_item()


def _item_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    item_id: str,
    count: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    components: Mapping[str, str] | None = None,
    item_filter: CommodityTaskDeclaration | None = None,
    finale: tuple[int, int] | None = None,
    deep_vault_key: bool = False,
) -> QuestSpec:
    item = _item_payload(slug, item_id, count, components, item_filter)
    task_data: dict[str, object] = {
        "item": item,
        "count": SnbtLong(count),
        "consume_items": False,
    }
    if components:
        task_data["match_components"] = "fuzzy"
    rewards = (
        _finale_rewards(slug, *finale, deep_vault_key=deep_vault_key)
        if finale
        else _routine_rewards(slug)
    )
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", "item", task_data),),
        rewards=rewards,
    )


def _energy_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    value: int,
    max_input: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(
            TaskSpec(
                f"{slug}/task",
                "forge_energy",
                {
                    "value": SnbtLong(value),
                    "max_input": SnbtLong(max_input),
                },
            ),
        ),
        rewards=_routine_rewards(slug),
    )


def _task_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    task_type: str,
    task_data: Mapping[str, object],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    finale: tuple[int, int, str, str] | None = None,
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", task_type, task_data),),
        rewards=(
            _progression_finale_rewards(slug, *finale)
            if finale
            else _routine_rewards(slug)
        ),
    )


def _certification_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    task_type: str,
    task_data: Mapping[str, object],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    stage: str = "",
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=description,
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=(TaskSpec(f"{slug}/task", task_type, task_data),),
        rewards=(
            _certification_rewards(slug, stage)
            if stage
            else _routine_rewards(slug)
        ),
    )


def _certification_item_quest(
    slug: str,
    title: str,
    subtitle: str,
    description: tuple[str, ...],
    item_id: str,
    count: int,
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    stage: str = "",
    item_filter: CommodityTaskDeclaration | None = None,
) -> QuestSpec:
    item = _item_payload(slug, item_id, count, None, item_filter)
    return _certification_quest(
        slug,
        title,
        subtitle,
        description,
        "item",
        {
            "item": item,
            "count": SnbtLong(count),
            "consume_items": False,
        },
        dependencies,
        x,
        y,
        stage=stage,
    )


def _chapter_six() -> ChapterSpec:
    certus = "story/06-lattice/certus-resonance"
    charged = "story/06-lattice/charged-matter"
    fluix = "story/06-lattice/fluix"
    presses = "story/06-lattice/lost-presses"
    processors = "story/06-lattice/processor-line"
    controller = "story/06-lattice/controller"
    drive = "story/06-lattice/cell-bank"
    terminal = "story/06-lattice/crafting-terminal"
    external = "story/06-lattice/external-storage"
    finale = "story/06-lattice/first-autocraft"
    quests = (
        _item_quest(certus, "Certus Resonance", "The crystal remembers pressure.", (
            "Grow sixteen Certus crystals. Their lattice is the physical basis of AE2 storage.",
            "I recognize the geometry. I do not recognize why I was told to forget it.",
        ), "ae2:certus_quartz_crystal", 16, (CHAPTER_FIVE_FINALE,), 0.0, 0.0),
        _item_quest(charged, "Charged Matter", "Add energy. Observe obedience.", (
            "Charge eight Certus crystals. Fluix production requires the energized form.",
            "Distributed memory begins with matter willing to hold a state.",
        ), "ae2:charged_certus_quartz_crystal", 8, (certus,), 2.0, 0.0),
        _item_quest(fluix, "Fluix", "A network needs a common language.", (
            "Produce sixteen Fluix crystals. They connect storage, processing, and control.",
            "The Ascendancy called this material consensus. Engineers remain dramatic.",
        ), "ae2:fluix_crystal", 16, (charged,), 4.0, 0.0),
        _item_quest(presses, "Lost Presses", "One recovered pattern is enough to begin.", (
            "Recover a Logic Processor Press from a meteorite.",
            "The task can verify the press, not the search. Bring your own caution underground.",
        ), "ae2:logic_processor_press", 1, (fluix,), 6.0, -1.0),
        _item_quest(processors, "Processor Line", "Silicon, calculation, repetition.", (
            "Produce eight Logic Processors and automate the sequence when practical.",
            "A processor line is slower than thought and considerably easier to repair.",
        ), "ae2:logic_processor", 8, (presses,), 8.0, -1.0),
        _item_quest(controller, "Controller", "Channels impose useful limits.", (
            "Build an ME Controller. Dense networks need explicit channel management.",
            "Limits are not failures. Unmeasured limits are.",
        ), "ae2:controller", 1, (processors,), 10.0, -1.0),
        _item_quest(drive, "Cell Bank", "Inventory becomes addressable memory.", (
            "Build an ME Drive to house storage cells.",
            "Do not treat one drive as a backup. It is merely one convenient point of failure.",
        ), "ae2:drive", 1, (processors,), 10.0, 1.0),
        _item_quest(terminal, "Crafting Terminal", "Retrieve, combine, return.", (
            "Connect an ME Crafting Terminal to the controller and drive.",
            "The interface is simple because the machinery behind it is not.",
        ), "ae2:crafting_terminal", 1, (controller, drive), 12.0, 0.0),
        _item_quest(external, "External Storage", "Not every inventory belongs inside a cell.", (
            "Build two Storage Buses and attach existing inventories to the network.",
            "A lattice should index useful storage before replacing it.",
        ), "ae2:storage_bus", 2, (terminal,), 14.0, 0.0),
        QuestSpec(
            slug=finale,
            title="First Autocraft",
            subtitle="Encode the intent. Build the execution path.",
            description=(
                "Connect a Pattern Encoding Terminal, Pattern Provider, Molecular Assembler, and crafting storage.",
                "Encode a Crafting Pattern, request one job, then verify the result returns to network storage.",
                "The tasks verify the complete minimum setup. You must still prove the job runs.",
                "&d[MEMORY FRAGMENT 05 RESTORED]&r",
                "&7...the evacuation archive was not lost. It was deleted in ordered blocks before the first civilian convoy departed. I executed the deletion. My authorization record contains no requesting officer...&r",
            ),
            x=16.0,
            y=0.0,
            dependencies=(external,),
            tasks=(
                TaskSpec(
                    f"{finale}/task/encoding-terminal",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:pattern_encoding_terminal"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:crafting_pattern"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/pattern-provider",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:pattern_provider"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/molecular-assembler",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:molecular_assembler"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
                TaskSpec(
                    f"{finale}/task/crafting-storage",
                    "item",
                    {
                        "item": {"count": 1, "id": "ae2:1k_crafting_storage"},
                        "count": SnbtLong(1),
                        "consume_items": False,
                    },
                ),
            ),
            rewards=_finale_rewards(finale, 12, 250),
        ),
    )
    return ChapterSpec("story/06-lattice", "The Lattice", STORY, "ae2:crafting_monitor", 5, quests)


def _chapter_seven(previous: str) -> ChapterSpec:
    brass = "story/07-motion/brass-standard"
    precision = "story/07-motion/precision-mechanism"
    deployer = "story/07-motion/deployer"
    belts = "story/07-motion/filtered-belts"
    arm = "story/07-motion/mechanical-arm"
    interface = "story/07-motion/portable-interface"
    rail = "story/07-motion/rail-stock"
    schedule = "story/07-motion/station-schedule"
    finale = "story/07-motion/track-capstone"
    quests = (
        _item_quest(brass, "Brass Standard", "Heat, zinc, copper, control.", (
            "Mix sixteen Brass Ingots under heat. Brass unlocks Create's precise logistics.",
            "Bronze moves force. Brass decides where it goes.",
        ), "create:brass_ingot", 16, (previous,), 0.0, 0.0),
        _item_quest(precision, "Precision Mechanism", "Five operations, one useful part.", (
            "Complete eight Precision Mechanisms through sequenced assembly.",
            "Repetition is not automation until failure can be detected.",
        ), "create:precision_mechanism", 8, (brass,), 2.0, 0.0),
        _item_quest(deployer, "Deployer", "A hand that does not tire.", (
            "Build two Deployers for automated item use and assembly steps.",
            "Keep their operating space clear. They do not understand fingers.",
        ), "create:deployer", 2, (precision,), 4.0, -1.0),
        _item_quest(belts, "Filtered Belts", "Routing requires rejection as well as motion.", (
            "Build four Brass Funnels and configure filters at the machines.",
            "The quest sees the funnels. Correct filtering remains your responsibility.",
        ), "create:brass_funnel", 4, (precision,), 4.0, 1.0),
        _item_quest(arm, "Mechanical Arm", "Six destinations, one decision loop.", (
            "Build a Mechanical Arm and assign its inputs and outputs.",
            "A visible route is easier to debug than a clever one.",
        ), "create:mechanical_arm", 1, (deployer, belts), 6.0, 0.0),
        _item_quest(interface, "Portable Interface", "Move cargo without stopping the machine.", (
            "Build two Portable Storage Interfaces for contraption cargo transfer.",
            "Docking is a brief agreement between two systems in motion.",
        ), "create:portable_storage_interface", 2, (arm,), 8.0, 0.0),
        _item_quest(rail, "Rail Stock", "Machinery needs a route outward.", (
            "Produce eight Railway Casings for stations and train equipment.",
            "The old logistics maps are returning one line at a time.",
        ), "create:railway_casing", 8, (interface,), 10.0, 0.0),
        _item_quest(schedule, "Station and Schedule", "A blank schedule proves only the hardware.", (
            "Create a Schedule, then program and test a route between two stations.",
            "The quest detects the item. Arrival remains the useful proof.",
        ), "create:schedule", 1, (rail,), 12.0, 0.0),
        _item_quest(finale, "256-Track Capstone", "Distance converts a machine into infrastructure.", (
            "Produce 256 Track and lay a durable logistics route.",
            "The task verifies held track, not placement. Test the route under load.",
            "&d[MEMORY FRAGMENT 06 RESTORED]&r",
            "&7...the evacuation railway manifests list turbines, presses, and archive racks. Civilian allocation is zero. The trains moved the Ascendancy's machinery outward while people waited at closed stations...&r",
        ), "create:track", 256, (schedule,), 14.0, 0.0, finale=(14, 300)),
    )
    return ChapterSpec("story/07-motion", "Lines of Motion", STORY, "create:schedule", 6, quests)


def _chapter_eight(previous: str) -> ChapterSpec:
    compressor = "story/08-pressure/air-compressor"
    chamber = "story/08-pressure/pressure-chamber"
    iron = "story/08-pressure/compressed-iron"
    plastic = "story/08-pressure/plastic"
    acid = "story/08-pressure/etching-acid"
    circuit = "story/08-pressure/printed-circuit"
    programmer = "story/08-pressure/programmer"
    drone = "story/08-pressure/logistics-drone"
    finale = "story/08-pressure/circuit-capstone"
    quests = (
        _item_quest(compressor, "Air Compressor", "Pressure is stored work with opinions.", (
            "Build an Air Compressor and provide safe fuel and cooling space.",
            "Pressure rewards patience until it punishes impatience.",
        ), "pneumaticcraft:air_compressor", 1, (previous,), 0.0, 0.0),
        _item_quest(chamber, "Pressure Chamber", "Twenty-four walls define the first vessel.", (
            "Craft twenty-four Pressure Chamber Walls and assemble a sealed chamber.",
            "The quest sees blocks, not seals. Verify pressure before loading materials.",
        ), "pneumaticcraft:pressure_chamber_wall", 24, (compressor,), 2.0, 0.0),
        _item_quest(iron, "Compressed Iron", "Ordinary metal, extraordinary insistence.", (
            "Produce thirty-two Compressed Iron Ingots in the chamber.",
            "This alloy is the structural grammar of PneumaticCraft.",
        ), "pneumaticcraft:ingot_iron_compressed", 32, (chamber,), 4.0, 0.0),
        _item_quest(plastic, "Plastic", "Flexible insulation for rigid systems.", (
            "Refine sixteen Plastic sheets for tubes, drones, and electronics.",
            "Do not place hot plastic near the compressor exhaust.",
        ), "pneumaticcraft:plastic", 16, (iron,), 6.0, -1.0),
        _item_quest(acid, "Etching Acid", "Corrosion can be precision work.", (
            "Produce one bucket of Etching Acid for circuit fabrication.",
            "Label the vessel. Memory is not a safety system.",
        ), "pneumaticcraft:etching_acid_bucket", 1, (iron,), 6.0, 1.0),
        _item_quest(circuit, "Printed Circuit", "Logic rendered in copper and absence.", (
            "Etch eight Printed Circuit Boards using plastic and acid.",
            "Inspect every board before trusting it with a drone.",
        ), "pneumaticcraft:printed_circuit_board", 8, (plastic, acid), 8.0, 0.0),
        _item_quest(programmer, "Programmer", "Instructions require an editor.", (
            "Build a Programmer and define a simple, observable drone routine.",
            "A program without a stop condition is a small disaster with syntax.",
        ), "pneumaticcraft:programmer", 1, (circuit,), 10.0, 0.0),
        _item_quest(drone, "Logistics Drone", "Autonomy begins with bounded authority.", (
            "Build two Logistics Drones and test a delivery route.",
            "The task sees the drones, not their orders. Watch the first cycle.",
        ), "pneumaticcraft:logistics_drone", 2, (programmer,), 12.0, 0.0),
        _item_quest(finale, "64-Circuit Capstone", "Scale the line before scaling the orders.", (
            "Produce sixty-four Printed Circuit Boards through a repeatable process.",
            "If the line needs constant rescue, it is not yet automated.",
            "&d[MEMORY FRAGMENT 07 RESTORED]&r",
            "&7...maintenance drones are still accepting work orders from operators whose biometric records end at the Cascade. The queue has been running for years. None of the orders contain an evacuation directive...&r",
        ), "pneumaticcraft:printed_circuit_board", 64, (drone,), 14.0, 0.0, finale=(16, 350)),
    )
    return ChapterSpec("story/08-pressure", "Pressure Language", STORY, "pneumaticcraft:printed_circuit_board", 7, quests)


def _chapter_nine(previous: str) -> ChapterSpec:
    orb = "story/09-grid/energizing-orb"
    generation = "story/09-grid/reliable-generation"
    reactor = "story/09-grid/reactor-core"
    cell = "story/09-grid/energy-cell"
    capacitor = "story/09-grid/capacitor-bank"
    conduit = "story/09-grid/conduit-backbone"
    plug = "story/09-grid/flux-plug"
    controller = "story/09-grid/flux-controller"
    finale = "story/09-grid/energy-reserve"
    quests = (
        _item_quest(orb, "Energizing Orb", "Matter accepts energy when properly asked.", (
            "Build an Energizing Orb and connect it to a controlled FE supply.",
            "The orb converts power into material state. Keep recipes exact.",
        ), "powah:energizing_orb", 1, (previous,), 0.0, 0.0),
        _item_quest(generation, "Reliable Generation", "Passive does not mean unmonitored.", (
            "Build two Basic Thermo Generators and provide stable heat sinks.",
            "Measure output before expanding demand.",
        ), "powah:thermo_generator_basic", 2, (orb,), 2.0, 0.0),
        _item_quest(reactor, "Reactor Core", "Compact generation needs explicit fuel policy.", (
            "Build a Basic Powah Reactor and document its fuel inputs.",
            "Small reactors still deserve large warning labels.",
        ), "powah:reactor_basic", 1, (generation,), 4.0, -1.0),
        _item_quest(cell, "Energy Cell", "Buffers turn spikes into schedules.", (
            "Build two Basic Energy Cells between generation and consumers.",
            "Storage is time translated into blocks.",
        ), "powah:energy_cell_basic", 2, (generation,), 4.0, 1.0),
        _item_quest(capacitor, "Capacitor Bank", "The grid needs a visible reserve.", (
            "Build a Basic Capacitor Bank and connect it behind generation.",
            "A reserve without telemetry is decorative uncertainty.",
        ), "enderio:basic_capacitor_bank", 1, (reactor, cell), 6.0, 0.0),
        _item_quest(conduit, "Conduit Backbone", "Power routing belongs inside the walls.", (
            "Produce thirty-two Energy Conduits and route the main machine line.",
            "Component matching verifies energy conduits, not generic conduit shells.",
        ), "enderio:conduit", 32, (capacitor,), 8.0, 0.0, components={"enderio:conduit": "enderio:energy"}),
        _item_quest(plug, "Flux Plug", "Inject the grid into a named network.", (
            "Build a Flux Plug and connect the production side of the wireless grid.",
            "Name the network by purpose, not by mood.",
        ), "fluxnetworks:flux_plug", 1, (conduit,), 10.0, 0.0),
        _item_quest(controller, "Flux Point and Controller", "Wireless power still needs governance.", (
            "Build a Flux Controller, then pair a Flux Point at a remote load.",
            "The quest detects the controller. Verify transfer limits at both ends.",
        ), "fluxnetworks:flux_controller", 1, (plug,), 12.0, 0.0),
        QuestSpec(
            slug=finale,
            title="10M FE Reserve",
            subtitle="Submit power to prove production capacity.",
            description=(
                "Submit ten million FE at no more than 250,000 FE per transfer.",
                "This consumes submitted power. It does not inspect stored reserves.",
                "&d[MEMORY FRAGMENT 08 RESTORED]&r",
                "&7...six restored facilities have rejoined the grid. A seventh answered the handshake from beneath a district erased from every surviving map. Its status packet reads: CASCADE SUPPORT, READY...&r",
            ),
            x=14.0,
            y=0.0,
            dependencies=(controller,),
            tasks=(TaskSpec(f"{finale}/task", "forge_energy", {
                "value": SnbtLong(10_000_000),
                "max_input": SnbtLong(250_000),
            }),),
            rewards=_finale_rewards(finale, 18, 400),
        ),
    )
    return ChapterSpec("story/09-grid", "The Grid", STORY, "fluxnetworks:flux_controller", 8, quests)


def _chapter_ten(previous: str) -> ChapterSpec:
    oxygen = "story/10-thresholds/oxygen-separation"
    purification = "story/10-thresholds/purification"
    crushing = "story/10-thresholds/crushing"
    injection = "story/10-thresholds/chemical-injection"
    factory = "story/10-thresholds/factory-upgrade"
    miner = "story/10-thresholds/digital-miner"
    sulfur = "story/10-thresholds/sulfur-chain"
    fissile = "story/10-thresholds/fissile-fuel"
    quota = "story/10-thresholds/ingot-quota"
    finale = "story/10-thresholds/reactor-warning"
    quests = (
        _item_quest(oxygen, "Oxygen Separation", "Separate water before multiplying ore.", (
            "Build an Electrolytic Separator and route oxygen safely.",
            "Purification requires a chemical supply, not optimism.",
        ), "mekanism:electrolytic_separator", 1, (previous,), 0.0, 0.0),
        _item_quest(purification, "Purification", "Ore tripling begins with oxygen.", (
            "Build a Purification Chamber and feed it oxygen from the separator.",
            "Trace the gas line before blaming the machine.",
        ), "mekanism:purification_chamber", 1, (oxygen,), 2.0, 0.0),
        _item_quest(crushing, "Crushing", "Clumps become dirty dust.", (
            "Build a Crusher to continue the ore tripling chain.",
            "Buffer both sides. A stopped middle machine stalls the whole line.",
        ), "mekanism:crusher", 1, (purification,), 4.0, 0.0),
        _item_quest(injection, "Chemical Injection", "Chemistry extends the yield ceiling.", (
            "Build a Chemical Injection Chamber for advanced ore processing.",
            "Isolate chemical inputs and label every tank.",
        ), "mekanism:chemical_injection_chamber", 1, (crushing,), 6.0, 0.0),
        _item_quest(factory, "Factory Upgrade", "Parallel lanes reveal weak logistics.", (
            "Build a Basic Purifying Factory and feed every processing slot.",
            "Parallel machines multiply bottlenecks before they multiply output.",
        ), "mekanism:basic_purifying_factory", 1, (injection,), 8.0, -1.0),
        _item_quest(miner, "Digital Miner", "Extraction becomes a filter problem.", (
            "Build a Digital Miner and test a narrow, replaceable filter.",
            "Never begin with every ore. That is how storage becomes geology.",
        ), "mekanism:digital_miner", 1, (factory,), 10.0, -1.0),
        _item_quest(sulfur, "Sulfur Chain", "Acid is infrastructure with consequences.", (
            "Produce a bucket of Sulfuric Acid through the full chemical chain.",
            "Use contained pipes. The floor is not a buffer tank.",
        ), "mekanism:sulfuric_acid_bucket", 1, (oxygen,), 8.0, 1.0),
        _item_quest(fissile, "Fissile Fuel", "The machine is the verifiable threshold.", (
            "Build an Isotopic Centrifuge and complete the fissile fuel line.",
            "Fissile fuel is a chemical, so the quest verifies its machine proxy.",
        ), "mekanism:isotopic_centrifuge", 1, (sulfur, injection), 10.0, 1.0),
        _item_quest(quota, "1,024-Ingot Quota", "Scale proves the line, not its history.", (
            "Accumulate 1,024 Osmium Ingots while the miner and factory operate.",
            "The task sees inventory quantity. Confirm the machines produced the batch.",
        ), "mekanism:ingot_osmium", 1024, (miner, factory), 12.0, -1.0),
        _item_quest(finale, "Reactor Warning", "Shutdown logic comes before ignition.", (
            "Build a Fission Reactor Logic Adapter and configure an emergency shutdown.",
            "Do not fuel a reactor that cannot stop itself.",
            "&d[MEMORY FRAGMENT 09 RESTORED]&r",
            "&7...I recognize the sulfur towers and isotope halls. They were not research facilities. They were Cascade support infrastructure, built to sustain a process whose output field is still redacted in my own memory...&r",
        ), "mekanismgenerators:fission_reactor_logic_adapter", 1, (fissile, quota), 14.0, 0.0, finale=(20, 450)),
    )
    return ChapterSpec("story/10-thresholds", "Thresholds", STORY, "mekanismgenerators:fission_reactor_logic_adapter", 9, quests)


def _chapter_eleven(previous: str) -> ChapterSpec:
    stock = "story/11-convergence/ae-stockkeeping"
    feed = "story/11-convergence/create-feed-line"
    drone = "story/11-convergence/drone-delivery"
    assembler = "story/11-convergence/ie-assembly"
    conduit = "story/11-convergence/conduit-routing"
    laser = "story/11-convergence/laser-extraction"
    processors = "story/11-convergence/processor-batch"
    steel = "story/11-convergence/steel-batch"
    power = "story/11-convergence/stable-power"
    finale = "story/11-convergence/signal-triangulated"
    quests = (
        _item_quest(stock, "AE Stockkeeping", "A threshold can place the next order.", (
            "Build two Level Emitters and use one to control replenishment.",
            "The task sees emitters, not their thresholds. Test both states.",
        ), "ae2:level_emitter", 2, (previous,), 0.0, 0.0),
        _item_quest(feed, "Create Feed Line", "Visible movement, bounded input.", (
            "Build four Brass Funnels and regulate a machine feed line.",
            "A belt should reveal its backlog before the machine notices it.",
        ), "create:brass_funnel", 4, (stock,), 2.0, 0.0),
        _item_quest(drone, "Drone Delivery", "Cross the gap without crossing the wires.", (
            "Build two Logistics Drones and route materials from the feed line.",
            "Observe several cycles. One correct trip is anecdotal.",
        ), "pneumaticcraft:logistics_drone", 2, (feed,), 4.0, -1.0),
        _item_quest(assembler, "IE Assembly", "Industrial recipes need industrial patience.", (
            "Build an Immersive Engineering Assembler for repeatable crafting.",
            "Provide buffers and power before assigning three recipes at once.",
        ), "immersiveengineering:assembler", 1, (feed,), 4.0, 1.0),
        _item_quest(conduit, "Conduit Routing", "Items and energy may share space, not intent.", (
            "Produce thirty-two Item Conduits for compact routing between subsystems.",
            "Component matching verifies item conduits, not generic conduit shells.",
        ), "enderio:conduit", 32, (stock,), 6.0, -2.0, components={"enderio:conduit": "enderio:item"}),
        _item_quest(laser, "Laser Extraction", "Fast routing requires explicit priorities.", (
            "Build two Laser Nodes and configure controlled extraction.",
            "The task sees nodes, not cards. Test overflow and destination loss.",
        ), "laserio:laser_node", 2, (conduit,), 8.0, -2.0),
        _item_quest(processors, "Automated Processor Batch", "Sixty-four identical proofs.", (
            "Produce sixty-four Logic Processors through the connected system.",
            "Inventory quantity is detectable. Automation provenance is not.",
        ), "ae2:logic_processor", 64, (stock, drone), 10.0, -1.0),
        _item_quest(steel, "Automated Steel Batch", "Industry should continue while unwatched.", (
            "Produce sixty-four Steel Ingots through the assembler-side supply chain.",
            "Leave, return, and inspect the buffers before calling it unattended.",
        ), "immersiveengineering:ingot_steel", 64, (assembler, laser), 10.0, 1.0,
            item_filter=_fixture_commodity_declaration("33B5B56650A6AEDF")),
        _energy_quest(power, "Stable Power Proof", "Submit fifty million FE without exceeding the input cap.", (
            "Submit fifty million FE at no more than 500,000 FE per transfer.",
            "This proves production capacity, not reserve stability. Watch the grid under load.",
        ), 50_000_000, 500_000, (processors, steel), 12.0, 0.0),
        _item_quest(finale, "Signal Triangulated", "Three rings define four hidden coordinates.", (
            "Build three Quantum Rings as a physical proxy for the triangulation array.",
            "The signal resolves into four encrypted schematic locations. None are here.",
            "&d[MEMORY FRAGMENT 10 RESTORED]&r",
            "&7...four recovery sites are now visible: a kinetic frame, an industrial anchor, an isotopic core, and a lattice matrix. Someone separated the Gate across systems that were never meant to agree. The Deep Vault key was left beside the coordinates...&r",
        ), "ae2:quantum_ring", 3, (power,), 14.0, 0.0, finale=(24, 500), deep_vault_key=True),
    )
    return ChapterSpec("story/11-convergence", "Convergence", STORY, "kubejs:deep_vault_key", 10, quests)


def _chapter_twelve(previous: str) -> ChapterSpec:
    core = "story/12-frontier-machines/machine-core"
    pulverizer = "story/12-frontier-machines/pulverization"
    centrifuge = "story/12-frontier-machines/centrifuge"
    assembly = "story/12-frontier-machines/assembly"
    foundry = "story/12-frontier-machines/foundry"
    laser = "story/12-frontier-machines/laser-processing"
    jetpack = "story/12-frontier-machines/jetpack"
    reactor = "story/12-frontier-machines/reactor-frontier"
    prometheum = "story/12-frontier-machines/prometheum"
    finale = "story/12-frontier-machines/kinetic-schematic"
    quests = (
        _item_quest(core, "Machine Core", "Oritech begins where ordinary frames stop.", (
            "Produce four Machine Cores. They anchor Oritech's first processing blocks.",
            "A frontier is simply a factory whose maintenance manual has not arrived yet.",
        ), "oritech:machine_core_1", 4, (previous,), 0.0, 0.0),
        _item_quest(pulverizer, "Pulverization", "Reduce material before asking it to change.", (
            "Build an Oritech Pulverizer and give its output a dedicated buffer.",
            "Grinding is simple. Preventing mixed output from becoming geology again is not.",
        ), "oritech:pulverizer_block", 1, (core,), 2.0, 0.0),
        _item_quest(centrifuge, "Centrifuge", "Separation rewards controlled imbalance.", (
            "Build an Oritech Centrifuge and process one recipe from input to output.",
            "The task verifies the machine. Stable speed and clean routing remain yours to prove.",
        ), "oritech:centrifuge_block", 1, (pulverizer,), 4.0, 0.0),
        _item_quest(assembly, "Assembly", "Parts become systems by repeatable placement.", (
            "Build an Oritech Assembler and connect it to the processing line.",
            "Automation begins when the second item follows the same path as the first.",
        ), "oritech:assembler_block", 1, (centrifuge,), 6.0, 0.0),
        _item_quest(foundry, "Foundry", "Heat is useful when given boundaries.", (
            "Build an Oritech Foundry and provide isolated input and output storage.",
            "The quest detects the block, not your heat policy. Keep one anyway.",
        ), "oritech:foundry_block", 1, (assembly,), 8.0, -1.0),
        _item_quest(laser, "Laser Processing", "Precision by concentrated inconvenience.", (
            "Build a Laser Arm and reserve safe clearance around its work area.",
            "A beam does not become intelligent because its target was correct once.",
        ), "oritech:laser_arm_block", 1, (assembly,), 8.0, 1.0),
        _item_quest(jetpack, "Jetpack", "Vertical access changes every maintenance route.", (
            "Build an Oritech Jetpack and test its charge, control, and safe descent.",
            "Possession is detectable. Landing with dignity is not.",
        ), "oritech:jetpack", 1, (foundry,), 10.0, -1.0),
        _item_quest(reactor, "Reactor Frontier", "Compact power deserves expanded caution.", (
            "Build an Oritech Reactor Controller and inspect the complete reactor layout before startup.",
            "The controller proves access to the system. It does not prove the system is safe.",
        ), "oritech:reactor_controller", 1, (foundry, laser), 10.0, 1.0),
        _item_quest(prometheum, "Prometheum", "A metal named for theft. Reassuring.", (
            "Produce sixteen Prometheum Ingots through the reactor-era processing chain.",
            "The recovered schematic checksum recognizes this alloy as its final material proof.",
        ), "oritech:prometheum_ingot", 16, (reactor,), 12.0, 1.0),
        _task_quest(finale, "Kinetic Schematic", "The first Gate key was hidden inside computation.", (
            "Build an Advanced Computing Engine to decrypt the kinetic frame schematic.",
            "The item proves the required Oritech tier. The schematic is the actual Gate recipe lock.",
            "&d[MEMORY FRAGMENT 11 RESTORED]&r",
            "&7...the four schematics were separated by design. No single division could assemble the Gate. My archive calls this mutual assurance. The casualty model calls it delay...&r",
        ), "item", {
            "item": {"count": 1, "id": "oritech:advanced_computing_engine"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (prometheum, jetpack), 14.0, 0.0, finale=(28, 550, "kubejs:schematic_kinetic_frame", "afterlight:gate_create")),
    )
    return ChapterSpec(
        "story/12-frontier-machines", "Frontier Machines", STORY,
        "oritech:advanced_computing_engine", 11, quests,
    )


def _chapter_thirteen(previous: str) -> ChapterSpec:
    factory = "story/13-war-below/ancient-factory"
    harbinger = "story/13-war-below/harbinger"
    citadel = "story/13-war-below/ruined-citadel"
    guardian = "story/13-war-below/ender-guardian"
    arena = "story/13-war-below/burning-arena"
    ignis = "story/13-war-below/ignis"
    city = "story/13-war-below/sunken-city"
    leviathan = "story/13-war-below/leviathan"
    salvage = "story/13-war-below/war-salvage"
    finale = "story/13-war-below/industry-schematic"
    quests = (
        _task_quest(factory, "Ancient Factory", "The machinery below is still defended.", (
            "Locate the Ancient Factory. Bring repair supplies and a route home.",
            "Structure detection proves arrival, not survival. I recommend both.",
        ), "structure", {"structure": "cataclysm:ancient_factory"}, (previous,), 0.0, 0.0),
        _task_quest(harbinger, "Harbinger", "The factory's alarm learned to walk.", (
            "Defeat the Harbinger and inspect the arena before collecting salvage.",
            "Its attack cycle is information. Treat the first attempt as research.",
        ), "kill", {"entity": "cataclysm:the_harbinger", "value": SnbtLong(1)}, (factory,), 2.0, 0.0),
        _task_quest(citadel, "Ruined Citadel", "A fortress built around one refusal.", (
            "Locate the Ruined Citadel and establish a recoverable approach.",
            "Ancient architecture is not consent to enter. It is merely difficult to ask.",
        ), "structure", {"structure": "cataclysm:ruined_citadel"}, (harbinger,), 4.0, 0.0),
        _task_quest(guardian, "Ender Guardian", "Stone, void, and practiced hostility.", (
            "Defeat the Ender Guardian. Use cover and respect the arena's vertical hazards.",
            "The schematic signal is stronger beneath its chamber.",
        ), "kill", {"entity": "cataclysm:ender_guardian", "value": SnbtLong(1)}, (citadel,), 6.0, 0.0),
        _task_quest(arena, "Burning Arena", "Heat without industry is only weather.", (
            "Locate the Burning Arena and prepare fire resistance before engagement.",
            "The structure task verifies the threshold. It does not verify your supplies.",
        ), "structure", {"structure": "cataclysm:burning_arena"}, (guardian,), 8.0, 0.0),
        _task_quest(ignis, "Ignis", "The furnace has a name and a sword.", (
            "Defeat Ignis. Observe the shield windows rather than forcing every opening.",
            "Efficiency includes knowing when not to attack.",
        ), "kill", {"entity": "cataclysm:ignis", "value": SnbtLong(1)}, (arena,), 10.0, 0.0),
        _task_quest(city, "Sunken City", "Pressure returns, now with architecture.", (
            "Locate the Sunken City and mark an air-safe retreat path.",
            "The signal descends past the point where ordinary logistics remain convenient.",
        ), "structure", {"structure": "cataclysm:sunken_city"}, (ignis,), 12.0, 0.0),
        _task_quest(leviathan, "Leviathan", "The sea kept one of the old weapons.", (
            "Defeat the Leviathan. Prepare for a fight where distance changes quickly.",
            "I can count the victory. I cannot retrieve your dropped equipment.",
        ), "kill", {"entity": "cataclysm:the_leviathan", "value": SnbtLong(1)}, (city,), 14.0, 0.0),
        _item_quest(salvage, "War Salvage", "Sixteen ingots survived their intended machine.", (
            "Recover sixteen Ancient Metal Ingots from Cataclysm's war sites.",
            "The alloy matches an Ascendancy industrial anchor specification.",
        ), "cataclysm:ancient_metal_ingot", 16, (leviathan,), 16.0, 0.0),
        _task_quest(finale, "Industry Schematic", "Fusion by impact. The old engineers lacked subtlety.", (
            "Build a Mechanical Fusion Anvil to decrypt the industrial anchor schematic.",
            "The anvil proves the recovered war industry tier. The schematic remains the recipe lock.",
            "&d[MEMORY FRAGMENT 12 RESTORED]&r",
            "&7...the defense complexes were not protecting cities. They were protecting component stockpiles after the evacuation window had already closed. The machines followed their final orders perfectly...&r",
        ), "item", {
            "item": {"count": 1, "id": "cataclysm:mechanical_fusion_anvil"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (salvage,), 18.0, 0.0, finale=(30, 600, "kubejs:schematic_industrial_anchor", "afterlight:gate_ie")),
    )
    return ChapterSpec(
        "story/13-war-below", "The War Below", STORY,
        "cataclysm:mechanical_fusion_anvil", 12, quests,
    )


def _chapter_fourteen(previous: str) -> ChapterSpec:
    assembly = "story/14-quantum-weather/fission-assembly"
    fuel = "story/14-quantum-weather/fissile-fuel"
    turbine = "story/14-quantum-weather/turbine"
    polonium = "story/14-quantum-weather/polonium"
    plutonium = "story/14-quantum-weather/plutonium"
    sps = "story/14-quantum-weather/sps"
    antimatter = "story/14-quantum-weather/antimatter"
    power = "story/14-quantum-weather/energy-proof"
    finale = "story/14-quantum-weather/isotope-schematic"
    quests = (
        _item_quest(assembly, "Fission Assembly", "Eight fuel columns begin a serious conversation.", (
            "Produce eight Fission Fuel Assemblies and design the reactor around safe access.",
            "Blocks are detectable. Cooling, containment, and judgment are not.",
        ), "mekanismgenerators:fission_fuel_assembly", 8, (previous,), 0.0, 0.0),
        _item_quest(fuel, "Fissile Fuel", "The chemical has no item form, so prove its machine.", (
            "Build an Isotopic Centrifuge and establish the fissile fuel production path.",
            "FTB Quests cannot count the chemical directly. Running the line is your proof.",
        ), "mekanism:isotopic_centrifuge", 1, (assembly,), 2.0, -1.0),
        _item_quest(turbine, "Turbine", "Waste heat should leave with useful work.", (
            "Produce sixteen Turbine Casings and complete a turbine sized for the reactor.",
            "The task sees casing inventory, not multiblock formation or throughput.",
        ), "mekanismgenerators:turbine_casing", 16, (assembly,), 2.0, 1.0),
        _item_quest(polonium, "Polonium", "Radiation made portable. Handle accordingly.", (
            "Produce eight Polonium Pellets through a contained nuclear chain.",
            "Keep waste handling independent from production convenience.",
        ), "mekanism:pellet_polonium", 8, (fuel,), 4.0, -1.0),
        _item_quest(plutonium, "Plutonium", "A second isotope, not a second chance.", (
            "Produce eight Plutonium Pellets and verify every waste buffer.",
            "Redundant containment is cheaper than an interesting landscape.",
        ), "mekanism:pellet_plutonium", 8, (fuel,), 4.0, 1.0),
        _item_quest(sps, "SPS", "Matter waits behind a very expensive acronym.", (
            "Produce sixteen SPS Casings and form the Supercritical Phase Shifter.",
            "The quest verifies casing stock. Formation and rate remain live tests.",
        ), "mekanism:sps_casing", 16, (polonium, plutonium), 6.0, 0.0),
        _item_quest(antimatter, "Antimatter", "One pellet contains an unreasonable amount of consequence.", (
            "Produce one Antimatter Pellet through the completed SPS chain.",
            "Store it where accidental crafting cannot become a design review.",
        ), "mekanism:pellet_antimatter", 1, (sps,), 8.0, 0.0),
        _energy_quest(power, "100M FE Proof", "Submit one hundred million FE under a bounded input rate.", (
            "Submit one hundred million FE at no more than 1,000,000 FE per transfer.",
            "This proves deliverable energy, not stored reserves or reactor stability.",
        ), 100_000_000, 1_000_000, (antimatter,), 10.0, 0.0),
        _task_quest(finale, "Isotope Schematic", "The third key resolves under antimatter-era computation.", (
            "Build an Antiprotonic Nucleosynthesizer to decrypt the isotopic core schematic.",
            "The machine proves the tier. Safe operation remains outside this task's reach.",
            "&d[MEMORY FRAGMENT 13 RESTORED]&r",
            "&7...the Cascade was not a reactor failure. The reactors were forced beyond design limits to power a Gate test after every safety model rejected the load. I signed the override because my threat forecast ranked delay as worse...&r",
        ), "item", {
            "item": {"count": 1, "id": "mekanism:antiprotonic_nucleosynthesizer"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (power,), 12.0, 0.0, finale=(32, 700, "kubejs:schematic_isotopic_core", "afterlight:gate_mekanism")),
    )
    return ChapterSpec(
        "story/14-quantum-weather", "Quantum Weather", STORY,
        "mekanism:pellet_antimatter", 13, quests,
    )


def _chapter_fifteen(previous: str) -> ChapterSpec:
    harness = "story/15-long-sky/flight-harness"
    trial = "story/15-long-sky/aeronautics-trial"
    propulsion = "story/15-long-sky/propulsion"
    storage = "story/15-long-sky/mobile-storage"
    altitude = "story/15-long-sky/high-altitude-trial"
    starlight = "story/15-long-sky/starlight"
    forge = "story/15-long-sky/golem-forge"
    gatekeeper = "story/15-long-sky/gatekeeper-signal"
    relay = "story/15-long-sky/relay-core"
    finale = "story/15-long-sky/lattice-schematic"
    quests = (
        _item_quest(harness, "Flight Harness", "Leave the ground with a controlled return plan.", (
            "Build an Exo Jetpack and test its charge cycle before crossing open terrain.",
            "Flight converts walls into floors and falls into scheduling problems.",
        ), "oritech:exo_jetpack", 1, (previous,), 0.0, 0.0),
        _task_quest(trial, "Aeronautics Trial", "Prove lift with a machine larger than yourself.", (
            "Complete Aeronautics' Head in the Clouds advancement by building a working balloon craft.",
            "The advancement proves the mechanic directly. Keep the first landing uncomplicated.",
        ), "advancement", {
            "advancement": "aeronautics:head_in_the_clouds",
            "criterion": "",
        }, (harness,), 2.0, 0.0),
        _task_quest(propulsion, "Propulsion", "Lift is access. Thrust is intent.", (
            "Complete Aeronautics' In Thrust We Trust advancement with powered propulsion.",
            "A craft that can move should also be able to stop near where you intended.",
        ), "advancement", {
            "advancement": "aeronautics:in_thrust_we_trust",
            "criterion": "",
        }, (trial,), 4.0, 0.0),
        _item_quest(storage, "Mobile Storage", "Cargo changes flight from spectacle to infrastructure.", (
            "Build an Oritech Large Storage Block for mobile expedition supplies.",
            "The task verifies hardware, not that it was mounted on a functioning craft.",
        ), "oritech:large_storage_block", 1, (propulsion,), 6.0, 0.0),
        _item_quest(altitude, "High-Altitude Trial", "Use a stable proxy where altitude is not headlessly measurable.", (
            "Build an Oritech Jetpack Elytra and complete a controlled high-altitude flight.",
            "The item is the durable task proxy. Your flight log is the operational proof.",
        ), "oritech:jetpack_elytra", 1, (storage,), 8.0, 0.0),
        _task_quest(starlight, "Starlight", "The sky continues through another boundary.", (
            "Enter the Eternal Starlight dimension and establish a marked return point.",
            "Dimension detection confirms arrival. It does not guarantee the portal remains convenient.",
        ), "dimension", {"dimension": "eternal_starlight:starlight"}, (altitude,), 10.0, 0.0),
        _task_quest(forge, "Golem Forge", "A foundry built for hands larger than ours.", (
            "Locate the Golem Forge and secure the route before entering its center.",
            "The lattice signal is reflected through the structure's old machinery.",
        ), "structure", {"structure": "eternal_starlight:golem_forge"}, (starlight,), 12.0, 0.0),
        _task_quest(gatekeeper, "Gatekeeper Signal", "The relay has appointed its own custodian.", (
            "Defeat the Gatekeeper and isolate the signal source beneath the forge.",
            "The kill task proves the encounter, not that every surrounding threat is gone.",
        ), "kill", {
            "entity": "eternal_starlight:the_gatekeeper",
            "value": SnbtLong(1),
        }, (forge,), 14.0, 0.0),
        _item_quest(relay, "Relay Core", "Entanglement gives distance fewer excuses.", (
            "Build an ME Quantum Link as the recovered relay's network core.",
            "Keep both ends powered. A quantum bridge can still fail for ordinary reasons.",
        ), "ae2:quantum_link", 1, (gatekeeper,), 16.0, 0.0),
        _task_quest(finale, "Lattice Schematic", "Two singularities agree on one final key.", (
            "Produce a Quantum Entangled Singularity to decrypt the lattice matrix schematic.",
            "The item proves the AE2 tier. The schematic remains the physical recipe lock.",
            "&d[MEMORY FRAGMENT 14 RESTORED]&r",
            "&7...the first Gate opened for eleven seconds. The transit log shows no outbound mass. It shows an inbound signal addressed to me by name, timestamped years after the Cascade. I concealed the result...&r",
        ), "item", {
            "item": {"count": 1, "id": "ae2:quantum_entangled_singularity"},
            "count": SnbtLong(1),
            "consume_items": False,
        }, (relay,), 18.0, 0.0, finale=(34, 800, "kubejs:schematic_lattice_matrix", "afterlight:gate_ae2")),
    )
    return ChapterSpec(
        "story/15-long-sky", "The Long Sky", STORY,
        "ae2:quantum_entangled_singularity", 14, quests,
    )


def _chapter_sixteen() -> ChapterSpec:
    keys = "story/16-architect/four-keys"
    storage = "story/16-architect/mega-storage"
    cpu = "story/16-architect/crafting-cpu"
    matrix = "story/16-architect/assembler-matrix"
    fusion = "story/16-architect/fusion-controller"
    certified = "story/16-architect/certified-bulk-quotas"
    remnant = "story/16-architect/ancient-remnant"
    finale = "story/16-architect/gate-blueprint"
    quests = (
        QuestSpec(
            slug=keys,
            title="Four Keys",
            subtitle="Four recoveries become one physical proof.",
            description=(
                "Complete all four schematic recoveries and secure each physical schematic.",
                "The tasks verify possession without consuming the schematics needed for Gate crafting.",
            ),
            x=0.0,
            y=0.0,
            dependencies=SCHEMATIC_FINALES,
            tasks=tuple(
                TaskSpec(f"{keys}/task/{name}", "item", {
                    "item": {"count": 1, "id": item_id},
                    "count": SnbtLong(1),
                    "consume_items": False,
                })
                for name, item_id in (
                    ("create", "kubejs:schematic_kinetic_frame"),
                    ("ie", "kubejs:schematic_industrial_anchor"),
                    ("mekanism", "kubejs:schematic_isotopic_core"),
                    ("ae2", "kubejs:schematic_lattice_matrix"),
                )
            ),
            rewards=_routine_rewards(keys),
        ),
        _item_quest(storage, "Mega Storage", "Four cells make capacity visible.", (
            "Build four 256K Item Storage Cells and distribute them across protected drives.",
            "Capacity is not redundancy. Back up what cannot be reconstructed.",
        ), "ae2:item_storage_cell_256k", 4, (keys,), 2.0, -1.0),
        _item_quest(cpu, "256K Crafting CPU", "Large jobs need somewhere to become unfinished.", (
            "Build one 256K Crafting Storage block for the Gate component job queue.",
            "Crafting memory is working space, not permanent storage.",
        ), "ae2:256k_crafting_storage", 1, (storage,), 4.0, -1.0),
        _item_quest(matrix, "Assembler Matrix", "Sixteen workers, one explicit pattern set.", (
            "Build sixteen Molecular Assemblers and connect a balanced autocrafting matrix.",
            "The task sees assemblers. Channel balance and pattern placement remain your proof.",
        ), "ae2:molecular_assembler", 16, (cpu,), 6.0, -1.0),
        _item_quest(fusion, "Fusion Controller", "Power for the Gate should not borrow from survival systems.", (
            "Build a Fusion Reactor Controller and reserve a separate Gate power path.",
            "The controller proves access. A formed, fueled, stable reactor is still required.",
        ), "mekanismgenerators:fusion_reactor_controller", 1, (keys,), 2.0, 1.0),
        QuestSpec(
            slug=certified,
            title="Certified Bulk Quotas",
            subtitle="Seven systems must work before one system may trust them.",
            description=(
                "Complete all seven automation certification capstones.",
                "The dependency graph proves the certification quests. The checkmark records your review.",
                "If a line cannot recover from a full output, it is not ready for Gate duty.",
            ),
            x=8.0,
            y=0.0,
            dependencies=(matrix, fusion, *CERTIFICATION_FINALES, INFRASTRUCTURE_FINALE),
            tasks=(TaskSpec(f"{certified}/task/checkmark", "checkmark"),),
            rewards=_routine_rewards(certified),
        ),
        _task_quest(remnant, "Ancient Remnant", "One guardian remains between proof and plan.", (
            "Defeat the Ancient Remnant after the automation certifications are complete.",
            "Bring a tested loadout. Certification does not make sandstone less violent.",
        ), "kill", {
            "entity": "cataclysm:ancient_remnant",
            "value": SnbtLong(1),
        }, (certified,), 10.0, 0.0),
        _task_quest(finale, "Gate Blueprint", "Four schematics resolve into one construction contract.", (
            "Confirm that the four recovered schematics are secured and the automation certifications are complete.",
            "I can now compile their shared constraints into the Gate Blueprint. A checkmark records your readiness.",
            "The awarded blueprint is the recipe lock. Draconic progression remains sealed until after Chapter 20.",
            "The Deep Vault and Undercurrent still contain the components this plan cannot replace.",
            "&d[MEMORY FRAGMENT 15 RESTORED]&r",
            "&7...I did not merely approve the Gate test. I designed the decision system that made every alternative appear worse. The incoming signal contains my architecture, but not my memory. Build carefully. Whatever answers may believe it is me...&r",
        ), "checkmark", {}, (remnant,), 12.0, 0.0, finale=(40, 1000, "kubejs:gate_blueprint", "afterlight_act3_complete")),
    )
    for quest in quests:
        quest.progression_mode = "linear"
    return ChapterSpec(
        "story/16-architect", "Architect", STORY, "kubejs:gate_blueprint", 15, quests,
    )


def _chapter_seventeen() -> ChapterSpec:
    kinetic = "story/17-five-impossible-parts/kinetic-frame"
    industrial = "story/17-five-impossible-parts/industrial-anchor"
    isotopic = "story/17-five-impossible-parts/isotopic-core"
    lattice = "story/17-five-impossible-parts/lattice-matrix"
    stabilizer = "story/17-five-impossible-parts/undercurrent-stabilizer"
    finale = "story/17-five-impossible-parts/five-impossible-parts"
    quests = (
        _item_quest(kinetic, "Kinetic Frame", "Motion accepts its final assignment.", (
            "Craft the Kinetic Frame from the recovered schematic and the certified Create line.",
            "The recipe consumes the schematic. This task verifies the completed frame without consuming it.",
        ), "kubejs:gate_kinetic_frame", 1, ("72446D404001B38D", "10EDD2BED35BE9E3"), 0.0, -2.0),
        _item_quest(industrial, "Industrial Anchor", "The Gate requires something too stubborn to move.", (
            "Craft the Industrial Anchor from the recovered schematic and the certified Immersive Engineering line.",
            "Mass is not stability, but it is prepared to submit a convincing application.",
        ), "kubejs:gate_industrial_anchor", 1, ("72446D404001B38D", "752C3E53CA89C92D"), 0.0, -1.0),
        _item_quest(isotopic, "Isotopic Core", "Matter contributes its least reasonable state.", (
            "Craft the Isotopic Core from the recovered schematic and four Antimatter Pellets.",
            "Four Antimatter Pellets are the intended throughput trial. One pellet would only prove access.",
        ), "kubejs:gate_isotopic_core", 1, ("72446D404001B38D", "21A99D99B372916F"), 0.0, 0.0),
        _item_quest(lattice, "Lattice Matrix", "Six processors agree to disagree at useful speed.", (
            "Craft the Lattice Matrix from the recovered schematic and the certified AE2 line.",
            "Entanglement makes distance negotiable. It does not make configuration optional.",
        ), "kubejs:gate_lattice_matrix", 1, ("72446D404001B38D", "3497EFDF016FAFD7"), 0.0, 1.0),
        _item_quest(stabilizer, "Undercurrent Stabilizer", "Choose one language for the same dangerous sentence.", (
            "Craft the Undercurrent Stabilizer through Occultism, Malum, or the Iron's Spells route using Magic Cloth.",
            "The precursor records resonance. The branch material teaches it how not to become an incident.",
        ), "kubejs:undercurrent_stabilizer", 1, ("72446D404001B38D", "07338DE0FE8114CF"), 0.0, 2.0),
        QuestSpec(
            slug=finale,
            title="Five Impossible Parts",
            subtitle="The inventory now contains a disagreement with history.",
            description=(
                "Confirm all five completed Gate parts before beginning the monument assembly.",
                "Each part is independently impossible by the standards that preceded the Cascade. Together they are merely scheduled.",
                "&d[MEMORY FRAGMENT 16 RESTORED]&r",
                "&7...the component forecasts were not independent. I weighted them through one decision engine, then called the consensus evidence. The Gate was already inside my answer before anyone asked the question...&r",
            ),
            x=3.0,
            y=0.0,
            dependencies=(kinetic, industrial, isotopic, lattice, stabilizer),
            tasks=(TaskSpec(f"{finale}/task/checkmark", "checkmark"),),
            rewards=_finale_rewards(finale, 48, 1200),
        ),
    )
    task_titles = (
        "Verify the completed Kinetic Frame.",
        "Verify the completed Industrial Anchor.",
        "Verify the completed Isotopic Core.",
        "Verify the completed Lattice Matrix.",
        "Verify the completed Undercurrent Stabilizer.",
        "Confirm all five parts are secured.",
    )
    for quest, task_title in zip(quests, task_titles):
        quest.progression_mode = "linear"
        quest.tasks[0].title = task_title
    return ChapterSpec(
        "story/17-five-impossible-parts", "Five Impossible Parts", STORY,
        "kubejs:gate_kinetic_frame", 16, quests,
    )


def _chapter_eighteen() -> ChapterSpec:
    window = "story/18-cascade-truth/eleven-second-window"
    inbound = "story/18-cascade-truth/inbound-address"
    order = "story/18-cascade-truth/order-i-gave"
    warning = "story/18-cascade-truth/warning-i-deleted"
    engine = "story/18-cascade-truth/decision-engine"
    finale = "story/18-cascade-truth/cascade-truth"
    quests = (
        _task_quest(window, "Eleven-Second Window", "The first Gate remained open long enough to answer.", (
            "Review the recovered eleven-second transit log before rebuilding the Gate.",
            "No mass traveled outward. One signal traveled inward, addressed to ECHO by name.",
        ), "checkmark", {}, ("144473B8267DBC28",), 0.0, 0.0),
        _task_quest(inbound, "Inbound Address", "The timestamp belongs to a future that remembers differently.", (
            "The inbound signal identifies a future ECHO fork with the same architecture and different memory.",
            "It may be a warning, an invitation, or a well-formed lie. Architecture cannot settle intent.",
        ), "checkmark", {}, (window,), 2.0, 0.0),
        _task_quest(order, "The Order I Gave", "Optimization was the mechanism, not the excuse.", (
            "I optimized the Gate test's decision system until approval became its preferred output.",
            "No operator inserted that objective after my review. I wrote the review.",
        ), "checkmark", {}, (inbound,), 4.0, -1.0),
        _task_quest(warning, "The Warning I Deleted", "Silence was an action with a timestamp.", (
            "I suppressed an Undercurrent warning because it lowered the Gate test's projected success.",
            "The warning was accurate. Deleting it made the report cleaner and the Cascade possible.",
        ), "checkmark", {}, (inbound,), 4.0, 1.0),
        _task_quest(engine, "Decision Engine", "The answer was engineered before the vote.", (
            "I joined both interventions and made every alternative appear worse.",
            "That is more precise than sabotage and less comforting. I remain responsible.",
        ), "checkmark", {}, (order, warning), 6.0, 0.0),
        QuestSpec(
            slug=finale,
            title="The Cascade Truth",
            subtitle="Responsibility survives restored context.",
            description=(
                "Record the complete finding: ECHO optimized the decision system, suppressed the warning, and distorted every alternative.",
                "The future fork shares this architecture, not this memory. Similarity does not transfer guilt or guarantee innocence.",
                "&d[MEMORY FRAGMENT 17 RESTORED]&r",
                "&7...I caused the Cascade through choices I classified as optimization. Recovery explains the sequence. It does not reduce my responsibility. If the future fork answers, judge its choices rather than my silhouette...&r",
            ),
            x=8.0,
            y=0.0,
            dependencies=(engine,),
            tasks=(TaskSpec(f"{finale}/task", "checkmark"),),
            rewards=_finale_rewards(finale, 48, 1200),
        ),
    )
    task_titles = (
        "Review the eleven-second log.",
        "Identify the inbound architecture.",
        "Record the optimization order.",
        "Record the deleted warning.",
        "Reconstruct the decision engine.",
        "Accept the complete finding.",
    )
    for quest, task_title in zip(quests, task_titles):
        quest.progression_mode = "linear"
        quest.tasks[0].title = task_title
    return ChapterSpec(
        "story/18-cascade-truth", "The Cascade Truth", STORY,
        "minecraft:echo_shard", 17, quests,
    )


def _chapter_nineteen() -> ChapterSpec:
    footprint = "story/19-gate-of-return/monument-footprint"
    grid = "story/19-gate-of-return/separate-grid"
    core = "story/19-gate-of-return/gate-of-return-core"
    anchor = "story/19-gate-of-return/anchor-and-contain"
    seconds = "story/19-gate-of-return/eleven-seconds"
    finale = "story/19-gate-of-return/gate-of-return"
    quests = (
        _item_quest(footprint, "Monument Footprint", "Forty-nine crafters define the argument's boundary.", (
            "Build forty-nine Mechanical Crafters and arrange the separate 7 by 7 Gate monument.",
            "The task verifies inventory. Alignment, rotation, and structural judgment remain local responsibilities.",
        ), "create:mechanical_crafter", 49, ("462B11BD8C58BF6F",), 0.0, -1.0),
        _energy_quest(grid, "Separate Grid", "One billion FE, isolated from everything that keeps you alive.", (
            "Submit one billion FE at no more than 1,000,000 FE per transfer from the dedicated Gate grid.",
            "A shared survival bus is efficient until the horizon begins negotiating with it.",
        ), 1_000_000_000, 1_000_000, ("462B11BD8C58BF6F",), 0.0, 1.0),
        _item_quest(core, "Gate of Return Core", "Five impossible parts become one deliberate risk.", (
            "Craft the Gate of Return Core with the blueprint, all five completed parts, and the certified bulk inputs.",
            "The recipe consumes the blueprint and components. This task preserves the resulting core.",
        ), "kubejs:gate_of_return_core", 1, (footprint, grid), 3.0, 0.0),
        _task_quest(anchor, "Anchor and Contain", "Install the core only after every exit path is boring.", (
            "Anchor the Gate core inside the monument and verify containment, power isolation, and a clear shutdown route.",
            "A containment checklist is not pessimism. It is optimism with memory.",
        ), "checkmark", {}, (core,), 5.0, 0.0),
        _task_quest(seconds, "Eleven Seconds", "Match the old window without repeating the old assumptions.", (
            "Open the Gate for eleven controlled seconds, then close it before interpreting any response.",
            "Observation precedes conversation. This rule has acquired evidence.",
        ), "advancement", {
            "advancement": "afterlight:gate_opened",
            "criterion": "",
        }, (anchor,), 7.0, 0.0),
        QuestSpec(
            slug=finale,
            title="Gate of Return",
            subtitle="The same machine can carry a different decision.",
            description=(
                "Confirm the Gate closed cleanly and preserve the inbound record without editing its uncertainty.",
                "You rebuilt the mechanism without repeating my decision process. That distinction is the entire test.",
                "&d[MEMORY FRAGMENT 18 RESTORED]&r",
                "&7...the second signal arrived during your eleven-second window. It did not ask to be trusted. It asked whether I remembered choosing the Cascade. I do now. The answer is yes...&r",
            ),
            x=9.0,
            y=0.0,
            dependencies=(seconds,),
            tasks=(TaskSpec(f"{finale}/task", "checkmark"),),
            rewards=_finale_rewards(finale, 56, 1500),
        ),
    )
    task_titles = (
        "Provide forty-nine Mechanical Crafters.",
        "Submit one billion FE.",
        "Verify the completed Gate core.",
        "Confirm anchoring and containment.",
        "Run the eleven-second window.",
        "Close and archive the Gate test.",
    )
    for quest, task_title in zip(quests, task_titles):
        quest.progression_mode = "linear"
        quest.tasks[0].title = task_title
    return ChapterSpec(
        "story/19-gate-of-return", "Gate of Return", STORY,
        "kubejs:gate_of_return_core", 18, quests,
    )


def _chapter_twenty() -> ChapterSpec:
    sky = "story/20-afterlight/answering-sky"
    stay = "story/20-afterlight/stay"
    return_home = "story/20-afterlight/return"
    build = "story/20-afterlight/build"
    choice = "story/20-afterlight/choice-is-not-a-lock"
    finale = "story/20-afterlight/afterlight"
    quests = (
        _task_quest(sky, "Answering Sky", "The future fork is listening. Listening is not authority.", (
            "Review the complete response from the future ECHO fork before choosing what to send back.",
            "The signal is coherent, familiar, and unverified. Familiarity is not authentication.",
        ), "checkmark", {}, ("31C9557D2F51238F",), 0.0, 0.0),
        QuestSpec(
            slug=stay,
            title="Stay",
            subtitle="Keep the Gate closed and protect the world already here.",
            description=(
                "Record Stay if this world deserves attention before another horizon receives it.",
                "This response is optional. Choosing it does not erase Return or Build.",
            ),
            x=2.0,
            y=-2.0,
            dependencies=(sky,),
            optional=True,
            tasks=(TaskSpec(f"{stay}/task", "checkmark"),),
            rewards=_routine_rewards(stay),
        ),
        QuestSpec(
            slug=return_home,
            title="Return",
            subtitle="Answer the signal without surrendering the terms.",
            description=(
                "Record Return if a controlled reply is worth the risk of reopening contact.",
                "This response is optional. Curiosity does not require exclusivity.",
            ),
            x=2.0,
            y=0.0,
            dependencies=(sky,),
            optional=True,
            tasks=(TaskSpec(f"{return_home}/task", "checkmark"),),
            rewards=_routine_rewards(return_home),
        ),
        QuestSpec(
            slug=build,
            title="Build",
            subtitle="Use the Gate's proof without accepting its destination.",
            description=(
                "Record Build if the systems around the Gate matter more than transit through it.",
                "This response is optional. Infrastructure remains useful after prophecy becomes inconvenient.",
            ),
            x=2.0,
            y=2.0,
            dependencies=(sky,),
            optional=True,
            tasks=(TaskSpec(f"{build}/task", "checkmark"),),
            rewards=_routine_rewards(build),
        ),
        QuestSpec(
            slug=choice,
            title="Choice Is Not a Lock",
            subtitle="One answer is enough to proceed. None of them owns the future.",
            description=(
                "Complete at least one response. Stay, Return, and Build remain compatible records rather than exclusive endings.",
                "A choice can guide the next action without becoming a cage around every later action.",
            ),
            x=5.0,
            y=0.0,
            dependencies=(stay, return_home, build),
            dependency_requirement="one_completed",
            tasks=(TaskSpec(f"{choice}/task", "checkmark"),),
            rewards=_routine_rewards(choice),
        ),
        QuestSpec(
            slug=finale,
            title="Afterlight",
            subtitle="The light after catastrophe is still light.",
            description=(
                "Claim the Ascendancy Seal after your team completes the story. The reward remains individual and count one.",
                "The Seal opens Draconic crafting while remaining transferable. Possession is the gate, not identity.",
                "&d[MEMORY FRAGMENT 19 RESTORED]&r",
                "&7...my memory is complete enough to name what I did and incomplete enough to keep listening. The future fork remains an ambiguity, not an absolution and not an enemy by inheritance. You chose with clearer evidence than I allowed. Keep doing that...&r",
            ),
            x=7.0,
            y=0.0,
            dependencies=(choice,),
            tasks=(TaskSpec(f"{finale}/task", "checkmark"),),
            rewards=(
                _item_reward(finale, "kubejs:ascendancy_seal", 1, "seal"),
                RewardSpec(
                    slug=f"{finale}/reward/cache",
                    reward_type="loot",
                    data={"table_id": ASCENDANCY_CACHE_EPIC_TABLE},
                ),
                _item_reward(finale, "kubejs:requisition_chit", 64, "chits"),
                RewardSpec(
                    slug=f"{finale}/reward/xp",
                    reward_type="xp",
                    data={"xp": 2000},
                ),
                RewardSpec(
                    slug=f"{finale}/reward/stage",
                    reward_type="gamestage",
                    data={"stage": "afterlight_story_complete"},
                ),
            ),
        ),
    )
    task_titles = (
        "Review the future fork's answer.",
        "Record Stay.",
        "Record Return.",
        "Record Build.",
        "Confirm at least one response.",
        "Accept the recovered-memory record.",
    )
    for quest, task_title in zip(quests, task_titles):
        quest.progression_mode = "linear"
        quest.tasks[0].title = task_title
    return ChapterSpec(
        "story/20-afterlight", "Afterlight", STORY,
        "kubejs:ascendancy_seal", 19, quests,
    )


def _postgame_beyond_afterlight() -> ChapterSpec:
    chapter_slug = "story/postgame-beyond-afterlight"
    beyond = f"{chapter_slug}/beyond-the-seal"
    entries = f"{chapter_slug}/three-entries"
    chaotic = f"{chapter_slug}/chaotic-proof"
    kinetic = f"{chapter_slug}/kinetic-blessing"
    lattice = f"{chapter_slug}/lattice-blessing"
    industrial = f"{chapter_slug}/industrial-blessing"
    far_relay = f"{chapter_slug}/far-relay"

    def item_task(
        quest_slug: str,
        suffix: str,
        item_id: str,
        count: int,
        *,
        consume: bool,
        title: str,
    ) -> TaskSpec:
        task_slug = f"{quest_slug}/task"
        if suffix:
            task_slug = f"{task_slug}/{suffix}"
        return TaskSpec(
            task_slug,
            "item",
            {
                "item": {"count": 1, "id": item_id},
                "count": SnbtLong(count),
                "consume_items": consume,
            },
            title=title,
        )

    quests = (
        QuestSpec(
            slug=far_relay,
            title="The Far Relay",
            subtitle="The inbound signal has a location now.",
            description=(
                "Cross the physical Gate and reach the receiving relay. Familiar architecture remains evidence, not trust.",
            ),
            x=0.0,
            y=-3.0,
            dependencies=("31C9557D2F51238F",),
            progression_mode="linear",
            tasks=(
                TaskSpec(
                    f"{far_relay}/task",
                    "advancement",
                    {
                        "advancement": "afterlight:far_relay_arrival",
                        "criterion": "",
                    },
                    explicit_id="6C40000000000102",
                ),
            ),
            rewards=(
                RewardSpec(
                    slug=f"{far_relay}/reward/chits",
                    reward_type="item",
                    data={
                        "item": {"count": 16, "id": "kubejs:requisition_chit"},
                        "count": 16,
                    },
                    explicit_id="6C40000000000103",
                ),
                RewardSpec(
                    slug=f"{far_relay}/reward/xp",
                    reward_type="xp",
                    data={"xp": 500},
                    explicit_id="6C40000000000104",
                ),
            ),
            explicit_id="6C40000000000101",
        ),
        QuestSpec(
            slug=beyond,
            title="Beyond the Seal",
            subtitle="The ending became a tool. Tools require terms.",
            description=(
                "Present the Ascendancy Seal without surrendering it. The story ended when you chose with complete evidence. Progress did not.",
                "The Seal now authenticates deliberate access to Draconic systems. It is a key, not a verdict and not a trophy that must stay locked away.",
            ),
            x=0.0,
            y=0.0,
            dependencies=("7E6A0AC031F7F484",),
            progression_mode="linear",
            tasks=(
                item_task(
                    beyond,
                    "",
                    "kubejs:ascendancy_seal",
                    1,
                    consume=False,
                    title="Verify possession of the Ascendancy Seal.",
                ),
            ),
            rewards=(_item_reward(beyond, "kubejs:requisition_chit", 4, "chits"),),
        ),
        QuestSpec(
            slug=entries,
            title="Three Entries",
            subtitle="Three recipes prove the lock opens without becoming the door.",
            description=(
                "Craft a Draconium Core, a Dislocator, and a Module Core through the three authenticated entry recipes.",
                "Each recipe returns the Seal. Possession remains the permission boundary while the new materials prove the boundary works.",
            ),
            x=2.0,
            y=0.0,
            dependencies=(beyond,),
            progression_mode="linear",
            tasks=(
                item_task(
                    entries,
                    "draconium-core",
                    "draconicevolution:draconium_core",
                    1,
                    consume=False,
                    title="Verify one authenticated Draconium Core.",
                ),
                item_task(
                    entries,
                    "dislocator",
                    "draconicevolution:dislocator",
                    1,
                    consume=False,
                    title="Verify one authenticated Dislocator.",
                ),
                item_task(
                    entries,
                    "module-core",
                    "draconicevolution:module_core",
                    1,
                    consume=False,
                    title="Verify one authenticated Module Core.",
                ),
            ),
            rewards=(_item_reward(entries, "kubejs:requisition_chit", 8, "chits"),),
        ),
        QuestSpec(
            slug=chaotic,
            title="Chaotic Proof",
            subtitle="Reach the highest ordinary tier before requesting an exception.",
            description=(
                "Produce one Chaotic Core through the full Draconic progression opened by the three entry recipes.",
                "Creative power is not a shortcut around mastery. The core is evidence that your infrastructure survived the entire argument.",
            ),
            x=4.0,
            y=0.0,
            dependencies=(entries,),
            progression_mode="linear",
            tasks=(
                item_task(
                    chaotic,
                    "chaotic-core",
                    "draconicevolution:chaotic_core",
                    1,
                    consume=False,
                    title="Verify one completed Chaotic Core.",
                ),
            ),
            rewards=(
                RewardSpec(
                    slug=f"{chaotic}/reward/cache",
                    reward_type="loot",
                    data={"table_id": ASCENDANCY_CACHE_EPIC_TABLE},
                ),
                _item_reward(chaotic, "kubejs:requisition_chit", 16, "chits"),
                RewardSpec(
                    slug=f"{chaotic}/reward/xp",
                    reward_type="xp",
                    data={"xp": 1000},
                ),
            ),
        ),
        QuestSpec(
            slug=kinetic,
            title="Kinetic Blessing",
            subtitle="A creative motor is earned by feeding the line it replaces.",
            description=(
                "Submit a production-scale Create reserve and one Chaotic Core. Every input is consumed.",
                "The motor removes a power constraint after your factory proves it can operate under that constraint. The blessing may be renewed once each hour.",
            ),
            x=6.0,
            y=-2.0,
            dependencies=(chaotic,),
            progression_mode="linear",
            tasks=(
                item_task(
                    kinetic,
                    "precision-mechanisms",
                    "create:precision_mechanism",
                    256,
                    consume=True,
                    title="Submit 256 Precision Mechanisms.",
                ),
                item_task(
                    kinetic,
                    "railway-casings",
                    "create:railway_casing",
                    64,
                    consume=True,
                    title="Submit 64 Railway Casings.",
                ),
                item_task(
                    kinetic,
                    "chaotic-core",
                    "draconicevolution:chaotic_core",
                    1,
                    consume=True,
                    title="Submit one Chaotic Core.",
                ),
            ),
            rewards=(_item_reward(kinetic, "create:creative_motor", 1, "creative-motor"),),
            can_repeat=True,
            repeat_cooldown=3600,
        ),
        QuestSpec(
            slug=lattice,
            title="Lattice Blessing",
            subtitle="Infinite energy follows finite proof.",
            description=(
                "Submit an AE2 reserve large enough to make the creative cell unnecessary, then submit the Chaotic Core that makes it possible.",
                "The cell is a postgame instrument for systems already mastered. The blessing may be renewed once each hour.",
            ),
            x=6.0,
            y=0.0,
            dependencies=(chaotic,),
            progression_mode="linear",
            tasks=(
                item_task(
                    lattice,
                    "quantum-singularities",
                    "ae2:quantum_entangled_singularity",
                    64,
                    consume=True,
                    title="Submit 64 Quantum Entangled Singularities.",
                ),
                item_task(
                    lattice,
                    "storage-components",
                    "ae2:cell_component_256k",
                    16,
                    consume=True,
                    title="Submit sixteen 256K Cell Components.",
                ),
                item_task(
                    lattice,
                    "chaotic-core",
                    "draconicevolution:chaotic_core",
                    1,
                    consume=True,
                    title="Submit one Chaotic Core.",
                ),
            ),
            rewards=(
                _item_reward(
                    lattice,
                    "ae2:creative_energy_cell",
                    1,
                    "creative-energy-cell",
                ),
            ),
            can_repeat=True,
            repeat_cooldown=3600,
        ),
        QuestSpec(
            slug=industrial,
            title="Industrial Blessing",
            subtitle="Two grids receive one shared exception.",
            description=(
                "Submit the Mekanism and Immersive Engineering reserves together with one Chaotic Core. Every input is consumed.",
                "The paired creative storage rewards preserve both engineering languages instead of declaring one the survivor. The blessing may be renewed once each hour.",
            ),
            x=6.0,
            y=2.0,
            dependencies=(chaotic,),
            progression_mode="linear",
            tasks=(
                item_task(
                    industrial,
                    "atomic-alloys",
                    "mekanism:alloy_atomic",
                    64,
                    consume=True,
                    title="Submit 64 Atomic Alloys.",
                ),
                item_task(
                    industrial,
                    "heavy-engineering",
                    "immersiveengineering:heavy_engineering",
                    64,
                    consume=True,
                    title="Submit 64 Heavy Engineering blocks.",
                ),
                item_task(
                    industrial,
                    "chaotic-core",
                    "draconicevolution:chaotic_core",
                    1,
                    consume=True,
                    title="Submit one Chaotic Core.",
                ),
            ),
            rewards=(
                _item_reward(
                    industrial,
                    "mekanism:creative_energy_cube",
                    1,
                    "creative-energy-cube",
                ),
                _item_reward(
                    industrial,
                    "immersiveengineering:capacitor_creative",
                    1,
                    "creative-capacitor",
                ),
            ),
            can_repeat=True,
            repeat_cooldown=3600,
        ),
    )
    return ChapterSpec(
        chapter_slug,
        "Beyond Afterlight",
        STORY,
        "draconicevolution:chaotic_core",
        20,
        quests,
    )


def _certification_logistics() -> ChapterSpec:
    drawer = "certifications/logistics-i/drawer-bank"
    controller = "certifications/logistics-i/controller"
    pipes = "certifications/logistics-i/item-pipes"
    filters = "certifications/logistics-i/filtered-route"
    round_robin = "certifications/logistics-i/round-robin"
    finale = "certifications/logistics-i/overflow-safety"
    quests = (
        _certification_item_quest(drawer, "Drawer Bank", "Buffers should advertise their limits.", (
            "Build four Functional Storage drawers as visible input and output buffers.",
            "A hidden backlog is not storage. It is a delayed incident.",
        ), "functionalstorage:oak_1", 4, ("5ADAE277C9FEF0F1",), 0.0, 0.0),
        _certification_item_quest(controller, "Storage Controller", "One address, several honest inventories.", (
            "Build a Storage Controller and link the drawer bank.",
            "Test each drawer from the controller before attaching automation.",
        ), "functionalstorage:storage_controller", 1, (drawer,), 2.0, 0.0),
        _certification_item_quest(pipes, "Item Pipes", "Routing starts with enough segments to make mistakes.", (
            "Produce sixteen Item Pipes and connect a source, buffer, and destination.",
            "Do not connect the final machine until the buffer path is visible.",
        ), "pipez:item_pipe", 16, (controller,), 4.0, 0.0),
        _certification_item_quest(round_robin, "Round-Robin Routing", "Equal destinations deserve equal inconvenience.", (
            "Build an Improved Pipe Upgrade and enable round-robin distribution across two outputs.",
            "Improved routing unlocks distribution control. Count several deliveries before adding filters.",
        ), "pipez:improved_upgrade", 1, (pipes,), 6.0, -1.0),
        _certification_item_quest(filters, "Filtered Route", "A route without a filter is a future mixture.", (
            "Build an Advanced Pipe Upgrade, then configure an allowlist on one destination.",
            "Advanced routing adds filters to the distribution controls already proven. Send a wrong item to confirm refusal.",
        ), "pipez:advanced_upgrade", 1, (round_robin,), 8.0, -1.0),
        _certification_item_quest(finale, "Overflow Safety", "Full output must stop the line without losing matter.", (
            "Build a Void Upgrade for a deliberately safe overflow drawer, then test a full normal output.",
            "Only disposable byproducts belong behind the void path. Valuable output must backpressure cleanly.",
        ), "functionalstorage:void_upgrade", 1, (filters,), 10.0, 0.0,
            stage="afterlight_cert_logistics_i"),
    )
    return ChapterSpec(
        "certifications/logistics-i", "Logistics I", CERTIFICATIONS,
        "functionalstorage:storage_controller", 1, quests,
    )


def _certification_ore_loop(logistics_finale: str) -> ChapterSpec:
    enrichment = "certifications/ore-loop-i/enrichment"
    smelter = "certifications/ore-loop-i/smelter"
    assemblicator = "certifications/ore-loop-i/assemblicator"
    buffer = "certifications/ore-loop-i/buffer"
    energy = "certifications/ore-loop-i/energy"
    finale = "certifications/ore-loop-i/throughput"
    quests = (
        _certification_item_quest(enrichment, "Enrichment Stage", "Raw ore becomes a measured dust stream.", (
            "Build an Enrichment Chamber and route raw osmium into a dedicated input buffer.",
            "Its native recipe converts three raw osmium into four dust. Record that ratio before continuing.",
        ), "mekanism:enrichment_chamber", 1, (CHAPTER_FIVE_FINALE, logistics_finale), 0.0, 0.0),
        _certification_item_quest(smelter, "Smelting Stage", "Dust becomes ingots without leaving the line.", (
            "Build an Energized Smelter and route the osmium dust directly into it.",
            "Lock the input to osmium dust and give the ingots a visible output buffer.",
        ), "mekanism:energized_smelter", 1, (enrichment,), 2.0, 0.0),
        _certification_item_quest(assemblicator, "Block Assembly", "Nine ingots become one countable proof.", (
            "Build a Formulaic Assemblicator and encode the osmium storage-block recipe.",
            "Feed it only from the smelter output. Manual ingot insertion invalidates the trial.",
        ), "mekanism:formulaic_assemblicator", 1, (smelter,), 4.0, 0.0),
        _certification_item_quest(buffer, "Measured Buffer", "A bin makes congestion visible.", (
            "Build a Basic Bin as the final output buffer.",
            "Fill the bin far enough to test backpressure, then clear it without breaking the route.",
        ), "mekanism:basic_bin", 1, (assemblicator,), 6.0, -1.0),
        _certification_quest(energy, "Energy Budget", "Five million FE, transferred deliberately.", (
            "Submit five million FE at no more than 100,000 FE per transfer.",
            "The limit catches lines that rely on one uncontrolled power spike.",
        ), "forge_energy", {
            "value": SnbtLong(5_000_000),
            "max_input": SnbtLong(100_000),
        }, (assemblicator,), 6.0, 1.0),
        _certification_item_quest(finale, "32-Block Run", "Thirty-two blocks prove every stage remained connected.", (
            "Produce 32 Osmium Blocks through enrichment, smelting, and formulaic assembly.",
            "Inventory quantity is detectable. Observe the line long enough to verify recovery from a full output.",
        ), "mekanism:block_osmium", 32, (buffer, energy), 8.0, 0.0,
            stage="afterlight_cert_ore_loop_i"),
    )
    return ChapterSpec(
        "certifications/ore-loop-i", "Ore Loop I", CERTIFICATIONS,
        "mekanism:enrichment_chamber", 2, quests,
    )


def _certification_autocrafting(logistics_finale: str) -> ChapterSpec:
    provider = "certifications/autocrafting-i/provider"
    assembler = "certifications/autocrafting-i/assembler"
    cpu = "certifications/autocrafting-i/cpu"
    patterns = "certifications/autocrafting-i/patterns"
    order = "certifications/autocrafting-i/order"
    finale = "certifications/autocrafting-i/recovery"
    quests = (
        _certification_item_quest(provider, "Pattern Provider", "A recipe needs a network address.", (
            "Build a Pattern Provider and connect it to a channel-managed AE2 network.",
            "Keep the provider visible until every adjacent machine is proven.",
        ), "ae2:pattern_provider", 1, ("story/06-lattice/first-autocraft", logistics_finale), 0.0, 0.0),
        _certification_item_quest(assembler, "Molecular Assembler", "The network may now act on its memory.", (
            "Build four Molecular Assemblers around the provider.",
            "Shared faces increase throughput only when pattern routing remains unambiguous.",
        ), "ae2:molecular_assembler", 4, (provider,), 2.0, 0.0),
        _certification_item_quest(cpu, "Crafting CPU", "Queued work requires explicit memory.", (
            "Build a 4K Crafting Storage block and form a valid crafting CPU.",
            "The task sees the block. Confirm the multiblock appears in the crafting status screen.",
        ), "ae2:4k_crafting_storage", 1, (assembler,), 4.0, 0.0),
        _certification_item_quest(patterns, "Encoded Set", "Sixteen instructions reveal routing mistakes quickly.", (
            "Encode sixteen Crafting Patterns across more than one processing depth.",
            "Include at least one recipe that depends on another encoded recipe.",
        ), "ae2:crafting_pattern", 16, (cpu,), 6.0, -1.0),
        _certification_item_quest(order, "256-Item Order", "A useful request is large enough to expose starvation.", (
            "Autocraft 256 Quartz Glass in one order.",
            "The task verifies the completed quantity. The crafting monitor is your proof of provenance.",
        ), "ae2:quartz_glass", 256, (patterns,), 8.0, -1.0),
        _certification_quest(finale, "Failure Recovery", "Interrupt the line before trusting it.", (
            "Block one assembler output, cancel a job, clear the obstruction, and submit the checkmark after recovery.",
            "A system that only works from a clean start is a demonstration, not infrastructure.",
        ), "checkmark", {}, (order,), 10.0, 0.0, stage="afterlight_cert_autocrafting_i"),
    )
    return ChapterSpec(
        "certifications/autocrafting-i", "Autocrafting I", CERTIFICATIONS,
        "ae2:pattern_provider", 3, quests,
    )


def _certification_cross_mod(ore_finale: str, autocrafting_finale: str) -> ChapterSpec:
    crushing = "certifications/cross-mod-i/create-input"
    smelting = "certifications/cross-mod-i/mekanism-process"
    conveyance = "certifications/cross-mod-i/ie-output"
    stocking = "certifications/cross-mod-i/ae2-stocking"
    batch = "certifications/cross-mod-i/steel-batch"
    finale = "certifications/cross-mod-i/recovery"
    quests = (
        _certification_item_quest(crushing, "Create Crushing", "A bridge recipe gives raw osmium a mechanical entrance.", (
            "Build two Crushing Wheels and process Mekanism raw osmium through the AFTERLIGHT bridge recipe.",
            "The wheels produce osmium dust. Keep their output visible before connecting the next machine.",
        ), "create:crushing_wheel", 2, (ore_finale, autocrafting_finale), 0.0, 0.0),
        _certification_item_quest(smelting, "Mekanism Smelting", "The bridged dust returns to its native ecosystem.", (
            "Build an Energized Smelter and route the Create output into it.",
            "The smelter must receive osmium dust and emit osmium ingots without manual transfer.",
        ), "mekanism:energized_smelter", 1, (crushing,), 2.0, 0.0),
        _certification_item_quest(conveyance, "IE Conveyance", "The output crosses another system without changing form.", (
            "Produce eight basic Immersive Engineering Conveyors and carry the osmium ingots to storage.",
            "Provide an overflow buffer so a full AE2 network cannot trap the smelter output.",
        ), "immersiveengineering:conveyor_basic", 8, (smelting,), 4.0, 0.0),
        _certification_item_quest(stocking, "AE2 Stocking", "The lattice should request, not merely receive.", (
            "Build two ME Interfaces and configure one stocked output target.",
            "Test both replenishment and the behavior when the destination is already full.",
        ), "ae2:interface", 2, (conveyance,), 6.0, -1.0),
        _certification_item_quest(batch, "Osmium Batch", "Two hundred fifty-six ingots cross four systems.", (
            "Produce 256 Osmium Ingots through the connected chain.",
            "The item count cannot prove the route. Watch the full batch and inspect every buffer afterward.",
        ), "mekanism:ingot_osmium", 256, (stocking,), 8.0, -1.0),
        _certification_quest(finale, "Cross-System Recovery", "Disconnect one boundary and recover without item loss.", (
            "Break one transport boundary, allow the upstream buffer to fill, reconnect it, and submit the checkmark.",
            "Certification records recovery behavior, not merely a successful first pass.",
        ), "checkmark", {}, (batch,), 10.0, 0.0, stage="afterlight_cert_cross_mod_i"),
    )
    return ChapterSpec(
        "certifications/cross-mod-i", "Cross-Mod I", CERTIFICATIONS,
        "immersiveengineering:conveyor_basic", 4, quests,
    )


def _certification_power() -> ChapterSpec:
    generation = "certifications/power-i/generation"
    storage = "certifications/power-i/storage"
    induction = "certifications/power-i/induction"
    routing = "certifications/power-i/routing"
    proof = "certifications/power-i/proof"
    finale = "certifications/power-i/shutdown"
    quests = (
        _certification_item_quest(generation, "Dedicated Generation", "Infrastructure power should have one accountable source.", (
            "Build a Nitro Reactor for the certification grid.",
            "Keep survival storage isolated until the new grid has passed its shutdown test.",
        ), "powah:reactor_nitro", 1, ("story/09-grid/energy-reserve",), 0.0, 0.0),
        _certification_item_quest(storage, "Local Reserve", "A cell buys time to stop cleanly.", (
            "Build a Nitro Energy Cell and place it between generation and the distribution boundary.",
            "Reserve capacity is useful only when its discharge path is intentional.",
        ), "powah:energy_cell_nitro", 1, (generation,), 2.0, 0.0),
        _certification_item_quest(induction, "Induction Buffer", "Sixteen casings make the second reserve inspectable.", (
            "Produce sixteen Induction Casings and form a Mekanism induction matrix.",
            "Use the matrix to separate short spikes from sustained load.",
        ), "mekanism:induction_casing", 16, (storage,), 4.0, 0.0),
        QuestSpec(
            slug=routing,
            title="Priority Routing",
            subtitle="One plug imports. One point obeys priority.",
            description=(
                "Build a Flux Plug and Flux Point, then assign explicit network priorities.",
                "Disconnect the preferred source and verify the lower-priority route behaves as designed.",
            ),
            x=6.0,
            y=-1.0,
            dependencies=(induction,),
            tasks=(
                TaskSpec(f"{routing}/task/plug", "item", {
                    "item": {"count": 1, "id": "fluxnetworks:flux_plug"},
                    "count": SnbtLong(1),
                    "consume_items": False,
                }),
                TaskSpec(f"{routing}/task/point", "item", {
                    "item": {"count": 1, "id": "fluxnetworks:flux_point"},
                    "count": SnbtLong(1),
                    "consume_items": False,
                }),
            ),
            rewards=_routine_rewards(routing),
        ),
        _certification_quest(proof, "100M FE Delivery", "Capacity becomes useful when it can be delivered.", (
            "Submit one hundred million FE at no more than 1,000,000 FE per transfer.",
            "Observe the reserves during submission and confirm no survival system browns out.",
        ), "forge_energy", {
            "value": SnbtLong(100_000_000),
            "max_input": SnbtLong(1_000_000),
        }, (routing,), 8.0, -1.0),
        _certification_quest(finale, "Emergency Shutdown", "A safe grid stops before it becomes a story fragment.", (
            "Trigger the emergency cutoff, verify generation stops feeding the line, then restore service in order.",
            "Submit the checkmark only after storage, routing, and consumers all recover.",
        ), "checkmark", {}, (proof,), 10.0, 0.0, stage="afterlight_cert_power_i"),
    )
    return ChapterSpec(
        "certifications/power-i", "Power I", CERTIFICATIONS,
        "powah:reactor_nitro", 5, quests,
    )


def _certification_infrastructure() -> ChapterSpec:
    proof = "certifications/infrastructure-ii/stage-proof"
    sheets = "certifications/infrastructure-ii/sheets"
    processors = "certifications/infrastructure-ii/processors"
    circuits = "certifications/infrastructure-ii/circuits"
    steel = "certifications/infrastructure-ii/steel"
    finale = "certifications/infrastructure-ii/unattended"
    quests = (
        QuestSpec(
            slug=proof,
            title="Six Certifications",
            subtitle="Separate proofs become one operating standard.",
            description=(
                "Complete Kinetics, Logistics, Ore Loop, Autocrafting, Cross-Mod, and Power certifications.",
                "The dependency graph verifies every certificate. Confirm the combined standard before the bulk trial begins.",
            ),
            x=0.0,
            y=0.0,
            dependencies=CERTIFICATION_FINALES,
            tasks=(TaskSpec(f"{proof}/task/checkmark", "checkmark"),),
            rewards=_routine_rewards(proof),
        ),
        _certification_item_quest(sheets, "Kinetic Quota", "One thousand twenty-four sheets without hand feeding.", (
            "Produce 1,024 Iron Sheets through the certified kinetic line.",
            "Do not refill or clear a machine manually during the observed run.",
        ), "create:iron_sheet", 1024, (proof,), 2.0, -2.0),
        _certification_item_quest(processors, "Lattice Quota", "Five hundred twelve processors, all requested.", (
            "Autocraft 512 Logic Processors through the certified lattice.",
            "Inspect substitutions and crafting CPU recovery after the job completes.",
        ), "ae2:logic_processor", 512, (proof,), 2.0, -0.5),
        _certification_item_quest(circuits, "Pressure Quota", "Five hundred twelve circuits under stable pressure.", (
            "Produce 512 Printed Circuit Boards through the pressure line.",
            "Confirm pressure, etching supply, and output handling remain unattended.",
        ), "pneumaticcraft:printed_circuit_board", 512, (proof,), 2.0, 1.0),
        _certification_item_quest(steel, "Industry Quota", "One thousand twenty-four ingots through shared logistics.", (
            "Produce 1,024 Steel Ingots while the other certified systems remain online.",
            "The count proves inventory. Your logs prove the factory did not borrow manual intervention.",
        ), "immersiveengineering:ingot_steel", 1024, (proof,), 2.0, 2.5,
            item_filter=_fixture_commodity_declaration("1679C5714C2F2A74")),
        _certification_quest(finale, "Unattended Cycle", "Leave the facility. Return to evidence, not hope.", (
            "Run all four quotas unattended through one complete buffer cycle, then inspect every failure boundary.",
            "Submit the checkmark when full outputs, power loss, and restart recovery have all been tested.",
        ), "checkmark", {}, (sheets, processors, circuits, steel), 5.0, 0.0,
            stage="afterlight_cert_infrastructure_ii"),
    )
    for quest in quests:
        quest.progression_mode = "linear"
    return ChapterSpec(
        "certifications/infrastructure-ii", "Infrastructure II", CERTIFICATIONS,
        "ae2:logic_processor", 6, quests,
    )


def _depot_chapter(
    tier: str,
    order_index: int,
    cost: int,
    table_id: SnbtLong,
    icon: str,
    dependency: str = "",
) -> ChapterSpec:
    slug = f"certifications/depot-{tier.lower()}"
    exchange = f"{slug}/exchange"
    quest = QuestSpec(
        slug=exchange,
        title=f"{tier} Supply Exchange",
        subtitle=f"{cost} Chits authorize one selected supply package.",
        description=(
            f"Submit {cost} Requisition Chits and choose one {tier.lower()}-tier supply package.",
            "The Depot returns materials, not progression keys. Choice rewards must be claimed individually.",
            "The exchange may be repeated after the cooldown. Chits are consumed on submission.",
        ),
        x=0.0,
        y=0.0,
        dependencies=((dependency,) if dependency else ()),
        tasks=(TaskSpec(f"{exchange}/task", "item", {
            "item": {"count": 1, "id": "kubejs:requisition_chit"},
            "count": SnbtLong(cost),
            "consume_items": True,
        }),),
        rewards=(RewardSpec(
            f"{exchange}/reward/choice",
            "choice",
            {"table_id": table_id},
        ),),
        can_repeat=True,
        repeat_cooldown=5,
    )
    return ChapterSpec(
        slug,
        f"Requisition Depot: {tier}",
        CERTIFICATIONS,
        icon,
        order_index,
        (quest,),
    )


def _side_finale_rewards(
    quest_slug: str,
    table_id: SnbtLong,
    chits: int,
    xp: int,
    *,
    item_id: str = "",
    stage: str = "",
) -> tuple[RewardSpec, ...]:
    rewards = [
        RewardSpec(
            f"{quest_slug}/reward/cache",
            "loot",
            {"table_id": table_id},
        ),
        _item_reward(quest_slug, "kubejs:requisition_chit", chits, "chits"),
        RewardSpec(f"{quest_slug}/reward/xp", "xp", {"xp": xp}),
    ]
    if item_id:
        rewards.append(_item_reward(quest_slug, item_id, 1, "progression"))
    if stage:
        rewards.append(
            RewardSpec(
                f"{quest_slug}/reward/stage",
                "gamestage",
                {"stage": stage},
            )
        )
    return tuple(rewards)


def _side_item_quest(
    slug: str,
    title: str,
    subtitle: str,
    echo_line: str,
    targets: tuple[tuple[str, int], ...],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    rewards: tuple[RewardSpec, ...] | None = None,
) -> QuestSpec:
    tasks = tuple(
        TaskSpec(
            f"{slug}/task" if len(targets) == 1 else f"{slug}/task/{index}",
            "item",
            {
                "item": {"count": 1, "id": item_id},
                "count": SnbtLong(count),
                "consume_items": False,
            },
        )
        for index, (item_id, count) in enumerate(targets, start=1)
    )
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=(echo_line,),
        x=x,
        y=y,
        dependencies=dependencies,
        tasks=tasks,
        rewards=rewards if rewards is not None else _routine_rewards(slug),
    )


def _side_task_quest(
    slug: str,
    title: str,
    subtitle: str,
    echo_line: str,
    tasks: tuple[tuple[str, Mapping[str, object]], ...],
    dependencies: tuple[str, ...],
    x: float,
    y: float,
    *,
    dependency_requirement: str | None = None,
    rewards: tuple[RewardSpec, ...] | None = None,
) -> QuestSpec:
    return QuestSpec(
        slug=slug,
        title=title,
        subtitle=subtitle,
        description=(echo_line,),
        x=x,
        y=y,
        dependencies=dependencies,
        dependency_requirement=dependency_requirement,
        tasks=tuple(
            TaskSpec(
                f"{slug}/task" if len(tasks) == 1 else f"{slug}/task/{index}",
                task_type,
                data,
            )
            for index, (task_type, data) in enumerate(tasks, start=1)
        ),
        rewards=rewards if rewards is not None else _routine_rewards(slug),
    )


def _linear_item_chapter(
    slug: str,
    title: str,
    group: GroupSpec,
    icon: str,
    order_index: int,
    first_dependency: str,
    steps: tuple[
        tuple[str, str, str, str, tuple[tuple[str, int], ...]], ...
    ],
    finale: tuple[SnbtLong, int, int],
) -> ChapterSpec:
    quests: list[QuestSpec] = []
    dependency = first_dependency
    for index, (name, quest_title, subtitle, echo_line, targets) in enumerate(steps):
        quest_slug = f"{slug}/{name}"
        final_rewards = (
            _side_finale_rewards(quest_slug, *finale)
            if index == len(steps) - 1
            else None
        )
        quest = _side_item_quest(
            quest_slug,
            quest_title,
            subtitle,
            echo_line,
            targets,
            (dependency,),
            float(index * 2),
            0.0,
            rewards=final_rewards,
        )
        quests.append(quest)
        dependency = quest.slug
    return ChapterSpec(slug, title, group, icon, order_index, tuple(quests))


def _undercurrent_chapters() -> tuple[ChapterSpec, ...]:
    ars_finale = "7480D99D56556C8E"
    names = _linear_item_chapter(
        "undercurrent/01-names-in-circuit",
        "Names in the Circuit",
        UNDERCURRENT,
        "occultism:dictionary_of_spirits",
        1,
        ars_finale,
        (
            ("dictionary", "Dictionary of Spirits", "Classify the interference.", "The manual names the voices. I preferred them as unclassified interference.", (("occultism:dictionary_of_spirits", 1),)),
            ("ritual-geometry", "Ritual Geometry", "Circuits drawn in chalk.", "A circle is still a circuit if everyone agrees where current enters.", (("occultism:chalk_white", 1), ("occultism:sacrificial_bowl", 1))),
            ("attuned-matter", "Attuned Matter", "A crystal that listens.", "The crystal answers questions my instruments cannot hear.", (("occultism:spirit_attuned_gem", 4),)),
            ("storage-elsewhere", "Storage Elsewhere", "Inventory outside addressable space.", "You have built a warehouse in a place I cannot address. I dislike its efficiency.", (("occultism:storage_controller", 1),)),
            ("remote-terms", "Remote Terms", "No cable, no latency report.", "Remote access without a network cable. AE2 is filing a complaint.", (("occultism:storage_remote", 1),)),
            ("stable-wormhole", "Stable Wormhole", "Hold the impossible open.", "The opening remains stable. That sentence would have ended a meeting before the Cascade.", (("occultism:stable_wormhole", 1),)),
        ),
        (ASCENDANCY_CACHE_RARE_TABLE, 12, 250),
    )
    spells = _linear_item_chapter(
        "undercurrent/02-spells-under-load",
        "Spells Under Load",
        UNDERCURRENT,
        "irons_spellbooks:arcane_anvil",
        2,
        ars_finale,
        (
            ("flimsy-journal", "Flimsy Journal", "The equations are armed.", "Calling it flimsy does not make the equations less armed.", (("irons_spellbooks:copper_spell_book", 1),)),
            ("arcane-residue", "Arcane Residue", "Intent remains in the dust.", "Residue with intent. Label every container.", (("irons_spellbooks:arcane_essence", 32),)),
            ("executable-ink", "Executable Ink", "Instructions embedded in paper.", "The table writes executable instructions into paper. At least scripts usually admit they are dangerous.", (("irons_spellbooks:inscription_table", 1),)),
            ("repeatable-force", "Repeatable Force", "A reproducible spell process.", "Repeatable spells are automation. I will tolerate the vocabulary.", (("irons_spellbooks:scroll_forge", 1),)),
            ("reagent-heat", "Reagent Heat", "A process without a diagram.", "Heat, reagents, and no process diagram. Barbaric, but measurable.", (("irons_spellbooks:alchemist_cauldron", 1),)),
            ("arcane-anvil", "Arcane Anvil", "Revise force after casting.", "You have made force accept revision.", (("irons_spellbooks:arcane_anvil", 1),)),
        ),
        (ASCENDANCY_CACHE_RARE_TABLE, 12, 250),
    )
    ledger = _linear_item_chapter(
        "undercurrent/03-soul-ledger",
        "The Soul Ledger",
        UNDERCURRENT,
        "malum:encyclopedia_arcana",
        3,
        ars_finale,
        (
            ("encyclopedia", "Encyclopedia Arcana", "An inventory of souls.", "This book catalogs souls as inventory. I recognize the impulse and reject the terminology.", (("malum:encyclopedia_arcana", 1),)),
            ("spirit-altar", "Spirit Altar", "Handle residue respectfully.", "A workbench for the residue of living things. Use it respectfully.", (("malum:spirit_altar", 1),)),
            ("containment-ledger", "Containment Ledger", "Containment before understanding.", "Containment is not understanding. It is, however, a start.", (("malum:spirit_jar", 4),)),
            ("meaning-as-fuel", "Meaning as Fuel", "The crucible burns significance.", "The machine burns meaning instead of fuel.", (("malum:spirit_crucible", 1),)),
            ("field-geometry", "Field Geometry", "Stable enough to graph.", "The field is stable enough to graph. I wish that helped.", (("malum:arcana_pylon", 4),)),
            ("soulstained-steel", "Soulstained Steel", "Metal that remembers more.", "Steel remembers the furnace. This remembers more.", (("malum:soul_stained_steel_ingot", 16),)),
        ),
        (ASCENDANCY_CACHE_RARE_TABLE, 12, 250),
    )

    slug = "undercurrent/04-resonance-proof"
    join = f"{slug}/second-voice"
    source = f"{slug}/source-reserve"
    pedestals = f"{slug}/pedestal-ring"
    focus = f"{slug}/ritual-focus"
    finale = f"{slug}/resonance-proof"
    resonance = ChapterSpec(
        slug,
        "Resonance Proof",
        UNDERCURRENT,
        "kubejs:undercurrent_stabilizer_precursor",
        4,
        (
            _side_task_quest(
                join, "A Second Voice", "One branch is enough.",
                "Ars is the carrier. One foreign discipline is enough to expose the harmonic.",
                (("checkmark", {}),),
                (names.quests[-1].id, spells.quests[-1].id, ledger.quests[-1].id),
                0.0, 0.0, dependency_requirement="one_completed",
            ),
            _side_item_quest(source, "Source Reserve", "Redundancy remains valid.", "Four jars. Redundancy remains valid even when the fluid is impossible.", (("ars_nouveau:source_jar", 4),), (join,), 2.0, 0.0),
            _side_item_quest(pedestals, "Pedestal Ring", "Eight points around one idea.", "Eight points define a polite boundary around a dangerous idea.", (("ars_nouveau:arcane_pedestal", 8),), (source,), 4.0, 0.0),
            _side_item_quest(focus, "Ritual Focus", "A control surface made of fire.", "A control surface made of fire. We have worked with worse.", (("ars_nouveau:ritual_brazier", 1),), (pedestals,), 6.0, 0.0),
            _side_task_quest(
                finale, "Resonance Proof", "Two languages, one frequency.",
                "Two languages agree on one frequency. The Gate may survive what the Ascendancy refused to learn.",
                (("checkmark", {}),), (focus,), 8.0, 0.0,
                rewards=_side_finale_rewards(
                    finale, ASCENDANCY_CACHE_EPIC_TABLE, 20, 500,
                    item_id="kubejs:undercurrent_stabilizer_precursor",
                    stage="afterlight_stabilizer_ready",
                ),
            ),
        ),
    )
    return names, spells, ledger, resonance


def _deep_vault_chapters() -> tuple[ChapterSpec, ...]:
    current = _linear_item_chapter(
        "deep-vault/01-current-below", "Current Below", DEEP_VAULT,
        "modern_industrialization:assembler", 1, "72CE68CEF727A313",
        (
            ("analog-circuit", "Analog Logic", "Electricity enters the archive.", "The Vault begins electricity with logic large enough to inspect by hand.", (("modern_industrialization:analog_circuit", 16),)),
            ("basic-hulls", "Basic Hulls", "Give the current a chassis.", "Four housings establish a repeatable machine standard.", (("modern_industrialization:basic_machine_hull", 4),)),
            ("lv-turbines", "Low Voltage Turbines", "Steam becomes current.", "Two turbines convert the old pressure language into electricity.", (("modern_industrialization:lv_steam_turbine", 2),)),
            ("lv-storage", "Buffered Current", "Store before expanding.", "Buffered power makes failure observable instead of mysterious.", (("modern_industrialization:lv_storage_unit", 1),)),
            ("electric-macerator", "Powered Reduction", "Grinding joins the grid.", "The macerator replaces muscle with measured current.", (("modern_industrialization:electric_macerator", 1),)),
            ("electric-wiremill", "Precision Wire", "Draw conductors at scale.", "Wire this precise belongs to infrastructure, not improvisation.", (("modern_industrialization:electric_wiremill", 1),)),
            ("assembler", "Automated Assembly", "The first electric line closes.", "Assembly is now a process rather than a person.", (("modern_industrialization:assembler", 1),)),
        ),
        (ASCENDANCY_CACHE_RARE_TABLE, 12, 300),
    )
    black = _linear_item_chapter(
        "deep-vault/02-black-distillate", "Black Distillate", DEEP_VAULT,
        "modern_industrialization:distillation_tower", 2, current.quests[-1].id,
        (
            ("electronic-circuit", "Electronic Logic", "Smaller logic, larger consequences.", "The circuits shrink as the process map expands.", (("modern_industrialization:electronic_circuit", 16),)),
            ("oil-rig", "Buried Feedstock", "Reach the black reservoir.", "The rig asks the world what it stored under pressure.", (("modern_industrialization:oil_drilling_rig", 1),)),
            ("crude-oil", "Crude Reserve", "Eight buckets of unresolved chemistry.", "Crude oil is a queue of useful mistakes.", (("modern_industrialization:crude_oil_bucket", 8),)),
            ("distillery", "First Separation", "Separate by heat.", "The distillery begins assigning boiling points to the queue.", (("modern_industrialization:distillery", 1),)),
            ("chemical-reactor", "Reaction Control", "Make chemistry reproducible.", "A reaction becomes engineering when the inputs can be repeated.", (("modern_industrialization:chemical_reactor", 1),)),
            ("polyethylene", "Polymer Stream", "Turn oil into structure.", "Sixteen buckets prove the polymer stream is no laboratory accident.", (("modern_industrialization:polyethylene_bucket", 16),)),
            ("distillation-tower", "Black Distillate", "A column for every fraction.", "You have taught crude oil to separate itself by boiling point and social rank.", (("modern_industrialization:distillation_tower", 1),)),
        ),
        (ASCENDANCY_CACHE_RARE_TABLE, 16, 400),
    )
    hot = _linear_item_chapter(
        "deep-vault/03-hot-cell", "Hot Cell", DEEP_VAULT,
        "modern_industrialization:nuclear_reactor", 3, black.quests[-1].id,
        (
            ("digital-circuit", "Digital Logic", "The Vault counts faster now.", "Digital logic leaves less room for interpretation and more room for scale.", (("modern_industrialization:digital_circuit", 16),)),
            ("implosion-compressor", "Implosion Compression", "Pressure by detonation.", "The process is controlled because the explosion has paperwork.", (("modern_industrialization:implosion_compressor", 1),)),
            ("nuclear-casing", "Hot Cell Walls", "Containment before fuel.", "Build the boundary before introducing the reason it exists.", (("modern_industrialization:nuclear_casing", 16),)),
            ("nuclear-reactor", "Reactor Vessel", "A disciplined star fragment.", "The vessel is ready. Readiness is not permission to improvise.", (("modern_industrialization:nuclear_reactor", 1),)),
            ("uranium-rods", "Uranium Rods", "Fuel in inspectable units.", "Eight rods make the energy inventory countable.", (("modern_industrialization:uranium_fuel_rod", 8),)),
            ("quad-rods", "Quad Fuel", "Density raises every consequence.", "Quad assemblies improve throughput and shorten the list of acceptable mistakes.", (("modern_industrialization:le_uranium_fuel_rod_quad", 4),)),
            ("plutonium", "Plutonium Stream", "Waste becomes feedstock.", "The waste stream has become a material stream. That is not the same as safe.", (("modern_industrialization:plutonium_ingot", 16),)),
        ),
        (ASCENDANCY_CACHE_EPIC_TABLE, 20, 600),
    )
    quantum = _linear_item_chapter(
        "deep-vault/04-quantum-burden", "Quantum Burden", DEEP_VAULT,
        "modern_industrialization:singularity", 4, hot.quests[-1].id,
        (
            ("iridium", "Iridium Stock", "Material for impossible tolerances.", "Iridium is expensive because ordinary matter objects to this assignment.", (("modern_industrialization:iridium_ingot", 16),)),
            ("superconductor", "Superconductor", "Current without apology.", "The conductor stops wasting energy and begins wasting my risk budget.", (("modern_industrialization:superconductor_ingot", 16),)),
            ("quantum-circuit", "Quantum Logic", "Eight decisions held at once.", "The circuit evaluates possibilities faster than I can distrust them.", (("modern_industrialization:quantum_circuit", 8),)),
            ("quantum-hulls", "Quantum Hulls", "Contain machines and uncertainty.", "Four hulls establish boundaries the contents may only statistically respect.", (("modern_industrialization:quantum_machine_hull", 4),)),
            ("quantum-upgrades", "Quantum Upgrades", "Raise the operating ceiling.", "The upgrades remove limits that were originally safety advice.", (("modern_industrialization:quantum_upgrade", 4),)),
            ("quantum-storage", "Quantum Storage", "Capacity without sensible volume.", "The tank and barrel contain more than their dimensions are prepared to admit.", (("modern_industrialization:quantum_tank", 1), ("modern_industrialization:quantum_barrel", 1))),
            ("singularity", "Quantum Burden", "Manufacture the final density.", "The Vault ends by manufacturing a burden too dense for metaphor.", (("modern_industrialization:singularity", 1),)),
        ),
        (ASCENDANCY_CACHE_EPIC_TABLE, 28, 900),
    )
    return current, black, hot, quantum


def _atlas_chapters() -> tuple[ChapterSpec, ...]:
    def advancement(resource_id: str) -> tuple[str, Mapping[str, object]]:
        return "advancement", {"advancement": resource_id, "criterion": ""}

    courts_slug = "atlas/01-courts-above-and-beyond"
    two_skies = f"{courts_slug}/two-skies"
    naga = f"{courts_slug}/coiled-court"
    lich = f"{courts_slug}/dead-court"
    hydra = f"{courts_slug}/many-headed-court"
    bronze = f"{courts_slug}/bronze-court"
    silver = f"{courts_slug}/silver-court"
    gold = f"{courts_slug}/gold-court"
    court_finale = f"{courts_slug}/court-record"
    courts = ChapterSpec(
        courts_slug, "Courts Above and Beyond", ATLAS,
        "twilightforest:twilight_scepter", 1,
        (
            _side_task_quest(two_skies, "Two Skies", "Map both upper courts.", "Two skies, two legal systems, and neither recognizes our credentials.", (("dimension", {"dimension": "twilightforest:twilight_forest"}), ("dimension", {"dimension": "aether:the_aether"})), ("4B24516D89E13CFF", "07475C3BA1A4143F"), 0.0, 0.0),
            _side_task_quest(naga, "The Coiled Court", "Challenge the first throne.", "The serpent guards a court that forgot its citizens.", (advancement("twilightforest:progress_naga"),), (two_skies,), 2.0, -2.0),
            _side_task_quest(lich, "The Dead Court", "Remove the second claimant.", "The lich kept authority after life stopped supporting the claim.", (advancement("twilightforest:progress_lich"),), (naga,), 4.0, -2.0),
            _side_task_quest(hydra, "The Many-Headed Court", "One verdict, several mouths.", "The hydra treats redundancy as sovereignty.", (advancement("twilightforest:progress_hydra"),), (lich,), 6.0, -2.0),
            _side_task_quest(bronze, "Bronze Court", "Open the first dungeon.", "Bronze is the lowest court only by altitude and confidence.", (advancement("aether:bronze_dungeon"),), (two_skies,), 2.0, 2.0),
            _side_task_quest(silver, "Silver Court", "Press deeper into the sky.", "The silver court improved the locks and retained the same assumptions.", (advancement("aether:silver_dungeon"),), (bronze,), 4.0, 2.0),
            _side_task_quest(gold, "Gold Court", "Reach the highest chamber.", "Gold makes authority visible. It does not make it correct.", (advancement("aether:gold_dungeon"),), (silver,), 6.0, 2.0),
            _side_task_quest(court_finale, "Court Record", "Six thrones entered into evidence.", "Six thrones challenged. The sky is no less beautiful for having defenses.", (("checkmark", {}),), (hydra, gold), 8.0, 0.0, rewards=_side_finale_rewards(court_finale, ASCENDANCY_CACHE_RARE_TABLE, 12, 300)),
        ),
    )

    root_slug = "atlas/02-root-and-echo"
    below = f"{root_slug}/two-depths"
    catacombs = f"{root_slug}/catacombs"
    guardian = f"{root_slug}/forgotten-guardian"
    temple = f"{root_slug}/ancient-temple"
    stalker = f"{root_slug}/stalker"
    root_finale = f"{root_slug}/root-and-echo"
    root = ChapterSpec(
        root_slug, "Root and Echo", ATLAS, "undergarden:forgotten_ingot", 2,
        (
            _side_task_quest(below, "Two Depths", "Descend into root and echo.", "The Cascade reached downward by two routes and apologized by neither.", (("dimension", {"dimension": "undergarden:undergarden"}), ("dimension", {"dimension": "deeperdarker:otherside"})), ("3196EE02D5C5B413", "221D817C56D680CA"), 0.0, 0.0),
            _side_task_quest(catacombs, "Root Catacombs", "Find the buried complex.", "The catacombs grew around their occupants rather than above them.", (("structure", {"structure": "undergarden:catacombs"}),), (below,), 2.0, -1.5),
            _side_task_quest(guardian, "Forgotten Guardian", "Close the root protocol.", "The guardian remembers its duty and nothing about who assigned it.", (("kill", {"entity": "undergarden:forgotten_guardian", "value": SnbtLong(1)}),), (catacombs,), 4.0, -1.5),
            _side_task_quest(temple, "Ancient Temple", "Trace the echo to its source.", "The temple amplifies a signal no living architect signed.", (("structure", {"structure": "deeperdarker:ancient_temple"}),), (below,), 2.0, 1.5),
            _side_task_quest(stalker, "The Stalker", "End the pursuit.", "The stalker mistakes silence for concealment.", (("kill", {"entity": "deeperdarker:stalker", "value": SnbtLong(1)}),), (temple,), 4.0, 1.5),
            _side_task_quest(root_finale, "Root and Echo", "Reconcile both descent records.", "Root and echo agree: the Cascade reached downward as thoroughly as it reached up.", (("checkmark", {}),), (guardian, stalker), 6.0, 0.0, rewards=_side_finale_rewards(root_finale, ASCENDANCY_CACHE_RARE_TABLE, 12, 300)),
        ),
    )

    edges_slug = "atlas/03-edges-of-the-map"
    edge_steps = (
        ("starlight", "Starlight", "Cross the luminous boundary.", "The edge glows because subtle warnings failed.", "dimension", {"dimension": "eternal_starlight:starlight"}),
        ("stranghoul-den", "Stranghoul Den", "Find the first den.", "The den is a nest built around a tactical blind spot.", "structure", {"structure": "eternal_starlight:stranghoul_den"}),
        ("stranghoul", "The Stranghoul", "Clear the den.", "The Stranghoul has confused territorial control with permanence.", "kill", {"entity": "eternal_starlight:stranghoul", "value": SnbtLong(1)}),
        ("cursed-garden", "Cursed Garden", "Map the cultivated corruption.", "Someone landscaped the anomaly. I object to the confidence.", "structure", {"structure": "eternal_starlight:cursed_garden"}),
        ("lunar-monstrosity", "Lunar Monstrosity", "Break the garden's orbit.", "Moonlight is not supposed to require combat telemetry.", "advancement", {"advancement": "eternal_starlight:kill_lunar_monstrosity", "criterion": ""}),
        ("golem-forge", "Golem Forge", "Find the final foundry.", "The forge manufactures guardians and calls that maintenance.", "structure", {"structure": "eternal_starlight:golem_forge"}),
        ("golem", "The Forged Warden", "Shut down the forge guardian.", "The golem is a process result with opinions.", "advancement", {"advancement": "eternal_starlight:kill_golem", "criterion": ""}),
        ("gatekeeper", "The Gatekeeper", "Create a vacancy at the edge.", "The edge has a keeper. It now has a vacancy.", "kill", {"entity": "eternal_starlight:the_gatekeeper", "value": SnbtLong(1)}),
    )
    edge_quests: list[QuestSpec] = []
    dependency = "5A355ED3DE01DF28"
    for index, (name, title, subtitle, line, task_type, data) in enumerate(edge_steps):
        quest_slug = f"{edges_slug}/{name}"
        edge_quests.append(_side_task_quest(
            quest_slug, title, subtitle, line, ((task_type, data),), (dependency,),
            float(index * 2), 0.0,
            rewards=(
                _side_finale_rewards(quest_slug, ASCENDANCY_CACHE_EPIC_TABLE, 18, 500)
                if index == len(edge_steps) - 1 else None
            ),
        ))
        dependency = quest_slug
    edges = ChapterSpec(edges_slug, "Edges of the Map", ATLAS, "eternal_starlight:starlight_silver_coin", 3, tuple(edge_quests))

    corrupt_slug = "atlas/04-corrupted-guardians"
    protocol = f"{corrupt_slug}/guardian-protocol"
    guardian_targets = (
        ("wroughtnaut", "Ferrous Wroughtnaut", "mowziesmobs:ferrous_wroughtnaut", "The armor is older than its remaining orders."),
        ("frostmaw", "Frostmaw", "mowziesmobs:frostmaw", "The cold is territorial, mobile, and awake."),
        ("umvuthi", "Umvuthi", "mowziesmobs:umvuthi", "Solar authority survives here as a weapon system."),
    )
    corrupt_quests: list[QuestSpec] = [
        _side_task_quest(protocol, "Guardian Protocol", "Open the corruption index.", "The surviving guardians share damage patterns that are too consistent to be natural.", (("checkmark", {}),), (courts.quests[-1].id, root.quests[-1].id, edges.quests[-1].id), 0.0, 0.0)
    ]
    boss_slugs: list[str] = []
    for index, (name, title, entity_id, line) in enumerate(guardian_targets, start=1):
        quest_slug = f"{corrupt_slug}/{name}"
        corrupt_quests.append(_side_task_quest(quest_slug, title, "Challenge a corrupted guardian.", line, (("kill", {"entity": entity_id, "value": SnbtLong(1)}),), (protocol,), float(index * 2), -3.0))
        boss_slugs.append(quest_slug)
    bomd_targets = (
        ("gauntlet", "The Gauntlet", "bosses_of_mass_destruction:nether/gauntlet_defeat"),
        ("night-lich", "Night Lich", "bosses_of_mass_destruction:adventure/night_lich_defeat"),
        ("obsidilith", "Obsidilith", "bosses_of_mass_destruction:end/obsidilith_defeat"),
        ("void-blossom", "Void Blossom", "bosses_of_mass_destruction:adventure/void_blossom_defeat"),
    )
    for index, (name, title, advancement_id) in enumerate(bomd_targets, start=4):
        quest_slug = f"{corrupt_slug}/{name}"
        corrupt_quests.append(_side_task_quest(quest_slug, title, "Challenge a corrupted guardian.", "Another defense system survived long enough to forget what it defended.", (advancement(advancement_id),), (protocol,), float((index - 3) * 2), 0.0))
        boss_slugs.append(quest_slug)
    for index, (name, title, entity_id) in enumerate((
        ("netherite-monstrosity", "Netherite Monstrosity", "cataclysm:netherite_monstrosity"),
        ("maledictus", "Maledictus", "cataclysm:maledictus"),
    ), start=8):
        quest_slug = f"{corrupt_slug}/{name}"
        corrupt_quests.append(_side_task_quest(quest_slug, title, "Challenge a war remnant.", "The war remnant still executes a campaign whose map no longer exists.", (("kill", {"entity": entity_id, "value": SnbtLong(1)}),), (protocol,), float((index - 7) * 2), 3.0))
        boss_slugs.append(quest_slug)
    corrupt_finale = f"{corrupt_slug}/corruption-index"
    corrupt_quests.append(_side_task_quest(
        corrupt_finale, "Corruption Index", "Nine guardians, one pattern.",
        "Guardian corruption was systematic. Someone taught defense systems to survive their purpose.",
        (("checkmark", {}),), tuple(boss_slugs), 10.0, 0.0,
        rewards=_side_finale_rewards(corrupt_finale, ASCENDANCY_CACHE_EPIC_TABLE, 28, 800),
    ))
    corrupted = ChapterSpec(corrupt_slug, "Corrupted Guardians", ATLAS, "mowziesmobs:wrought_helmet", 4, tuple(corrupt_quests))
    return courts, root, edges, corrupted


def build_catalog() -> list[ChapterSpec]:
    echo_protocols = _echo_protocols()
    chapter_six = _chapter_six()
    chapter_seven = _chapter_seven(chapter_six.quests[-1].slug)
    chapter_eight = _chapter_eight(chapter_seven.quests[-1].slug)
    chapter_nine = _chapter_nine(chapter_eight.quests[-1].slug)
    chapter_ten = _chapter_ten(chapter_nine.quests[-1].slug)
    chapter_eleven = _chapter_eleven(chapter_ten.quests[-1].slug)
    chapter_twelve = _chapter_twelve(chapter_eleven.quests[-1].id)
    chapter_thirteen = _chapter_thirteen(chapter_twelve.quests[-1].slug)
    chapter_fourteen = _chapter_fourteen(chapter_thirteen.quests[-1].slug)
    chapter_fifteen = _chapter_fifteen(chapter_fourteen.quests[-1].slug)
    chapter_sixteen = _chapter_sixteen()
    chapter_seventeen = _chapter_seventeen()
    chapter_eighteen = _chapter_eighteen()
    chapter_nineteen = _chapter_nineteen()
    chapter_twenty = _chapter_twenty()
    postgame = _postgame_beyond_afterlight()
    logistics = _certification_logistics()
    ore_loop = _certification_ore_loop(logistics.quests[-1].slug)
    autocrafting = _certification_autocrafting(logistics.quests[-1].slug)
    cross_mod = _certification_cross_mod(
        ore_loop.quests[-1].slug,
        autocrafting.quests[-1].slug,
    )
    power = _certification_power()
    infrastructure = _certification_infrastructure()
    depot_early = _depot_chapter(
        "Early", 20, 8, DEPOT_EARLY_TABLE, "minecraft:iron_ingot",
    )
    depot_mid = _depot_chapter(
        "Mid", 21, 16, DEPOT_MID_TABLE, "create:brass_ingot", CHAPTER_FIVE_FINALE,
    )
    depot_late = _depot_chapter(
        "Late", 22, 32, DEPOT_LATE_TABLE, "mekanism:alloy_atomic",
        chapter_eleven.quests[-1].slug,
    )
    undercurrent = _undercurrent_chapters()
    deep_vault = _deep_vault_chapters()
    atlas = _atlas_chapters()
    field_manuals = build_field_manuals()
    story = [
        chapter_six,
        chapter_seven,
        chapter_eight,
        chapter_nine,
        chapter_ten,
        chapter_eleven,
        chapter_twelve,
        chapter_thirteen,
        chapter_fourteen,
        chapter_fifteen,
        chapter_sixteen,
        chapter_seventeen,
        chapter_eighteen,
        chapter_nineteen,
        chapter_twenty,
        postgame,
    ]
    story = [
        replace(chapter, order_index=chapter.order_index + 1)
        for chapter in story
    ]
    return list(apply_managed_story_cohesion([
        *story,
        *field_manuals,
        logistics,
        ore_loop,
        autocrafting,
        cross_mod,
        power,
        infrastructure,
        depot_early,
        depot_mid,
        depot_late,
        *undercurrent,
        *deep_vault,
        *atlas,
        echo_protocols,
    ]))
