#!/usr/bin/env python3

from pathlib import Path

from afterlight_quests.echo_route import build_echo_route, write_echo_route


ROOT = Path(__file__).resolve().parents[1]
QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"
OUTPUT = ROOT / "config" / "afterlight" / "echo_route.json"


def main() -> int:
    write_echo_route(QUEST_ROOT, OUTPUT)
    route = build_echo_route(QUEST_ROOT)
    quest_count = sum(len(segment["quests"]) for segment in route["segments"])
    print(
        f"BUILD ECHO ROUTE: OK ({len(route['segments'])} segments, "
        f"{quest_count} quests)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
