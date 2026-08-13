# AFTERLIGHT Project Memory

This committed ledger is the canonical cross-agent memory for AFTERLIGHT. Search it before work and update it before completion. External memory indexes can assist recall but do not override this file.

## Event Schema

Every event uses the following fields. Update the original event when its status changes.

- **Date:** `YYYY-MM-DD`
- **Category:** `issue`, `vulnerability`, `addition`, `failure`, `success`, or `decision`
- **Status:** `open`, `investigating`, `resolved`, `verified`, `accepted`, or `superseded`
- **Subsystem:** Searchable project area, mod, quest, release stage, or infrastructure component
- **Summary:** One concise statement of what happened
- **Evidence:** Same-session command, failure marker, test result, artifact digest, or production check
- **Files or Commit:** Repository paths and fixing or deciding commit when available
- **Impact:** Player, operator, security, compatibility, or maintenance consequence
- **Follow-up:** Next action, residual risk, or `None`

## Privacy Rules

- Never record secrets, player names, UUIDs, raw live progress, access tokens, private keys, IP addresses, or production backup contents.
- Keep evidence minimal and reproducible. Do not paste complete logs or private artifacts.
- A success requires same-session evidence. A prior agent's claim is context, not proof.

## Events

### MEM-2026-08-13-001

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Cross-agent continuity
- **Summary:** The committed project ledger is canonical because the available external memory index had no prior AFTERLIGHT observations and exposed no write operation.
- **Evidence:** External memory search returned no matching observations; repository guardrails and contract tests define the fallback.
- **Files or Commit:** `AGENTS.md`, `.agents/skills/afterlight-project-memory/SKILL.md`, `tools/tests/test_project_memory.py`
- **Impact:** Codex and Claude share durable history through Git even when session memory is absent.
- **Follow-up:** Search both stores before work and keep this ledger current.

### MEM-2026-08-13-002

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Signal companion networking
- **Summary:** ECHO Pin and Claim actions disconnected clients because the server attempted to encode an invalid custom payload.
- **Evidence:** Client disconnect reports named `minecraft:custom_payload`; the Signal 0.2.1 focused tests and dedicated-server boot passed after the payload fix. Released-client Pin and Claim confirmation remains pending.
- **Files or Commit:** `30a5416` and the Signal companion source under `mods-src/`
- **Impact:** The candidate no longer reproduces the known encoder defect in automated validation, but this is not a claim of completed player acceptance.
- **Follow-up:** Confirm Pin and Claim from the immutable released client, then update this event to verified.

### MEM-2026-08-13-003

- **Date:** 2026-08-13
- **Category:** issue
- **Status:** resolved
- **Subsystem:** FTB Quests, Slow Fire
- **Summary:** The Coke Oven quest could not progress because it required a held item even though completion is represented by a formed multiblock.
- **Evidence:** The task now tracks the verified Immersive Engineering multiblock formation advancement and the quest and server gates passed.
- **Files or Commit:** `5a41531`
- **Impact:** Normal Coke Oven construction completes Slow Fire without admin intervention.
- **Follow-up:** Prefer exact installed advancements for formed multiblocks when no inventory item can prove completion.

### MEM-2026-08-13-004

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** verified
- **Subsystem:** FTB Quests, Steel Yourself
- **Summary:** Steel Yourself accepts any steel ingot represented by the common `c:ingots/steel` tag through FTB Filter System.
- **Evidence:** Focused quest tests passed, `VERIFY: ALL GREEN` passed, and `SERVER BOOT: OK` passed with FTB Filter System 21.1.4 on both sides.
- **Files or Commit:** `7fcbc3a`
- **Impact:** Cross-mod steel production no longer blocks story progression.
- **Follow-up:** Audit other item tasks, but generalize only commodities with equivalent semantics and verified runtime tags.

### MEM-2026-08-13-005

