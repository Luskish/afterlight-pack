#!/usr/bin/env python3
from pathlib import Path

from rc_hygiene import build_filter_archive


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "kubejs" / "data" / "afterlight_rc_hygiene.zip"


def main() -> None:
    ARCHIVE.write_bytes(build_filter_archive())
    print(f"FILTER: WROTE {ARCHIVE}")


if __name__ == "__main__":
    main()
