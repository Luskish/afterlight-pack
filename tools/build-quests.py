#!/usr/bin/env python3

from pathlib import Path

from afterlight_quests import build_catalog, write_catalog


ROOT = Path(__file__).resolve().parents[1]
QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"


def main() -> int:
    written = write_catalog(build_catalog(), QUEST_ROOT)
    print(f"BUILD QUESTS: OK ({len(written)} compiler-managed chapters written)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