- **Date:** 2026-08-13
- **Category:** issue
- **Status:** resolved
- **Subsystem:** CurseForge client installation
- **Summary:** A friend received a JavaFML provider mismatch after installing a SmartBrainLib artifact from the wrong loader line despite selecting a NeoForge-labeled file.
- **Evidence:** The exact pack-managed dependency worked in a clean Prism install. CurseForge archive acceptance remained pending, so no CurseForge recovery is claimed.
- **Files or Commit:** Packwiz SmartBrainLib metadata and launcher archives
- **Impact:** Manual mod replacement can silently create loader-line mismatches and prevent startup.
- **Follow-up:** Distribute immutable launcher archives, avoid manual dependency replacement, and complete the clean CurseForge acceptance check.

### MEM-2026-08-13-006

- **Date:** 2026-08-13
- **Category:** vulnerability
- **Status:** resolved
- **Subsystem:** Public release artifacts
- **Summary:** An earlier CI artifact path could expose a jar-bearing CurseForge export without the final release inventory and archive classification gates.
- **Evidence:** The jar-bearing artifact was deleted, CI now publishes metadata-safe output, and the release pipeline enforces a five-file flat inventory with archive inspection.
- **Files or Commit:** `98f62b9`, `AGENTS.md`, release artifact tests
- **Impact:** Public delivery no longer depends on an unclassified intermediate archive.
- **Follow-up:** Reject extra files, links, unsafe paths, secrets, and checksum drift on every immutable release.

### MEM-2026-08-13-007

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Story cohesion and live progress
- **Summary:** The main story remains the required spine while eight optional field manuals teach linked mods from zero without becoming dependencies.
- **Evidence:** The approved design freezes existing identities, defines a complete compatibility fixture, and requires canonical pre-deploy and post-deploy progress comparison.
- **Files or Commit:** `76389da`, `docs/superpowers/specs/2026-08-13-afterlight-story-cohesion-design.md`
- **Impact:** Story guidance can improve without invalidating completed, active, claimed, or pinned player state.
- **Follow-up:** Fail the build or deployment on any undeclared quest corpus or live progress mutation.

### MEM-2026-08-13-008

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Release verification discipline
- **Summary:** AFTERLIGHT mandates static pack validation, a fresh Java 21 dedicated-server boot, exact-SHA CI, immutable artifact inspection, and zero-player guarded deployment before production claims.
- **Evidence:** `AGENTS.md`, the release tooling, and the deployment design define the required markers and fail-closed sequence; each release must execute them again.
- **Files or Commit:** `AGENTS.md`, `tools/verify-pack.sh`, `tools/server-test.sh`, release scripts and tests
- **Impact:** Client/server parity and deployment safety are executable contracts instead of agent assumptions.
- **Follow-up:** Re-run every applicable gate in the same session as each release.

### MEM-2026-08-13-009

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Local skill validation
- **Summary:** The system skill validator could not start under the default Python because PyYAML was not installed.
- **Evidence:** The first run failed with `ModuleNotFoundError: No module named 'yaml'`; a disposable virtual environment with PyYAML then printed `Skill is valid!`.
- **Files or Commit:** `.agents/skills/afterlight-project-memory/SKILL.md`
- **Impact:** Project skill validation remains reproducible without changing the repository or system Python.
- **Follow-up:** Create or reuse a disposable virtual environment with PyYAML whenever the default Python lacks the validator dependency.

### MEM-2026-08-13-010

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** Packwiz release validation
- **Summary:** Direct Packwiz refresh stops after the final pack commit, while the required gauntlet may refresh only inside its disposable detached validation worktree.
- **Evidence:** `tools/release-gauntlet.sh` validates an exact clean SHA, runs `verify-pack.sh` in isolation, and rejects any resulting Git diff.
- **Files or Commit:** `AGENTS.md`, `docs/RELEASING.md`, `tools/release-gauntlet.sh`
- **Impact:** The release pipeline can prove Packwiz idempotence without mutating the branch worktree after its final pack commit.
- **Follow-up:** Treat any branch-worktree refresh after the final pack commit as a process failure.

