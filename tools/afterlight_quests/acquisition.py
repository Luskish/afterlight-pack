from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Literal, Mapping, TypeAlias


SCHEMA_VERSION = 1
NONCE_PLACEHOLDER = "__AFTERLIGHT_BOOT_NONCE__"
ACQUISITION_AUDIT_RELATIVE = (
    "kubejs/server_scripts/afterlight/generated_manual_acquisition_audit.js"
)
FIXTURE_RELATIVE = "tools/fixtures/quests/manual-acquisition.json"

_APPROVED_EXPLICIT_QUEST_IDS = MappingProxyType(
    {
        "manuals/applied-energistics-2/read-the-lattice": "70380821D8D0339D",
        "manuals/create/ponder-kinetics": "686943DC0749D6E0",
        "manuals/immersive-engineering/recover-field-manual": "3E77A16CB0C0AD11",
        "manuals/mekanism/configure-the-first-machine": "6B09A1A11CD08E68",
        "manuals/nuclear-systems/safety-before-output": "4EEAB6F41DB426E7",
        "manuals/oritech/frontier-orientation": "6CC0CCE16F9FB5BE",
        "manuals/pneumaticcraft/read-pressure-safely": "084209B68927F9FC",
        "manuals/power-networks/define-the-grid": "5334545A948815F6",
    }
)
_APPROVED_EXPLICIT_TASK_IDS: Mapping[str, str] = MappingProxyType({})


JSONScalar: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONScalar | tuple["JSONValue", ...] | Mapping[str, "JSONValue"]


