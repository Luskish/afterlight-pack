# AFTERLIGHT Plan 04: Quest Framework + Act I

> **For agentic workers:** AGENTS.md binding. Read `.agents/skills/ftb-quests/SKILL.md` before touching SNBT. All quest text lives in `config/ftbquests/quests/lang/en_us.snbt`, written in ECHO's voice (dry, precise, a fragmentary AI recovering itself; no em dashes ever). IDs are 16-char uppercase hex, 0-9 A-F only. Verify: server boot OK + no ftbquests errors in logs + SNBT loads (grep "quests" boot log).

**Goal:** The quest book exists, themed around ECHO, with chapter-group architecture for the whole pack and a genuinely playable Act I opening (Chapter 1 complete, Chapter 2 + first Certification started). Chit economy live from quest one.

**Architecture:** 5 chapter groups: The Story (acts), Certifications, The Undercurrent, The Deep Vault, Atlas of the Broken World. Story chapters gate by dependencies (soft); memory-fragment lore beats are chapter-completion rewards. Generator script `tools/gen-quests.py` emits SNBT + lang from a single python source of truth (IDs generated once, then stable; the file becomes hand-editable after generation and the generator is retired rather than re-run over hand edits).

## Tasks

- [x] Task 1: data.snbt + chapter_groups.snbt + group lang
- [x] Task 2: Chapter 1 "Cold Boot" (12 quests, full ECHO text, chit rewards, memory fragment finale)
- [x] Task 3: Chapter 2 "Scavenger's Creed" opening (6 quests) + Certification: Kinetics I (6 quests, bulk capstone pattern)
- [x] Task 4: Boot verification (ftbquests loads clean), ship, HANDOFF
- [ ] Later (Plan 05+): remaining Act I chapters, reward tables/caches as loot crates, book theming resource pack, per-chapter images