### MEM-2026-08-13-011

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Story-cohesion release plan
- **Summary:** The first implementation plan omitted shutdown-time progress comparison, complete rollback safeguards, and the repository's exact immutable promotion pipeline.
- **Evidence:** Independent review found release, shutdown comparison, and rollback gaps. Four scoped fix rounds added executable deployment, acquisition, client smoke, provenance, and reboot quarantine contracts; final targeted review reported no residual load-bearing issue.
- **Files or Commit:** `docs/superpowers/plans/2026-08-13-afterlight-story-cohesion.md`, `AGENTS.md`
- **Impact:** The corrected plan prevents an unaccepted SHA or shutdown-written progress mutation from reaching players.
- **Follow-up:** Execute the tested transaction without shortcuts and record every implementation failure or success.

### MEM-2026-08-13-012

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Project memory integrity
- **Summary:** The first ledger contract checked policy words globally and two seeded events overstated unconfirmed released-client acceptance.
- **Evidence:** Independent review reproduced malformed-entry and continuation-line bypasses; tests now validate every event's exact one-line schema and full raw-body sensitive-data patterns. Final scoped review reported no remaining findings.
- **Files or Commit:** `tools/tests/test_project_memory.py`, `docs/PROJECT_MEMORY.md`, `.agents/skills/afterlight-project-memory/agents/openai.yaml`
- **Impact:** Future memory entries fail closed on malformed structure and no longer convert automated evidence into unearned player acceptance claims.
- **Follow-up:** Keep task reviews independent and update event status only after matching same-session evidence.

### MEM-2026-08-13-013

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** resolved
- **Subsystem:** FTB Quests, story compatibility baseline
- **Summary:** Story compatibility binds frozen and current quest entities through fail-closed identity indexes, and scans the complete supplied baseline fixture wrapper plus the supplied current input before corpus unwrapping.
- **Evidence:** Independent review reproduced duplicate quest and chapter additions returning `[]` and one valid front insertion producing 41 false mismatches. Fix regressions first ended with `FAILED (failures=70)`. The first implementation run then ended with `FAILED (failures=1)` because reward items were misclassified as commodity task targets, and the hygiene edge cycle ended with `FAILED (failures=2)` for nil UUID and UNC path gaps. Deliberately removing the cross-corpus binding check made the saved-progress reuse regression end with `FAILED (failures=1)`. After restoring the binding and hygiene checks, all 26 focused compatibility tests passed. A complete-wrapper metadata regression then ended with `FAILED (failures=9)` across every supported hygiene category before the checked unwrapping boundary was added. The independently separated wrapper and current-corpus hygiene tests subsequently ended with `Ran 2 tests in 0.015s` and `OK`, and the complete focused suite ended with `Ran 27 tests in 0.992s` and `OK`. The unchanged fixture still matches exact Git object `7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25` at SHA-256 `b0e2fe06bb712e0f19f9fd3e94f5c4d75a570315c4d1956b6e95478b45df2d5c`.
- **Files or Commit:** `0568dae`, `4d0fca3`, `tools/afterlight_quests/compatibility.py`, `tools/fixtures/quests/story-cohesion-baseline.json`, and `tools/tests/test_afterlight_quests.py`
- **Impact:** Additive entities can appear at any position without rebinding saved progress. Missing IDs, duplicate IDs, cross-kind collisions, frozen-order mutations, undeclared payload changes, and covered contamination anywhere in the supplied baseline fixture wrapper or current input fail with searchable paths. This is a compatibility-input validation guarantee, not a broader runtime or live-state guarantee.
- **Follow-up:** Run independent Task 2 re-review before beginning story-corpus generation, and use commodity declarations only for Shane-approved runtime-backed interchangeable tags.

