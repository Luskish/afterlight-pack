#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import stat
import struct
import sys
import tomllib
import zipfile
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable, Sequence
from urllib.parse import quote

try:
    from afterlight_quests.builder import (
        _SnbtPathScanner,
        _parse_snbt,
        _quest_item_ids,
        _render_quest_item_audit,
        quest_item_audit_digest,
        validate_quest_item_audit_logs,
    )
    from afterlight_quests.acquisition import (
        ACQUISITION_AUDIT_RELATIVE,
        FIXTURE_RELATIVE,
        load_manifest as load_acquisition_manifest,
        render_manual_acquisition_audit as render_acquisition_source,
        validate_acquisition_audit_logs,
    )
except ModuleNotFoundError:
    from tools.afterlight_quests.builder import (
        _SnbtPathScanner,
        _parse_snbt,
        _quest_item_ids,
        _render_quest_item_audit,
        quest_item_audit_digest,
        validate_quest_item_audit_logs,
    )
    from tools.afterlight_quests.acquisition import (
        ACQUISITION_AUDIT_RELATIVE,
        FIXTURE_RELATIVE,
        load_manifest as load_acquisition_manifest,
        render_manual_acquisition_audit as render_acquisition_source,
        validate_acquisition_audit_logs,
    )


class VerificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class LogRecord:
    timestamp: str
    thread: str
    level: str
    logger: str
    message: str
    continuations: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class LogAllowance:
    label: str
    level: str
    logger: str
    message: str
    count: int
    thread: str = "main"
    continuations: tuple[str, ...] = ()
    canonical_sha256: str | None = None


@dataclass(frozen=True)
class DedicatedErrorEvidence:
    label: str
    latest_record_indices: tuple[int, ...]
    debug_record_indices: tuple[int, ...]


RUNTIME_DIST_CLEANER_MESSAGE = (
    "Attempted to load class net/minecraft/client/multiplayer/ClientLevel "
    "for invalid dist DEDICATED_SERVER"
)
MOONLIGHT_FABRIC_MESSAGE = (
    "Fabric API detected! This is not a Fabric mod, so please don't report related "
    "issues to MoonlightLib or its dependent(s). This can usually happen when using "
    "Connector, or when using a mod that does NOT have a native Neoforge implementation. "
    "This can easily lead to poor compatibility and other bizarre issues. Proceed at "
    "your own risk. "
)
ITEMSTACK_AIR_MESSAGE = "Tried to load invalid item: 'Item must not be minecraft:air'"
JDT_WARNING_MESSAGE = (
    "Error white registering dispenser behavior for item justdirethings:fuel_canister: "
    "java.lang.IllegalStateException: Cannot get config value before config is loaded."
)
KALEIDOSCOPE_SUFFIX = (
    "[kaleidoscope_cookery:stockpot], falling back to default value: "
    "java.lang.IllegalStateException: Failed to parse either. First: Item array cannot "
    "be empty, at least one item must be defined; Second: Not a JSON object: []"
)
INCENDIUM_WARNING_MESSAGE = (
    "KubeRecipe.java#90: Failed to parse recipe "
    "'incendium:upgrade_elytra[minecraft:smithing_transform]'! Falling back to vanilla: "
    "Failed to read required component 'template: ingredient' - "
    "java.lang.IllegalStateException: Failed to parse either. First: Item array cannot "
    "be empty, at least one item must be defined; Second: Not a JSON object: []"
)
APOTHIC_WARNING_MESSAGE = (
    "Found data map file for non-existent data map type "
    "'apothic_enchanting:enchantment_info' on registry 'minecraft:enchantment'."
)

JDT_ARTIFACT_SHA256 = {
    "mods/just-dire-things.pw.toml": "6e5f7dd7091cc271fee66b0df62bde2250e8b52397b51dd911f79c088eb22d2f",
    "mods/supplementaries.pw.toml": "cdd3d67b510f20f386690a2cbdbe63fd1ae9c8a620861738b6b80b1fa5c996f9",
    "mods/moonlight.pw.toml": "e64737a18c934fe1fac2c4bf3ea1e997012d06ab67e2a06635def5968edb4474",
    "mods/kubejs.pw.toml": "01767bb677a9c4a8f318717c4c21bca7e7ef80995603403a551068a0e064e740",
}
JDT_CLASS_SHA256 = {
    (
        "mods/supplementaries.pw.toml",
        "net/mehvahdjukaar/supplementaries/common/block/dispenser/DispenserBehaviorsManager.class",
    ): "55d5096f83b294f4c6830bcde99b8e3c3a0f9d18f101c60cccc7c88828c2e70a",
    (
        "mods/supplementaries.pw.toml",
        "net/mehvahdjukaar/supplementaries/common/block/ModBlockProperties$Topping.class",
    ): "4637feea2f739e9169b3a615b705b0dfa2d65755c33e784bb00d1592caca041f",
    (
        "mods/just-dire-things.pw.toml",
        "com/direwolf20/justdirethings/common/items/FuelCanister.class",
    ): "ff6b13094a4b1cacd6a3a0dc155aee7e6cb4fa4fe1d948549858b9e6b8e55b28",
}
JDT_RUNTIME_SHA256 = {
    "libraries/net/neoforged/neoforge/21.1.248/neoforge-21.1.248-universal.jar": (
        "90a56f70425711b4e1a4b94ff0c2904ae9f6d74ca6478b3b2152ac794a07b8e5"
    ),
    "libraries/net/minecraft/server/1.21.1-20240808.144430/"
    "server-1.21.1-20240808.144430-srg.jar": (
        "26ca9c40d7e1681190b428583c38816852218e78df3f8bdb60a59a78503aec71"
    ),
}
JDT_CONFIG_SHA256 = "1585ad9a8fe3627f4858968de254f17dce69b73607940ca81e99d17a62289fe2"

SABLE_METADATA = "mods/sable.pw.toml"
SABLE_ARTIFACT_SHA256 = "da6c3b66238586603d1dcaa2afb012d36815fbce0a2d5938fbb2936701d42279"
SABLE_MIXIN_CONFIG = "sable.mixins.json"
SABLE_MIXIN_CONFIG_SHA256 = "02dd86d2bd0ed6bef4841b1ae4ac8579edeb33fe0134f2060191b49102c4878d"
SABLE_MIXIN_CLASSES = {
    "entity.entity_aabb_lookup.LevelsMixin": (
        40,
        "dev/ryanhcode/sable/mixin/entity/entity_aabb_lookup/LevelsMixin.class",
        "0b6d6e637410852d131f2178c53a454bdd506555e509c5aea2ce3127d01070c0",
    ),
    "plot.LevelsMixin": (
        100,
        "dev/ryanhcode/sable/mixin/plot/LevelsMixin.class",
        "660410f918f5676d49e734028cb2e74967a622746cc7c7f22ff805016c476bda",
    ),
    "water_occlusion.LevelsMixin": (
        132,
        "dev/ryanhcode/sable/mixin/water_occlusion/LevelsMixin.class",
        "f5cecf91372f08ef0b5b9bc36f609b6f2df726dc3612731d9e0a5a56460b647c",
    ),
}
SABLE_ENABLED_METADATA_COUNT = 159
SABLE_TOP_LEVEL_ARTIFACT_COUNT = 159
SABLE_ARCHIVE_SCOPE_COUNT = 307
SABLE_MIXIN_CONFIG_COUNT = 265
SABLE_COMMON_MIXIN_COUNT = 2320
SABLE_SERVER_MIXIN_COUNT = 5
SABLE_ANNOTATION_CLIENTLEVEL_MIXIN_COUNT = 3
REVIEWED_SERVER_ARTIFACT_COUNT = 159
REVIEWED_SERVER_ARTIFACT_INVENTORY_SHA256 = (
    "1efcf4537b3aaa0f72f9b4b49c3480dcd16003ec562ec035a5614581943cdcad"
)
REVIEWED_MIXIN_CORPUS_SHA256 = (
    "2cf50d4b9af27d7868fb1332be39ab604c3b87a5b44b27aa4a3c04fc62ee3318"
)
REVIEWED_CLIENT_TARGET_COUNT = 31
REVIEWED_CLIENT_TARGET_INVENTORY_SHA256 = (
    "cbb81775f677097560dff565346df0d9cb6a6b68af1f38a52ce9e43184ed6f59"
)
REVIEWED_CLIENT_TARGETS = (
    "Ldev/emi/emi/screen/RecipeScreen;",
    "Lnet/neoforged/neoforge/client/model/generators/ModelBuilder;",
    "Lnet/caffeinemc/mods/sodium/client/render/chunk/compile/pipeline/BlockOcclusionCache;",
    "Lnet/caffeinemc/mods/sodium/client/render/chunk/compile/pipeline/BlockRenderer;",
    "Lcom/simibubi/create/CreateClient;",
    "Lcom/simibubi/create/foundation/blockEntity/behaviour/ValueBoxRenderer;",
    "Lnet/createmod/catnip/gui/AbstractSimiScreen;",
    "Ldev/lopyluna/dndesires/compat/jei/category/DragonBreathingCategory;",
    "Ldev/lopyluna/dndesires/compat/jei/category/FreezingCategory;",
    "Ldev/lopyluna/dndesires/compat/jei/category/SandingCategory;",
    "Lnet/dakotapride/garnished/registry/JEI/DyeBlowingFanCategory;",
    "Lnet/dakotapride/garnished/registry/JEI/FreezingFanCategory;",
    "Lcom/simibubi/create/compat/jei/category/CreateRecipeCategory;",
    "Lcom/aetherteam/aether/client/TriviaGenerator;",
    "Lnet/neoforged/neoforge/client/extensions/IBlockEntityRendererExtension;",
    "Lmezz/jei/gui/bookmarks/BookmarkList;",
    "Lmezz/jei/gui/overlay/bookmarks/BookmarkOverlay;",
    "Lnet/neoforged/neoforge/client/ClientHooks;",
    "Learth/terrarium/athena/api/client/models/neoforge/FactoryManagerImpl;",
    "Lcom/simibubi/create/content/schematics/client/tools/DeployTool;",
    "Lcom/simibubi/create/content/schematics/client/SchematicAndQuillHandler;",
    "Lcom/simibubi/create/content/schematics/client/tools/SchematicToolBase;",
    "Lcom/simibubi/create/content/equipment/toolbox/ToolboxHandlerClient;",
    "Lio/github/mortuusars/exposure/client/animation/CameraPoses;",
    "Lnet/mehvahdjukaar/moonlight/api/client/util/LOD;",
    "Lnet/mehvahdjukaar/vista/client/ViewFinderController;",
    "Lnet/minecraft/client/multiplayer/ClientLevel;",
    "Lnet/minecraft/client/multiplayer/ClientLevel;",
    "Lnet/minecraft/client/multiplayer/ClientLevel;",
    "Ldev/ryanhcode/sable/sublevel/render/dispatcher/VanillaSubLevelRenderDispatcher;",
    "Lmezz/jei/library/plugins/vanilla/ingredients/ItemStackListFactory;",
)
SABLE_STACK_SHA256 = {
    "prepare": "bae3607214c9f8b88f6bd73e309b99f58eb926a2baae5d8515d3feba85efc7ca",
    "validate": "364c2c1f95784628e77870ba1d8be5f7b808016042ba565bc18d4ef27c94500b",
    "validate_changes": "6c44a8c02c15710e7a9233fe7b9b1ba456a7598db09ac21858b1d59b0fc29cac",
}
SABLE_RUNTIME_SHA256 = {
    "libraries/net/neoforged/fancymodloader/loader/4.0.43/loader-4.0.43.jar": (
        "ba406038d0ce8242391bb23b9974648748d217b67332c0db620fcabf50edbc37"
    ),
    "libraries/net/fabricmc/sponge-mixin/0.15.2+mixin.0.8.7/"
    "sponge-mixin-0.15.2+mixin.0.8.7.jar": (
        "1d45cfe3ae4a2eab38dc74276803748cf799088986260d6d912e50ddb35d15c5"
    ),
}

IDAS_COMPAT_METADATA = "mods/afterlight-idas-compat.pw.toml"
IDAS_COMPAT_VERSION = "0.1.2+1.21.1"
IDAS_COMPAT_FILENAME = "afterlight_idas_compat-0.1.2+1.21.1.jar"
IDAS_COMPAT_URL = (
    "https://github.com/Luskish/afterlight-idas-compat/releases/download/"
    "v0.1.2/afterlight_idas_compat-0.1.2%2B1.21.1.jar"
)
IDAS_COMPAT_SHA512 = (
    "f9bf2f432098babe88e13b5bea3ba631d433500f8d10f7b146d800f60cc2b46c"
    "6b4acc5dcce07f00561205880a75d27a2639d25fc35ae3a5f32aa0b5cd6cc892"
)
IDAS_COMPAT_SHA256 = "51ec890b6f079994c1fcc1a348a99a6ab359993e5bc83fe1d71ed8986da37f2b"
IDAS_COMPAT_SIZE = 39392
IDAS_COMPAT_SOURCE_COMMIT = "b3d43520e2119296324faedccc2bf4fda4fd587f"
IDAS_COMPAT_SOURCE_TREE_SHA256 = (
    "6c264d8fb9d3ef1a9ce61e6aa5b80cf0ef806988dd7389713f5eea91e55081d4"
)
IDAS_COMPAT_REVIEWED_TEMPLATES = {
    "idas:underground_camp/underground_camp_deep1": {
        "sourceSha256": "652e2bbac736f171c102342547538430a2f5327de38319503fc4bd323e7ee7da",
        "sourceLength": 1213,
        "candidateCount": 1,
        "auditDigest": "5bdae5e78f79a6f01fa99f65a940ddda00618218c1f5d3976ce473bf1f460830",
    },
    "idas:underground_camp/underground_camp1": {
        "sourceSha256": "0d7ecc5059d0d94d8cde9621d5358df1a9b89bf7dc27e93fd564668064aceb8a",
        "sourceLength": 1238,
        "candidateCount": 2,
        "auditDigest": "198210096c1bacea6802e639ce1f649a540fcdbedfb2b6e21dacadbf5e77f234",
    },
    "idas:tudor_pub/tudor_pub": {
        "sourceSha256": "36e2bbc9ae46052b84d97819a50a65c1233064af4708a724e94ebaffdb424c3f",
        "sourceLength": 62199,
        "candidateCount": 8,
        "auditDigest": "071ed0a79840f3600668b04dffdf02fc8cba4805f79ff58f3de429ed2a8d8107",
    },
    "idas:tudor_pub/tudor_pub_bottom": {
        "sourceSha256": "67a0d8447e8ec42c1eef447111bc3d40bd71e089395fa5472ae754ed88052bd2",
        "sourceLength": 19879,
        "candidateCount": 9,
        "auditDigest": "9fac0222c1f0c56de2a9100a2de3a34d83bd14259884d72962616c4d86377f27",
    },
}
IDAS_COMPAT_RESOURCE_SHA256 = {
    "META-INF/LICENSE": (
        "b5b105b0aec29aa2fd5d1b53d75339152409f6905873ca9a4f1b47a9def4e00e"
    ),
    "META-INF/MANIFEST.MF": (
        "ed53c0c2a482c08ed1c531a4306d2b6d1b71831a9c80e16638191870862868b1"
    ),
    "META-INF/afterlight-provenance.json": (
        "cc6861039400a44331c3a19c149b61d4499897028976beb5c2a70d8d52f6839e"
    ),
    "META-INF/neoforge.mods.toml": (
        "99439a71bdb9f4f39192175e995f5e3bed13402b4734ff709cb6868e4dde72ba"
    ),
    "afterlight_idas_compat.mixins.json": (
        "f1ea036959fde1aed3d5626343b11b328bad56d2174795b8cd9c065e2812fece"
    ),
    "dev/afterlight/idascompat/AfterlightIdasCompat.class": (
        "092d27ea4f2020ad8bc7296101cfd86356637f8ba44420ef5eba3308a387ffb3"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier$Authentication.class": (
        "8acd9a29f3767813c2b4200de2f781a2646b71508afa19464f2a98eb096bd12b"
    ),
    "dev/afterlight/idascompat/AuthenticatedStructureResourceLoader$Digester.class": (
        "70b98340fd5f336e8bd45ffc3c3a1c3d306f069995b32ef2ca7515f661f8f89a"
    ),
    "dev/afterlight/idascompat/AuthenticatedStructureResourceLoader$Operations.class": (
        "5ac90d61264960942a00cb5fe33c2f548657bd147136fb2edbd2fb462a74e39f"
    ),
    "dev/afterlight/idascompat/AuthenticatedStructureResourceLoader$Parser.class": (
        "aa70b83fc49fc50a88270be966e04bea9e1b353d2670ee11db78ec17354866ca"
    ),
    "dev/afterlight/idascompat/AuthenticatedStructureResourceLoader$Sanitizer.class": (
        "61ea7215ecb110882453f43392962379080f200012c9ee6472446d414f363597"
    ),
    "dev/afterlight/idascompat/AuthenticatedStructureResourceLoader.class": (
        "7e24770ddf98729dd9a0e9eff0de1974969c79b0a0f2284efdbc8b2fd94eeafb"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier$ArtifactHasher.class": (
        "95a786175fa4385b4ce61b71c2a9f025deb80d7f7667a2d8b33a52aacef4a4c0"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier$InstalledArtifact.class": (
        "20a5adcc90749d7676c9cd390d31d2861f1d37c591ec91421c20ca4e6206a342"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier$InstalledArtifactLookup.class": (
        "1297f21840398c2df3d19a2faabeee18bc08813f9a8f5a8701ea81c786e4db9f"
    ),
    "dev/afterlight/idascompat/IdasArtifactVerifier.class": (
        "da668afae36ea817bddbf74d8369c53295864ae3bc15dcced49f53be59d8a266"
    ),
    "dev/afterlight/idascompat/ReviewedTemplateRegistry$Approval.class": (
        "82bebeb6f807142f812ec5b1da545256d5848617cde15cc3a87126daf7177270"
    ),
    "dev/afterlight/idascompat/ReviewedTemplateRegistry.class": (
        "80f511170eda44af8dd4f5dd5dfd80569b02cd3e35cbe47f4c821c1edd195bff"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Action.class": (
        "320bf3f1a40ba5ff80881bd0a1ca5ec523158ccb62a96e61944e9f1f56595ae8"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Inspection.class": (
        "4b445f8333042a4c5f0996c829ca397d2e50af76bf20ef2e5019e46f8725cd5d"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Mutation.class": (
        "c410f98f8cdd590438f9ac5de5fb3d49d2843e1f72950233161cdca653f35ada"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Parent.class": (
        "6f1e0099ce4746869b1ea58c61cb87a5a20fde8144c03e6486c17034355cb658"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Result.class": (
        "723597f597a61e33e4bbac04ca4a9076afde1f3da134fe79e674b92161f97ec0"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Root.class": (
        "6568f8635e5366e380f38cf2fae84e379f020b9d2066737d4c2c7ade7f7c5f9b"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Shape.class": (
        "17921e5a0a8f3cf8031d442294dc936caa924fdbdb7aee8577b25559c772599b"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer$Unreviewed.class": (
        "b1fb27ad46692a41ce5331ad08065d43701df473f86a6307fe5ddb1d9658997a"
    ),
    "dev/afterlight/idascompat/StructureAirItemSanitizer.class": (
        "45bfe31e4d268fb2ddc48257e534526ff346a4a608cdd92d54490adc463de334"
    ),
    "dev/afterlight/idascompat/mixin/StructureTemplateAccessor.class": (
        "eeaef3dd31492cabec8db1d8dec79cd5aa0777c4ec4e048a4794fcf4b1361a86"
    ),
    "dev/afterlight/idascompat/mixin/StructureTemplateManagerMixin.class": (
        "014f4ecef2cedc8f79cb825bb75d3370a2da2ffb70cc2adcde3bb226f2e44a8f"
    ),
}
IDAS_COMPAT_LOGGER = "afterlight_idas_compat/STRUCTURE_SANITIZER/"
IDAS_COMPAT_READY_MESSAGE = (
    "AFTERLIGHT_IDAS_COMPAT_READY idas_version=1.13.7+1.21.1-neoforge "
    "artifact_sha256=7f5031dd90ae0b32d7fe5c6c47c877cac1eb95a178bc78d196cb24c17ce82522 "
    "known_compounds=1684 known_templates=100"
)
IDAS_COMPAT_CAMP_MESSAGE = (
    "AFTERLIGHT_IDAS_SANITIZED template=idas:underground_camp/underground_camp1 "
    "replacements=2 "
    "digest=198210096c1bacea6802e639ce1f649a540fcdbedfb2b6e21dacadbf5e77f234"
)
IDAS_COMPAT_BOOT_SANITIZED_MESSAGES = (
    "AFTERLIGHT_IDAS_SANITIZED template=idas:underground_camp/underground_camp_deep1 "
    "replacements=1 "
    "digest=5bdae5e78f79a6f01fa99f65a940ddda00618218c1f5d3976ce473bf1f460830",
    IDAS_COMPAT_CAMP_MESSAGE,
    "AFTERLIGHT_IDAS_SANITIZED template=idas:tudor_pub/tudor_pub replacements=8 "
    "digest=071ed0a79840f3600668b04dffdf02fc8cba4805f79ff58f3de429ed2a8d8107",
    "AFTERLIGHT_IDAS_SANITIZED template=idas:tudor_pub/tudor_pub_bottom replacements=9 "
    "digest=9fac0222c1f0c56de2a9100a2de3a34d83bd14259884d72962616c4d86377f27",
)


LOG_HEADER = re.compile(
    r"^\[(?P<timestamp>\d{2}[A-Z][a-z]{2}\d{4} \d{2}:\d{2}:\d{2}\.\d{3})\] "
    r"\[(?P<thread>[^\]\r\n]+)\/(?P<level>TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\] "
    r"\[(?P<logger>[^\]]+)\]: (?P<message>.*)$"
)
CONSOLE_HEADER = re.compile(
    r"^\[(?P<timestamp>\d{2}:\d{2}:\d{2}(?:\.\d{3})?)\] "
    r"\[(?P<thread>[^\]\r\n]+)\/(?P<level>TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\] "
    r"\[(?P<logger>[^\]]+)\]: (?P<message>.*)$"
)
ANSI_ESCAPE = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|[@-_])")
SGR_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")
HEADER_LEVEL_LIKE = re.compile(
    r"\[[^\]\r\n]+/(?:TRACE|DEBUG|INFO|WARN|ERROR|FATAL)(?:\]|\s|$)"
)
SEVERE_OUTPUT_LIKE = re.compile(
    r"(?:\b(?:FATAL|ERROR)\b|"
    r"(?:^|\n)[ \t]*(?:Exception|Error|Throwable):|"
    r"(?<![A-Za-z0-9_$])(?:[A-Za-z_$][A-Za-z0-9_$]*\.)*"
    r"[A-Z][A-Za-z0-9_$]*?(?:Exception|Error|Throwable)(?![A-Za-z0-9_$])|"
    r"(?<![A-Za-z0-9_$])(?:[a-z_$][A-Za-z0-9_$]*\.)+"
    r"(?:Exception|Error|Throwable)(?![A-Za-z0-9_$])|"
    r"\bCaused by:|\bSegmentation fault\b|\bpanic:)",
)
REVIEWED_CONSOLE_SEVERE_COUNT = 60
REVIEWED_CONSOLE_SEVERE_SHA256 = (
    "901cf0988b781987d58e2821e05f963fbbdc75e65ade282ffad5de0767627351"
)
REVIEWED_DEBUG_SEVERE_COUNT = 77
REVIEWED_DEBUG_SEVERE_SHA256 = (
    "826e9160f647ed1bc0796692c0be0da695633655e12d4eaeacec2dbffea35e44"
)
CONSOLE_LOGGER_CANONICAL = {
    "common.asm.RuntimeDistCleaner/DISTXFORM": (
        "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM"
    ),
    "ne.ne.fm.co.as.RuntimeDistCleaner/DISTXFORM": (
        "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM"
    ),
    "minecraft/AbstractPackResources": (
        "net.minecraft.server.packs.AbstractPackResources/"
    ),
    "ne.ne.fm.VersionChecker/": "net.neoforged.fml.VersionChecker/",
}
CONSOLE_ATTACHED_NOISE = (
    "WARN StatusConsoleListener Advanced terminal features are not available in "
    "this environment"
)

PACK_SHIPPING_ROOTS = frozenset(
    {
        "config",
        "defaultconfigs",
        "global_packs",
        "kubejs",
        "mods",
        "resourcepacks",
        "shaderpacks",
    }
)
EXPECTED_PACK_NAME = "AFTERLIGHT"
EXPECTED_PACK_AUTHOR = "Shane + ECHO"
EXPECTED_PACK_FORMAT = "packwiz:1.1.0"
EXPECTED_INDEX_FILE = "index.toml"
EXPECTED_MINECRAFT_VERSION = "1.21.1"
EXPECTED_NEOFORGE_VERSION = "21.1.248"
FORBIDDEN_SHIPPING_PARTS = frozenset(
    {
        ".agents",
        ".claude",
        ".git",
        ".github",
        ".superpowers",
        "dist",
        "docs",
        "server-test",
        "tools",
    }
)
FORBIDDEN_SHIPPING_SUFFIXES = frozenset(
    {".env", ".jar", ".key", ".nbt", ".p12", ".pem"}
)
SENSITIVE_SHIPPING_PART = re.compile(
    r"(?:^|[._-])(?:credential|credentials|secret|secrets|token|tokens)(?:[._-]|$)",
    re.IGNORECASE,
)

YUNGS_VOLATILE_WORKER_WARNINGS = frozenset(
    {
        "Discarding @Unique public method getEnhancedJunctionIterator in "
        "yungsapi.mixins.json:BeardifierMixin from mod yungsapi because it already "
        "exists in net.minecraft.world.level.levelgen.Beardifier",
        "Discarding @Unique public method setEnhancedJunctionIterator in "
        "yungsapi.mixins.json:BeardifierMixin from mod yungsapi because it already "
        "exists in net.minecraft.world.level.levelgen.Beardifier",
    }
)
SUPPLEMENTARIES_VOLATILE_WORKER_WARNINGS = frozenset(
    {
        "Could not find Sign for wood cataclysm:chorus. Does this block even "
        "exist? It should! Skipping way sign recipe generation",
        "Could not find Sign for wood iceandfire:dreadwood. Does this block even "
        "exist? It should! Skipping way sign recipe generation",
    }
)
REVIEWED_WARNING_TOTAL = 473
REVIEWED_WARNING_UNIQUE = 379
REVIEWED_WARNING_MULTISET_SHA256 = (
    "f693303650af44b70cd2cfe1eaf78c6d44bd1e70ce111857870a20de9bf3c295"
)
REVIEWED_DUPLICATE_ZIP_MEMBERS = {
    ("mods/ars-nouveau.pw.toml", "META-INF/LICENSE.txt"): (
        6,
        "a2521407b3209df7dcebfc12cd6d732b24bfa2fe44982ef613e269666482521d",
    ),
    ("mods/ars-nouveau.pw.toml", "META-INF/NOTICE.txt"): (
        6,
        "a5b67acba0dd6a28db1c36f4d9cf8052979b59c36dba0a9119cf03c8e5365fb0",
    ),
}
BETTER_STRONGHOLDS_ORE_RELATIVE = PurePosixPath(
    "config/betterstrongholds/neoforge-1_21/ores.json"
)
BETTER_STRONGHOLDS_ORE_ENTRIES = {
    "minecraft:lapis_ore": 0.15,
    "minecraft:redstone_ore[lit=false]": 0.15,
    "minecraft:diamond_ore": 0.05,
    "minecraft:emerald_ore": 0.05,
    "minecraft:iron_ore": 0.2,
    "minecraft:coal_ore": 0.19,
    "minecraft:gold_ore": 0.2,
}


def _hash_bytes(payload: bytes, hash_format: str) -> str:
    normalized = hash_format.lower().replace("-", "")
    try:
        digest = hashlib.new(normalized)
    except ValueError as error:
        raise VerificationError(f"unsupported hash format {hash_format}") from error
    digest.update(payload)
    return digest.hexdigest()


def _hash_file(path: Path, hash_format: str) -> str:
    normalized = hash_format.lower().replace("-", "")
    try:
        digest = hashlib.new(normalized)
    except ValueError as error:
        raise VerificationError(f"unsupported hash format {hash_format}") from error
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise VerificationError(f"cannot read TOML {path}: {error}") from error


def _safe_relative_path(value: str, label: str) -> PurePosixPath:
    path = PurePosixPath(value)
    if path.as_posix() != value:
        raise VerificationError(f"noncanonical {label} path {value!r}")
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise VerificationError(f"unsafe {label} path {value!r}")
    return path


def _validated_root(
    value: Path | str, label: str, *, must_exist: bool = True
) -> Path:
    raw = os.fspath(value)
    if not raw:
        raise VerificationError(f"{label} path is empty")
    candidate = Path(os.path.abspath(raw))
    current = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        current /= part
        try:
            current_stat = current.lstat()
        except FileNotFoundError as error:
            if must_exist:
                raise VerificationError(
                    f"cannot inspect {label} path {candidate}: {error}"
                ) from error
            return candidate
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} path {candidate}: {error}"
            ) from error
        if stat.S_ISLNK(current_stat.st_mode):
            raise VerificationError(f"symlink in {label} path: {current}")
    try:
        resolved = candidate.resolve(strict=must_exist)
    except OSError as error:
        raise VerificationError(f"cannot resolve {label} path {candidate}: {error}") from error
    if resolved != candidate:
        raise VerificationError(
            f"{label} path is not physically canonical: {candidate} != {resolved}"
        )
    if must_exist:
        try:
            root_stat = candidate.lstat()
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} path {candidate}: {error}"
            ) from error
        if not stat.S_ISDIR(root_stat.st_mode):
            raise VerificationError(f"{label} is not a directory: {candidate}")
    return candidate


def _verified_regular_file(
    root: Path, relative: PurePosixPath, label: str
) -> Path:
    root = _validated_root(root, f"{label} root")
    target = root
    for part in relative.parts:
        target /= part
        try:
            target_stat = target.lstat()
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} path {relative.as_posix()}: {error}"
            ) from error
        if stat.S_ISLNK(target_stat.st_mode):
            raise VerificationError(
                f"symlink in {label} path: {relative.as_posix()}"
            )
    try:
        resolved = target.resolve(strict=True)
    except OSError as error:
        raise VerificationError(
            f"cannot resolve {label} path {relative.as_posix()}: {error}"
        ) from error
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise VerificationError(
            f"{label} path escapes pack root: {relative.as_posix()}"
        ) from error
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(target, flags)
    except OSError as error:
        raise VerificationError(
            f"cannot open {label} path {relative.as_posix()}: {error}"
        ) from error
    try:
        opened_stat = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    if not stat.S_ISREG(opened_stat.st_mode):
        raise VerificationError(f"{label} is missing: {relative.as_posix()}")
    if opened_stat.st_nlink != 1:
        raise VerificationError(
            f"hardlink rejected for {label}: {relative.as_posix()}"
        )
    if (opened_stat.st_dev, opened_stat.st_ino) != (
        target_stat.st_dev,
        target_stat.st_ino,
    ):
        raise VerificationError(
            f"{label} changed during verification: {relative.as_posix()}"
        )
    return resolved


