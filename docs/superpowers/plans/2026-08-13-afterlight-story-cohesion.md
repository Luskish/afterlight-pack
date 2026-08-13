# AFTERLIGHT Story Cohesion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Deliver eight optional beginner field manuals, cohesive story transitions, progress-safe quest links, common-tag item matching where semantics are interchangeable, durable project memory, and an immutable client/server release without changing existing player progress.

**Architecture:** Extend the deterministic Python quest compiler with first-class quest links, additive field-manual catalog data, strict legacy overlays, and a complete canonical compatibility fixture. Keep existing IDs stable. Treat repository memory as the cross-agent source of truth, with the optional external memory index used only for recall. Release through the existing Packwiz, CI, immutable artifact, website, and VPS paths after all local and production safety gates pass.

**Tech Stack:** Python 3.11+, `unittest`, FTB Quests SNBT, FTB Filter System, Packwiz, NeoForge 1.21.1, Java 21, GitHub Actions, systemd, SSH.

**Applicable Skills:** `ftb-quests`, `minecraft-modpack-authoring`, `modrinth-api`, `minecraft-modding`, `neoforge-modding`, `superpowers:test-driven-development`, `superpowers:verification-before-completion`, `skill-creator`.

## Global Constraints

- [ ] Never use U+2014 in code, docs, quest text, commits, or user-facing messages.
- [ ] Never change an existing chapter, quest, task, reward, or link ID.
- [ ] Preserve task counts, reward state, claims, pinned state, and team ownership.
- [ ] New manual quests are optional and never become story dependencies.
- [ ] Generalize only truly interchangeable commodities with verified `c:` tags.
- [ ] Do not generalize machines, components, schematics, unique progression items, or mod-specific resources.
- [ ] Do not commit player names, UUIDs, live progress values, tokens, keys, or backups.
- [ ] Do not deploy or restart while a player is online.
- [ ] Every implementation commit includes `Co-Authored-By: Codex <noreply@openai.com>`.
- [ ] Never run `packwiz refresh` after the final pack commit.

## Task 1: Add Durable Cross-Agent Project Memory

**Files:**

- Create: `.agents/skills/afterlight-project-memory/SKILL.md`
- Create: `docs/PROJECT_MEMORY.md`
- Create: `tools/tests/test_project_memory.py`
- Modify: `AGENTS.md`

- [ ] **Step 1: Write the failing memory contract test**

Add tests that require:

- `AGENTS.md` names and mandates `afterlight-project-memory` before and after every task.
- `docs/PROJECT_MEMORY.md` contains the required event schema and all six categories: issue, vulnerability, addition, failure, success, decision.
- The project-memory skill directs agents to search before work and append after verified events.
- The ledger forbids secrets, player identity, UUIDs, and raw live progress.
- All three files contain no U+2014.

Run:

```bash
python3 -m unittest tools.tests.test_project_memory -v
```

Expected: FAIL because the skill and ledger do not exist.

- [ ] **Step 2: Scaffold the project skill**

Run:

```bash
python3 /Users/shaneliszewski/.codex/skills/.system/skill-creator/scripts/init_skill.py \
  afterlight-project-memory \
  --path .agents/skills
```

Replace the generated template with a concise workflow:

1. Search `docs/PROJECT_MEMORY.md` and available external memory before work.
2. Record every verified issue, vulnerability, addition, failure, success, and decision.
3. Include date, category, status, subsystem, summary, evidence, files or commit, impact, and follow-up.
4. Update an existing entry when the same event changes state instead of creating contradictory history.
5. Redact secrets and live player data.
6. Never claim success without same-session evidence.

- [ ] **Step 3: Seed the canonical ledger**

Create a concise ledger with durable lessons already established in this project:

- Signal Pin and Claim packet encoding failure and the verified 0.2.1 fix.
- Slow Fire multiblock advancement detection repair.
- Steel Yourself common-tag repair using `c:ingots/steel`.
- SmartBrainLib loader-line mismatch lesson for CurseForge clients.
- Client/server parity, static validation, boot validation, and immutable release requirements.
- Story-cohesion compatibility contract and live-progress protection.
- Any verification failure encountered during this implementation, followed by its resolution.

Do not include player names, UUIDs, timestamps copied from live files, or progress values.

- [ ] **Step 4: Update AGENTS.md**

Add a hard-rule section that makes the repository ledger canonical for Codex, Claude, and other agents. Require the project-memory skill before and after every task and require event recording before a task is called complete.