### MEM-2026-08-13-014

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** verified
- **Subsystem:** FTB Quests, quest-link compiler
- **Summary:** Managed chapters compile deterministic first-class quest links through a complete quest-slug index, a public catalog-aware in-memory renderer, canonical one-decimal SNBT coordinates with one signed-zero identity, strict explicit targets, and a path-aware global identity namespace with consistent repeated groups.
- **Evidence:** The original focused TDD run ended with `Ran 18 tests in 0.016s` and `FAILED (failures=1, errors=22)` before the link model existed. Independent review then found hash-based slug aliases, raw-float duplicate checks, and a repeated-group collision bypass. The amended fix-round run reproduced those gaps with `Ran 25 tests in 0.088s` and `FAILED (failures=18, errors=1)`. After correction, the expanded focused suite ended with `Ran 26 tests in 0.043s` and `OK`. The first existing-builder run ended with `Ran 72 tests in 0.647s` and `FAILED (failures=1, skipped=2)` because its collision fixture reused a now-rejected duplicate quest slug; the corrected distinct-slug collision fixture then ended with `Ran 72 tests in 0.618s` and `OK (skipped=2)`. A second review found distinct signed-zero literals and no public slug-aware rendering route. The round-two red run ended with `Ran 31 tests in 0.074s` and `FAILED (failures=6, errors=2)`. After correction, the same focused suite ended with `Ran 31 tests in 0.065s` and `OK`, and the existing-builder suite ended with `Ran 72 tests in 0.651s` and `OK (skipped=2)`. Both skips required an authenticated live install and were outside this task.
- **Files or Commit:** `tools/afterlight_quests/builder.py`, `tools/afterlight_quests/__init__.py`, `tools/tests/test_afterlight_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Catalog-aware slug links resolve to each managed quest's exact ID, including explicit IDs. Direct in-memory rendering fails closed for slug targets without catalog context while preserving no-link and explicit-ID output. Writer preflight rejects invalid target syntax, absent aliases, duplicate quest slugs, canonical serialized coordinate duplicates including signed zero, divergent repeated groups, global collisions, and declared legacy reuse before quest-root mutation. These are compiler and in-memory rendering guarantees, not Minecraft runtime guarantees.
- **Follow-up:** Pass declared unmanaged quest identities only as exact signed-safe IDs through `legacy_quest_ids` when later overlay tasks compile links to frozen legacy quests.

### MEM-2026-08-13-015

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** FTB Quests, legacy story overlays
- **Summary:** Private artifact and rollback-created directory cleanup now ends with atomic, lossless retention instead of pathname unlink or rmdir. Verified owned records are reusable and bounded, while unexpected recovery remains explicit and blocks residue growth.
- **Evidence:** Independent Fix Round 3 re-review reproduced `FINAL_UNLINK_THIRD_PARTY_DELETED True`, `FINAL_UNLINK_WARNINGS 0`, `FINAL_UNLINK_RECOVERY_PATHS 0`, `FINAL_RMDIR_MODE_DIRECTORY_DELETED True`, and `FINAL_RMDIR_MODE_SURFACED False`. Fix Round 4 direct final-syscall and repeated-retention tests first ended with `Ran 3 tests in 0.030s` and `FAILED (failures=3)`. The in-root recovery retry test separately failed before fail-closed snapshot detection. After correction, `python3 -m unittest tools.tests.test_quest_build_transaction` ended with `Ran 50 tests in 11.714s` and `OK`; the relevant Story compatibility, QuestLink, overlay, QuestCompiler, and memory suite ended with `Ran 160 tests in 9.963s` and `OK (skipped=2)`. Compile, diff, no-em-dash, and generated-corpus guards passed.
- **Files or Commit:** `tools/afterlight_quests/quest_build_transaction.py`, `tools/afterlight_quests/legacy_quest_overlays.py`, `tools/afterlight_quests/builder.py`, `tools/build-quests.py`, `tools/tests/test_quest_build_transaction.py`, `tools/tests/test_afterlight_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Cleanup never destructively unlinks or removes the final replaceable private pathname. Ordinary committed results expose authenticated reusable records through `retained_paths`; unexpected state uses `unexpected_recovery_paths`, cleanup warnings, or rollback evidence without deleting third-party bytes, mode, identity, or children.
- **Follow-up:** Require independent rereview before downstream overlay population. Operators must resolve any reported unexpected recovery before retrying the affected build.