def _installed_shipping_inventory(install_path: Path) -> set[str]:
    inventory: set[str] = set()
    for root_name in sorted(PACK_SHIPPING_ROOTS):
        shipping_root = install_path / root_name
        try:
            root_stat = shipping_root.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise VerificationError(
                f"cannot inspect installed shipping root {root_name}: {error}"
            ) from error
        if stat.S_ISLNK(root_stat.st_mode):
            raise VerificationError(f"symlink in installed shipping root: {root_name}")
        if not stat.S_ISDIR(root_stat.st_mode):
            raise VerificationError(
                f"installed shipping root is not a directory: {root_name}"
            )
        for directory, directory_names, file_names in os.walk(
            shipping_root, followlinks=False
        ):
            directory_path = Path(directory)
            for name in tuple(directory_names):
                relative = _safe_relative_path(
                    (directory_path / name).relative_to(install_path).as_posix(),
                    "installed directory",
                )
                child_stat = (directory_path / name).lstat()
                if stat.S_ISLNK(child_stat.st_mode):
                    raise VerificationError(
                        f"symlink in installed shipping path: {relative.as_posix()}"
                    )
                if not stat.S_ISDIR(child_stat.st_mode):
                    raise VerificationError(
                        f"non-directory in installed shipping path: {relative.as_posix()}"
                    )
            for name in file_names:
                relative = _safe_relative_path(
                    (directory_path / name).relative_to(install_path).as_posix(),
                    "installed file",
                )
                _verified_regular_file(
                    install_path, relative, "installed shipping file"
                )
                inventory.add(relative.as_posix())
    return inventory