def _frozen_mapping(value: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class StackProof:
    id: str
    count: int
    components: Mapping[str, JSONScalar]

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", _frozen_mapping(self.components))


@dataclass(frozen=True)
class RecipeProof:
    task_id: str
    id: str
    recipe_type: str
    serializer: str
    extractor: Literal["result_item"]
    output: StackProof


@dataclass(frozen=True)
class StackOutputProof:
    kind: Literal["stack"]
    task_id: str | None
    id: str
    count: int
    components: Mapping[str, JSONScalar]

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", _frozen_mapping(self.components))


@dataclass(frozen=True)
class TagOutputProof:
    kind: Literal["item_tag"]
    id: str
    count: int


ProcessOutputProof: TypeAlias = StackOutputProof | TagOutputProof


@dataclass(frozen=True)
class ProcessStepProof:
    id: str
    recipe_type: str
    serializer: str
    extractor: Literal[
        "result_item",
        "ie_coke",
        "create_rollable_results",
        "create_sequenced",
        "pnc_outputs",
        "pnc_heat_frame",
        "pnc_assembly",
    ]
    role: Literal["intermediate", "final"]
    outputs: tuple[ProcessOutputProof, ...]
    attributes: Mapping[str, JSONScalar | StackProof]

    def __post_init__(self) -> None:
        object.__setattr__(self, "outputs", tuple(self.outputs))
        object.__setattr__(self, "attributes", _frozen_mapping(self.attributes))


@dataclass(frozen=True)
class FluidContainerProof:
    kind: Literal["fluid_container"]
    task_id: str
    source_step: int
    cycles: int
    fluid: str
    millibuckets: int
    output: StackProof


@dataclass(frozen=True)
class EntityInteractionProof:
    kind: Literal["entity_interaction"]
    task_id: str
    source_step: int
    input: StackProof
    entity_id: str
    item_class: str
    method: str
    output: StackProof


NativeCheckProof: TypeAlias = FluidContainerProof | EntityInteractionProof


@dataclass(frozen=True)
class ResourceProof:
    location: str
    sha256: str


@dataclass(frozen=True)
class CriterionProof:
    name: str
    trigger: str
    instance_class: str
    fields: Mapping[str, JSONScalar]

    def __post_init__(self) -> None:
        object.__setattr__(self, "fields", _frozen_mapping(self.fields))


@dataclass(frozen=True)
class AdvancementProof:
    id: str
    criteria: tuple[CriterionProof, ...]
    requirements: tuple[tuple[str, ...], ...]
    resource: ResourceProof

    def __post_init__(self) -> None:
        object.__setattr__(self, "criteria", tuple(self.criteria))
        object.__setattr__(
            self,
            "requirements",
            tuple(tuple(requirement) for requirement in self.requirements),
        )


@dataclass(frozen=True)
class RegistryKeyProof:
    registry: str
    key: str


@dataclass(frozen=True)
class TaskItemProof:
    task_id: str
    id: str
    count: int
    components: Mapping[str, JSONScalar]

    def __post_init__(self) -> None:
        object.__setattr__(self, "components", _frozen_mapping(self.components))


@dataclass(frozen=True)
class TagMembershipProof:
    id: str
    members: tuple[TaskItemProof, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "members", tuple(self.members))


@dataclass(frozen=True)
class EquivalentTagProof:
    id: str
    equals: str
    minimum_members: int


@dataclass(frozen=True)
class NativeTargetProof:
    block_id: str
    loot_table_id: str
    silk_touch: bool


@dataclass(frozen=True)
class WorldgenProof:
    registry_keys: tuple[RegistryKeyProof, ...]
    resources: tuple[ResourceProof, ...]
    item_tag: TagMembershipProof
    biome_tag: EquivalentTagProof
    native_target: NativeTargetProof

    def __post_init__(self) -> None:
        object.__setattr__(self, "registry_keys", tuple(self.registry_keys))
        object.__setattr__(self, "resources", tuple(self.resources))


@dataclass(frozen=True)
class ManualCheckProof:
    locale: str
    localization_key: str


@dataclass(frozen=True)
class RecipeNodeProof:
    recipes: tuple[RecipeProof, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "recipes", tuple(self.recipes))


@dataclass(frozen=True)
class ProcessNodeProof:
    steps: tuple[ProcessStepProof, ...]
    native_checks: tuple[NativeCheckProof, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "native_checks", tuple(self.native_checks))


@dataclass(frozen=True)
class AcquisitionNode:
    quest_id: str
    quest_slug: str
    task_ids: tuple[str, ...]
    method: Literal["recipe", "process", "worldgen", "advancement", "manual_check"]
    proof: RecipeNodeProof | ProcessNodeProof | AdvancementProof | WorldgenProof | ManualCheckProof

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_ids", tuple(self.task_ids))


@dataclass(frozen=True)
class AcquisitionManifest:
    schema_version: int
    nodes: tuple[AcquisitionNode, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(self.nodes))


_FTB_ID = re.compile(r"^[0-7][0-9A-F]{15}$")
_RESOURCE_ID = re.compile(r"^[a-z0-9_.-]+:[a-z0-9_./-]+$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_NONCE = re.compile(r"^[A-Za-z0-9._-]+$")
_METHODS = frozenset(
    {"recipe", "process", "worldgen", "advancement", "manual_check"}
)
_METHOD_COUNTS = {
    "recipe": 53,
    "process": 9,
    "worldgen": 1,
    "advancement": 8,
    "manual_check": 10,
}
_PROCESS_EXTRACTORS = frozenset(
    {
        "result_item",
        "ie_coke",
        "create_rollable_results",
        "create_sequenced",
        "pnc_outputs",
        "pnc_heat_frame",
        "pnc_assembly",
    }
)


def _duplicate_rejecting_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError(f"duplicate JSON key {key}")
        value[key] = child
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid JSON constant {value}")


def _object(value: object, keys: set[str], label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    actual = set(value)
    if actual != keys:
        raise ValueError(
            f"{label} keys changed: missing={sorted(keys - actual)} "
            f"extra={sorted(actual - keys)}"
        )
    return value


def _list(value: object, label: str, *, nonempty: bool = False) -> list[object]:
    if not isinstance(value, list) or (nonempty and not value):
        suffix = " nonempty" if nonempty else ""
        raise ValueError(f"{label} must be a{suffix} array")
    return value


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty string")
    return value


def _integer(
    value: object,
    label: str,
    *,
    minimum: int = 1,
    maximum: int = 2_147_483_647,
) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or value < minimum
        or value > maximum
    ):
        raise ValueError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _finite_number(value: object, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    if not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    return value


def _resource_id(value: object, label: str) -> str:
    identifier = _string(value, label)
    if _RESOURCE_ID.fullmatch(identifier) is None:
        raise ValueError(f"{label} is not a resource location: {identifier!r}")
    return identifier


def _ftb_id(value: object, label: str) -> str:
    identifier = _string(value, label)
    if _FTB_ID.fullmatch(identifier) is None:
        raise ValueError(f"{label} is not a signed-safe FTB ID: {identifier!r}")
    return identifier


def _sha256(value: object, label: str) -> str:
    digest = _string(value, label)
    if _SHA256.fullmatch(digest) is None:
        raise ValueError(f"{label} is not a SHA-256 digest")
    return digest


def _components(value: object, label: str) -> Mapping[str, JSONScalar]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    result: dict[str, JSONScalar] = {}
    for key, child in value.items():
        resource_key = _resource_id(key, f"{label} key")
        if not isinstance(child, str):
            raise ValueError(f"{label} values must be strings")
        result[resource_key] = child
    return result


def _stack(value: object, label: str) -> StackProof:
    data = _object(value, {"id", "count", "components"}, label)
    return StackProof(
        _resource_id(data["id"], f"{label}.id"),
        _integer(data["count"], f"{label}.count"),
        _components(data["components"], f"{label}.components"),
    )


def _stack_output(value: object, label: str) -> StackOutputProof:
    data = _object(
        value,
        {"kind", "task_id", "id", "count", "components"},
        label,
    )
    if data["kind"] != "stack":
        raise ValueError(f"{label}.kind must be stack")
    task_value = data["task_id"]
    task_id = None if task_value is None else _ftb_id(task_value, f"{label}.task_id")
    return StackOutputProof(
        "stack",
        task_id,
        _resource_id(data["id"], f"{label}.id"),
        _integer(data["count"], f"{label}.count"),
        _components(data["components"], f"{label}.components"),
    )


def _process_output(value: object, label: str) -> ProcessOutputProof:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    kind = value.get("kind")
    if kind == "stack":
        return _stack_output(value, label)
    if kind == "item_tag":
        data = _object(value, {"kind", "id", "count"}, label)
        return TagOutputProof(
            "item_tag",
            _resource_id(data["id"], f"{label}.id"),
            _integer(data["count"], f"{label}.count"),
        )
    raise ValueError(f"{label}.kind is unsupported: {kind!r}")


def _recipe(value: object, label: str) -> RecipeProof:
    data = _object(
        value,
        {"task_id", "id", "recipe_type", "serializer", "extractor", "output"},
        label,
    )
    if data["extractor"] != "result_item":
        raise ValueError(f"{label}.extractor must be result_item")
    return RecipeProof(
        _ftb_id(data["task_id"], f"{label}.task_id"),
        _resource_id(data["id"], f"{label}.id"),
        _resource_id(data["recipe_type"], f"{label}.recipe_type"),
        _resource_id(data["serializer"], f"{label}.serializer"),
        "result_item",
        _stack(data["output"], f"{label}.output"),
    )


def _process_attributes(
    value: object,
    extractor: str,
    recipe_type: str,
    label: str,
) -> Mapping[str, JSONScalar | StackProof]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    expected: set[str]
    if extractor in {"result_item", "create_rollable_results"}:
        expected = set()
    elif extractor == "ie_coke":
        expected = {"creosote_millibuckets"}
    elif extractor == "create_sequenced":
        expected = {"loops", "transitional_output"}
    elif extractor == "pnc_outputs":
        expected = (
            {"loss_rate"}
            if recipe_type == "pneumaticcraft:explosion_crafting"
            else {"pressure"}
        )
    elif extractor == "pnc_heat_frame":
        expected = {"threshold_temperature"}
    else:
        expected = {"program"}
    if set(value) != expected:
        raise ValueError(
            f"{label} keys changed: missing={sorted(expected - set(value))} "
            f"extra={sorted(set(value) - expected)}"
        )
    if not expected:
        return {}
    if extractor == "create_sequenced":
        return {
            "loops": _integer(value["loops"], f"{label}.loops"),
            "transitional_output": _stack(
                value["transitional_output"],
                f"{label}.transitional_output",
            ),
        }
    if "pressure" in expected:
        return {"pressure": _finite_number(value["pressure"], f"{label}.pressure")}
    key = next(iter(expected))
    if key == "program":
        return {key: _string(value[key], f"{label}.{key}")}
    return {key: _integer(value[key], f"{label}.{key}")}


def _process_step(value: object, label: str) -> ProcessStepProof:
    data = _object(
        value,
        {
            "id",
            "recipe_type",
            "serializer",
            "extractor",
            "role",
            "outputs",
            "attributes",
        },
        label,
    )
    extractor = _string(data["extractor"], f"{label}.extractor")
    if extractor not in _PROCESS_EXTRACTORS:
        raise ValueError(f"{label}.extractor is unsupported: {extractor}")
    role = _string(data["role"], f"{label}.role")
    if role not in {"intermediate", "final"}:
        raise ValueError(f"{label}.role is unsupported: {role}")
    recipe_type = _resource_id(data["recipe_type"], f"{label}.recipe_type")
    outputs = tuple(
        _process_output(child, f"{label}.outputs[{index}]")
        for index, child in enumerate(
            _list(data["outputs"], f"{label}.outputs", nonempty=True)
        )
    )
    return ProcessStepProof(
        _resource_id(data["id"], f"{label}.id"),
        recipe_type,
        _resource_id(data["serializer"], f"{label}.serializer"),
        extractor,
        role,
        outputs,
        _process_attributes(
            data["attributes"],
            extractor,
            recipe_type,
            f"{label}.attributes",
        ),
    )


def _native_check(value: object, label: str) -> NativeCheckProof:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    kind = value.get("kind")
    if kind == "fluid_container":
        data = _object(
            value,
            {
                "kind",
                "task_id",
                "source_step",
                "cycles",
                "fluid",
                "millibuckets",
                "output",
            },
            label,
        )
        return FluidContainerProof(
            "fluid_container",
            _ftb_id(data["task_id"], f"{label}.task_id"),
            _integer(data["source_step"], f"{label}.source_step", minimum=0),
            _integer(data["cycles"], f"{label}.cycles"),
            _resource_id(data["fluid"], f"{label}.fluid"),
            _integer(data["millibuckets"], f"{label}.millibuckets"),
            _stack(data["output"], f"{label}.output"),
        )
    if kind == "entity_interaction":
        data = _object(
            value,
            {
                "kind",
                "task_id",
                "source_step",
                "input",
                "entity_id",
                "item_class",
                "method",
                "output",
            },
            label,
        )
        return EntityInteractionProof(
            "entity_interaction",
            _ftb_id(data["task_id"], f"{label}.task_id"),
            _integer(data["source_step"], f"{label}.source_step", minimum=0),
            _stack(data["input"], f"{label}.input"),
            _resource_id(data["entity_id"], f"{label}.entity_id"),
            _string(data["item_class"], f"{label}.item_class"),
            _string(data["method"], f"{label}.method"),
            _stack(data["output"], f"{label}.output"),
        )
    raise ValueError(f"{label}.kind is unsupported: {kind!r}")


def _resource(value: object, label: str) -> ResourceProof:
    data = _object(value, {"location", "sha256"}, label)
    return ResourceProof(
        _resource_id(data["location"], f"{label}.location"),
        _sha256(data["sha256"], f"{label}.sha256"),
    )


def _criterion(value: object, label: str) -> CriterionProof:
    data = _object(value, {"name", "trigger", "instance_class", "fields"}, label)
    raw_fields = data["fields"]
    if not isinstance(raw_fields, dict):
        raise ValueError(f"{label}.fields must be an object")
    criterion_fields: dict[str, JSONScalar] = {}
    for key, child in raw_fields.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label}.fields key must be a nonempty string")
        if not isinstance(child, (str, int, float, bool)) or not (
            not isinstance(child, float) or math.isfinite(child)
        ):
            raise ValueError(f"{label}.fields value must be a JSON scalar")
        criterion_fields[key] = child
    return CriterionProof(
        _string(data["name"], f"{label}.name"),
        _resource_id(data["trigger"], f"{label}.trigger"),
        _string(data["instance_class"], f"{label}.instance_class"),
        criterion_fields,
    )


def _advancement(value: object, label: str) -> AdvancementProof:
    data = _object(value, {"id", "criteria", "requirements", "resource"}, label)
    criteria = tuple(
        _criterion(child, f"{label}.criteria[{index}]")
        for index, child in enumerate(
            _list(data["criteria"], f"{label}.criteria", nonempty=True)
        )
    )
    names = [criterion.name for criterion in criteria]
    if len(names) != len(set(names)):
        raise ValueError(f"{label}.criteria contains duplicate names")
    requirements: list[tuple[str, ...]] = []
    for index, requirement in enumerate(
        _list(data["requirements"], f"{label}.requirements", nonempty=True)
    ):
        values = tuple(
            _string(child, f"{label}.requirements[{index}]")
            for child in _list(
                requirement,
                f"{label}.requirements[{index}]",
                nonempty=True,
            )
        )
        requirements.append(values)
    requirement_names = {name for requirement in requirements for name in requirement}
    if requirement_names != set(names):
        raise ValueError(f"{label}.requirements do not equal criterion names")
    return AdvancementProof(
        _resource_id(data["id"], f"{label}.id"),
        criteria,
        tuple(requirements),
        _resource(data["resource"], f"{label}.resource"),
    )


def _worldgen(value: object, label: str) -> WorldgenProof:
    data = _object(
        value,
        {"registry_keys", "resources", "item_tag", "biome_tag", "native_target"},
        label,
    )
    registry_keys = []
    for index, child in enumerate(
        _list(data["registry_keys"], f"{label}.registry_keys", nonempty=True)
    ):
        entry = _object(child, {"registry", "key"}, f"{label}.registry_keys[{index}]")
        registry_keys.append(
            RegistryKeyProof(
                _resource_id(
                    entry["registry"],
                    f"{label}.registry_keys[{index}].registry",
                ),
                _resource_id(entry["key"], f"{label}.registry_keys[{index}].key"),
            )
        )
    resources = tuple(
        _resource(child, f"{label}.resources[{index}]")
        for index, child in enumerate(
            _list(data["resources"], f"{label}.resources", nonempty=True)
        )
    )
    item_tag_data = _object(data["item_tag"], {"id", "members"}, f"{label}.item_tag")
    members = []
    for index, child in enumerate(
        _list(item_tag_data["members"], f"{label}.item_tag.members", nonempty=True)
    ):
        member = _object(
            child,
            {"task_id", "id", "count", "components"},
            f"{label}.item_tag.members[{index}]",
        )
        members.append(
            TaskItemProof(
                _ftb_id(
                    member["task_id"],
                    f"{label}.item_tag.members[{index}].task_id",
                ),
                _resource_id(
                    member["id"],
                    f"{label}.item_tag.members[{index}].id",
                ),
                _integer(
                    member["count"],
                    f"{label}.item_tag.members[{index}].count",
                ),
                _components(
                    member["components"],
                    f"{label}.item_tag.members[{index}].components",
                ),
            )
        )
    biome = _object(
        data["biome_tag"],
        {"id", "equals", "minimum_members"},
        f"{label}.biome_tag",
    )
    native = _object(
        data["native_target"],
        {"block_id", "loot_table_id", "silk_touch"},
        f"{label}.native_target",
    )
    if not isinstance(native["silk_touch"], bool):
        raise ValueError(f"{label}.native_target.silk_touch must be boolean")
    return WorldgenProof(
        tuple(registry_keys),
        resources,
        TagMembershipProof(
            _resource_id(item_tag_data["id"], f"{label}.item_tag.id"),
            tuple(members),
        ),
        EquivalentTagProof(
            _resource_id(biome["id"], f"{label}.biome_tag.id"),
            _resource_id(biome["equals"], f"{label}.biome_tag.equals"),
            _integer(
                biome["minimum_members"],
                f"{label}.biome_tag.minimum_members",
            ),
        ),
        NativeTargetProof(
            _resource_id(native["block_id"], f"{label}.native_target.block_id"),
            _resource_id(
                native["loot_table_id"],
                f"{label}.native_target.loot_table_id",
            ),
            native["silk_touch"],
        ),
    )


def _manual_check(value: object, task_ids: tuple[str, ...], label: str) -> ManualCheckProof:
    data = _object(value, {"locale", "localization_key"}, label)
    if data["locale"] != "en_us":
        raise ValueError(f"{label}.locale must be en_us")
    if len(task_ids) != 1:
        raise ValueError(f"{label} requires exactly one task")
    expected_key = f"task.{task_ids[0]}.title"
    if data["localization_key"] != expected_key:
        raise ValueError(f"{label}.localization_key must be {expected_key}")
    return ManualCheckProof("en_us", expected_key)


def _node(value: object, index: int) -> AcquisitionNode:
    label = f"nodes[{index}]"
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    method = value.get("method")
    if method not in _METHODS:
        raise ValueError(f"{label}.method is unsupported: {method!r}")
    payload_keys = {
        "recipe": {"recipes"},
        "process": {"steps", "native_checks"},
        "worldgen": {"worldgen"},
        "advancement": {"advancement"},
        "manual_check": {"manual_check"},
    }[method]
    data = _object(
        value,
        {"method", "quest_id", "quest_slug", "task_ids"} | payload_keys,
        label,
    )
    quest_id = _ftb_id(data["quest_id"], f"{label}.quest_id")
    quest_slug = _string(data["quest_slug"], f"{label}.quest_slug")
    if (
        not quest_slug.startswith("manuals/")
        or "//" in quest_slug
        or any(not segment for segment in quest_slug.split("/"))
    ):
        raise ValueError(f"{label}.quest_slug is malformed: {quest_slug!r}")
    task_ids = tuple(
        _ftb_id(child, f"{label}.task_ids[{task_index}]")
        for task_index, child in enumerate(
            _list(data["task_ids"], f"{label}.task_ids", nonempty=True)
        )
    )
    if len(task_ids) != len(set(task_ids)):
        raise ValueError(f"{label}.task_ids contains duplicates")

    if method == "recipe":
        recipes = tuple(
            _recipe(child, f"{label}.recipes[{recipe_index}]")
            for recipe_index, child in enumerate(
                _list(data["recipes"], f"{label}.recipes", nonempty=True)
            )
        )
        if len({recipe.id for recipe in recipes}) != len(recipes):
            raise ValueError(f"{label}.recipes contains duplicate IDs")
        if tuple(recipe.task_id for recipe in recipes) != task_ids:
            raise ValueError(f"{label}.recipes do not cover ordered task_ids")
        proof: RecipeNodeProof | ProcessNodeProof | AdvancementProof | WorldgenProof | ManualCheckProof = RecipeNodeProof(recipes)
    elif method == "process":
        steps = tuple(
            _process_step(child, f"{label}.steps[{step_index}]")
            for step_index, child in enumerate(
                _list(data["steps"], f"{label}.steps", nonempty=True)
            )
        )
        if len({step.id for step in steps}) != len(steps):
            raise ValueError(f"{label}.steps contains duplicate IDs")
        if not any(step.role == "final" for step in steps):
            raise ValueError(f"{label}.steps requires a final step")
        checks = tuple(
            _native_check(child, f"{label}.native_checks[{check_index}]")
            for check_index, child in enumerate(
                _list(data["native_checks"], f"{label}.native_checks")
            )
        )
        covered = [
            output.task_id
            for step_value in steps
            for output in step_value.outputs
            if isinstance(output, StackOutputProof) and output.task_id is not None
        ] + [check.task_id for check in checks]
        if len(covered) != len(set(covered)) or set(covered) != set(task_ids):
            raise ValueError(f"{label} automatic tasks are not covered exactly once")
        if any(check.source_step >= len(steps) for check in checks):
            raise ValueError(f"{label}.native_checks source_step is out of range")
        proof = ProcessNodeProof(steps, checks)
    elif method == "advancement":
        proof = _advancement(data["advancement"], f"{label}.advancement")
    elif method == "worldgen":
        proof = _worldgen(data["worldgen"], f"{label}.worldgen")
        member_tasks = tuple(member.task_id for member in proof.item_tag.members)
        if member_tasks != task_ids:
            raise ValueError(f"{label}.worldgen members do not cover ordered task_ids")
    else:
        proof = _manual_check(data["manual_check"], task_ids, f"{label}.manual_check")
    return AcquisitionNode(quest_id, quest_slug, task_ids, method, proof)


def _contains_u2014(value: object) -> bool:
    if isinstance(value, str):
        return "\u2014" in value
    if isinstance(value, dict):
        return any(_contains_u2014(key) or _contains_u2014(child) for key, child in value.items())
    if isinstance(value, list):
        return any(_contains_u2014(child) for child in value)
    return False


def load_manifest(path: Path) -> AcquisitionManifest:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"cannot read acquisition fixture {path}: {error}") from error
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_duplicate_rejecting_object,
            parse_constant=_reject_json_constant,
        )
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid acquisition fixture JSON: {error}") from error
    if _contains_u2014(parsed):
        raise ValueError("acquisition fixture contains U+2014")
    root = _object(parsed, {"schema_version", "nodes"}, "root")
    if isinstance(root["schema_version"], bool) or root["schema_version"] != SCHEMA_VERSION:
        raise ValueError(f"schema_version must be integer {SCHEMA_VERSION}")
    nodes = tuple(
        _node(child, index)
        for index, child in enumerate(
            _list(root["nodes"], "nodes", nonempty=True)
        )
    )
    if len(nodes) != 81:
        raise ValueError(f"acquisition fixture must contain exactly 81 nodes, got {len(nodes)}")
    quest_ids = [node.quest_id for node in nodes]
    if quest_ids != sorted(quest_ids):
        raise ValueError("acquisition nodes are not sorted by quest_id")
    if len(quest_ids) != len(set(quest_ids)):
        raise ValueError("acquisition fixture contains duplicate quest IDs")
    quest_slugs = [node.quest_slug for node in nodes]
    if len(quest_slugs) != len(set(quest_slugs)):
        raise ValueError("acquisition fixture contains duplicate quest slugs")
    all_task_ids = [task_id for node in nodes for task_id in node.task_ids]
    if len(all_task_ids) != len(set(all_task_ids)):
        raise ValueError("acquisition fixture contains duplicate task IDs")
    method_counts = {method: 0 for method in _METHODS}
    for node in nodes:
        method_counts[node.method] += 1
    if method_counts != _METHOD_COUNTS:
        raise ValueError(
            f"acquisition fixture method counts changed: {method_counts}"
        )
    manifest = AcquisitionManifest(SCHEMA_VERSION, nodes)
    expected = (
        json.dumps(
            manifest_to_data(manifest),
            ensure_ascii=True,
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    if raw != expected:
        raise ValueError("acquisition fixture bytes are not canonical")
    return manifest


def _stack_to_data(value: StackProof) -> dict[str, object]:
    return {
        "components": dict(value.components),
        "count": value.count,
        "id": value.id,
    }


def _process_output_to_data(value: ProcessOutputProof) -> dict[str, object]:
    if isinstance(value, TagOutputProof):
        return {"count": value.count, "id": value.id, "kind": value.kind}
    return {
        "components": dict(value.components),
        "count": value.count,
        "id": value.id,
        "kind": value.kind,
        "task_id": value.task_id,
    }


def _attributes_to_data(
    attributes: Mapping[str, JSONScalar | StackProof],
) -> dict[str, object]:
    return {
        key: _stack_to_data(value) if isinstance(value, StackProof) else value
        for key, value in attributes.items()
    }


def _node_to_data(node: AcquisitionNode) -> dict[str, object]:
    common: dict[str, object] = {
        "method": node.method,
        "quest_id": node.quest_id,
        "quest_slug": node.quest_slug,
        "task_ids": list(node.task_ids),
    }
    proof = node.proof
    if isinstance(proof, RecipeNodeProof):
        common["recipes"] = [
            {
                "extractor": recipe.extractor,
                "id": recipe.id,
                "output": _stack_to_data(recipe.output),
                "recipe_type": recipe.recipe_type,
                "serializer": recipe.serializer,
                "task_id": recipe.task_id,
            }
            for recipe in proof.recipes
        ]
    elif isinstance(proof, ProcessNodeProof):
        common["native_checks"] = [
            (
                {
                    "cycles": check.cycles,
                    "fluid": check.fluid,
                    "kind": check.kind,
                    "millibuckets": check.millibuckets,
                    "output": _stack_to_data(check.output),
                    "source_step": check.source_step,
                    "task_id": check.task_id,
                }
                if isinstance(check, FluidContainerProof)
                else {
                    "entity_id": check.entity_id,
                    "input": _stack_to_data(check.input),
                    "item_class": check.item_class,
                    "kind": check.kind,
                    "method": check.method,
                    "output": _stack_to_data(check.output),
                    "source_step": check.source_step,
                    "task_id": check.task_id,
                }
            )
            for check in proof.native_checks
        ]
        common["steps"] = [
            {
                "attributes": _attributes_to_data(step.attributes),
                "extractor": step.extractor,
                "id": step.id,
                "outputs": [_process_output_to_data(output) for output in step.outputs],
                "recipe_type": step.recipe_type,
                "role": step.role,
                "serializer": step.serializer,
            }
            for step in proof.steps
        ]
    elif isinstance(proof, AdvancementProof):
        common["advancement"] = {
            "criteria": [
                {
                    "fields": dict(criterion.fields),
                    "instance_class": criterion.instance_class,
                    "name": criterion.name,
                    "trigger": criterion.trigger,
                }
                for criterion in proof.criteria
            ],
            "id": proof.id,
            "requirements": [list(requirement) for requirement in proof.requirements],
            "resource": {
                "location": proof.resource.location,
                "sha256": proof.resource.sha256,
            },
        }
    elif isinstance(proof, WorldgenProof):
        common["worldgen"] = {
            "biome_tag": {
                "equals": proof.biome_tag.equals,
                "id": proof.biome_tag.id,
                "minimum_members": proof.biome_tag.minimum_members,
            },
            "item_tag": {
                "id": proof.item_tag.id,
                "members": [
                    {
                        "components": dict(member.components),
                        "count": member.count,
                        "id": member.id,
                        "task_id": member.task_id,
                    }
                    for member in proof.item_tag.members
                ],
            },
            "native_target": {
                "block_id": proof.native_target.block_id,
                "loot_table_id": proof.native_target.loot_table_id,
                "silk_touch": proof.native_target.silk_touch,
            },
            "registry_keys": [
                {"key": key.key, "registry": key.registry}
                for key in proof.registry_keys
            ],
            "resources": [
                {"location": resource.location, "sha256": resource.sha256}
                for resource in proof.resources
            ],
        }
    elif isinstance(proof, ManualCheckProof):
        common["manual_check"] = {
            "locale": proof.locale,
            "localization_key": proof.localization_key,
        }
    else:
        raise TypeError(f"unsupported acquisition proof {type(proof).__name__}")
    return common


def manifest_to_data(manifest: AcquisitionManifest) -> dict[str, object]:
    return {
        "nodes": [_node_to_data(node) for node in manifest.nodes],
        "schema_version": manifest.schema_version,
    }


def canonical_bytes(value: object) -> bytes:
    if isinstance(value, AcquisitionManifest):
        value = manifest_to_data(value)
    elif isinstance(value, AcquisitionNode):
        value = _node_to_data(value)
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def manifest_digest(manifest: AcquisitionManifest) -> str:
    return hashlib.sha256(canonical_bytes(manifest_to_data(manifest))).hexdigest()


def proof_digest(node: AcquisitionNode, manifest_sha256: str, nonce: str) -> str:
    if _SHA256.fullmatch(manifest_sha256) is None:
        raise ValueError("manifest digest is malformed")
    if _NONCE.fullmatch(nonce) is None:
        raise ValueError("acquisition audit nonce is malformed")
    material = (
        b"AFTERLIGHT-ACQUISITION-PROOF\0"
        + manifest_sha256.encode("ascii")
        + b"\0"
        + nonce.encode("ascii")
        + b"\0"
        + canonical_bytes(_node_to_data(node))
    )
    return hashlib.sha256(material).hexdigest()


_AUDIT_RUNTIME_SOURCE = r"""
const AFTERLIGHT_SHA256_CONSTANTS = [
  0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
  0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
  0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
  0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
  0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
  0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
  0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
  0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
  0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
  0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
  0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
  0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
  0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
  0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
  0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
  0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

function afterlightRotateRight(value, count) {
  return (value >>> count) | (value << (32 - count))
}

function afterlightSha256Bytes(input) {
  var bytes = []
  for (var byteIndex = 0; byteIndex < input.length; byteIndex++) {
    bytes.push(Number(input[byteIndex]) & 0xFF)
  }

  var bitLength = bytes.length * 8
  bytes.push(0x80)
  while (bytes.length % 64 !== 56) bytes.push(0)
  var bitLengthHigh = Math.floor(bitLength / 0x100000000)
  var bitLengthLow = bitLength >>> 0
  bytes.push(
    (bitLengthHigh >>> 24) & 0xFF,
    (bitLengthHigh >>> 16) & 0xFF,
    (bitLengthHigh >>> 8) & 0xFF,
    bitLengthHigh & 0xFF,
    (bitLengthLow >>> 24) & 0xFF,
    (bitLengthLow >>> 16) & 0xFF,
    (bitLengthLow >>> 8) & 0xFF,
    bitLengthLow & 0xFF
  )

  var hash = [
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
  ]
  var words = new Array(64)
  for (var offset = 0; offset < bytes.length; offset += 64) {
    var cursor = offset
    for (var wordIndex = 0; wordIndex < 16; wordIndex++) {
      words[wordIndex] = (
        (bytes[cursor] << 24)
        | (bytes[cursor + 1] << 16)
        | (bytes[cursor + 2] << 8)
        | bytes[cursor + 3]
      ) >>> 0
      cursor += 4
    }
    for (var scheduleIndex = 16; scheduleIndex < 64; scheduleIndex++) {
      var prior = words[scheduleIndex - 15]
      var recent = words[scheduleIndex - 2]
      var sigma0 = afterlightRotateRight(prior, 7)
        ^ afterlightRotateRight(prior, 18) ^ (prior >>> 3)
      var sigma1 = afterlightRotateRight(recent, 17)
        ^ afterlightRotateRight(recent, 19) ^ (recent >>> 10)
      words[scheduleIndex] = (
        words[scheduleIndex - 16] + sigma0
        + words[scheduleIndex - 7] + sigma1
      ) >>> 0
    }

    var a = hash[0]
    var b = hash[1]
    var c = hash[2]
    var d = hash[3]
    var e = hash[4]
    var f = hash[5]
    var g = hash[6]
    var h = hash[7]
    for (var roundIndex = 0; roundIndex < 64; roundIndex++) {
      var sum1 = afterlightRotateRight(e, 6)
        ^ afterlightRotateRight(e, 11) ^ afterlightRotateRight(e, 25)
      var choice = (e & f) ^ (~e & g)
      var temporary1 = (
        h + sum1 + choice
        + AFTERLIGHT_SHA256_CONSTANTS[roundIndex] + words[roundIndex]
      ) >>> 0
      var sum0 = afterlightRotateRight(a, 2)
        ^ afterlightRotateRight(a, 13) ^ afterlightRotateRight(a, 22)
      var majority = (a & b) ^ (a & c) ^ (b & c)
      var temporary2 = (sum0 + majority) >>> 0
      h = g
      g = f
      f = e
      e = (d + temporary1) >>> 0
      d = c
      c = b
      b = a
      a = (temporary1 + temporary2) >>> 0
    }

    hash[0] = (hash[0] + a) >>> 0
    hash[1] = (hash[1] + b) >>> 0
    hash[2] = (hash[2] + c) >>> 0
    hash[3] = (hash[3] + d) >>> 0
    hash[4] = (hash[4] + e) >>> 0
    hash[5] = (hash[5] + f) >>> 0
    hash[6] = (hash[6] + g) >>> 0
    hash[7] = (hash[7] + h) >>> 0
  }

  var result = ''
  for (var hashIndex = 0; hashIndex < hash.length; hashIndex++) {
    result += ('00000000' + hash[hashIndex].toString(16)).slice(-8)
  }
  return result
}

function afterlightSha256Ascii(text) {
  var value = String(text)
  var bytes = []
  for (var textIndex = 0; textIndex < value.length; textIndex++) {
    var code = value.codePointAt(textIndex)
    if (code > 0x7F) throw new Error('acquisition proof material is not ASCII')
    bytes.push(code)
  }
  return afterlightSha256Bytes(bytes)
}

function afterlightProofDigest(manifestSha256, nonce, canonical) {
  return afterlightSha256Ascii('AFTERLIGHT-ACQUISITION-PROOF\0'
    + manifestSha256 + '\0' + nonce + '\0' + canonical)
}

const AfterlightLong = Java.loadClass('java.lang.Long')
const AfterlightResourceLocation = Java.loadClass('net.minecraft.resources.ResourceLocation')
const AfterlightResourceKey = Java.loadClass('net.minecraft.resources.ResourceKey')
const AfterlightRegistries = Java.loadClass('net.minecraft.core.registries.Registries')
const AfterlightBuiltInRegistries = Java.loadClass('net.minecraft.core.registries.BuiltInRegistries')
const AfterlightTagKey = Java.loadClass('net.minecraft.tags.TagKey')
const AfterlightItemStack = Java.loadClass('net.minecraft.world.item.ItemStack')
const AfterlightJsonOps = Java.loadClass('com.mojang.serialization.JsonOps')
const AfterlightJsonParser = Java.loadClass('com.google.gson.JsonParser')
const AfterlightFluidUtil = Java.loadClass('net.neoforged.neoforge.fluids.FluidUtil')
const AfterlightFakePlayerFactory = Java.loadClass('net.neoforged.neoforge.common.util.FakePlayerFactory')
const AfterlightEntityType = Java.loadClass('net.minecraft.world.entity.EntityType')
const AfterlightInteractionHand = Java.loadClass('net.minecraft.world.InteractionHand')
const AfterlightServerQuestFile = Java.loadClass('dev.ftb.mods.ftbquests.quest.ServerQuestFile')
const AfterlightCheckmarkTask = Java.loadClass('dev.ftb.mods.ftbquests.quest.task.CheckmarkTask')
const AfterlightTranslationKey = Java.loadClass('dev.ftb.mods.ftbquests.quest.translation.TranslationKey')
const AfterlightCokeOvenRecipe = Java.loadClass('blusunrize.immersiveengineering.api.crafting.CokeOvenRecipe')
const AfterlightProcessingRecipe = Java.loadClass('com.simibubi.create.content.processing.recipe.ProcessingRecipe')
const AfterlightSequencedAssemblyRecipe = Java.loadClass('com.simibubi.create.content.processing.sequenced.SequencedAssemblyRecipe')
const AfterlightPressureChamberRecipe = Java.loadClass('me.desht.pneumaticcraft.api.crafting.recipe.PressureChamberRecipe')
const AfterlightExplosionCraftingRecipe = Java.loadClass('me.desht.pneumaticcraft.api.crafting.recipe.ExplosionCraftingRecipe')
const AfterlightHeatFrameCoolingRecipe = Java.loadClass('me.desht.pneumaticcraft.api.crafting.recipe.HeatFrameCoolingRecipe')
const AfterlightAssemblyRecipe = Java.loadClass('me.desht.pneumaticcraft.api.crafting.recipe.AssemblyRecipe')

ServerEvents.loaded(event => {
  const server = event.server
  const registries = server.registryAccess()
  const level = server.overworld()
  const bootNonce = '__AFTERLIGHT_BOOT_NONCE__'
  let okCount = 0
  let activeSpec = null

  function digestBytes(bytes) {
    return afterlightSha256Bytes(bytes)
  }

  function proof(spec) {
    return afterlightProofDigest(
      AFTERLIGHT_ACQUISITION_MANIFEST_SHA256,
      bootNonce,
      spec.canonical
    )
  }

  function fail(reason) {
    const error = new Error(reason)
    error.afterlightReason = reason
    throw error
  }

  function resource(value) {
    return AfterlightResourceLocation.parse(value)
  }

  function javaArray(value) {
    var result = []
    if ('length' in value) {
      for (var arrayIndex = 0; arrayIndex < value.length; arrayIndex++) {
        result.push(value[arrayIndex])
      }
      return result
    }
    var iterator = value.iterator()
    while (iterator.hasNext()) result.push(iterator.next())
    return result
  }

  function sortedStrings(value) {
    return javaArray(value).map(entry => String(entry)).sort()
  }

  function arraysEqual(actual, expected) {
    if (actual.length !== expected.length) return false
    for (let index = 0; index < actual.length; index++) {
      if (actual[index] !== expected[index]) return false
    }
    return true
  }

  function expectedStack(spec) {
    const context = registries.createSerializationContext(AfterlightJsonOps.INSTANCE)
    const parsed = AfterlightJsonParser.parseString(JSON.stringify(spec))
    return AfterlightItemStack.CODEC.parse(context, parsed).getOrThrow()
  }

  function stackItemId(stack) {
    return String(AfterlightBuiltInRegistries.ITEM.getKey(stack.getItem()))
  }

  function verifyStack(actual, declared, itemReason, countReason, componentsReason) {
    const expected = expectedStack(declared)
    if (stackItemId(actual) !== declared.id) fail(itemReason)
    if (actual.getCount() !== declared.count) fail(countReason)
    if (!AfterlightItemStack.isSameItemSameComponents(actual, expected)) fail(componentsReason)
  }

  function recipeHolder(id, missingReason) {
    const optional = server.getRecipeManager().byKey(resource(id))
    if (optional.isEmpty()) fail(missingReason)
    return optional.get()
  }

  function verifyRecipeIdentity(holder, spec, idReason, typeReason, serializerReason) {
    if (String(holder.id()) !== spec.id) fail(idReason)
    const recipe = holder.value()
    if (String(AfterlightBuiltInRegistries.RECIPE_TYPE.getKey(recipe.getType())) !== spec.recipe_type) fail(typeReason)
    if (String(AfterlightBuiltInRegistries.RECIPE_SERIALIZER.getKey(recipe.getSerializer())) !== spec.serializer) fail(serializerReason)
    return recipe
  }

  function resultItem(recipe) {
    return recipe['getResultItem(net.minecraft.core.HolderLookup$Provider)'](registries)
  }

  function verifyRecipeNode(node) {
    node.recipes.forEach(spec => {
      const holder = recipeHolder(spec.id, 'RECIPE_MISSING')
      const recipe = verifyRecipeIdentity(
        holder,
        spec,
        'RECIPE_ID_MISMATCH',
        'RECIPE_TYPE_MISMATCH',
        'RECIPE_SERIALIZER_MISMATCH'
      )
      verifyStack(
        resultItem(recipe),
        spec.output,
        'RECIPE_OUTPUT_ITEM_MISMATCH',
        'RECIPE_OUTPUT_COUNT_MISMATCH',
        'RECIPE_OUTPUT_COMPONENTS_MISMATCH'
      )
    })
  }

  function itemTagMembers(tagId) {
    const itemRegistry = registries.registryOrThrow(AfterlightRegistries.ITEM)
    const tag = AfterlightTagKey.create(AfterlightRegistries.ITEM, resource(tagId))
    const optional = itemRegistry.getTag(tag)
    if (optional.isEmpty()) return null
    return javaArray(optional.get()).map(holder => String(holder.unwrapKey().get().location())).sort()
  }

  function verifyProcessOutputs(actualValues, declared, role) {
    const actual = javaArray(actualValues)
    const reason = role === 'intermediate' ? 'PROCESS_INTERMEDIATE_MISMATCH' : 'PROCESS_FINAL_MISMATCH'
    if (actual.length !== declared.length) fail(reason)
    for (let index = 0; index < declared.length; index++) {
      const output = declared[index]
      const stack = actual[index]
      if (output.kind === 'item_tag') {
        const members = itemTagMembers(output.id)
        if (members === null || members.indexOf(stackItemId(stack)) < 0 || stack.getCount() !== output.count) fail(reason)
      } else {
        verifyStack(stack, output, reason, reason, reason)
      }
    }
  }

  function verifyProcessStep(spec) {
    const holder = recipeHolder(spec.id, 'PROCESS_STEP_MISSING')
    const recipe = verifyRecipeIdentity(
      holder,
      spec,
      'PROCESS_ATTRIBUTE_MISMATCH',
      'PROCESS_ATTRIBUTE_MISMATCH',
      'PROCESS_ATTRIBUTE_MISMATCH'
    )
    let outputs
    if (spec.extractor === 'result_item') {
      outputs = [resultItem(recipe)]
    } else if (spec.extractor === 'ie_coke') {
      if (!(recipe instanceof AfterlightCokeOvenRecipe)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      if (recipe.creosoteOutput !== spec.attributes.creosote_millibuckets) fail('PROCESS_ATTRIBUTE_MISMATCH')
      outputs = [resultItem(recipe)]
    } else if (spec.extractor === 'create_rollable_results') {
      if (!(recipe instanceof AfterlightProcessingRecipe)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      outputs = recipe.getRollableResultsAsItemStacks()
    } else if (spec.extractor === 'create_sequenced') {
      if (!(recipe instanceof AfterlightSequencedAssemblyRecipe)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      if (recipe.getLoops() !== spec.attributes.loops) fail('PROCESS_ATTRIBUTE_MISMATCH')
      verifyStack(recipe.getTransitionalItem(), spec.attributes.transitional_output, 'PROCESS_ATTRIBUTE_MISMATCH', 'PROCESS_ATTRIBUTE_MISMATCH', 'PROCESS_ATTRIBUTE_MISMATCH')
      outputs = [resultItem(recipe)]
    } else if (spec.extractor === 'pnc_outputs') {
      var pressureRecipe = recipe instanceof AfterlightPressureChamberRecipe
      var explosionRecipe = recipe instanceof AfterlightExplosionCraftingRecipe
      if (!pressureRecipe && !explosionRecipe) fail('PROCESS_ATTRIBUTE_MISMATCH')
      outputs = recipe.getOutputs()
      if (Object.prototype.hasOwnProperty.call(spec.attributes, 'loss_rate') && (!explosionRecipe || recipe.getLossRate() !== spec.attributes.loss_rate)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      if (Object.prototype.hasOwnProperty.call(spec.attributes, 'pressure') && (!pressureRecipe || Math.abs(recipe.getPressure() - spec.attributes.pressure) > 0.000001)) fail('PROCESS_ATTRIBUTE_MISMATCH')
    } else if (spec.extractor === 'pnc_heat_frame') {
      if (!(recipe instanceof AfterlightHeatFrameCoolingRecipe)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      if (recipe.getThresholdTemperature() !== spec.attributes.threshold_temperature) fail('PROCESS_ATTRIBUTE_MISMATCH')
      outputs = [recipe.getOutput()]
    } else if (spec.extractor === 'pnc_assembly') {
      if (!(recipe instanceof AfterlightAssemblyRecipe)) fail('PROCESS_ATTRIBUTE_MISMATCH')
      if (String(recipe.getProgramType().name()) !== spec.attributes.program) fail('PROCESS_ATTRIBUTE_MISMATCH')
      outputs = [recipe.getOutput()]
    } else {
      fail('METHOD_UNSUPPORTED')
    }
    verifyProcessOutputs(outputs, spec.outputs, spec.role)
  }

  function verifyFluidContainer(check, node) {
    const source = node.steps[check.source_step]
    if (source.attributes.creosote_millibuckets * check.cycles !== check.millibuckets) fail('PROCESS_NATIVE_MISMATCH')
    const container = expectedStack(check.output)
    const optional = AfterlightFluidUtil.getFluidContained(container)
    if (optional.isEmpty()) fail('PROCESS_NATIVE_MISMATCH')
    const fluid = optional.get()
    if (String(AfterlightBuiltInRegistries.FLUID.getKey(fluid.getFluid())) !== check.fluid || fluid.getAmount() !== check.millibuckets) fail('PROCESS_NATIVE_MISMATCH')
  }

  function verifyEntityInteraction(check) {
    const input = expectedStack(check.input)
    const output = expectedStack(check.output)
    const inputItem = input.getItem()
    const outputItem = output.getItem()
    var expectedItemClass = Java.loadClass(check.item_class)
    if (!(inputItem instanceof expectedItemClass) || !(outputItem instanceof expectedItemClass)) fail('PROCESS_NATIVE_MISMATCH')
    if (inputItem.hasCapturedBlaze() || !outputItem.hasCapturedBlaze()) fail('PROCESS_NATIVE_MISMATCH')
    const player = AfterlightFakePlayerFactory.getMinecraft(level)
    const prior = player.getItemInHand(AfterlightInteractionHand.MAIN_HAND).copy()
    let blaze = null
    try {
      blaze = AfterlightEntityType.BLAZE.create(level)
      if (blaze === null) fail('PROCESS_NATIVE_MISMATCH')
      player.setItemInHand(AfterlightInteractionHand.MAIN_HAND, input.copy())
      inputItem.interactLivingEntity(
        player.getItemInHand(AfterlightInteractionHand.MAIN_HAND),
        player,
        blaze,
        AfterlightInteractionHand.MAIN_HAND
      )
      const hand = player.getItemInHand(AfterlightInteractionHand.MAIN_HAND)
      verifyStack(hand, check.output, 'PROCESS_NATIVE_MISMATCH', 'PROCESS_NATIVE_MISMATCH', 'PROCESS_NATIVE_MISMATCH')
      if (!blaze.isRemoved()) fail('PROCESS_NATIVE_MISMATCH')
    } finally {
      player.setItemInHand(AfterlightInteractionHand.MAIN_HAND, prior)
      if (blaze !== null && !blaze.isRemoved()) blaze.discard()
    }
  }

  function verifyProcessNode(node) {
    node.steps.forEach(verifyProcessStep)
    node.native_checks.forEach(check => {
      if (check.kind === 'fluid_container') verifyFluidContainer(check, node)
      else if (check.kind === 'entity_interaction') verifyEntityInteraction(check)
      else fail('METHOD_UNSUPPORTED')
    })
  }

  function resourceDigest(location, missingReason, mismatchReason, expected) {
    const optional = server.getResourceManager().getResource(resource(location))
    if (optional.isEmpty()) fail(missingReason)
    const stream = optional.get().open()
    let actual
    try {
      actual = digestBytes(stream.readAllBytes())
    } finally {
      stream.close()
    }
    if (actual !== expected) fail(mismatchReason)
  }

  function verifyAdvancementNode(spec) {
    const holder = server.getAdvancements().get(resource(spec.id))
    if (holder === null) fail('ADVANCEMENT_MISSING')
    if (String(holder.id()) !== spec.id) fail('ADVANCEMENT_MISSING')
    const advancement = holder.value()
    const criteria = advancement.criteria()
    const actualNames = sortedStrings(criteria.keySet())
    const expectedNames = spec.criteria.map(entry => entry.name).sort()
    if (!arraysEqual(actualNames, expectedNames)) fail('ADVANCEMENT_CRITERIA_MISMATCH')
    const actualRequirements = javaArray(advancement.requirements().requirements()).map(requirement => javaArray(requirement).map(entry => String(entry)).join(','))
    const expectedRequirements = spec.requirements.map(requirement => requirement.join(','))
    if (!arraysEqual(actualRequirements, expectedRequirements)) fail('ADVANCEMENT_REQUIREMENTS_MISMATCH')
    spec.criteria.forEach(declared => {
      const criterion = criteria.get(declared.name)
      if (criterion === null) fail('ADVANCEMENT_CRITERIA_MISMATCH')
      if (String(AfterlightBuiltInRegistries.TRIGGER_TYPES.getKey(criterion.trigger())) !== declared.trigger) fail('ADVANCEMENT_TRIGGER_MISMATCH')
      const instance = criterion.triggerInstance()
      var expectedInstanceClass = Java.loadClass(declared.instance_class)
      if (!(instance instanceof expectedInstanceClass)) fail('ADVANCEMENT_INSTANCE_MISMATCH')
      Object.keys(declared.fields).forEach(field => {
        let actual
        if (field === 'items') actual = instance.items().size()
        else actual = String(instance[field]())
        if (actual !== declared.fields[field]) fail('ADVANCEMENT_FIELD_MISMATCH')
      })
    })
    resourceDigest(spec.resource.location, 'ADVANCEMENT_RESOURCE_MISMATCH', 'ADVANCEMENT_RESOURCE_MISMATCH', spec.resource.sha256)
  }

  function registryTagMembers(registryKey, tagId) {
    const registry = registries.registryOrThrow(registryKey)
    const optional = registry.getTag(AfterlightTagKey.create(registryKey, resource(tagId)))
    if (optional.isEmpty()) return null
    return javaArray(optional.get()).map(holder => String(holder.unwrapKey().get().location())).sort()
  }

  function verifyWorldgenNode(spec) {
    spec.registry_keys.forEach(entry => {
      let value
      let registry
      if (entry.registry === 'minecraft:worldgen/structure') registry = registries.registryOrThrow(AfterlightRegistries.STRUCTURE)
      else if (entry.registry === 'minecraft:worldgen/structure_set') registry = registries.registryOrThrow(AfterlightRegistries.STRUCTURE_SET)
      else if (entry.registry === 'minecraft:worldgen/structure_type') registry = AfterlightBuiltInRegistries.STRUCTURE_TYPE
      else fail('METHOD_UNSUPPORTED')
      value = registry.get(resource(entry.key))
      if (value === null || String(registry.getKey(value)) !== entry.key) fail('WORLDGEN_REGISTRY_MISSING')
    })
    spec.resources.forEach(entry => resourceDigest(entry.location, 'WORLDGEN_RESOURCE_MISSING', 'WORLDGEN_RESOURCE_MISMATCH', entry.sha256))
    const itemMembers = itemTagMembers(spec.item_tag.id)
    if (itemMembers === null) fail('WORLDGEN_TAG_MISSING')
    const expectedMembers = spec.item_tag.members.map(member => member.id).sort()
    if (!arraysEqual(itemMembers, expectedMembers)) fail('WORLDGEN_TAG_MISMATCH')
    const meteoriteBiomes = registryTagMembers(AfterlightRegistries.BIOME, spec.biome_tag.id)
    const overworldBiomes = registryTagMembers(AfterlightRegistries.BIOME, spec.biome_tag.equals)
    if (meteoriteBiomes === null || overworldBiomes === null) fail('WORLDGEN_TAG_MISSING')
    if (meteoriteBiomes.length < spec.biome_tag.minimum_members || !arraysEqual(meteoriteBiomes, overworldBiomes)) fail('WORLDGEN_BIOME_TAG_MISMATCH')
    const lootKey = AfterlightResourceKey.create(AfterlightRegistries.LOOT_TABLE, resource(spec.native_target.loot_table_id))
    if (!server.reloadableRegistries().getKeys(AfterlightRegistries.LOOT_TABLE).contains(lootKey.location())) fail('LOOT_TABLE_MISSING')
    server.reloadableRegistries().getLootTable(lootKey)
    const blockId = resource(spec.native_target.block_id)
    const block = AfterlightBuiltInRegistries.BLOCK.get(blockId)
    if (block === null || String(AfterlightBuiltInRegistries.BLOCK.getKey(block)) !== spec.native_target.block_id) fail('NATIVE_BLOCK_MISSING')
  }

  function verifyManualNode(node) {
    const optional = AfterlightServerQuestFile.getInstance()
    if (optional.isEmpty()) fail('MANUAL_TASK_MISSING')
    const questFile = optional.get()
    const taskId = node.task_ids[0]
    const task = questFile.getTask(AfterlightLong.parseUnsignedLong(taskId, 16))
    if (task === null) fail('MANUAL_TASK_MISSING')
    if (!(task instanceof AfterlightCheckmarkTask)) fail('MANUAL_TASK_CLASS_MISMATCH')
    if (task.getQuest().getCodeString() !== node.quest_id) fail('MANUAL_PARENT_MISMATCH')
    const expectedKey = 'task.' + task.getCodeString() + '.title'
    if (node.manual_check.localization_key !== expectedKey) fail('MANUAL_KEY_MISMATCH')
    const translation = questFile.getTranslationManager().getStringTranslation(task, node.manual_check.locale, AfterlightTranslationKey.TITLE)
    if (translation.isEmpty()) fail('MANUAL_TRANSLATION_MISSING')
    const translated = String(translation.get()).trim()
    if (translated.length === 0) fail('MANUAL_TRANSLATION_EMPTY')
    if (translated === node.manual_check.localization_key) fail('MANUAL_TRANSLATION_UNRESOLVED')
    if (String(task.getTitle().getString()).trim().length === 0) fail('MANUAL_TRANSLATION_EMPTY')
  }

  function verifyNode(node) {
    if (node.method === 'recipe') verifyRecipeNode(node)
    else if (node.method === 'process') verifyProcessNode(node)
    else if (node.method === 'advancement') verifyAdvancementNode(node.advancement)
    else if (node.method === 'worldgen') verifyWorldgenNode(node.worldgen)
    else if (node.method === 'manual_check') verifyManualNode(node)
    else fail('METHOD_UNSUPPORTED')
  }

  setTimeout(() => {
    console.info(`AFTERLIGHT_ACQUISITION_AUDIT_BEGIN schema=1 nonce=${bootNonce} manifest=${AFTERLIGHT_ACQUISITION_MANIFEST_SHA256}`)
    try {
      for (let index = 0; index < AFTERLIGHT_ACQUISITION_SPECS.length; index++) {
        activeSpec = AFTERLIGHT_ACQUISITION_SPECS[index]
        try {
          verifyNode(activeSpec.data)
          console.info(`AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=${activeSpec.data.quest_id} task=${activeSpec.data.task_ids.join(',')} method=${activeSpec.data.method} status=OK proof=${proof(activeSpec)}`)
          okCount++
        } catch (error) {
          var nodeReason = error.afterlightReason && AFTERLIGHT_ACQUISITION_FAILURE_REASONS.indexOf(String(error.afterlightReason)) >= 0
            ? String(error.afterlightReason) : 'RUNTIME_EXCEPTION'
          console.info(`AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=${activeSpec.data.quest_id} task=${activeSpec.data.task_ids.join(',')} method=${activeSpec.data.method} status=FAIL reason=${nodeReason} proof=${proof(activeSpec)}`)
          console.info(`AFTERLIGHT_ACQUISITION_AUDIT_FAIL count=${okCount} nonce=${bootNonce} manifest=${AFTERLIGHT_ACQUISITION_MANIFEST_SHA256} reason=${nodeReason}`)
          console.error(`AFTERLIGHT acquisition audit detail for ${activeSpec.data.quest_id}: ${String(error)}`)
          return
        }
      }
      console.info(`AFTERLIGHT_ACQUISITION_AUDIT_OK count=${okCount} nonce=${bootNonce} manifest=${AFTERLIGHT_ACQUISITION_MANIFEST_SHA256}`)
    } catch (error) {
      var outerReason = 'RUNTIME_EXCEPTION'
      if (activeSpec !== null) {
        console.info(`AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=${activeSpec.data.quest_id} task=${activeSpec.data.task_ids.join(',')} method=${activeSpec.data.method} status=FAIL reason=${outerReason} proof=${proof(activeSpec)}`)
      }
      console.info(`AFTERLIGHT_ACQUISITION_AUDIT_FAIL count=${okCount} nonce=${bootNonce} manifest=${AFTERLIGHT_ACQUISITION_MANIFEST_SHA256} reason=${outerReason}`)
      console.error(`AFTERLIGHT acquisition audit outer failure: ${String(error)}`)
    }
  }, Duration.ofMillis(1))
})
"""


def render_manual_acquisition_audit(manifest: AcquisitionManifest) -> str:
    manifest_sha256 = manifest_digest(manifest)
    canonical_nodes = [canonical_bytes(_node_to_data(node)).decode("ascii") for node in manifest.nodes]
    if any("'" in node or "\\" in node for node in canonical_nodes):
        raise ValueError("acquisition canonical node is not safe for ASCII JS embedding")
    rendered_nodes = "\n".join(
        f"  '{node}'{',' if index + 1 < len(canonical_nodes) else ''}"
        for index, node in enumerate(canonical_nodes)
    )
    failure_reasons = json.dumps(sorted(_FAILURE_REASONS), ensure_ascii=True)
    source = (
        "// Generated by tools/build-quests.py. Do not edit by hand.\n"
        f"const AFTERLIGHT_ACQUISITION_MANIFEST_SHA256 = '{manifest_sha256}'\n"
        "const AFTERLIGHT_ACQUISITION_SPECS = [\n"
        + rendered_nodes
        + "\n].map(canonical => ({ canonical: canonical, data: JSON.parse(canonical) }))\n"
        f"const AFTERLIGHT_ACQUISITION_FAILURE_REASONS = {failure_reasons}\n"
        + _AUDIT_RUNTIME_SOURCE.lstrip("\n")
    )
    source.encode("ascii")
    if source.count(NONCE_PLACEHOLDER) != 1:
        raise ValueError("acquisition audit nonce placeholder count changed")
    return source


_HAZMAT_TASK_ITEMS = {
    "495A10C44F72378A": "mekanism:hazmat_mask",
    "34E4C99926170FB3": "mekanism:hazmat_gown",
    "6BB96C5647B7454A": "mekanism:hazmat_pants",
    "26554BB1116B4315": "mekanism:hazmat_boots",
}


def _expected_task_stacks(node: AcquisitionNode) -> dict[str, StackProof]:
    proof = node.proof
    if isinstance(proof, RecipeNodeProof):
        return {recipe.task_id: recipe.output for recipe in proof.recipes}
    if isinstance(proof, ProcessNodeProof):
        expected = {
            output.task_id: StackProof(output.id, 1, output.components)
            for step in proof.steps
            for output in step.outputs
            if isinstance(output, StackOutputProof) and output.task_id is not None
        }
        expected.update(
            {check.task_id: StackProof(check.output.id, 1, check.output.components) for check in proof.native_checks}
        )
        return expected
    if isinstance(proof, WorldgenProof):
        return {
            member.task_id: StackProof(member.id, 1, member.components)
            for member in proof.item_tag.members
        }
    if isinstance(proof, AdvancementProof) and node.quest_id == "4EEAB6F41DB426E7":
        return {
            task_id: StackProof(item_id, 1, {})
            for task_id, item_id in _HAZMAT_TASK_ITEMS.items()
        }
    return {}


def _normalized_count(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    wrapped = getattr(value, "value", None)
    if isinstance(wrapped, int) and not isinstance(wrapped, bool):
        return wrapped
    if isinstance(value, str):
        match = re.fullmatch(r"(-?\d+)(?:L)?", value)
        if match is not None:
            return int(match.group(1))
    return None


def _task_stack_errors(
    node: AcquisitionNode,
    task_id: str,
    task_type: object,
    data: Mapping[str, object],
    expected: StackProof,
) -> list[str]:
    errors: list[str] = []
    prefix = f"acquisition task {task_id} for {node.quest_slug}"
    if task_type != "item":
        errors.append(f"{prefix} task type mismatch: expected item, got {task_type!r}")
        return errors
    stack = data.get("item")
    if not isinstance(stack, Mapping):
        errors.append(f"{prefix} task stack is missing")
        return errors
    actual_id = stack.get("id")
    if actual_id != expected.id:
        errors.append(
            f"{prefix} task stack ID mismatch: expected {expected.id}, got {actual_id!r}"
        )
    actual_components = stack.get("components", {})
    if not isinstance(actual_components, Mapping) or dict(actual_components) != dict(
        expected.components
    ):
        errors.append(
            f"{prefix} task components mismatch: expected {dict(expected.components)!r}, "
            f"got {actual_components!r}"
        )
    if _normalized_count(stack.get("count")) != 1 or _normalized_count(
        data.get("count")
    ) != 1:
        errors.append(f"{prefix} task count mismatch: expected one non-consuming item")
    if data.get("consume_items") is not False:
        errors.append(f"{prefix} task consume_items must be false")
    match_components = data.get("match_components")
    if expected.components:
        if match_components != "fuzzy":
            errors.append(
                f"{prefix} match_components mismatch: expected fuzzy, "
                f"got {match_components!r}"
            )
    elif "match_components" in data:
        errors.append(
            f"{prefix} match_components mismatch: expected absent, "
            f"got {match_components!r}"
        )
    return errors


def _validate_task_contract(
    node: AcquisitionNode,
    task: object,
    *,
    parsed: bool,
) -> list[str]:
    if parsed:
        if not isinstance(task, Mapping):
            return [f"acquisition task for {node.quest_slug} is malformed"]
        task_id = task.get("id")
        task_type = task.get("type")
        data: Mapping[str, object] = task
        title: object = None
    else:
        task_id = getattr(task, "id", None)
        task_type = getattr(task, "task_type", None)
        data = getattr(task, "data", {})
        title = getattr(task, "title", None)
    if not isinstance(task_id, str):
        return [f"acquisition task for {node.quest_slug} has malformed task ID"]
    expected_stacks = _expected_task_stacks(node)
    if task_id in expected_stacks:
        return _task_stack_errors(
            node,
            task_id,
            task_type,
            data,
            expected_stacks[task_id],
        )
    if isinstance(node.proof, AdvancementProof):
        if task_type != "advancement":
            return [
                f"acquisition task {task_id} for {node.quest_slug} task type mismatch: "
                f"expected advancement, got {task_type!r}"
            ]
        if data.get("advancement") != node.proof.id:
            return [
                f"acquisition task {task_id} for {node.quest_slug} advancement mismatch: "
                f"expected {node.proof.id}, got {data.get('advancement')!r}"
            ]
        return []
    if isinstance(node.proof, ManualCheckProof):
        errors = []
        if task_type != "checkmark":
            errors.append(
                f"acquisition task {task_id} for {node.quest_slug} task type mismatch: "
                f"expected checkmark, got {task_type!r}"
            )
        if not parsed and (not isinstance(title, str) or not title.strip()):
            errors.append(
                f"acquisition task {task_id} for {node.quest_slug} manual action is empty"
            )
        return errors
    return [f"acquisition task {task_id} for {node.quest_slug} has no proof binding"]


def _validate_catalog_agreement(
    manifest: AcquisitionManifest,
    catalog: object,
) -> list[str]:
    errors: list[str] = []
    chapters = tuple(catalog) if not isinstance(catalog, (str, bytes, Path)) else ()
    quests_by_slug: dict[str, object] = {}
    for chapter in chapters:
        for quest in getattr(chapter, "quests", ()):
            slug = getattr(quest, "slug", None)
            if isinstance(slug, str) and slug.startswith("manuals/"):
                if slug in quests_by_slug:
                    errors.append(f"duplicate manual quest slug {slug}")
                quests_by_slug[slug] = quest
    expected_slugs = {node.quest_slug for node in manifest.nodes}
    missing = sorted(expected_slugs - set(quests_by_slug))
    extra = sorted(set(quests_by_slug) - expected_slugs)
    if missing:
        errors.append(f"acquisition fixture missing catalog quest {missing[0]}")
    if extra:
        errors.append(f"acquisition fixture has no record for manual quest {extra[0]}")
    try:
        from .builder import stable_id
    except ImportError:
        stable_id = None
    for node in manifest.nodes:
        quest = quests_by_slug.get(node.quest_slug)
        if quest is None:
            continue
        quest_id = getattr(quest, "id", None)
        if quest_id != node.quest_id:
            errors.append(
                f"acquisition quest ID mismatch for {node.quest_slug}: "
                f"expected {node.quest_id}, got {quest_id!r}"
            )
        explicit_id = getattr(quest, "explicit_id", None)
        approved_explicit_id = _APPROVED_EXPLICIT_QUEST_IDS.get(node.quest_slug)
        if explicit_id != approved_explicit_id:
            errors.append(
                f"acquisition quest explicit ID ownership mismatch for "
                f"{node.quest_slug}: expected {approved_explicit_id!r}, "
                f"got {explicit_id!r}"
            )
        if explicit_id is None and stable_id is not None:
            stable = stable_id("quest", node.quest_slug)
            if quest_id != stable:
                errors.append(
                    f"acquisition quest ID is not stable for {node.quest_slug}: "
                    f"expected {stable}, got {quest_id!r}"
                )
        tasks = tuple(getattr(quest, "tasks", ()))
        task_ids = tuple(getattr(task, "id", None) for task in tasks)
        if task_ids != node.task_ids:
            errors.append(
                f"acquisition ordered task IDs mismatch for {node.quest_slug}: "
                f"expected {node.task_ids}, got {task_ids}"
            )
        for task_index, task in enumerate(tasks):
            if task_index >= len(node.task_ids):
                break
            task_slug = getattr(task, "slug", None)
            task_explicit_id = getattr(task, "explicit_id", None)
            approved_task_explicit_id = (
                _APPROVED_EXPLICIT_TASK_IDS.get(task_slug)
                if isinstance(task_slug, str)
                else None
            )
            if task_explicit_id != approved_task_explicit_id:
                errors.append(
                    f"acquisition task explicit ID ownership mismatch for "
                    f"{task_slug!r}: expected {approved_task_explicit_id!r}, "
                    f"got {task_explicit_id!r}"
                )
            if task_explicit_id is None and stable_id is not None and isinstance(
                task_slug, str
            ):
                expected_id = stable_id("task", task_slug)
                if getattr(task, "id", None) != expected_id:
                    errors.append(
                        f"acquisition task ID is not stable for {task_slug}: "
                        f"expected {expected_id}, got {getattr(task, 'id', None)!r}"
                    )
            errors.extend(_validate_task_contract(node, task, parsed=False))
    return errors


def _validate_parsed_agreement(
    manifest: AcquisitionManifest,
    quest_root: Path,
) -> list[str]:
    errors: list[str] = []
    try:
        from .builder import SnbtParseError, _parse_snbt
    except ImportError as error:
        return [f"acquisition parsed-SNBT support unavailable: {error}"]
    quest_by_id: dict[str, tuple[Mapping[str, object], Path]] = {}
    owner_quests: dict[Path, set[str]] = {}
    try:
        for chapter_path in sorted((quest_root / "chapters").glob("*.snbt")):
            parsed = _parse_snbt(chapter_path.read_text(encoding="utf-8"))
            if not isinstance(parsed, Mapping) or not isinstance(
                parsed.get("quests"), list
            ):
                continue
            chapter_ids: set[str] = set()
            for quest in parsed["quests"]:
                if not isinstance(quest, Mapping) or not isinstance(
                    quest.get("id"), str
                ):
                    continue
                quest_id = str(quest["id"])
                chapter_ids.add(quest_id)
                if quest_id in quest_by_id:
                    errors.append(f"duplicate parsed quest ID {quest_id}")
                quest_by_id[quest_id] = (quest, chapter_path)
            owner_quests[chapter_path] = chapter_ids
    except (OSError, SnbtParseError) as error:
        return [f"acquisition parsed-SNBT read failed: {error}"]
    fixture_ids = {node.quest_id for node in manifest.nodes}
    owner_paths = {
        quest_by_id[node.quest_id][1]
        for node in manifest.nodes
        if node.quest_id in quest_by_id
    }
    parsed_manual_ids = {
        quest_id for owner in owner_paths for quest_id in owner_quests[owner]
    }
    missing = sorted(fixture_ids - set(quest_by_id))
    if missing:
        errors.append(f"acquisition parsed quest missing {missing[0]}")
    extra = sorted(parsed_manual_ids - fixture_ids)
    if extra:
        errors.append(f"acquisition parsed manual quest has no record {extra[0]}")
    language: Mapping[str, object] = {}
    try:
        parsed_language = _parse_snbt(
            (quest_root / "lang" / "en_us.snbt").read_text(encoding="utf-8")
        )
        if isinstance(parsed_language, Mapping):
            language = parsed_language
    except (OSError, SnbtParseError) as error:
        errors.append(f"acquisition localization read failed: {error}")
    for node in manifest.nodes:
        found = quest_by_id.get(node.quest_id)
        if found is None:
            continue
        quest = found[0]
        tasks = quest.get("tasks")
        if not isinstance(tasks, list):
            errors.append(f"acquisition parsed tasks malformed for {node.quest_slug}")
            continue
        task_ids = tuple(
            task.get("id") if isinstance(task, Mapping) else None for task in tasks
        )
        if task_ids != node.task_ids:
            errors.append(
                f"acquisition parsed ordered task IDs mismatch for {node.quest_slug}: "
                f"expected {node.task_ids}, got {task_ids}"
            )
        for task in tasks:
            errors.extend(_validate_task_contract(node, task, parsed=True))
        if isinstance(node.proof, ManualCheckProof):
            translation = language.get(node.proof.localization_key)
            if not isinstance(translation, str) or not translation.strip():
                errors.append(
                    f"acquisition manual action localization missing or empty: "
                    f"{node.proof.localization_key}"
                )
    return errors


def validate_fixture_to_quests(
    manifest: AcquisitionManifest,
    corpus: object,
) -> list[str]:
    if isinstance(corpus, Path):
        return _validate_parsed_agreement(manifest, corpus)
    return _validate_catalog_agreement(manifest, corpus)


_FAILURE_REASONS = frozenset(
    {
        "METHOD_UNSUPPORTED",
        "RUNTIME_EXCEPTION",
        "RECIPE_MISSING",
        "RECIPE_ID_MISMATCH",
        "RECIPE_TYPE_MISMATCH",
        "RECIPE_SERIALIZER_MISMATCH",
        "RECIPE_OUTPUT_ITEM_MISMATCH",
        "RECIPE_OUTPUT_COUNT_MISMATCH",
        "RECIPE_OUTPUT_COMPONENTS_MISMATCH",
        "PROCESS_STEP_MISSING",
        "PROCESS_INTERMEDIATE_MISMATCH",
        "PROCESS_FINAL_MISMATCH",
        "PROCESS_ATTRIBUTE_MISMATCH",
        "PROCESS_NATIVE_MISMATCH",
        "ADVANCEMENT_MISSING",
        "ADVANCEMENT_CRITERIA_MISMATCH",
        "ADVANCEMENT_REQUIREMENTS_MISMATCH",
        "ADVANCEMENT_TRIGGER_MISMATCH",
        "ADVANCEMENT_INSTANCE_MISMATCH",
        "ADVANCEMENT_FIELD_MISMATCH",
        "ADVANCEMENT_RESOURCE_MISMATCH",
        "WORLDGEN_REGISTRY_MISSING",
        "WORLDGEN_RESOURCE_MISSING",
        "WORLDGEN_RESOURCE_MISMATCH",
        "WORLDGEN_TAG_MISSING",
        "WORLDGEN_TAG_MISMATCH",
        "WORLDGEN_BIOME_TAG_MISMATCH",
        "LOOT_TABLE_MISSING",
        "NATIVE_BLOCK_MISSING",
        "MANUAL_TASK_MISSING",
        "MANUAL_TASK_CLASS_MISMATCH",
        "MANUAL_PARENT_MISMATCH",
        "MANUAL_KEY_MISMATCH",
        "MANUAL_TRANSLATION_MISSING",
        "MANUAL_TRANSLATION_EMPTY",
        "MANUAL_TRANSLATION_UNRESOLVED",
    }
)
_BEGIN_PATTERN = re.compile(
    r"^AFTERLIGHT_ACQUISITION_AUDIT_BEGIN schema=(?P<schema>\d+) "
    r"nonce=(?P<nonce>[A-Za-z0-9._-]+) manifest=(?P<manifest>[0-9a-f]{64})$"
)
_NODE_OK_PATTERN = re.compile(
    r"^AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=(?P<quest>[0-7][0-9A-F]{15}) "
    r"task=(?P<tasks>[0-7][0-9A-F]{15}(?:,[0-7][0-9A-F]{15})*) "
    r"method=(?P<method>[a-z_]+) status=OK proof=(?P<proof>[0-9a-f]{64})$"
)
_NODE_FAIL_PATTERN = re.compile(
    r"^AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=(?P<quest>[0-7][0-9A-F]{15}) "
    r"task=(?P<tasks>[0-7][0-9A-F]{15}(?:,[0-7][0-9A-F]{15})*) "
    r"method=(?P<method>[a-z_]+) status=FAIL reason=(?P<reason>[A-Z_]+) "
    r"proof=(?P<proof>[0-9a-f]{64})$"
)
_TERMINAL_OK_PATTERN = re.compile(
    r"^AFTERLIGHT_ACQUISITION_AUDIT_OK count=(?P<count>\d+) "
    r"nonce=(?P<nonce>[A-Za-z0-9._-]+) manifest=(?P<manifest>[0-9a-f]{64})$"
)
_TERMINAL_FAIL_PATTERN = re.compile(
    r"^AFTERLIGHT_ACQUISITION_AUDIT_FAIL count=(?P<count>\d+) "
    r"nonce=(?P<nonce>[A-Za-z0-9._-]+) manifest=(?P<manifest>[0-9a-f]{64}) "
    r"reason=(?P<reason>[A-Z_]+)$"
)
_MARKER_PREFIX = "AFTERLIGHT_ACQUISITION_AUDIT_"


def _append_once(errors: list[str], error: str) -> None:
    if error not in errors:
        errors.append(error)


def _audit_markers(text: str, errors: list[str]) -> list[tuple[int, str, re.Match[str]]]:
    markers: list[tuple[int, str, re.Match[str]]] = []
    patterns = (
        ("begin", _BEGIN_PATTERN),
        ("node_ok", _NODE_OK_PATTERN),
        ("node_fail", _NODE_FAIL_PATTERN),
        ("terminal_ok", _TERMINAL_OK_PATTERN),
        ("terminal_fail", _TERMINAL_FAIL_PATTERN),
    )
    for line_index, line in enumerate(text.splitlines()):
        if _MARKER_PREFIX not in line:
            continue
        marker = line[line.index(_MARKER_PREFIX) :]
        matches = [(kind, pattern.fullmatch(marker)) for kind, pattern in patterns]
        matched = [(kind, match) for kind, match in matches if match is not None]
        if len(matched) != 1:
            _append_once(errors, "acquisition audit malformed marker")
            continue
        kind, match = matched[0]
        markers.append((line_index, kind, match))
    return markers


def _validate_acquisition_log_text(
    manifest: AcquisitionManifest,
    nonce: str,
    text: str,
) -> list[str]:
    errors: list[str] = []
    manifest_sha256 = manifest_digest(manifest)
    markers = _audit_markers(text, errors)
    begins = [marker for marker in markers if marker[1] == "begin"]
    terminals = [marker for marker in markers if marker[1].startswith("terminal_")]
    nodes = [marker for marker in markers if marker[1].startswith("node_")]
    if not begins:
        _append_once(errors, "acquisition audit missing begin")
    elif len(begins) > 1:
        _append_once(errors, "acquisition audit duplicate begin")
    if not terminals:
        _append_once(errors, "acquisition audit missing terminal")
    elif len(terminals) > 1:
        _append_once(errors, "acquisition audit duplicate terminal")
    for _, _, match in begins + terminals:
        groups = match.groupdict()
        marker_nonce = groups.get("nonce")
        marker_manifest = groups.get("manifest")
        if marker_nonce is not None and marker_nonce != nonce:
            _append_once(errors, "acquisition audit stale nonce")
        if marker_manifest is not None and marker_manifest != manifest_sha256:
            _append_once(errors, "acquisition audit stale manifest")
    if begins and terminals:
        begin_index = begins[0][0]
        terminal_index = terminals[-1][0]
        if any(
            marker_index < begin_index or marker_index > terminal_index
            for marker_index, _, _ in markers
        ):
            _append_once(errors, "acquisition audit malformed marker")

    expected_by_id = {node.quest_id: node for node in manifest.nodes}
    seen: dict[str, int] = {}
    observed_order: list[str] = []
    for _, kind, match in nodes:
        groups = match.groupdict()
        quest_id = groups["quest"]
        observed_order.append(quest_id)
        seen[quest_id] = seen.get(quest_id, 0) + 1
        node = expected_by_id.get(quest_id)
        if node is None:
            _append_once(errors, f"acquisition audit extra node {quest_id}")
            continue
        if seen[quest_id] > 1:
            _append_once(errors, f"acquisition audit duplicate node {quest_id}")
        if groups["tasks"] != ",".join(node.task_ids):
            _append_once(errors, f"acquisition audit wrong task list {quest_id}")
        if groups["method"] != node.method:
            _append_once(errors, f"acquisition audit wrong method {quest_id}")
        expected_proof = proof_digest(node, manifest_sha256, nonce)
        if groups["proof"] != expected_proof:
            _append_once(errors, f"acquisition audit wrong proof {quest_id}")
        if kind == "node_fail":
            reason = groups["reason"]
            if reason not in _FAILURE_REASONS:
                _append_once(errors, "acquisition audit malformed marker")
            _append_once(
                errors,
                f"acquisition audit failure {quest_id} {reason}",
            )
    for node in manifest.nodes:
        if seen.get(node.quest_id, 0) == 0:
            _append_once(errors, f"acquisition audit missing node {node.quest_id}")
    expected_order = [node.quest_id for node in manifest.nodes]
    if (
        observed_order != expected_order
        and not any(count != 1 for count in seen.values())
        and set(observed_order) == set(expected_order)
    ):
        _append_once(errors, "acquisition audit malformed marker")

    if terminals:
        _, kind, terminal = terminals[-1]
        groups = terminal.groupdict()
        if int(groups["count"]) != len(manifest.nodes):
            _append_once(errors, "acquisition audit wrong terminal count")
        if kind == "terminal_fail":
            reason = groups["reason"]
            if reason not in _FAILURE_REASONS:
                _append_once(errors, "acquisition audit malformed marker")
            if not any(error.startswith("acquisition audit failure ") for error in errors):
                _append_once(
                    errors,
                    f"acquisition audit failure terminal {reason}",
                )
    return errors


def validate_acquisition_audit_logs(
    manifest: AcquisitionManifest,
    nonce: str,
    log_paths: tuple[Path, Path, Path],
) -> list[str]:
    if _NONCE.fullmatch(nonce) is None:
        return ["acquisition audit stale nonce"]
    if len(log_paths) != 3:
        return ["acquisition audit missing begin"]
    errors: list[str] = []
    for path in log_paths:
        try:
            text = path.read_bytes().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            _append_once(errors, "acquisition audit missing begin")
            continue
        for error in _validate_acquisition_log_text(manifest, nonce, text):
            _append_once(errors, error)
    return errors