### MEM-2026-08-13-016

- **Date:** 2026-08-13
- **Category:** vulnerability
- **Status:** resolved
- **Subsystem:** FTB Quests, story compatibility allowlists
- **Summary:** The compatibility comparator had assigned the manual and Certification group ID to the Story constant, so it rejected approved Story prose while allowing unrelated manual prose and granted order changes to the wrong semantic scope.
- **Evidence:** The focused pre-fix probe reported two Story prose mismatches while accepting manual prose and order changes. The red regression ended with `Ran 2 tests in 0.175s` and `FAILED (failures=2)`. After splitting Story group `4525BB3160467FCB` from manual and Certification group `4A20F33642175B95`, the complete compatibility and memory run ended with `Ran 35 tests in 1.406s` and `OK`.
- **Files or Commit:** `tools/afterlight_quests/compatibility.py`, `tools/tests/test_afterlight_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Existing subtitle and description changes are accepted only for actual Story quests, while the group title and approved order changes are accepted only for the manual and Certification group.
- **Follow-up:** Keep Task 7 prose and Task 4 order overlays in separate explicit manifests and re-run the frozen-corpus comparator after generation.

### MEM-2026-08-13-017

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Production read-only audit tooling
- **Summary:** Early operator audit probes hit Git repository trust, shell quoting, zsh variable shadowing, and command-policy errors before corrected read-only commands completed the audit.
- **Evidence:** The failed probes produced a Git safe-directory rejection, two malformed byte-sum commands, command-not-found output after a loop variable replaced shell PATH, and one rejected command that unnecessarily included cleanup. Corrected read-only probes completed without changing production state.
- **Files or Commit:** `docs/PROJECT_MEMORY.md`
- **Impact:** No server, world, quest progress, firewall, service, or release state changed, and future audits have searchable warnings against these four operator-tooling mistakes.
- **Follow-up:** Use an explicit Git safe directory or the service account, avoid shell interpolation inside remote byte sums, never name a zsh loop variable `path`, and omit cleanup from read-only probes.

### MEM-2026-08-13-018

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** resolved
- **Subsystem:** FTB Quests, deterministic generated inventory
- **Summary:** A standalone snapshot tool copies every generated quest file plus the two exact generated audit scripts and records canonical relative path, mode, size, SHA-256, and Git state, including ignored and untracked files.
- **Evidence:** The first red run ended with `Ran 5 tests in 0.001s` and `FAILED (errors=5)` because the tool did not exist. Blueprint review then found that the first manifest-only implementation omitted source bytes, atomic publication, source-mutation detection, nested output-parent symlink rejection, and repeatability coverage. After correction, `python3 -m unittest tools.tests.test_hash_generated_quests -v` ended with `Ran 10 tests in 0.962s` and `OK`; diff and U+2014 scans were clean.
- **Files or Commit:** `tools/hash-generated-quests.py`, `tools/tests/test_hash_generated_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Consecutive quest builds can compare complete mode-preserving filesystem snapshots rather than relying on Git state, timestamps, or a digest-only manifest, and publication fails closed on source mutation or an unsafe destination.
- **Follow-up:** Run the tool after both final Task 8 build passes and require byte-identical inventory manifests before Packwiz refresh.

