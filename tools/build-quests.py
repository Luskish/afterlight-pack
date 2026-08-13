#!/usr/bin/env python3

import copy
from pathlib import Path
from typing import Sequence

from afterlight_quests import (
    ChapterSpec,
    build_catalog,
    validate_quests,
    write_catalog,
    write_legacy_quest_overlays,
)
from afterlight_quests.builder import COMMODITY_FIXTURE_RELATIVE, _parse_snbt
from afterlight_quests.acquisition import (
    ACQUISITION_AUDIT_RELATIVE,
    FIXTURE_RELATIVE,
)
from afterlight_quests.quest_build_transaction import (
    PromotionResult,
    QuestBuildTransaction,
    candidate_workspace,
    quest_build_dependency_roots,
)


ROOT = Path(__file__).resolve().parents[1]
QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"


def _legacy_quest_ids(
    quest_root: Path,
    catalog: Sequence[ChapterSpec],
) -> tuple[str, ...]:
    current_managed_chapters = {chapter.id for chapter in catalog}
    quest_ids: list[str] = []
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        chapter = _parse_snbt(path.read_text(encoding="utf-8"))
        if (
            not isinstance(chapter, dict)
            or chapter.get("id") != path.stem
            or not isinstance(chapter.get("quests"), list)
        ):
            raise ValueError(f"malformed unmanaged chapter in {path}")
        if path.stem in current_managed_chapters:
            continue
        for quest in chapter["quests"]:
            if not isinstance(quest, dict) or not isinstance(quest.get("id"), str):
                raise ValueError(f"malformed unmanaged quest in {path}")
            quest_ids.append(quest["id"])
    return tuple(quest_ids)


def _build_quests(
    root: Path,
    *,
    catalog: Sequence[ChapterSpec] | None = None,
) -> PromotionResult:
    quest_root = root / "config" / "ftbquests" / "quests"
    managed_catalog = copy.deepcopy(
        tuple(build_catalog() if catalog is None else catalog)
    )
    audit_paths = (
        root
        / "kubejs"
        / "server_scripts"
        / "afterlight"
        / "generated_quest_item_audit.js",
        root / ACQUISITION_AUDIT_RELATIVE,
    )
    with QuestBuildTransaction(root) as transaction:
        frozen = transaction.freeze(
            (
                *quest_build_dependency_roots(
                    root,
                    include_validation_inputs=True,
                ),
                root / FIXTURE_RELATIVE,
                root / COMMODITY_FIXTURE_RELATIVE,
            )
        )
        with candidate_workspace(transaction, frozen) as candidate_root:
            candidate_quest_root = (
                candidate_root / quest_root.relative_to(root)
            )
            candidate_mods = candidate_root / "server-test" / "mods"
            legacy_quest_ids = _legacy_quest_ids(
                candidate_quest_root,
                managed_catalog,
            )
            catalog_result = write_catalog(
                managed_catalog,
                candidate_quest_root,
                legacy_quest_ids=legacy_quest_ids,
                transaction=transaction,
            )
            if catalog_result.cleanup_warnings:
                raise RuntimeError(
                    "candidate catalog write returned cleanup warnings: "
                    + "; ".join(
                        str(warning) for warning in catalog_result.cleanup_warnings
                    )
                )
            write_legacy_quest_overlays(
                candidate_quest_root,
                catalog=managed_catalog,
                known_quest_ids=legacy_quest_ids,
                transaction=transaction,
            )
            errors = validate_quests(candidate_quest_root, candidate_mods)
            if errors:
                raise ValueError(
                    "quest corpus validation failed:\n" + "\n".join(errors)
                )
            writes, deletions = frozen.candidate_changes(
                candidate_root,
                (quest_root, *audit_paths),
            )

        def validate_promoted_corpus() -> None:
            promoted_errors = validate_quests(
                quest_root,
                root / "server-test" / "mods",
            )
            if promoted_errors:
                raise ValueError(
                    "quest corpus validation failed:\n"
                    + "\n".join(promoted_errors)
                )

        promotion = transaction.promote_bytes(
            writes,
            frozen,
            deletions=deletions,
            post_validate=validate_promoted_corpus,
        )
    return PromotionResult(
        (
            quest_root / "chapters" / f"{chapter.id}.snbt"
            for chapter in managed_catalog
        ),
        cleanup_warnings=promotion.cleanup_warnings,
        recovery_paths=promotion.recovery_paths,
    )


def main() -> int:
    written = _build_quests(ROOT)
    if written.cleanup_warnings:
        print(
            "BUILD QUESTS: COMMITTED WITH CLEANUP WARNINGS "
            f"({len(written.cleanup_warnings)} warnings, "
            f"{len(written.recovery_paths)} retained recovery paths)"
        )
        for warning in written.cleanup_warnings:
            print(f"CLEANUP WARNING: {warning}")
        for path in written.recovery_paths:
            print(f"RETAINED RECOVERY: {path}")
        return 2
    print(f"BUILD QUESTS: OK ({len(written)} compiler-managed chapters written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
