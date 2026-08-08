#!/usr/bin/env python3

import argparse

from pathlib import Path

from afterlight_quests import count_quests, validate_quests


ROOT = Path(__file__).resolve().parents[1]
QUEST_ROOT = ROOT / "config" / "ftbquests" / "quests"
MODS_DIR = ROOT / "server-test" / "mods"
RUNTIME_LOGS = (
    ROOT / "server-test" / "logs" / "latest.log",
    ROOT / "server-test" / "logs" / "debug.log",
    ROOT / "server-test" / "logs" / "kubejs" / "server.log",
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--static",
        action="store_true",
        help="skip the fresh runtime registry digest requirement before a server boot",
    )
    args = parser.parse_args()
    errors = validate_quests(
        QUEST_ROOT,
        MODS_DIR,
        runtime_logs=RUNTIME_LOGS,
        require_runtime_audit=not args.static,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"VALIDATE QUESTS: FAILED ({len(errors)} errors)")
        return 1
    counts = count_quests(QUEST_ROOT)
    print(
        "VALIDATE QUESTS: OK "
        f"({counts.chapters} chapters, {counts.quests} quests, "
        f"{counts.tasks} tasks, {counts.rewards} rewards)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
