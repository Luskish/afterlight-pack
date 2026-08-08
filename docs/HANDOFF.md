# AFTERLIGHT Handoff Guide

For continuing this project in Codex, a fresh Claude session, or any capable agent. Last updated: 2026-08-08 by Codex during the final autonomous build. Codex is executing Plans 05-07 on `dev`; the three executable plan files now exist under `docs/superpowers/plans/`.

## Active completion run (Codex)

- Goal: finish all 20 story chapters, side groups, certifications, Gate finale, VPS package, the 0.9.0 release candidate, and full-project gauntlet. Version 1.0.0 remains gated by Shane's manual acceptance matrix.
- Active plan: `docs/superpowers/plans/2026-08-08-afterlight-05-acts-ii-iii.md`.
- Queued plans: `docs/superpowers/plans/2026-08-08-afterlight-06-finale.md` and `docs/superpowers/plans/2026-08-08-afterlight-07-launch.md`.
- Current checkpoint: Plan 05 Task 5 is complete on `dev`. Resume at Plan 05 Task 6, Side Group Completion.
- Task 5 certifications and Depot: added six compiler-managed certification chapters with 36 quests covering Logistics I, Ore Loop I, Autocrafting I, Cross-Mod I, Power I, and Infrastructure II. Their finales award the exact stable stages required by Chapter 16. The legacy Kinetics I finale now awards `afterlight_cert_kinetics_i` without changing any existing chapter, quest, task, or reward ID. Infrastructure II checks all six prerequisite stages before four bulk quotas and an unattended recovery check. Three repeatable Requisition Depot chapters consume 8, 16, or 32 Chits and grant a choice from progression-safe early, mid, or late supply tables. Depot quests use exact FTB Quests 2101.1.30 fields `can_repeat`, `repeat_cooldown`, `consume_items`, `choice`, and numeric `table_id`. The full corpus is now 29 chapters, 199 quests, 218 tasks, 282 quest rewards, and 4 reward tables. A clean dedicated-server boot loaded all counts, KubeJS loaded 1/1 startup scripts and 5/5 server scripts with zero script errors and zero script warnings, and the runtime item audit passed all 160 registry IDs. Thirty-four unit tests, static validation, runtime validation, Packwiz idempotence, and `VERIFY: ALL GREEN` passed.
- Task 4 Act III: compiler-managed Story Chapters 12-16 add exactly 47 named quests, bringing the full corpus to 20 chapters, 160 quests, 173 tasks, and 230 rewards. The five chapters are `Frontier Machines`, `The War Below`, `Quantum Weather`, `The Long Sky`, and `Architect`, with exact deterministic finale IDs recorded in tests. Each finale restores Memory Fragments 11-15, awards an Ascendancy Cache, Chits, XP, its exact progression item, and its exact stage. Chapter 16 proves the four schematic stages and seven certification stages. Its final Gate Blueprint task is a readiness checkmark, not a Draconic item task: Draconic progression is seal-gated until after Chapter 20, so requiring `draconicevolution:awakened_core` here would be circular. A regression forbids every Act III task from referencing `draconicevolution:`. A clean dedicated-server boot loaded 6 chapter groups, 20 chapters, 160 quests, and 1 reward table. KubeJS loaded 1/1 startup scripts and 5/5 server scripts with zero script errors and zero script warnings. The runtime audit passed all 138 referenced and allowlisted registry IDs. Unit tests, static validation, runtime validation, Packwiz idempotence, and `VERIFY: ALL GREEN` all passed. Existing upstream recipe fallback warnings remain queued for the release gauntlet and were not introduced by Task 4.
- Task 3 Act II: compiler-managed Story Chapters 6-11 add exactly 57 named quests, bringing the corpus to 15 chapters, 113 quests, 117 tasks, and 163 rewards. Chapter 6 starts from legacy Chapter 5 finale `DA407B47132C07C6`; every later chapter starts from the prior finale. Memory Fragments 05-10, six Ascendancy Caches, Chits, XP, and the single `kubejs:deep_vault_key` reward are in their specified finales. Independent review corrected the AE2 on-ramp to require the Logic Processor Press and a complete minimum autocrafting setup. The clean dedicated-server boot loaded 6 chapter groups, 15 chapters, 113 quests, and 1 reward table. The runtime item audit passed all 111 referenced and allowlisted registry IDs. KubeJS loaded 1/1 startup scripts and 5/5 server scripts with 0 script errors and 0 warnings. Four pre-existing IDAS optional-biome tag messages still log at KubeJS ERROR level and remain a release-gauntlet cleanup item; they are unrelated to quest scripts or Task 3 data.
- Task 2 progression items: registered and boot-verified `kubejs:deep_vault_key`, `kubejs:schematic_kinetic_frame`, `kubejs:schematic_industrial_anchor`, `kubejs:schematic_isotopic_core`, `kubejs:schematic_lattice_matrix`, `kubejs:gate_blueprint`, and `kubejs:undercurrent_stabilizer_precursor`. The generated runtime item audit now includes every entry in `KUBEJS_ITEM_ALLOWLIST`, covering these seven plus `kubejs:requisition_chit` and `kubejs:ascendancy_seal`. The fresh boot marker passed with 59 total audited registry IDs, KubeJS loaded 1/1 startup and 5/5 server scripts with 0 errors, and FTB Quests loaded 6 chapter groups, 9 chapters, 56 quests, and 1 reward table.
- Task 1 recovery state: `python3 tools/build-quests.py` writes only chapters declared in `tools/afterlight_quests/catalog.py`, removes stale compiler-owned output through `.afterlight-managed.json`, preserves legacy localization, and emits a digest-bound KubeJS runtime item audit. `python3 tools/validate-quests.py --static` checks structure before boot; the default command additionally requires the matching runtime registry digest from a fresh server boot. The invalid `sophisticated_backpacks:backpack` reference was corrected to `sophisticatedbackpacks:backpack` without changing quest or task IDs, then covered by the runtime registry audit.
- Recovery instruction if interrupted: run `git status`, read this section and the three plan files, then resume at Plan 05 Task 6. Do not rerun any retired `tools/gen-quests*.py` script. All four retired scripts are committed with mode `100644`, not executable.
- Plan 07 audit correction: AutoModpack and empty-host recovery are mandatory; use one `/data` bind plus separate backups; never auto-restore a partially migrated world; pin packwiz-installer-bootstrap v0.0.3 and verify its SHA-256. Automated completion releases `0.9.0-rc1`; `1.0.0` waits for Shane's manual client, multiplayer, voice, AutoModpack, gameplay, and restore matrix.

