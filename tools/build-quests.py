#!/usr/bin/env python3

from pathlib import Path
from typing import Sequence

from afterlight_quests import (
    ChapterSpec,
    build_catalog,
    validate_quests,
    write_catalog,
    write_legacy_quest_overlays,
)
from afterlight_quests.builder import _load_managed_state, _parse_snbt


ROOT = Path(__file__).resolve().parents[1]
QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"


def _legacy_quest_ids(quest_root: Path) -> tuple[str, ...]:
    managed_chapters, _ = _load_managed_state(
        quest_root / ".afterlight-managed.json"
    )
    quest_ids: list[str] = []
    for path in sorted((quest_root / "chapters").glob("*.snbt")):
        if path.stem in managed_chapters:
            continue
        chapter = _parse_snbt(path.read_text(encoding="utf-8"))
        if not isinstance(chapter, dict) or not isinstance(chapter.get("quests"), list):
            raise ValueError(f"malformed unmanaged chapter in {path}")
        for quest in chapter["quests"]:
            if not isinstance(quest, dict) or not isinstance(quest.get("id"), str):
                raise ValueError(f"malformed unmanaged quest in {path}")
            quest_ids.append(quest["id"])
    return tuple(quest_ids)


def _build_quests(
    root: Path,
    *,
    catalog: Sequence[ChapterSpec] | None = None,
) -> list[Path]:
    quest_root = root / "config" / "ftbquests" / "quests"
    managed_catalog = tuple(build_catalog() if catalog is None else catalog)
    legacy_quest_ids = _legacy_quest_ids(quest_root)
    written = write_catalog(
        managed_catalog,
        quest_root,
        legacy_quest_ids=legacy_quest_ids,
    )
    write_legacy_quest_overlays(
        quest_root,
        catalog=managed_catalog,
        known_quest_ids=legacy_quest_ids,
    )
    errors = validate_quests(quest_root, root / "server-test" / "mods")
    if errors:
        raise ValueError("quest corpus validation failed:\n" + "\n".join(errors))
    return written


def main() -> int:
    written = _build_quests(ROOT)
    print(f"BUILD QUESTS: OK ({len(written)} compiler-managed chapters written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
