from __future__ import annotations

from .builder import ChapterSpec, GroupSpec


STORY = GroupSpec("story", "The Story", "4525BB3160467FCB")
CERTIFICATIONS = GroupSpec("certifications", "Certifications", "CA20F33642175B95")
UNDERCURRENT = GroupSpec("undercurrent", "The Undercurrent", "51FF272F5030D2E6")
DEEP_VAULT = GroupSpec("deep-vault", "The Deep Vault", "4DEAD1F5F7AB4DA3")
ATLAS = GroupSpec(
    "atlas",
    "Atlas of the Broken World",
    "C8F8381D9519D002",
)


def build_catalog() -> list[ChapterSpec]:
    return []