def _artifact_inventory_digest(inventory: Sequence[dict[str, str]]) -> str:
    payload = json.dumps(
        list(inventory), ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return _hash_bytes(payload, "sha256")


def verify_reviewed_server_artifact_inventory(
    provenance: dict,
    *,
    expected_count: int = REVIEWED_SERVER_ARTIFACT_COUNT,
    expected_digest: str = REVIEWED_SERVER_ARTIFACT_INVENTORY_SHA256,
) -> None:
    actual = provenance.get("afterlightServerArtifacts")
    expected = {"count": expected_count, "digest": expected_digest}
    actual_summary = (
        {"count": actual.get("count"), "digest": actual.get("digest")}
        if isinstance(actual, dict)
        else actual
    )
    if actual_summary != expected:
        raise VerificationError(
            "server artifact inventory changed: "
            f"expected={expected} actual={actual_summary}"
        )


def _server_artifact_evidence(
    metadata_relatives: Sequence[str], resolved: dict[str, Path], provenance: dict
) -> dict[str, object]:
    inventory = []
    for metadata_relative in metadata_relatives:
        cached = provenance["cachedFiles"].get(metadata_relative)
        if not isinstance(cached, dict) or not isinstance(
            cached.get("cachedLocation"), str
        ):
            raise VerificationError(
                f"missing cached location for server artifact {metadata_relative}"
            )
        inventory.append(
            {
                "metadata": metadata_relative,
                "cachedLocation": cached["cachedLocation"],
                "sha256": _hash_file(resolved[metadata_relative], "sha256"),
            }
        )
    inventory.sort(key=lambda entry: (entry["metadata"], entry["cachedLocation"]))
    return {
        "count": len(inventory),
        "digest": _artifact_inventory_digest(inventory),
        "inventory": inventory,
    }


def _enforce_shipping_policy(relative: PurePosixPath) -> None:
    lowered_parts = tuple(part.lower() for part in relative.parts)
    if lowered_parts[0] not in PACK_SHIPPING_ROOTS:
        raise VerificationError(
            f"shipping policy rejects root leakage: {relative.as_posix()}"
        )
    forbidden = sorted(set(lowered_parts) & FORBIDDEN_SHIPPING_PARTS)
    if forbidden:
        raise VerificationError(
            "shipping policy rejects forbidden path component "
            f"{forbidden[0]} in {relative.as_posix()}"
        )
    sensitive = next(
        (part for part in relative.parts if SENSITIVE_SHIPPING_PART.search(part)),
        None,
    )
    if sensitive is not None:
        raise VerificationError(
            "shipping policy rejects sensitive path component "
            f"{sensitive} in {relative.as_posix()}"
        )
    if relative.suffix.lower() in FORBIDDEN_SHIPPING_SUFFIXES:
        raise VerificationError(
            f"shipping policy rejects forbidden extension: {relative.as_posix()}"
        )


def verify_better_strongholds_contract(root: Path | str) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    config_path = _verified_regular_file(
        root_path, BETTER_STRONGHOLDS_ORE_RELATIVE, "Better Strongholds ore config"
    )
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(
            f"cannot read Better Strongholds ore config: {error}"
        ) from error
    expected = {
        "oreChances": {
            "entries": BETTER_STRONGHOLDS_ORE_ENTRIES,
            "defaultBlock": "minecraft:coal_ore",
        }
    }
    if config != expected:
        raise VerificationError(
            f"Better Strongholds complete ore contract changed: {config}"
        )
    fallback = 1.0 - sum(BETTER_STRONGHOLDS_ORE_ENTRIES.values())
    effective_coal = BETTER_STRONGHOLDS_ORE_ENTRIES["minecraft:coal_ore"] + fallback
    if abs(fallback - 0.01) > 1e-12 or abs(effective_coal - 0.2) > 1e-12:
        raise VerificationError(
            "Better Strongholds effective fallback coal probability changed"
        )
    return {
        "entries": dict(BETTER_STRONGHOLDS_ORE_ENTRIES),
        "fallback": fallback,
        "effective_coal": effective_coal,
    }


def verify_manifest(root: Path | str) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    pack_path = _verified_regular_file(
        root_path, PurePosixPath("pack.toml"), "pack manifest"
    )
    pack_bytes = pack_path.read_bytes()
    pack = _read_toml(pack_path)
    if pack.get("name") != EXPECTED_PACK_NAME:
        raise VerificationError("pack name changed")
    if pack.get("author") != EXPECTED_PACK_AUTHOR:
        raise VerificationError("pack author changed")
    version = pack.get("version")
    if not isinstance(version, str) or not version.strip():
        raise VerificationError("pack version is missing")
    if pack.get("pack-format") != EXPECTED_PACK_FORMAT:
        raise VerificationError("pack format changed")
    versions = pack.get("versions")
    if not isinstance(versions, dict):
        raise VerificationError("pack runtime versions are missing")
    if versions.get("minecraft") != EXPECTED_MINECRAFT_VERSION:
        raise VerificationError("Minecraft version changed")
    if versions.get("neoforge") != EXPECTED_NEOFORGE_VERSION:
        raise VerificationError("NeoForge version changed")
    index_config = pack.get("index")
    if not isinstance(index_config, dict):
        raise VerificationError("pack.toml has no index table")

    index_relative = _safe_relative_path(str(index_config.get("file", "")), "index")
    if index_relative != PurePosixPath(EXPECTED_INDEX_FILE):
        raise VerificationError("pack index file changed")
    index_hash_format = str(index_config.get("hash-format", ""))
    if index_hash_format != "sha256":
        raise VerificationError("pack.toml index hash-format must remain sha256")
    index_path = _verified_regular_file(root_path, index_relative, "pack index")
    index_bytes = index_path.read_bytes()
    expected_index_hash = str(index_config.get("hash", ""))
    actual_index_hash = _hash_bytes(index_bytes, index_hash_format)
    if actual_index_hash != expected_index_hash:
        raise VerificationError(
            f"index hash mismatch: expected {expected_index_hash}, got {actual_index_hash}"
        )

    index = _read_toml(index_path)
    file_hash_format = str(index.get("hash-format", ""))
    if file_hash_format != "sha256":
        raise VerificationError("index.toml hash-format must remain sha256")
    entries = index.get("files")
    if not isinstance(entries, list):
        raise VerificationError("index.toml has no files array")

    indexed_hashes: dict[str, str] = {}
    indexed_entries: dict[str, dict[str, object]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise VerificationError("index.toml contains a non-table file entry")
        relative_text = str(entry.get("file", ""))
        relative = _safe_relative_path(relative_text, "indexed file")
        _enforce_shipping_policy(relative)
        if relative_text in indexed_hashes:
            raise VerificationError(f"duplicate index entry {relative_text}")
        metafile = entry.get("metafile", False)
        if not isinstance(metafile, bool):
            raise VerificationError(
                f"index entry metafile flag is not boolean: {relative_text}"
            )
        target = _verified_regular_file(root_path, relative, "indexed file")
        expected_hash = str(entry.get("hash", ""))
        actual_hash = _hash_file(target, file_hash_format)
        if actual_hash != expected_hash:
            raise VerificationError(
                f"indexed file hash mismatch for {relative_text}: expected {expected_hash}, got {actual_hash}"
            )
        indexed_hashes[relative_text] = expected_hash
        indexed_entries[relative_text] = {
            "hash": expected_hash,
            "metafile": metafile,
        }

    return {
        "pack_hash": _hash_bytes(pack_bytes, "sha256"),
        "index_hash": actual_index_hash,
        "index_hash_format": index_hash_format,
        "file_hash_format": file_hash_format,
        "indexed_hashes": indexed_hashes,
        "indexed_entries": indexed_entries,
    }


def validate_pack_version_payload(payload: bytes, expected_version: str) -> str:
    try:
        value = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VerificationError("pack runtime version is not valid UTF-8") from error
    if value != f"{expected_version}\n":
        raise VerificationError(
            "pack runtime version must be one exact line matching pack.toml"
        )
    return expected_version


def verify_signal_runtime_identity(
    root: Path | str,
    manifest: dict[str, object] | None = None,
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    manifest = verify_manifest(root_path) if manifest is None else manifest
    indexed_entries = manifest.get("indexed_entries")
    if not isinstance(indexed_entries, dict):
        raise VerificationError("manifest has no indexed entry inventory")

    pack = _read_toml(
        _verified_regular_file(
            root_path, PurePosixPath("pack.toml"), "pack manifest"
        )
    )
    version = pack.get("version")
    if not isinstance(version, str) or not version:
        raise VerificationError("pack version is missing")

    required_entries = {
        "config/afterlight/pack_version.txt": False,
        "config/afterlight/echo_route.json": False,
        "mods/afterlight-signal.pw.toml": True,
    }
    for relative, metafile in required_entries.items():
        entry = indexed_entries.get(relative)
        if not isinstance(entry, dict) or entry.get("metafile") is not metafile:
            raise VerificationError(
                f"Signal runtime file has wrong or missing index entry: {relative}"
            )

    version_path = _verified_regular_file(
        root_path,
        PurePosixPath("config/afterlight/pack_version.txt"),
        "pack runtime version",
    )
    validate_pack_version_payload(version_path.read_bytes(), version)

    route_path = _verified_regular_file(
        root_path,
        PurePosixPath("config/afterlight/echo_route.json"),
        "ECHO route",
    )
    quest_root = root_path / "config" / "ftbquests" / "quests"
    try:
        from afterlight_quests.echo_route import (
            build_echo_route,
            render_echo_route,
            validate_echo_route,
        )
    except ModuleNotFoundError:
        from tools.afterlight_quests.echo_route import (
            build_echo_route,
            render_echo_route,
            validate_echo_route,
        )
    try:
        route = json.loads(route_path.read_text(encoding="utf-8"))
        errors = validate_echo_route(route, quest_root)
        expected_route = render_echo_route(build_echo_route(quest_root))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise VerificationError(f"cannot validate deterministic ECHO route: {error}") from error
    if errors:
        raise VerificationError("invalid ECHO route: " + "; ".join(errors))
    if route_path.read_text(encoding="utf-8") != expected_route:
        raise VerificationError("ECHO route differs from deterministic builder output")

    descriptor_path = _verified_regular_file(
        root_path,
        PurePosixPath("mods/afterlight-signal.pw.toml"),
        "AFTERLIGHT Signal descriptor",
    )
    descriptor = _read_toml(descriptor_path)
    if descriptor.get("name") != "AFTERLIGHT Signal":
        raise VerificationError("AFTERLIGHT Signal descriptor name changed")
    if descriptor.get("filename") != "afterlight-signal-0.2.1+1.21.1.jar":
        raise VerificationError("AFTERLIGHT Signal descriptor filename changed")
    if descriptor.get("side") != "both":
        raise VerificationError("AFTERLIGHT Signal descriptor side must be both")
    download = descriptor.get("download")
    if not isinstance(download, dict):
        raise VerificationError("AFTERLIGHT Signal descriptor has no download table")
    signal_url = (
        "https://github.com/Luskish/afterlight-signal/releases/download/v0.2.1/"
        "afterlight-signal-0.2.1%2B1.21.1.jar"
    )
    if download.get("url") != signal_url:
        raise VerificationError("AFTERLIGHT Signal descriptor URL changed")
    if download.get("hash-format") != "sha512":
        raise VerificationError("AFTERLIGHT Signal descriptor must use SHA-512")
    signal_sha512 = download.get("hash")
    if not isinstance(signal_sha512, str) or not re.fullmatch(
        r"[0-9a-f]{128}", signal_sha512
    ):
        raise VerificationError("AFTERLIGHT Signal descriptor SHA-512 is malformed")

    segments = route["segments"]
    return {
        "version": version,
        "route_segments": len(segments),
        "route_quests": sum(len(segment["quests"]) for segment in segments),
        "terminal_quest": route["terminal_quest"],
        "signal_side": descriptor["side"],
        "signal_url": signal_url,
        "signal_sha512": signal_sha512,
    }


def verify_install_provenance(
    root: Path | str, install: Path | str, verify_files: bool = True
) -> dict:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    manifest = verify_manifest(root_path)
    provenance_path = _verified_regular_file(
        install_path, PurePosixPath("packwiz.json"), "installer provenance"
    )
    try:
        provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError(f"cannot read installer provenance {provenance_path}: {error}") from error

    expected_pack = provenance.get("packFileHash", {})
    if expected_pack != {"type": "sha256", "value": manifest["pack_hash"]}:
        raise VerificationError("installed pack provenance does not match current pack.toml")
    expected_index = provenance.get("indexFileHash", {})
    if expected_index != {
        "type": manifest["index_hash_format"],
        "value": manifest["index_hash"],
    }:
        raise VerificationError("installed index provenance does not match current index.toml")
    if provenance.get("cachedSide") != "server":
        raise VerificationError("installer provenance is not for server side")
    cached_files = provenance.get("cachedFiles")
    if not isinstance(cached_files, dict):
        raise VerificationError("installer provenance has no cachedFiles map")

    indexed_entries = manifest["indexed_entries"]
    if not isinstance(indexed_entries, dict):
        raise VerificationError("authenticated manifest has no indexed entry map")
    file_hash_format = str(manifest["file_hash_format"])
    expected_cached_files: dict[str, dict[str, object]] = {}
    installed_locations: dict[str, str] = {}
    client_only_locations: set[str] = set()
    server_artifact_metadata: dict[str, str] = {}
    for relative_text, indexed in indexed_entries.items():
        if not isinstance(relative_text, str) or not isinstance(indexed, dict):
            raise VerificationError("authenticated manifest entry is malformed")
        indexed_hash = str(indexed.get("hash", ""))
        if not indexed.get("metafile", False):
            prior_metadata = installed_locations.get(relative_text)
            if prior_metadata is not None:
                raise VerificationError(
                    "duplicate cachedLocation derived from authenticated index: "
                    f"{relative_text} ({prior_metadata}, {relative_text})"
                )
            installed_locations[relative_text] = relative_text
            expected_cached_files[relative_text] = {
                "hash": {"type": file_hash_format, "value": indexed_hash},
                "cachedLocation": relative_text,
                "optionValue": True,
            }
            continue

        metadata_relative = _safe_relative_path(relative_text, "metadata")
        metadata_path = _verified_regular_file(
            root_path, metadata_relative, "metadata"
        )
        metadata = _read_toml(metadata_path)
        side = metadata.get("side")
        if side not in ("client", "server", "both"):
            raise VerificationError(
                f"metadata has no deliberate side value: {relative_text}"
            )
        if side == "client":
            filename = _safe_relative_path(
                str(metadata.get("filename", "")), "metadata filename"
            )
            if len(filename.parts) != 1:
                raise VerificationError(
                    f"metadata filename must be a basename: {relative_text}"
                )
            client_only_locations.add(
                (PurePosixPath(relative_text).parent / filename).as_posix()
            )
            expected_cached_files[relative_text] = {
                "optionValue": True,
                "onlyOtherSide": True,
            }
            continue

        filename = _safe_relative_path(
            str(metadata.get("filename", "")), "metadata filename"
        )
        if len(filename.parts) != 1:
            raise VerificationError(
                f"metadata filename must be a basename: {relative_text}"
            )
        download = metadata.get("download")
        if not isinstance(download, dict):
            raise VerificationError(f"metadata has no download table: {relative_text}")
        linked_hash_format = str(download.get("hash-format", ""))
        linked_hash = str(download.get("hash", ""))
        _hash_bytes(b"", linked_hash_format)
        if not re.fullmatch(r"[0-9a-f]+", linked_hash):
            raise VerificationError(
                f"metadata download hash is malformed: {relative_text}"
            )
        cached_location = (
            PurePosixPath(relative_text).parent / filename
        ).as_posix()
        prior_metadata = installed_locations.get(cached_location)
        if prior_metadata is not None:
            raise VerificationError(
                "duplicate cachedLocation derived from authenticated metadata: "
                f"{cached_location} ({prior_metadata}, {relative_text})"
            )
        installed_locations[cached_location] = relative_text
        server_artifact_metadata[cached_location] = relative_text
        expected_cached_files[relative_text] = {
            "hash": {"type": file_hash_format, "value": indexed_hash},
            "linkedFileHash": {
                "type": linked_hash_format,
                "value": linked_hash,
            },
            "cachedLocation": cached_location,
            "optionValue": True,
        }

    if cached_files != expected_cached_files:
        actual_keys = set(cached_files)
        expected_keys = set(expected_cached_files)
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        changed = sorted(
            key
            for key in actual_keys & expected_keys
            if cached_files[key] != expected_cached_files[key]
        )
        raise VerificationError(
            "installed cachedFiles payload differs from authenticated server pack: "
            f"missing={missing} extra={extra} changed={changed}"
        )

    if not verify_files:
        return provenance

    physical_inventory = _installed_shipping_inventory(install_path)
    present_client_artifacts = sorted(client_only_locations & physical_inventory)
    if present_client_artifacts:
        raise VerificationError(
            f"client-only artifact present in server install: {present_client_artifacts}"
        )
    expected_physical_inventory = {
        str(cached["cachedLocation"])
        for cached in expected_cached_files.values()
        if isinstance(cached.get("cachedLocation"), str)
    }
    if physical_inventory != expected_physical_inventory:
        raise VerificationError(
            "physical shipping inventory differs from authenticated server pack: "
            f"missing={sorted(expected_physical_inventory - physical_inventory)} "
            f"extra={sorted(physical_inventory - expected_physical_inventory)}"
        )

    artifact_inventory: list[dict[str, str]] = []
    for relative_text, cached in expected_cached_files.items():
        cached_location = cached.get("cachedLocation")
        if not isinstance(cached_location, str):
            continue
        installed_relative = _safe_relative_path(
            cached_location, f"installed location for {relative_text}"
        )
        installed_path = _verified_regular_file(
            install_path, installed_relative, "installed pack file"
        )
        hash_spec = cached.get("linkedFileHash", cached.get("hash"))
        if not isinstance(hash_spec, dict):
            raise VerificationError(
                f"installed pack file has no authenticated hash: {cached_location}"
            )
        expected_hash = str(hash_spec.get("value", ""))
        actual_hash = _hash_file(installed_path, str(hash_spec.get("type", "")))
        if actual_hash != expected_hash:
            raise VerificationError(
                "installed file hash mismatch for "
                f"{cached_location}: expected {expected_hash}, got {actual_hash}"
            )
        metadata_identity = server_artifact_metadata.get(cached_location)
        if metadata_identity is not None:
            artifact_inventory.append(
                {
                    "metadata": metadata_identity,
                    "cachedLocation": cached_location,
                    "sha256": _hash_file(installed_path, "sha256"),
                }
            )
    artifact_inventory.sort(
        key=lambda entry: (entry["metadata"], entry["cachedLocation"])
    )
    provenance["afterlightServerArtifacts"] = {
        "count": len(artifact_inventory),
        "digest": _artifact_inventory_digest(artifact_inventory),
        "inventory": artifact_inventory,
    }
    if (root_path / FIXTURE_RELATIVE).is_file():
        for relative_text, renderer in QUEST_RUNTIME_AUDITS:
            indexed = indexed_entries.get(relative_text)
            if not isinstance(indexed, dict) or indexed.get("metafile", False):
                raise VerificationError(
                    "quest runtime audit source is not directly indexed: "
                    f"{relative_text}"
                )
            relative = PurePosixPath(relative_text)
            canonical = renderer(root_path)
            source_path = _verified_regular_file(
                root_path,
                relative,
                "repository quest runtime audit source",
            )
            installed_path = _verified_regular_file(
                install_path,
                relative,
                "installed quest runtime audit source",
            )
            if source_path.read_bytes() != canonical:
                raise VerificationError(
                    f"quest runtime audit repository source is stale: {relative_text}"
                )
            if installed_path.read_bytes() != canonical:
                raise VerificationError(
                    f"quest runtime audit install source is stale: {relative_text}"
                )
    return provenance


def _resolve_source_jar(
    root_path: Path,
    install_path: Path,
    metadata_relative: str,
    manifest: dict,
    provenance: dict,
) -> Path:
    metadata_posix = _safe_relative_path(metadata_relative, "metadata")
    if metadata_posix.suffixes[-2:] != [".pw", ".toml"]:
        raise VerificationError(f"source metadata must be an exact .pw.toml path: {metadata_relative}")
    metadata_path = root_path.joinpath(*metadata_posix.parts)
    indexed_hashes = manifest["indexed_hashes"]
    if metadata_relative not in indexed_hashes:
        raise VerificationError(f"source metadata is not indexed: {metadata_relative}")

    metadata = _read_toml(metadata_path)
    filename = str(metadata.get("filename", ""))
    if not filename or PurePosixPath(filename).name != filename:
        raise VerificationError(f"invalid source filename in {metadata_relative}")
    side = metadata.get("side")
    if side not in ("server", "both"):
        raise VerificationError(
            f"source metadata {metadata_relative} is not installed on the server side"
        )
    download = metadata.get("download")
    if not isinstance(download, dict):
        raise VerificationError(f"source metadata has no download table: {metadata_relative}")
    declared_hash_format = str(download.get("hash-format", ""))
    declared_hash = str(download.get("hash", ""))

    cached = provenance["cachedFiles"].get(metadata_relative)
    if not isinstance(cached, dict):
        raise VerificationError(f"installer provenance has no entry for {metadata_relative}")
    expected_metadata_hash = {
        "type": manifest["file_hash_format"],
        "value": indexed_hashes[metadata_relative],
    }
    if cached.get("hash") != expected_metadata_hash:
        raise VerificationError(f"stale installer metadata provenance for {metadata_relative}")
    if cached.get("linkedFileHash") != {
        "type": declared_hash_format,
        "value": declared_hash,
    }:
        raise VerificationError(f"stale installer artifact provenance for {metadata_relative}")
    if cached.get("optionValue") is not True:
        raise VerificationError(f"installer disabled source artifact {metadata_relative}")
    cached_location = str(cached.get("cachedLocation", ""))
    cached_posix = _safe_relative_path(cached_location, "cached artifact")
    if cached_posix.name != filename:
        raise VerificationError(
            f"cached artifact filename mismatch for {metadata_relative}: {cached_posix.name} != {filename}"
        )
    jar_path = _verified_regular_file(
        install_path, cached_posix, "source artifact"
    )
    actual_hash = _hash_file(jar_path, declared_hash_format)
    if actual_hash != declared_hash:
        raise VerificationError(
            f"{filename} hash mismatch: expected {declared_hash}, got {actual_hash}"
        )
    return jar_path


def resolve_source_jars(
    root: Path | str, install: Path | str, metadata_relatives: Iterable[str]
) -> dict[str, Path]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    manifest = verify_manifest(root_path)
    provenance = verify_install_provenance(
        root_path, install_path, verify_files=False
    )
    return {
        metadata_relative: _resolve_source_jar(
            root_path,
            install_path,
            metadata_relative,
            manifest,
            provenance,
        )
        for metadata_relative in metadata_relatives
    }


def resolve_source_jar(
    root: Path | str, install: Path | str, metadata_relative: str
) -> Path:
    return resolve_source_jars(root, install, (metadata_relative,))[metadata_relative]


def _enabled_server_metadata(
    root_path: Path, manifest: dict, provenance: dict
) -> tuple[str, ...]:
    enabled: list[str] = []
    for relative in sorted(manifest["indexed_hashes"]):
        if not relative.endswith(".pw.toml"):
            continue
        metadata = _read_toml(root_path / relative)
        if metadata.get("side") not in ("server", "both"):
            continue
        cached = provenance["cachedFiles"].get(relative)
        if isinstance(cached, dict) and cached.get("optionValue") is True:
            enabled.append(relative)
    return tuple(enabled)


class _ClassReader:
    def __init__(self, payload: bytes):
        self.payload = memoryview(payload)
        self.offset = 0

    def read(self, size: int) -> bytes:
        end = self.offset + size
        if size < 0 or end > len(self.payload):
            raise VerificationError("truncated class file")
        value = self.payload[self.offset:end].tobytes()
        self.offset = end
        return value

    def u1(self) -> int:
        return int.from_bytes(self.read(1), "big")

    def u2(self) -> int:
        return int.from_bytes(self.read(2), "big")

    def u4(self) -> int:
        return int.from_bytes(self.read(4), "big")


def _class_utf8(pool: Sequence[object | None], index: int) -> str:
    if not 0 < index < len(pool) or not isinstance(pool[index], str):
        raise VerificationError(f"invalid class UTF-8 constant index {index}")
    return pool[index]


def _annotation_value(reader: _ClassReader, pool: Sequence[object | None]):
    tag = chr(reader.u1())
    if tag in "BCDFIJSZ":
        return (tag, reader.u2())
    if tag == "s":
        return _class_utf8(pool, reader.u2())
    if tag == "e":
        return ("enum", _class_utf8(pool, reader.u2()), _class_utf8(pool, reader.u2()))
    if tag == "c":
        return ("class", _class_utf8(pool, reader.u2()))
    if tag == "@":
        return _annotation(reader, pool)
    if tag == "[":
        return tuple(_annotation_value(reader, pool) for _ in range(reader.u2()))
    raise VerificationError(f"unsupported annotation value tag {tag!r}")


def _annotation(
    reader: _ClassReader, pool: Sequence[object | None]
) -> tuple[str, dict[str, object]]:
    descriptor = _class_utf8(pool, reader.u2())
    values = {
        _class_utf8(pool, reader.u2()): _annotation_value(reader, pool)
        for _ in range(reader.u2())
    }
    return descriptor, values


def _skip_class_attributes(reader: _ClassReader) -> None:
    for _ in range(reader.u2()):
        reader.read(6)
        for _ in range(reader.u2()):
            reader.read(2)
            reader.read(reader.u4())


def _class_annotations(payload: bytes) -> dict[str, dict[str, object]]:
    reader = _ClassReader(payload)
    if reader.u4() != 0xCAFEBABE:
        raise VerificationError("invalid class file magic")
    reader.read(4)
    pool_count = reader.u2()
    pool: list[object | None] = [None] * pool_count
    index = 1
    while index < pool_count:
        tag = reader.u1()
        if tag == 1:
            try:
                pool[index] = reader.read(reader.u2()).decode("utf-8")
            except UnicodeDecodeError as error:
                raise VerificationError("invalid class UTF-8 constant") from error
        elif tag in (3, 4):
            reader.read(4)
        elif tag in (5, 6):
            reader.read(8)
            index += 1
        elif tag in (7, 8, 16, 19, 20):
            reader.read(2)
        elif tag in (9, 10, 11, 12, 17, 18):
            reader.read(4)
        elif tag == 15:
            reader.read(3)
        else:
            raise VerificationError(f"unsupported class constant tag {tag}")
        index += 1

    reader.read(6)
    reader.read(2 * reader.u2())
    _skip_class_attributes(reader)
    _skip_class_attributes(reader)
    annotations: dict[str, dict[str, object]] = {}
    for _ in range(reader.u2()):
        name = _class_utf8(pool, reader.u2())
        attribute = _ClassReader(reader.read(reader.u4()))
        if name not in ("RuntimeVisibleAnnotations", "RuntimeInvisibleAnnotations"):
            continue
        for _ in range(attribute.u2()):
            descriptor, values = _annotation(attribute, pool)
            annotations[descriptor] = values
        if attribute.offset != len(attribute.payload):
            raise VerificationError(f"unparsed class annotation bytes in {name}")
    return annotations


def _normalize_mixin_target(target: str) -> str:
    if not target or target != target.strip():
        raise VerificationError(f"invalid Mixin target {target!r}")
    if target.startswith("L") or target.endswith(";"):
        if not target.startswith("L") or not target.endswith(";"):
            raise VerificationError(f"malformed Mixin target descriptor {target!r}")
        internal = target[1:-1]
    elif "/" in target:
        if "." in target:
            raise VerificationError(f"mixed Mixin target notation {target!r}")
        internal = target
    else:
        internal = target.replace(".", "/")
    segment = r"[A-Za-z_$][A-Za-z0-9_$]*"
    if re.fullmatch(rf"{segment}(?:/{segment})*", internal) is None:
        raise VerificationError(f"invalid Mixin target class name {target!r}")
    return f"L{internal};"


def _mixin_targets(payload: bytes) -> tuple[bool, bool, str, tuple[str, ...]]:
    annotations = _class_annotations(payload)
    pseudo = "Lorg/spongepowered/asm/mixin/Pseudo;" in annotations
    mixin = annotations.get("Lorg/spongepowered/asm/mixin/Mixin;")
    if mixin is None:
        return pseudo, False, "none", ()
    has_value = "value" in mixin
    has_targets = "targets" in mixin
    if has_value == has_targets:
        raise VerificationError(
            "Mixin annotation must declare exactly one of value or targets"
        )
    if has_value:
        declaration = mixin["value"]
        form = "value"
        if not isinstance(declaration, tuple) or not declaration:
            raise VerificationError("Mixin value annotation is not a non-empty array")
        raw_targets = []
        for value in declaration:
            if (
                not isinstance(value, tuple)
                or len(value) != 2
                or value[0] != "class"
                or not isinstance(value[1], str)
            ):
                raise VerificationError("Mixin value contains a non-class target")
            raw_targets.append(value[1])
    else:
        declaration = mixin["targets"]
        form = "targets"
        if not isinstance(declaration, tuple) or not declaration:
            raise VerificationError("Mixin targets annotation is not a non-empty array")
        if not all(isinstance(value, str) for value in declaration):
            raise VerificationError("Mixin targets contains a non-string target")
        raw_targets = list(declaration)
    targets = tuple(_normalize_mixin_target(target) for target in raw_targets)
    return pseudo, True, form, targets


def _manifest_attributes(payload: bytes) -> dict[str, str]:
    try:
        lines = payload.decode("utf-8").replace("\r\n", "\n").split("\n")
    except UnicodeDecodeError as error:
        raise VerificationError("invalid JAR manifest encoding") from error
    unfolded: list[str] = []
    for line in lines:
        if line.startswith(" ") and unfolded:
            unfolded[-1] += line[1:]
        else:
            unfolded.append(line)
    return {
        key.strip(): value.strip()
        for line in unfolded
        if ":" in line
        for key, value in (line.split(":", 1),)
    }


def _declared_mixin_configs(archive: zipfile.ZipFile, names: set[str]) -> tuple[str, ...]:
    configs: set[str] = set()
    for metadata_resource in ("META-INF/neoforge.mods.toml", "META-INF/mods.toml"):
        if metadata_resource not in names:
            continue
        try:
            metadata = tomllib.loads(archive.read(metadata_resource).decode("utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise VerificationError(
                f"cannot parse mixin declarations in {metadata_resource}: {error}"
            ) from error
        declarations = metadata.get("mixins", [])
        if isinstance(declarations, list):
            for declaration in declarations:
                if isinstance(declaration, dict) and isinstance(
                    declaration.get("config"), str
                ):
                    configs.add(declaration["config"])

    if "fabric.mod.json" in names:
        try:
            metadata = json.loads(archive.read("fabric.mod.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError(f"cannot parse fabric.mod.json: {error}") from error
        declarations = metadata.get("mixins", []) if isinstance(metadata, dict) else []
        if isinstance(declarations, list):
            for declaration in declarations:
                if isinstance(declaration, str):
                    configs.add(declaration)
                elif isinstance(declaration, dict):
                    environment = declaration.get("environment", "*")
                    config = declaration.get("config")
                    if environment != "client" and isinstance(config, str):
                        configs.add(config)

    if "quilt.mod.json" in names:
        try:
            metadata = json.loads(archive.read("quilt.mod.json"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise VerificationError(f"cannot parse quilt.mod.json: {error}") from error
        loader = metadata.get("quilt_loader", {}) if isinstance(metadata, dict) else {}
        mixins = loader.get("mixin", []) if isinstance(loader, dict) else []
        if isinstance(mixins, str):
            configs.add(mixins)
        elif isinstance(mixins, list):
            configs.update(config for config in mixins if isinstance(config, str))

    if "META-INF/MANIFEST.MF" in names:
        attributes = _manifest_attributes(archive.read("META-INF/MANIFEST.MF"))
        declared = attributes.get("MixinConfigs", "")
        configs.update(config.strip() for config in declared.split(",") if config.strip())
    return tuple(sorted(configs))


def _client_target_classification(target: str) -> str | None:
    if not target.startswith("L") or not target.endswith(";"):
        return None
    internal = target[1:-1]
    parts = internal.split("/")
    simple_name = parts[-1].split("$", 1)[0]
    package_parts = tuple(part.lower() for part in parts[:-1])
    if internal.startswith("net/minecraft/client/"):
        return "minecraft-client-package"
    if internal.startswith("net/neoforged/neoforge/client/"):
        return "neoforge-client-package"
    if internal.startswith("net/caffeinemc/mods/sodium/client/"):
        return "sodium-client-package"
    if internal.startswith("com/simibubi/create/") and (
        "client" in package_parts
        or "render" in package_parts
        or "renderer" in package_parts
        or simple_name.endswith(("Client", "Renderer"))
    ):
        return "create-client-class"
    if "screen" in package_parts:
        return "mod-screen-package"
    if "gui" in package_parts:
        return "mod-gui-package"
    if "jei" in package_parts:
        return "jei-integration-package"
    if "client" in package_parts:
        return "mod-client-package"
    if "render" in package_parts or "renderer" in package_parts:
        return "mod-render-package"
    if simple_name.endswith("Client"):
        return "client-class-suffix"
    if simple_name.endswith("Renderer"):
        return "renderer-class-suffix"
    return None


def _finalize_client_target_inventory(
    scan: dict[str, object],
) -> tuple[tuple[object, ...], ...]:
    candidates = scan.get("client_target_candidates")
    evidence_map = scan.get("client_target_class_evidence")
    if not isinstance(candidates, list) or not isinstance(evidence_map, dict):
        raise VerificationError("invalid client target inventory accumulator")
    inventory = []
    for candidate in candidates:
        target = candidate[-1]
        if not isinstance(target, str) or not target.startswith("L") or not target.endswith(";"):
            raise VerificationError("invalid client target descriptor")
        resource = f"{target[1:-1]}.class"
        evidence = tuple(sorted(evidence_map.get(resource, ())))
        if not evidence:
            evidence = (("absent-from-server-artifact-corpus", resource, ""),)
        inventory.append((*candidate, evidence))
    return tuple(inventory)


def _zip_member_alias_identity(info: zipfile.ZipInfo) -> tuple[object, ...]:
    return (
        info.filename,
        info.orig_filename,
        info.date_time,
        info.compress_type,
        info.comment,
        info.extra,
        info.create_system,
        info.create_version,
        info.extract_version,
        info.reserved,
        info.flag_bits,
        info.volume,
        info.internal_attr,
        info.external_attr,
        info.header_offset,
        info.CRC,
        info.compress_size,
        info.file_size,
    )


def _read_reviewed_zip_alias(
    archive: zipfile.ZipFile,
    infos: tuple[zipfile.ZipInfo, ...],
    member_infos: list[zipfile.ZipInfo],
    label: str,
    name: str,
) -> bytes:
    header_offset = infos[0].header_offset
    physical_end = min(
        (
            info.header_offset
            for info in member_infos
            if info.header_offset > header_offset
        ),
        default=archive.start_dir,
    )
    end_offsets = tuple(getattr(info, "_end_offset", None) for info in infos)
    if all(end_offset is None for end_offset in end_offsets):
        return archive.read(infos[0])
    candidates = tuple(
        info
        for info, end_offset in zip(infos, end_offsets, strict=True)
        if end_offset == physical_end
    )
    if len(candidates) != 1:
        raise VerificationError(
            "duplicate ZIP member has no unique physical boundary: "
            f"{label}!/{name} header={header_offset} end={physical_end} "
            f"candidates={len(candidates)}"
        )
    return archive.read(candidates[0])


def _scan_mixin_archive(
    label: str,
    payload: Path | bytes,
    result: dict[str, object],
    nested_queue: list[tuple[str, Path | bytes]] | None = None,
) -> None:
    try:
        archive_sha256 = (
            _hash_file(payload, "sha256")
            if isinstance(payload, Path)
            else _hash_bytes(payload, "sha256")
        )
        corpus_entries = result["mixin_corpus_entries"]
        if not isinstance(corpus_entries, list):
            raise VerificationError("invalid mixin corpus accumulator")
        corpus_entries.append(("archive", label, archive_sha256))
        archive_source = payload if isinstance(payload, Path) else io.BytesIO(payload)
        with zipfile.ZipFile(archive_source) as archive:
            member_infos = archive.infolist()
            member_counts = Counter(info.filename for info in member_infos)
            for name, count in sorted(member_counts.items()):
                if count == 1:
                    continue
                infos = tuple(info for info in member_infos if info.filename == name)
                reviewed = REVIEWED_DUPLICATE_ZIP_MEMBERS.get((label, name))
                if reviewed is None or reviewed[0] != count:
                    raise VerificationError(
                        "duplicate ZIP member is not an exact reviewed third-party "
                        f"exception: {label}!/{name} count={count}"
                    )
                identities = {_zip_member_alias_identity(info) for info in infos}
                if len(identities) != 1:
                    raise VerificationError(
                        "duplicate ZIP member metadata differs across reviewed aliases: "
                        f"{label}!/{name} count={count}"
                    )
                payload_hash = _hash_bytes(
                    _read_reviewed_zip_alias(
                        archive, infos, member_infos, label, name
                    ),
                    "sha256",
                )
                if payload_hash != reviewed[1]:
                    raise VerificationError(
                        "duplicate ZIP member is not an exact reviewed third-party "
                        f"exception: {label}!/{name} count={count} "
                        f"hash={payload_hash}"
                    )
            names = set(member_counts)
            result["archive_scopes"] = int(result["archive_scopes"]) + 1
            class_evidence = result.get("client_target_class_evidence")
            if not isinstance(class_evidence, dict):
                raise VerificationError("invalid client target class evidence accumulator")
            for name in sorted(names):
                if not name.endswith(".class"):
                    continue
                descriptor = f"L{name[:-6]};"
                if _client_target_classification(descriptor) is None:
                    continue
                class_evidence.setdefault(name, []).append(
                    (label, name, _hash_bytes(archive.read(name), "sha256"))
                )
            for resource in _declared_mixin_configs(archive, names):
                if resource not in names:
                    raise VerificationError(
                        f"declared mixin config is missing: {label}!/{resource}"
                    )
                try:
                    config_payload = archive.read(resource)
                    config = json.loads(config_payload)
                except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as error:
                    raise VerificationError(
                        f"cannot parse declared mixin config {label}!/{resource}: {error}"
                    ) from error
                if not isinstance(config, dict) or not isinstance(config.get("package"), str):
                    continue
                listed = [config.get(key) for key in ("mixins", "client", "server")]
                if not any(isinstance(entries, list) for entries in listed):
                    continue
                config_hashes = result["mixin_config_hashes"]
                if not isinstance(config_hashes, dict):
                    raise VerificationError("invalid mixin config hash accumulator")
                config_hash = _hash_bytes(config_payload, "sha256")
                identity = (label, resource)
                prior_hash = config_hashes.get(identity)
                if prior_hash is not None:
                    if prior_hash != config_hash:
                        raise VerificationError(
                            "conflicting mixin config bytes for authenticated identity "
                            f"{label}!/{resource}: {prior_hash} != {config_hash}"
                        )
                    continue
                config_hashes[identity] = config_hash
                corpus_entries.append(("config", label, resource, config_hash))
                result["mixin_configs"] = int(result["mixin_configs"]) + 1
                package = config["package"].replace(".", "/")
                for list_key, counter_key in (
                    ("mixins", "common_mixins"),
                    ("server", "server_mixins"),
                ):
                    entries = config.get(list_key, [])
                    if not isinstance(entries, list):
                        raise VerificationError(
                            f"invalid {list_key} mixin list in {label}!/{resource}"
                        )
                    for position, mixin_name in enumerate(entries):
                        if not isinstance(mixin_name, str):
                            raise VerificationError(
                                f"invalid {list_key} mixin entry in {label}!/{resource}"
                            )
                        result[counter_key] = int(result[counter_key]) + 1
                        class_resource = (
                            f"{package}/{mixin_name.replace('.', '/')}.class"
                        )
                        if class_resource not in names:
                            raise VerificationError(
                                "missing dedicated-server mixin class "
                                f"{label}!/{class_resource}"
                            )
                        class_payload = archive.read(class_resource)
                        pseudo, has_mixin, target_form, targets = _mixin_targets(
                            class_payload
                        )
                        class_hash = _hash_bytes(class_payload, "sha256")
                        corpus_entries.append(
                            (
                                "mixin",
                                label,
                                resource,
                                list_key,
                                position,
                                mixin_name,
                                class_resource,
                                class_hash,
                                pseudo,
                                has_mixin,
                                target_form,
                                targets,
                            )
                        )
                        client_targets = result["client_target_candidates"]
                        if not isinstance(client_targets, list):
                            raise VerificationError("invalid client target accumulator")
                        for target in targets:
                            classification = _client_target_classification(target)
                            if classification is None:
                                continue
                            client_targets.append(
                                (
                                    label,
                                    resource,
                                    list_key,
                                    position,
                                    mixin_name,
                                    class_resource,
                                    class_hash,
                                    target_form,
                                    targets,
                                    classification,
                                    target,
                                )
                            )
                        if has_mixin and (
                            "Lnet/minecraft/client/multiplayer/ClientLevel;" in targets
                        ):
                            result["annotation_clientlevel_mixins"] = (
                                int(result["annotation_clientlevel_mixins"]) + 1
                            )
                            if pseudo:
                                candidates = result["pseudo_clientlevel_candidates"]
                                if not isinstance(candidates, list):
                                    raise VerificationError(
                                        "invalid candidate accumulator"
                                    )
                                candidates.append(
                                    (
                                        label,
                                        resource,
                                        mixin_name,
                                        class_resource,
                                        class_hash,
                                        target_form,
                                        targets,
                                    )
                                )
            for nested in sorted(name for name in names if name.lower().endswith(".jar")):
                try:
                    nested_payload = archive.read(nested)
                    if zipfile.is_zipfile(io.BytesIO(nested_payload)):
                        nested_scope = (f"{label}!/{nested}", nested_payload)
                        if nested_queue is None:
                            _scan_mixin_archive(*nested_scope, result)
                        else:
                            nested_queue.append(nested_scope)
                except KeyError as error:
                    raise VerificationError(
                        f"cannot read nested archive {label}!/{nested}: {error}"
                    ) from error
    except (OSError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot scan mixin archive {label}: {error}") from error


def verify_sable_source_evidence(root: Path | str, install: Path | str) -> dict:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    manifest = verify_manifest(root_path)
    provenance = verify_install_provenance(
        root_path, install_path, verify_files=False
    )
    metadata_relatives = _enabled_server_metadata(root_path, manifest, provenance)
    if len(metadata_relatives) != SABLE_ENABLED_METADATA_COUNT:
        raise VerificationError(
            "enabled server metadata count changed: "
            f"expected {SABLE_ENABLED_METADATA_COUNT}, got {len(metadata_relatives)}"
        )
    resolved = {
        relative: _resolve_source_jar(
            root_path, install_path, relative, manifest, provenance
        )
        for relative in metadata_relatives
    }
    provenance["afterlightServerArtifacts"] = _server_artifact_evidence(
        metadata_relatives, resolved, provenance
    )
    verify_reviewed_server_artifact_inventory(provenance)
    unique_archives: dict[Path, str] = {}
    for relative, archive_path in resolved.items():
        unique_archives.setdefault(archive_path.resolve(), relative)
    if len(unique_archives) != SABLE_TOP_LEVEL_ARTIFACT_COUNT:
        raise VerificationError(
            "top-level server artifact count changed: "
            f"expected {SABLE_TOP_LEVEL_ARTIFACT_COUNT}, got {len(unique_archives)}"
        )

    sable_path = resolved[SABLE_METADATA]
    sable_hash = _hash_file(sable_path, "sha256")
    if sable_hash != SABLE_ARTIFACT_SHA256:
        raise VerificationError(
            f"Sable artifact hash mismatch: expected {SABLE_ARTIFACT_SHA256}, got {sable_hash}"
        )
    try:
        with zipfile.ZipFile(sable_path) as archive:
            mixin_payload = archive.read(SABLE_MIXIN_CONFIG)
            mixin_config = json.loads(mixin_payload)
            class_payloads = {
                mixin_name: archive.read(resource)
                for mixin_name, (_, resource, _) in SABLE_MIXIN_CLASSES.items()
            }
    except (OSError, KeyError, json.JSONDecodeError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot read Sable source evidence: {error}") from error
    mixin_config_hash = _hash_bytes(mixin_payload, "sha256")
    if mixin_config_hash != SABLE_MIXIN_CONFIG_SHA256:
        raise VerificationError(
            "Sable mixin config hash mismatch: "
            f"expected {SABLE_MIXIN_CONFIG_SHA256}, got {mixin_config_hash}"
        )
    common_mixins = mixin_config.get("mixins")
    client_mixins = mixin_config.get("client")
    if not isinstance(common_mixins, list) or not isinstance(client_mixins, list):
        raise VerificationError("Sable mixin config has invalid common or client lists")

    class_hashes: dict[str, str] = {}
    expected_candidates = []
    expected_targets = (
        "Lnet/minecraft/server/level/ServerLevel;",
        "Lnet/minecraft/client/multiplayer/ClientLevel;",
    )
    for mixin_name, (position, resource, expected_hash) in SABLE_MIXIN_CLASSES.items():
        if position >= len(common_mixins) or common_mixins[position] != mixin_name:
            raise VerificationError(
                f"Sable common mixin position changed for {mixin_name} at index {position}"
            )
        if mixin_name in client_mixins:
            raise VerificationError(f"Sable source mixin moved to client list: {mixin_name}")
        payload = class_payloads[mixin_name]
        actual_hash = _hash_bytes(payload, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"Sable mixin class hash mismatch for {resource}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        pseudo, has_mixin, target_form, targets = _mixin_targets(payload)
        if (
            not pseudo
            or not has_mixin
            or target_form != "value"
            or targets != expected_targets
        ):
            raise VerificationError(
                "Sable mixin annotations changed for "
                f"{resource}: pseudo={pseudo}, form={target_form}, targets={targets}"
            )
        class_hashes[resource] = actual_hash
        expected_candidates.append(
            (
                SABLE_METADATA,
                SABLE_MIXIN_CONFIG,
                mixin_name,
                resource,
                actual_hash,
                target_form,
                targets,
            )
        )

    runtime_hashes: dict[str, str] = {}
    for relative, expected_hash in SABLE_RUNTIME_SHA256.items():
        runtime_path = _verified_regular_file(
            install_path,
            _safe_relative_path(relative, "Sable runtime evidence"),
            "Sable runtime evidence",
        )
        actual_hash = _hash_file(runtime_path, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"Sable runtime hash mismatch for {relative}: "
                f"expected {expected_hash}, got {actual_hash}"
            )
        runtime_hashes[relative] = actual_hash

    scan: dict[str, object] = {
        "archive_scopes": 0,
        "mixin_configs": 0,
        "common_mixins": 0,
        "server_mixins": 0,
        "annotation_clientlevel_mixins": 0,
        "pseudo_clientlevel_candidates": [],
        "mixin_config_hashes": {},
        "mixin_corpus_entries": [],
        "client_target_candidates": [],
        "client_target_class_evidence": {},
    }
    archive_queue: list[tuple[str, Path | bytes]] = [
        (metadata_relative, archive_path)
        for archive_path, metadata_relative in sorted(
            unique_archives.items(), key=lambda item: item[1]
        )
    ]
    queue_index = 0
    while queue_index < len(archive_queue):
        label, payload = archive_queue[queue_index]
        queue_index += 1
        _scan_mixin_archive(label, payload, scan, archive_queue)
    expected_counts = {
        "archive_scopes": SABLE_ARCHIVE_SCOPE_COUNT,
        "mixin_configs": SABLE_MIXIN_CONFIG_COUNT,
        "common_mixins": SABLE_COMMON_MIXIN_COUNT,
        "server_mixins": SABLE_SERVER_MIXIN_COUNT,
        "annotation_clientlevel_mixins": SABLE_ANNOTATION_CLIENTLEVEL_MIXIN_COUNT,
    }
    for key, expected in expected_counts.items():
        actual = int(scan[key])
        if actual != expected:
            raise VerificationError(
                f"Sable exhaustive {key} count changed: expected {expected}, got {actual}"
            )
    candidates = tuple(scan["pseudo_clientlevel_candidates"])
    if candidates != tuple(expected_candidates):
        raise VerificationError(
            "Sable exhaustive @Pseudo ClientLevel candidate set changed: "
            f"expected {tuple(expected_candidates)}, got {candidates}"
        )
    corpus_entries = tuple(scan["mixin_corpus_entries"])
    corpus_digest = _hash_bytes(
        json.dumps(
            corpus_entries,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        "sha256",
    )
    if corpus_digest != REVIEWED_MIXIN_CORPUS_SHA256:
        raise VerificationError(
            "Sable exhaustive mixin corpus digest changed: "
            f"expected {REVIEWED_MIXIN_CORPUS_SHA256}, got {corpus_digest}"
        )
    client_targets = _finalize_client_target_inventory(scan)
    client_target_digest = _hash_bytes(
        json.dumps(
            client_targets,
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        "sha256",
    )
    target_descriptors = tuple(candidate[-2] for candidate in client_targets)
    expected_client_target_summary = (
        REVIEWED_CLIENT_TARGET_COUNT,
        REVIEWED_CLIENT_TARGET_INVENTORY_SHA256,
        REVIEWED_CLIENT_TARGETS,
    )
    actual_client_target_summary = (
        len(client_targets),
        client_target_digest,
        target_descriptors,
    )
    if actual_client_target_summary != expected_client_target_summary:
        raise VerificationError(
            "Sable exhaustive client target inventory changed: "
            f"expected={expected_client_target_summary} "
            f"actual={actual_client_target_summary}"
        )

    return {
        "artifact_sha256": sable_hash,
        "mixin_config_sha256": mixin_config_hash,
        "mixin_class_sha256": class_hashes,
        "runtime_sha256": runtime_hashes,
        "enabled_metadata": len(metadata_relatives),
        "top_level_artifacts": len(unique_archives),
        "archive_scopes": int(scan["archive_scopes"]),
        "mixin_configs": int(scan["mixin_configs"]),
        "common_mixins": int(scan["common_mixins"]),
        "server_mixins": int(scan["server_mixins"]),
        "annotation_clientlevel_mixins": int(
            scan["annotation_clientlevel_mixins"]
        ),
        "pseudo_clientlevel_candidates": candidates,
        "mixin_corpus_count": len(corpus_entries),
        "mixin_corpus_sha256": corpus_digest,
        "client_target_candidates": client_targets,
        "client_target_count": len(client_targets),
        "client_target_sha256": client_target_digest,
        "mixin_config_identities": tuple(
            (label, resource, config_hash)
            for (label, resource), config_hash in sorted(
                scan["mixin_config_hashes"].items()
            )
        ),
    }


def verify_idas_compat_source_evidence(root: Path | str, install: Path | str) -> dict:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    metadata = _read_toml(root_path / IDAS_COMPAT_METADATA)
    if metadata.get("filename") != IDAS_COMPAT_FILENAME:
        raise VerificationError("IDAS compat filename changed")
    if metadata.get("side") != "both":
        raise VerificationError("IDAS compat side must remain both")
    download = metadata.get("download")
    if not isinstance(download, dict):
        raise VerificationError("IDAS compat metadata has no download table")
    expected_download = {
        "url": IDAS_COMPAT_URL,
        "hash-format": "sha512",
        "hash": IDAS_COMPAT_SHA512,
    }
    if download != expected_download:
        raise VerificationError(
            f"IDAS compat download provenance changed: {download}"
        )

    artifact = resolve_source_jar(root_path, install_path, IDAS_COMPAT_METADATA)
    artifact_size = artifact.stat().st_size
    if artifact_size != IDAS_COMPAT_SIZE:
        raise VerificationError(
            "IDAS compat artifact size mismatch: "
            f"expected {IDAS_COMPAT_SIZE}, got {artifact_size}"
        )
    artifact_sha256 = _hash_file(artifact, "sha256")
    if artifact_sha256 != IDAS_COMPAT_SHA256:
        raise VerificationError(
            "IDAS compat artifact SHA-256 mismatch: "
            f"expected {IDAS_COMPAT_SHA256}, got {artifact_sha256}"
        )
    try:
        with zipfile.ZipFile(artifact) as archive:
            names = {
                entry.filename for entry in archive.infolist() if not entry.is_dir()
            }
            forbidden = sorted(
                name
                for name in names
                if name.endswith(".nbt")
                or name.startswith("data/idas/")
                or name.lower().endswith(".jar")
            )
            if forbidden:
                raise VerificationError(
                    f"IDAS compat artifact contains forbidden payloads: {forbidden}"
                )
            expected_names = set(IDAS_COMPAT_RESOURCE_SHA256)
            if names != expected_names:
                raise VerificationError(
                    "IDAS compat artifact file set changed: "
                    f"expected {sorted(expected_names)}, got {sorted(names)}"
                )
            resources = {
                resource: archive.read(resource)
                for resource in IDAS_COMPAT_RESOURCE_SHA256
            }
    except (OSError, KeyError, zipfile.BadZipFile) as error:
        raise VerificationError(f"cannot inspect IDAS compat artifact: {error}") from error

    resource_hashes = {
        resource: _hash_bytes(payload, "sha256")
        for resource, payload in resources.items()
    }
    if resource_hashes != IDAS_COMPAT_RESOURCE_SHA256:
        raise VerificationError(
            f"IDAS compat resource hashes changed: {resource_hashes}"
        )
    try:
        mixin_config = json.loads(resources["afterlight_idas_compat.mixins.json"])
        provenance = json.loads(
            resources["META-INF/afterlight-provenance.json"]
        )
        mod_metadata = tomllib.loads(
            resources["META-INF/neoforge.mods.toml"].decode("utf-8")
        )
    except (UnicodeDecodeError, json.JSONDecodeError, tomllib.TOMLDecodeError) as error:
        raise VerificationError(f"cannot parse IDAS compat metadata: {error}") from error
    if mixin_config.get("package") != "dev.afterlight.idascompat.mixin":
        raise VerificationError("IDAS compat mixin package changed")
    if mixin_config.get("mixins") != [
        "StructureTemplateAccessor",
        "StructureTemplateManagerMixin",
    ]:
        raise VerificationError("IDAS compat mixin set changed")
    if "client" in mixin_config:
        raise VerificationError("IDAS compat gained a client-only mixin list")
    expected_provenance = {
        "schema": 3,
        "sourceTreeDigestSchema": 2,
        "sourceRepository": (
            "https://github.com/Luskish/afterlight-idas-compat"
        ),
        "sourceCommit": IDAS_COMPAT_SOURCE_COMMIT,
        "sourceTreeSha256": IDAS_COMPAT_SOURCE_TREE_SHA256,
        "releaseBuild": True,
        "version": IDAS_COMPAT_VERSION,
        "idasArtifactSha256": (
            "7f5031dd90ae0b32d7fe5c6c47c877cac1eb95a178bc78d196cb24c17ce82522"
        ),
        "reviewedTemplates": IDAS_COMPAT_REVIEWED_TEMPLATES,
    }
    if provenance != expected_provenance:
        raise VerificationError(
            f"IDAS compat embedded source provenance changed: {provenance}"
        )
    mods = mod_metadata.get("mods")
    if not isinstance(mods, list) or len(mods) != 1:
        raise VerificationError("IDAS compat mod metadata shape changed")
    if mods[0].get("modId") != "afterlight_idas_compat" or mods[0].get(
        "version"
    ) != IDAS_COMPAT_VERSION:
        raise VerificationError("IDAS compat mod identity changed")
    dependencies = mod_metadata.get("dependencies", {}).get(
        "afterlight_idas_compat", []
    )
    idas_dependencies = [
        dependency
        for dependency in dependencies
        if isinstance(dependency, dict) and dependency.get("modId") == "idas"
    ]
    if idas_dependencies != [
        {
            "modId": "idas",
            "type": "optional",
            "versionRange": "[1.13.7+1.21.1-neoforge]",
            "ordering": "AFTER",
            "side": "BOTH",
        }
    ]:
        raise VerificationError("IDAS compat IDAS dependency pin changed")
    return {
        "artifact_size": artifact_size,
        "artifact_sha256": artifact_sha256,
        "artifact_sha512": IDAS_COMPAT_SHA512,
        "resource_sha256": resource_hashes,
        "source_commit": provenance["sourceCommit"],
        "source_tree_sha256": provenance["sourceTreeSha256"],
        "release_build": provenance["releaseBuild"],
        "reviewed_templates": provenance["reviewedTemplates"],
    }


def _strip_boundary_ansi(raw_line: str, line_number: int) -> str:
    if "\x1b" not in raw_line:
        return raw_line
    line = raw_line
    while True:
        prefix = SGR_ESCAPE.match(line)
        if prefix is None:
            break
        line = line[prefix.end() :]
    suffix = re.search(r"(?:\x1b\[[0-9;]*m)+$", line)
    if suffix is not None:
        line = line[: suffix.start()]
    if "\x1b" in line:
        raise VerificationError(
            f"unsupported interior ANSI escape in log line {line_number}"
        )
    return line


def parse_log_records(log_text: str) -> tuple[LogRecord, ...]:
    records: list[LogRecord] = []
    current_match: re.Match[str] | None = None
    current_lines: list[str] = []

    def finish_record() -> None:
        nonlocal current_match, current_lines
        if current_match is None:
            return
        records.append(
            LogRecord(
                timestamp=current_match.group("timestamp"),
                thread=current_match.group("thread"),
                level=current_match.group("level"),
                logger=current_match.group("logger"),
                message=current_match.group("message"),
                continuations=tuple(current_lines[1:]),
                text="\n".join(current_lines),
            )
        )

    for line_number, raw_line in enumerate(log_text.splitlines(), start=1):
        line = _strip_boundary_ansi(raw_line, line_number)
        match = LOG_HEADER.match(line)
        if match:
            finish_record()
            current_match = match
            current_lines = [line]
            continue
        if HEADER_LEVEL_LIKE.search(line):
            raise VerificationError(
                f"malformed or relocated log header at line {line_number}: {line}"
            )
        if current_match is None:
            raise VerificationError(
                f"unattached log line {line_number}: {line}"
            )
        current_lines.append(line)
    finish_record()
    return tuple(records)


def parse_console_records(console_text: str) -> tuple[LogRecord, ...]:
    records: list[LogRecord] = []
    current_match: re.Match[str] | None = None
    current_lines: list[str] = []

    def finish_record() -> None:
        nonlocal current_match, current_lines
        if current_match is None:
            return
        records.append(
            LogRecord(
                timestamp=current_match.group("timestamp"),
                thread=current_match.group("thread"),
                level=current_match.group("level"),
                logger=current_match.group("logger"),
                message=current_match.group("message"),
                continuations=tuple(current_lines[1:]),
                text="\n".join(current_lines),
            )
        )

    logical_lines: list[tuple[int, str]] = []
    for physical_number, raw_line in enumerate(console_text.splitlines(), start=1):
        without_sgr = SGR_ESCAPE.sub("", raw_line)
        if "\x1b" in without_sgr:
            raise VerificationError(
                f"unsupported ANSI escape in console line {physical_number}"
            )
        pieces = re.sub(
            r"(?<!^)(?=\[\d{2}:\d{2}:\d{2}(?:\.\d{3})?\] )",
            "\n",
            without_sgr,
        ).splitlines()
        logical_lines.extend((physical_number, piece) for piece in pieces)

    for line_number, line in logical_lines:
        match = CONSOLE_HEADER.match(line)
        if match:
            finish_record()
            current_match = match
            current_lines = [line]
            continue
        if HEADER_LEVEL_LIKE.search(line):
            raise VerificationError(
                "malformed or relocated console header at line "
                f"{line_number}: {line}"
            )
        if current_match is None:
            raise VerificationError(
                f"unattached console line {line_number}: {line}"
            )
        current_lines.append(line)
    finish_record()
    return tuple(records)


def _severe_console_projection(
    records: Sequence[LogRecord],
    *,
    console: bool = False,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[tuple[str, str, str, str, tuple[str, ...]], ...]:
    projection = []
    for record in records:
        if record.level not in ("ERROR", "FATAL") and not SEVERE_OUTPUT_LIKE.search(
            "\n".join((record.message, *record.continuations))
        ):
            continue
        canonical = canonical_record_tuple(
            record,
            workspace_root=workspace_root,
            install_root=install_root,
        )
        continuations = []
        for line in canonical[4]:
            normalized_line = line.rstrip(" ")
            if console and normalized_line == CONSOLE_ATTACHED_NOISE:
                continue
            if console:
                normalized_line = re.sub(r" \{[^{}]*\}$", "", normalized_line)
            continuations.append(normalized_line)
        canonical = (
            canonical[0],
            canonical[1],
            CONSOLE_LOGGER_CANONICAL.get(canonical[2], canonical[2]),
            canonical[3].rstrip(" "),
            tuple(continuations),
        )
        projection.append(canonical)
    return tuple(projection)


def _validate_console_projection(
    console_records: Sequence[LogRecord],
    latest_records: Sequence[LogRecord],
    debug_records: Sequence[LogRecord],
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[str, int]:
    console_projection = _severe_console_projection(
        console_records,
        console=True,
        workspace_root=workspace_root,
        install_root=install_root,
    )
    latest_projection = _severe_console_projection(
        latest_records,
        workspace_root=workspace_root,
        install_root=install_root,
    )
    debug_projection = _severe_console_projection(
        debug_records,
        workspace_root=workspace_root,
        install_root=install_root,
    )
    latest_payload = json.dumps(
        sorted(Counter(latest_projection).items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    latest_actual = (
        len(latest_projection),
        _hash_bytes(latest_payload, "sha256"),
    )
    latest_expected = (
        REVIEWED_CONSOLE_SEVERE_COUNT,
        REVIEWED_CONSOLE_SEVERE_SHA256,
    )
    if latest_actual != latest_expected:
        raise VerificationError(
            "latest.log severe corpus changed: "
            f"expected={latest_expected} actual={latest_actual}"
        )
    debug_payload = json.dumps(
        sorted(Counter(debug_projection).items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    debug_actual = (
        len(debug_projection),
        _hash_bytes(debug_payload, "sha256"),
    )
    debug_expected = (
        REVIEWED_DEBUG_SEVERE_COUNT,
        REVIEWED_DEBUG_SEVERE_SHA256,
    )
    if debug_actual != debug_expected:
        raise VerificationError(
            "debug.log severe corpus changed: "
            f"expected={debug_expected} actual={debug_actual}"
        )
    console_errors = Counter(
        record for record in console_projection if record[1] in ("ERROR", "FATAL")
    )
    latest_errors = Counter(
        record for record in latest_projection if record[1] in ("ERROR", "FATAL")
    )
    if console_errors != latest_errors or Counter(console_projection) - Counter(
        latest_projection
    ):
        raise VerificationError(
            "console severe projection differs from authenticated latest.log records"
        )
    payload = json.dumps(
        sorted(Counter(console_projection).items()),
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    digest = _hash_bytes(payload, "sha256")
    actual = (len(console_projection), digest)
    expected = (
        REVIEWED_CONSOLE_SEVERE_COUNT,
        REVIEWED_CONSOLE_SEVERE_SHA256,
    )
    if actual != expected:
        raise VerificationError(
            f"console severe corpus changed: expected={expected} actual={actual}"
        )
    return digest, len(console_projection)


def _read_strict_utf8(
    root: Path, relative: PurePosixPath, label: str
) -> str:
    path = _verified_regular_file(root, relative, label)
    try:
        return path.read_bytes().decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise VerificationError(f"{label} is not strict UTF-8: {error}") from error
    except OSError as error:
        raise VerificationError(f"cannot read {label} {path}: {error}") from error


def _record_is(
    record: LogRecord, level: str, logger: str, message: str
) -> bool:
    return (
        record.level == level
        and record.logger == logger
        and record.message == message
    )


def _normalized_record_thread(record: LogRecord) -> str:
    if (
        record.logger == "net.neoforged.neoforge.registries.DataMapLoader/"
        and record.level == "WARN"
        and record.message == APOTHIC_WARNING_MESSAGE
        and re.fullmatch(r"Worker-Main-\d+", record.thread)
    ):
        return "Worker-Main-N"
    if record.logger == IDAS_COMPAT_LOGGER:
        if re.fullmatch(r"Worker-Main-\d+", record.thread):
            return "Worker-Main-N"
        if re.fullmatch(r"modloading-worker-\d+", record.thread):
            return "modloading-worker-N"
    if (
        record.logger == "mixin/"
        and record.level == "WARN"
        and record.message in YUNGS_VOLATILE_WORKER_WARNINGS
        and re.fullmatch(r"Worker-Main-\d+", record.thread)
    ):
        return "Worker-Main-N"
    if (
        record.logger == "Supplementaries/"
        and record.level == "WARN"
        and record.message in SUPPLEMENTARIES_VOLATILE_WORKER_WARNINGS
        and re.fullmatch(r"pool-\d+-thread-\d+", record.thread)
    ):
        return re.sub(
            r"(?<=pool-)\d+(?=-thread-)", "N", record.thread, count=1
        )
    return record.thread


def _normalize_absolute_roots(
    value: str,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> str:
    replacements: list[tuple[str, str]] = []

    def add_root(source: str, marker: str) -> None:
        replacements.extend(
            (variant, marker)
            for variant in {
                source,
                quote(source, safe="/:"),
                quote(source, safe=""),
            }
        )

    if install_root is not None:
        add_root(os.path.abspath(os.fspath(install_root)), "<INSTALL>")
    if workspace_root is not None:
        workspace = os.path.abspath(os.fspath(workspace_root))
        add_root(os.path.join(workspace, "server-test"), "<INSTALL>")
        add_root(workspace, "<WORKSPACE>")
    normalized = value
    for source, marker in sorted(
        set(replacements), key=lambda replacement: len(replacement[0]), reverse=True
    ):
        normalized = normalized.replace(source, marker)
    return normalized


def _normalize_continuation_line(
    line: str,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> str:
    normalized = _normalize_absolute_roots(
        line, workspace_root=workspace_root, install_root=install_root
    )
    normalized = re.sub(r"jar%23\d+", "jar%23N", normalized)
    return re.sub(
        r"\$Anonymous\$[0-9a-fA-F]+", "$Anonymous$<ANON>", normalized
    )


def _normalize_record_message(
    record: LogRecord,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> str:
    message = _normalize_absolute_roots(
        record.message,
        workspace_root=workspace_root,
        install_root=install_root,
    )
    if (
        record.level == "WARN"
        and record.logger
        == "net.minecraft.server.packs.VanillaPackResourcesBuilder/"
        and re.fullmatch(
            r"Assets URL 'union:[^'\r\n]+\.jar%23\d+!/(?:assets|data)/"
            r"\.mcassetsroot' uses unexpected schema",
            message,
        )
    ):
        return re.sub(r"(?<=\.jar)%23\d+(?=!/)", "%23N", message, count=1)
    if (
        record.level == "DEBUG"
        and record.logger == "mixin/"
        and re.fullmatch(
            r"Renaming synthetic method .+ to md[0-9a-f]{6}\$[^\r\n]+ "
            r"in [^\r\n]+ from mod [^\r\n]+",
            message,
        )
    ):
        return re.sub(
            r"(?<= to )md[0-9a-f]{6}(?=\$)",
            "md<SESSION>",
            message,
            count=1,
        )
    if (
        record.level == "WARN"
        and record.logger == "com.yanny.aci.manager.ManagedRegistry/"
    ):
        return re.sub(
            r"\$\$Lambda/0x[0-9a-fA-F]+",
            "$$Lambda/0x<ADDR>",
            message,
        )
    if record.level == "WARN" and record.logger == "ModernFix/":
        if re.fullmatch(r"Initial datapack load took \d+\.\d+ s", message):
            return "Initial datapack load took <SECONDS> s"
        if re.fullmatch(
            r"Dedicated server took \d+\.\d+ seconds to load", message
        ):
            return "Dedicated server took <SECONDS> seconds to load"
    return message


def canonical_record_tuple(
    record: LogRecord,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[str, str, str, str, tuple[str, ...]]:
    return (
        _normalized_record_thread(record),
        record.level,
        record.logger,
        _normalize_record_message(
            record,
            workspace_root=workspace_root,
            install_root=install_root,
        ),
        tuple(
            _normalize_continuation_line(
                line,
                workspace_root=workspace_root,
                install_root=install_root,
            )
            for line in record.continuations
        ),
    )


def warning_multiset_evidence(
    records: Sequence[LogRecord],
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[str, int, int]:
    fingerprints = Counter(
        canonical_record_fingerprint(
            record,
            workspace_root=workspace_root,
            install_root=install_root,
        )
        for record in records
        if record.level == "WARN"
    )
    payload = json.dumps(
        sorted(fingerprints.items()),
        separators=(",", ":"),
    ).encode("utf-8")
    return (
        hashlib.sha256(payload).hexdigest(),
        sum(fingerprints.values()),
        len(fingerprints),
    )


def _optional_environment_warning_label(record: LogRecord) -> str | None:
    fields = (
        record.thread,
        record.level,
        record.logger,
        record.message,
        record.continuations,
    )
    return {
        (
            "LanServerPinger #1",
            "WARN",
            "net.minecraft.client.server.LanServerPinger/",
            "LanServerPinger: No route to host",
            (),
        ): "LAN multicast route",
        (
            "spark-async-sampler-worker-thread",
            "WARN",
            "spark/",
            "Timed out waiting for world statistics",
            (),
        ): "Spark startup world statistics timeout",
    }.get(fields)


def _validate_reviewed_warning_multiset(
    records: Sequence[LogRecord],
    label: str,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> Counter[str]:
    optional_counts = Counter(
        optional_label
        for record in records
        if (
            optional_label := _optional_environment_warning_label(record)
        ) is not None
    )
    duplicates = {
        optional_label: count
        for optional_label, count in optional_counts.items()
        if count > 1
    }
    if duplicates:
        raise VerificationError(
            f"{label} optional environmental WARN occurred more than once: "
            f"{duplicates}"
        )
    actual = warning_multiset_evidence(
        tuple(
            record
            for record in records
            if _optional_environment_warning_label(record) is None
        ),
        workspace_root=workspace_root,
        install_root=install_root,
    )
    expected = (
        REVIEWED_WARNING_MULTISET_SHA256,
        REVIEWED_WARNING_TOTAL,
        REVIEWED_WARNING_UNIQUE,
    )
    if actual != expected:
        raise VerificationError(
            f"{label} complete WARN fingerprint multiset changed: "
            f"expected={expected} actual={actual}"
        )
    return optional_counts


def _canonical_fields_tuple(
    thread: str,
    level: str,
    logger: str,
    message: str,
    continuations: Sequence[str] = (),
) -> tuple[str, str, str, str, tuple[str, ...]]:
    return (
        thread,
        level,
        logger,
        message,
        tuple(_normalize_continuation_line(line) for line in continuations),
    )


def _canonical_tuple_sha256(
    canonical: tuple[str, str, str, str, tuple[str, ...]],
) -> str:
    payload = json.dumps(
        canonical, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")
    return _hash_bytes(payload, "sha256")


def canonical_record_fingerprint(
    record: LogRecord,
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> str:
    return _canonical_tuple_sha256(
        canonical_record_tuple(
            record,
            workspace_root=workspace_root,
            install_root=install_root,
        )
    )


def _allowance_fingerprint(allowance: LogAllowance) -> str:
    if allowance.canonical_sha256 is not None:
        if re.fullmatch(r"[0-9a-f]{64}", allowance.canonical_sha256) is None:
            raise VerificationError(
                f"{allowance.label} has an invalid canonical SHA-256"
            )
        return allowance.canonical_sha256
    return _canonical_tuple_sha256(
        _canonical_fields_tuple(
            allowance.thread,
            allowance.level,
            allowance.logger,
            allowance.message,
            allowance.continuations,
        )
    )


def _allowance_matches(record: LogRecord, allowance: LogAllowance) -> bool:
    return (
        record.level == allowance.level
        and record.logger == allowance.logger
        and record.message == allowance.message
        and _normalized_record_thread(record) == allowance.thread
        and canonical_record_fingerprint(record) == _allowance_fingerprint(allowance)
    )


def _normalized_stack_payload(record: LogRecord) -> bytes:
    return "\n".join(
        _normalize_continuation_line(line) for line in record.continuations
    ).encode("utf-8")


def _require_stack_hash(record: LogRecord, expected: str, label: str) -> None:
    actual = _hash_bytes(_normalized_stack_payload(record), "sha256")
    if actual != expected:
        raise VerificationError(
            f"RuntimeDistCleaner {label} normalized stack hash changed: "
            f"expected {expected}, got {actual}"
        )


def _require_single_line(record: LogRecord, label: str) -> None:
    if record.continuations:
        raise VerificationError(f"{label} record gained unreviewed continuation context")


def project_sable_error_requirement() -> LogAllowance:
    return LogAllowance(
        label="RuntimeDistCleaner Sable ClientLevel errors",
        level="ERROR",
        logger="net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
        message=RUNTIME_DIST_CLEANER_MESSAGE,
        count=12,
        thread="main",
    )


def _require_exact_context_record(
    record: LogRecord,
    thread: str,
    level: str,
    logger: str,
    message: str,
    label: str,
) -> None:
    expected = _canonical_fields_tuple(thread, level, logger, message)
    if canonical_record_tuple(record) != expected:
        raise VerificationError(f"RuntimeDistCleaner {label} context changed")


def _unique_record_index(
    records: Sequence[LogRecord],
    level: str,
    logger: str,
    message: str,
    label: str,
) -> int:
    indices = [
        index
        for index, record in enumerate(records)
        if _record_is(record, level, logger, message)
    ]
    if len(indices) != 1:
        raise VerificationError(
            f"RuntimeDistCleaner {label} anchor count changed: expected 1, got {len(indices)}"
        )
    _require_exact_context_record(
        records[indices[0]], "main", level, logger, message, label
    )
    return indices[0]


def _validate_sable_debug_records(
    records: Sequence[LogRecord], requirement: LogAllowance
) -> tuple[int, ...]:
    indices = [
        index
        for index, record in enumerate(records)
        if _allowance_matches(record, requirement)
    ]
    if len(indices) != requirement.count:
        raise VerificationError(
            "RuntimeDistCleaner debug provenance count mismatch: "
            f"expected {requirement.count}, got {len(indices)}"
        )
    for index in indices:
        record = records[index]
        _require_single_line(record, "RuntimeDistCleaner")

    access_logger = "net.neoforged.accesstransformer.AccessTransformer/AXFORM"
    access_field = (
        "Transforming net.minecraft.client.multiplayer.ClientLevel FIELD entityStorage "
        "to access PUBLIC and LEAVE"
    )
    access_method = (
        "Transforming net.minecraft.client.multiplayer.ClientLevel METHOD "
        "getEntities()Lnet/minecraft/world/level/entity/LevelEntityGetter; "
        "to access PUBLIC and LEAVE"
    )
    mixin_load_warning = (
        "Error loading class: net/minecraft/client/multiplayer/ClientLevel "
        f"(java.lang.RuntimeException: {RUNTIME_DIST_CLEANER_MESSAGE})"
    )
    source_mixins = tuple(SABLE_MIXIN_CLASSES)

    for position, index in enumerate(indices[:9]):
        if index < 2 or index + 1 >= len(records):
            raise VerificationError("RuntimeDistCleaner lifecycle context is truncated")
        _require_exact_context_record(
            records[index - 2],
            "main",
            "DEBUG",
            access_logger,
            access_field,
            f"lifecycle record {position + 1} ClientLevel field",
        )
        _require_exact_context_record(
            records[index - 1],
            "main",
            "DEBUG",
            access_logger,
            access_method,
            f"lifecycle record {position + 1} ClientLevel method",
        )
        catching = records[index + 1]
        if not _record_is(catching, "TRACE", "mixin/CATCHING", "Catching"):
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} lost Mixin catch context"
            )
        if catching.thread != "main":
            raise VerificationError(
                f"RuntimeDistCleaner lifecycle record {position + 1} catch thread changed"
            )

    for position, mixin_name in enumerate(source_mixins):
        index = indices[position]
        _require_stack_hash(
            records[index + 1], SABLE_STACK_SHA256["prepare"], f"prepare {mixin_name}"
        )
        segment_end = indices[position + 1]
        expected_marker = (
            "Skipping virtual target net.minecraft.client.multiplayer.ClientLevel for "
            f"sable.mixins.json:{mixin_name} from mod sable"
        )
        markers = [
            record
            for record in records[index + 2 : segment_end]
            if record.logger == "mixin/"
            and record.message.startswith(
                "Skipping virtual target net.minecraft.client.multiplayer.ClientLevel for "
                "sable.mixins.json:"
            )
        ]
        if len(markers) != 1:
            raise VerificationError(
                "RuntimeDistCleaner prepare source context changed for "
                f"{mixin_name}: {[record.message for record in markers]}"
            )
        _require_exact_context_record(
            markers[0],
            "main",
            "DEBUG",
            "mixin/",
            expected_marker,
            f"prepare source {mixin_name}",
        )

    access_logger = "net.neoforged.accesstransformer.AccessTransformer/AXFORM"
    p3_first = _unique_record_index(
        records,
        "TRACE",
        "mixin/",
        "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
        "ServerConnectionListenerMixin$1 to metadata cache",
        "P3 first start",
    )
    p3_second = _unique_record_index(
        records,
        "TRACE",
        "mixin/",
        "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
        "ServerConnectionListenerMixin$2 to metadata cache",
        "P3 second start",
    )
    if p3_second != p3_first + 1:
        raise VerificationError(
            "RuntimeDistCleaner P3 named metadata anchors are no longer adjacent"
        )
    windows = (
        (
            "P1",
            "Added class metadata for dev/ryanhcode/sable/api/command/"
            "SubLevelArgumentType$Info to metadata cache",
            (
                "DEBUG",
                access_logger,
                "Transforming net.minecraft.world.level.pathfinder.NodeEvaluator "
                "FIELD mob to access PUBLIC and LEAVE",
            ),
        ),
        (
            "P2",
            "Added class metadata for dev/ryanhcode/sable/sublevel/entity_collision/"
            "SubLevelEntityCollision$FirstCollisionInfo to metadata cache",
            (
                "TRACE",
                "mixin/",
                "Added class metadata for net/minecraft/BlockUtil$FoundRectangle "
                "to metadata cache",
            ),
        ),
        (
            "P3",
            "Added class metadata for dev/ryanhcode/sable/mixin/udp/"
            "ServerConnectionListenerMixin$2 to metadata cache",
            (
                "DEBUG",
                "net.neoforged.fml.common.asm.RuntimeDistCleaner/DISTXFORM",
                "Removing method: com/simibubi/create/foundation/blockEntity/"
                "CachedRenderBBBlockEntity.getRenderBoundingBox()"
                "Lnet/minecraft/world/phys/AABB;",
            ),
        ),
    )
    for pair, (window_name, start_message, end_identity) in enumerate(windows):
        start_index = _unique_record_index(
            records, "TRACE", "mixin/", start_message, f"{window_name} start"
        )
        end_index = _unique_record_index(
            records, *end_identity, f"{window_name} end"
        )
        validate_index = indices[3 + pair * 2]
        changes_index = indices[4 + pair * 2]
        window_errors = tuple(
            index for index in indices if start_index < index < end_index
        )
        if window_errors != (validate_index, changes_index):
            raise VerificationError(
                f"RuntimeDistCleaner {window_name} source window changed: {window_errors}"
            )
        _require_stack_hash(
            records[validate_index + 1],
            SABLE_STACK_SHA256["validate"],
            f"{window_name} validate {source_mixins[pair]}",
        )
        _require_stack_hash(
            records[changes_index + 1],
            SABLE_STACK_SHA256["validate_changes"],
            f"{window_name} validate changes {source_mixins[pair]}",
        )
        mixin_name = source_mixins[pair]
        for phase_index in (validate_index, changes_index):
            if phase_index + 3 >= len(records):
                raise VerificationError(
                    f"RuntimeDistCleaner validation context is truncated for {mixin_name}"
                )
            _require_exact_context_record(
                records[phase_index + 2],
                "main",
                "WARN",
                "mixin/",
                mixin_load_warning,
                f"validation warning {mixin_name}",
            )
            _require_exact_context_record(
                records[phase_index + 3],
                "main",
                "TRACE",
                "mixin/",
                "Added class metadata for net/minecraft/client/multiplayer/ClientLevel "
                "to metadata cache",
                f"validation metadata {mixin_name}",
            )

    for position, mixin_name in enumerate(source_mixins):
        index = indices[9 + position]
        expected_source = (
            f"Mixing {mixin_name} from sable.mixins.json into "
            "net.minecraft.server.level.ServerLevel"
        )
        if index < 1 or index + 1 >= len(records):
            raise VerificationError(
                f"RuntimeDistCleaner application context is truncated for {mixin_name}"
            )
        _require_exact_context_record(
            records[index - 1],
            "main",
            "DEBUG",
            "mixin/",
            expected_source,
            f"application source {mixin_name}",
        )
        _require_exact_context_record(
            records[index + 1],
            "main",
            "WARN",
            "mixin/",
            mixin_load_warning,
            f"application warning {mixin_name}",
        )
    return tuple(indices)


def _error_fatal_projection(
    records: Sequence[LogRecord],
) -> tuple[tuple[str, str, str, str, tuple[str, ...]], ...]:
    return tuple(
        canonical_record_tuple(record)
        for record in records
        if record.level in ("ERROR", "FATAL")
    )


def _accepted_warning_projection(
    records: Sequence[LogRecord],
    indices: Sequence[int],
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[tuple[str, str, str, str, tuple[str, ...]], ...]:
    return tuple(
        canonical_record_tuple(
            records[index],
            workspace_root=workspace_root,
            install_root=install_root,
        )
        for index in indices
    )


def _validate_canonical_log_pair(
    latest_records: Sequence[LogRecord],
    debug_records: Sequence[LogRecord],
    *,
    workspace_root: Path | str | None = None,
    install_root: Path | str | None = None,
) -> tuple[
    Counter[str],
    Counter[str],
    tuple[int, ...],
    tuple[int, ...],
]:
    error_allowances = project_error_allowances() + (
        project_sable_error_requirement(),
    )
    latest_errors, latest_error_indices = _validate_allowance_records(
        latest_records,
        error_allowances,
        lambda record: record.level in ("ERROR", "FATAL"),
        "ERROR/FATAL",
        require_every_selected=True,
    )
    debug_errors, debug_error_indices = _validate_allowance_records(
        debug_records,
        error_allowances,
        lambda record: record.level in ("ERROR", "FATAL"),
        "ERROR/FATAL",
        require_every_selected=True,
    )
    latest_error_projection = tuple(
        canonical_record_tuple(
            latest_records[index],
            workspace_root=workspace_root,
            install_root=install_root,
        )
        for index in latest_error_indices
    )
    debug_error_projection = tuple(
        canonical_record_tuple(
            debug_records[index],
            workspace_root=workspace_root,
            install_root=install_root,
        )
        for index in debug_error_indices
    )
    if latest_error_projection != debug_error_projection:
        raise VerificationError(
            "latest.log and debug.log canonical ERROR/FATAL projections differ"
        )
    if latest_errors != debug_errors:
        raise VerificationError(
            "latest.log and debug.log canonical ERROR/FATAL identities differ"
        )

    latest_optional_warning_count = _validate_reviewed_warning_multiset(
        latest_records,
        "latest.log",
        workspace_root=workspace_root,
        install_root=install_root,
    )
    debug_optional_warning_count = _validate_reviewed_warning_multiset(
        debug_records,
        "debug.log",
        workspace_root=workspace_root,
        install_root=install_root,
    )
    if latest_optional_warning_count != debug_optional_warning_count:
        raise VerificationError(
            "latest.log and debug.log optional environmental WARN presence differs"
        )
    warning_allowances = project_warning_allowances()
    warning_identities = {
        (allowance.level, allowance.logger, allowance.message)
        for allowance in warning_allowances
    }
    latest_warnings, latest_warning_indices = _validate_allowance_records(
        latest_records,
        warning_allowances,
        lambda record: (record.level, record.logger, record.message)
        in warning_identities,
        "known residual WARN",
        require_every_selected=False,
    )
    debug_warnings, debug_warning_indices = _validate_allowance_records(
        debug_records,
        warning_allowances,
        lambda record: (record.level, record.logger, record.message)
        in warning_identities,
        "known residual WARN",
        require_every_selected=False,
    )
    if _accepted_warning_projection(
        latest_records,
        latest_warning_indices,
        workspace_root=workspace_root,
        install_root=install_root,
    ) != _accepted_warning_projection(
        debug_records,
        debug_warning_indices,
        workspace_root=workspace_root,
        install_root=install_root,
    ):
        raise VerificationError(
            "latest.log and debug.log canonical accepted WARN projections differ"
        )
    if latest_warnings != debug_warnings:
        raise VerificationError(
            "latest.log and debug.log accepted WARN identities differ"
        )
    return (
        latest_errors,
        latest_warnings,
        latest_error_indices,
        debug_error_indices,
    )


def verify_sable_runtime_dist_cleaner_evidence(
    root: Path | str,
    install: Path | str,
    latest_text: str,
    debug_text: str,
    nonce: str,
    status: int,
) -> DedicatedErrorEvidence:
    verify_sable_source_evidence(root, install)
    latest_state = validate_boot_markers(latest_text, nonce, status, root)
    debug_state = validate_boot_markers(debug_text, nonce, status, root)
    if latest_state != debug_state:
        raise VerificationError(
            "latest.log and debug.log canonical boot state projections differ"
        )
    latest_records = parse_log_records(latest_text)
    debug_records = parse_log_records(debug_text)
    _, _, latest_error_indices, debug_error_indices = _validate_canonical_log_pair(
        latest_records,
        debug_records,
        workspace_root=root,
        install_root=install,
    )

    requirement = project_sable_error_requirement()
    latest_indices = tuple(
        index
        for index in latest_error_indices
        if _allowance_matches(latest_records[index], requirement)
    )
    if len(latest_indices) != requirement.count:
        raise VerificationError(
            "RuntimeDistCleaner latest.log count mismatch: "
            f"expected {requirement.count}, got {len(latest_indices)}"
        )
    debug_indices = _validate_sable_debug_records(debug_records, requirement)
    projected_debug_indices = tuple(
        index
        for index in debug_error_indices
        if _allowance_matches(debug_records[index], requirement)
    )
    if debug_indices != projected_debug_indices:
        raise VerificationError(
            "RuntimeDistCleaner debug source indices differ from canonical projection"
        )
    return DedicatedErrorEvidence(
        label=requirement.label,
        latest_record_indices=latest_indices,
        debug_record_indices=debug_indices,
    )


def _idas_compat_audit_projection(
    records: Sequence[LogRecord],
) -> tuple[tuple[str, str, str, str, tuple[str, ...]], ...]:
    return tuple(
        canonical_record_tuple(record)
        for record in records
        if record.logger == IDAS_COMPAT_LOGGER
        and record.level in ("INFO", "WARN", "ERROR", "FATAL")
    )


def verify_idas_compat_runtime_evidence(
    root: Path | str,
    install: Path | str,
    latest_text: str,
    debug_text: str,
) -> Counter[str]:
    verify_idas_compat_source_evidence(root, install)
    latest_records = parse_log_records(latest_text)
    debug_records = parse_log_records(debug_text)
    latest_projection = _idas_compat_audit_projection(latest_records)
    debug_projection = _idas_compat_audit_projection(debug_records)
    if latest_projection != debug_projection:
        raise VerificationError(
            "latest.log and debug.log IDAS compat audit projections differ"
        )

    for label, records in (("latest.log", latest_records), ("debug.log", debug_records)):
        air_errors = [
            record
            for record in records
            if _record_is(
                record,
                "ERROR",
                "net.minecraft.world.item.ItemStack/",
                ITEMSTACK_AIR_MESSAGE,
            )
        ]
        if air_errors:
            raise VerificationError(
                f"{label} contains {len(air_errors)} generic ItemStack air ERROR records"
            )

    latest_audits = [
        (index, record)
        for index, record in enumerate(latest_records)
        if record.logger == IDAS_COMPAT_LOGGER
        and record.level in ("INFO", "WARN", "ERROR", "FATAL")
    ]
    invalid_levels = [
        record for _, record in latest_audits if record.level != "INFO"
    ]
    if invalid_levels:
        raise VerificationError(
            "IDAS compat emitted an unreviewed non-INFO audit record"
        )
    ready_indices = [
        index
        for index, record in latest_audits
        if record.message == IDAS_COMPAT_READY_MESSAGE
    ]
    if len(ready_indices) != 1:
        raise VerificationError(
            f"IDAS compat READY count mismatch: expected 1, got {len(ready_indices)}"
        )
    sanitized_pattern = re.compile(
        r"AFTERLIGHT_IDAS_SANITIZED template=(?P<template>idas:[a-z0-9_./-]+) "
        r"replacements=(?P<replacements>[1-9][0-9]*) digest=(?P<digest>[0-9a-f]{64})"
    )
    sanitized: list[tuple[int, LogRecord, re.Match[str]]] = []
    for index, record in latest_audits:
        if record.message == IDAS_COMPAT_READY_MESSAGE:
            continue
        match = sanitized_pattern.fullmatch(record.message)
        if match is None:
            raise VerificationError(
                f"unreviewed IDAS compat audit record: {record.message}"
            )
        sanitized.append((index, record, match))
    if any(index <= ready_indices[0] for index, _, _ in sanitized):
        raise VerificationError("IDAS compat SANITIZED record preceded READY")
    template_counts = Counter(match.group("template") for _, _, match in sanitized)
    duplicates = sorted(
        template for template, count in template_counts.items() if count != 1
    )
    if duplicates:
        raise VerificationError(
            f"IDAS compat sanitized a template more than once: {duplicates}"
        )
    sanitized_messages = tuple(record.message for _, record, _ in sanitized)
    if sanitized_messages != IDAS_COMPAT_BOOT_SANITIZED_MESSAGES:
        raise VerificationError(
            "IDAS compat clean-boot SANITIZED audit sequence changed: "
            f"{sanitized_messages}"
        )
    camp_count = sum(
        record.message == IDAS_COMPAT_CAMP_MESSAGE for _, record, _ in sanitized
    )
    if camp_count != 1:
        raise VerificationError(
            f"IDAS camp1 SANITIZED audit count mismatch: expected 1, got {camp_count}"
        )
    return Counter(
        {
            "IDAS compat READY": 1,
            "IDAS camp1 sanitized": 1,
            "IDAS sanitized templates": len(sanitized),
        }
    )


def validate_error_records(
    log_text: str,
    allowances: Iterable[LogAllowance],
    consumed_record_indices: Iterable[int] = (),
) -> Counter[str]:
    if tuple(consumed_record_indices):
        raise VerificationError(
            "pre-consumed ERROR/FATAL records are not supported by the canonical oracle"
        )
    allowance_list = tuple(allowances)
    records = parse_log_records(log_text)
    observed, _ = _validate_allowance_records(
        records,
        allowance_list,
        lambda record: record.level in ("ERROR", "FATAL"),
        "ERROR/FATAL",
        require_every_selected=True,
    )
    return observed


def _validate_allowance_records(
    records: Sequence[LogRecord],
    allowances: Sequence[LogAllowance],
    selected: Callable[[LogRecord], bool],
    category: str,
    require_every_selected: bool,
) -> tuple[Counter[str], tuple[int, ...]]:
    observed: Counter[str] = Counter()
    accepted_indices: list[int] = []
    for index, record in enumerate(records):
        if not selected(record):
            continue
        matches = [
            allowance
            for allowance in allowances
            if _allowance_matches(record, allowance)
        ]
        if not matches and not require_every_selected:
            expected_identity = any(
                record.level == allowance.level
                and record.logger == allowance.logger
                and record.message == allowance.message
                for allowance in allowances
            )
            if not expected_identity:
                continue
        if len(matches) != 1:
            raise VerificationError(
                f"unmatched canonical {category} record from "
                f"{record.thread} {record.logger}: {record.message}"
            )
        observed[matches[0].label] += 1
        accepted_indices.append(index)

    for allowance in allowances:
        actual = observed[allowance.label]
        if actual != allowance.count:
            raise VerificationError(
                f"{allowance.label} count mismatch: expected {allowance.count}, got {actual}"
            )
    return observed, tuple(accepted_indices)


def project_error_allowances() -> tuple[LogAllowance, ...]:
    return (
        LogAllowance(
            label="Moonlight Fabric API detection error",
            level="ERROR",
            logger="Moonlight/",
            message=MOONLIGHT_FABRIC_MESSAGE,
            count=1,
            thread="modloading-sync-worker",
            continuations=(
                "Mods that bundle Fabric API: [forgified-fabric-api-0.115.6+2.1.0+1.21.1.jar]",
            ),
            canonical_sha256=(
                "16f8b1e44b35ebd10d63ee3b244e44e208f3d40a267a49bd16e43d3e2fa4288c"
            ),
        ),
        LogAllowance(
            label="Fabric overlay metadata error",
            level="ERROR",
            logger="net.minecraft.server.packs.AbstractPackResources/",
            message="Couldn't load fabric:overlays metadata",
            count=1,
            thread="main",
            canonical_sha256=(
                "a21b5e9526cfa36945dc2596eae19282286ffdada02a5355aa4e32aca35fdd9b"
            ),
        ),
    )


def project_warning_allowances() -> tuple[LogAllowance, ...]:
    kaleidoscope = tuple(
        LogAllowance(
            label=f"Kaleidoscope carrier {food}_count_{count}",
            level="WARN",
            logger="KubeJS Server/",
            message=(
                "RecipeComponent.java#160: Failed to read component 'carrier: ingredient?' "
                f"from recipe kaleidoscope_cookery:stockpot/{food}_count_{count}"
                f"{KALEIDOSCOPE_SUFFIX}"
            ),
            count=1,
            thread="main",
        )
        for food in ("shengjian_mantou", "dumpling", "zongzi")
        for count in range(1, 10)
    )
    malum = tuple(
        LogAllowance(
            label=f"EnderIO Malum inheritance {metal}",
            level="WARN",
            logger="net.minecraft.world.item.crafting.RecipeManager/",
            message=(
                "[EnderIO] Unable to inherit the cooking recipe with ID: "
                f"malum:{metal}_from_node_smelting. Reason: The result item is empty."
            ),
            count=1,
            thread="main",
        )
        for metal in (
            "tin",
            "uranium",
            "copper",
            "silver",
            "zinc",
            "osmium",
            "nickel",
            "lead",
            "aluminum",
        )
    )
    return kaleidoscope + (
        LogAllowance(
            label="Incendium smithing fallback",
            level="WARN",
            logger="KubeJS Server/",
            message=INCENDIUM_WARNING_MESSAGE,
            count=1,
            thread="main",
        ),
    ) + malum + (
        LogAllowance(
            label="Apothic Enchanting stale data map type",
            level="WARN",
            logger="net.neoforged.neoforge.registries.DataMapLoader/",
            message=APOTHIC_WARNING_MESSAGE,
            count=1,
            thread="Worker-Main-N",
        ),
        LogAllowance(
            label="Just Dire Things early pancake candidate scan",
            level="WARN",
            logger="Supplementaries/",
            message=JDT_WARNING_MESSAGE,
            count=1,
            thread="main",
        ),
    )


def validate_known_residual_warnings(log_text: str) -> Counter[str]:
    records = parse_log_records(log_text)
    for record in records:
        if record.level != "WARN":
            continue
        if (
            record.logger == "net.minecraft.core.MappedRegistry/"
            and re.fullmatch(
                r"Not all defined tags for registry ResourceKey\[minecraft:root / "
                r"minecraft:worldgen/biome\] are present in data pack: idas:[a-z0-9_./-]+",
                record.message,
            )
        ) or (
            record.logger == "net.minecraft.tags.TagLoader/"
            and re.fullmatch(r"Couldn't load tag idas:[a-z0-9_./-]+.*", record.message)
        ):
            raise VerificationError(
                f"unmatched known residual WARN from {record.logger}: {record.message}"
            )
    allowances = project_warning_allowances()
    identities = {
        (allowance.level, allowance.logger, allowance.message)
        for allowance in allowances
    }
    observed, _ = _validate_allowance_records(
        records,
        allowances,
        lambda record: (record.level, record.logger, record.message) in identities,
        "known residual WARN",
        require_every_selected=False,
    )
    return observed


def verify_jdt_evidence(root: Path | str, install: Path | str) -> None:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    resolved = resolve_source_jars(
        root_path, install_path, JDT_ARTIFACT_SHA256.keys()
    )
    for metadata_relative, expected_hash in JDT_ARTIFACT_SHA256.items():
        jar_path = resolved[metadata_relative]
        actual_hash = _hash_file(jar_path, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT evidence artifact hash mismatch for {metadata_relative}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    for (metadata_relative, resource), expected_hash in JDT_CLASS_SHA256.items():
        try:
            with zipfile.ZipFile(resolved[metadata_relative]) as archive:
                payload = archive.read(resource)
        except (OSError, KeyError, zipfile.BadZipFile) as error:
            raise VerificationError(f"cannot read JDT evidence class {resource}: {error}") from error
        actual_hash = _hash_bytes(payload, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT evidence class hash mismatch for {resource}: "
                f"expected {expected_hash}, got {actual_hash}"
            )

    for relative, expected_hash in JDT_RUNTIME_SHA256.items():
        runtime_path = _verified_regular_file(
            install_path,
            _safe_relative_path(relative, "JDT runtime evidence"),
            "JDT runtime evidence",
        )
        actual_hash = _hash_file(runtime_path, "sha256")
        if actual_hash != expected_hash:
            raise VerificationError(
                f"JDT runtime hash mismatch for {relative}: expected {expected_hash}, got {actual_hash}"
            )

    for config_root, config_label in (
        (root_path, "source JDT config"),
        (install_path, "installed JDT config"),
    ):
        config_path = _verified_regular_file(
            config_root,
            PurePosixPath("config/justdirethings-server.toml"),
            config_label,
        )
        actual_hash = _hash_file(config_path, "sha256")
        if actual_hash != JDT_CONFIG_SHA256:
            raise VerificationError(
                f"JDT config hash mismatch for {config_path}: "
                f"expected {JDT_CONFIG_SHA256}, got {actual_hash}"
            )


def verify_boot_run(
    root: Path | str, install: Path | str, nonce: str, status: int
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    seal_sources = verify_seal_sources(root_path, install_path)
    quest_identity = verify_quest_identity_stability(root_path, install_path)
    gate_audit_sha256 = verify_installed_gate_audit(
        root_path, install_path, nonce
    )
    quest_audit_provenance = verify_installed_quest_audits(
        root_path,
        install_path,
        nonce,
    )
    verify_install_provenance(root_path, install_path, verify_files=False)
    verify_jdt_evidence(root_path, install_path)
    log_text = _read_strict_utf8(
        install_path, PurePosixPath("logs/latest.log"), "latest.log"
    )
    debug_text = _read_strict_utf8(
        install_path, PurePosixPath("logs/debug.log"), "debug.log"
    )
    _read_strict_utf8(
        install_path,
        PurePosixPath("logs/kubejs/server.log"),
        "KubeJS server.log",
    )
    boot_text = _read_strict_utf8(
        install_path, PurePosixPath("boot.log"), "boot.log"
    )
    runtime_logs = (
        install_path / "logs" / "latest.log",
        install_path / "logs" / "debug.log",
        install_path / "logs" / "kubejs" / "server.log",
    )
    quest_root = root_path / "config" / "ftbquests" / "quests"
    acquisition_manifest = load_acquisition_manifest(
        root_path / FIXTURE_RELATIVE
    )
    runtime_audit_errors = [
        *validate_quest_item_audit_logs(quest_root, nonce, runtime_logs),
        *validate_acquisition_audit_logs(
            acquisition_manifest,
            nonce,
            runtime_logs,
        ),
    ]
    if runtime_audit_errors:
        raise VerificationError(
            "quest runtime audit validation failed: "
            + "; ".join(runtime_audit_errors)
        )
    sable = verify_sable_runtime_dist_cleaner_evidence(
        root_path,
        install_path,
        log_text,
        debug_text,
        nonce,
        status,
    )
    audits = verify_idas_compat_runtime_evidence(
        root_path, install_path, log_text, debug_text
    )
    latest_records = parse_log_records(log_text)
    debug_records = parse_log_records(debug_text)
    console_records = parse_console_records(boot_text)
    errors, warnings, _, _ = _validate_canonical_log_pair(
        latest_records,
        debug_records,
        workspace_root=root_path,
        install_root=install_path,
    )
    latest_warning_check = validate_known_residual_warnings(log_text)
    debug_warning_check = validate_known_residual_warnings(debug_text)
    if latest_warning_check != warnings or debug_warning_check != warnings:
        raise VerificationError(
            "canonical warning projection differs from repaired-signature validation"
        )
    if errors[sable.label] != len(sable.latest_record_indices):
        raise VerificationError("Sable canonical error count differs from source proof")
    console_digest, console_count = _validate_console_projection(
        console_records,
        latest_records,
        debug_records,
        workspace_root=root_path,
        install_root=install_path,
    )
    return {
        "errors": errors,
        "warnings": warnings,
        "warning_records": REVIEWED_WARNING_TOTAL,
        "audits": audits,
        "gate_audit_sha256": gate_audit_sha256,
        "quest_audit_provenance": quest_audit_provenance,
        "seal_source_sha256": seal_sources["sha256"],
        "seal_code_corpus_sha256": seal_sources["code_corpus_sha256"],
        "quest_identity_count": quest_identity["count"],
        "quest_identity_sha256": quest_identity["sha256"],
        "console_severe_count": console_count,
        "console_severe_sha256": console_digest,
    }


QUEST_AUDIT_NONCE_PLACEHOLDER = b"__AFTERLIGHT_BOOT_NONCE__"
QUEST_RUNTIME_AUDIT_PROVENANCE = PurePosixPath(
    "afterlight-runtime-audit-provenance.json"
)


def render_quest_item_audit(root: Path | str) -> bytes:
    root_path = _validated_root(root, "pack root")
    return _render_quest_item_audit(
        root_path / "config" / "ftbquests" / "quests"
    ).encode("utf-8")


def render_manual_acquisition_audit(root: Path | str) -> bytes:
    root_path = _validated_root(root, "pack root")
    manifest = load_acquisition_manifest(root_path / FIXTURE_RELATIVE)
    return render_acquisition_source(manifest).encode("utf-8")


QUEST_RUNTIME_AUDITS = (
    (
        "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
        render_quest_item_audit,
    ),
    (ACQUISITION_AUDIT_RELATIVE, render_manual_acquisition_audit),
)


def _atomic_runtime_write(
    root: Path,
    relative: PurePosixPath,
    payload: bytes,
    *,
    mode: int,
    must_exist: bool,
) -> Path:
    root_path = _validated_root(root, "runtime audit write root")
    if must_exist:
        target = _verified_regular_file(
            root_path,
            relative,
            "runtime audit write target",
        )
    else:
        parent = root_path
        for part in relative.parent.parts:
            parent /= part
            try:
                parent_status = parent.lstat()
            except OSError as error:
                raise VerificationError(
                    f"cannot inspect runtime audit write parent {relative}: {error}"
                ) from error
            if stat.S_ISLNK(parent_status.st_mode) or not stat.S_ISDIR(
                parent_status.st_mode
            ):
                raise VerificationError(
                    f"unsafe runtime audit write parent: {relative.as_posix()}"
                )
        target = root_path.joinpath(*relative.parts)
        try:
            target_status = target.lstat()
        except FileNotFoundError:
            target_status = None
        except OSError as error:
            raise VerificationError(
                f"cannot inspect runtime audit write target {relative}: {error}"
            ) from error
        if target_status is not None and (
            stat.S_ISLNK(target_status.st_mode)
            or not stat.S_ISREG(target_status.st_mode)
        ):
            raise VerificationError(
                f"unsafe runtime audit write target: {relative.as_posix()}"
            )

    temporary = target.with_name(
        f".{target.name}.afterlight-{os.getpid()}-{os.urandom(8).hex()}"
    )
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = -1
    try:
        descriptor = os.open(temporary, flags, mode)
        remaining = memoryview(payload)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("short runtime audit write")
            remaining = remaining[written:]
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.chmod(temporary, mode)
        os.replace(temporary, target)
    except OSError as error:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        raise VerificationError(
            f"cannot atomically write runtime audit {relative.as_posix()}: {error}"
        ) from error
    try:
        actual = target.read_bytes()
    except OSError as error:
        raise VerificationError(
            f"cannot read back runtime audit {relative.as_posix()}: {error}"
        ) from error
    if actual != payload:
        raise VerificationError(
            f"runtime audit readback mismatch: {relative.as_posix()}"
        )
    return target


def _runtime_audit_expectations(
    root: Path,
    install: Path,
    nonce: str,
    *,
    require_pre_render: bool,
) -> list[dict[str, object]]:
    if re.fullmatch(r"[A-Za-z0-9._-]+", nonce) is None:
        raise VerificationError("installed quest audit nonce is malformed")
    expectations: list[dict[str, object]] = []
    for relative_text, renderer in QUEST_RUNTIME_AUDITS:
        relative = PurePosixPath(relative_text)
        canonical = renderer(root)
        source_path = _verified_regular_file(
            root,
            relative,
            "repository quest audit source",
        )
        try:
            tracked = source_path.read_bytes()
        except OSError as error:
            raise VerificationError(
                f"cannot read repository quest audit source {relative_text}: {error}"
            ) from error
        if tracked != canonical:
            raise VerificationError(
                f"repository quest audit source is not canonical: {relative_text}"
            )
        if canonical.count(QUEST_AUDIT_NONCE_PLACEHOLDER) != 1:
            raise VerificationError(
                f"quest audit nonce placeholder count changed: {relative_text}"
            )
        installed_path = _verified_regular_file(
            install,
            relative,
            "installed quest audit",
        )
        try:
            installed = installed_path.read_bytes()
        except OSError as error:
            raise VerificationError(
                f"cannot read installed quest audit {relative_text}: {error}"
            ) from error
        rendered = canonical.replace(
            QUEST_AUDIT_NONCE_PLACEHOLDER,
            nonce.encode("ascii"),
            1,
        )
        expected_installed = canonical if require_pre_render else rendered
        if installed != expected_installed:
            phase = "pre-render source" if require_pre_render else "post-render bytes"
            raise VerificationError(
                f"installed quest audit {phase} mismatch: {relative_text}"
            )
        expectations.append(
            {
                "path": relative_text,
                "relative": relative,
                "canonical": canonical,
                "rendered": rendered,
                "mode": stat.S_IMODE(installed_path.stat().st_mode),
                "source_sha256": _hash_bytes(canonical, "sha256"),
                "rendered_sha256": _hash_bytes(rendered, "sha256"),
            }
        )
    return expectations


def _runtime_audit_provenance_payload(
    expectations: Sequence[dict[str, object]],
    nonce: str,
) -> tuple[dict[str, object], bytes]:
    document: dict[str, object] = {
        "schema_version": 1,
        "nonce": nonce,
        "audits": [
            {
                "path": expectation["path"],
                "source_sha256": expectation["source_sha256"],
                "rendered_sha256": expectation["rendered_sha256"],
            }
            for expectation in sorted(
                expectations,
                key=lambda value: str(value["path"]),
            )
        ],
    }
    payload = (json.dumps(document, indent=2, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    return document, payload


def render_installed_quest_audits(
    root: Path | str,
    install: Path | str,
    nonce: str,
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    expectations = _runtime_audit_expectations(
        root_path,
        install_path,
        nonce,
        require_pre_render=True,
    )
    written: list[dict[str, object]] = []
    provenance_path = install_path / QUEST_RUNTIME_AUDIT_PROVENANCE
    if provenance_path.exists() or provenance_path.is_symlink():
        raise VerificationError(
            "runtime audit provenance must be absent before rendering"
        )
    try:
        for expectation in expectations:
            _atomic_runtime_write(
                install_path,
                expectation["relative"],
                expectation["rendered"],
                mode=int(expectation["mode"]),
                must_exist=True,
            )
            written.append(expectation)
        document, payload = _runtime_audit_provenance_payload(
            expectations,
            nonce,
        )
        _atomic_runtime_write(
            install_path,
            QUEST_RUNTIME_AUDIT_PROVENANCE,
            payload,
            mode=0o600,
            must_exist=False,
        )
        result = verify_installed_quest_audits(
            root_path,
            install_path,
            nonce,
        )
    except VerificationError:
        for expectation in reversed(written):
            try:
                _atomic_runtime_write(
                    install_path,
                    expectation["relative"],
                    expectation["canonical"],
                    mode=int(expectation["mode"]),
                    must_exist=True,
                )
            except VerificationError:
                pass
        try:
            provenance_path.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass
        raise
    return result


def verify_installed_quest_audits(
    root: Path | str,
    install: Path | str,
    nonce: str,
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    expectations = _runtime_audit_expectations(
        root_path,
        install_path,
        nonce,
        require_pre_render=False,
    )
    expected_document, expected_payload = _runtime_audit_provenance_payload(
        expectations,
        nonce,
    )
    provenance_path = _verified_regular_file(
        install_path,
        QUEST_RUNTIME_AUDIT_PROVENANCE,
        "runtime audit provenance",
    )
    try:
        actual_payload = provenance_path.read_bytes()
    except OSError as error:
        raise VerificationError(
            f"cannot read runtime audit provenance: {error}"
        ) from error
    if actual_payload != expected_payload:
        raise VerificationError("runtime audit provenance mismatch")
    if stat.S_IMODE(provenance_path.stat().st_mode) != 0o600:
        raise VerificationError("runtime audit provenance mode must be 0600")
    return expected_document


def quest_audit_expectation(root: Path | str) -> tuple[str, int]:
    root_path = _validated_root(root, "pack root")
    script_path = (
        root_path
        / "kubejs"
        / "server_scripts"
        / "afterlight"
        / "generated_quest_item_audit.js"
    )
    try:
        script = script_path.read_text(encoding="utf-8")
    except OSError as error:
        raise VerificationError(
            f"cannot read generated quest audit script {script_path}: {error}"
        ) from error
    quest_root = root_path / "config" / "ftbquests" / "quests"
    expected_script = _render_quest_item_audit(quest_root)
    if script != expected_script:
        raise VerificationError(
            "generated quest audit script differs from deterministic builder output"
        )
    digest_matches = re.findall(
        r"^const AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST = '([0-9a-f]{64})'$",
        script,
        flags=re.MULTILINE,
    )
    if len(digest_matches) != 1:
        raise VerificationError(
            "generated quest audit script must declare exactly one digest"
        )
    item_match = re.search(
        r"^const AFTERLIGHT_QUEST_ITEM_IDS = (?P<items>\[.*?\])\n\n"
        r"const AFTERLIGHT_QUEST_COMMODITY =",
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    if item_match is None:
        raise VerificationError("generated quest audit item array is malformed")
    try:
        items = json.loads(item_match.group("items"))
    except json.JSONDecodeError as error:
        raise VerificationError(
            f"generated quest audit item array cannot be decoded: {error}"
        ) from error
    if (
        not isinstance(items, list)
        or not items
        or not all(isinstance(item, str) for item in items)
        or len(set(items)) != len(items)
    ):
        raise VerificationError("generated quest audit item array is not canonical")
    success_line = (
        "  console.info(`[AFTERLIGHT QUEST ITEM AUDIT] OK "
        "${AFTERLIGHT_QUEST_ITEM_AUDIT_DIGEST} "
        "${AFTERLIGHT_QUEST_ITEM_IDS.length} ${bootNonce}`)"
    )
    if script.count(success_line) != 1:
        raise VerificationError("generated quest audit success emitter changed")
    source_items = _quest_item_ids(quest_root)
    source_digest = quest_item_audit_digest(quest_root)
    if tuple(items) != source_items or digest_matches[0] != source_digest:
        raise VerificationError(
            "quest audit source mismatch: generated array and digest must match "
            "the authenticated quest compiler inputs"
        )
    return source_digest, len(source_items)


def verify_installed_quest_audit(
    root: Path | str, install: Path | str, nonce: str
) -> str:
    if re.fullmatch(r"[A-Za-z0-9._-]+", nonce) is None:
        raise VerificationError("installed quest audit nonce is malformed")
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    quest_root = root_path / "config" / "ftbquests" / "quests"
    expected_source = _render_quest_item_audit(quest_root)
    placeholder = QUEST_AUDIT_NONCE_PLACEHOLDER.decode("ascii")
    if expected_source.count(placeholder) != 1:
        raise VerificationError("quest audit builder nonce contract changed")
    expected = expected_source.replace(placeholder, nonce, 1).encode("utf-8")
    relative = PurePosixPath(
        "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
    )
    installed_path = _verified_regular_file(
        install_path, relative, "installed quest audit"
    )
    try:
        actual = installed_path.read_bytes()
    except OSError as error:
        raise VerificationError(
            f"cannot read installed quest audit {installed_path}: {error}"
        ) from error
    if actual != expected:
        raise VerificationError(
            "installed quest audit differs from canonical post-nonce builder bytes"
        )
    return _hash_bytes(actual, "sha256")


GATE_AUDIT_RELATIVE = PurePosixPath(
    "kubejs/server_scripts/afterlight/gate_recipe_audit.js"
)
GATE_AUDIT_SHA256_PLACEHOLDER = b"__AFTERLIGHT_GATE_AUDIT_SHA256__"
GATE_AUDIT_NONCE_PLACEHOLDER = b"__AFTERLIGHT_GATE_BOOT_NONCE__"
GATE_AUDIT_RECIPE_COUNT = 11
SEAL_LITERAL_PATTERN = re.compile(r"ascendancy_seal")
SEAL_CODE_REFERENCE_PATTERN = re.compile(
    r"ascendancy_seal|\bSEAL\b|AFTERLIGHT\s*\["
)
SEAL_BINARY_REFERENCE_PATTERN = re.compile(
    rb"ascendancy_seal|AFTERLIGHT(?:\.SEAL|\s*\[[^\]]*SEAL)"
)
SEAL_JSON_ESCAPE_PATTERN = re.compile(r"\\u([0-9A-Fa-f]{4})")
SEAL_SCAN_ROOTS = ("config", "global_packs", "kubejs", "mods")
SEAL_CODE_SUFFIXES = frozenset((".js", ".jsx", ".mjs", ".ts", ".tsx"))
SEAL_CODE_MAX_FILE_BYTES = 4 * 1024 * 1024
SEAL_CODE_MAX_TOTAL_BYTES = 8 * 1024 * 1024
SEAL_CODE_MAX_FILES = 4_096
SEAL_CODE_MAX_TOTAL_PATH_BYTES = 1024 * 1024
SEAL_WALK_MAX_ENTRIES = 100_000
SEAL_WALK_MAX_TOTAL_PATH_BYTES = 16 * 1024 * 1024
SEAL_METADATA_MAX_FILE_BYTES = 1024 * 1024
SEAL_METADATA_MAX_FILES = 4_096
SEAL_METADATA_MAX_TOTAL_PATH_BYTES = 1024 * 1024
SEAL_METADATA_MAX_TOTAL_BYTES = 8 * 1024 * 1024
SEAL_SEMANTIC_DESCRIPTOR_MAX_INLINE_CHARS = 4_096
EXPECTED_SEAL_CODE_CORPUS_COUNT = 10
EXPECTED_SEAL_CODE_CORPUS_SHA256 = (
    "fa46a0e76f16fb2413fe83ac71ba43f0ba46e9ecb73fa6d74fe87e446188d53f"
)
SEAL_RENDERED_CODE_RELATIVES = frozenset(
    {
        "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
        "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
    }
)
SEAL_ARCHIVE_MAX_DEPTH = 8
SEAL_ARCHIVE_MAX_MEMBERS = 50_000
SEAL_ARCHIVE_MAX_MEMBER_BYTES = 128 * 1024 * 1024
SEAL_ARCHIVE_MAX_EXPANDED_BYTES = 512 * 1024 * 1024
SEAL_ARCHIVE_MAX_TOTAL_MEMBERS = 1_000_000
SEAL_ARCHIVE_MAX_TOTAL_EXPANDED_BYTES = 4 * 1024 * 1024 * 1024
SEAL_ARCHIVE_MAX_COMPRESSION_RATIO = 500
SEAL_ARCHIVE_MAX_CENTRAL_DIRECTORY_BYTES = 64 * 1024 * 1024
SEAL_ARCHIVE_MAX_ZIP64_RECORD_BYTES = 64 * 1024
SEAL_SCAN_MAX_OCCURRENCES = 100_000
EXPECTED_SEAL_OCCURRENCES = Counter(
    (
        (
            "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
            "snbt:$.icon.id=kubejs:ascendancy_seal",
        ),
        (
            "config/ftbquests/quests/chapters/245BADE04399406C.snbt",
            "snbt:$.quests[].rewards[].item.id=kubejs:ascendancy_seal",
        ),
        (
            "config/ftbquests/quests/chapters/3FF4AF7B0C73F058.snbt",
            "snbt:$.quests[].tasks[].item.id=kubejs:ascendancy_seal",
        ),
        (
            "kubejs/assets/kubejs/lang/en_us.json",
            'json-key:$["item.kubejs.ascendancy_seal"]',
        ),
        (
            "kubejs/server_scripts/afterlight/_constants.js",
            "SEAL: 'kubejs:ascendancy_seal',",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_draconic.js",
            "}).keepIngredient({ item: AFTERLIGHT.SEAL, index: 7 })",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "C: 'minecraft:diamond', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "C: 'minecraft:ender_eye', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "I: 'minecraft:iron_ingot', R: 'minecraft:redstone', Z: AFTERLIGHT.SEAL",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "countTwoKeys.Z = Item.of(AFTERLIGHT.SEAL, 2)",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 2) {",
        ),
        (
            "kubejs/server_scripts/afterlight/gate_recipe_audit.js",
            "if (!ItemStack.isSameItemSameComponents(stack, Item.of(AFTERLIGHT.SEAL)) || stack.getCount() !== 1) {",
        ),
        (
            "kubejs/server_scripts/afterlight/generated_quest_item_audit.js",
            '"kubejs:ascendancy_seal",',
        ),
        (
            "kubejs/startup_scripts/afterlight/registry.js",
            "event.create('ascendancy_seal')",
        ),
    )
)


@dataclass(frozen=True)
class _SealZipMetadata:
    members: int
    central_directory_size: int
    central_directory_offset: int


@dataclass(frozen=True)
class _SealWalkFile:
    relative: PurePosixPath
    snapshot: tuple[int, int, int, int, int]


def _seal_file_identity(value: os.stat_result) -> tuple[int, int, int, int, int]:
    return (
        value.st_dev,
        value.st_ino,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )


def _seal_bounded_walk(
    root: Path,
    roots: Iterable[PurePosixPath],
    label: str,
) -> Iterable[_SealWalkFile]:
    root = _validated_root(root, f"{label} Seal source traversal root")
    entry_count = 0
    total_path_bytes = 0
    pending: list[
        tuple[PurePosixPath, tuple[int, int, int, int, int]]
    ] = []

    def account(
        relative: PurePosixPath,
        value: os.stat_result,
    ) -> tuple[int, int, int, int, int]:
        nonlocal entry_count, total_path_bytes
        entry_count += 1
        if entry_count > SEAL_WALK_MAX_ENTRIES:
            raise VerificationError(
                f"Seal source traversal entry count exceeds limit: {entry_count}"
            )
        total_path_bytes += len(relative.as_posix().encode("utf-8"))
        if total_path_bytes > SEAL_WALK_MAX_TOTAL_PATH_BYTES:
            raise VerificationError(
                "Seal source aggregate traversal path bytes exceeds limit: "
                f"{total_path_bytes}"
            )
        return _seal_file_identity(value)

    root_entries: list[
        tuple[PurePosixPath, tuple[int, int, int, int, int]]
    ] = []
    for relative in roots:
        canonical = _safe_relative_path(
            relative.as_posix(), f"{label} Seal source root"
        )
        path = root / canonical
        try:
            root_stat = path.lstat()
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} Seal source root "
                f"{canonical.as_posix()}: {error}"
            ) from error
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise VerificationError(
                f"invalid {label} Seal source root: {canonical.as_posix()}"
            )
        root_entries.append((canonical, account(canonical, root_stat)))
    pending.extend(sorted(root_entries, reverse=True))

    while pending:
        relative, expected_snapshot = pending.pop()
        directory_path = root / relative
        try:
            before_scan = directory_path.lstat()
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} Seal source directory "
                f"{relative.as_posix()}: {error}"
            ) from error
        if (
            stat.S_ISLNK(before_scan.st_mode)
            or not stat.S_ISDIR(before_scan.st_mode)
            or _seal_file_identity(before_scan) != expected_snapshot
        ):
            raise VerificationError(
                f"{label} Seal source directory changed during traversal: "
                f"{relative.as_posix()}"
            )
        children: list[
            tuple[
                PurePosixPath,
                os.stat_result,
                tuple[int, int, int, int, int],
            ]
        ] = []
        try:
            with os.scandir(directory_path) as entries:
                for entry in entries:
                    child_relative = _safe_relative_path(
                        (relative / entry.name).as_posix(),
                        f"{label} Seal source entry",
                    )
                    try:
                        child_stat = entry.stat(follow_symlinks=False)
                    except OSError as error:
                        raise VerificationError(
                            f"cannot inspect {label} Seal source entry "
                            f"{child_relative.as_posix()}: {error}"
                        ) from error
                    if stat.S_ISLNK(child_stat.st_mode):
                        raise VerificationError(
                            f"symlink in {label} Seal source traversal: "
                            f"{child_relative.as_posix()}"
                        )
                    if not (
                        stat.S_ISDIR(child_stat.st_mode)
                        or stat.S_ISREG(child_stat.st_mode)
                    ):
                        raise VerificationError(
                            f"non-regular {label} Seal source entry: "
                            f"{child_relative.as_posix()}"
                        )
                    snapshot = account(child_relative, child_stat)
                    children.append((child_relative, child_stat, snapshot))
        except VerificationError:
            raise
        except OSError as error:
            raise VerificationError(
                f"cannot scan {label} Seal source directory "
                f"{relative.as_posix()}: {error}"
            ) from error
        try:
            after_scan = directory_path.lstat()
        except OSError as error:
            raise VerificationError(
                f"cannot recheck {label} Seal source directory "
                f"{relative.as_posix()}: {error}"
            ) from error
        if _seal_file_identity(after_scan) != expected_snapshot:
            raise VerificationError(
                f"{label} Seal source directory changed during traversal: "
                f"{relative.as_posix()}"
            )
        child_directories: list[
            tuple[PurePosixPath, tuple[int, int, int, int, int]]
        ] = []
        for child_relative, child_stat, snapshot in sorted(
            children, key=lambda child: child[0].as_posix()
        ):
            if stat.S_ISDIR(child_stat.st_mode):
                child_directories.append((child_relative, snapshot))
            else:
                yield _SealWalkFile(child_relative, snapshot)
        pending.extend(reversed(child_directories))


class _SealStableFile:
    def __init__(
        self,
        root: Path,
        relative: PurePosixPath,
        label: str,
        *,
        max_bytes: int | None = None,
        size_kind: str = "file",
        expected_identity: tuple[int, int, int, int, int] | None = None,
    ) -> None:
        self.root = root
        self.relative = relative
        self.label = label
        self.max_bytes = max_bytes
        self.size_kind = size_kind
        self.expected_identity = expected_identity
        self.path: Path | None = None
        self.handle = None
        self.snapshot: tuple[int, int, int, int, int] | None = None
        self.initial_sha256: str | None = None

    def _hash(self) -> str:
        if self.handle is None:
            raise VerificationError(f"closed stable descriptor for {self.label}")
        self.handle.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: self.handle.read(1024 * 1024), b""):
            digest.update(chunk)
        self.handle.seek(0)
        return digest.hexdigest()

    def __enter__(self) -> "_SealStableFile":
        root = _validated_root(self.root, f"{self.label} root")
        target = root
        target_stat = None
        for part in self.relative.parts:
            target /= part
            try:
                target_stat = target.lstat()
            except OSError as error:
                raise VerificationError(
                    f"cannot inspect {self.label} path "
                    f"{self.relative.as_posix()}: {error}"
                ) from error
            if stat.S_ISLNK(target_stat.st_mode):
                raise VerificationError(
                    f"symlink in {self.label} path: {self.relative.as_posix()}"
                )
        if target_stat is None or not stat.S_ISREG(target_stat.st_mode):
            raise VerificationError(
                f"non-regular {self.label} path: {self.relative.as_posix()}"
            )
        if target_stat.st_nlink != 1:
            raise VerificationError(
                f"unsafe link count for {self.label} path: "
                f"{self.relative.as_posix()}"
            )
        if (
            self.expected_identity is not None
            and _seal_file_identity(target_stat) != self.expected_identity
        ):
            raise VerificationError(
                f"{self.label} changed before open: {self.relative.as_posix()}"
            )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        try:
            descriptor = os.open(target, flags)
        except OSError as error:
            raise VerificationError(
                f"cannot open {self.label} path {self.relative.as_posix()}: {error}"
            ) from error
        try:
            opened_stat = os.fstat(descriptor)
            if (
                target_stat is None
                or not stat.S_ISREG(opened_stat.st_mode)
                or opened_stat.st_nlink != 1
                or (opened_stat.st_dev, opened_stat.st_ino)
                != (target_stat.st_dev, target_stat.st_ino)
            ):
                raise VerificationError(
                    f"{self.label} changed during open: {self.relative.as_posix()}"
                )
            if self.max_bytes is not None and opened_stat.st_size > self.max_bytes:
                raise VerificationError(
                    f"Seal source {self.size_kind} size exceeds limit: "
                    f"{self.relative.as_posix()} size={opened_stat.st_size}"
                )
            self.path = target
            self.snapshot = _seal_file_identity(opened_stat)
            self.handle = os.fdopen(descriptor, "rb")
            descriptor = -1
            self.initial_sha256 = self._hash()
            if _seal_file_identity(os.fstat(self.handle.fileno())) != self.snapshot:
                raise VerificationError(
                    f"{self.label} changed during initial hash: "
                    f"{self.relative.as_posix()}"
                )
            return self
        except BaseException:
            if self.handle is not None:
                self.handle.close()
                self.handle = None
            elif descriptor >= 0:
                os.close(descriptor)
            raise

    @property
    def size(self) -> int:
        if self.snapshot is None:
            raise VerificationError(f"closed stable descriptor for {self.label}")
        return self.snapshot[2]

    def read_bytes(self, limit: int) -> bytes:
        if self.handle is None:
            raise VerificationError(f"closed stable descriptor for {self.label}")
        self.handle.seek(0)
        payload = self.handle.read(limit + 1)
        self.handle.seek(0)
        if len(payload) > limit:
            raise VerificationError(
                f"Seal source {self.size_kind} size exceeds limit: "
                f"{self.relative.as_posix()}"
            )
        if len(payload) != self.size:
            raise VerificationError(
                f"{self.label} size changed while reading: "
                f"{self.relative.as_posix()} metadata={self.size} "
                f"actual={len(payload)}"
            )
        return payload

    def __exit__(self, exception_type, exception, traceback) -> bool:
        stability_error: VerificationError | None = None
        try:
            if (
                self.handle is None
                or self.snapshot is None
                or self.path is None
                or self.initial_sha256 is None
            ):
                return False
            before_final = os.fstat(self.handle.fileno())
            if _seal_file_identity(before_final) != self.snapshot:
                raise VerificationError(
                    f"{self.label} changed during scan: {self.relative.as_posix()}"
                )
            final_sha256 = self._hash()
            after_final = os.fstat(self.handle.fileno())
            if (
                _seal_file_identity(after_final) != self.snapshot
                or final_sha256 != self.initial_sha256
            ):
                raise VerificationError(
                    f"{self.label} changed during scan: {self.relative.as_posix()}"
                )
            try:
                path_stat = self.path.lstat()
            except OSError as error:
                raise VerificationError(
                    f"{self.label} path changed during scan: "
                    f"{self.relative.as_posix()}: {error}"
                ) from error
            if stat.S_ISLNK(path_stat.st_mode):
                raise VerificationError(
                    f"symlink replaced {self.label} during scan: "
                    f"{self.relative.as_posix()}"
                )
            if _seal_file_identity(path_stat) != self.snapshot:
                raise VerificationError(
                    f"{self.label} descriptor identity changed during scan: "
                    f"{self.relative.as_posix()}"
                )
        except VerificationError as error:
            stability_error = error
        finally:
            if self.handle is not None:
                self.handle.close()
                self.handle = None
        if stability_error is not None:
            if exception is not None:
                raise stability_error from exception
            raise stability_error
        return False


def _seal_zip_preflight(
    source,
    relative_label: str,
    *,
    required: bool,
) -> _SealZipMetadata | None:
    source.seek(0, os.SEEK_END)
    archive_size = source.tell()
    tail_size = min(
        archive_size,
        22 + 65535 + 20 + 12 + SEAL_ARCHIVE_MAX_ZIP64_RECORD_BYTES,
    )
    tail_offset = archive_size - tail_size
    source.seek(tail_offset)
    tail = source.read(tail_size)
    source.seek(0)
    if len(tail) != tail_size:
        raise VerificationError(
            f"Seal source ZIP metadata changed while reading: {relative_label}"
        )

    eocd_candidates: list[tuple[int, tuple[object, ...]]] = []
    search_offset = 0
    while True:
        position = tail.find(b"PK\x05\x06", search_offset)
        if position < 0:
            break
        search_offset = position + 1
        if position + 22 > len(tail):
            continue
        fields = struct.unpack_from("<4s4H2LH", tail, position)
        comment_length = fields[-1]
        absolute = tail_offset + position
        if absolute + 22 + comment_length == archive_size:
            eocd_candidates.append((absolute, fields))

    if not eocd_candidates:
        source.seek(0)
        prefix = source.read(min(4, archive_size))
        source.seek(0)
        looks_like_zip = (
            prefix in (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
            or any(
                signature in tail
                for signature in (
                    b"PK\x05\x06",
                    b"PK\x06\x06",
                    b"PK\x06\x07",
                )
            )
        )
        if required or looks_like_zip:
            raise VerificationError(
                f"invalid or truncated Seal source ZIP metadata: {relative_label}"
            )
        return None
    if len(eocd_candidates) != 1:
        raise VerificationError(
            f"duplicate Seal source ZIP end metadata: {relative_label}"
        )

    eocd_offset, fields = eocd_candidates[0]
    (
        _signature,
        disk_number,
        central_disk,
        entries_on_disk,
        total_entries,
        central_size,
        central_offset,
        _comment_length,
    ) = fields
    if disk_number != 0 or central_disk != 0:
        raise VerificationError(
            f"multi-disk Seal source ZIP is unsupported: {relative_label}"
        )
    needs_zip64 = (
        entries_on_disk == 0xFFFF
        or total_entries == 0xFFFF
        or central_size == 0xFFFFFFFF
        or central_offset == 0xFFFFFFFF
    )
    locator_offset = eocd_offset - 20
    locator = None
    if locator_offset >= 0:
        source.seek(locator_offset)
        locator_bytes = source.read(20)
        source.seek(0)
        if len(locator_bytes) == 20 and locator_bytes.startswith(b"PK\x06\x07"):
            locator = struct.unpack("<4sLQL", locator_bytes)

    central_actual_offset: int
    if needs_zip64:
        if locator is None:
            raise VerificationError(
                f"missing Seal source ZIP64 locator: {relative_label}"
            )
        _locator_signature, locator_disk, zip64_relative_offset, disk_count = locator
        if locator_disk != 0 or disk_count != 1:
            raise VerificationError(
                f"invalid Seal source ZIP64 disk metadata: {relative_label}"
            )
        record_search_start = max(
            0,
            locator_offset - (12 + SEAL_ARCHIVE_MAX_ZIP64_RECORD_BYTES),
        )
        source.seek(record_search_start)
        record_region = source.read(locator_offset - record_search_start)
        source.seek(0)
        zip64_candidates: list[tuple[int, int]] = []
        search_offset = 0
        while True:
            position = record_region.find(b"PK\x06\x06", search_offset)
            if position < 0:
                break
            search_offset = position + 1
            if position + 12 > len(record_region):
                continue
            record_size = struct.unpack_from("<Q", record_region, position + 4)[0]
            absolute = record_search_start + position
            if (
                44 <= record_size <= SEAL_ARCHIVE_MAX_ZIP64_RECORD_BYTES
                and absolute + 12 + record_size == locator_offset
            ):
                zip64_candidates.append((absolute, record_size))
        if len(zip64_candidates) != 1:
            raise VerificationError(
                f"missing or duplicate Seal source ZIP64 end metadata: "
                f"{relative_label}"
            )
        zip64_offset, zip64_record_size = zip64_candidates[0]
        source.seek(zip64_offset)
        zip64_record = source.read(12 + zip64_record_size)
        source.seek(0)
        if len(zip64_record) != 12 + zip64_record_size:
            raise VerificationError(
                f"truncated Seal source ZIP64 end metadata: {relative_label}"
            )
        (
            _version_made,
            _version_needed,
            zip64_disk,
            zip64_central_disk,
            zip64_entries_on_disk,
            zip64_total_entries,
            zip64_central_size,
            zip64_central_offset,
        ) = struct.unpack_from("<2H2L4Q", zip64_record, 12)
        if (
            zip64_disk != 0
            or zip64_central_disk != 0
            or zip64_entries_on_disk != zip64_total_entries
        ):
            raise VerificationError(
                f"inconsistent Seal source ZIP64 disk metadata: {relative_label}"
            )
        if entries_on_disk != 0xFFFF and entries_on_disk != zip64_entries_on_disk:
            raise VerificationError(
                f"inconsistent Seal source ZIP64 member count: {relative_label}"
            )
        if total_entries != 0xFFFF and total_entries != zip64_total_entries:
            raise VerificationError(
                f"inconsistent Seal source ZIP64 member count: {relative_label}"
            )
        if central_size != 0xFFFFFFFF and central_size != zip64_central_size:
            raise VerificationError(
                f"inconsistent Seal source ZIP64 directory size: {relative_label}"
            )
        if central_offset != 0xFFFFFFFF and central_offset != zip64_central_offset:
            raise VerificationError(
                f"inconsistent Seal source ZIP64 directory offset: {relative_label}"
            )
        total_entries = zip64_total_entries
        entries_on_disk = zip64_entries_on_disk
        central_size = zip64_central_size
        central_offset = zip64_central_offset
        archive_prefix = zip64_offset - central_size - central_offset
        if archive_prefix < 0 or archive_prefix + zip64_relative_offset != zip64_offset:
            raise VerificationError(
                f"impossible Seal source ZIP64 offsets: {relative_label}"
            )
        central_actual_offset = archive_prefix + central_offset
        if central_actual_offset + central_size != zip64_offset:
            raise VerificationError(
                f"inconsistent Seal source ZIP64 directory boundary: "
                f"{relative_label}"
            )
    else:
        if locator is not None:
            raise VerificationError(
                f"unexpected Seal source ZIP64 locator: {relative_label}"
            )
        if entries_on_disk != total_entries:
            raise VerificationError(
                f"inconsistent Seal source ZIP member count: {relative_label}"
            )
        archive_prefix = eocd_offset - central_size - central_offset
        if archive_prefix < 0:
            raise VerificationError(
                f"impossible Seal source ZIP offsets: {relative_label}"
            )
        central_actual_offset = archive_prefix + central_offset
        if central_actual_offset + central_size != eocd_offset:
            raise VerificationError(
                f"inconsistent Seal source ZIP directory boundary: "
                f"{relative_label}"
            )

    if total_entries > SEAL_ARCHIVE_MAX_MEMBERS:
        raise VerificationError(
            f"Seal source archive member count exceeds limit: "
            f"{relative_label} count={total_entries}"
        )
    if central_size > SEAL_ARCHIVE_MAX_CENTRAL_DIRECTORY_BYTES:
        raise VerificationError(
            f"Seal source archive central directory size exceeds limit: "
            f"{relative_label} size={central_size}"
        )
    if central_actual_offset < 0 or central_actual_offset + central_size > archive_size:
        raise VerificationError(
            f"truncated Seal source ZIP central directory: {relative_label}"
        )
    source.seek(central_actual_offset)
    central_directory = source.read(central_size)
    source.seek(0)
    if len(central_directory) != central_size:
        raise VerificationError(
            f"truncated Seal source ZIP central directory: {relative_label}"
        )
    position = 0
    parsed_entries = 0
    while position < len(central_directory):
        if position + 46 > len(central_directory):
            raise VerificationError(
                f"truncated Seal source ZIP member metadata: {relative_label}"
            )
        member_fields = struct.unpack_from(
            "<4s6H3L5H2L", central_directory, position
        )
        if member_fields[0] != b"PK\x01\x02":
            raise VerificationError(
                f"invalid Seal source ZIP central signature: {relative_label}"
            )
        filename_length = member_fields[10]
        extra_length = member_fields[11]
        comment_length = member_fields[12]
        member_size = 46 + filename_length + extra_length + comment_length
        if member_size < 46 or position + member_size > len(central_directory):
            raise VerificationError(
                f"truncated Seal source ZIP member metadata: {relative_label}"
            )
        position += member_size
        parsed_entries += 1
    if position != central_size or parsed_entries != total_entries:
        raise VerificationError(
            f"inconsistent Seal source ZIP central directory metadata: "
            f"{relative_label} declared={total_entries} parsed={parsed_entries}"
        )
    return _SealZipMetadata(
        members=total_entries,
        central_directory_size=central_size,
        central_directory_offset=central_actual_offset,
    )


def _snbt_child_path(path: str, key: str) -> str:
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
        return f"{path}.{key}"
    return f"{path}[{json.dumps(key, ensure_ascii=False)}]"


def _seal_semantic_occurrence_descriptors(
    kind: str,
    path: str,
    value: str,
    *,
    include_value: bool,
) -> Iterable[str]:
    match_count = sum(1 for _match in SEAL_LITERAL_PATTERN.finditer(value))
    if match_count == 0:
        return
    inline_chars = len(kind) + len(path) + 1
    if include_value:
        inline_chars += len(value) + 1
    if match_count == 1 and inline_chars <= SEAL_SEMANTIC_DESCRIPTOR_MAX_INLINE_CHARS:
        descriptor = f"{kind}:{path}={value}" if include_value else f"{kind}:{path}"
    else:
        digest = hashlib.sha256()
        for component in (kind, path, value):
            digest.update(component.encode("utf-8"))
            digest.update(b"\0")
        descriptor = (
            f"{kind}:matches={match_count}:path_chars={len(path)}:"
            f"value_chars={len(value)}:sha256={digest.hexdigest()}"
        )
    for _position in range(match_count):
        yield descriptor


def _snbt_seal_occurrences(value: object, path: str = "$") -> Iterable[str]:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key)
            child_path = _snbt_child_path(path, key_text)
            yield from _seal_semantic_occurrence_descriptors(
                "snbt-key",
                child_path,
                key_text,
                include_value=False,
            )
            yield from _snbt_seal_occurrences(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from _snbt_seal_occurrences(child, f"{path}[]")
    elif isinstance(value, str):
        yield from _seal_semantic_occurrence_descriptors(
            "snbt",
            path,
            value,
            include_value=True,
        )


class _JsonObject(list[tuple[str, object]]):
    pass


def _json_seal_occurrences(value: object, path: str = "$") -> Iterable[str]:
    if isinstance(value, _JsonObject):
        for key, child in value:
            child_path = _snbt_child_path(path, key)
            yield from _seal_semantic_occurrence_descriptors(
                "json-key",
                child_path,
                key,
                include_value=False,
            )
            yield from _json_seal_occurrences(child, child_path)
    elif isinstance(value, list):
        for child in value:
            yield from _json_seal_occurrences(child, f"{path}[]")
    elif isinstance(value, str):
        yield from _seal_semantic_occurrence_descriptors(
            "json",
            path,
            value,
            include_value=True,
        )


def _decode_json_unicode_escapes(text: str) -> str:
    return SEAL_JSON_ESCAPE_PATTERN.sub(
        lambda match: chr(int(match.group(1), 16)), text
    )


def _seal_archive_review_labels(root: Path) -> dict[str, str]:
    mods_root = root / "mods"
    try:
        mods_root_stat = mods_root.lstat()
    except FileNotFoundError:
        return {}
    except OSError as error:
        raise VerificationError(
            f"cannot inspect Seal archive metadata root: {error}"
        ) from error
    if stat.S_ISLNK(mods_root_stat.st_mode) or not stat.S_ISDIR(
        mods_root_stat.st_mode
    ):
        raise VerificationError("invalid Seal archive metadata root")
    metadata_files: list[_SealWalkFile] = []
    metadata_count = 0
    total_path_bytes = 0
    total_content_bytes = 0
    try:
        with os.scandir(mods_root) as entries:
            for entry in entries:
                if not entry.name.endswith(".pw.toml"):
                    continue
                metadata_relative = _safe_relative_path(
                    (PurePosixPath("mods") / entry.name).as_posix(),
                    "Seal archive metadata",
                )
                metadata_count += 1
                if metadata_count > SEAL_METADATA_MAX_FILES:
                    raise VerificationError(
                        "Seal archive metadata file count exceeds limit: "
                        f"{metadata_count}"
                    )
                total_path_bytes += len(
                    metadata_relative.as_posix().encode("utf-8")
                )
                if total_path_bytes > SEAL_METADATA_MAX_TOTAL_PATH_BYTES:
                    raise VerificationError(
                        "Seal archive aggregate metadata path bytes exceeds limit: "
                        f"{total_path_bytes}"
                    )
                try:
                    metadata_stat = entry.stat(follow_symlinks=False)
                except OSError as error:
                    raise VerificationError(
                        "cannot inspect Seal archive metadata "
                        f"{metadata_relative.as_posix()}: {error}"
                    ) from error
                if stat.S_ISLNK(metadata_stat.st_mode):
                    raise VerificationError(
                        "symlink in Seal archive metadata path: "
                        f"{metadata_relative.as_posix()}"
                    )
                if not stat.S_ISREG(metadata_stat.st_mode):
                    raise VerificationError(
                        "non-regular Seal archive metadata path: "
                        f"{metadata_relative.as_posix()}"
                    )
                if metadata_stat.st_size > SEAL_METADATA_MAX_FILE_BYTES:
                    raise VerificationError(
                        "Seal source metadata file size exceeds limit: "
                        f"{metadata_relative.as_posix()} size={metadata_stat.st_size}"
                    )
                total_content_bytes += metadata_stat.st_size
                if total_content_bytes > SEAL_METADATA_MAX_TOTAL_BYTES:
                    raise VerificationError(
                        "Seal archive aggregate metadata bytes exceeds limit: "
                        f"{total_content_bytes}"
                    )
                metadata_files.append(
                    _SealWalkFile(
                        metadata_relative,
                        _seal_file_identity(metadata_stat),
                    )
                )
    except VerificationError:
        raise
    except OSError as error:
        raise VerificationError(
            f"cannot scan Seal archive metadata root: {error}"
        ) from error
    try:
        final_mods_root_stat = mods_root.lstat()
    except OSError as error:
        raise VerificationError(
            f"cannot recheck Seal archive metadata root: {error}"
        ) from error
    if _seal_file_identity(final_mods_root_stat) != _seal_file_identity(
        mods_root_stat
    ):
        raise VerificationError("Seal archive metadata root changed during scan")

    labels: dict[str, str] = {}
    for metadata_file in sorted(
        metadata_files, key=lambda item: item.relative.as_posix()
    ):
        metadata_relative = metadata_file.relative
        with _SealStableFile(
            root,
            metadata_relative,
            "Seal archive metadata",
            max_bytes=SEAL_METADATA_MAX_FILE_BYTES,
            size_kind="metadata file",
            expected_identity=metadata_file.snapshot,
        ) as stable:
            payload = stable.read_bytes(SEAL_METADATA_MAX_FILE_BYTES)
            try:
                metadata = tomllib.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
                raise VerificationError(
                    "cannot parse Seal archive metadata "
                    f"{metadata_relative.as_posix()}: {error}"
                ) from error
        filename = _safe_relative_path(
            str(metadata.get("filename", "")),
            f"Seal archive filename for {metadata_relative.as_posix()}",
        )
        if len(filename.parts) != 1:
            raise VerificationError(
                "Seal archive filename must be a basename: "
                f"{metadata_relative.as_posix()}"
            )
        installed_relative = (PurePosixPath("mods") / filename).as_posix()
        prior = labels.get(installed_relative)
        if prior is not None:
            raise VerificationError(
                "duplicate Seal archive filename in metadata: "
                f"{installed_relative} ({prior}, {metadata_relative.as_posix()})"
            )
        labels[installed_relative] = metadata_relative.as_posix()
    return labels


def _seal_code_inventory(root: Path, label: str) -> dict[str, bytes]:
    code_root = root / "kubejs"
    try:
        code_root_stat = code_root.lstat()
    except OSError as error:
        raise VerificationError(
            f"cannot inspect {label} Seal source code root: {error}"
        ) from error
    if stat.S_ISLNK(code_root_stat.st_mode) or not stat.S_ISDIR(
        code_root_stat.st_mode
    ):
        raise VerificationError(f"invalid {label} Seal source code root")

    inventory: dict[str, bytes] = {}
    total_bytes = 0
    file_count = 0
    total_path_bytes = 0
    for walked_file in _seal_bounded_walk(
        root,
        (PurePosixPath("kubejs"),),
        label,
    ):
        relative = walked_file.relative
        if relative.suffix.lower() not in SEAL_CODE_SUFFIXES:
            continue
        file_count += 1
        if file_count > SEAL_CODE_MAX_FILES:
            raise VerificationError(
                f"Seal source code file count exceeds limit: {file_count}"
            )
        total_path_bytes += len(relative.as_posix().encode("utf-8"))
        if total_path_bytes > SEAL_CODE_MAX_TOTAL_PATH_BYTES:
            raise VerificationError(
                "Seal source aggregate code path bytes exceeds limit: "
                f"{total_path_bytes}"
            )
        with _SealStableFile(
            root,
            relative,
            f"{label} Seal source code file",
            max_bytes=SEAL_CODE_MAX_FILE_BYTES,
            size_kind="code file",
            expected_identity=walked_file.snapshot,
        ) as stable:
            payload = stable.read_bytes(SEAL_CODE_MAX_FILE_BYTES)
        total_bytes += len(payload)
        if total_bytes > SEAL_CODE_MAX_TOTAL_BYTES:
            raise VerificationError(
                f"Seal source aggregate code bytes exceeds limit: "
                f"{total_bytes}"
            )
        inventory[relative.as_posix()] = payload
    return inventory


def _seal_code_corpus_digest(inventory: dict[str, bytes]) -> str:
    canonical = tuple(
        (relative, _hash_bytes(payload, "sha256"))
        for relative, payload in sorted(inventory.items())
    )
    return _hash_bytes(
        json.dumps(
            canonical, ensure_ascii=False, separators=(",", ":")
        ).encode("utf-8"),
        "sha256",
    )


def _seal_rendered_code_nonce(payload: bytes, relative: str) -> str:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VerificationError(
            f"cannot decode rendered Seal source code {relative}: {error}"
        ) from error
    matches = re.findall(
        r"^  const bootNonce = '([A-Za-z0-9._-]+)'$", text, re.MULTILINE
    )
    if len(matches) != 1:
        raise VerificationError(
            f"rendered Seal source code nonce changed: {relative}"
        )
    return matches[0]


def _verify_seal_code_corpus(root: Path, install: Path) -> str:
    root_inventory = _seal_code_inventory(root, "repository")
    root_digest = _seal_code_corpus_digest(root_inventory)
    if (
        len(root_inventory) != EXPECTED_SEAL_CODE_CORPUS_COUNT
        or root_digest != EXPECTED_SEAL_CODE_CORPUS_SHA256
    ):
        raise VerificationError(
            "Seal source corpus code changed: "
            f"expected_count={EXPECTED_SEAL_CODE_CORPUS_COUNT} "
            f"actual_count={len(root_inventory)} "
            f"expected_sha256={EXPECTED_SEAL_CODE_CORPUS_SHA256} "
            f"actual_sha256={root_digest}"
        )

    install_inventory = _seal_code_inventory(install, "installed")
    if set(install_inventory) != set(root_inventory):
        raise VerificationError(
            "Seal source corpus code paths differ between repository and install: "
            f"missing={sorted(set(root_inventory) - set(install_inventory))} "
            f"extra={sorted(set(install_inventory) - set(root_inventory))}"
        )

    rendered_nonces: list[str] = []
    rendered_relatives: set[str] = set()
    non_seal_rendered_relatives: set[str] = set()
    non_seal_runtime_relatives = {
        relative
        for relative, _renderer in QUEST_RUNTIME_AUDITS
        if relative != "kubejs/server_scripts/afterlight/generated_quest_item_audit.js"
    }
    for relative, root_payload in sorted(root_inventory.items()):
        installed_payload = install_inventory[relative]
        if installed_payload == root_payload:
            continue
        if relative in non_seal_runtime_relatives:
            nonce = _seal_rendered_code_nonce(installed_payload, relative)
            if root_payload.count(QUEST_AUDIT_NONCE_PLACEHOLDER) != 1:
                raise VerificationError(
                    "repository non-Seal quest audit nonce placeholder count changed"
                )
            expected_rendered = root_payload.replace(
                QUEST_AUDIT_NONCE_PLACEHOLDER,
                nonce.encode("ascii"),
                1,
            )
            if installed_payload != expected_rendered:
                raise VerificationError(
                    "installed non-Seal quest audit differs from authenticated "
                    "code-corpus nonce substitution"
                )
            non_seal_rendered_relatives.add(relative)
            rendered_nonces.append(nonce)
            continue
        if relative not in SEAL_RENDERED_CODE_RELATIVES:
            raise VerificationError(
                f"Seal source corpus code bytes differ: {relative}"
            )
        nonce = _seal_rendered_code_nonce(installed_payload, relative)
        if relative == GATE_AUDIT_RELATIVE.as_posix():
            verify_installed_gate_audit(root, install, nonce)
        else:
            placeholder = b"__AFTERLIGHT_BOOT_NONCE__"
            if root_payload.count(placeholder) != 1:
                raise VerificationError(
                    "repository quest audit nonce placeholder count changed"
                )
            expected_rendered = root_payload.replace(
                placeholder, nonce.encode("ascii"), 1
            )
            if installed_payload != expected_rendered:
                raise VerificationError(
                    "installed quest audit differs from authenticated "
                    "code-corpus nonce substitution"
                )
        rendered_relatives.add(relative)
        rendered_nonces.append(nonce)

    if rendered_relatives and (
        rendered_relatives != SEAL_RENDERED_CODE_RELATIVES
        or len(set(rendered_nonces)) != 1
    ):
        raise VerificationError(
            "Seal source corpus rendered code is incomplete or nonce-divergent: "
            f"paths={sorted(rendered_relatives)} nonces={sorted(set(rendered_nonces))}"
        )
    if non_seal_rendered_relatives and (
        non_seal_rendered_relatives != non_seal_runtime_relatives
        or len(set(rendered_nonces)) != 1
    ):
        raise VerificationError(
            "non-Seal quest audit rendered code is incomplete or nonce-divergent: "
            f"paths={sorted(non_seal_rendered_relatives)} "
            f"nonces={sorted(set(rendered_nonces))}"
        )
    return root_digest


def _seal_occurrences(
    root: Path,
    label: str,
    archive_review_labels: dict[str, str] | None = None,
) -> tuple[tuple[str, str], ...]:
    occurrences: list[tuple[str, str]] = []
    archive_budget = {"members": 0, "expanded_bytes": 0}
    review_labels = archive_review_labels or {}

    def record_occurrences(values: Iterable[tuple[str, str]]) -> None:
        for value in values:
            if len(occurrences) >= SEAL_SCAN_MAX_OCCURRENCES:
                raise VerificationError(
                    "Seal source occurrence count exceeds limit: "
                    f"{SEAL_SCAN_MAX_OCCURRENCES}"
                )
            occurrences.append(value)

    def looks_like_zlib(payload: bytes) -> bool:
        if len(payload) < 2:
            return False
        compression_method, flags = payload[0], payload[1]
        return (
            compression_method & 0x0F == 8
            and compression_method >> 4 <= 7
            and ((compression_method << 8) | flags) % 31 == 0
        )

    def account_compressed_payload(
        relative_label: str,
        payload: bytes,
        expanded: bytes,
        compression_depth: int,
        kind: str,
        review_label: str,
    ) -> None:
        if len(expanded) > SEAL_ARCHIVE_MAX_MEMBER_BYTES:
            raise VerificationError(
                f"Seal source compressed payload size exceeds limit: {relative_label}"
            )
        if expanded:
            ratio = len(expanded) / len(payload)
            if ratio > SEAL_ARCHIVE_MAX_COMPRESSION_RATIO:
                raise VerificationError(
                    "Seal source compressed payload ratio exceeds limit: "
                    f"{relative_label} ratio={ratio:.2f}"
                )
        archive_budget["expanded_bytes"] += len(expanded)
        if archive_budget["expanded_bytes"] > SEAL_ARCHIVE_MAX_TOTAL_EXPANDED_BYTES:
            raise VerificationError(
                "Seal source archive aggregate expanded bytes exceeds limit: "
                f"{archive_budget['expanded_bytes']}"
            )
        scan_payload(
            f"{relative_label}!{kind}",
            expanded,
            compression_depth + 1,
            review_label,
        )

    def scan_payload(
        relative_label: str,
        payload: bytes,
        compression_depth: int = 0,
        review_label: str | None = None,
    ) -> None:
        if compression_depth > SEAL_ARCHIVE_MAX_DEPTH:
            raise VerificationError(
                f"Seal source compression nesting depth exceeds limit: {relative_label}"
            )
        effective_review_label = review_label or relative_label
        payload_source = io.BytesIO(payload)
        zip_metadata = _seal_zip_preflight(
            payload_source,
            relative_label,
            required=False,
        )
        if zip_metadata is not None:
            scan_archive(
                relative_label,
                effective_review_label,
                payload_source,
                compression_depth + 1,
                zip_metadata,
            )
            return
        member_label = relative_label.rsplit("!", 1)[-1]
        suffix = PurePosixPath(member_label).suffix.lower()
        if payload.startswith(b"\x1f\x8b") or looks_like_zlib(payload):
            if len(payload) > SEAL_ARCHIVE_MAX_MEMBER_BYTES:
                raise VerificationError(
                    f"Seal source compressed payload exceeds limit: {relative_label}"
                )
            trailing = b""
            if payload.startswith(b"\x1f\x8b"):
                kind = "gzip"
                try:
                    remaining_payload = payload
                    expanded_parts: list[bytes] = []
                    expanded_size = 0
                    compressed_size = 0
                    while remaining_payload.startswith(b"\x1f\x8b"):
                        remaining_budget = (
                            SEAL_ARCHIVE_MAX_MEMBER_BYTES + 1 - expanded_size
                        )
                        if remaining_budget <= 0:
                            raise VerificationError(
                                "Seal source compressed payload size exceeds limit: "
                                f"{relative_label}"
                            )
                        decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
                        expanded_part = decompressor.decompress(
                            remaining_payload,
                            remaining_budget,
                        )
                        if decompressor.unconsumed_tail:
                            raise VerificationError(
                                "Seal source compressed payload size exceeds limit: "
                                f"{relative_label}"
                            )
                        if not decompressor.eof:
                            raise VerificationError(
                                f"cannot decompress {label} Seal source payload "
                                f"{relative_label}: incomplete gzip data"
                            )
                        consumed = len(remaining_payload) - len(
                            decompressor.unused_data
                        )
                        if consumed <= 0:
                            raise VerificationError(
                                f"cannot decompress {label} Seal source payload "
                                f"{relative_label}: empty gzip member"
                            )
                        expanded_parts.append(expanded_part)
                        expanded_size += len(expanded_part)
                        compressed_size += consumed
                        remaining_payload = decompressor.unused_data
                    expanded = b"".join(expanded_parts)
                    compressed_payload = payload[:compressed_size]
                    trailing = remaining_payload
                except zlib.error as error:
                    raise VerificationError(
                        f"cannot decompress {label} Seal source payload "
                        f"{relative_label}: {error}"
                    ) from error
            else:
                kind = "zlib"
                try:
                    decompressor = zlib.decompressobj()
                    expanded = decompressor.decompress(
                        payload,
                        SEAL_ARCHIVE_MAX_MEMBER_BYTES + 1,
                    )
                    if decompressor.unconsumed_tail:
                        raise VerificationError(
                            "Seal source compressed payload size exceeds limit: "
                            f"{relative_label}"
                        )
                    if not decompressor.eof:
                        raise VerificationError(
                            f"cannot decompress {label} Seal source payload "
                            f"{relative_label}: incomplete zlib data"
                        )
                    compressed_size = len(payload) - len(decompressor.unused_data)
                    compressed_payload = payload[:compressed_size]
                    trailing = decompressor.unused_data
                    remaining = SEAL_ARCHIVE_MAX_MEMBER_BYTES + 1 - len(expanded)
                    if remaining > 0:
                        expanded += decompressor.flush(remaining)
                except zlib.error as error:
                    raise VerificationError(
                        f"cannot decompress {label} Seal source payload "
                        f"{relative_label}: {error}"
                    ) from error
            account_compressed_payload(
                relative_label,
                compressed_payload,
                expanded,
                compression_depth,
                kind,
                effective_review_label,
            )
            if trailing:
                scan_payload(
                    f"{relative_label}!{kind}-trailing",
                    trailing,
                    compression_depth + 1,
                    effective_review_label,
                )
            return

        if suffix in (".json", ".mcmeta"):
            if not (b"ascendancy_seal" in payload or b"\\u" in payload):
                return
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as error:
                raise VerificationError(
                    "Seal source corpus cannot decode potential "
                    f"{label} JSON {relative_label}: {error}"
                ) from error
            decoded_escapes = _decode_json_unicode_escapes(text)
            if not (
                SEAL_LITERAL_PATTERN.search(text)
                or SEAL_LITERAL_PATTERN.search(decoded_escapes)
            ):
                return
            try:
                semantic = _json_seal_occurrences(
                    json.loads(text, object_pairs_hook=_JsonObject)
                )
            except json.JSONDecodeError as error:
                raise VerificationError(
                    f"cannot parse {label} Seal source JSON {relative_label}: {error}"
                ) from error
            record_occurrences((relative_label, item) for item in semantic)
            return

        if suffix == ".snbt":
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as error:
                if b"ascendancy_seal" in payload:
                    raise VerificationError(
                        f"cannot decode {label} Seal source SNBT {relative_label}: {error}"
                    ) from error
                return
            textual_count = 0
            remaining_occurrences = SEAL_SCAN_MAX_OCCURRENCES - len(occurrences)
            for _match in SEAL_LITERAL_PATTERN.finditer(text):
                textual_count += 1
                if textual_count > remaining_occurrences:
                    raise VerificationError(
                        "Seal source occurrence count exceeds limit: "
                        f"{SEAL_SCAN_MAX_OCCURRENCES}"
                    )
            if not textual_count:
                return
            try:
                semantic = _snbt_seal_occurrences(_parse_snbt(text))
            except ValueError as error:
                raise VerificationError(
                    f"cannot parse {label} Seal source SNBT {relative_label}: {error}"
                ) from error
            semantic_count = 0
            for item in semantic:
                semantic_count += 1
                record_occurrences(((relative_label, item),))
            if semantic_count != textual_count:
                raise VerificationError(
                    f"cannot account for every {label} Seal source SNBT reference: "
                    f"{relative_label} text={textual_count} "
                    f"semantic={semantic_count}"
                )
            return

        if suffix in SEAL_CODE_SUFFIXES:
            try:
                text = payload.decode("utf-8")
            except UnicodeDecodeError as error:
                if SEAL_BINARY_REFERENCE_PATTERN.search(payload) or b"SEAL" in payload:
                    raise VerificationError(
                        f"cannot decode {label} Seal source code {relative_label}: {error}"
                    ) from error
                return
            for line in text.splitlines():
                if SEAL_CODE_REFERENCE_PATTERN.search(line):
                    record_occurrences(((relative_label, line.strip()),))
            return

        for match in SEAL_BINARY_REFERENCE_PATTERN.finditer(payload):
            record_occurrences(
                ((relative_label, f"binary:offset={match.start()}"),)
            )

    def stream_member_flags(
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        member: PurePosixPath,
    ) -> tuple[bool, bool, bool]:
        suffix = member.suffix.lower()
        needles = [b"ascendancy_seal", b"AFTERLIGHT"]
        if suffix in SEAL_CODE_SUFFIXES:
            needles.append(b"SEAL")
        if suffix in (".json", ".mcmeta"):
            needles.append(b"\\u")
        zip_signatures = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")
        tail = b""
        tail_size = max(
            *(len(needle) for needle in needles),
            *(len(signature) for signature in zip_signatures),
        ) - 1
        first_chunk = True
        try:
            with archive.open(info) as source:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        return False, False, False
                    compressed_payload = first_chunk and (
                        chunk.startswith(b"\x1f\x8b") or looks_like_zlib(chunk)
                    )
                    first_chunk = False
                    window = tail + chunk
                    seal_candidate = any(needle in window for needle in needles)
                    embedded_archive = any(
                        signature in window for signature in zip_signatures
                    )
                    if seal_candidate or embedded_archive or compressed_payload:
                        return seal_candidate, embedded_archive, compressed_payload
                    tail = window[-tail_size:]
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise VerificationError(
                f"cannot stream {label} Seal source archive member "
                f"{info.filename}: {error}"
            ) from error

    def read_archive_member(
        archive: zipfile.ZipFile,
        info: zipfile.ZipInfo,
        relative_label: str,
    ) -> bytes:
        try:
            with archive.open(info) as source:
                payload = source.read(SEAL_ARCHIVE_MAX_MEMBER_BYTES + 1)
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise VerificationError(
                f"cannot read {label} Seal source archive member "
                f"{relative_label}: {error}"
            ) from error
        if len(payload) > SEAL_ARCHIVE_MAX_MEMBER_BYTES:
            raise VerificationError(
                f"Seal source archive member size exceeds limit: {relative_label}"
            )
        if len(payload) != info.file_size:
            raise VerificationError(
                f"Seal source archive member size changed while reading: "
                f"{relative_label} metadata={info.file_size} actual={len(payload)}"
            )
        return payload

    def scan_archive(
        relative_label: str,
        review_label: str,
        source,
        depth: int,
        metadata: _SealZipMetadata | None = None,
    ) -> None:
        if depth > SEAL_ARCHIVE_MAX_DEPTH:
            raise VerificationError(
                f"Seal source archive nesting depth exceeds limit: {relative_label}"
            )
        archive_source = source
        try:
            if metadata is None:
                metadata = _seal_zip_preflight(
                    archive_source,
                    relative_label,
                    required=True,
                )
            if metadata is None:
                raise VerificationError(
                    f"cannot inspect {label} Seal source archive "
                    f"{relative_label}: invalid ZIP"
                )
            archive_source.seek(0)
            with zipfile.ZipFile(archive_source) as archive:
                member_infos = archive.infolist()
                if (
                    len(member_infos) != metadata.members
                    or archive.start_dir != metadata.central_directory_offset
                ):
                    raise VerificationError(
                        "Seal source ZIP metadata changed after preflight: "
                        f"{relative_label}"
                    )
                if len(member_infos) > SEAL_ARCHIVE_MAX_MEMBERS:
                    raise VerificationError(
                        f"Seal source archive member count exceeds limit: "
                        f"{relative_label} count={len(member_infos)}"
                    )
                archive_budget["members"] += len(member_infos)
                if archive_budget["members"] > SEAL_ARCHIVE_MAX_TOTAL_MEMBERS:
                    raise VerificationError(
                        "Seal source archive aggregate member count exceeds limit: "
                        f"{archive_budget['members']}"
                    )

                expanded_bytes = 0
                for info in member_infos:
                    if info.file_size < 0 or info.compress_size < 0:
                        raise VerificationError(
                            f"invalid Seal source archive member size: "
                            f"{relative_label}!{info.filename}"
                        )
                    if info.file_size > SEAL_ARCHIVE_MAX_MEMBER_BYTES:
                        raise VerificationError(
                            "Seal source archive member size exceeds limit: "
                            f"{relative_label}!{info.filename} size={info.file_size}"
                        )
                    if info.file_size:
                        if info.compress_size == 0:
                            raise VerificationError(
                                "Seal source archive compression ratio is unbounded: "
                                f"{relative_label}!{info.filename}"
                            )
                        ratio = info.file_size / info.compress_size
                        if ratio > SEAL_ARCHIVE_MAX_COMPRESSION_RATIO:
                            raise VerificationError(
                                "Seal source archive compression ratio exceeds limit: "
                                f"{relative_label}!{info.filename} ratio={ratio:.2f}"
                            )
                    expanded_bytes += info.file_size

                if expanded_bytes > SEAL_ARCHIVE_MAX_EXPANDED_BYTES:
                    raise VerificationError(
                        "Seal source archive expanded bytes exceed limit: "
                        f"{relative_label} bytes={expanded_bytes}"
                    )
                archive_budget["expanded_bytes"] += expanded_bytes
                if (
                    archive_budget["expanded_bytes"]
                    > SEAL_ARCHIVE_MAX_TOTAL_EXPANDED_BYTES
                ):
                    raise VerificationError(
                        "Seal source archive aggregate expanded bytes exceed limit: "
                        f"{archive_budget['expanded_bytes']}"
                    )

                member_counts = Counter(info.filename for info in member_infos)
                reviewed_payloads: dict[str, bytes] = {}
                for name, count in sorted(member_counts.items()):
                    if count == 1:
                        continue
                    infos = tuple(
                        info for info in member_infos if info.filename == name
                    )
                    reviewed = REVIEWED_DUPLICATE_ZIP_MEMBERS.get(
                        (review_label, name)
                    )
                    if reviewed is None or reviewed[0] != count:
                        raise VerificationError(
                            "duplicate archive member is not an exact reviewed "
                            f"exception: {relative_label}!{name} count={count}"
                        )
                    identities = {
                        _zip_member_alias_identity(info) for info in infos
                    }
                    if len(identities) != 1:
                        raise VerificationError(
                            "duplicate archive member metadata differs across "
                            f"reviewed aliases: {relative_label}!{name} count={count}"
                        )
                    reviewed_payload = _read_reviewed_zip_alias(
                        archive, infos, member_infos, review_label, name
                    )
                    payload_hash = _hash_bytes(reviewed_payload, "sha256")
                    if payload_hash != reviewed[1]:
                        raise VerificationError(
                            "duplicate archive member is not an exact reviewed "
                            f"exception: {relative_label}!{name} count={count} "
                            f"hash={payload_hash}"
                        )
                    reviewed_payloads[name] = reviewed_payload

                scanned_names: set[str] = set()
                for info in sorted(member_infos, key=lambda item: item.filename):
                    if info.filename in scanned_names:
                        continue
                    scanned_names.add(info.filename)
                    if "\\" in info.filename or "\x00" in info.filename:
                        raise VerificationError(
                            f"unsafe archive member in {label} Seal source file: "
                            f"{relative_label}!{info.filename}"
                        )
                    canonical_name = (
                        info.filename[:-1]
                        if info.is_dir() and info.filename.endswith("/")
                        else info.filename
                    )
                    try:
                        member = _safe_relative_path(
                            canonical_name,
                            f"{label} Seal source archive member",
                        )
                    except VerificationError as error:
                        raise VerificationError(
                            f"unsafe archive member in {label} Seal source file: "
                            f"{relative_label}!{info.filename}"
                        ) from error
                    if info.is_dir():
                        continue
                    member_label = f"{relative_label}!{member.as_posix()}"
                    member_review_label = f"{review_label}!/{member.as_posix()}"
                    payload = reviewed_payloads.get(info.filename)
                    declared_archive = member.suffix.lower() in (".jar", ".zip")
                    if declared_archive:
                        if payload is None:
                            payload = read_archive_member(archive, info, member_label)
                        nested_source = io.BytesIO(payload)
                        nested_metadata = _seal_zip_preflight(
                            nested_source,
                            member_label,
                            required=True,
                        )
                        scan_archive(
                            member_label,
                            member_review_label,
                            nested_source,
                            depth + 1,
                            nested_metadata,
                        )
                        continue
                    if payload is not None:
                        nested_source = io.BytesIO(payload)
                        nested_metadata = _seal_zip_preflight(
                            nested_source,
                            member_label,
                            required=False,
                        )
                        if nested_metadata is not None:
                            scan_archive(
                                member_label,
                                member_review_label,
                                nested_source,
                                depth + 1,
                                nested_metadata,
                            )
                            continue
                        scan_payload(
                            member_label,
                            payload,
                            depth,
                            member_review_label,
                        )
                        continue
                    seal_candidate, embedded_archive, compressed_payload = stream_member_flags(
                        archive, info, member
                    )
                    if not (seal_candidate or embedded_archive or compressed_payload):
                        continue
                    payload = read_archive_member(archive, info, member_label)
                    if embedded_archive:
                        nested_source = io.BytesIO(payload)
                        nested_metadata = _seal_zip_preflight(
                            nested_source,
                            member_label,
                            required=False,
                        )
                        if nested_metadata is not None:
                            scan_archive(
                                member_label,
                                member_review_label,
                                nested_source,
                                depth + 1,
                                nested_metadata,
                            )
                        elif seal_candidate or compressed_payload:
                            scan_payload(
                                member_label,
                                payload,
                                depth,
                                member_review_label,
                            )
                    elif seal_candidate or compressed_payload:
                        scan_payload(
                            member_label,
                            payload,
                            depth,
                            member_review_label,
                        )
        except VerificationError:
            raise
        except (OSError, RuntimeError, zipfile.BadZipFile) as error:
            raise VerificationError(
                f"cannot inspect {label} Seal source archive "
                f"{relative_label}: {error}"
            ) from error

    scan_roots: list[PurePosixPath] = []
    for root_name in SEAL_SCAN_ROOTS:
        scan_root = root / root_name
        try:
            root_stat = scan_root.lstat()
        except FileNotFoundError:
            continue
        except OSError as error:
            raise VerificationError(
                f"cannot inspect {label} Seal source root {root_name}: {error}"
            ) from error
        if stat.S_ISLNK(root_stat.st_mode) or not stat.S_ISDIR(root_stat.st_mode):
            raise VerificationError(
                f"invalid {label} Seal source root: {root_name}"
            )
        scan_roots.append(PurePosixPath(root_name))

    code_scan_bytes = 0
    for walked_file in _seal_bounded_walk(root, scan_roots, label):
        relative = walked_file.relative
        suffix = relative.suffix.lower()
        is_code = suffix in SEAL_CODE_SUFFIXES
        with _SealStableFile(
            root,
            relative,
            f"{label} Seal source file",
            max_bytes=SEAL_CODE_MAX_FILE_BYTES if is_code else None,
            size_kind="code file" if is_code else "file",
            expected_identity=walked_file.snapshot,
        ) as stable:
            declared_archive = suffix in (".jar", ".zip")
            metadata = _seal_zip_preflight(
                stable.handle,
                relative.as_posix(),
                required=declared_archive,
            )
            if metadata is not None:
                scan_archive(
                    relative.as_posix(),
                    review_labels.get(relative.as_posix(), relative.as_posix()),
                    stable.handle,
                    1,
                    metadata,
                )
                continue
            raw_limit = (
                SEAL_CODE_MAX_FILE_BYTES
                if is_code
                else SEAL_ARCHIVE_MAX_MEMBER_BYTES
            )
            if stable.size > raw_limit:
                size_kind = "code file" if is_code else "raw file"
                raise VerificationError(
                    f"Seal source {size_kind} size exceeds limit: "
                    f"{relative.as_posix()} size={stable.size}"
                )
            payload = stable.read_bytes(raw_limit)
            if is_code:
                code_scan_bytes += len(payload)
                if code_scan_bytes > SEAL_CODE_MAX_TOTAL_BYTES:
                    raise VerificationError(
                        "Seal source aggregate code bytes exceeds limit: "
                        f"{code_scan_bytes}"
                    )
            scan_payload(relative.as_posix(), payload)
    return tuple(occurrences)


def verify_seal_sources(
    root: Path | str, install: Path | str
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    code_corpus_sha256 = _verify_seal_code_corpus(root_path, install_path)
    archive_review_labels = _seal_archive_review_labels(root_path)
    inventories = {
        "root": _seal_occurrences(root_path, "repository"),
        "install": _seal_occurrences(
            install_path, "installed", archive_review_labels
        ),
    }
    for label, inventory in inventories.items():
        actual = Counter(inventory)
        unexpected = actual - EXPECTED_SEAL_OCCURRENCES
        missing = EXPECTED_SEAL_OCCURRENCES - actual
        if unexpected or missing:
            raise VerificationError(
                f"Seal source corpus {label} changed: "
                f"unexpected={sorted(unexpected.items())} "
                f"missing={sorted(missing.items())}"
            )
    if Counter(inventories["root"]) != Counter(inventories["install"]):
        raise VerificationError("Seal source corpus root and install differ")
    canonical = tuple(sorted(Counter(inventories["root"]).items()))
    digest = _hash_bytes(
        json.dumps(canonical, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        ),
        "sha256",
    )
    return {
        **inventories,
        "sha256": digest,
        "code_corpus_sha256": code_corpus_sha256,
    }


SIGNED_SAFE_FTB_ID = re.compile(r"^[0-7][0-9A-F]{15}$")
QUEST_IDENTITY_SPELL_BOOK_DEFAULT_COMPONENT = {
    "data": [],
    "maxSpells": "5",
    "mustEquip": "1b",
    "spellWheel": "1b",
}
QUEST_IDENTITY_ORDER_NORMALIZATIONS = {
    "chapter": {
        "099200314296766A": (22, 9),
        "758F5AEF697F7EFD": (20, 7),
        "7C611E8A94BC5CE5": (21, 8),
    },
    "reward_table": {
        "17E69C9CFEA907D4": (10, 3),
        "182578C414DC8A45": (11, 4),
        "399722D6E7EF5835": (12, 5),
    },
}
QUEST_IDENTITY_REVIEWED_REWARD_TABLES = {
    "1369E4AACBCDF5A1": ("ascendancy_cache", "Ascendancy Cache"),
    "5D9DAC80C11182CF": (
        "ascendancy_cache_rare",
        "Ascendancy Cache: Rare",
    ),
    "1A4FA21B1999BDD5": (
        "ascendancy_cache_epic",
        "Ascendancy Cache: Epic",
    ),
    "17E69C9CFEA907D4": ("depot_early", "Requisition Depot: Early"),
    "182578C414DC8A45": ("depot_mid", "Requisition Depot: Mid"),
    "399722D6E7EF5835": ("depot_late", "Requisition Depot: Late"),
}
QUEST_IDENTITY_DATA_SAVE_DEFAULTS = {
    "fallback_locale": "",
    "verify_on_load": False,
    "presets": {
        "goal": {"shape": "hexagon", "size": "2.0d"},
        "info": {"shape": "gear", "size": "1.0d"},
        "normal": {"shape": "square", "size": "1.0d"},
    },
}


def _quest_identity_mapping(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise VerificationError(f"{label} must be an SNBT compound")
    return value


def _quest_identity_list(value: object, label: str) -> list:
    if not isinstance(value, list):
        raise VerificationError(f"{label} must be an SNBT list")
    return value


def _quest_identity_id(value: object, label: str) -> str:
    if not isinstance(value, str) or SIGNED_SAFE_FTB_ID.fullmatch(value) is None:
        raise VerificationError(
            f"{label} is not a signed-safe FTB ID: {value!r}"
        )
    return value


def _quest_identity_type(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise VerificationError(f"{label} must be a non-empty string")
    return value


def _quest_identity_copy(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _quest_identity_copy(child) for key, child in value.items()}
    if isinstance(value, list):
        return [_quest_identity_copy(child) for child in value]
    return value


def _quest_identity_repository_object(
    value: object,
    label: str,
    kind: str,
) -> dict:
    identity = _quest_identity_mapping(_quest_identity_copy(value), label)
    if identity.get("type") == "item":
        expected_count = "1L" if kind == "task" else "1"
        if "count" not in identity:
            raise VerificationError(
                f"repository {label} must retain explicit count {expected_count}"
            )
        item = _quest_identity_mapping(identity.get("item"), f"{label} item")
        if (
            item.get("id") == "irons_spellbooks:copper_spell_book"
            and isinstance(item.get("components"), dict)
            and item["components"].get("irons_spellbooks:spell_container")
            == QUEST_IDENTITY_SPELL_BOOK_DEFAULT_COMPONENT
        ):
            raise VerificationError(
                "repository Iron's Spells item contains an installed save default"
            )
    if kind == "table_reward":
        if identity.get("type") != "item":
            raise VerificationError(
                f"repository {label} must retain explicit item type"
            )
        if "weight" not in identity:
            raise VerificationError(
                f"repository {label} must retain explicit reward weight"
            )
    return identity


def _quest_identity_installed_item(
    value: object,
    repository_value: object,
    label: str,
) -> dict:
    installed = _quest_identity_mapping(_quest_identity_copy(value), label)
    repository = _quest_identity_mapping(
        _quest_identity_copy(repository_value), f"repository {label}"
    )
    if repository.get("id") != "irons_spellbooks:copper_spell_book":
        return installed
    if "components" in repository:
        return installed
    components = installed.get("components")
    if not isinstance(components, dict):
        return installed
    if (
        components.get("irons_spellbooks:spell_container")
        != QUEST_IDENTITY_SPELL_BOOK_DEFAULT_COMPONENT
    ):
        return installed
    components.pop("irons_spellbooks:spell_container")
    if not components:
        installed.pop("components")
    return installed


def _quest_identity_installed_object(
    value: object,
    repository_value: object | None,
    label: str,
    kind: str,
) -> dict:
    identity = _quest_identity_mapping(_quest_identity_copy(value), label)
    if not isinstance(repository_value, dict):
        return identity
    repository = _quest_identity_mapping(
        _quest_identity_copy(repository_value), f"repository {label}"
    )
    if (
        kind == "table_reward"
        and "type" not in identity
        and repository.get("type") == "item"
        and "item" in identity
    ):
        identity["type"] = "item"
    if identity.get("type") == "item" and repository.get("type") == "item":
        identity["item"] = _quest_identity_installed_item(
            identity.get("item"), repository.get("item"), f"{label} item"
        )
        expected_count = "1L" if kind == "task" else "1"
        if "count" not in identity and repository.get("count") == expected_count:
            identity["count"] = expected_count
    if (
        kind == "table_reward"
        and "weight" not in identity
        and repository.get("weight") == "1.0f"
    ):
        identity["weight"] = "1.0f"
    return identity


def _quest_identity_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _quest_identity_order_index(value: dict, label: str) -> int:
    order_index = value.get("order_index")
    if not isinstance(order_index, str) or re.fullmatch(r"-?[0-9]+", order_index) is None:
        raise VerificationError(f"{label} order_index must be an integer")
    return int(order_index)


def _quest_identity_require_unique_orders(
    values: Sequence[tuple[str, str, int]],
) -> None:
    by_scope: dict[str, list[tuple[int, str]]] = {}
    for identifier, scope, order_index in values:
        by_scope.setdefault(scope, []).append((order_index, identifier))
    for scope, entries in by_scope.items():
        order_indices = [order_index for order_index, _identifier in entries]
        if len(set(order_indices)) != len(order_indices):
            raise VerificationError(
                f"quest identity corpus {scope} has duplicate order_index values"
            )


def _quest_identity_canonical_order(
    kind: str,
    identifier: str,
    order_index: int,
    repository_orders: dict[str, int] | None,
) -> int:
    normalization = QUEST_IDENTITY_ORDER_NORMALIZATIONS[kind].get(identifier)
    if repository_orders is None:
        if normalization is not None and order_index != normalization[0]:
            raise VerificationError(
                f"repository {kind} {identifier} order_index changed: "
                f"expected={normalization[0]} actual={order_index}"
            )
        return order_index
    repository_order = repository_orders.get(identifier)
    if repository_order is None:
        return order_index
    if normalization is None:
        return order_index
    if repository_order != normalization[0] or order_index not in normalization:
        raise VerificationError(
            f"installed {kind} {identifier} order_index is not characterized: "
            f"repository={repository_order} installed={order_index}"
        )
    return repository_order


def _quest_identity_parse(root: Path, relative: PurePosixPath, label: str) -> dict:
    path = _verified_regular_file(root, relative, label)
    try:
        text = path.read_text(encoding="utf-8")
        parsed = _parse_snbt(text)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        raise VerificationError(
            f"cannot parse {label} {relative.as_posix()}: {error}"
        ) from error
    return _quest_identity_mapping(parsed, label)


def _quest_identity_localization_records(
    root: Path,
    quest_root: Path,
    quest_relative: PurePosixPath,
    label: str,
) -> tuple[tuple[str, ...], ...]:
    lang_root = _validated_root(quest_root / "lang", f"{label} localization root")
    records: list[tuple[str, ...]] = []
    for directory, directory_names, file_names in os.walk(
        lang_root, followlinks=False
    ):
        directory_path = Path(directory)
        directory_names.sort()
        file_names.sort()
        for name in directory_names:
            child = directory_path / name
            child_stat = child.lstat()
            if stat.S_ISLNK(child_stat.st_mode) or not stat.S_ISDIR(
                child_stat.st_mode
            ):
                raise VerificationError(
                    f"invalid {label} localization directory: "
                    f"{child.relative_to(lang_root).as_posix()}"
                )
        for name in file_names:
            path = directory_path / name
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if relative.suffix != ".snbt":
                raise VerificationError(
                    f"unexpected {label} localization file: {relative.as_posix()}"
                )
            verified = _verified_regular_file(
                root, relative, f"{label} localization file"
            )
            try:
                text = verified.read_text(encoding="utf-8")
                parsed = _parse_snbt(text)
                _scalars, key_tokens = _SnbtPathScanner(text).scan()
            except (OSError, UnicodeDecodeError, ValueError) as error:
                raise VerificationError(
                    f"cannot parse {label} localization {relative.as_posix()}: "
                    f"{error}"
                ) from error
            localization = _quest_identity_mapping(
                parsed, f"{label} localization {relative.as_posix()}"
            )
            top_level_keys = [
                token.value for parent_path, token in key_tokens if not parent_path
            ]
            if len(top_level_keys) != len(key_tokens):
                raise VerificationError(
                    f"nested compound in {label} localization {relative.as_posix()}"
                )
            if len(top_level_keys) != len(set(top_level_keys)):
                raise VerificationError(
                    f"duplicate key in {label} localization {relative.as_posix()}"
                )
            if set(top_level_keys) != set(localization):
                raise VerificationError(
                    f"unaccounted key in {label} localization {relative.as_posix()}"
                )
            localization_relative = path.relative_to(lang_root).as_posix()
            records.append(
                (
                    "localization_file",
                    localization_relative,
                    f"{len(top_level_keys):08d}",
                )
            )
            for key, value in localization.items():
                if isinstance(value, str):
                    records.append(
                        (
                            "localization_scalar",
                            localization_relative,
                            key,
                            value,
                        )
                    )
                    continue
                if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value
                ):
                    raise VerificationError(
                        f"invalid {label} localization value for {key}"
                    )
                records.append(
                    (
                        "localization_array",
                        localization_relative,
                        key,
                        f"{len(value):08d}",
                    )
                )
                for position, item in enumerate(value):
                    records.append(
                        (
                            "localization_text",
                            localization_relative,
                            key,
                            f"{position:08d}",
                            item,
                        )
                    )
    return tuple(records)


def _quest_identity_data(
    value: object,
    label: str,
    repository_value: object | None,
) -> dict:
    data = _quest_identity_mapping(_quest_identity_copy(value), label)
    if repository_value is None:
        unexpected = sorted(set(data) & set(QUEST_IDENTITY_DATA_SAVE_DEFAULTS))
        if unexpected:
            raise VerificationError(
                f"repository data.snbt contains installed save defaults: {unexpected}"
            )
        return data
    repository = _quest_identity_mapping(
        _quest_identity_copy(repository_value), "repository data.snbt"
    )
    for key, default in QUEST_IDENTITY_DATA_SAVE_DEFAULTS.items():
        if key in repository or key not in data:
            continue
        if data[key] == default:
            data.pop(key)
    return data


def _quest_identity_inventory(
    root: Path,
    label: str,
    repository_reference: dict[str, object] | None = None,
) -> tuple[tuple[tuple[str, ...], ...], dict[str, object]]:
    quest_relative = PurePosixPath("config/ftbquests/quests")
    quest_root = _validated_root(root / quest_relative, f"{label} quest root")
    records: list[tuple[str, ...]] = []
    is_repository = repository_reference is None
    reference = repository_reference or {
        "objects": {},
        "chapter_orders": {},
        "reward_table_orders": {},
        "reward_tables": {},
        "reward_table_glows": {},
    }
    objects = reference["objects"]
    chapter_orders = reference["chapter_orders"]
    reward_table_orders = reference["reward_table_orders"]
    reward_tables = reference["reward_tables"]
    reward_table_glows = reference["reward_table_glows"]
    if not all(
        isinstance(value, dict)
        for value in (
            objects,
            chapter_orders,
            reward_table_orders,
            reward_tables,
            reward_table_glows,
        )
    ):
        raise VerificationError("invalid repository quest identity reference")

    data_relative = quest_relative / "data.snbt"
    data = _quest_identity_parse(root, data_relative, f"{label} data.snbt")
    canonical_data = _quest_identity_data(
        data,
        f"{label} data.snbt",
        None if is_repository else reference.get("data"),
    )
    if is_repository:
        reference["data"] = _quest_identity_copy(canonical_data)
    records.append(("data", _quest_identity_json(canonical_data)))
    records.extend(
        _quest_identity_localization_records(
            root, quest_root, quest_relative, label
        )
    )

    groups_relative = quest_relative / "chapter_groups.snbt"
    groups_data = _quest_identity_parse(root, groups_relative, f"{label} chapter groups")
    groups = _quest_identity_list(
        groups_data.get("chapter_groups"), f"{label} chapter_groups"
    )
    for position, group_value in enumerate(groups):
        group = _quest_identity_mapping(
            group_value, f"{label} chapter group {position}"
        )
        group_id = _quest_identity_id(
            group.get("id"), f"{label} chapter group {position} ID"
        )
        records.append(
            (
                "group",
                f"{position:08d}",
                group_id,
                _quest_identity_json(group),
            )
        )

    chapter_directory = _validated_root(
        quest_root / "chapters", f"{label} chapter directory"
    )
    chapters: list[tuple[Path, PurePosixPath, dict, str, str, str, int]] = []
    for path in sorted(chapter_directory.glob("*.snbt")):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        chapter = _quest_identity_parse(root, relative, f"{label} chapter")
        chapter_id = _quest_identity_id(
            chapter.get("id"), f"{label} chapter {relative.name} ID"
        )
        filename = _quest_identity_id(
            chapter.get("filename"), f"{label} chapter {relative.name} filename"
        )
        group_id = _quest_identity_id(
            chapter.get("group"), f"{label} chapter {relative.name} group"
        )
        stem = _quest_identity_id(path.stem, f"{label} chapter file stem")
        order_index = _quest_identity_order_index(
            chapter, f"{label} chapter {chapter_id}"
        )
        chapters.append(
            (path, relative, chapter, chapter_id, filename, group_id, order_index)
        )

    _quest_identity_require_unique_orders(
        tuple(
            (chapter_id, group_id, order_index)
            for _path, _relative, _chapter, chapter_id, _filename, group_id, order_index
            in chapters
        )
    )
    for path, relative, chapter, chapter_id, filename, group_id, order_index in chapters:
        canonical_order = _quest_identity_canonical_order(
            "chapter",
            chapter_id,
            order_index,
            None if is_repository else chapter_orders,
        )
        if is_repository:
            chapter_orders[chapter_id] = order_index
        chapter_semantics = _quest_identity_copy(chapter)
        chapter_semantics.pop("quests", None)
        chapter_semantics.pop("order_index", None)
        records.append(
            (
                "chapter",
                path.stem,
                chapter_id,
                filename,
                group_id,
                str(canonical_order),
                _quest_identity_json(chapter_semantics),
            )
        )
        quests = _quest_identity_list(
            chapter.get("quests"), f"{label} chapter {chapter_id} quests"
        )
        for quest_position, quest_value in enumerate(quests):
            quest = _quest_identity_mapping(
                quest_value,
                f"{label} chapter {chapter_id} quest {quest_position}",
            )
            quest_id = _quest_identity_id(
                quest.get("id"),
                f"{label} chapter {chapter_id} quest {quest_position} ID",
            )
            quest_semantics = _quest_identity_copy(quest)
            quest_semantics.pop("tasks", None)
            quest_semantics.pop("rewards", None)
            records.append(
                (
                    "quest",
                    chapter_id,
                    f"{quest_position:08d}",
                    quest_id,
                    _quest_identity_json(quest_semantics),
                )
            )
            dependencies = _quest_identity_list(
                quest.get("dependencies", []),
                f"{label} quest {quest_id} dependencies",
            )
            for dependency_position, dependency_value in enumerate(dependencies):
                dependency = _quest_identity_id(
                    dependency_value, f"{label} quest {quest_id} dependency"
                )
                records.append(
                    (
                        "dependency",
                        quest_id,
                        f"{dependency_position:08d}",
                        dependency,
                    )
                )
            for kind in ("tasks", "rewards"):
                values = _quest_identity_list(
                    quest.get(kind), f"{label} quest {quest_id} {kind}"
                )
                singular = kind[:-1]
                for position, object_value in enumerate(values):
                    identity = _quest_identity_mapping(
                        object_value,
                        f"{label} quest {quest_id} {singular} {position}",
                    )
                    identity_id = _quest_identity_id(
                        identity.get("id"),
                        f"{label} quest {quest_id} {singular} {position} ID",
                    )
                    object_key = (singular, identity_id)
                    if is_repository:
                        normalized_identity = _quest_identity_repository_object(
                            identity,
                            f"quest {quest_id} {singular} {identity_id}",
                            singular,
                        )
                        if object_key in objects:
                            raise VerificationError(
                                f"duplicate repository quest identity object: {object_key}"
                            )
                        objects[object_key] = _quest_identity_copy(
                            normalized_identity
                        )
                    else:
                        normalized_identity = _quest_identity_installed_object(
                            identity,
                            objects.get(object_key),
                            f"quest {quest_id} {singular} {identity_id}",
                            singular,
                        )
                    identity_type = _quest_identity_type(
                        normalized_identity.get("type"),
                        f"{label} quest {quest_id} {singular} {identity_id} type",
                    )
                    records.append(
                        (
                            singular,
                            quest_id,
                            f"{position:08d}",
                            identity_id,
                            identity_type,
                            _quest_identity_json(normalized_identity),
                        )
                    )

    table_directory = _validated_root(
        quest_root / "reward_tables", f"{label} reward table directory"
    )
    tables: list[tuple[Path, dict, str, int]] = []
    for path in sorted(table_directory.glob("*.snbt")):
        relative = PurePosixPath(path.relative_to(root).as_posix())
        table = _quest_identity_parse(root, relative, f"{label} reward table")
        table_id = _quest_identity_id(
            table.get("id"), f"{label} reward table {relative.name} ID"
        )
        order_index = _quest_identity_order_index(
            table, f"{label} reward table {table_id}"
        )
        tables.append((path, table, table_id, order_index))

    _quest_identity_require_unique_orders(
        tuple(
            (table_id, "reward_tables", order_index)
            for _path, _table, table_id, order_index in tables
        )
    )
    observed_table_ids: set[str] = set()
    for path, table, table_id, order_index in tables:
        observed_table_ids.add(table_id)
        canonical_order = _quest_identity_canonical_order(
            "reward_table",
            table_id,
            order_index,
            None if is_repository else reward_table_orders,
        )
        reviewed = QUEST_IDENTITY_REVIEWED_REWARD_TABLES.get(table_id)
        if reviewed is None:
            raise VerificationError(f"unreviewed reward table in {label}: {table_id}")
        if is_repository:
            actual_metadata = (table.get("filename"), table.get("title"))
            if actual_metadata != reviewed or path.stem != reviewed[0]:
                raise VerificationError(
                    f"reviewed reward table metadata changed for {table_id}: "
                    f"expected={reviewed} actual={actual_metadata} path={path.stem}"
                )
            reward_tables[table_id] = reviewed
            reward_table_orders[table_id] = order_index
        else:
            repository_metadata = reward_tables.get(table_id)
            if repository_metadata != reviewed:
                raise VerificationError(
                    f"repository reward table metadata is missing for {table_id}"
                )
            for key, expected in zip(("filename", "title"), reviewed, strict=True):
                actual = table.get(key)
                if actual is None:
                    table[key] = expected
                elif actual != expected:
                    raise VerificationError(
                        f"installed reviewed reward table {key} changed for "
                        f"{table_id}: expected={expected!r} actual={actual!r}"
                    )
        table_semantics = _quest_identity_copy(table)
        table_semantics.pop("order_index", None)
        loot_crate = table_semantics.get("loot_crate")
        if isinstance(loot_crate, dict):
            glow = loot_crate.get("glow")
            if is_repository:
                if glow is not None and not isinstance(glow, bool):
                    raise VerificationError(
                        f"repository reward table glow encoding changed for {table_id}"
                    )
                reward_table_glows[table_id] = glow
            else:
                repository_glow = reward_table_glows.get(table_id)
                if glow == "1b" and repository_glow is True:
                    loot_crate["glow"] = True
                elif glow == "0b" and repository_glow is False:
                    loot_crate["glow"] = False
        table_rewards = _quest_identity_list(
            table_semantics.get("rewards"), f"{label} reward table {table_id} rewards"
        )
        normalized_rewards: list[dict] = []
        for position, reward_value in enumerate(table_rewards):
            raw_reward = _quest_identity_mapping(
                reward_value,
                f"{label} reward table {table_id} reward {position}",
            )
            reward_id = _quest_identity_id(
                raw_reward.get("id"),
                f"{label} reward table {table_id} reward {position} ID",
            )
            object_key = ("table_reward", reward_id)
            if is_repository:
                reward = _quest_identity_repository_object(
                    raw_reward,
                    f"reward table {table_id} reward {reward_id}",
                    "table_reward",
                )
                if object_key in objects:
                    raise VerificationError(
                        f"duplicate repository quest identity object: {object_key}"
                    )
                objects[object_key] = _quest_identity_copy(reward)
            else:
                reward = _quest_identity_installed_object(
                    raw_reward,
                    objects.get(object_key),
                    f"reward table {table_id} reward {reward_id}",
                    "table_reward",
                )
            _quest_identity_type(
                reward.get("type"),
                f"{label} reward table {table_id} reward {reward_id} type",
            )
            normalized_rewards.append(reward)
        table_semantics["rewards"] = normalized_rewards
        records.append(
            (
                "reward_table",
                path.stem,
                table_id,
                str(canonical_order),
                _quest_identity_json(table_semantics),
            )
        )

    if is_repository and observed_table_ids != set(
        QUEST_IDENTITY_REVIEWED_REWARD_TABLES
    ):
        raise VerificationError(
            "repository reviewed reward table set changed: "
            f"expected={sorted(QUEST_IDENTITY_REVIEWED_REWARD_TABLES)} "
            f"actual={sorted(observed_table_ids)}"
        )
    return tuple(sorted(records)), reference


def verify_quest_identity_stability(
    root: Path | str, install: Path | str
) -> dict[str, object]:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    try:
        root_inventory, repository_reference = _quest_identity_inventory(
            root_path, "repository"
        )
        install_inventory, _reference = _quest_identity_inventory(
            install_path,
            "installed",
            repository_reference,
        )
    except VerificationError as error:
        raise VerificationError(f"quest identity corpus invalid: {error}") from error
    inventories = {
        "root": root_inventory,
        "install": install_inventory,
    }
    root_counter = Counter(inventories["root"])
    install_counter = Counter(inventories["install"])
    if root_counter != install_counter:
        unexpected = install_counter - root_counter
        missing = root_counter - install_counter
        raise VerificationError(
            "quest identity corpus changed after FTB save: "
            f"unexpected={sorted(unexpected.items())[:20]} "
            f"missing={sorted(missing.items())[:20]}"
        )
    digest = _hash_bytes(
        json.dumps(
            inventories["root"],
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8"),
        "sha256",
    )
    return {
        **inventories,
        "count": len(inventories["root"]),
        "sha256": digest,
    }


def _gate_audit_source(root: Path | str) -> bytes:
    root_path = _validated_root(root, "pack root")
    source_path = _verified_regular_file(
        root_path, GATE_AUDIT_RELATIVE, "Gate audit source"
    )
    try:
        source = source_path.read_bytes()
        text = source.decode("utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise VerificationError(
            f"cannot read Gate audit source {source_path}: {error}"
        ) from error
    for placeholder in (
        GATE_AUDIT_SHA256_PLACEHOLDER,
        GATE_AUDIT_NONCE_PLACEHOLDER,
    ):
        if source.count(placeholder) != 1:
            raise VerificationError(
                "Gate audit placeholder count changed for "
                f"{placeholder.decode('ascii')}"
            )
    if text.count("ServerEvents.loaded(") != 1:
        raise VerificationError(
            "Gate audit source must contain exactly one ServerEvents.loaded listener"
        )
    if text.count("[AFTERLIGHT GATE RECIPE AUDIT] OK") != 1:
        raise VerificationError(
            "Gate audit source must contain exactly one success marker"
        )
    for helper in (
        "afterlightRecipe",
        "afterlightMechanicalInput",
        "afterlightCraftingInput",
        "afterlightAssertMatch",
        "afterlightAssertNoMatch",
        "afterlightAssertOnlySealRemainder",
    ):
        if text.count(f"function {helper}(") != 1:
            raise VerificationError(
                f"Gate audit helper contract changed for {helper}"
            )
    success_emitter = (
        "  console.info(`[AFTERLIGHT GATE RECIPE AUDIT] OK "
        "${auditSha256} 11 ${bootNonce}`)"
    )
    if text.count(success_emitter) != 1:
        raise VerificationError("Gate audit success emitter changed")
    return source


def gate_audit_expectation(root: Path | str) -> tuple[str, int]:
    source = _gate_audit_source(root)
    return _hash_bytes(source, "sha256"), GATE_AUDIT_RECIPE_COUNT


def render_installed_gate_audit(root: Path | str, nonce: str) -> bytes:
    if re.fullmatch(r"[A-Za-z0-9._-]+", nonce) is None:
        raise VerificationError("installed Gate audit nonce is malformed")
    source = _gate_audit_source(root)
    digest = _hash_bytes(source, "sha256").encode("ascii")
    return source.replace(
        GATE_AUDIT_SHA256_PLACEHOLDER, digest, 1
    ).replace(GATE_AUDIT_NONCE_PLACEHOLDER, nonce.encode("ascii"), 1)


def _install_rendered_gate_audit(
    root: Path | str, install: Path | str, nonce: str
) -> str:
    root_path = _validated_root(root, "pack root")
    install_path = _validated_root(install, "install root")
    source = _gate_audit_source(root_path)
    installed_path = _verified_regular_file(
        install_path, GATE_AUDIT_RELATIVE, "installed Gate audit"
    )
    try:
        installed_source = installed_path.read_bytes()
    except OSError as error:
        raise VerificationError(
            f"cannot read installed Gate audit {installed_path}: {error}"
        ) from error
    if installed_source != source:
        raise VerificationError(
            "installed Gate audit pre-substitution bytes differ from root source"
        )
    rendered = render_installed_gate_audit(root_path, nonce)
    try:
        installed_path.write_bytes(rendered)
    except OSError as error:
        raise VerificationError(
            f"cannot write installed Gate audit {installed_path}: {error}"
        ) from error
    return verify_installed_gate_audit(root_path, install_path, nonce)


def verify_installed_gate_audit(
    root: Path | str, install: Path | str, nonce: str
) -> str:
    expected = render_installed_gate_audit(root, nonce)
    install_path = _validated_root(install, "install root")
    installed_path = _verified_regular_file(
        install_path, GATE_AUDIT_RELATIVE, "installed Gate audit"
    )
    try:
        actual = installed_path.read_bytes()
    except OSError as error:
        raise VerificationError(
            f"cannot read installed Gate audit {installed_path}: {error}"
        ) from error
    if actual != expected:
        raise VerificationError(
            "installed Gate audit differs from authenticated source substitutions"
        )
    return _hash_bytes(actual, "sha256")


def validate_boot_markers(
    log_text: str,
    nonce: str,
    status: int,
    root: Path | str | None = None,
) -> tuple[tuple[str, tuple[str, str, str, str, tuple[str, ...]]], ...]:
    if status != 0:
        raise VerificationError(f"server exit status {status} is not a graceful exit")
    records = parse_log_records(log_text)
    root_path = (
        _validated_root(root, "pack root")
        if root is not None
        else Path(__file__).resolve().parents[1]
    )
    audit_digest, audit_count = quest_audit_expectation(root_path)
    audit_message = (
        f"[AFTERLIGHT QUEST ITEM AUDIT] OK {audit_digest} {audit_count} {nonce}"
    )
    gate_digest, gate_count = gate_audit_expectation(root_path)
    gate_message = (
        f"[AFTERLIGHT GATE RECIPE AUDIT] OK {gate_digest} {gate_count} {nonce}"
    )
    ftb_message = "Loaded 6 chapter groups, 47 chapters, 315 quests, 6 reward tables"

    def exact_single(
        record: LogRecord,
        thread_pattern: str,
        logger: str,
        message: str,
    ) -> bool:
        return (
            record.level == "INFO"
            and re.fullmatch(thread_pattern, record.thread) is not None
            and record.logger == logger
            and record.message == message
            and not record.continuations
        )

    marker_specs: list[
        tuple[str, Callable[[LogRecord], bool], str | None]
    ] = [
        (
            "IDAS READY",
            lambda record: exact_single(
                record,
                r"modloading-worker-\d+",
                IDAS_COMPAT_LOGGER,
                IDAS_COMPAT_READY_MESSAGE,
            ),
            None,
        )
    ]
    marker_specs.extend(
        (
            f"IDAS SANITIZED {position}",
            lambda record, message=message: exact_single(
                record, r"Worker-Main-\d+", IDAS_COMPAT_LOGGER, message
            ),
            None,
        )
        for position, message in enumerate(
            IDAS_COMPAT_BOOT_SANITIZED_MESSAGES, start=1
        )
    )
    done_pattern = re.compile(
        r'Done \(\d+(?:\.\d+)?s\)! For help, type "help"'
    )
    marker_specs.extend(
        (
            (
                "DedicatedServer Done",
                lambda record: (
                    record.thread == "Server thread"
                    and record.level == "INFO"
                    and record.logger
                    == "net.minecraft.server.dedicated.DedicatedServer/"
                    and done_pattern.fullmatch(record.message) is not None
                    and not record.continuations
                ),
                'Done (<SECONDS>s)! For help, type "help"',
            ),
            (
                "quest audit",
                lambda record: exact_single(
                    record, r"Server thread", "KubeJS Server/", audit_message
                ),
                None,
            ),
            (
                "Gate audit",
                lambda record: exact_single(
                    record, r"Server thread", "KubeJS Server/", gate_message
                ),
                None,
            ),
            (
                "FTB Quests load",
                lambda record: exact_single(
                    record, r"Server thread", "FTB Quests/", ftb_message
                ),
                None,
            ),
            (
                "stopping",
                lambda record: exact_single(
                    record,
                    r"Server thread",
                    "net.minecraft.server.MinecraftServer/",
                    "Stopping server",
                ),
                None,
            ),
            (
                "saving players",
                lambda record: exact_single(
                    record,
                    r"Server thread",
                    "net.minecraft.server.MinecraftServer/",
                    "Saving players",
                ),
                None,
            ),
            (
                "saving worlds",
                lambda record: exact_single(
                    record,
                    r"Server thread",
                    "net.minecraft.server.MinecraftServer/",
                    "Saving worlds",
                ),
                None,
            ),
            (
                "all dimensions saved",
                lambda record: exact_single(
                    record,
                    r"Server thread",
                    "net.minecraft.server.MinecraftServer/",
                    "ThreadedAnvilChunkStorage: All dimensions are saved",
                ),
                None,
            ),
        )
    )

    selected: list[tuple[str, int, LogRecord, str | None]] = []
    for label, predicate, normalized_message in marker_specs:
        matches = [
            (index, record)
            for index, record in enumerate(records)
            if predicate(record)
        ]
        if len(matches) != 1:
            raise VerificationError(
                f"boot state marker {label} count mismatch: expected 1, got {len(matches)}"
            )
        index, record = matches[0]
        selected.append((label, index, record, normalized_message))

    selected_by_label = {
        label: (index, record, normalized_message)
        for label, index, record, normalized_message in selected
    }
    ordered_labels = tuple(
        label
        for label, _, _, _ in selected
        if label not in ("quest audit", "Gate audit")
    )
    ordered_indices = tuple(selected_by_label[label][0] for label in ordered_labels)
    all_indices = tuple(index for _, index, _, _ in selected)
    if (
        ordered_indices != tuple(sorted(ordered_indices))
        or len(set(all_indices)) != len(all_indices)
    ):
        raise VerificationError(
            f"boot state marker order changed: {tuple(label for label, _, _, _ in selected)}"
        )
    done_index = selected_by_label["DedicatedServer Done"][0]
    ftb_index = selected_by_label["FTB Quests load"][0]
    for label in ("quest audit", "Gate audit"):
        audit_index = selected_by_label[label][0]
        if not done_index < audit_index < ftb_index:
            raise VerificationError(
                f"boot state marker {label} is outside the post-Done, pre-FTB window"
            )
    sanitized_threads = {
        record.thread for _, _, record, _ in selected[1:5]
    }
    if len(sanitized_threads) != 1:
        raise VerificationError(
            f"IDAS SANITIZED worker thread changed within run: {sanitized_threads}"
        )

    projection = []
    for label, _, record, normalized_message in selected:
        canonical = canonical_record_tuple(record)
        if normalized_message is not None:
            canonical = (
                canonical[0],
                canonical[1],
                canonical[2],
                normalized_message,
                canonical[4],
            )
        projection.append((label, canonical))
    return tuple(projection)


FILTER_METADATA = {
    "pack": {
        "description": "AFTERLIGHT RC hygiene resource filter",
        "pack_format": 48,
    },
    "filter": {
        "block": [
            {
                "namespace": "^create_enchantment_industry$",
                "path": r"^data_maps/fluid/unit/experience\.json$",
            }
        ]
    },
}


def filter_matches(
    namespace_pattern: str, path_pattern: str, namespace: str, path: str
) -> bool:
    return bool(re.fullmatch(namespace_pattern, namespace)) and bool(
        re.fullmatch(path_pattern, path)
    )


def build_filter_archive() -> bytes:
    payload = (json.dumps(FILTER_METADATA, indent=2) + "\n").encode("utf-8")
    output = io.BytesIO()
    entry = zipfile.ZipInfo("pack.mcmeta", date_time=(1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_STORED
    entry.create_system = 3
    entry.external_attr = 0o100644 << 16
    entry.extra = b""
    entry.comment = b""
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        archive.comment = b""
        archive.writestr(entry, payload)
    return output.getvalue()


def _cli_verify_manifest(args: argparse.Namespace) -> None:
    result = verify_manifest(Path(args.root))
    verify_better_strongholds_contract(Path(args.root))
    signal = verify_signal_runtime_identity(Path(args.root), result)
    print(
        "MANIFEST: OK "
        f"pack={result['pack_hash']} index={result['index_hash']} "
        f"files={len(result['indexed_hashes'])} "
        f"signal-route={signal['route_quests']}"
    )


def _cli_verify_install_root(args: argparse.Namespace) -> None:
    install = _validated_root(
        Path(args.install), "install root", must_exist=not args.allow_missing
    )
    print(f"INSTALL ROOT: OK {install}")


def _cli_verify_provenance(args: argparse.Namespace) -> None:
    result = verify_install_provenance(Path(args.root), Path(args.install))
    verify_reviewed_server_artifact_inventory(result)
    artifacts = result["afterlightServerArtifacts"]
    print(
        "PROVENANCE: OK "
        f"server-artifacts={artifacts['count']} "
        f"sha256={artifacts['digest']}"
    )


def _cli_verify_boot(args: argparse.Namespace) -> None:
    result = verify_boot_run(
        Path(args.root), Path(args.install), args.nonce, args.status
    )
    print(
        "BOOT ORACLE: OK "
        f"errors={sum(result['errors'].values())} "
        f"warnings={result['warning_records']} "
        f"named-residuals={sum(result['warnings'].values())}"
    )


def _cli_verify_quest_audit(args: argparse.Namespace) -> None:
    digest = verify_installed_quest_audit(
        Path(args.root), Path(args.install), args.nonce
    )
    print(f"QUEST AUDIT BYTES: OK sha256={digest}")


def _cli_render_installed_quest_audits(args: argparse.Namespace) -> None:
    result = render_installed_quest_audits(
        Path(args.root),
        Path(args.install),
        args.nonce,
    )
    print(
        "QUEST AUDIT RENDER: OK "
        f"audits={len(result['audits'])} nonce={result['nonce']}"
    )


def _cli_verify_quest_audits(args: argparse.Namespace) -> None:
    result = verify_installed_quest_audits(
        Path(args.root),
        Path(args.install),
        args.nonce,
    )
    print(
        "QUEST AUDIT BYTES: OK "
        f"audits={len(result['audits'])} nonce={result['nonce']}"
    )


def _cli_render_installed_gate_audit(args: argparse.Namespace) -> None:
    digest = _install_rendered_gate_audit(
        Path(args.root), Path(args.install), args.nonce
    )
    print(f"GATE AUDIT RENDER: OK sha256={digest}")


def _cli_verify_gate_audit(args: argparse.Namespace) -> None:
    digest = verify_installed_gate_audit(
        Path(args.root), Path(args.install), args.nonce
    )
    print(f"GATE AUDIT BYTES: OK sha256={digest}")


def _cli_verify_seal_sources(args: argparse.Namespace) -> None:
    result = verify_seal_sources(Path(args.root), Path(args.install))
    print(
        "SEAL SOURCES: OK "
        f"occurrences={len(result['root'])} sha256={result['sha256']} "
        f"code-corpus-sha256={result['code_corpus_sha256']}"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AFTERLIGHT RC hygiene verifier")
    subparsers = parser.add_subparsers(dest="command", required=True)
    manifest = subparsers.add_parser("verify-manifest")
    manifest.add_argument("--root", default=".")
    manifest.set_defaults(handler=_cli_verify_manifest)
    install_root = subparsers.add_parser("verify-install-root")
    install_root.add_argument("--install", required=True)
    install_root.add_argument("--allow-missing", action="store_true")
    install_root.set_defaults(handler=_cli_verify_install_root)
    provenance = subparsers.add_parser("verify-provenance")
    provenance.add_argument("--root", default=".")
    provenance.add_argument("--install", required=True)
    provenance.set_defaults(handler=_cli_verify_provenance)
    quest_audit = subparsers.add_parser("verify-quest-audit")
    quest_audit.add_argument("--root", default=".")
    quest_audit.add_argument("--install", required=True)
    quest_audit.add_argument("--nonce", required=True)
    quest_audit.set_defaults(handler=_cli_verify_quest_audit)
    quest_audit_render = subparsers.add_parser(
        "render-installed-quest-audits"
    )
    quest_audit_render.add_argument("--root", default=".")
    quest_audit_render.add_argument("--install", required=True)
    quest_audit_render.add_argument("--nonce", required=True)
    quest_audit_render.set_defaults(
        handler=_cli_render_installed_quest_audits
    )
    quest_audits = subparsers.add_parser("verify-quest-audits")
    quest_audits.add_argument("--root", default=".")
    quest_audits.add_argument("--install", required=True)
    quest_audits.add_argument("--nonce", required=True)
    quest_audits.set_defaults(handler=_cli_verify_quest_audits)
    gate_render = subparsers.add_parser("render-installed-gate-audit")
    gate_render.add_argument("--root", default=".")
    gate_render.add_argument("--install", required=True)
    gate_render.add_argument("--nonce", required=True)
    gate_render.set_defaults(handler=_cli_render_installed_gate_audit)
    gate_audit = subparsers.add_parser("verify-gate-audit")
    gate_audit.add_argument("--root", default=".")
    gate_audit.add_argument("--install", required=True)
    gate_audit.add_argument("--nonce", required=True)
    gate_audit.set_defaults(handler=_cli_verify_gate_audit)
    seal_sources = subparsers.add_parser("verify-seal-sources")
    seal_sources.add_argument("--root", default=".")
    seal_sources.add_argument("--install", required=True)
    seal_sources.set_defaults(handler=_cli_verify_seal_sources)
    boot = subparsers.add_parser("verify-boot")
    boot.add_argument("--root", default=".")
    boot.add_argument("--install", required=True)
    boot.add_argument("--nonce", required=True)
    boot.add_argument("--status", required=True, type=int)
    boot.set_defaults(handler=_cli_verify_boot)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except VerificationError as error:
        print(f"RC HYGIENE: FAILED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