## Current state (verified, not aspirational)

- Repo: https://github.com/Luskish/afterlight-pack (public). `main` = stable, `dev` = working branch, both pushed and identical at Plan 01 completion.
- Auto-update URL live and byte-exact: https://luskish.github.io/afterlight-pack/pack.toml (GitHub Pages from main root).
- CI (`pack-ci`) green on main and dev: manifest integrity, both exports build (no artifacts uploaded: friends-only policy), full headless NeoForge server boot on ubuntu.
- Pack: see the live progress table below for current mod count and wave state. Baseline platform: NeoForge 21.1.248, MC 1.21.1. Modrinth-sourced mods are live-API verified by `tools/verify-pack.sh`; CurseForge-sourced mods show SKIP there and are validated by the server boot + CI instead.
- Friend-facing artifact `dist/AFTERLIGHT-prism-instance.zip` is built but NOT yet distribution-approved: Shane must first do one manual Prism import + launch (client-side boot has never been exercised; needs a Microsoft account).
- The design spec, the completed Plan 01 (with the Plan 02-07 roadmap table), and six committed project skills in `.agents/skills/` are all in this repo.

## Plan 04 status: CORE COMPLETE (2026-08-08)

Plan doc: docs/superpowers/plans/2026-08-08-afterlight-04-quests-act1.md. The quest book EXISTS and boot-loads clean (FTB Quests: 6 chapter groups, 3 chapters, 22 quests, translations OK). Delivered: data.snbt (flexible progression), 5 chapter groups (Story, Certifications, Undercurrent, Deep Vault, Atlas), Chapter 1 "Cold Boot" (12 quests, full ECHO voice, memory fragment 01, chit economy live), Chapter 2 "Scavenger's Creed" opening (5 quests), Certification: Kinetics I (6 quests, bulk capstone pattern). Chapter ids: ch1 DB93C6934B230CFB, ch2 4C01977EF77930A6, kinetics 23643435F7BE74AC. tools/gen-quests.py was a ONE-SHOT generator: NEVER re-run it (fresh ids would orphan the committed files + lang); hand-edit the SNBT or use the in-game editor from here on. Chapter 3 "The Scarlands" (5 quests, memory fragment 02, biome/structure/dimension tasks) + Ascendancy Cache reward table with loot crate (string_id ascendancy_cache, table 9369E4AACBCDF5A1) shipped via ADDITIVE generator tools/gen-quests-ch3.py (also one-shot: retired; append-only lang pattern is the template for future chapters). FTB Quests loads: 4 chapters, 27 quests, 1 reward table, clean. Chapter 4 "Foothold" shipped (7 quests, ACT I COMPLETE: memory fragment 03, IE steel arc, first FE, energy task, act-finale cache): additive generator tools/gen-quests-ch4.py (retired). FTB Quests: 5 chapters, 34 quests. Item ids jar-verified before writing (workbench/ingot_steel/coke_oven/heat_generator). Theme shipped (global_packs/required_resources/afterlight_theme: ECHO cyan on vault-dark, ftb_quests_theme.txt). Act II OPENED: Chapter 5 "The Engine Room" (6 quests, Mekanism entry arc, memory fragment 04, ids jar-verified) via retired one-shot tools/gen-quests-ch5.py. FTB Quests: 6 chapters, 40 quests. Undercurrent opener "Anomalous Readings" shipped (5 quests, Ars Nouveau taste arc, foreshadows the Gate stabilizer; ids jar-verified). FTB Quests: 7 chapters, 45 quests, all boot-verified. NEXT UP (in order): Certification: Logistics I, Act II ch6 (AE2 "The Lattice"), Act II ch7 (Create logistics/trains), cache tiers (rare/epic), per-chapter images, Undercurrent ch2 (Occultism), Deep Vault ch2 (MI electric age). DONE this morning: Deep Vault opener (5 quests, MI steam), Atlas opener "Expedition Log" (6 quests, five dimension expeditions, dimension ids jar-verified: aether:the_aether, twilightforest:twilight_forest, undergarden:undergarden, deeperdarker:otherside, eternal_starlight:starlight). Book state: 9 chapters, 56 quests, every group populated. The additive-generator pattern (see tools/gen-quests-ch5.py as the cleanest template): new ids, append-only lang, jar-verify item ids first, boot after, never re-run a retired generator.