- [ ] **Step 5: Validate and commit**

Run:

```bash
python3 -m unittest tools.tests.test_project_memory -v
python3 /Users/shaneliszewski/.codex/skills/.system/skill-creator/scripts/quick_validate.py \
  .agents/skills/afterlight-project-memory
rg -n $'\u2014' AGENTS.md docs/PROJECT_MEMORY.md .agents/skills/afterlight-project-memory || true
git diff --check
```

Expected: tests pass, skill validation passes, U+2014 search is empty.

Commit:

```text
docs(project): add durable cross-agent memory

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 2: Freeze the Quest Compatibility Baseline

**Files:**

- Create: `tools/afterlight_quests/compatibility.py`
- Create: `tools/fixtures/quests/story-cohesion-baseline.json`
- Modify: `tools/tests/test_afterlight_quests.py`
- Modify: `docs/superpowers/specs/2026-08-13-afterlight-story-cohesion-design.md`
- Modify: `tools/afterlight_quests/__init__.py`

- [ ] **Step 1: Amend the approved compatibility contract**

Document the user-approved commodity exception:

- An existing item task may change from one mod-specific commodity item to a semantically equivalent `ftbfiltersystem:item_tag` filter.
- The task ID, count, consume behavior, components matching, and all surrounding quest data remain fixed.
- The tag must exist in the installed runtime and represent interchangeable outputs.
- No machine, component, schematic, custom progression item, or mod-specific resource qualifies.

- [ ] **Step 2: Write failing baseline tests**

Test a canonical recursive representation of:

- `chapter_groups.snbt`
- every chapter and quest link
- every quest, task, and reward
- `lang/en_us.snbt`
- reward tables

Mutation tests must fail for a changed task count, reward payload, quest flag, dependency, title, icon, and owner. The only allowed existing-field changes are those listed in the design, plus declared commodity task item replacements.

Run:

```bash
python3 -m unittest \
  tools.tests.test_afterlight_quests.StoryCohesionCompatibilityTests -v
```

Expected: FAIL because compatibility support and the fixture do not exist.

- [ ] **Step 3: Implement canonical capture and comparison**

Add interfaces:

```python
def capture_quest_corpus(quest_root: Path) -> dict[str, object]: ...

def compare_quest_corpus(
    baseline: Mapping[str, object],
    current: Mapping[str, object],
    *,
    commodity_replacements: Mapping[str, str],
) -> list[str]: ...
```

Canonicalize mappings recursively, preserve list order where FTB semantics use order, and report exact paths for every mismatch.

- [ ] **Step 4: Capture the immutable pre-overhaul fixture**

Extract `config/ftbquests/quests` directly from Git object `7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25` into a disposable directory and capture the fixture from those bytes, not from the working tree. Include a schema version and source commit, but no machine-specific absolute paths. Before accepting the fixture, prove that the current pre-overhaul corpus is canonically equal to the extracted Git object except for no fields at all. This prevents accidental working-tree drift from being blessed as the baseline.

- [ ] **Step 5: Prove fail-closed behavior and commit**

Run the focused test twice and confirm deterministic fixture serialization.

Commit:

```text
test(quests): freeze story compatibility baseline

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 3: Add First-Class Quest Link Compilation

**Files:**

- Modify: `tools/afterlight_quests/builder.py`
- Modify: `tools/afterlight_quests/__init__.py`
- Modify: `tools/tests/test_afterlight_quests.py`

- [ ] **Step 1: Write failing link tests**

Cover:

- deterministic IDs from `stable_id("quest_link", slug)`
- explicit signed-safe IDs
- slug and explicit quest targets
- rendering into the chapter-level `quest_links` array
- global collision detection across groups, chapters, links, quests, tasks, and rewards
- unresolved link targets
- duplicate target-and-coordinate triples
- separate rejection tests for `NaN`, positive infinity, and negative infinity coordinates
- malformed coordinates and high-bit IDs
- empty chapters retaining `quest_links: [ ]`

- [ ] **Step 2: Add the data model**

Implement:

```python
@dataclass(frozen=True)
class QuestLinkSpec:
    slug: str
    linked_quest: str
    x: float
    y: float
    explicit_id: str | None = None
```

Add `quest_links: tuple[QuestLinkSpec, ...] = ()` to `ChapterSpec`.

- [ ] **Step 3: Render and validate links**

Render only the installed FTB Quests 2101.1.30 schema:

```snbt
quest_links: [
    { id: "...", linked_quest: "...", x: 0.0d, y: 0.0d }
]
```

Resolve all link targets against the complete catalog and declared legacy quest ID set before writing output.

- [ ] **Step 4: Run focused tests and commit**

Commit:

```text
feat(quests): compile deterministic quest links

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 4: Add Fail-Closed Legacy Quest Overlays

**Files:**

- Create: `tools/afterlight_quests/legacy_quest_overlays.py`
- Modify: `tools/build-quests.py`
- Modify: `tools/tests/test_afterlight_quests.py`

- [ ] **Step 1: Write failing overlay tests**

Cover exact overlays for:

- Scavenger's Creed, chapter `4C01977EF77930A6`
- The Scarlands, chapter `770DAD173D9C234B`
- Foothold, chapter `45491A24F6B8C192`
- The Engine Room, chapter `52EF477C2D995F40`
- all seven existing Certification chapters, preserving their current relative order while moving them to 10 through 16
- all three existing Requisition Depot chapters, preserving their current relative order while moving them to 30 through 32

Tests must prove:

- only declared top-level `quest_links`, `order_index`, and localization keys change
- every existing chapter in group `4A20F33642175B95` has one unique order from the approved range with no collision against manuals
- a digest mismatch outside permitted spans fails before writing
- the second build is byte-identical
- missing or duplicate structural spans fail closed

- [ ] **Step 2: Implement explicit overlay manifests**

Expose immutable manifests for link overlays, chapter order overlays, and localization overlays. Use the existing structural SNBT scanner rather than regular-expression-only replacement.

- [ ] **Step 3: Integrate build order**

`tools/build-quests.py` must:

1. Write compiler-managed chapters.
2. Apply legacy overlays.
3. Validate the complete corpus.
4. Write no unrelated file.

- [ ] **Step 4: Run focused tests and commit**

Commit:

```text
feat(quests): add guarded legacy story overlays

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 5: Generalize Interchangeable Quest Commodities

**Files:**

- Create: `tools/fixtures/quests/common-commodity-tasks.json`
- Modify: `tools/afterlight_quests/catalog.py`
- Modify: applicable legacy chapter files through the guarded overlay path
- Modify: `tools/tests/test_afterlight_quests.py`

- [ ] **Step 1: Complete the item-task audit**

Inventory every existing item task and classify it as:

- common commodity, eligible
- mod-specific resource, ineligible
- machine or component, ineligible
- custom progression item, ineligible
- ambiguous, retain exact item

For each eligible task, record chapter ID, quest ID, task ID, old item, new common tag, count, consume behavior, and installed-runtime evidence.

- [ ] **Step 2: Write failing commodity tests**

Tests must require:

- only declared task IDs use tag filters
- every declared tag is present in the installed runtime tag audit
- task IDs, counts, consume behavior, and all non-item fields match the baseline
- at least two interchangeable producers are evidenced when the pack has multiple producers
- no machine, component, unique resource, or custom item enters the declaration

- [ ] **Step 3: Apply declared replacements**

Use the exact FTB Filter System item representation already verified by Steel Yourself. Do not introduce custom KubeJS predicates.

- [ ] **Step 4: Run focused tests and commit**

Commit:

```text
fix(quests): generalize interchangeable commodities

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 6: Author Eight Optional Field Manuals

**Files:**

- Create: `tools/afterlight_quests/field_manuals.py`
- Modify: `tools/afterlight_quests/catalog.py`
- Modify: `tools/afterlight_quests/__init__.py`
- Modify: `tools/tests/test_afterlight_quests.py`

- [ ] **Step 1: Write failing manual structure tests**

Require the exact chapter and root IDs from design section 6:

| Manual | Chapter ID | Root Quest ID |
| --- | --- | --- |
| Heavy Industry | `150C6F996983394C` | `3E77A16CB0C0AD11` |
| Matter Systems | `4DE10FFCDEEF9892` | `6B09A1A11CD08E68` |
| Storage Lattice | `01749E1554DFF98B` | `70380821D8D0339D` |
| Kinetics | `4690C88367D47FF3` | `686943DC0749D6E0` |
| Pressure | `0A510C4BD2A3818B` | `084209B68927F9FC` |
| Power Networks | `67F13F819570ED52` | `5334545A948815F6` |
| Frontier Machines | `67C126F7B1338CB1` | `6CC0CCE16F9FB5BE` |
| Nuclear Safety | `0B7C7859EBD6EFF3` | `4EEAB6F41DB426E7` |

Also require:

- group `4A20F33642175B95` localizes as `Field Manuals & Certifications`
- manual order 0 through 7
- every manual quest is `optional: true`
- every root has no dependencies
- every manual has exactly one finale reachable from its root
- no story quest depends directly or transitively on a manual quest
- every item task explicitly has `consume_items: false`
- every reward type is `item` or `xp`
- every item reward is exactly `kubejs:requisition_chit`; no other item reward is allowed
- no reward uses loot, stage, command, custom, choice, random, or table semantics
- all IDs are signed-safe and globally unique

- [ ] **Step 2: Author ECHO-voice curricula**

Implement the exact teaching goals and acquisition contracts from design sections 6.1 through 6.9. Every manual task is non-consuming. Use advancements only when the exact installed advancement exists and proves the intended action.

- [ ] **Step 3: Add rewards and visual grammar**

Use modest Requisition Chits and experience only. Do not grant starter materials, machines, schematics, Gate parts, seals, keys, or progression stages. Maintain the recovered-terminal and blackbox-cathedral voice.

- [ ] **Step 4: Run focused tests and commit**

Commit:

```text
feat(quests): add optional field manuals

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 7: Link Story Milestones and Rewrite Transitions

**Files:**

- Modify: `tools/afterlight_quests/catalog.py`
- Modify: `tools/afterlight_quests/field_manuals.py`
- Modify: `tools/afterlight_quests/legacy_quest_overlays.py`
- Modify: `config/ftbquests/quests/lang/en_us.snbt` through the compiler and overlays
- Create: `tools/fixtures/quests/story-audit.json`
- Modify: `tools/tests/test_afterlight_quests.py`

- [ ] **Step 1: Write failing link-map and prose-audit tests**

Require every source and target pair in design section 7 to resolve exactly. Each manual must contain a return link for every matching outbound story link. Return visibility must mirror the exact story target.

Require every existing story quest to be classified in `story-audit.json` as retained, revised, or linked. Revised entries may change only subtitle and description localization keys.

- [ ] **Step 2: Add managed and legacy outbound links**

Use deterministic link IDs and coordinates. Links remain visual navigation only. They never become dependencies and never contribute progress.

- [ ] **Step 3: Rewrite only approved transition prose**

Make each technology answer the problem introduced by the previous stage. Preserve titles, IDs, task data, rewards, dependencies, positions, shapes, and flags.

- [ ] **Step 4: Add return links and audit coverage**

Every manual should teach from zero, point back to the relevant story milestone, and never reveal a story target before FTB Quests would show it.

- [ ] **Step 5: Run focused tests and commit**

Commit:

```text
feat(quests): connect story to field manuals

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 8: Prove Deterministic Generation and Runtime Acquisition

**Files:**

- Modify: `tools/validate-quests.py`
- Modify: `tools/afterlight_quests/builder.py`
- Create: `tools/afterlight_quests/acquisition.py`
- Create: `tools/fixtures/quests/manual-acquisition.json`
- Modify: `tools/tests/test_afterlight_quests.py`
- Create: `tools/hash-generated-quests.py`
- Create: `tools/client-quest-smoke.sh`
- Modify: `tools/release-gauntlet.sh`
- Modify: `tools/server-test.sh`
- Modify: `tools/rc_hygiene.py`
- Modify: `tools/tests/test_rc_hygiene.py`
- Modify: `tools/tests/test_rc_hygiene_reliability.py`
- Modify: applicable release and client test files
- Modify: generated quest files under `config/ftbquests/quests/`
- Create: `kubejs/server_scripts/afterlight/generated_manual_acquisition_audit.js`

- [ ] **Step 1: Run all quest tests**

```bash
python3 -m unittest tools.tests.test_afterlight_quests -v
```

- [ ] **Step 2: Build twice and prove complete byte idempotence**

```bash
rm -rf /tmp/afterlight-quest-pass-1 /tmp/afterlight-quest-pass-2
python3 tools/build-quests.py
python3 tools/hash-generated-quests.py --output /tmp/afterlight-quest-pass-1
python3 tools/build-quests.py
python3 tools/hash-generated-quests.py --output /tmp/afterlight-quest-pass-2
diff -ru /tmp/afterlight-quest-pass-1 /tmp/afterlight-quest-pass-2
```

The generated-file inventory must include every tracked and newly created chapter, localization file, managed-state file, reward table when applicable, `kubejs/server_scripts/afterlight/generated_quest_item_audit.js`, and `kubejs/server_scripts/afterlight/generated_manual_acquisition_audit.js`. It must detect untracked files and compare path, mode, size, and SHA-256.

- [ ] **Step 3: Run static validation**

```bash
python3 tools/validate-quests.py --static
```

Require exactly one checked-in acquisition declaration for every manual node. Static validation proves the declaration type agrees with the task contract.

The acquisition fixture uses schema version 1 and maps each quest ID to exactly one record with `task_id`, `method`, and method-specific proof:

- `advancement`: exact advancement resource ID
- `recipe`: exact effective recipe ID, recipe type, expected output item, and minimum count
- `process`: ordered effective recipe IDs and types with expected intermediate and final outputs
- `worldgen`: exact loaded registry keys or resource paths plus the documented native acquisition target
- `manual_check`: exact checkmark task ID and observable action localization key

Item targets and common filters remain in the quest task, not duplicated as unverified free text in the fixture.

- [ ] **Step 4: Prove effective runtime acquisition**

Generate `generated_manual_acquisition_audit.js` deterministically from the fixture. On a fresh server, after KubeJS recipes are active, it emits:

```text
AFTERLIGHT_ACQUISITION_AUDIT_BEGIN schema=1 nonce=<nonce> manifest=<sha256>
AFTERLIGHT_ACQUISITION_AUDIT_NODE quest=<id> task=<id> method=<method> status=OK proof=<sha256>
AFTERLIGHT_ACQUISITION_AUDIT_OK count=<count> nonce=<nonce> manifest=<sha256>
```

For recipes and processes, inspect the effective server recipe manager by exact recipe ID, exact recipe type, and actual result stack after KubeJS changes. For advancements, inspect the loaded advancement manager. For worldgen, inspect every declared loaded registry key or server resource and its native acquisition target. Manual checks require a checkmark task and nonempty observable-action localization. A registry item entry alone is insufficient.

`tools/validate-quests.py` computes the fixture digest, requires the current boot nonce and manifest in the KubeJS server log, rejects duplicate or missing node lines, and requires exact proof digests. Focused red tests cover zero declarations, duplicate declarations, invalid methods, missing recipes, wrong recipe types, replaced outputs, broken process intermediates, missing advancements, absent worldgen resources, stale nonces, stale manifests, and extra or missing runtime lines.

`tools/server-test.sh` injects the same fresh nonce into both generated quest audits before boot. `tools/rc_hygiene.py` and its reliability tests must classify the new audit as generated source, require its installed pre-render bytes to match the Packwiz source, permit only the exact nonce placeholder substitution, and bind its post-render digest into provenance. Missing, stale, multiply substituted, or otherwise changed installed audit bytes fail before launch.

- [ ] **Step 5: Add and run a real client quest smoke test**

Create a fail-closed harness with this exact protocol:

1. Allocate loopback-only random Packwiz, Minecraft, and RCON ports and a mode `0700` temporary root.
2. Install a disposable server from the candidate Packwiz bytes with `server-ip=127.0.0.1`, `online-mode=false`, a random RCON password, and no externally reachable listener.
3. Download or reuse one pinned official Prism Launcher release whose version, URL, size, and SHA-256 live in `tools/versions.env`; reject any mismatch.
4. Build one disposable Prism application root containing only the candidate instance. Launch it with `--dir "$TEMP_PRISM_ROOT" --offline AfterlightSmoke --launch afterlight-smoke --server 127.0.0.1:<port>`. Never read or copy the user's normal Prism root or account files.
5. Wait at most 600 seconds for RCON `list` to report exactly the offline smoke identity, then run `execute as AfterlightSmoke run ftbquests open_book 3E77A16CB0C0AD11`.
6. Wait 15 seconds and require the same client to remain connected. This is the deterministic screen-open success marker because the open-book packet is handled synchronously by the real FTB Quests client before the second RCON check.
7. Reject client or server logs containing disconnects, decoder or encoder exceptions, SNBT parse failures, missing localization, failed custom payloads, crashes, or FTB Quests sync errors. Require normal client login, server join, and open-book command markers.
8. Always terminate the client, launcher, server, and Packwiz processes and delete the temporary root. Distinct timeout and cleanup failures are nonzero.

Emit only `CLIENT QUEST SMOKE: OK` after every marker passes. Add the harness to `release-gauntlet.sh`. Focused tests fake each process and prove loopback binding, the exact `--dir` and offline arguments, stale marker rejection, timeout behavior, fatal-log rejection, second-list enforcement, credential-root isolation, and cleanup.

- [ ] **Step 6: Run the full test suite**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
```