### MEM-2026-08-13-019

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** accepted
- **Subsystem:** Prism client-smoke automation
- **Summary:** Official Prism Launcher 11.0.3 cannot satisfy the proposed sterile offline direct-launch probe because Offline accounts are excluded from ownership and the first-run setup gate requires an ownership-valid account before CLI launch proceeds.
- **Evidence:** The exact 11.0.3 macOS asset matched size `43608206`, SHA-256 `b8e06ef55ec78fceddfa9f4270b3d4d93f2606b83f70ad6a2c6dde90f2b65408`, arm64 architecture, strict signature, identifier, team, and leaf authority. Three disposable-root probes loaded the explicit data root and candidate instance but produced no game child; the final result was `PRISM DIRECT PROBE: missing-game-child`. Exact tagged source shows the setup predicate calls `anyAccountIsValid()`, which calls `ownsMinecraft()`, while Offline accounts always return false.
- **Files or Commit:** `.superpowers/sdd/2026-08-13-afterlight-story-cohesion/task-8-client-blueprint.md`, `docs/PROJECT_MEMORY.md`
- **Impact:** This impossible credential-free probe must not be presented as client acceptance or added as a mandatory gauntlet step. The established install, static, server-boot, and manual real-account client checks remain the truthful release evidence.
- **Follow-up:** Revisit only after an official Prism change enables direct Offline startup, or use an explicitly user-operated real-account smoke without copying, fabricating, or retaining credentials.

### MEM-2026-08-13-020