## Plan 03 status: CORE COMPLETE (2026-08-08)

Plan doc: docs/superpowers/plans/2026-08-08-afterlight-03-integration.md. Delivered and boot-verified (10 recipes added, 0 kubejs errors): custom items requisition_chit + ascendancy_seal (textures + lang included), Draconic entry recipes seal-gated (exact-copy replacements from jar JSONs), Create crushing + IE crusher accept Mekanism raw ores (osmium/uranium/lead/tin, conservative yields), chit loot injection into five structure chest tables. LESSONS: .withChance() dead on 1.21, use CreateItem.of(item, chance); IE recipes via event.custom with jar-extracted schema; mekanism has NO raw_fluorite. Remaining Plan 03 scope folded forward: MMR Gate multiblocks land with Plan 06 (their consumer), more bridges with Plan 05.

## Plan 02 status: COMPLETE (merged to main 2026-08-08)

The full plan is written: `docs/superpowers/plans/2026-08-08-afterlight-02-roster.md` (Task 0 hardening + Waves 1-13 + verification sweep + configs). Resume at the first wave below not marked complete, following the plan's Wave Pattern exactly.

### Plan 02 live progress (update after every wave)

| Task | Status | Notes |
|---|---|---|
| Task 0 hardening (3 commits) | COMPLETE | .nojekyll live, Pages verified 200 post-deploy, CI hardened + packwiz pinned (dfd8b68) |
| W1 Tech spine A | COMPLETE | 37 mods total. CF-sourced (Modrinth-absent): Applied Flux, ExtendedAE (file ex-pattern-provider.pw.toml), Glodium dep. LESSONS: pipe `printf 'Y\n'` into every `packwiz mr add` (dep prompts EOF-abort otherwise); slug extendedae on Modrinth is the WRONG mod (Plus addon). POLICY: CI no longer uploads pack artifacts (CF-sourced mods embed jars in mrpack overrides; friends-only). verify-pack check 1 now tests true refresh idempotence, works mid-wave. |
| W2 Tech spine B (MILESTONE) | COMPLETE | 63 mods total. Local server boot OK with full tech spine. Modrinth slug is `enderio` not ender-io. CF-sourced: LaserIO, RFTools Base/Utility/Power, Compact Machines (slug compact-machines), Flux Networks, Just Dire Things (slug just-dire-things). CF name-search trap: "Compact Machines" query offers Preview Fixer first, use exact slugs. Modrinth-absent on 1.21.1: Compact Machines, Flux Networks, Just Dire Things. |
| W3 Create set | COMPLETE | 73 mods. All 7 requested + 3 legit required deps (Sable via Aeronautics, Create: Dragons Plus via Enchantment Industry, Kotlin for Forge via Slice and Dice). All Modrinth-native. |
| W4 Deep Vault (MILESTONE) | COMPLETE | 74 mods. ENGINE SWAP (Shane-approved, spec amended): Modern Industrialization replaces GTCEu. GTCEu 7.0.x crashes dedicated servers (client class on server dist); GTCEu 1.4.6 incompatible with Create 6 (IStressValueProvider removed). Both proven by boot tests. MI 2.5.6 boots green. Revisit GTCEu at 26.x migration. |
| W5 Undercurrent magic | COMPLETE | 81 mods. 4 requested + legit deps: curios (W9 want), modonomicon (W12 want), smartbrainlib. All Modrinth-native. |
| W6 Dangerous world (MILESTONE) | COMPLETE | 101 mods, boot OK. Slugs: l_enders-cataclysm (underscore), bosses-of-mass-destruction-forge. CF: alexs-mobs-1-21-1-port (+Citadel port dep). LESSON: Modrinth dep metadata MISSES some required libs; boot revealed irons_lib + lodestonelib missing (wave 5 gap, fixed here). Slug lodestone = a datapack, the lib is lodestonelib. Non-milestone waves rely on CI boot for this class of catch. |
| W7 Worldgen/structures | COMPLETE | 124 mods. IDAS slug is idas; it pulled Quark (W9 want, early), Supplementaries, Integrated API as required deps. All Modrinth-native. |
| W8 Dimensions (MILESTONE) | COMPLETE | 134 mods, boot OK. Slugs: deeperdarker; Twilight Forest is CF-only (the-twilight-forest). LESSON: Stardust multi-version projects can resolve 26.x jars that PASS the API check but fail to load (filename says 26.2): Structory + Towers repinned to 1.21.x version URLs (MXU49bpN, lefqbuOP). Also fixed undeclared libs moonlight (Supplementaries) + zeta (Quark). Verify-pack improvement candidate: flag filenames with a different MC line than 1.21. |
| W9 Storage/QoL 2 | COMPLETE | 142 mods. quark+curios arrived early via deps in W5/W7. Inventory Sorter is CF-only (slug inventory-sorter); Modrinth veinminer-client is correctly side=client. |
| W10 Food | COMPLETE | Farmers Delight + My Nethers Delight + Kaleidoscope Cookery. |
| W11 Multiplayer | COMPLETE | 151 mods. FTB suite is CF-only: slugs ftb-teams-forge/ftb-chunks-forge/ftb-ranks-forge (+ftb-library-forge dep) but plain ftb-essentials. SVC + LuckPerms Modrinth-native. W10 note: mynethersdelight not on Modrinth 1.21.1, skipped per plan.
| W12 Story/scripting (MILESTONE) | COMPLETE | 161 mods, boot OK. Slugs: almostunified (no hyphen), CF ftb-quests-forge + ftb-xmod-compat + immersive-messages-api; Global Packs CF slug is global-datapacks. Modonomicon was already in via W5. |
| W13 Endgame + perf 2 | COMPLETE | 167 mods. Draconic Evolution via CF (beta, post-story gating comes in Plan 03). Perf adds correctly side=client. gpumemleakfix not found on CF under any slug: SKIPPED (minor, revisit). |
| Task 14 verification sweep | COMPLETE | 167 mods: boot OK, verify-pack ALL GREEN, exports build (mrpack 90M with CF-sourced mods embedded in overrides, CF zip 662M: BOTH friends-only now), client-side audit clean (10 render/UI mods), 156 server jars. |
| Task 15 configs + main merge | COMPLETE | AU priorities (mekanism>enderio>ie>create>oritech>MI), FTB Chunks 2000 claims/100 forceload, FTB Essentials 5 homes, all boot-verified. Merge executed under Shane's blanket keep-going authorization (2026-08-08, asleep); zero friends consume the channel yet (instance zip never distributed), so publish moment is inert. PLAN 02 CLOSED. |