- [ ] **Step 7: Refresh and run local gates before the final pack commit**

Source the version environment, refresh the indexed pack once, then run the verifier while the final pack changes are still uncommitted:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
./tools/verify-pack.sh
BOOT_TIMEOUT=600 ./tools/server-test.sh
python3 tools/validate-quests.py
```

Required output includes `VERIFY: ALL GREEN`, `SERVER BOOT: OK`, and successful runtime acquisition validation. Confirm the second refresh inside `verify-pack.sh` causes no further diff.

- [ ] **Step 8: Commit generated quest corpus together**

Commit all compiler, fixture, generated quest, `pack.toml`, `index.toml`, and applicable pack files together:

```text
feat(quests): build cohesive story corpus

Co-Authored-By: Codex <noreply@openai.com>
```

Do not run `packwiz refresh` after this commit.

## Task 9: Review and Accept the Exact Release Commit

**Files:**

- Create: `server/afterlight-progress-guard.py`
- Create: `server/afterlight-quest-safe-update.sh`
- Create: `server/afterlight-quarantine-gate.sh`
- Create: `server/systemd/afterlight-quarantine-gate.service`
- Modify: `server/afterlight-server.sh`
- Modify: `server/afterlight-maintenance.sh`
- Modify: `server/README.md`
- Modify: `tools/tests/test_friend_server.py`
- Modify: `tools/tests/test_server_maintenance.py`
- Create: `tools/tests/test_quest_safe_update.py`
- Modify only other files when a gate exposes a root-cause defect.
- Update: `docs/PROJECT_MEMORY.md`

- [ ] **Step 1: Write failing deployment-transaction tests**

Add fake Docker, RCON, `iptables`, filesystem, archive, and operator fixtures. Require one executable `server/afterlight-quest-safe-update.sh EXPECTED_SHA --confirm` transaction that:

- validates the repository HEAD equals the exact 40-character expected SHA
- takes the same nonblocking `flock` on `/run/afterlight/maintenance.lock` used by scheduled maintenance
- requires a healthy current container and two exact zero-player RCON checks
- inserts one `DOCKER-USER` TCP `25565` NEW-connection REJECT rule with a unique transaction comment, verifies it with `iptables -C`, and removes only that exact rule
- runs `save-all flush`, stops Minecraft cleanly while retaining internal operator control, and never exposes RCON
- creates a mode `0700` snapshot directory with canonical pre-state manifests and a full direct post-stop backup bound to SHA-256 and preflight extraction evidence
- starts the exact expected release behind the gate, checks health and pack revision, stops cleanly, compares complete canonical FTB Quests and FTB Teams state, then performs the second healthy start
- removes the gate and lock only after every success marker
- on every injected failure, keeps the gate closed, stops the candidate, restores the prior exact release and affected quest/team data, proves the restored state through a clean stop and equality comparison, starts it again, then removes only the owned rule and lock
- if rollback itself fails, first changes the Minecraft and backup containers to restart policy `no`, stops them, verifies both states, leaves the owned firewall rule installed, and writes a mode `0600` durable marker under `/var/lib/afterlight/quest-update-quarantine`; ordinary operator updates and scheduled maintenance must reject that marker until explicit documented recovery clears it
- installs a systemd quarantine gate ordered after Docker. On reboot the persisted `restart: no` state keeps both containers stopped while the unit waits boundedly for `DOCKER-USER`, reconstructs the exact recorded rule, verifies it, and leaves the containers disabled. If the chain never appears, the unit fails but the stopped containers remain unable to autorestart

Tests cover lock contention, malformed RCON output, players at either check, firewall insert/check/delete drift, save failure, backup verification failure, mode drift, candidate boot failure, pack SHA mismatch, shutdown failure, every canonical mismatch class, rollback failure, durable quarantine enforcement, verified `restart: no` persistence, reboot-time gate reconstruction after Docker, a boot where `DOCKER-USER` never appears, second-start failure, whitelist drift, signal interruption, and idempotent cleanup. The chain-absent reboot test must prove both containers remain stopped with autorestart disabled. No test logs identity-bearing values.

- [ ] **Step 2: Implement canonical progress guard**

`server/afterlight-progress-guard.py` is dependency-free and supports:

```text
snapshot --world WORLD --output MODE_0700_DIR
compare --world WORLD --snapshot MODE_0700_DIR
```

It structurally parses every FTB Quests and FTB Teams SNBT or JSON document, recursively canonicalizes complete values, and writes only relative file identifiers, document counts, byte hashes, canonical hashes, schema version, and snapshot digest. It rejects links, unsafe paths, duplicates, parse failures, extra or missing files, permission drift, and unsupported formats. Console output contains counts and hashes only.

- [ ] **Step 3: Implement the guarded update command**

Keep ordinary `update` for non-quest changes, but document and require `afterlight-quest-safe-update.sh` for every quest corpus deployment. Reuse existing health, revision, archive, and rollback primitives where safe. Do not shell out to ordinary `update`, because its one-start flow is not progress-safe.

- [ ] **Step 4: Run independent final review**

Review the entire branch against the approved design, compatibility fixture, common-tag declaration, no-U+2014 rule, release policy, and player-progress contract. Fix every Critical and Important finding, then repeat affected gates.

- [ ] **Step 5: Record pre-acceptance outcomes**

Append every discovered failure, fix, and verified local-gate success to `docs/PROJECT_MEMORY.md`. If review changes indexed pack content, rule the prior pack commit non-final, reopen Task 8, refresh and run all pack gates before creating its replacement final pack commit. If review changes only docs or server tooling outside the Packwiz index, run the affected tests without Packwiz refresh. Once the replacement final pack commit exists, never refresh the branch worktree.

```text
docs(project): record story release evidence