- **Date:** 2026-08-13
- **Category:** decision
- **Status:** accepted
- **Subsystem:** FTB Quests, common commodity declarations
- **Summary:** Task 5 permits only Rations, Steel Yourself, Automated Steel Batch, and Industry Quota to use installed-runtime-backed common commodity filters. Steel Yourself is already generalized, while the other three retain their IDs, counts, consumption behavior, and every non-item field.
- **Evidence:** `tools/fixtures/quests/common-commodity-tasks.json` binds frozen baseline SHA-256 `b0e2fe06bb712e0f19f9fd3e94f5c4d75a570315c4d1956b6e95478b45df2d5c` and exact Git object `7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25`. Focused fixture, compatibility, compiler, and overlay validation ended with `Ran 53 tests in 9.705s` and `OK` against temporary roots. Local installed-jar inspection proved two bread producers and four declared steel producers. The complete quest suite retained two expected generated-corpus drift failures because Task 5 intentionally did not run the generator.
- **Files or Commit:** `tools/fixtures/quests/common-commodity-tasks.json`, `tools/afterlight_quests/catalog.py`, `tools/afterlight_quests/compatibility.py`, `tools/afterlight_quests/legacy_quest_overlays.py`, `tools/afterlight_quests/__init__.py`, `tools/tests/test_afterlight_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Interchangeable bread and steel outputs can satisfy the named quests without admitting machines, components, unique resources, custom progression items, or ambiguous story materials.
- **Follow-up:** Task 8 must generate the corpus once, emit and validate fresh commodity-audit records, and run the required pack and server gates before this event becomes verified.

### MEM-2026-08-13-021

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** open
- **Subsystem:** FTB Quests, generated item audit
- **Summary:** The requested Task 6 base commit already fails the committed-corpus regeneration guard because the generated quest item audit contains a stale digest.
- **Evidence:** Before Task 6 changes, `python3 -m unittest tools.tests.test_afterlight_quests tools.tests.test_project_memory -v` ended with `Ran 197 tests in 10.871s` and `FAILED (failures=1, skipped=2)` at `test_full_catalog_regeneration_is_byte_identical_to_committed_output`; the isolated regeneration expected digest prefix `9950f9bba126daefa892798ec0ffdeb01a9eb5425`, while the committed audit used prefix `cbed5a3a1b3157edd9971fcfb6ad8634f3da4e5bd`. After Task 6, the full quest suite ended with `Ran 200 tests in 10.839s` and the same single failure.
- **Files or Commit:** `df677afb0855b613420c8ad0368fab5b5787c8cd`, `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`, `tools/tests/test_afterlight_quests.py`
- **Impact:** The broad quest suite is not fully green at this base commit, but the mismatch is independent of the Task 6 catalog because the committed generated quest corpus and audit remained byte-untouched.
- **Follow-up:** Task 8 must regenerate both quest audits through the owned transaction, prove deterministic bytes, and resolve this failure without a Task 6 corpus write.

### MEM-2026-08-13-022

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** resolved
- **Subsystem:** FTB Quests, optional field manuals
- **Summary:** The catalog now contains exactly eight optional ECHO-voice field manuals with 81 linear quests, 101 non-consuming or action tasks, 89 policy-limited rewards, deterministic acquisition classifications, and no Story dependency or quest links.
- **Evidence:** The test-first run ended with `Ran 10 tests in 0.025s` and `FAILED (failures=10)` before the manual builder existed. The final focused run ended with `Ran 15 tests in 1.958s` and `OK`; independent blueprint comparison printed `BLUEPRINT_COMPARE_OK chapters=8 quests=81 task8_ids=81 corrections=2`; compile and diff verification printed `VERIFY_FOCUSED_AND_COMPILE_OK`, `GENERATED_CORPUS_UNTOUCHED`, `TASK4_TASK5_OWNERS_UNTOUCHED`, `U2014_DIFF_CLEAN`, and `OWNERSHIP_AND_DIFF_GUARDS_OK`.
- **Files or Commit:** `tools/afterlight_quests/field_manuals.py`, `tools/afterlight_quests/catalog.py`, `tools/afterlight_quests/__init__.py`, `tools/tests/test_afterlight_quests.py`, `docs/PROJECT_MEMORY.md`
- **Impact:** Players can receive beginner guidance for Heavy Industry, Matter Systems, Storage Lattice, Kinetics, Pressure, Power Networks, Frontier Machines, and Nuclear Safety without making any manual part of required Story progression. PneumaticCraft uses the component-bearing Patchouli guide and AE2 uses the craftable blank pattern.
- **Follow-up:** Task 7 may add approved quest links, and Task 8 must generate the quest corpus and exact acquisition fixture, then prove all 81 acquisition records against the effective runtime.

### MEM-2026-08-13-023

- **Date:** 2026-08-13
- **Category:** addition
- **Status:** resolved
- **Subsystem:** Cross-agent handoff continuity
- **Summary:** The handoff now records the exact Story-cohesion checkpoint, integrated safeguards and content, active task boundaries, expected pre-generation audit drift, Prism automation limitation, and progress-safe release sequence.
- **Evidence:** `docs/HANDOFF.md` names the local integration lineage through `7825f92`, preserves the dirty-checkout warning, and gives a restart prompt that requires the memory ledger and defers Packwiz, publication, and VPS deployment to their verified gates.
- **Files or Commit:** `docs/HANDOFF.md`, `docs/PROJECT_MEMORY.md`
- **Impact:** A replacement Codex or Claude session can resume without repeating completed work, weakening release gates, regenerating too early, or risking live player progress.
- **Follow-up:** Update the checkpoint again with final commit, CI, release, backup, and production evidence before declaring RC2 complete.

### MEM-2026-08-13-024

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Quest transaction release integration
- **Summary:** The first complete post-integration Python sweep exposed a credential-scanner false positive on a retention-state variable and a stale transaction test inventory that omitted the newly integrated manual and commodity outputs.
- **Evidence:** `python3 -m unittest discover -s tools/tests -p 'test_*.py' -v` ended with `Ran 768 tests in 250.123s` and `FAILED (failures=9, errors=6, skipped=77)`. Six errors and six failures were downstream forms of the intentionally stale generated audit, while three integration failures identified credential-like local names and a changed-file expectation that predated the integrated content. The locals were renamed without changing behavior, and the expected inventory now names the exact managed state, 20 changed chapter files, localization, and generated item audit.
- **Files or Commit:** `tools/afterlight_quests/quest_build_transaction.py`, `tools/tests/test_quest_build_transaction.py`, `docs/PROJECT_MEMORY.md`
- **Impact:** The secret scanner no longer confuses a cryptographic filesystem-state suffix with credential material, and the whole-build transaction test remains exact after optional manuals and generalized commodities were integrated.
- **Follow-up:** Re-run the focused transaction, repository scan, release-policy regression, memory contract, and the complete suite after final Task 8 generation removes the deliberate audit drift.

### MEM-2026-08-13-025

- **Date:** 2026-08-13
- **Category:** issue
- **Status:** resolved
- **Subsystem:** FTB Quests, Task 7 external link validation
- **Summary:** Task 7 adds valid links to legacy and not-yet-generated manual quests, but the old committed-corpus regeneration helper did not declare those exact external target IDs when it intentionally excluded manual chapters.
- **Evidence:** The first combined run ended with `Ran 222 tests in 30.157s` and three errors, including unresolved target `70380821D8D0339D`. After deriving the external ID universe from unmanaged committed quests plus excluded manual quests, the complete suite reached only the two expected Task 8 generated-corpus drift assertions.
- **Files or Commit:** `tools/tests/test_afterlight_quests.py`
- **Impact:** Source-level link validation now resolves the approved cross-boundary graph and fails on actual generated drift instead of an incomplete test target universe. Production already supplies exact unmanaged IDs.
- **Follow-up:** Task 8 must generate the manuals, Story links, localization, and audits together, then restore the committed-corpus byte-identity tests.

### MEM-2026-08-13-026

- **Date:** 2026-08-13
- **Category:** failure
- **Status:** resolved
- **Subsystem:** Local Task 7 verification wrapper
- **Summary:** Verification helper attempts hit a disallowed force-removal cleanup form, zsh's read-only `status` variable, an unmatched optional wildcard, an unescaped backtick pattern, and the machine's runtime-less system Java stub.
- **Evidence:** The first wrapper was rejected before execution. The second printed `Ran 111 tests in 30.337s` and `OK`, then ended with `read-only variable: status`. Later probes printed `no matches found: requirements*`, `unmatched "`, and `Unable to locate a Java Runtime`. Replacing cleanup with `unlink`, using `run_code`, discovering optional files through `find`, single-quoting the backtick pattern, and prepending `$JAVA_HOME/bin` produced clean reruns, including `Ran 111 tests in 31.164s`, `OK`, exit 0, and no temporary link.
- **Files or Commit:** `docs/PROJECT_MEMORY.md`
- **Impact:** Repository files and generated quest data were unaffected, and the reusable verification form now preserves the test exit code without leaving local runtime fixtures attached.
- **Follow-up:** Use `unlink` for the temporary ignored runtime link, avoid reserved zsh parameter names, discover optional paths without bare globs, single-quote patterns containing backticks, and prepend `$JAVA_HOME/bin` for Java tooling.