## Plan 02 original scope notes

Scope per the roadmap: grow from 22 to roughly 320 mods in category waves following spec section 5, then config normalization and AlmostUnified recipe unification. Mandated first three commits (from the final Plan 01 review):
1. Add an empty `.nojekyll` at repo root, then confirm https://luskish.github.io/afterlight-pack/pack.toml still serves after the next main deploy.
2. Harden `.github/workflows/pack-ci.yml`: `permissions: {contents: read}`, `concurrency` group with cancel-in-progress, `timeout-minutes: 30`, `workflow_dispatch:` trigger.
3. Pin the packwiz version in CI (replace `@latest` in the `go install` line with a known-good commit hash).

Wave pattern for mod additions (repeat per category from spec section 5): add mods with correct sides, `packwiz refresh`, commit (pack.toml + index.toml + mods/ together), run `./tools/verify-pack.sh` (must be ALL GREEN), push dev, confirm CI green. Run `BOOT_TIMEOUT=600 ./tools/server-test.sh` before any merge to main. Expect some mods to need dependency additions; accept packwiz's dependency prompts and verify them.

## Step-by-step: handing off to Codex

1. In Codex, connect the GitHub account (Luskish) and point it at `Luskish/afterlight-pack`, branch `dev`. The repo is public and self-contained: skills, tools, docs all travel with the clone. No secrets exist or are needed.
2. Local-machine note: if running on Shane's Mac instead of Codex cloud, the toolchain already exists (JDK in `~/.jdks`, packwiz in `~/go/bin`). On a fresh cloud machine, `tools/server-test.sh` bootstraps its own NeoForge; packwiz installs via `go install github.com/packwiz/packwiz@latest`; Java 21 via the environment (see `tools/versions.env`, environment wins).
3. Paste the Kickoff Prompt below as the first message.
4. Review the Plan 02 document the agent produces BEFORE letting it execute (this is the one human gate that catches scope drift cheapest).
5. Per session afterwards, paste the Continuation Prompt.