Co-Authored-By: Codex <noreply@openai.com>
```

- [ ] **Step 6: Run server transaction tests and full local suite**

```bash
python3 -m unittest tools.tests.test_quest_safe_update -v
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
git diff --check
```

Commit all transaction tooling, tests, docs, review fixes, and memory updates. Confirm the branch is clean.

- [ ] **Step 7: Run the exact clean-SHA release gauntlet**

From a clean `dev` checkout, derive `SHA=$(git rev-parse HEAD)` and run:

```bash
./tools/release-gauntlet.sh "$SHA"
```

Require `GAUNTLET: ACCEPTED $SHA`, capture the printed `GAUNTLET RECEIPT SHA-256`, and independently verify the receipt digest. The gauntlet's Packwiz refresh occurs only inside its disposable detached validation worktree and must leave the exact commit clean. Do not run Packwiz refresh in the branch worktree after the final pack commit.

## Task 10: Publish, Release, and Deploy Safely

**Files:**

- Use existing release scripts and documentation.
- Execute the tested `server/afterlight-quest-safe-update.sh` transaction from the accepted SHA.
- Update generated release notes and website data only through existing supported paths.

- [ ] **Step 1: Promote only the gauntlet-accepted SHA**

```bash
tools/promote-release.sh "$SHA" "$RECEIPT_SHA256" --confirm
```

The promoter must push `dev` by explicit refspec, wait for exact accepted `dev` CI, fast-forward `main` to the same SHA, wait for exact `main` CI, verify ordinary and cache-busted Pages parity, verify clean install parity, create the immutable annotated tag, and return to `dev`. Do not manually merge or push around the promoter.

- [ ] **Step 2: Commit and verify release evidence**

Populate the matching release document with the accepted SHA, receipt digest, gauntlet transcript digest, exact `dev` and `main` CI URLs, Pages hashes, tool versions, Signal evidence, and five artifact hashes. Commit only `docs/HANDOFF.md` and the release document as the distinct evidence commit, push `dev`, and require that exact commit's `pack-ci` run to pass.

- [ ] **Step 3: Publish the immutable accepted artifacts**

Run the existing publisher with the same accepted SHA and independently captured receipt digest:

```bash
tools/publish-release.sh "$SHA" "$VERSION" "$RECEIPT_SHA256" --confirm
```

Use `--prerelease --confirm` instead when the selected version is a release candidate. Require exactly:

- `AFTERLIGHT-prism-instance.zip`
- `AFTERLIGHT-curseforge.zip`
- `AFTERLIGHT.mrpack`
- `SHA256SUMS`
- `release-metadata.json`

Reject unsafe paths, links, secrets, malformed archives, extra files, receipt drift, or checksum drift. Publish under the new immutable tag created by the promoter. Never replace an existing asset or move a tag.

- [ ] **Step 4: Verify public delivery**

Confirm the AFTERLIGHT portal at `https://rl-labs.org/afterlight` points to the newly published immutable assets and that Prism, CurseForge, and Modrinth downloads return the expected checksums.

