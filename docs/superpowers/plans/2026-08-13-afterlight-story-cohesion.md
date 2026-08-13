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

Capture from the current quest corpus based on commit `7fcbc3a99fedcb8f6a62861ef86a2fd1e05fef25`. Include a schema version and source commit, but no machine-specific absolute paths.

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
- Certification: Kinetics I, chapter `23643435F7BE74AC`, order 0 to 10

Tests must prove:

- only declared top-level `quest_links`, `order_index`, and localization keys change
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
- no story quest depends directly or transitively on a manual quest
- all IDs are signed-safe and globally unique

- [ ] **Step 2: Author ECHO-voice curricula**

Implement the exact teaching goals and acquisition contracts from design sections 6.1 through 6.9. Keep tasks non-consuming unless a deliberate demonstration requires consumption. Use advancements only when the exact installed advancement exists and proves the intended action.

- [ ] **Step 3: Add rewards and visual grammar**

Use modest starter materials, requisition chits, and experience. Do not grant machines that skip the lesson. Maintain the recovered-terminal and blackbox-cathedral voice.

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
- Modify: `tools/tests/test_afterlight_quests.py`
- Modify: generated quest files under `config/ftbquests/quests/`
- Modify: generated runtime audit inputs when required

- [ ] **Step 1: Run all quest tests**

```bash
python3 -m unittest tools.tests.test_afterlight_quests -v
```

- [ ] **Step 2: Build twice and prove byte idempotence**

```bash
python3 tools/build-quests.py
git diff -- config/ftbquests/quests > /tmp/afterlight-quest-pass-1.diff
python3 tools/build-quests.py
git diff -- config/ftbquests/quests > /tmp/afterlight-quest-pass-2.diff
cmp /tmp/afterlight-quest-pass-1.diff /tmp/afterlight-quest-pass-2.diff
```

- [ ] **Step 3: Run static validation**

```bash
python3 tools/validate-quests.py --static
```

- [ ] **Step 4: Run the full test suite**

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' -v
```

- [ ] **Step 5: Commit generated quest corpus together**

If Packwiz indexes changed pack files, source the version environment and refresh exactly once before the commit:

```bash
source tools/versions.env && export PATH="$PATH_EXTRA:$PATH"
packwiz refresh
```

Commit all compiler, fixture, generated quest, `pack.toml`, `index.toml`, and applicable pack files together:

```text
feat(quests): build cohesive story corpus

Co-Authored-By: Codex <noreply@openai.com>
```

Do not run `packwiz refresh` after this commit.

## Task 9: Run Local Release Gates and Final Review

**Files:**

- Modify only when a gate exposes a root-cause defect.
- Update: `docs/PROJECT_MEMORY.md`

- [ ] **Step 1: Run pack verification**

```bash
./tools/verify-pack.sh
```

Required output: `VERIFY: ALL GREEN`.

- [ ] **Step 2: Run a fresh server boot**

```bash
BOOT_TIMEOUT=600 ./tools/server-test.sh
```

Required output: `SERVER BOOT: OK`.

- [ ] **Step 3: Validate runtime quest acquisition**

```bash
python3 tools/validate-quests.py
```

Require every manual item, advancement, filter tag, and reward to resolve in the fresh runtime registry audit.

- [ ] **Step 4: Re-run pack verification**

```bash
./tools/verify-pack.sh
git status --short
```

Required output: `VERIFY: ALL GREEN`, followed by an expected clean or explicitly reviewed tree.

- [ ] **Step 5: Run independent final review**

Review the entire branch against the approved design, compatibility fixture, common-tag declaration, no-U+2014 rule, release policy, and player-progress contract. Fix every Critical and Important finding, then repeat affected gates.

- [ ] **Step 6: Record verified outcomes**

Append every discovered failure and verified success to `docs/PROJECT_MEMORY.md`. Commit only if the ledger changed:

```text
docs(project): record story release evidence

Co-Authored-By: Codex <noreply@openai.com>
```

## Task 10: Publish, Release, and Deploy Safely

**Files:**

- Use existing release scripts and documentation.
- Update generated release notes and website data only through existing supported paths.

- [ ] **Step 1: Push dev and bind CI to the exact SHA**

```bash
git push origin dev
```

Wait for `pack-ci` on the pushed SHA. Require green status and retain the run URL and SHA as evidence.

- [ ] **Step 2: Merge dev to main without rewriting history**

Merge only after exact-SHA CI is green. Push `main`, then require exact-main-SHA CI green.

- [ ] **Step 3: Build and inspect immutable release artifacts**

Use the existing release scripts. Require exactly:

- `AFTERLIGHT-prism-instance.zip`
- `AFTERLIGHT-curseforge.zip`
- `AFTERLIGHT.mrpack`
- `SHA256SUMS`
- `release-metadata.json`

Reject unsafe paths, links, secrets, malformed archives, extra files, or checksum drift. Publish under a new immutable version and tag. Never replace an existing asset.

- [ ] **Step 4: Verify public delivery**

Confirm the AFTERLIGHT portal at `https://rl-labs.org/afterlight` points to the newly published immutable assets and that Prism, CurseForge, and Modrinth downloads return the expected checksums.

- [ ] **Step 5: Gate live deployment on zero players**

Before any server modification:

1. Query the live server player list.
2. Abort if any player is online.
3. Close external connections before shutdown.
4. Create a timestamped backup of `world/ftbquests`, `world/ftbteams`, `usercache.json`, and `whitelist.json`.
5. Canonically parse and snapshot complete FTB Quests and FTB Teams progress objects locally without committing them.

- [ ] **Step 6: Deploy server files and prove progress preservation**

Deploy the exact released server pack, start behind the closed connection gate, and wait for a clean boot. Canonically compare all pre-deploy and post-deploy progress values. Abort and restore the backup on any mismatch.

- [ ] **Step 7: Open connections and verify production**

Open the connection gate only after:

- server boot is clean
- mod inventory matches the released manifest
- quest corpus loads
- complete progress comparison is identical
- whitelist remains intact
- no recovery action was needed

Run a final status check and record the deployment success or any failure in `docs/PROJECT_MEMORY.md` without recording player identity or progress values.

## Completion Criteria

- [ ] All eight field manuals exist, are optional, and teach from zero.
- [ ] All section 7 story links resolve and have correct return links.
- [ ] Story transitions read as one ECHO-led recovery plan.
- [ ] Safe commodity tasks accept all verified common-tag variants.
- [ ] Existing quest identities and live progress remain intact.
- [ ] Quest build is deterministic and idempotent.
- [ ] `VERIFY: ALL GREEN` and `SERVER BOOT: OK` pass in the final session.
- [ ] Exact-SHA CI is green on dev and main.
- [ ] Immutable launcher artifacts and website links are verified.
- [ ] VPS deployment completes only with zero players and an identical canonical progress comparison.
- [ ] The repository memory ledger records all verified additions, failures, issues, vulnerabilities, decisions, and successes.