### MEM-2026-08-13-027

- **Date:** 2026-08-13
- **Category:** success
- **Status:** resolved
- **Subsystem:** FTB Quests, Story cohesion source contract
- **Summary:** Task 7 source declarations now classify all 170 Story quests, revise exactly 20 transitions, compile exactly 39 outbound links and 19 manual returns, and preserve optional navigation, stable identities, dependencies, tasks, rewards, and completion shapes.
- **Evidence:** The focused suite ended with `Ran 14 tests in 4.349s` and `OK`, including two independent temporary roots with byte-identical first and second generations. The full relevant source matrix ended with `Ran 111 tests in 31.164s` and `OK`. The complete quest run ended with `Ran 225 tests in 34.845s` and only two expected Task 8 generated-corpus drift failures, with two authenticated-live skips.
- **Files or Commit:** `tools/afterlight_quests/story_cohesion.py`, `tools/afterlight_quests/catalog.py`, `tools/afterlight_quests/field_manuals.py`, `tools/afterlight_quests/legacy_quest_overlays.py`, `tools/fixtures/quests/story-audit.json`, `tools/tests/test_story_cohesion_task7.py`, `tools/tests/test_afterlight_quests.py`, and `docs/PROJECT_MEMORY.md`
- **Impact:** Story technology transitions are cohesive and staged while field manuals remain optional guided branches. This is a source and temporary-generation guarantee, not a committed generated-corpus or released-runtime guarantee.
- **Follow-up:** Task 8 must generate and validate the committed corpus, acquisition audit, pack gates, server boot, and release evidence before this source-level result can become verified.