- [ ] **Step 5: Begin the tested production safety transaction**

On the VPS, require a clean repository checkout at the accepted SHA, then run:

```bash
sudo server/afterlight-quest-safe-update.sh "$SHA" --confirm
```

The command owns the full transaction. Before any server modification it must:

1. Acquire the existing host maintenance lock and fail if another maintenance operation owns it.
2. Query the live server player list through internal RCON and abort if any player is online.
3. Install a fail-closed `DOCKER-USER` rule that rejects new external TCP `25565` connections without affecting SSH or internal health checks. Record and verify the exact rule identity for later removal.
4. Reconfirm zero players through internal RCON.
5. Flush saves and stop Minecraft cleanly.
6. Create a mode `0700` timestamped snapshot directory and a verified authenticated backup of `world/ftbquests`, `world/ftbteams`, `usercache.json`, and `whitelist.json`.
7. Canonically parse and hash every complete FTB Quests and FTB Teams document, including task progress, started, completed, repeatable, completion counts, claimed rewards, player data, pins, scalar flags, and team properties. Output only per-file counts and hashes.

- [ ] **Step 6: Deploy, stop, and prove shutdown-time preservation**

Require the transaction transcript to prove it deployed the exact CI-approved and published server release while the gate and lock remained active. It starts behind the gate, proves the released mod inventory, waits for clean health checks, verifies the quest corpus, then stops cleanly so FTB Quests and FTB Teams flush shutdown-time state. Only after shutdown may it compare every pre-deploy and post-stop progress and team document. Any changed document, key, value, count, cooldown, repeat state, claim, pin, property, or flag triggers its tested rollback path.

- [ ] **Step 7: Perform the second verified start**

Require the transaction transcript and final status to prove the accepted release started a second time behind the connection gate with clean health checks, exact released mod inventory, quest corpus load, intact whitelist, and unchanged canonical progress hashes. The lock and firewall rule remain active until every check passes.

- [ ] **Step 8: Open connections and verify production**

The transaction opens the connection gate only after:

- server boot is clean
- mod inventory matches the released manifest
- quest corpus loads
- the post-shutdown complete progress comparison is identical
- the second start is healthy
- whitelist remains intact
- no recovery action was needed

Verify it removed only the exact owned firewall rule and released the maintenance lock, then run a final status check. Record the deployment success or any failure in `docs/PROJECT_MEMORY.md` without recording player identity or progress values.

- [ ] **Step 9: Fail-closed rollback when any production gate fails**

On any failure, require the transaction to keep the external gate closed and stop the candidate. It restores the previous exact server release and restores pre-deploy FTB Quests and FTB Teams data when canonical comparison proves mutation. It starts the previous release behind the gate, stops cleanly, requires equality with the original snapshot, starts it once more, passes health checks, then removes only its exact rule and releases the lock. If automated rollback itself fails, set and verify `restart: no` for both containers, stop and verify them, leave the exact firewall rule installed, and write the durable fail-closed quarantine marker that blocks ordinary updates and scheduled maintenance. After reboot, Docker may start but the containers remain stopped while the post-Docker systemd gate reconstructs and verifies the recorded rule. If `DOCKER-USER` is absent, the unit fails without enabling either container. Print snapshot and authenticated backup digests without identities and require documented manual recovery. Record the rejected candidate and fix forward through a new commit, gauntlet, release, and immutable tag.

## Completion Criteria

- [ ] All eight field manuals exist, are optional, and teach from zero.
- [ ] All section 7 story links resolve and have correct return links.
- [ ] Story transitions read as one ECHO-led recovery plan.
- [ ] Safe commodity tasks accept all verified common-tag variants.
- [ ] Existing quest identities and live progress remain intact.
- [ ] Quest build is deterministic and idempotent.
- [ ] A clean real client joins the disposable server, receives quest sync, and opens the quest screen without parse or packet failure.
- [ ] `VERIFY: ALL GREEN` and `SERVER BOOT: OK` pass in the final session.
- [ ] Exact-SHA CI is green on dev and main.
- [ ] Immutable launcher artifacts and website links are verified.
- [ ] VPS deployment completes only with zero players and an identical canonical progress comparison.
- [ ] The repository memory ledger records all verified additions, failures, issues, vulnerabilities, decisions, and successes.