## Kickoff Prompt (paste into Codex, first session)

```
You are taking over the AFTERLIGHT Minecraft modpack project mid-stream. It is a story-driven kitchen-sink pack (NeoForge 1.21.1) with completed foundation infrastructure. Work on branch dev.

Before any action:
1. Read AGENTS.md at the repo root. Every guardrail in it is binding (no em dashes anywhere, skills-first workflow, verification before claims, packwiz discipline, branch model).
2. Read docs/HANDOFF.md (current state), docs/superpowers/specs/2026-08-07-afterlight-modpack-design.md (the approved design), and the roadmap table in docs/superpowers/plans/2026-08-07-afterlight-01-foundation.md.
3. Read the SKILL.md of each skill in .agents/skills/. Before each piece of work, re-read the relevant skill and follow it (packwiz work: minecraft-modpack-authoring; mod lookups: modrinth-api; later phases: ftb-quests, kubejs-modding).

Then: docs/superpowers/plans/2026-08-08-afterlight-02-roster.md already exists and is partially executed. Find the first wave in docs/HANDOFF.md's live progress table that is not COMPLETE and execute it per the plan's Wave Pattern (including the lessons recorded in completed waves' notes: printf 'Y\n' piped into every packwiz add, exact-slug discipline, side checks). Update the live progress table after every wave. If instead all Plan 02 tasks are complete, write the next plan per the roadmap table in the Plan 01 document and present it for approval before executing.

Respect the spec's taste calibration: Create moderate, magic compact, GregTech as optional Deep Vault, generous on wow-factor. Every wave ends with tools/verify-pack.sh ALL GREEN and a commit; server-test green at MILESTONE waves and before any merge to main. When you hit a genuine ambiguity, ask me one question at a time with a recommended option.
```

## Continuation Prompt (paste to resume in later sessions)

```
Continuing the AFTERLIGHT modpack project on branch dev. Re-read AGENTS.md and docs/HANDOFF.md, check git log and the current plan document in docs/superpowers/plans/ to find the first unfinished task, then continue executing it. Follow every guardrail (no em dashes, skills-first, verify before claiming, packwiz discipline). Run ./tools/verify-pack.sh before telling me anything is done. Ask me one question at a time when genuinely blocked.
```

## Review Prompt (optional, run periodically or before merging dev to main)

```
Act as a skeptical reviewer of the AFTERLIGHT repo on branch dev. Read AGENTS.md for the binding guardrails, then audit the most recent work: verify tools/verify-pack.sh is ALL GREEN, confirm every mod added since the last merge has a deliberate side value and matches a spec section 5 category, check no root file entered the packwiz index unintentionally (grep index.toml), confirm CI is green, and list any guardrail violations with file references. Report findings ranked by severity. Do not fix anything without my approval.
```

## Hard rules the prompts assume (also in AGENTS.md)

- No em dashes in any text, anywhere.
- Skills in `.agents/skills/` are read before the work they cover, every time.
- Nothing is "done" without its verification command having just run green.
- `dev` for work, `main` only via green CI, never force-push, never delete dev.
- No jars/secrets in git; CF zip stays friends-only; new root files go into `.packwizignore`.
- One question at a time when blocked, with a recommendation.

## If returning to Claude instead of Codex

Same prompts work. Claude Code additionally auto-loads `CLAUDE.md` (which points at AGENTS.md) and has project memory covering state and Shane's preferences (opus/fable-only subagents, personal verification passes). The superpowers plugin skills (brainstorming, writing-plans, subagent-driven-development) apply on top for plan authoring and execution.
